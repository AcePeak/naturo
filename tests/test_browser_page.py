"""Tests for naturo.browser._page — BrowserPage CDP abstraction.

All tests mock the CDP layer so no Chrome instance is needed.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch, call

import pytest

from naturo.cdp import CDPConnectionError, CDPError


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_page(
    tabs=None,
    evaluate_return="",
    send_return=None,
):
    """Build a BrowserPage with a fully mocked CDPClient.

    Args:
        tabs: Value returned by list_tabs().
        evaluate_return: Default return for cdp.evaluate().
        send_return: Default return dict for cdp.send().
    """
    if tabs is None:
        tabs = [{"id": "tab-1", "title": "Example", "url": "https://example.com"}]

    mock_cdp = MagicMock()
    mock_cdp.list_tabs.return_value = tabs
    mock_cdp.evaluate.return_value = evaluate_return
    mock_cdp.send.return_value = send_return or {}

    with patch("naturo.browser._page.CDPClient", return_value=mock_cdp):
        from naturo.browser._page import BrowserPage
        page = BrowserPage(port=9222)

    return page, mock_cdp


# ═════════════════════════════════════════════════════════════════════════════
# Construction & connection
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageConnect:
    """Connection and tab selection tests."""

    def test_connects_to_first_tab_by_default(self):
        page, cdp = _make_page()
        cdp.connect.assert_called_once_with("tab-1")

    def test_connects_to_specified_tab_index(self):
        tabs = [
            {"id": "tab-a", "title": "First"},
            {"id": "tab-b", "title": "Second"},
        ]
        mock_cdp = MagicMock()
        mock_cdp.list_tabs.return_value = tabs
        mock_cdp.evaluate.return_value = ""
        mock_cdp.send.return_value = {}

        with patch("naturo.browser._page.CDPClient", return_value=mock_cdp):
            from naturo.browser._page import BrowserPage
            page = BrowserPage(port=9222, tab_index=1)

        mock_cdp.connect.assert_called_once_with("tab-b")

    def test_raises_on_no_tabs(self):
        mock_cdp = MagicMock()
        mock_cdp.list_tabs.return_value = []

        with patch("naturo.browser._page.CDPClient", return_value=mock_cdp):
            from naturo.browser._page import BrowserPage
            with pytest.raises(CDPConnectionError, match="No browser tabs"):
                BrowserPage(port=9222)

    def test_raises_on_tab_index_out_of_range(self):
        mock_cdp = MagicMock()
        mock_cdp.list_tabs.return_value = [{"id": "only-tab", "title": "X"}]

        with patch("naturo.browser._page.CDPClient", return_value=mock_cdp):
            from naturo.browser._page import BrowserPage
            with pytest.raises(CDPConnectionError, match="out of range"):
                BrowserPage(port=9222, tab_index=5)


# ═════════════════════════════════════════════════════════════════════════════
# Properties
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageProperties:
    """URL and title property tests."""

    def test_url_returns_evaluated_href(self):
        page, cdp = _make_page(evaluate_return="https://example.com/page")
        assert page.url == "https://example.com/page"
        cdp.evaluate.assert_called_with("window.location.href")

    def test_url_returns_empty_on_none(self):
        page, cdp = _make_page(evaluate_return=None)
        assert page.url == ""

    def test_title_returns_evaluated_title(self):
        page, cdp = _make_page(evaluate_return="Example Title")
        assert page.title == "Example Title"

    def test_title_returns_empty_on_none(self):
        page, cdp = _make_page(evaluate_return=None)
        _ = page.url  # consume first evaluate call
        cdp.evaluate.return_value = None
        assert page.title == ""


# ═════════════════════════════════════════════════════════════════════════════
# Navigation
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageNavigation:
    """Navigation method tests."""

    def test_navigate_sends_page_navigate(self):
        page, cdp = _make_page()
        cdp.evaluate.return_value = "complete"
        page.navigate("https://example.com")
        cdp.send.assert_any_call("Page.enable")
        cdp.send.assert_any_call("Page.navigate", {"url": "https://example.com"})

    def test_navigate_waits_for_load_by_default(self):
        page, cdp = _make_page()
        cdp.evaluate.return_value = "complete"
        page.navigate("https://example.com")
        # _wait_for_event polls document.readyState
        cdp.evaluate.assert_called_with("document.readyState")

    def test_navigate_domcontentloaded_checks_interactive(self):
        page, cdp = _make_page()
        cdp.evaluate.return_value = "interactive"
        page.navigate("https://example.com", wait_until="domcontentloaded")
        cdp.evaluate.assert_called_with("document.readyState")

    def test_navigate_networkidle(self):
        page, cdp = _make_page()
        cdp.evaluate.return_value = "complete"
        with patch("naturo.browser._page.time.sleep"):
            page.navigate("https://example.com", wait_until="networkidle")

    def test_reload_sends_page_reload(self):
        page, cdp = _make_page()
        cdp.evaluate.return_value = "complete"
        page.reload()
        cdp.send.assert_any_call("Page.enable")
        cdp.send.assert_any_call("Page.reload")

    def test_back_evaluates_history_back(self):
        page, cdp = _make_page()
        page.back()
        cdp.evaluate.assert_called_with("window.history.back()")

    def test_forward_evaluates_history_forward(self):
        page, cdp = _make_page()
        page.forward()
        cdp.evaluate.assert_called_with("window.history.forward()")


# ═════════════════════════════════════════════════════════════════════════════
# Element finding
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageFind:
    """Element finding tests."""

    def test_find_returns_element_for_valid_selector(self):
        page, cdp = _make_page()
        cdp.send.return_value = {
            "result": {"objectId": "obj-123", "description": "div#main"}
        }

        from naturo.browser._element import BrowserElement
        el = page.find("#main")
        assert isinstance(el, BrowserElement)
        assert el.object_id == "obj-123"

    def test_find_raises_on_no_match(self):
        page, cdp = _make_page()
        cdp.send.return_value = {"result": {"subtype": "null"}}

        with pytest.raises(RuntimeError, match="No element found"):
            page.find("#nonexistent")

    def test_find_all_returns_list(self):
        page, cdp = _make_page()
        # First call: Runtime.evaluate returns array objectId
        # Second call: Runtime.getProperties returns indexed props
        cdp.send.side_effect = [
            {"result": {"objectId": "arr-1"}},
            {
                "result": [
                    {
                        "name": "0",
                        "value": {"objectId": "el-0", "description": "li"},
                    },
                    {
                        "name": "1",
                        "value": {"objectId": "el-1", "description": "li"},
                    },
                    {
                        "name": "length",
                        "value": {"type": "number", "value": 2},
                    },
                ]
            },
        ]
        elements = page.find_all("li")
        assert len(elements) == 2
        assert elements[0].object_id == "el-0"
        assert elements[1].object_id == "el-1"

    def test_find_all_returns_empty_on_no_oid(self):
        page, cdp = _make_page()
        cdp.send.return_value = {"result": {}}
        assert page.find_all(".missing") == []

    def test_find_with_xpath_selector(self):
        page, cdp = _make_page()
        cdp.send.return_value = {
            "result": {"objectId": "obj-x", "description": "span"}
        }
        el = page.find("xpath://span[@class='name']")
        assert el.object_id == "obj-x"

    def test_find_with_text_selector(self):
        page, cdp = _make_page()
        cdp.send.return_value = {
            "result": {"objectId": "obj-t", "description": "button"}
        }
        el = page.find("text:Login")
        assert el.object_id == "obj-t"


# ═════════════════════════════════════════════════════════════════════════════
# wait_for
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageWaitFor:
    """Wait-for-element tests."""

    def test_wait_for_attached_returns_immediately_if_found(self):
        page, cdp = _make_page()
        cdp.send.return_value = {
            "result": {"objectId": "obj-w", "description": "div"}
        }
        el = page.wait_for("#target", timeout=1.0, state="attached")
        assert el.object_id == "obj-w"

    def test_wait_for_detached_returns_when_not_found(self):
        page, cdp = _make_page()
        cdp.send.return_value = {"result": {"subtype": "null"}}
        el = page.wait_for("#gone", timeout=1.0, state="detached")
        assert el._description == "<detached>"

    def test_wait_for_hidden_returns_when_not_found(self):
        page, cdp = _make_page()
        cdp.send.return_value = {"result": {"subtype": "null"}}
        el = page.wait_for("#hidden", timeout=1.0, state="hidden")
        assert el._description == "<hidden>"

    def test_wait_for_timeout_raises(self):
        page, cdp = _make_page()
        cdp.send.return_value = {"result": {"subtype": "null"}}

        with patch("naturo.browser._page.time.sleep"):
            with patch("naturo.browser._page.time.monotonic") as mock_time:
                # First call sets deadline, subsequent calls exceed it
                mock_time.side_effect = [0.0, 0.0, 2.0]
                with pytest.raises(TimeoutError, match="Timeout waiting"):
                    page.wait_for("#never", timeout=1.0)

    def test_wait_for_visible_checks_displayed(self):
        page, cdp = _make_page()
        # _resolve_element returns element
        cdp.send.return_value = {
            "result": {"objectId": "obj-v", "description": "div"}
        }
        # Visibility is decided by _is_displayed (the element's rendered box),
        # not _get_click_point — a display:none node yields a valid (0,0) point
        # there and would wrongly satisfy "visible" (#1083).
        with patch(
            "naturo.browser._element.BrowserElement._is_displayed",
            return_value=True,
        ):
            el = page.wait_for("#visible", timeout=1.0, state="visible")
            assert el.object_id == "obj-v"

    def test_wait_for_hidden_returns_when_present_but_not_displayed(self):
        page, cdp = _make_page()
        # _resolve_element finds the element, but it is not rendered.
        cdp.send.return_value = {
            "result": {"objectId": "obj-h", "description": "div"}
        }
        with patch(
            "naturo.browser._element.BrowserElement._is_displayed",
            return_value=False,
        ):
            el = page.wait_for("#spinner", timeout=1.0, state="hidden")
            assert el.object_id == "obj-h"


# ═════════════════════════════════════════════════════════════════════════════
# wait_for_load
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageWaitForLoad:
    """Page load waiting tests."""

    def test_wait_for_load_enables_page_and_waits(self):
        page, cdp = _make_page()
        cdp.evaluate.return_value = "complete"
        page.wait_for_load(timeout=5.0)
        cdp.send.assert_any_call("Page.enable")


# ═════════════════════════════════════════════════════════════════════════════
# Screenshot
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageScreenshot:
    """Screenshot capture tests."""

    def test_screenshot_saves_file(self, tmp_path):
        import base64
        fake_png = base64.b64encode(b"fakepng").decode()
        page, cdp = _make_page()
        cdp.send.return_value = {"data": fake_png}

        path = str(tmp_path / "shot.png")
        result = page.screenshot(path)

        assert result == path
        with open(path, "rb") as f:
            assert f.read() == b"fakepng"

    def test_screenshot_full_page_uses_clip(self, tmp_path):
        import base64
        fake_png = base64.b64encode(b"full").decode()
        page, cdp = _make_page()
        cdp.send.side_effect = [
            {"contentSize": {"width": 1920, "height": 5000}},  # getLayoutMetrics
            {"data": fake_png},  # captureScreenshot
        ]

        path = str(tmp_path / "full.png")
        page.screenshot(path, full_page=True)

        # First call is getLayoutMetrics
        cdp.send.assert_any_call("Page.getLayoutMetrics")


# ═════════════════════════════════════════════════════════════════════════════
# Evaluate
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageEvaluate:
    """JavaScript evaluation tests."""

    def test_evaluate_delegates_to_cdp(self):
        page, cdp = _make_page(evaluate_return=42)
        result = page.evaluate("1 + 1")
        cdp.evaluate.assert_called_with("1 + 1")

    def test_evaluate_returns_string(self):
        page, cdp = _make_page(evaluate_return="hello")
        assert page.evaluate("'hello'") == "hello"


# ═════════════════════════════════════════════════════════════════════════════
# Tab management
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageTabs:
    """Tab management tests."""

    def test_tabs_returns_list(self):
        tabs = [
            {"id": "t1", "title": "Tab 1", "url": "https://a.com"},
            {"id": "t2", "title": "Tab 2", "url": "https://b.com"},
        ]
        page, cdp = _make_page(tabs=tabs)
        cdp.list_tabs.return_value = tabs
        result = page.tabs()
        assert len(result) == 2
        assert result[0]["id"] == "t1"

    def test_switch_tab_reconnects(self):
        page, cdp = _make_page()
        page.switch_tab("tab-new")
        cdp.close.assert_called_once()
        cdp.connect.assert_called_with("tab-new")


# ═════════════════════════════════════════════════════════════════════════════
# Scrolling
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageScroll:
    """Page scroll tests."""

    def test_scroll_to_bottom(self):
        page, cdp = _make_page()
        page.scroll_to_bottom()
        cdp.evaluate.assert_called_with(
            "window.scrollTo(0, document.body.scrollHeight)"
        )

    def test_scroll_to_top(self):
        page, cdp = _make_page()
        page.scroll_to_top()
        cdp.evaluate.assert_called_with("window.scrollTo(0, 0)")

    def test_scroll_by_positive(self):
        page, cdp = _make_page()
        page.scroll_by(300)
        cdp.evaluate.assert_called_with("window.scrollBy(0, 300)")

    def test_scroll_by_negative(self):
        page, cdp = _make_page()
        page.scroll_by(-200)
        cdp.evaluate.assert_called_with("window.scrollBy(0, -200)")

    def test_scroll_to_element(self):
        page, cdp = _make_page()
        cdp.send.return_value = {
            "result": {"objectId": "obj-s", "description": "div"}
        }
        with patch(
            "naturo.browser._element.BrowserElement.scroll_into_view"
        ) as mock_scroll:
            mock_scroll.return_value = MagicMock()
            page.scroll_to_element("#footer")


# ═════════════════════════════════════════════════════════════════════════════
# Lifecycle
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserPageLifecycle:
    """Close and context manager tests."""

    def test_close_closes_cdp(self):
        page, cdp = _make_page()
        page.close()
        cdp.close.assert_called_once()

    def test_context_manager(self):
        page, cdp = _make_page()
        with page as p:
            assert p is page
        cdp.close.assert_called_once()

    def test_repr(self):
        page, cdp = _make_page()
        cdp.port = 9222
        assert "BrowserPage" in repr(page)


# ═════════════════════════════════════════════════════════════════════════════
# Internal: _wait_for_event
# ═════════════════════════════════════════════════════════════════════════════


class TestWaitForEvent:
    """Internal event waiting tests."""

    def test_wait_for_load_event_polls_readystate(self):
        page, cdp = _make_page()
        cdp.evaluate.return_value = "complete"
        page._wait_for_event("Page.loadEventFired", timeout=2.0)
        cdp.evaluate.assert_called_with("document.readyState")

    def test_wait_for_domcontent_accepts_interactive(self):
        page, cdp = _make_page()
        cdp.evaluate.return_value = "interactive"
        page._wait_for_event("Page.domContentEventFired", timeout=2.0)

    def test_wait_for_generic_event_sleeps(self):
        page, cdp = _make_page()
        with patch("naturo.browser._page.time.sleep") as mock_sleep:
            page._wait_for_event("Custom.event", timeout=2.0)
            mock_sleep.assert_called_once_with(1.0)

    def test_wait_for_load_handles_cdp_error(self):
        page, cdp = _make_page()
        # First evaluate raises CDPError, second returns complete
        cdp.evaluate.side_effect = [CDPError("oops"), "complete"]
        with patch("naturo.browser._page.time.sleep"):
            page._wait_for_event("Page.loadEventFired", timeout=5.0)


# ═════════════════════════════════════════════════════════════════════════════
# Internal: _wait_for_network_idle
# ═════════════════════════════════════════════════════════════════════════════


class TestWaitForNetworkIdle:
    """Network idle waiting tests."""

    def test_network_idle_waits_after_load(self):
        page, cdp = _make_page()
        cdp.evaluate.return_value = "complete"
        with patch("naturo.browser._page.time.sleep") as mock_sleep:
            page._wait_for_network_idle(idle_time=0.5, timeout=5.0)
            mock_sleep.assert_called_with(0.5)
