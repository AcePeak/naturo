#!/usr/bin/env python3
"""Build the naturo Claude Desktop Extension bundle (``naturo.mcpb``).

An MCP Bundle (``.mcpb``, formerly ``.dxt``) is a zip archive with a
``manifest.json`` at its root. MCPB-aware clients such as Claude Desktop read
that manifest to install an MCP server in a single click. This script stamps the
canonical manifest (``packaging/mcpb/manifest.json``) with the current package
version and the live MCP tool list, then writes the bundle to
``dist/naturo.mcpb``.

The bundle wraps the *installed* ``naturo`` console script (it launches
``naturo mcp start``) rather than vendoring the Windows-only native core, so
``pip install naturo`` is a prerequisite. See ``packaging/mcpb/README.md`` for
the rationale and the full-vendoring follow-up.

Usage::

    python scripts/build_mcpb.py            # -> dist/naturo.mcpb
    python scripts/build_mcpb.py --check    # assemble + validate, write nothing
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_SOURCE = REPO_ROOT / "packaging" / "mcpb" / "manifest.json"
BUNDLE_README = REPO_ROOT / "packaging" / "mcpb" / "README.md"
VERSION_FILE = REPO_ROOT / "naturo" / "version.py"
MCP_TOOLS_DIR = REPO_ROOT / "naturo" / "mcp"
DEFAULT_OUTPUT = REPO_ROOT / "dist" / "naturo.mcpb"

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


def main() -> int:
    """CLI entry point. Returns a process exit code."""
    parser = argparse.ArgumentParser(description="Build the naturo .mcpb bundle.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Assemble and validate the manifest without writing the bundle.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)}).",
    )
    args = parser.parse_args()

    manifest = assemble_manifest()
    summary = (
        f"manifest_version={manifest['manifest_version']} "
        f"name={manifest['name']} version={manifest['version']} "
        f"tools={len(manifest['tools'])}"
    )
    if args.check:
        print(f"OK  {summary}")
        return 0

    path = build_bundle(args.output)
    print(f"Built {path.relative_to(REPO_ROOT)}  ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
