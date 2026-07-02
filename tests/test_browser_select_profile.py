"""Tests for browser select command and BrowserPage profile integration."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.browser_cmd import browser


@pytest.fixture()
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# BrowserElement.select
# ---------------------------------------------------------------------------


class TestBrowserElementSelect:
    """Tests for the select() method on BrowserElement."""

    def test_select_by_value(self):
        from naturo.browser._element import BrowserElement

        page = MagicMock()
        el = BrowserElement(page, "obj123")

        # Mock _call_function to return the selected value
        el._call_function = MagicMock(return_value="US")
        result = el.select("US")
        assert result is el  # chainable
        el._call_function.assert_called_once()
        call_js = el._call_function.call_args[0][0]
        assert "'US'" in call_js

    def test_select_not_found_raises(self):
        from naturo.browser._element import BrowserElement

        page = MagicMock()
        el = BrowserElement(page, "obj123")
        el._call_function = MagicMock(return_value="NOT_FOUND")

        with pytest.raises(RuntimeError, match="No <option>"):
            el.select("nonexistent")

    def test_select_escapes_quotes(self):
        from naturo.browser._element import BrowserElement

        page = MagicMock()
        el = BrowserElement(page, "obj123")
        el._call_function = MagicMock(return_value="it's")

        el.select("it's")
        call_js = el._call_function.call_args[0][0]
        assert "it\\'s" in call_js


# ---------------------------------------------------------------------------
# CLI: browser select
# ---------------------------------------------------------------------------


class TestSelectCli:
    """Tests for 'naturo browser select' command."""

    @patch("naturo.cli.browser_cmd._get_page")
    def test_select_basic(self, mock_get_page, runner):
        mock_page = MagicMock()
        mock_el = MagicMock()
        mock_page.find.return_value = mock_el
        mock_get_page.return_value = mock_page

        result = runner.invoke(browser, ["select", "#country", "US"])
        assert result.exit_code == 0
        assert "Selected" in result.output
        mock_el.select.assert_called_once_with("US")

    @patch("naturo.cli.browser_cmd._get_page")
    def test_select_json(self, mock_get_page, runner):
        mock_page = MagicMock()
        mock_el = MagicMock()
        mock_page.find.return_value = mock_el
        mock_get_page.return_value = mock_page

        result = runner.invoke(browser, ["select", "#lang", "en", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "ok"
        assert data["value"] == "en"

    @patch("naturo.cli.browser_cmd._get_page")
    def test_select_not_found(self, mock_get_page, runner):
        mock_page = MagicMock()
        mock_page.find.side_effect = RuntimeError("No element found")
        mock_get_page.return_value = mock_page

        result = runner.invoke(browser, ["select", "#missing", "val"])
        assert result.exit_code != 0

    def test_select_help(self, runner):
        result = runner.invoke(browser, ["select", "--help"])
        assert result.exit_code == 0
        assert "--by" in result.output
        assert "VALUE" in result.output


# ---------------------------------------------------------------------------
# BrowserPage profile integration
# ---------------------------------------------------------------------------


class TestBrowserPageProfile:
    """Tests for BrowserPage auto-launch via profile parameter."""

    @patch("naturo.browser._page.CDPClient")
    @patch("naturo.browser._launcher.launch_chrome")
    def test_profile_launches_chrome(self, mock_launch, mock_cdp_cls):
        from naturo.browser._page import BrowserPage

        mock_proc = MagicMock()
        mock_proc.port = 19200
        mock_launch.return_value = mock_proc

        mock_cdp = MagicMock()
        mock_cdp.list_tabs.return_value = [{"id": "tab1", "title": "New Tab"}]
        mock_cdp_cls.return_value = mock_cdp

        page = BrowserPage(profile="test-profile")

        mock_launch.assert_called_once()
        call_kwargs = mock_launch.call_args[1]
        assert call_kwargs["profile"] == "test-profile"
        assert page._chrome_process is mock_proc
        # CDPClient should connect to the launched port
        mock_cdp_cls.assert_called_once_with(
            host="localhost", port=19200, timeout=30.0
        )

    @patch("naturo.browser._page.CDPClient")
    @patch("naturo.browser._launcher.launch_chrome")
    def test_profile_with_stealth(self, mock_launch, mock_cdp_cls):
        from naturo.browser._page import BrowserPage

        mock_proc = MagicMock()
        mock_proc.port = 9222
        mock_launch.return_value = mock_proc

        mock_cdp = MagicMock()
        mock_cdp.list_tabs.return_value = [{"id": "t1", "title": ""}]
        mock_cdp_cls.return_value = mock_cdp

        BrowserPage(profile="stealth-test", stealth=True)

        call_kwargs = mock_launch.call_args[1]
        assert call_kwargs["extra_args"] is not None
        assert len(call_kwargs["extra_args"]) > 0

    @patch("naturo.browser._page.CDPClient")
    @patch("naturo.browser._launcher.launch_chrome")
    def test_close_terminates_chrome(self, mock_launch, mock_cdp_cls):
        from naturo.browser._page import BrowserPage

        mock_proc = MagicMock()
        mock_proc.port = 9222
        mock_launch.return_value = mock_proc

        mock_cdp = MagicMock()
        mock_cdp.list_tabs.return_value = [{"id": "t1", "title": ""}]
        mock_cdp_cls.return_value = mock_cdp

        page = BrowserPage(profile="temp")
        page.close()

        mock_proc.terminate.assert_called_once()
        assert page._chrome_process is None

    @patch("naturo.browser._page.CDPClient")
    def test_no_profile_no_launch(self, mock_cdp_cls):
        from naturo.browser._page import BrowserPage

        mock_cdp = MagicMock()
        mock_cdp.list_tabs.return_value = [{"id": "t1", "title": ""}]
        mock_cdp_cls.return_value = mock_cdp

        page = BrowserPage(port=9222)
        assert page._chrome_process is None
