"""Tests for window command backward compatibility (fixes #277, #278).

Verifies:
- ``naturo window focus "Name"`` positional argument works
- All window subcommands emit deprecation warnings
- ``naturo hotkey`` emits deprecation warning
"""
from __future__ import annotations

import unittest.mock as mock

import pytest
from click.testing import CliRunner

from naturo.cli import main


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


# ── #277: Positional argument on window subcommands ──────────────────────


class TestWindowPositionalArg:
    """``naturo window focus "Notepad"`` should work (backward compat)."""

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_focus_positional(self, mock_backend, runner):
        """Positional NAME maps to --app."""
        result = runner.invoke(main, ["window", "focus", "Notepad"])
        assert result.exit_code == 0
        assert "Focused window" in result.output

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_close_positional(self, mock_backend, runner):
        result = runner.invoke(main, ["window", "close", "Notepad"])
        assert result.exit_code == 0
        assert "Closed window" in result.output

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_minimize_positional(self, mock_backend, runner):
        result = runner.invoke(main, ["window", "minimize", "Notepad"])
        assert result.exit_code == 0
        assert "Minimized window" in result.output

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_maximize_positional(self, mock_backend, runner):
        result = runner.invoke(main, ["window", "maximize", "Notepad"])
        assert result.exit_code == 0
        assert "Maximized window" in result.output

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_restore_positional(self, mock_backend, runner):
        result = runner.invoke(main, ["window", "restore", "Notepad"])
        assert result.exit_code == 0
        assert "Restored window" in result.output

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_focus_app_option_still_works(self, mock_backend, runner):
        """--app flag should still work."""
        result = runner.invoke(main, ["window", "focus", "--app", "Notepad"])
        assert result.exit_code == 0
        assert "Focused window" in result.output


# ── #278: Deprecation warnings ───────────────────────────────────────────


class TestWindowDeprecationWarning:
    """All window subcommands should emit deprecation warning to stderr."""

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_focus_deprecation(self, mock_backend, runner):
        result = runner.invoke(main, ["window", "focus", "--app", "X"])
        assert "deprecated" in result.stderr.lower()
        assert "naturo app" in result.stderr

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_close_deprecation(self, mock_backend, runner):
        result = runner.invoke(main, ["window", "close", "--app", "X"])
        assert "deprecated" in result.stderr.lower()

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_minimize_deprecation(self, mock_backend, runner):
        result = runner.invoke(main, ["window", "minimize", "--app", "X"])
        assert "deprecated" in result.stderr.lower()

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_list_deprecation(self, mock_backend, runner):
        mock_backend.return_value.list_windows.return_value = []
        result = runner.invoke(main, ["window", "list"])
        assert "deprecated" in result.stderr.lower()

    @mock.patch("naturo.cli.window_cmd._get_backend")
    def test_no_deprecation_in_json_mode(self, mock_backend, runner):
        """JSON mode should suppress stderr deprecation."""
        result = runner.invoke(main, ["window", "focus", "--app", "X", "--json"])
        # In JSON mode, no deprecation warning to stderr
        assert "deprecated" not in result.stderr.lower()


class TestHotkeyDeprecationWarning:
    """``naturo hotkey`` should emit deprecation warning."""

    @mock.patch("naturo.cli.interaction._get_backend")
    def test_hotkey_deprecation(self, mock_backend, runner):
        mock_be = mock.MagicMock()
        mock_be.press_key.return_value = None
        mock_backend.return_value = mock_be
        result = runner.invoke(main, ["hotkey", "ctrl+a"])
        assert "deprecated" in result.stderr.lower()
        assert "naturo press" in result.stderr
