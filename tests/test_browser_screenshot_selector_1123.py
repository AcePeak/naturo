"""Regression tests for #1123: ``browser screenshot --selector`` must crop.

``naturo browser screenshot`` advertises ``--selector <css>`` ("Capture only
this element"), but the option was parsed and then silently dropped — the
command captured the whole page regardless, a never-lie / confidently-wrong
defect (the user gets a full-page PNG while believing they cropped to an
element). These tests pin that the selector path now resolves the element's
bounding box and passes it as the ``clip`` to ``Page.captureScreenshot`` (the
non-default option path, per the dev-cycle 'option coverage' rule), and that a
missing / unrenderable element fails loudly instead of capturing the full page.
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import click.testing
import pytest

from naturo.cli._browser._group import browser


def _make_page(send_return=None):
    """Build a BrowserPage with a fully mocked CDPClient."""
    tabs = [{"id": "tab-1", "title": "Example", "url": "https://example.com"}]
    mock_cdp = MagicMock()
    mock_cdp.list_tabs.return_value = tabs
    mock_cdp.evaluate.return_value = ""
    mock_cdp.send.return_value = send_return or {}

    with patch("naturo.browser._page.CDPClient", return_value=mock_cdp):
        from naturo.browser._page import BrowserPage
        page = BrowserPage(port=9222)

    return page, mock_cdp


# ── BrowserPage.screenshot(selector=...) ──────────────────────────────────────


class TestScreenshotSelectorSDK:
    """SDK-level behaviour of the new ``selector`` capture path."""

    def test_selector_passes_element_clip(self, tmp_path):
        """The element's bounding box becomes the captureScreenshot clip."""
        png = base64.b64encode(b"cropped").decode()
        page, cdp = _make_page(send_return={"data": png})

        box = {"x": 8.0, "y": 88.0, "width": 748.0, "height": 24.0}
        element = MagicMock()
        element._bounding_box.return_value = box
        page.find = MagicMock(return_value=element)

        out = str(tmp_path / "intro.png")
        result = page.screenshot(out, selector="#intro")

        assert result == out
        page.find.assert_called_once_with("#intro")
        # The Page domain is enabled before the capture (headless first-frame
        # guard, #1124), then exactly one capture carries the element clip.
        cdp.send.assert_any_call("Page.enable")
        cdp.send.assert_any_call(
            "Page.captureScreenshot",
            {
                "format": "png",
                "clip": {
                    "x": 8.0,
                    "y": 88.0,
                    "width": 748.0,
                    "height": 24.0,
                    "scale": 1,
                },
                "captureBeyondViewport": True,
            },
        )
        capture_calls = [
            call
            for call in cdp.send.call_args_list
            if call.args[0] == "Page.captureScreenshot"
        ]
        assert len(capture_calls) == 1
        with open(out, "rb") as fh:
            assert fh.read() == b"cropped"

    def test_selector_not_found_raises_and_does_not_capture(self, tmp_path):
        """A missing element fails loudly — never a silent full-page capture."""
        page, cdp = _make_page()
        page.find = MagicMock(
            side_effect=RuntimeError("No element found for selector: #ghost")
        )

        with pytest.raises(RuntimeError, match="No element found"):
            page.screenshot(str(tmp_path / "x.png"), selector="#ghost")

        # The whole point of #1123: do NOT fall through to a full-page capture.
        for call in cdp.send.call_args_list:
            assert call.args[0] != "Page.captureScreenshot"

    def test_selector_without_layout_box_raises(self, tmp_path):
        """An element with no rendered box fails loudly rather than mis-cropping."""
        page, cdp = _make_page()
        element = MagicMock()
        element._bounding_box.return_value = None
        page.find = MagicMock(return_value=element)

        with pytest.raises(RuntimeError, match="no .*rendered layout box"):
            page.screenshot(str(tmp_path / "x.png"), selector="#hidden")

        for call in cdp.send.call_args_list:
            assert call.args[0] != "Page.captureScreenshot"

    def test_selector_and_full_page_conflict(self, tmp_path):
        """``selector`` and ``full_page`` are mutually exclusive."""
        page, _ = _make_page()
        page.find = MagicMock()

        with pytest.raises(ValueError, match="mutually exclusive"):
            page.screenshot(
                str(tmp_path / "x.png"), selector="#intro", full_page=True
            )

    def test_no_selector_is_plain_viewport_capture(self, tmp_path):
        """Without a selector the command stays a plain viewport capture."""
        png = base64.b64encode(b"viewport").decode()
        page, cdp = _make_page(send_return={"data": png})

        page.screenshot(str(tmp_path / "v.png"))

        # The Page domain is enabled before the capture (headless first-frame
        # guard, #1124); the capture itself stays a single plain viewport grab.
        cdp.send.assert_any_call("Page.enable")
        cdp.send.assert_any_call("Page.captureScreenshot", {"format": "png"})
        capture_calls = [
            call
            for call in cdp.send.call_args_list
            if call.args[0] == "Page.captureScreenshot"
        ]
        assert len(capture_calls) == 1


# ── BrowserElement._bounding_box ──────────────────────────────────────────────


class TestElementBoundingBox:
    """The bounding-box resolver used to build the clip."""

    def _element(self, quad=None, rect=None):
        from naturo.browser._element import BrowserElement

        page = MagicMock()
        element = BrowserElement(page, "obj-1", description="el")
        element.scroll_into_view = MagicMock()
        if quad is not None:
            page._cdp.send.return_value = {"quads": [quad]}
        else:
            page._cdp.send.return_value = {"quads": []}
            element._call_function = MagicMock(return_value=rect)
        return element

    def test_uses_content_quad(self):
        # quad order: top-left, top-right, bottom-right, bottom-left
        quad = [10.0, 20.0, 110.0, 20.0, 110.0, 70.0, 10.0, 70.0]
        element = self._element(quad=quad)

        box = element._bounding_box()

        assert box == {"x": 10.0, "y": 20.0, "width": 100.0, "height": 50.0}
        element.scroll_into_view.assert_called_once()

    def test_falls_back_to_bounding_client_rect(self):
        rect = {"x": 5.0, "y": 6.0, "width": 30.0, "height": 40.0}
        element = self._element(quad=None, rect=rect)

        assert element._bounding_box() == rect

    def test_zero_area_box_returns_none(self):
        rect = {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}
        element = self._element(quad=None, rect=rect)

        assert element._bounding_box() is None


# ── CLI wiring ────────────────────────────────────────────────────────────────


class TestScreenshotSelectorCLI:
    """The ``--selector`` flag must reach ``BrowserPage.screenshot``."""

    def _invoke(self, args, mock_page):
        runner = click.testing.CliRunner()
        with patch(
            "naturo.cli.browser_cmd._get_page", return_value=mock_page
        ):
            return runner.invoke(browser, args, catch_exceptions=False)

    def test_selector_forwarded(self):
        mock_page = MagicMock()
        mock_page.screenshot.return_value = "intro.png"

        result = self._invoke(
            ["screenshot", "--selector", "#intro", "--path", "intro.png"],
            mock_page,
        )

        assert result.exit_code == 0
        mock_page.screenshot.assert_called_once_with(
            "intro.png", full_page=False, selector="#intro"
        )

    def test_selector_and_full_page_rejected(self):
        mock_page = MagicMock()
        mock_page.screenshot.side_effect = ValueError(
            "screenshot: 'selector' and 'full_page' are mutually exclusive"
        )

        result = self._invoke(
            ["screenshot", "--selector", "#x", "--full-page", "--json"],
            mock_page,
        )

        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output
