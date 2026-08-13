#!/usr/bin/env python3
"""Build the naturo Claude Desktop Extension bundle (``naturo.mcpb``).

An MCP Bundle (``.mcpb``, formerly ``.dxt``) is a zip archive with a
``manifest.json`` at its root. MCPB-aware clients such as Claude Desktop read
that manifest to install an MCP server in a single click. This script stamps the
canonical manifest (``packaging/mcpb/manifest.json``) with the current package
version and the live MCP tool list, then writes the bundle to
``dist/naturo.mcpb``.

Two bundle flavours are produced from the same tool metadata:

* **Thin wrapper** (default): the bundle wraps the *installed* ``naturo`` console
  script (it launches ``naturo mcp start``) rather than vendoring the Windows-only
  native core, so ``pip install naturo`` is a prerequisite.
* **Self-contained** (``--self-contained``, issue #997): stacks on #41's embedded
  runtime. It assembles a CPython 3.12 runtime with ``naturo[mcp,windows]`` and the
  native ``naturo_core.dll`` INTO the bundle, then points the manifest command at
  the bundled ``python.exe`` via MCPB's ``${__dirname}`` bundle-root variable — so
  the ``.mcpb`` installs with no prior ``pip install``.

See ``packaging/mcpb/README.md`` for the rationale and layout of both modes.

Usage::

    python scripts/build_mcpb.py                    # -> dist/naturo.mcpb (thin)
    python scripts/build_mcpb.py --check            # assemble + validate, write nothing
    python scripts/build_mcpb.py --self-contained   # -> dist/naturo-selfcontained.mcpb
    python scripts/build_mcpb.py --self-contained --check   # validate layout, no download
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_SOURCE = REPO_ROOT / "packaging" / "mcpb" / "manifest.json"
BUNDLE_README = REPO_ROOT / "packaging" / "mcpb" / "README.md"
VERSION_FILE = REPO_ROOT / "naturo" / "version.py"
MCP_TOOLS_DIR = REPO_ROOT / "naturo" / "mcp"
DEFAULT_OUTPUT = REPO_ROOT / "dist" / "naturo.mcpb"

# Self-contained bundle (issue #997). Everything lands under dist/ (gitignored),
# so the vendored runtime and DLL never enter git.
SELF_CONTAINED_STAGING = REPO_ROOT / "dist" / "mcpb-selfcontained"
SELF_CONTAINED_OUTPUT = REPO_ROOT / "dist" / "naturo-selfcontained.mcpb"

# The bundled runtime lives at <staging>/server/runtime/python/. MCPB expands
# ``${__dirname}`` to the installed bundle root at launch time, so the manifest
# command is a bundle-relative path to the embedded interpreter.
_RUNTIME_SUBPATH = Path("server") / "runtime" / "python"
SELF_CONTAINED_COMMAND = "${__dirname}/server/runtime/python/python.exe"
SELF_CONTAINED_ARGS = ["-m", "naturo", "mcp", "start"]
# Full server dependency set for the self-contained runtime: the MCP server plus
# the Windows native UIA/COM surface. Names are the real extras from pyproject.toml.
SELF_CONTAINED_EXTRAS = "mcp,windows"

# Native core vendored into the runtime if the installed wheel lacks it. Default
# source is the local build tree (naturo/bin/*.dll is gitignored); override with
# --dll-source when building from a checkout that has no compiled core.
DEFAULT_DLL_SOURCE = REPO_ROOT / "naturo" / "bin" / "naturo_core.dll"
_DLL_NAME = "naturo_core.dll"

_SELF_CONTAINED_LONG_DESCRIPTION = (
    "Naturo exposes Windows desktop automation as MCP tools so AI agents can "
    "inspect the accessibility tree, capture screenshots, click, type, manage "
    "windows and apps, and drive dialogs. This self-contained bundle vendors an "
    "embedded CPython runtime with naturo[mcp,windows] and the native core "
    "(naturo_core.dll), and launches it via the bundled python.exe "
    "(`-m naturo mcp start`). It installs in one click with no separate Python "
    "or package install."
)

# The decorator that marks a nested function as a registered MCP tool. Every
# tool in ``naturo/mcp/_*.py`` is wrapped with it, so it is a reliable, parse-only
# (no import, no native DLL) signal we can also rely on from CI.
_TOOL_DECORATOR = "_safe_tool"

# Top-level manifest fields the MCPB spec requires; validated before packaging so
# a malformed bundle never ships. See https://github.com/anthropics/mcpb.
_REQUIRED_FIELDS = ("manifest_version", "name", "version", "description", "author", "server")


def read_version() -> str:
    """Return the package version from ``naturo/version.py``.

    Reads the source with a regex instead of importing the package so the build
    works on any platform without the native core present.

    Returns:
        The ``__version__`` string (e.g. ``"0.3.1"``).

    Raises:
        ValueError: If ``__version__`` cannot be found.
    """
    text = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise ValueError(f"Could not find __version__ in {VERSION_FILE}")
    return match.group(1)


def _docstring_summary(node: ast.FunctionDef) -> str:
    """Return the first non-empty line of a function's docstring, or ``""``."""
    doc = ast.get_docstring(node) or ""
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def extract_tools() -> list[dict[str, str]]:
    """Enumerate the MCP tools from source as ``{"name", "description"}`` dicts.

    Parses every ``naturo/mcp/*.py`` module with :mod:`ast` and collects each
    function decorated with ``@_safe_tool`` (the tool registration marker). This
    is purely static — it never imports naturo — so the tool list stays accurate
    in cross-platform CI where the Windows native core is absent.

    Returns:
        Tool descriptors sorted by name.
    """
    tools: list[dict[str, str]] = []
    for path in sorted(MCP_TOOLS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            decorator_names = {
                d.id for d in node.decorator_list if isinstance(d, ast.Name)
            }
            if _TOOL_DECORATOR in decorator_names:
                tools.append({"name": node.name, "description": _docstring_summary(node)})
    tools.sort(key=lambda tool: tool["name"])
    return tools


def assemble_manifest() -> dict:
    """Load the canonical manifest and stamp it with the live version and tools.

    The committed ``manifest.json`` is the single source for static metadata;
    this stamps the authoritative ``version`` (from ``naturo/version.py``) and
    refreshes the ``tools`` list so the bundle can never drift from the code.

    Returns:
        The fully assembled manifest dict.

    Raises:
        ValueError: If a required top-level field is missing.
    """
    manifest = json.loads(MANIFEST_SOURCE.read_text(encoding="utf-8"))
    manifest["version"] = read_version()
    manifest["tools"] = extract_tools()
    manifest["tools_generated"] = False

    missing = [field for field in _REQUIRED_FIELDS if field not in manifest]
    if missing:
        raise ValueError(f"manifest.json is missing required field(s): {', '.join(missing)}")
    return manifest


def build_bundle(output: Path) -> Path:
    """Write the assembled ``.mcpb`` bundle to ``output``.

    Args:
        output: Destination path for the bundle (parent dirs are created).

    Returns:
        The path written.
    """
    manifest = assemble_manifest()
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        # manifest.json MUST sit at the archive root for MCPB clients to find it.
        bundle.writestr("manifest.json", manifest_bytes)
        if BUNDLE_README.is_file():
            bundle.writestr("README.md", BUNDLE_README.read_text(encoding="utf-8"))
    return output


def assemble_selfcontained_manifest() -> dict:
    """Assemble the self-contained manifest (issue #997).

    Reuses :func:`assemble_manifest` for the version/tools stamping, then rewrites
    the fields that differ for a vendored bundle: the server command points at the
    bundled interpreter via ``${__dirname}`` and the ``long_description`` drops the
    ``pip install naturo`` prerequisite. The canonical thin-wrapper manifest on
    disk is never touched — this variant is generated in memory only.

    Returns:
        The self-contained manifest dict.
    """
    manifest = assemble_manifest()
    manifest["long_description"] = _SELF_CONTAINED_LONG_DESCRIPTION
    manifest["server"] = {
        "type": "binary",
        "entry_point": "server/runtime/python/python.exe",
        "mcp_config": {
            "command": SELF_CONTAINED_COMMAND,
            "args": list(SELF_CONTAINED_ARGS),
            "env": {},
        },
    }
    return manifest


def _find_installed_naturo_bin(runtime_dir: Path) -> Path | None:
    """Return the installed ``naturo/bin`` directory under ``runtime_dir``.

    The embeddable layout places pip installs under a ``site-packages`` folder
    whose exact parent varies, so this globs for the package rather than assuming
    a fixed path.

    Args:
        runtime_dir: Root of the assembled embedded runtime.

    Returns:
        The ``naturo/bin`` directory, or ``None`` if the package is not installed.
    """
    for site_packages in runtime_dir.rglob("site-packages"):
        bin_dir = site_packages / "naturo" / "bin"
        if bin_dir.is_dir() or (site_packages / "naturo").is_dir():
            return bin_dir
    return None


def ensure_core_dll(runtime_dir: Path, dll_source: Path) -> tuple[Path, str]:
    """Ensure ``naturo_core.dll`` is present in the runtime's ``naturo/bin``.

    If the installed wheel already carries the DLL, it is left in place; otherwise
    it is copied from ``dll_source`` (the local build tree). Presence is verified
    explicitly either way.

    Args:
        runtime_dir: Root of the assembled embedded runtime.
        dll_source: Fallback DLL to vendor if the wheel lacks one.

    Returns:
        ``(dll_path, source)`` where ``source`` is ``"published wheel"`` or
        ``"vendored from naturo/bin"``.

    Raises:
        RuntimeError: If the naturo package is missing, or the DLL is absent and
            no vendoring source exists.
    """
    bin_dir = _find_installed_naturo_bin(runtime_dir)
    if bin_dir is None:
        raise RuntimeError(f"naturo package not found under {runtime_dir}; pip install failed?")

    dll_path = bin_dir / _DLL_NAME
    if dll_path.is_file():
        return dll_path, "published wheel"

    if not dll_source.is_file():
        raise RuntimeError(
            f"{_DLL_NAME} not in the installed wheel and no vendoring source at "
            f"{dll_source}. Build the native core or pass --dll-source."
        )
    bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dll_source, dll_path)
    if not dll_path.is_file():
        raise RuntimeError(f"failed to vendor {_DLL_NAME} into {bin_dir}")
    return dll_path, "vendored from naturo/bin"


