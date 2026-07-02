"""Tests for naturo.browser._network — network monitoring and interception (#765)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner

from naturo.browser._network import NetworkMonitor
from naturo.cli.browser_cmd import browser


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def cdp():
    return MagicMock()


@pytest.fixture
def monitor(cdp):
    return NetworkMonitor(cdp)


# ---------------------------------------------------------------------------
# NetworkMonitor
# ---------------------------------------------------------------------------


class TestNetworkMonitor:
    """Test NetworkMonitor methods."""

    def test_capture_snapshot(self, monitor, cdp):
        """capture_snapshot returns list from performance API."""
        cdp.evaluate.return_value = [
            {"name": "https://example.com/api/data", "type": "fetch", "duration": 120, "size": 4096, "startTime": 100},
            {"name": "https://cdn.com/style.css", "type": "link", "duration": 50, "size": 8192, "startTime": 200},
        ]
        result = monitor.capture_snapshot()
        assert len(result) == 2
        assert result[0]["name"] == "https://example.com/api/data"

    def test_capture_snapshot_empty(self, monitor, cdp):
        """capture_snapshot returns empty list when no data."""
        cdp.evaluate.return_value = None
        assert monitor.capture_snapshot() == []

    def test_find_requests_with_pattern(self, monitor, cdp):
        """find_requests filters by glob pattern."""
        snapshot = [
            {"name": "https://example.com/api/users", "type": "fetch"},
            {"name": "https://cdn.com/style.css", "type": "link"},
            {"name": "https://example.com/api/posts", "type": "fetch"},
        ]
        result = monitor.find_requests("*/api/*", snapshot=snapshot)
        assert len(result) == 2
        assert all("api" in r["name"] for r in result)

    def test_find_requests_no_match(self, monitor, cdp):
        """find_requests returns empty when nothing matches."""
        snapshot = [{"name": "https://example.com/page.html", "type": "document"}]
        result = monitor.find_requests("*/api/*", snapshot=snapshot)
        assert result == []

    def test_find_requests_captures_if_no_snapshot(self, monitor, cdp):
        """find_requests calls capture_snapshot if none provided."""
        cdp.evaluate.return_value = [
            {"name": "https://example.com/api/x", "type": "fetch"},
        ]
        result = monitor.find_requests("*/api/*")
        assert len(result) == 1

    def test_abort_pattern(self, monitor, cdp):
        """abort_pattern injects JS abort rule."""
        cdp.send.return_value = {}
        cdp.evaluate.return_value = None
        monitor.abort_pattern("*/tracking/*")
        # Should call Page.addScriptToEvaluateOnNewDocument and evaluate
        assert cdp.send.call_count >= 2  # Network.enable + addScript
        assert cdp.evaluate.call_count >= 1

    def test_mock_response(self, monitor, cdp):
        """mock_response injects JS mock rule."""
        cdp.send.return_value = {}
        cdp.evaluate.return_value = None
        monitor.mock_response("*/config.json", body='{"debug": true}')
        assert cdp.send.call_count >= 2
        assert cdp.evaluate.call_count >= 1

    def test_intercept_continue(self, monitor, cdp):
        """intercept with action=continue enables network."""
        cdp.send.return_value = {}
        monitor.intercept("*/foo/*", action="continue")
        # Should enable Network domain
        cdp.send.assert_any_call("Network.enable")

    def test_glob_to_regex_star(self):
        """Single * matches non-slash chars."""
        regex = NetworkMonitor._glob_to_regex("*/api/*")
        assert regex == "[^/]*/api/[^/]*"

    def test_glob_to_regex_double_star(self):
        """Double ** matches any chars including slashes."""
        regex = NetworkMonitor._glob_to_regex("**/api/**")
        assert regex == ".*/api/.*"

    def test_glob_to_regex_escapes_dots(self):
        """Dots are escaped in regex."""
        regex = NetworkMonitor._glob_to_regex("*.example.com")
        assert regex == "[^/]*\\.example\\.com"

    def test_ensure_enabled_idempotent(self, monitor, cdp):
        """_ensure_enabled only sends Network.enable once."""
        cdp.send.return_value = {}
        monitor._ensure_enabled()
        monitor._ensure_enabled()
        assert cdp.send.call_count == 1


# ---------------------------------------------------------------------------
# BrowserPage.network property
# ---------------------------------------------------------------------------


class TestPageNetworkProperty:
    """Test BrowserPage.network lazy property."""

    def test_network_returns_monitor(self):
        """page.network returns a NetworkMonitor."""
        from naturo.browser._page import BrowserPage
        with patch.object(BrowserPage, "__init__", lambda self, **kw: None):
            page = BrowserPage.__new__(BrowserPage)
            page._cdp = MagicMock()
            net = page.network
            assert isinstance(net, NetworkMonitor)

    def test_network_is_cached(self):
        """page.network returns the same instance on repeat access."""
        from naturo.browser._page import BrowserPage
        with patch.object(BrowserPage, "__init__", lambda self, **kw: None):
            page = BrowserPage.__new__(BrowserPage)
            page._cdp = MagicMock()
            assert page.network is page.network


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


class TestRequestsCLI:
    """Test browser requests CLI command."""

    def test_requests_text(self, runner):
        """browser requests lists requests in text mode."""
        mock_page = MagicMock()
        mock_page.network.capture_snapshot.return_value = [
            {"name": "https://example.com/api/data", "type": "fetch", "size": 4096},
        ]
        mock_page.network.find_requests.return_value = [
            {"name": "https://example.com/api/data", "type": "fetch", "size": 4096},
        ]

        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page):
            result = runner.invoke(browser, ["requests"])
        assert result.exit_code == 0
        assert "1 request" in result.output

    def test_requests_json(self, runner):
        """browser requests --json outputs JSON."""
        mock_page = MagicMock()
        mock_page.network.capture_snapshot.return_value = []
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page):
            result = runner.invoke(browser, ["requests", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 0

    def test_requests_with_pattern(self, runner):
        """browser requests --pattern filters results."""
        mock_page = MagicMock()
        mock_page.network.capture_snapshot.return_value = [
            {"name": "https://example.com/api/x", "type": "fetch", "size": 100},
        ]
        mock_page.network.find_requests.return_value = [
            {"name": "https://example.com/api/x", "type": "fetch", "size": 100},
        ]
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page):
            result = runner.invoke(browser, ["requests", "--pattern", "*/api/*"])
        assert result.exit_code == 0


class TestInterceptCLI:
    """Test browser intercept CLI command."""

    def test_intercept_abort(self, runner):
        """browser intercept with abort action."""
        mock_page = MagicMock()
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page):
            result = runner.invoke(browser, ["intercept", "*/tracking/*", "--action", "abort"])
        assert result.exit_code == 0
        assert "abort" in result.output
        mock_page.network.abort_pattern.assert_called_once_with("*/tracking/*")

    def test_intercept_fulfill(self, runner):
        """browser intercept with fulfill action."""
        mock_page = MagicMock()
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page):
            result = runner.invoke(browser, [
                "intercept", "*/config.json",
                "--action", "fulfill",
                "--body", '{"debug": true}',
            ])
        assert result.exit_code == 0
        mock_page.network.mock_response.assert_called_once()

    def test_intercept_json(self, runner):
        """browser intercept --json outputs JSON."""
        mock_page = MagicMock()
        with patch("naturo.cli.browser_cmd._get_page", return_value=mock_page):
            result = runner.invoke(browser, [
                "intercept", "*/ads/*", "--action", "abort", "--json",
            ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["action"] == "abort"
