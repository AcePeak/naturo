#!/usr/bin/env python3
"""Assemble naturo's embedded Python 3.12 runtime (a build artifact, issue #41).

This script produces a self-contained CPython runtime with naturo pre-installed,
so a target machine can run naturo without a system Python. The output (~40MB) is
a BUILD ARTIFACT — it is gitignored, never committed. CI rebuilds it on demand
(see docs/EMBEDDED_RUNTIME.md).

Pipeline
--------
1. Download the official Windows embeddable zip from python.org
   (``python-<ver>-embed-amd64.zip``), pinned to a known-good 3.12.x.
2. Extract it into the destination directory.
3. Enable ``site`` by uncommenting ``import site`` in the ``python3xx._pth``
   file. The embeddable distribution ships with ``site`` DISABLED, which also
   makes ``site-packages`` invisible to ``import`` — the well-known embed gotcha
   that breaks ``pip install`` targets unless fixed first.
4. Bootstrap pip via ``get-pip.py`` (the embeddable build has no ``ensurepip``).
5. ``pip install`` naturo into the embedded ``site-packages`` — by default the
   PUBLISHED wheel (``naturo==<version>``) so naturo's native C++ core is NOT
   rebuilt from source; ``--from-local`` instead installs the local checkout.
6. Verify by running ``<dest>/python.exe -m naturo --version`` and asserting the
   expected version prints.
7. Report the total runtime size and warn if it exceeds the 50MB budget.

Usage::

    python scripts/bundle_python.py                       # published wheel -> dist/runtime/python
    python scripts/bundle_python.py --from-local          # install the local checkout instead
    python scripts/bundle_python.py --python-version 3.12.7 --naturo-version 0.3.2
    python scripts/bundle_python.py --check               # validate the plan, download nothing

Proxy: ``urllib`` honors ``HTTP_PROXY`` / ``HTTPS_PROXY`` from the environment
automatically. Nothing is hardcoded here.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO_ROOT / "naturo" / "version.py"

# Pinned, known-good CPython 3.12.x. Overridable via --python-version. Kept as a
# constant so the default bump is a one-line, reviewable change.
DEFAULT_PYTHON_VERSION = "3.12.7"

# Default output. Lives under dist/ (gitignored) so the artifact never lands in
# git. See .gitignore and docs/EMBEDDED_RUNTIME.md.
DEFAULT_DEST = REPO_ROOT / "dist" / "runtime" / "python"

# Acceptance-criteria size budget for the assembled runtime.
SIZE_BUDGET_MB = 50.0

# Official, deterministic download URLs. get-pip.py has no per-version pin; the
# canonical bootstrap URL is versionless and tracks a current pip.
_EMBED_URL = "https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip"
_GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

_VERSION_RE = re.compile(r"^3\.12\.\d+$")


def read_naturo_version() -> str:
    """Return naturo's version from ``naturo/version.py`` without importing it.

    A regex read keeps this build working on any platform even when the native
    core is absent (mirrors ``scripts/build_mcpb.py``).

    Returns:
        The ``__version__`` string (e.g. ``"0.3.2"``).

    Raises:
        ValueError: If ``__version__`` cannot be found.
    """
    text = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise ValueError(f"Could not find __version__ in {VERSION_FILE}")
    return match.group(1)


def embed_url(python_version: str) -> str:
    """Return the python.org embeddable-zip URL for ``python_version``."""
    return _EMBED_URL.format(version=python_version)


def _download(url: str, dest: Path) -> None:
    """Download ``url`` to ``dest``.

    ``urllib`` reads ``HTTP_PROXY``/``HTTPS_PROXY`` from the environment on its
    own, so a proxied host works without any special handling here.

    Args:
        url: Source URL.
        dest: Local file path to write.
    """
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as response:  # noqa: S310 (trusted python.org/pypa URLs)
        data = response.read()
    dest.write_bytes(data)
    print(f"    -> {dest} ({len(data) / 1_000_000:.1f} MB)")


def _find_pth_file(dest: Path) -> Path:
    """Return the ``python3xx._pth`` path-config file inside ``dest``.

    Raises:
        FileNotFoundError: If no ``._pth`` file is present (unexpected layout).
    """
    matches = sorted(dest.glob("python*._pth"))
    if not matches:
        raise FileNotFoundError(f"No python*._pth file found under {dest}")
    return matches[0]


def enable_site(pth_file: Path) -> None:
    """Enable ``site`` in an embeddable distribution's ``._pth`` file.

    The embeddable build ships ``._pth`` with ``import site`` commented out. While
    commented, ``site`` never initialises, so ``site-packages`` is not added to
    ``sys.path`` and ``pip``-installed packages are invisible. Uncommenting it
    (or appending it if absent) is the fix that makes the runtime pip-usable.

    Args:
        pth_file: Path to the ``python3xx._pth`` file to rewrite.
    """
    lines = pth_file.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    seen_import_site = False
    for line in lines:
        stripped = line.strip()
        if stripped in ("#import site", "# import site"):
            out.append("import site")
            seen_import_site = True
        elif stripped == "import site":
            out.append("import site")
            seen_import_site = True
        else:
            out.append(line)
    if not seen_import_site:
        out.append("import site")
    pth_file.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"  enabled site in {pth_file.name}")


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run ``cmd``, streaming a short banner; return the completed process."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)


def _dir_size_mb(path: Path) -> float:
    """Return the recursive size of ``path`` in megabytes (base-10 MB)."""
    total = 0
    for entry in path.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size
    return total / 1_000_000


def build_runtime(
    dest: Path,
    python_version: str,
    naturo_version: str,
    *,
    from_local: bool,
    workdir: Path,
    extras: str = "",
) -> float:
    """Assemble the embedded runtime at ``dest`` and return its size in MB.

    Args:
        dest: Destination directory for the runtime (recreated fresh).
        python_version: CPython version to fetch (e.g. ``"3.12.7"``).
        naturo_version: naturo version to install when using the published wheel.
        from_local: Install the local checkout (``pip install .``) instead of the
            published wheel.
        workdir: Scratch directory for downloads.
        extras: Optional pip extras to install alongside naturo, given as the
            bracket body without the brackets (e.g. ``"mcp,windows"``). Empty
            installs the lean default. Applies to both the published-wheel and
            ``--from-local`` targets so callers such as the self-contained
            ``.mcpb`` builder can pull the full server dependency set.

    Returns:
        The assembled runtime's total size in megabytes.

    Raises:
        RuntimeError: If pip bootstrap, install, or the verification step fails.
    """
    # 1. Fresh destination.
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    # 2. Download + extract the embeddable zip.
    embed_zip = workdir / f"python-{python_version}-embed-amd64.zip"
    _download(embed_url(python_version), embed_zip)
    print(f"  extracting to {dest}")
    with zipfile.ZipFile(embed_zip) as archive:
        archive.extractall(dest)

    python_exe = dest / "python.exe"
    if not python_exe.is_file():
        raise RuntimeError(f"python.exe not found after extraction at {python_exe}")

    # 3. Enable site so pip's site-packages become importable.
    enable_site(_find_pth_file(dest))

    # 4. Bootstrap pip via get-pip.py (embeddable build has no ensurepip).
    get_pip = workdir / "get-pip.py"
    _download(_GET_PIP_URL, get_pip)
    proc = _run([str(python_exe), str(get_pip), "--no-warn-script-location"])
    if proc.returncode != 0:
        raise RuntimeError(f"get-pip.py failed:\n{proc.stdout}\n{proc.stderr}")
    print("  pip bootstrapped")

    # 5. Install naturo. Published wheel by default so the native C++ core is not
    #    rebuilt; --from-local installs the working checkout instead.
    suffix = f"[{extras}]" if extras else ""
    if from_local:
        target = f"{REPO_ROOT}{suffix}" if suffix else str(REPO_ROOT)
        print(f"  installing local checkout: {target}")
    else:
        target = f"naturo{suffix}=={naturo_version}"
        print(f"  installing published wheel: {target}")
    proc = _run([str(python_exe), "-m", "pip", "install", "--no-warn-script-location", target])
    if proc.returncode != 0:
        raise RuntimeError(f"pip install {target} failed:\n{proc.stdout}\n{proc.stderr}")
    print("  naturo installed")

    # 6. Verify: the embedded interpreter must run naturo standalone.
    proc = _run([str(python_exe), "-m", "naturo", "--version"])
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        raise RuntimeError(f"embedded `python.exe -m naturo --version` failed:\n{output}")
    expected = naturo_version if not from_local else read_naturo_version()
    if expected not in output:
        raise RuntimeError(
            f"embedded naturo version mismatch: expected '{expected}' in output, got: {output!r}"
        )
    print(f"  verified: {output}")

    # 7. Size.
    return _dir_size_mb(dest)


def _plan_summary(dest: Path, python_version: str, naturo_version: str, from_local: bool) -> str:
    """Return a one-line human-readable summary of the build plan."""
    source = "local checkout" if from_local else f"naturo=={naturo_version}"
    return (
        f"python={python_version} naturo={source} "
        f"dest={dest} url={embed_url(python_version)}"
    )


def main() -> int:
    """CLI entry point. Returns a process exit code."""
    default_naturo = read_naturo_version()
    parser = argparse.ArgumentParser(
        description="Assemble naturo's embedded Python 3.12 runtime (build artifact, #41).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--python-version",
        default=DEFAULT_PYTHON_VERSION,
        help="CPython 3.12.x to embed.",
    )
    parser.add_argument(
        "--naturo-version",
        default=default_naturo,
        help="naturo version to install as the published wheel (ignored with --from-local).",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DEST,
        help="Destination directory for the runtime.",
    )
    parser.add_argument(
        "--from-local",
        action="store_true",
        help="Install the local checkout (pip install .) instead of the published wheel. "
        "May trigger naturo's native C++ build.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate inputs and print the plan; download and install nothing.",
    )
    args = parser.parse_args()

    if not _VERSION_RE.match(args.python_version):
        parser.error(f"--python-version must be a 3.12.x release, got '{args.python_version}'")

    plan = _plan_summary(args.dest, args.python_version, args.naturo_version, args.from_local)

    if os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"):
        print(f"(using proxy from environment: "
              f"{os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')})")

    if args.check:
        print(f"OK  plan: {plan}")
        print(f"    size budget: {SIZE_BUDGET_MB:.0f} MB")
        return 0

    print(f"Building embedded runtime: {plan}")
    with tempfile.TemporaryDirectory(prefix="naturo-embed-") as tmp:
        size_mb = build_runtime(
            args.dest,
            args.python_version,
            args.naturo_version,
            from_local=args.from_local,
            workdir=Path(tmp),
        )

    print(f"\nRuntime assembled at {args.dest}")
    print(f"Total size: {size_mb:.1f} MB (budget {SIZE_BUDGET_MB:.0f} MB)")
    if size_mb > SIZE_BUDGET_MB:
        print(
            f"WARNING: runtime size {size_mb:.1f} MB exceeds the {SIZE_BUDGET_MB:.0f} MB budget.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