def _zip_tree(staging: Path, output: Path) -> None:
    """Zip everything under ``staging`` into ``output`` (manifest.json at root)."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(staging).as_posix())


def build_selfcontained_bundle(
    output: Path,
    staging: Path,
    *,
    python_version: str,
    from_local: bool,
    dll_source: Path,
) -> tuple[Path, float, str]:
    """Assemble and zip the fully self-contained ``.mcpb`` (issue #997).

    Stages the manifest, the bundle README, and an embedded CPython runtime with
    ``naturo[mcp,windows]`` + the native core, then zips the tree. Reuses #41's
    ``bundle_python`` for the runtime assembly (download / ._pth / pip) rather than
    duplicating it.

    Args:
        output: Destination ``.mcpb`` path.
        staging: Staging directory (recreated fresh) that becomes the zip root.
        python_version: CPython 3.12.x to embed.
        from_local: Install the local checkout instead of the published wheel.
        dll_source: Fallback DLL to vendor if the wheel lacks the native core.

    Returns:
        ``(output_path, size_mb, dll_source_label)``.

    Raises:
        RuntimeError: If runtime assembly, DLL vendoring, or verification fails.
    """
    import bundle_python  # local import: only the real build needs #41's downloader

    manifest = assemble_selfcontained_manifest()
    naturo_version = read_version()

    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    runtime_dir = staging / _RUNTIME_SUBPATH
    with tempfile.TemporaryDirectory(prefix="naturo-mcpb-") as tmp:
        bundle_python.build_runtime(
            runtime_dir,
            python_version,
            naturo_version,
            from_local=from_local,
            workdir=Path(tmp),
            extras=SELF_CONTAINED_EXTRAS,
        )

    _, dll_label = ensure_core_dll(runtime_dir, dll_source)

    staging.joinpath("manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if BUNDLE_README.is_file():
        staging.joinpath("README.md").write_text(
            BUNDLE_README.read_text(encoding="utf-8"), encoding="utf-8"
        )

    _zip_tree(staging, output)
    size_mb = output.stat().st_size / 1_000_000
    return output, size_mb, dll_label


def main() -> int:
    """CLI entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(description="Build the naturo .mcpb bundle.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Assemble and validate the manifest without writing the bundle "
        "(with --self-contained, validates the layout without downloading/zipping).",
    )
    parser.add_argument(
        "--self-contained",
        action="store_true",
        help="Build the fully self-contained bundle (embedded runtime + vendored "
        "native core); needs no prior `pip install naturo`.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (defaults per mode: dist/naturo.mcpb or "
        "dist/naturo-selfcontained.mcpb).",
    )
    parser.add_argument(
        "--python-version",
        default="3.12.7",
        help="CPython 3.12.x to embed (self-contained mode only).",
    )
    parser.add_argument(
        "--from-local",
        action="store_true",
        help="Install the local checkout instead of the published wheel "
        "(self-contained mode only).",
    )
    parser.add_argument(
        "--dll-source",
        type=Path,
        default=DEFAULT_DLL_SOURCE,
        help=f"Fallback native core to vendor if the wheel lacks it "
        f"(default: {DEFAULT_DLL_SOURCE}).",
    )
    args = parser.parse_args()

    if args.self_contained:
        manifest = assemble_selfcontained_manifest()
        summary = (
            f"manifest_version={manifest['manifest_version']} "
            f"name={manifest['name']} version={manifest['version']} "
            f"tools={len(manifest['tools'])} command={manifest['server']['mcp_config']['command']}"
        )
        if args.check:
            print(f"OK  self-contained  {summary}")
            return 0
        output = args.output or SELF_CONTAINED_OUTPUT
        path, size_mb, dll_label = build_selfcontained_bundle(
            output,
            SELF_CONTAINED_STAGING,
            python_version=args.python_version,
            from_local=args.from_local,
            dll_source=args.dll_source,
        )
        print(
            f"Built {path.relative_to(REPO_ROOT)}  ({summary})\n"
            f"  size={size_mb:.1f} MB  native core: {dll_label}"
        )
        return 0

    manifest = assemble_manifest()
    summary = (
        f"manifest_version={manifest['manifest_version']} "
        f"name={manifest['name']} version={manifest['version']} "
        f"tools={len(manifest['tools'])}"
    )
    if args.check:
        print(f"OK  {summary}")
        return 0

    path = build_bundle(args.output or DEFAULT_OUTPUT)
    print(f"Built {path.relative_to(REPO_ROOT)}  ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
