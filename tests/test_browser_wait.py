"""Tests for browser wait mechanisms (#762).

Tests BrowserPage.wait_for_navigation, wait_for_url, wait_for_function,
wait_for_network_idle, and the corresponding CLI commands. All tests mock
the CDP layer — no Chrome required.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from naturo.browser._page import BrowserPage
from naturo.cdp import CDPError


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_page() -> BrowserPage:
    """Create a BrowserPage with a fully mocked CDP client."""
    with patch.object(BrowserPage, "__init__", lambda self, **kw: None):
        page = BrowserPage.__new__(BrowserPage)
    page._cdp = MagicMock()
    page._timeout = 2.0
    return page


# ═══════════════════════════════════════════════════════════════════════════════
# BrowserPage.wait_for_navigation
# ═══════════════════════════════════════════════════════════════════════════════


class TestWaitForNavigation:
    """Test wait_for_navigation: URL change + load complete."""

    def test_returns_new_url_after_navigation(self):
        page = _make_page()
        # Simulate: first call returns old URL, second returns new, readyState=complete
        url_values = ["https://old.example.com", "https://new.example.com"]
        with patch.object(type(page), "url", new_callable=PropertyMock,
                          side_effect=url_values):
            page._cdp.evaluate.return_value = "complete"
            result = page.wait_for_navigation(timeout=1.0)
        assert result == "https://new.example.com"

    def test_timeout_when_no_navigation(self):
        page = _make_page()
        with patch.object(type(page), "url", new_callable=PropertyMock,
                          return_value="https://same.example.com"):
            with pytest.raises(TimeoutError, match="Timeout waiting for navigation"):
                page.wait_for_navigation(timeout=0.3)

    def test_waits_for_load_complete(self):
        page = _make_page()
        # URL changes immediately but readyState is loading then complete
        urls = ["https://old.com", "https://new.com", "https://new.com"]
        states = ["loading", "complete"]
        with patch.object(type(page), "url", new_callable=PropertyMock,
                          side_effect=urls):
            page._cdp.evaluate.side_effect = states
            result = page.wait_for_navigation(timeout=2.0)
        assert result == "https://new.com"


# ═══════════════════════════════════════════════════════════════════════════════
# BrowserPage.wait_for_url
# ═══════════════════════════════════════════════════════════════════════════════


class TestWaitForUrl:
    """Test wait_for_url: substring and regex matching."""

    def test_substring_match(self):
        page = _make_page()
        with patch.object(type(page), "url", new_callable=PropertyMock,
                          return_value="https://example.com/dashboard"):
            result = page.wait_for_url("/dashboard", timeout=1.0)
        assert "dashboard" in result

    def test_regex_match(self):
        page = _make_page()
        with patch.object(type(page), "url", new_callable=PropertyMock,
                          return_value="https://example.com/order/12345"):
            result = page.wait_for_url(r"order/\d+", regex=True, timeout=1.0)
        assert "order/12345" in result

    def test_timeout_when_no_match(self):
        page = _make_page()
        with patch.object(type(page), "url", new_callable=PropertyMock,
                          return_value="https://example.com/login"):
            with pytest.raises(TimeoutError, match="Timeout waiting for URL"):
                page.wait_for_url("/dashboard", timeout=0.3)


# ═══════════════════════════════════════════════════════════════════════════════
# BrowserPage.wait_for_function
# ═══════════════════════════════════════════════════════════════════════════════


class TestWaitForFunction:
    """Test wait_for_function: JS expression polling."""

    def test_returns_truthy_result(self):
        page = _make_page()
        page._cdp.evaluate.return_value = True
        result = page.wait_for_function("window.ready", timeout=1.0)
        assert result is True

    def test_waits_for_truthy(self):
        page = _make_page()
        page._cdp.evaluate.side_effect = [None, False, 0, "loaded"]
        result = page.wait_for_function("getStatus()", timeout=2.0)
        assert result == "loaded"

    def test_timeout_when_never_truthy(self):
        page = _make_page()
        page._cdp.evaluate.return_value = False
        with pytest.raises(TimeoutError, match="Timeout waiting for expression"):
            page.wait_for_function("false", timeout=0.3)

    def test_cdp_error_retried(self):
        page = _make_page()
        page._cdp.evaluate.side_effect = [CDPError("transient"), 42]
        result = page.wait_for_function("compute()", timeout=2.0)
        assert result == 42


# ═══════════════════════════════════════════════════════════════════════════════
# BrowserPage.wait_for_network_idle
# ═══════════════════════════════════════════════════════════════════════════════


class TestWaitForNetworkIdle:
    """Test wait_for_network_idle: resource count stabilisation."""

    def test_returns_when_stable(self):
        page = _make_page()
        # Resource count stays at 5 for multiple polls
        page._cdp.evaluate.return_value = 5
        page.wait_for_network_idle(idle_time=0.2, timeout=2.0)
        # No exception means success

    def test_timeout_when_never_stable(self):
        page = _make_page()
        # Resource count keeps growing
        counter = iter(range(1000))
        page._cdp.evaluate.side_effect = lambda _: next(counter)
        with pytest.raises(TimeoutError, match="Timeout waiting for network idle"):
            page.wait_for_network_idle(idle_time=0.5, timeout=0.3)

    def test_cdp_error_treated_as_zero(self):
        page = _make_page()
        # CDPError followed by stable count
        page._cdp.evaluate.side_effect = [
            CDPError("fail"), CDPError("fail"), 5, 5, 5, 5, 5, 5,
        ]
        page.wait_for_network_idle(idle_time=0.2, timeout=2.0)
