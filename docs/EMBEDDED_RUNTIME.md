# Embedded Python runtime (#41)

Naturo can ship as a **self-contained bundle** that carries its own CPython 3.12
interpreter, so a target machine can run naturo without any pre-installed Python.
This document describes how that runtime is assembled, why it is a build
artifact (never committed), the one embed gotcha that makes it work, and the rule
that decides between a system Python and the bundled one at runtime.

## Two pieces

| Piece | Location | Committed? | Role |
| --- | --- | --- | --- |
| Bundler script | `scripts/bundle_python.py` | yes (source) | Assembles the runtime at build time |
| Runtime resolver | `naturo/runtime/resolver.py` | yes (source) | Picks system vs. embedded interpreter |
| The runtime itself | `dist/runtime/python/` | **no — gitignored** | ~40MB build artifact, rebuilt on demand |

The ~40MB runtime is a **build artifact**. It is produced by CI (or locally) and
never lands in git — `dist/` (and `dist/runtime/` explicitly) is gitignored.

## How `scripts/bundle_python.py` assembles the runtime

```
python scripts/bundle_python.py                 # published wheel -> dist/runtime/python
python scripts/bundle_python.py --from-local    # install the local checkout instead
python scripts/bundle_python.py --check         # validate the plan, download nothing
```

Pipeline:

1. **Download** the official Windows embeddable zip from python.org
   (`python-<ver>-embed-amd64.zip`), pinned to a known-good `3.12.x`
   (`DEFAULT_PYTHON_VERSION`, overridable with `--python-version`).
2. **Extract** it into the destination (`--dest`, default `dist/runtime/python/`).
3. **Enable `site`** (see the gotcha below).
4. **Bootstrap pip** via `get-pip.py` — the embeddable distribution has no
   `ensurepip`, so `get-pip.py` is the supported bootstrap path.
5. **Install naturo** into the embedded `site-packages`. By default this installs
   the **published wheel** (`naturo==<version>`, version read from
   `naturo/version.py`) so naturo's native C++ core is **not** rebuilt from
   source. `--from-local` instead installs the working checkout (`pip install .`),
   which may trigger the native build.
6. **Verify** by running `<dest>/python.exe -m naturo --version` and asserting the
   expected version prints — proof that naturo runs on an interpreter the system
   did not provide.
7. **Report size** and warn if the runtime exceeds the **50MB budget**.

### The `._pth` `site` gotcha

The Windows embeddable distribution ships a path-configuration file named
`python3xx._pth` (e.g. `python312._pth`) with this line **commented out**:

```
#import site
```

While `import site` is commented, Python's `site` module never initialises. The
practical consequence is that **`site-packages` is not added to `sys.path`**, so
anything `pip` installs is invisible to `import`. The bundler rewrites the file to

```
import site
```

*before* bootstrapping pip. This is the single well-known step that turns an
embeddable Python into one that can host installed packages. `enable_site()` in
`scripts/bundle_python.py` performs this rewrite (uncommenting, or appending the
line if it is absent).

### Proxy handling

Downloads use `urllib`, which honors `HTTP_PROXY` / `HTTPS_PROXY` from the
environment automatically. Nothing is hardcoded. On a host whose only outbound
path is a proxy, export it before running:

```
HTTPS_PROXY=http://127.0.0.1:PORT python scripts/bundle_python.py
```

### Note on optional extras

The default install pulls naturo and its declared runtime dependency (`click`).
naturo's Windows-only extras (`pywin32`, `comtypes` via `naturo[windows]`) are
**not** installed by default to keep the runtime lean. The embedded interpreter
can import naturo and run the CLI (`--version`, `--help`, and the pure-Python
paths) out of the box; deployments that need the full native UIA/COM surface
should extend the install to `naturo[windows]==<version>` (a follow-up may add a
flag for this). The native core DLL itself already ships inside the wheel as
package data, so it is present regardless.

## Runtime resolution: system vs. embedded

`naturo/runtime/resolver.py` implements issue #41's acceptance rule:

> **Prefer a system Python when available; fall back to the embedded runtime.**

Public API (`from naturo.runtime import ...`):

- `find_system_python(min_version=(3, 9)) -> str | None` — first suitable Python
  on `PATH` (≥ 3.9), probed by actually querying its version.
- `find_embedded_python(base: Path) -> str | None` — the bundled `python.exe`
  under `base`, checking the known bundle layouts
  (`_runtime/python/`, `dist/runtime/python/`, …).
- `resolve_python(prefer_system=True, base=None) -> str` — applies the rule and
  returns the chosen interpreter, or raises `RuntimeError` if neither exists.
  `prefer_system=False` inverts the order (embedded first).

The module is pure and filesystem-injectable (every function accepts the lookup
surface it depends on), has **no import-time side effects**, and is covered by
hermetic unit tests in `tests/test_runtime_resolver.py` (no network, no real
runtime, no desktop).

## Size budget

Acceptance criterion: the assembled runtime stays within **50MB**. A default
build (published wheel, CPython 3.12.7) measures **~39MB**, comfortably under
budget. `bundle_python.py` prints the total and emits a warning to stderr if a
build exceeds 50MB.

## CI wiring (ships as a separate patch — workflow scope)

The bundling step belongs in a GitHub Actions workflow. That change is
**workflow-scoped and ships as a separate patch** (this PR does not touch
`.github/`). The intended step, for a maintainer to add to a Windows job:

```yaml
# .github/workflows/<release-or-build>.yml  (add under a windows-latest job)
  bundle-embedded-runtime:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      # Dry-run the plan on every PR (no network) so the bundler stays valid.
      - name: Validate bundler plan
        run: python scripts/bundle_python.py --check
      # Full build only where a runtime artifact is wanted (e.g. release).
      - name: Build embedded runtime
        run: python scripts/bundle_python.py
      - name: Upload runtime artifact
        uses: actions/upload-artifact@v4
        with:
          name: naturo-embedded-runtime
          path: dist/runtime/python
          if-no-files-found: error
```

`--check` is safe to run on every PR (validates inputs and prints the plan,
downloads nothing); the full build runs only where the ~40MB artifact is
actually needed.
