# Standalone `naturo.exe` (#43)

Naturo can ship as a **single-file Windows executable** — `naturo.exe` — that
runs on a machine with **no pre-installed Python**. It is produced by
[PyInstaller](https://pyinstaller.org/) in `--onefile` mode from the committed,
reviewable spec `naturo.spec`.

The exe is a **build artifact**: it is gitignored and never committed
(`*.exe` in `.gitignore`, plus `build/` and `dist/`). Only the build tooling is
committed.

## Two pieces

| Piece | Location | Committed? | Role |
| --- | --- | --- | --- |
| PyInstaller spec | `naturo.spec` | yes (source) | Declares the freeze: entry point, bundled DLL, hidden imports, data |
| Build wrapper | `scripts/build_exe.py` | yes (source) | Runs the build, reports size, `--check` preflight |
| The exe itself | `dist/naturo.exe` | **no — gitignored** | ~single-file build artifact, rebuilt on demand |

## Build

```
python -m pip install pyinstaller     # one-time, into the build environment
python scripts/build_exe.py           # -> dist/naturo.exe
python scripts/build_exe.py --check   # validate spec + DLL, build nothing
python scripts/build_exe.py --clean   # wipe build/ and dist/ first
# equivalently, straight PyInstaller:
pyinstaller naturo.spec
```

The wrapper prints the output path, the size, and warns if the exe exceeds the
**80 MB** acceptance budget.

### Size

The onefile exe is **~79.5 MB** (verified build, naturo 0.3.2). The bulk is
naturo's OCR / vision stack — OpenCV, NumPy, and ONNX Runtime (rapidocr) — which
backs `see --ocr`, `find --image`, and cascade OCR. `naturo.spec` drops OpenCV's
~29 MB FFmpeg video-I/O DLL (`opencv_videoio_ffmpeg*.dll`): naturo does
still-image matching, never video decode, so it is dead weight. That trim is
what keeps the exe under the 80 MB budget. Cold start is ~3.3 s (onefile
unpacks to a temp dir on each launch).

## What gets bundled

PyInstaller's static import analysis finds most of naturo, but several things
are pulled in dynamically or live outside the Python import graph. `naturo.spec`
declares them explicitly:

- **The native engine `naturo_core.dll`.** naturo loads it at runtime via
  `Path(__file__).parent.parent / "bin" / "naturo_core.dll"`
  (`naturo/bridge/_core.py`). Under a onefile freeze `__file__` resolves inside
  the extracted `_MEIPASS` tree, so the spec bundles the DLL at `naturo/bin/`
  and the **existing loader finds it with no code change**. The DLL is located
  from the installed package (wheel RECORD / editable finder / package `bin/`),
  never a hardcoded path.
- **Dynamic-import deps** — `comtypes` (+ `comtypes.client`, `comtypes.gen`) for
  COM/Excel, the `win32*` / `pywin32` family (`win32com.client`, `pythoncom`,
  `win32gui`, …), `click`, and `PIL`. Declared as hidden imports;
  `collect_submodules('comtypes')` sweeps its submodules.
- **The MCP server** (`naturo mcp start`) — `collect_submodules('mcp')` so
  FastMCP and its stdio transport resolve when frozen.
- **naturo's own submodules** — `collect_submodules('naturo')` for backends/CLI
  subcommands that import lazily.
- **Package data** — the built-in selector JSON under
  `naturo/selectors_builtin/` via `collect_data_files('naturo')`.
- **Distribution metadata** — `copy_metadata('naturo')` (and `mcp`) so
  `importlib.metadata.version(...)` resolves inside the frozen app.

## Verify it runs standalone

```
dist\naturo.exe --version     # -> naturo, version 0.3.2
dist\naturo.exe --help        # -> full CLI help (click command tree bundled)
```

`--version` printing on its own proves the frozen CPython interpreter and the
naturo import both work with **no system Python invoked**. A brief
`naturo mcp start` stdio `initialize` handshake additionally proves the native
DLL and the `mcp` deps loaded.

## Relationship to the embedded runtime (#41) and the resolver (#997)

Naturo has **two** "no system Python" delivery mechanisms; they are
complementary, not duplicates:

| | `naturo.exe` (#43) | Embedded runtime (#41) |
| --- | --- | --- |
| Shape | one frozen executable | a `~40 MB` CPython tree with naturo installed |
| Built by | `naturo.spec` / `scripts/build_exe.py` | `scripts/bundle_python.py` |
| Interpreter | PyInstaller's frozen bootloader | a real, unpacked `python.exe` |
| Best for | drop-in CLI, easiest distribution | running arbitrary `python -m ...`, extensibility |

The runtime **resolver** (`naturo/runtime/resolver.py`, #997) decides, at
runtime, between a system Python and the embedded one. `naturo.exe` sidesteps
that choice entirely: it carries its own frozen interpreter, so no resolution
happens. The DLL-loading contract, however, is shared — both paths rely on the
same `naturo/bin/naturo_core.dll` layout, which is why bundling the DLL at
`naturo/bin/` inside the freeze is all that is required.

## CI release step (workflow-scope — maintainer applies)

The exe is not built in CI yet. A release job would install the published wheel
(so the native DLL is present) and PyInstaller, then build and upload the exe as
a release asset. Add to the release workflow (`.github/workflows/…`):

```yaml
  build-standalone-exe:
    runs-on: windows-latest
    needs: [build]  # after the wheel is built/published
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install naturo (wheel, brings the native DLL) + PyInstaller
        run: |
          python -m pip install --upgrade pip
          python -m pip install "naturo==${{ github.ref_name }}" pyinstaller
      - name: Build naturo.exe
        run: python scripts/build_exe.py
      - name: Smoke-test the exe
        run: |
          dist\naturo.exe --version
          dist\naturo.exe --help
      - name: Upload standalone exe
        uses: actions/upload-artifact@v4
        with:
          name: naturo-exe
          path: dist/naturo.exe
      # For a tagged release, attach it instead:
      # - uses: softprops/action-gh-release@v2
      #   with: { files: dist/naturo.exe }
```

## Deferred

- **Code-signing** (#50) — the exe is unsigned, so SmartScreen/AV will warn on
  first run on a clean machine. Signing needs an Authenticode certificate;
  `naturo.spec` leaves `codesign_identity=None` for a signing step to fill in.
- **Clean-machine test** — building here proves the freeze works on the build
  host. Confirming it runs on a machine with **no Python at all** is a manual
  step (a fresh VM / a colleague's box) tracked separately.
- **CI artifact upload** — the YAML above is the intended shape; a maintainer
  wires it into the release workflow (this change does not touch `.github/`).
