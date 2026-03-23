"""Tests for electron and chrome CLI commands.

Verifies that the CLI groups are registered and their subcommands
are accessible. Actual Electron/CDP functionality is tested in
integration tests (requires Windows).
"""

import json
import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


class TestElectronGroup:
    """Tests for `naturo electron` command group."""

    def test_electron_group_exists(self, runner):
        """Electron group is registered and shows help."""
        result = runner.invoke(main, ["electron", "--help"])
        assert result.exit_code == 0
        assert "Electron" in result.output or "electron" in result.output

    def test_electron_detect_help(self, runner):
        """electron detect subcommand exists."""
        result = runner.invoke(main, ["electron", "detect", "--help"])
        assert result.exit_code == 0
        assert "APP_NAME" in result.output

    def test_electron_list_help(self, runner):
        """electron list subcommand exists."""
        result = runner.invoke(main, ["electron", "list", "--help"])
        assert result.exit_code == 0

    def test_electron_connect_help(self, runner):
        """electron connect subcommand exists."""
        result = runner.invoke(main, ["electron", "connect", "--help"])
        assert result.exit_code == 0
        assert "APP_NAME" in result.output

    def test_electron_launch_help(self, runner):
        """electron launch subcommand exists."""
        result = runner.invoke(main, ["electron", "launch", "--help"])
        assert result.exit_code == 0
        assert "APP_PATH" in result.output

    @pytest.mark.skipif(
        __import__("sys").platform != "win32",
        reason="Electron detection requires Windows",
    )
    def test_electron_list_json(self, runner):
        """electron list --json returns valid JSON."""
        result = runner.invoke(main, ["electron", "list", "--json"])
        # Should produce valid JSON regardless of whether apps are found
        data = json.loads(result.output)
        assert "apps" in data or "error" in data

    @pytest.mark.skipif(
        __import__("sys").platform != "win32",
        reason="Electron detection requires Windows",
    )
    def test_electron_detect_nonexistent_json(self, runner):
        """electron detect returns is_electron=False for nonexistent app."""
        result = runner.invoke(main, ["electron", "detect", "nonexistent_app_12345", "--json"])
        data = json.loads(result.output)
        assert data.get("is_electron") is False


class TestChromeGroup:
    """Tests for `naturo chrome` command group."""

    def test_chrome_group_exists(self, runner):
        """Chrome group is registered and shows help."""
        result = runner.invoke(main, ["chrome", "--help"])
        assert result.exit_code == 0
        assert "Chrome" in result.output or "chrome" in result.output or "CDP" in result.output

    def test_chrome_tabs_help(self, runner):
        """chrome tabs subcommand exists."""
        result = runner.invoke(main, ["chrome", "tabs", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output

    def test_chrome_tabs_connection_error_json(self, runner):
        """chrome tabs --json returns error when no browser is running."""
        # Port 19999 is unlikely to have a browser
        result = runner.invoke(main, ["chrome", "tabs", "--port", "19999", "--json"])
        if result.output.strip():
            data = json.loads(result.output)
            assert "error" in data


class TestHelpTextConsistency:
    """Verify that help text references match registered commands."""

    def test_main_help_shows_electron(self, runner):
        """Main help lists the electron command."""
        result = runner.invoke(main, ["--help"])
        assert "electron" in result.output

    def test_main_help_shows_chrome(self, runner):
        """Main help lists the chrome command."""
        result = runner.invoke(main, ["--help"])
        assert "chrome" in result.output
