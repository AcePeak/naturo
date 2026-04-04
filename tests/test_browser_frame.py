"""Tests for naturo.browser._frame — iframe support via CDP execution contexts."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from click.testing import CliRunner

from naturo.browser._frame import (
    BrowserFrame,
    _flatten_frame_tree,
    _get_frame_tree,
)
from naturo.cdp import CDPError
from naturo.cli.browser_cmd import browser


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_page():
    """Create a mock BrowserPage with CDP client."""
    page = MagicMock()
    page._cdp = MagicMock()
    return page


@pytest.fixture
def sample_frame_tree():
    """A realistic frame tree with nested iframes."""
    return {
        "frame": {
            "id": "main-frame-id",
            "name": "",
            "url": "https://example.com",
            "parentId": "",
            "securityOrigin": "https://example.com",
        },
        "childFrames": [
            {
                "frame": {
                    "id": "iframe-1",
                    "name": "payment",
                    "url": "https://payment.example.com/form",
                    "parentId": "main-frame-id",
                    "securityOrigin": "https://payment.example.com",
                },
                "childFrames": [
                    {
                        "frame": {
                            "id": "iframe-1-1",
                            "name": "captcha",
                            "url": "https://captcha.example.com/verify",
                            "parentId": "iframe-1",
                            "securityOrigin": "https://captcha.example.com",
                        },
                        "childFrames": [],
                    }
                ],
            },
            {
                "frame": {
                    "id": "iframe-2",
                    "name": "ads",
                    "url": "https://ads.example.com/banner",
                    "parentId": "main-frame-id",
                    "securityOrigin": "https://ads.example.com",
                },
                "childFrames": [],
            },
        ],
    }


# ---------------------------------------------------------------------------
# _flatten_frame_tree
# ---------------------------------------------------------------------------


class TestFlattenFrameTree:
    """Tests for frame tree flattening."""

    def test_single_frame(self):
        tree = {
            "frame": {"id": "main", "name": "", "url": "https://example.com",
                       "parentId": "", "securityOrigin": ""},
            "childFrames": [],
        }
        frames = _flatten_frame_tree(tree)
        assert len(frames) == 1
        assert frames[0]["id"] == "main"
        assert frames[0]["depth"] == 0

    def test_nested_frames(self, sample_frame_tree):
        frames = _flatten_frame_tree(sample_frame_tree)
        assert len(frames) == 4  # main + 2 children + 1 grandchild

        # Check depth ordering
        depths = [f["depth"] for f in frames]
        assert depths == [0, 1, 2, 1]

    def test_frame_ids_preserved(self, sample_frame_tree):
        frames = _flatten_frame_tree(sample_frame_tree)
        ids = {f["id"] for f in frames}
        assert ids == {"main-frame-id", "iframe-1", "iframe-1-1", "iframe-2"}

    def test_parent_ids_preserved(self, sample_frame_tree):
        frames = _flatten_frame_tree(sample_frame_tree)
        frame_map = {f["id"]: f for f in frames}
        assert frame_map["iframe-1"]["parentId"] == "main-frame-id"
        assert frame_map["iframe-1-1"]["parentId"] == "iframe-1"
        assert frame_map["iframe-2"]["parentId"] == "main-frame-id"

    def test_names_preserved(self, sample_frame_tree):
        frames = _flatten_frame_tree(sample_frame_tree)
        frame_map = {f["id"]: f for f in frames}
        assert frame_map["iframe-1"]["name"] == "payment"
        assert frame_map["iframe-2"]["name"] == "ads"


# ---------------------------------------------------------------------------
# _get_frame_tree
# ---------------------------------------------------------------------------


class TestGetFrameTree:
    """Tests for retrieving frame tree from CDP."""

    def test_returns_frame_tree(self, mock_page, sample_frame_tree):
        mock_page._cdp.send.return_value = {"frameTree": sample_frame_tree}
        result = _get_frame_tree(mock_page)
        assert result == sample_frame_tree
        mock_page._cdp.send.assert_called_once_with("Page.getFrameTree")

    def test_returns_empty_on_missing_tree(self, mock_page):
        mock_page._cdp.send.return_value = {}
        result = _get_frame_tree(mock_page)
        assert result == {}


# ---------------------------------------------------------------------------
# BrowserFrame
# ---------------------------------------------------------------------------


class TestBrowserFrame:
    """Tests for BrowserFrame execution context and operations."""

    def test_attributes(self, mock_page):
        frame = BrowserFrame(mock_page, "frame-id", frame_name="test", frame_url="https://example.com")
        assert frame.frame_id == "frame-id"
        assert frame.name == "test"
        assert frame.url == "https://example.com"

    def test_repr(self, mock_page):
        frame = BrowserFrame(mock_page, "frame-id", frame_name="test", frame_url="https://example.com")
        r = repr(frame)
        assert "test" in r
        assert "example.com" in r

    def test_repr_without_name(self, mock_page):
        frame = BrowserFrame(mock_page, "abcdef123456789", frame_name="", frame_url="")
        r = repr(frame)
        assert "abcdef123456" in r

    def test_ensure_context_creates_isolated_world(self, mock_page):
        mock_page._cdp.send.return_value = {"executionContextId": 42}
        frame = BrowserFrame(mock_page, "frame-id")
        ctx_id = frame._ensure_context()
        assert ctx_id == 42
        mock_page._cdp.send.assert_called_with("Page.createIsolatedWorld", {
            "frameId": "frame-id",
            "worldName": "__naturo_frame_ctx__",
            "grantUniveralAccess": True,
        })

    def test_ensure_context_caches_id(self, mock_page):
        mock_page._cdp.send.return_value = {"executionContextId": 42}
        frame = BrowserFrame(mock_page, "frame-id")
        frame._ensure_context()
        frame._ensure_context()
        # Should only call createIsolatedWorld once
        assert mock_page._cdp.send.call_count == 1

    def test_ensure_context_raises_on_failure(self, mock_page):
        mock_page._cdp.send.return_value = {}
        frame = BrowserFrame(mock_page, "frame-id")
        with pytest.raises(CDPError, match="Failed to create execution context"):
            frame._ensure_context()

    def test_evaluate_uses_context_id(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},  # createIsolatedWorld
            {"result": {"value": "hello"}},  # Runtime.evaluate
        ]
        frame = BrowserFrame(mock_page, "frame-id")
        result = frame.evaluate("document.title")
        assert result == "hello"

        eval_call = mock_page._cdp.send.call_args_list[1]
        assert eval_call[0][0] == "Runtime.evaluate"
        assert eval_call[0][1]["contextId"] == 42

    def test_evaluate_raises_on_js_error(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},
            {
                "result": {"type": "object"},
                "exceptionDetails": {
                    "text": "ReferenceError",
                    "exception": {"description": "x is not defined"},
                },
            },
        ]
        frame = BrowserFrame(mock_page, "frame-id")
        with pytest.raises(CDPError, match="JavaScript error in frame"):
            frame.evaluate("x")

    def test_find_returns_element(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},
            {"result": {"objectId": "obj-1", "description": "input#name"}},
        ]
        frame = BrowserFrame(mock_page, "frame-id")
        el = frame.find("#name")
        assert el is not None
        assert el.object_id == "obj-1"

    def test_find_raises_on_not_found(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},
            {"result": {"subtype": "null"}},
        ]
        frame = BrowserFrame(mock_page, "frame-id")
        with pytest.raises(RuntimeError, match="Element not found in frame"):
            frame.find("#missing")

    def test_find_all_returns_elements(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},
            {"result": {"objectId": "arr-1"}},
            {"result": [
                {"name": "0", "value": {"objectId": "el-0", "description": "li"}},
                {"name": "1", "value": {"objectId": "el-1", "description": "li"}},
                {"name": "length", "value": {"value": 2}},
            ]},
        ]
        frame = BrowserFrame(mock_page, "frame-id")
        elements = frame.find_all("li")
        assert len(elements) == 2

    def test_find_all_returns_empty(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},
            {"result": {}},
        ]
        frame = BrowserFrame(mock_page, "frame-id")
        elements = frame.find_all("li")
        assert elements == []

    def test_title_property(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},
            {"result": {"value": "Payment Form"}},
        ]
        frame = BrowserFrame(mock_page, "frame-id")
        assert frame.title == "Payment Form"


# ---------------------------------------------------------------------------
# BrowserFrame.frame (nested)
# ---------------------------------------------------------------------------


class TestBrowserFrameNested:
    """Tests for nested iframe access."""

    def test_nested_frame_by_name(self, mock_page, sample_frame_tree):
        mock_page._cdp.send.return_value = {"frameTree": sample_frame_tree}
        outer = BrowserFrame(mock_page, "iframe-1", frame_name="payment")
        inner = outer.frame(name="captcha")
        assert inner.frame_id == "iframe-1-1"
        assert inner.name == "captcha"

    def test_nested_frame_by_url(self, mock_page, sample_frame_tree):
        mock_page._cdp.send.return_value = {"frameTree": sample_frame_tree}
        outer = BrowserFrame(mock_page, "iframe-1", frame_name="payment")
        inner = outer.frame(url="captcha.example.com")
        assert inner.frame_id == "iframe-1-1"

    def test_nested_frame_not_found_by_name(self, mock_page, sample_frame_tree):
        mock_page._cdp.send.return_value = {"frameTree": sample_frame_tree}
        outer = BrowserFrame(mock_page, "iframe-1", frame_name="payment")
        with pytest.raises(RuntimeError, match="No child frame with name"):
            outer.frame(name="nonexistent")

    def test_nested_frame_not_found_by_url(self, mock_page, sample_frame_tree):
        mock_page._cdp.send.return_value = {"frameTree": sample_frame_tree}
        outer = BrowserFrame(mock_page, "iframe-1", frame_name="payment")
        with pytest.raises(RuntimeError, match="No child frame matching URL"):
            outer.frame(url="missing.example.com")

    def test_nested_frame_requires_identifier(self, mock_page):
        frame = BrowserFrame(mock_page, "frame-id")
        with pytest.raises(RuntimeError, match="Specify selector, name, or url"):
            frame.frame()


# ---------------------------------------------------------------------------
# BrowserFrame._resolve_frame_by_selector
# ---------------------------------------------------------------------------


class TestResolveFrameBySelector:
    """Tests for selector-based frame resolution."""

    def test_resolves_by_name_match(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},
            {"result": {"value": {"name": "payment", "src": ""}}},
        ]
        frame = BrowserFrame(mock_page, "main-frame")
        child_frames = [
            {"id": "child-1", "name": "payment", "url": "https://pay.example.com"},
        ]
        result = frame._resolve_frame_by_selector("iframe#pay", child_frames)
        assert result is not None
        assert result["id"] == "child-1"

    def test_resolves_by_src_match(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},
            {"result": {"value": {"name": "", "src": "https://pay.example.com/form"}}},
        ]
        frame = BrowserFrame(mock_page, "main-frame")
        child_frames = [
            {"id": "child-1", "name": "", "url": "https://pay.example.com/form"},
        ]
        result = frame._resolve_frame_by_selector("iframe.pay", child_frames)
        assert result is not None
        assert result["id"] == "child-1"

    def test_returns_none_when_element_not_iframe(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},
            {"result": {"value": None}},
        ]
        frame = BrowserFrame(mock_page, "main-frame")
        result = frame._resolve_frame_by_selector("div.nope", [])
        assert result is None

    def test_fallback_to_single_child(self, mock_page):
        mock_page._cdp.send.side_effect = [
            {"executionContextId": 42},
            {"result": {"value": {"name": "", "src": "https://unknown.com"}}},
        ]
        frame = BrowserFrame(mock_page, "main-frame")
        child_frames = [
            {"id": "only-child", "name": "", "url": "https://different.com"},
        ]
        result = frame._resolve_frame_by_selector("iframe", child_frames)
        assert result is not None
        assert result["id"] == "only-child"


# ---------------------------------------------------------------------------
# BrowserPage.frames() and BrowserPage.frame()
# ---------------------------------------------------------------------------


class TestBrowserPageFrameMethods:
    """Tests for frame methods on BrowserPage (integration with _page.py)."""

    def test_page_frames_returns_list(self, mock_page, sample_frame_tree):
        """Verify the frames() method delegates to frame tree flattening."""
        # Directly test the frame tree functions since page.frames()
        # just calls these internally
        frames = _flatten_frame_tree(sample_frame_tree)
        assert len(frames) == 4
        assert frames[0]["depth"] == 0
        assert frames[1]["depth"] == 1

    def test_frame_tree_preserves_urls(self, sample_frame_tree):
        frames = _flatten_frame_tree(sample_frame_tree)
        urls = [f["url"] for f in frames]
        assert "https://example.com" in urls
        assert "https://payment.example.com/form" in urls
        assert "https://captcha.example.com/verify" in urls
        assert "https://ads.example.com/banner" in urls


# ---------------------------------------------------------------------------
# CLI: browser frames
# ---------------------------------------------------------------------------


class TestFramesCli:
    """Tests for 'naturo browser frames' CLI command."""

    def test_frames_help(self, runner):
        result = runner.invoke(browser, ["frames", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_frame_eval_help(self, runner):
        result = runner.invoke(browser, ["frame-eval", "--help"])
        assert result.exit_code == 0
        assert "FRAME_REF" in result.output
        assert "--by-name" in result.output
        assert "--by-url" in result.output

    def test_frame_find_help(self, runner):
        result = runner.invoke(browser, ["frame-find", "--help"])
        assert result.exit_code == 0
        assert "FRAME_REF" in result.output
        assert "--all" in result.output

    @patch("naturo.cli.browser_cmd._get_page")
    def test_frames_json_output(self, mock_get_page, runner):
        mock_page = MagicMock()
        mock_page.frames.return_value = [
            {"id": "main", "name": "", "url": "https://example.com", "parentId": "", "depth": 0},
            {"id": "f1", "name": "pay", "url": "https://pay.com", "parentId": "main", "depth": 1},
        ]
        mock_get_page.return_value = mock_page

        result = runner.invoke(browser, ["frames", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 2

    @patch("naturo.cli.browser_cmd._get_page")
    def test_frames_text_output(self, mock_get_page, runner):
        mock_page = MagicMock()
        mock_page.frames.return_value = [
            {"id": "main-frame-id", "name": "", "url": "https://example.com", "parentId": "", "depth": 0},
            {"id": "iframe-1-id", "name": "payment", "url": "https://pay.com/form", "parentId": "main", "depth": 1},
        ]
        mock_get_page.return_value = mock_page

        result = runner.invoke(browser, ["frames"])
        assert result.exit_code == 0
        assert "example.com" in result.output
        assert "payment" in result.output
        assert "2 frame(s)" in result.output

    @patch("naturo.cli.browser_cmd._get_page")
    def test_frames_empty(self, mock_get_page, runner):
        mock_page = MagicMock()
        mock_page.frames.return_value = []
        mock_get_page.return_value = mock_page

        result = runner.invoke(browser, ["frames"])
        assert result.exit_code == 0
        assert "No frames found" in result.output
