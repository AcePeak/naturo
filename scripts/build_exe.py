#!/usr/bin/env python3
"""Build the standalone ``naturo.exe`` via PyInstaller (issue #43).

Freezes ``naturo/__main__.py`` into a single-file ``naturo.exe`` that runs on a
machine with NO system Python, bundling the native ``naturo_core.dll`` and the
dynamic-import deps (comtypes / pywin32 / mcp) PyInstaller's static analysis
misses. The build is driven by the committed, reviewable ``naturo.spec``.

The produced exe (``dist/naturo.exe``) is a BUILD ARTIFACT — gitignored, never
committed (see .gitignore and docs/STANDALONE_EXE.md).

Usage::

    python scripts/build_exe.py           # build dist/naturo.exe
    python scripts/build_exe.py --check    # validate spec + DLL, build nothing
    python scripts/build_exe.py --clean    # remove build/ and dist/ first

Proxy: not needed — PyInstaller and all deps must already be installed
(``pip install pyinstaller``). This script only invokes the local toolchain.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = REPO_ROOT / "naturo.spec"
DIST = REPO_ROOT / "dist"
BUILD = REPO_ROOT / "build"
EXE = DIST / "naturo.exe"

# Acceptance-criteria size budget for the onefile exe (issue #43).
SIZE_BUDGET_MB = 80.0


def _resolve_dll() -> Path:
    """Locate ``naturo_core.dll`` from the installed naturo package.

    Resolved from the package (never a hardcoded path) so the build works
    wherever naturo is installed. Tried in order, first existing wins — robust
    across a normal wheel install, an editable install, and a source checkout
    that shadows the install on ``sys.path`` (mirrors naturo.spec).
    """
    candidates: list[Path] = []

    try:
        import naturo

        candidates.append(Path(naturo.__file__).resolve().parent / "bin" / "naturo_core.dll")
    except Exception:
        pass

    try:
        from importlib import metadata

        dist = metadata.distribution("naturo")
        for f in dist.files or []:
            if f.name.lower() == "naturo_core.dll":
                candidates.append(Path(dist.locate_file(f)))
    except Exception:
        pass

    for finder in list(sys.meta_path):
        mod = sys.modules.get(getattr(finder, "__module__", ""))
        mapping = getattr(mod, "MAPPING", None)
        if isinstance(mapping, dict) and "naturo" in mapping:
            candidates.append(Path(mapping["naturo"]) / "bin" / "naturo_core.dll")

    for cand in candidates:
        if cand.exists():
            return cand.resolve()

    raise SystemExit(
        "naturo_core.dll not found (searched: "
        + ", ".join(str(c) for c in candidates)
        + ").\nInstall the naturo wheel (which bundles the native engine) first: "
        "pip install naturo"
    )


def _check_pyinstaller() -> str:
    """Return the installed PyInstaller version, or exit with guidance."""
    try:
        import PyInstaller  # noqa: N813
    except ImportError:
        raise SystemExit(
            "PyInstaller is not installed. Install it into this environment:\n"
            "    python -m pip install pyinstaller"
        )
    return PyInstaller.__version__


def check() -> None:
    """Validate the build inputs without producing anything."""
    version = _check_pyinstaller()
    dll = _resolve_dll()
    if not SPEC.exists():
        raise SystemExit(f"Spec not found: {SPEC}")
    import naturo
    from naturo.version import __version__ as naturo_version

    print("naturo.exe build — preflight check")
    print(f"  PyInstaller : {version}")
    print(f"  naturo      : {naturo_version}  ({Path(naturo.__file__).parent})")
    print(f"  native DLL  : {dll}  ({dll.stat().st_size / 1024:.0f} KB)")
    print(f"  spec        : {SPEC}")
    print("OK — ready to build (run without --check).")


def build(clean: bool) -> int:
    """Run PyInstaller against naturo.spec and report the result."""
    version = _check_pyinstaller()
    dll = _resolve_dll()
    print(f"PyInstaller {version}; bundling native DLL {dll.name}")

    if clean:
        for path in (BUILD, DIST):
            if path.exists():
                print(f"Removing {path}")
                shutil.rmtree(path, ignore_errors=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        str(SPEC),
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print(f"PyInstaller failed (exit {result.returncode}).", file=sys.stderr)
        return result.returncode

    if not EXE.exists():
        print(f"Build reported success but {EXE} is missing.", file=sys.stderr)
        return 1

    size_mb = EXE.stat().st_size / (1024 * 1024)
    print()
    print(f"Built: {EXE}")
    print(f"Size : {size_mb:.1f} MB")
    if size_mb > SIZE_BUDGET_MB:
        print(
            f"WARNING: exceeds the {SIZE_BUDGET_MB:.0f} MB acceptance budget "
            f"by {size_mb - SIZE_BUDGET_MB:.1f} MB.",
            file=sys.stderr,
        )
    else:
        print(f"Within the {SIZE_BUDGET_MB:.0f} MB budget.")
    print()
    print("Verify it runs standalone:")
    print(f"    {EXE} --version")
    print(f"    {EXE} --help")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the spec + DLL presence without building",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove build/ and dist/ before building",
    )
    args = parser.parse_args()

    if args.check:
        check()
        return 0
    return build(clean=args.clean)


if __name__ == "__main__":
    raise SystemExit(main())
