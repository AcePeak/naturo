"""Tests for the CLI reference generator script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from naturo.cli import main


# Load the generator module from scripts/ without requiring it to be a package
_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "generate_cli_reference.py"
_spec = importlib.util.spec_from_file_location("generate_cli_reference", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

generate_reference = _mod.generate_reference
_walk_commands = _mod._walk_commands


class TestGenerateReference:
    """Tests for generate_reference()."""

    def test_generates_nonempty_markdown(self):
        result = generate_reference()
        assert len(result) > 1000, "Reference should be substantial"

    def test_contains_header(self):
        result = generate_reference()
        assert "# CLI Reference" in result

    def test_contains_global_options(self):
        result = generate_reference()
        assert "## Global Options" in result
        assert "`--json`" in result
        assert "`--verbose`" in result

    def test_contains_all_visible_top_commands(self):
        result = generate_reference()
        expected = [
            "naturo capture", "naturo see", "naturo click", "naturo type",
            "naturo press", "naturo scroll", "naturo drag", "naturo find",
            "naturo app", "naturo dialog", "naturo wait", "naturo diff",
            "naturo mcp", "naturo config", "naturo get", "naturo set",
            "naturo highlight", "naturo move", "naturo desktop",
            "naturo taskbar", "naturo tray", "naturo list",
            "naturo menu-inspect",
        ]
        for cmd in expected:
            assert cmd in result, f"Missing command: {cmd}"

    def test_no_sentinel_values(self):
        result = generate_reference()
        assert "Sentinel" not in result
        assert "UNSET" not in result

    def test_contains_subcommands(self):
        result = generate_reference()
        assert "naturo app launch" in result
        assert "naturo app quit" in result
        assert "naturo dialog detect" in result
        assert "naturo mcp start" in result

    def test_categories_present(self):
        result = generate_reference()
        assert "## See (Inspect UI)" in result
        assert "## Act (Interact)" in result
        assert "## App & Window Management" in result
        assert "## System" in result
        assert "## Tools" in result

    def test_hidden_commands_excluded_by_default(self):
        result = generate_reference()
        assert "naturo hotkey" not in result

    def test_options_table_format(self):
        result = generate_reference()
        assert "| Flag | Type | Description |" in result
        assert "|------|------|-------------|" in result


class TestWalkCommands:
    """Tests for _walk_commands()."""

    def test_returns_list(self):
        result = _walk_commands(main)
        assert isinstance(result, list)
        assert len(result) > 20, "Should find 20+ commands"

    def test_paths_are_string_lists(self):
        result = _walk_commands(main)
        for path, cmd in result:
            assert isinstance(path, list)
            assert all(isinstance(p, str) for p in path)

    def test_include_hidden_finds_more(self):
        visible = _walk_commands(main, include_hidden=False)
        with_hidden = _walk_commands(main, include_hidden=True)
        assert len(with_hidden) > len(visible)
