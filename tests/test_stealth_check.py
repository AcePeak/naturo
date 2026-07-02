"""Tests for #760: browser stealth-check verification command.

Tests check_stealth() function and the CLI stealth-check command.
All tests mock the CDP layer — no browser required.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.browser._stealth import check_stealth
from naturo.cli.browser_cmd import browser


@pytest.fixture
def mock_page():
    """Create a mock BrowserPage with a mock CDP connection."""
    page = MagicMock()
    page._cdp = MagicMock()
    return page


@pytest.fixture
def runner():
    return CliRunner()


# ── check_stealth() unit tests ──────────────────────────────────────────────


class TestCheckStealth:
    """Tests for the check_stealth() function."""

    def test_all_checks_pass(self, mock_page):
        """All checks return True when stealth patches are applied."""
        mock_page._cdp.evaluate.return_value = {
            "webdriver": True,
            "plugins": True,
            "languages": True,
            "chrome_runtime": True,
            "webgl_vendor": True,
            "permissions": True,
        }
        result = check_stealth(mock_page)
        assert all(result.values())
        assert len(result) == 6

    def test_some_checks_fail(self, mock_page):
        """Failed checks return False for their keys."""
        mock_page._cdp.evaluate.return_value = {
            "webdriver": False,
            "plugins": True,
            "languages": True,
            "chrome_runtime": False,
            "webgl_vendor": True,
            "permissions": True,
        }
        result = check_stealth(mock_page)
        assert result["webdriver"] is False
        assert result["chrome_runtime"] is False
        assert result["plugins"] is True

    def test_all_checks_fail(self, mock_page):
        """All checks fail when no stealth patches are applied."""
        mock_page._cdp.evaluate.return_value = {
            "webdriver": False,
            "plugins": False,
            "languages": False,
            "chrome_runtime": False,
            "webgl_vendor": False,
            "permissions": False,
        }
        result = check_stealth(mock_page)
        assert not any(result.values())

    def test_unexpected_return_type_raises(self, mock_page):
        """Non-dict return from JS raises RuntimeError."""
        mock_page._cdp.evaluate.return_value = "unexpected"
        with pytest.raises(RuntimeError, match="unexpected type"):
            check_stealth(mock_page)

    def test_none_return_raises(self, mock_page):
        """None return from JS raises RuntimeError."""
        mock_page._cdp.evaluate.return_value = None
        with pytest.raises(RuntimeError, match="unexpected type"):
            check_stealth(mock_page)


# ── CLI stealth-check command tests ──────────────────────────────────────────


ALL_PASS = {
    "webdriver": True,
    "plugins": True,
    "languages": True,
    "chrome_runtime": True,
    "webgl_vendor": True,
    "permissions": True,
}

SOME_FAIL = {
    "webdriver": False,
    "plugins": True,
    "languages": True,
    "chrome_runtime": False,
    "webgl_vendor": True,
    "permissions": True,
}


class TestStealthCheckCLI:
    """Tests for the stealth-check CLI command."""

    @patch("naturo.cli.browser_cmd._get_page")
    def test_all_pass_text(self, mock_get_page, runner):
        """Text output when all checks pass."""
        page = MagicMock()
        page._cdp.evaluate.return_value = ALL_PASS.copy()
        mock_get_page.return_value = page

        result = runner.invoke(browser, ["stealth-check"])
        assert result.exit_code == 0
        assert "PASS" in result.output
        assert "All 6 checks passed" in result.output

    @patch("naturo.cli.browser_cmd._get_page")
    def test_all_pass_json(self, mock_get_page, runner):
        """JSON output when all checks pass."""
        page = MagicMock()
        page._cdp.evaluate.return_value = ALL_PASS.copy()
        mock_get_page.return_value = page

        result = runner.invoke(browser, ["stealth-check", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert all(data["checks"].values())

    @patch("naturo.cli.browser_cmd._get_page")
    def test_some_fail_text(self, mock_get_page, runner):
        """Text output with failures — exit code 1."""
        page = MagicMock()
        page._cdp.evaluate.return_value = SOME_FAIL.copy()
        mock_get_page.return_value = page

        result = runner.invoke(browser, ["stealth-check"])
        assert result.exit_code == 1
        assert "FAIL" in result.output
        assert "webdriver" in result.output

    @patch("naturo.cli.browser_cmd._get_page")
    def test_some_fail_json(self, mock_get_page, runner):
        """JSON output with failures — exit code 1, success: false."""
        page = MagicMock()
        page._cdp.evaluate.return_value = SOME_FAIL.copy()
        mock_get_page.return_value = page

        result = runner.invoke(browser, ["stealth-check", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["checks"]["webdriver"] is False

    @patch("naturo.cli.browser_cmd._get_page")
    def test_connection_error_text(self, mock_get_page, runner):
        """Connection error produces text error and exit code 1."""
        mock_get_page.side_effect = ConnectionError("No browser")

        result = runner.invoke(browser, ["stealth-check"])
        assert result.exit_code == 1

    @patch("naturo.cli.browser_cmd._get_page")
    def test_connection_error_json(self, mock_get_page, runner):
        """Connection error produces JSON error and exit code 1."""
        mock_get_page.side_effect = ConnectionError("No browser")

        result = runner.invoke(browser, ["stealth-check", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "error" in data

    def test_help_output(self, runner):
        """stealth-check --help should mention detection vectors."""
        result = runner.invoke(browser, ["stealth-check", "--help"])
        assert result.exit_code == 0
        assert "stealth" in result.output.lower()
        assert "webdriver" in result.output.lower()
