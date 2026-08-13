# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the standalone naturo.exe (issue #43).

Freezes ``naturo/__main__.py`` (``from naturo.cli import run; run()``) into a
single-file ``naturo.exe`` that runs on a machine with NO system Python. The
produced exe is a BUILD ARTIFACT — gitignored, never committed (see .gitignore
and docs/STANDALONE_EXE.md). This spec is the committed, reviewable source.

Build:
    pyinstaller naturo.spec
    # or the wrapper, which also reports size / budget:
    python scripts/build_exe.py

What this spec takes care of that PyInstaller's static analysis misses:

* The native engine ``naturo_core.dll``. naturo loads it at runtime via
  ``Path(__file__).parent.parent / "bin" / "naturo_core.dll"`` (see
  naturo/bridge/_core.py). Under a onefile freeze ``__file__`` resolves inside
  the extracted _MEIPASS tree, so bundling the DLL at ``naturo/bin/`` makes the
  EXISTING loader find it with no code change.
* Dynamic-import deps: ``comtypes`` (COM / Excel), the ``win32*`` / pywin32
  family, and ``mcp`` (the ``naturo mcp start`` server). These are imported
  lazily / conditionally, so they are declared as hidden imports and collected.
* naturo's own submodules — CLI subcommands and backends are wired up at import
  time but some backends import lazily; ``collect_submodules('naturo')`` pulls
  them all in.
* Package data: the built-in selector JSON under ``naturo/selectors_builtin/``
  and any other bundled resources, via ``collect_data_files('naturo')``.
* Distribution metadata for ``naturo`` (and ``mcp``) so ``importlib.metadata``
  version lookups resolve inside the frozen app.
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)


def _resolve_core_dll() -> Path:
    """Locate ``naturo_core.dll`` from the INSTALLED naturo package.

    Resolved from the package (never a hardcoded path) so the build works
    wherever naturo is installed. The DLL ships in the wheel under
    ``naturo/bin/``. Tried in order, first existing wins — robust across a
    normal wheel install, an editable install, and a source checkout that
    shadows the install on ``sys.path``:

    1. the imported package's ``bin/`` (the wheel-install case);
    2. the distribution's RECORD (wheel install, even when the import above is
       shadowed by a source checkout on the path);
    3. the setuptools editable finder's ``MAPPING`` (editable install whose real
       source dir differs from the shadowing checkout).
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
        + "). Install the naturo wheel (which bundles the native engine) before "
        "building: pip install naturo"
    )


_dll = _resolve_core_dll()

# Bundle the DLL at naturo/bin/ INSIDE the frozen tree so the existing runtime
# loader (Path(__file__).parent.parent / 'bin') finds it unchanged.
binaries = [(str(_dll), "naturo/bin")]

# --- Data files + metadata ----------------------------------------------------
datas = []
datas += collect_data_files("naturo")  # selectors_builtin/*.json, etc.
datas += copy_metadata("naturo")       # importlib.metadata.version("naturo")
try:
    datas += copy_metadata("mcp")
except Exception:
    pass  # mcp metadata optional; the mcp server still imports without it

# --- Hidden imports -----------------------------------------------------------
# PyInstaller's static analysis misses lazy / conditional imports. Declare them.
hiddenimports = []
hiddenimports += collect_submodules("naturo")     # all naturo subpackages
hiddenimports += collect_submodules("comtypes")   # comtypes.client, comtypes.gen, ...
hiddenimports += [
    # pywin32 family naturo touches (win32com.client, pythoncom, win32gui, ...)
    "win32com",
    "win32com.client",
    "win32gui",
    "win32api",
    "pythoncom",
    "pywintypes",
    # CLI + imaging + protocol deps that may be pulled in dynamically
    "click",
    "PIL",
    "PIL.Image",
]
# The MCP server (naturo mcp start) — collect the whole package so FastMCP and
# its transports resolve when frozen. Guarded: a build without mcp still works
# for the non-mcp CLI surface.
try:
    hiddenimports += collect_submodules("mcp")
except Exception:
    pass


block_cipher = None

a = Analysis(
    ["naturo/__main__.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# --- Trim safe-to-drop bloat --------------------------------------------------
# opencv-python ships a ~29 MB FFmpeg video-I/O DLL (opencv_videoio_ffmpeg*.dll).
# naturo uses OpenCV only for still-image template matching and OCR
# pre-processing (find --image, see --ocr) — never video decode — so this DLL is
# dead weight in the freeze. Dropping it keeps OpenCV fully functional for
# naturo's use and brings the exe under the size budget.
_EXCLUDE_BINARY_SUBSTRINGS = ("opencv_videoio_ffmpeg",)
a.binaries = [
    b for b in a.binaries
    if not any(sub in b[0].lower() for sub in _EXCLUDE_BINARY_SUBSTRINGS)
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="naturo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
