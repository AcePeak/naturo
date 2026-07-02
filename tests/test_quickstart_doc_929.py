"""Regression guard for the 5-minute Notepad quickstart (issue #929).

Terminator and Windows-MCP win first-run with a copy-paste quickstart that
works on the first try. ``docs/QUICKSTART.md`` is naturo's answer: it must get a
brand-new user from ``pip install`` to a verifiable first success — Claude
opening Notepad, typing, and saving — in under five minutes (issue #929).

These tests pin the acceptance guarantees so the quickstart cannot silently
drift: it must exist, be linked from the README, walk the full
install -> connect MCP -> automate Notepad -> verify flow, show the expected
output, and only reference CLI commands and MCP tools that actually exist. The
guard reads plain files and the already-imported CLI object, so it collects on
every CI lane without the optional ``mcp`` dependency installed.
"""

from __future__ import annotations

from pathlib import Path

from naturo.cli import main

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DOC = _REPO_ROOT / "docs" / "QUICKSTART.md"
_README = _REPO_ROOT / "README.md"
_MCP_REF = _REPO_ROOT / "docs" / "MCP_SERVER.md"

#: MCP tools the Notepad walkthrough drives. Each must be a real, documented
#: tool in the MCP server reference so the quickstart cannot advertise a tool
#: that does not exist.
_REFERENCED_MCP_TOOLS = ("launch_app", "type_text", "press_key", "wait_for_window")


def _doc_text() -> str:
    return _DOC.read_text(encoding="utf-8")


def test_quickstart_exists() -> None:
    """The quickstart doc must exist (issue #929)."""
    assert _DOC.is_file(), "docs/QUICKSTART.md must exist (issue #929)"


def test_readme_links_quickstart() -> None:
    """The README must point first-time users at the quickstart."""
    assert "docs/QUICKSTART.md" in _README.read_text(encoding="utf-8"), (
        "README must link docs/QUICKSTART.md so new users can find it (#929)"
    )


def test_quickstart_covers_install_and_connect() -> None:
    """The walkthrough must start from install and an MCP connect step."""
    text = _doc_text()
    assert "pip install naturo" in text, "quickstart must show the install step"
    # A copy-paste connect step: the Claude Code one-liner or the desktop config.
    assert "claude mcp add naturo" in text or "claude_desktop_config.json" in text, (
        "quickstart must show how to connect naturo to the agent (#929)"
    )


def test_quickstart_has_notepad_flow() -> None:
    """The walkthrough must open Notepad, type, save, and verify."""
    text = _doc_text().lower()
    for step in ("notepad", "type", "save", "verify"):
        assert step in text, f"quickstart must cover the '{step}' step (#929)"


def test_quickstart_shows_expected_output() -> None:
    """A first-try quickstart must tell the reader what success looks like."""
    text = _doc_text().lower()
    assert "expected" in text, (
        "quickstart must show expected output so the user can confirm success (#929)"
    )


def test_quickstart_cli_commands_are_real() -> None:
    """The `naturo mcp start` entry point the quickstart relies on must exist."""
    assert "mcp" in main.commands, "CLI must expose an 'mcp' command group"
    mcp_group = main.commands["mcp"]
    assert "start" in getattr(mcp_group, "commands", {}), (
        "CLI must expose 'mcp start'; the quickstart references it (#929)"
    )


def test_quickstart_mcp_tools_are_documented() -> None:
    """Every MCP tool the walkthrough drives must be a real, documented tool."""
    text = _doc_text()
    reference = _MCP_REF.read_text(encoding="utf-8")
    for tool in _REFERENCED_MCP_TOOLS:
        assert tool in text, f"quickstart should demonstrate the `{tool}` tool (#929)"
        assert tool in reference, (
            f"`{tool}` must be a documented MCP tool in docs/MCP_SERVER.md so the "
            f"quickstart cannot reference a tool that does not exist (#929)"
        )
