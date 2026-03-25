"""Tests for deprecation warnings on legacy commands (hotkey, window).

Verifies that deprecated commands emit warnings without breaking
JSON output on stdout.

Fixes #278.
"""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestHotkeyDeprecationWarning:
    """Tests for 'naturo hotkey' deprecation warning."""

    def test_hotkey_text_mode_shows_warning(self, runner):
        """hotkey in text mode emits deprecation warning."""
        result = runner.invoke(main, ["hotkey", "ctrl+a"])
        assert "deprecated" in result.output.lower()
        assert "naturo press" in result.output

    def test_hotkey_json_mode_clean_json(self, runner):
        """hotkey --json must produce valid JSON without warning text on stdout."""
        # In JSON mode, the deprecation warning is suppressed entirely
        result = runner.invoke(main, ["hotkey", "ctrl+a", "--json"])
        # The entire output should be valid JSON (no warning prefix)
        lines = [ln for ln in result.output.strip().splitlines() if ln.strip()]
        for line in lines:
            # Each line should be parseable JSON
            data = json.loads(line)
            assert isinstance(data, dict)


class TestWindowDeprecationWarning:
    """Tests for 'naturo window' subcommand deprecation warnings."""

    def test_window_focus_text_mode_shows_warning(self, runner):
        """window focus in text mode emits deprecation warning."""
        result = runner.invoke(main, ["window", "focus", "--app", "Nonexistent"])
        assert "deprecated" in result.output.lower()
        assert "naturo app" in result.output

    def test_window_list_text_mode_shows_warning(self, runner):
        """window list in text mode emits deprecation warning."""
        result = runner.invoke(main, ["window", "list"])
        assert "deprecated" in result.output.lower()
        assert "naturo app" in result.output

    def test_window_focus_json_mode_clean_json(self, runner):
        """window focus --json must produce valid JSON without warning text."""
        result = runner.invoke(main, ["window", "focus", "--app", "Nonexistent", "--json"])
        lines = [ln for ln in result.output.strip().splitlines() if ln.strip()]
        for line in lines:
            data = json.loads(line)
            assert isinstance(data, dict)
