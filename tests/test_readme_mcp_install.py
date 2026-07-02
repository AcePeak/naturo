"""Regression guard for the one-line MCP install snippets in the README.

A first-time user must be able to connect naturo to their agent by copying a
single command (issue #927). These tests assert that the README keeps a
copy-paste install block for every supported client and that the commands the
block advertises map to a real CLI invocation, so the snippets cannot silently
drift away from the actual `naturo mcp start` entry point.
"""

from __future__ import annotations

from pathlib import Path

from naturo.cli import main

_README = Path(__file__).resolve().parent.parent / "README.md"


def _readme_text() -> str:
    return _README.read_text(encoding="utf-8")


def test_readme_exists() -> None:
    assert _README.is_file(), "README.md must exist at the repository root"


def test_advertised_command_is_real() -> None:
    """The documented `naturo mcp start` command must exist in the CLI."""
    assert "mcp" in main.commands, "CLI must expose an 'mcp' command group"
    mcp_group = main.commands["mcp"]
    assert "start" in getattr(mcp_group, "commands", {}), (
        "CLI must expose 'mcp start'; the README install snippets reference it"
    )


def test_readme_has_one_line_claude_code_install() -> None:
    """Claude Code gets a true one-liner via `claude mcp add`."""
    text = _readme_text()
    assert "claude mcp add naturo -- naturo mcp start" in text


def test_readme_has_per_client_install_blocks() -> None:
    """Every supported client must have a copy-paste install snippet."""
    text = _readme_text()
    for client in ("Claude Code", "Cursor", "VS Code", "Windsurf"):
        assert client in text, f"README is missing an install snippet for {client}"


def test_readme_install_snippets_use_canonical_command() -> None:
    """All snippets must launch the server via the canonical entry point."""
    text = _readme_text()
    # stdio clients (Cursor / VS Code / Windsurf) configure command+args
    assert '"command": "naturo"' in text
    assert '"args": ["mcp", "start"]' in text
