"""Guards for the Claude Desktop Extension bundle (`naturo.mcpb`, issue #926).

A first-time user should be able to install naturo into Claude Desktop in one
click. These tests assert that the committed ``manifest.json`` stays valid
against the MCPB spec, never drifts from the real package version or MCP tool
set, and that ``scripts/build_mcpb.py`` produces a well-formed bundle. They are
deliberately import- and platform-light (no native core required) so they run in
cross-platform CI exactly as on a Windows desktop.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_mcpb  # noqa: E402  (path injected above)
from naturo.version import __version__  # noqa: E402

_MANIFEST_PATH = _REPO_ROOT / "packaging" / "mcpb" / "manifest.json"


def _committed_manifest() -> dict:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_exists() -> None:
    assert _MANIFEST_PATH.is_file(), "packaging/mcpb/manifest.json must exist"


def test_manifest_has_required_fields() -> None:
    """Every field the MCPB spec marks required must be present."""
    manifest = _committed_manifest()
    for field in build_mcpb._REQUIRED_FIELDS:
        assert field in manifest, f"manifest.json is missing required field '{field}'"
    assert manifest["manifest_version"], "manifest_version must be non-empty"
    assert manifest["author"].get("name"), "author.name is required by the spec"


def test_manifest_launches_canonical_entry_point() -> None:
    """The bundle must launch the documented `naturo mcp start` server."""
    server = _committed_manifest()["server"]
    config = server["mcp_config"]
    assert config["command"] == "naturo"
    assert config["args"] == ["mcp", "start"]


def test_manifest_version_matches_package() -> None:
    """manifest.json version must track naturo/version.py (bump_version.py guard)."""
    assert _committed_manifest()["version"] == __version__


def test_manifest_tools_match_source() -> None:
    """The committed tool list must match the tools registered in naturo/mcp/."""
    committed = {tool["name"] for tool in _committed_manifest()["tools"]}
    source = {tool["name"] for tool in build_mcpb.extract_tools()}
    assert committed == source, (
        "manifest.json tools drifted from naturo/mcp/; "
        f"missing={source - committed} stale={committed - source}"
    )
    assert len(committed) >= 50, "expected the full MCP tool surface to be listed"


def test_every_tool_has_a_description() -> None:
    for tool in _committed_manifest()["tools"]:
        assert tool.get("description"), f"tool '{tool['name']}' has no description"


def test_build_produces_valid_bundle(tmp_path: Path) -> None:
    """build_bundle writes a zip with manifest.json at its root."""
    output = tmp_path / "naturo.mcpb"
    build_mcpb.build_bundle(output)

    assert output.is_file()
    assert zipfile.is_zipfile(output)
    with zipfile.ZipFile(output) as bundle:
        assert bundle.testzip() is None, "bundle archive is corrupt"
        names = bundle.namelist()
        assert "manifest.json" in names, "manifest.json must be at the bundle root"
        built = json.loads(bundle.read("manifest.json"))

    assert built["manifest_version"]
    assert built["version"] == __version__
    assert built["server"]["mcp_config"]["command"] == "naturo"
