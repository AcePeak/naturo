"""Tests for naturo.browser._element — BrowserElement CDP wrapper.

All tests mock the CDP layer so no Chrome instance is needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from naturo.browser._element import BrowserElement


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_element(
    object_id="obj-1",
    call_return=None,
    send_return=None,
):
    """Build a BrowserElement with mocked page and CDP.

    Args:
        object_id: CDP object ID for the element.
        call_return: Default return for Runtime.callFunctionOn.
        send_return: Default return for cdp.send().
    """
    mock_cdp = MagicMock()
    mock_cdp.send.return_value = send_return or {
        "result": {"value": call_return}
    }

    mock_page = MagicMock()
    mock_page._cdp = mock_cdp

    el = BrowserElement(
        page=mock_page,
        object_id=object_id,
        description="div#test",
    )
    return el, mock_page, mock_cdp


# ═════════════════════════════════════════════════════════════════════════════
# Properties
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserElementProperties:
    """Element property accessor tests."""

    def test_object_id(self):
        el, _, _ = _make_element(object_id="my-oid")
        assert el.object_id == "my-oid"

    def test_text_returns_text_content(self):
        el, _, cdp = _make_element(call_return="Hello World")
        assert el.text == "Hello World"

    def test_text_returns_empty_on_none(self):
        el, _, cdp = _make_element()
        cdp.send.return_value = {"result": {"value": None}}
        assert el.text == ""

    def test_inner_html(self):
        el, _, cdp = _make_element(call_return="<span>hi</span>")
        assert el.inner_html == "<span>hi</span>"

    def test_outer_html(self):
        el, _, cdp = _make_element(call_return="<div><span>hi</span></div>")
        assert el.outer_html == "<div><span>hi</span></div>"

    def test_tag_name(self):
        el, _, cdp = _make_element(call_return="INPUT")
        assert el.tag_name == "INPUT"

    def test_value(self):
        el, _, cdp = _make_element(call_return="user@example.com")
        assert el.value == "user@example.com"


# ═════════════════════════════════════════════════════════════════════════════
# Attributes
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserElementAttr:
    """Attribute access tests."""

    def test_attr_returns_string(self):
        el, _, cdp = _make_element(call_return="https://example.com")
        assert el.attr("href") == "https://example.com"

    def test_attr_returns_none_when_absent(self):
        el, _, cdp = _make_element()
        cdp.send.return_value = {"result": {"value": None}}
        assert el.attr("data-missing") is None

    def test_attr_escapes_quotes_in_name(self):
        el, _, cdp = _make_element(call_return="val")
        el.attr("data-it's")
        # Verify the function declaration escapes the quote
        call_args = cdp.send.call_args
        func_decl = call_args[0][1]["functionDeclaration"]
        assert "\\'" in func_decl


# ═════════════════════════════════════════════════════════════════════════════
# Click
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserElementClick:
    """Click interaction tests."""

    def test_click_dispatches_mouse_events(self):
        el, page, cdp = _make_element()
        # scrollIntoView, then DOM.getContentQuads (top-document coords, #1080).
        # Quad vertices: TL(100,200) TR(150,200) BR(150,230) BL(100,230).
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": [[100, 200, 150, 200, 150, 230, 100, 230]]},
            {},  # mousePressed
            {},  # mouseReleased
        ]

        result = el.click()
        assert result is el  # chaining

        # Check mouse events were dispatched
        mouse_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Input.dispatchMouseEvent"
        ]
        assert len(mouse_calls) == 2
        assert mouse_calls[0][0][1]["type"] == "mousePressed"
        assert mouse_calls[1][0][1]["type"] == "mouseReleased"

        # Click should be at the quad centroid: (100+150)/2, (200+230)/2
        assert mouse_calls[0][0][1]["x"] == 125.0
        assert mouse_calls[0][0][1]["y"] == 215.0

    def test_click_with_offset(self):
        el, page, cdp = _make_element()
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": [[100, 200, 150, 200, 150, 230, 100, 230]]},
            {},  # mousePressed
            {},  # mouseReleased
        ]

        el.click(offset_x=10, offset_y=5)

        mouse_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Input.dispatchMouseEvent"
        ]
        # Offsets are from the top-left quad vertex: 100 + 10, 200 + 5
        assert mouse_calls[0][0][1]["x"] == 110
        assert mouse_calls[0][0][1]["y"] == 205

    def test_click_falls_back_to_bounding_rect_without_quad(self):
        el, page, cdp = _make_element()
        # No content quad (unrendered/zero-area) -> getBoundingClientRect path.
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": []},  # getContentQuads: no quad
            {"result": {"value": {"x": 100, "y": 200, "width": 50, "height": 30}}},
            {},  # mousePressed
            {},  # mouseReleased
        ]

        el.click()

        mouse_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Input.dispatchMouseEvent"
        ]
        assert mouse_calls[0][0][1]["x"] == 125.0  # 100 + 25
        assert mouse_calls[0][0][1]["y"] == 215.0  # 200 + 15

    def test_click_raises_when_no_position(self):
        el, page, cdp = _make_element()
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": []},  # getContentQuads: no quad
            {"result": {"value": None}},  # getBoundingClientRect returns None
        ]

        with pytest.raises(RuntimeError, match="Cannot determine element position"):
            el.click()

    def test_click_raises_when_quad_computation_errors(self):
        el, page, cdp = _make_element()
        # getContentQuads can raise (CDP "could not compute content quads"); the
        # fallback then also finds no box -> click must raise, never silently
        # no-op (never-lie, #1080).
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            RuntimeError("could not compute content quads"),
            {"result": {"value": None}},  # getBoundingClientRect returns None
        ]

        with pytest.raises(RuntimeError, match="Cannot determine element position"):
            el.click()

    def test_click_raises_on_zero_area_box_never_dispatches(self):
        # display:none / detached / zero-area element: no content quad, and
        # getBoundingClientRect reports an all-zeros rect. click() must raise
        # rather than silently dispatch at the (0, 0) viewport origin (#1083).
        el, page, cdp = _make_element()
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": []},  # getContentQuads: no quad
            {"result": {"value": {"x": 0, "y": 0, "width": 0, "height": 0}}},
        ]

        with pytest.raises(RuntimeError, match="Cannot determine element position"):
            el.click()

        mouse_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Input.dispatchMouseEvent"
        ]
        assert mouse_calls == []  # never dispatched at (0, 0)


# ═════════════════════════════════════════════════════════════════════════════
# Hover
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserElementHover:
    """Hover interaction tests."""

    def test_hover_dispatches_mouse_moved(self):
        el, page, cdp = _make_element()
        # Quad TL(50,60) TR(70,60) BR(70,70) BL(50,70) -> centroid (60,65).
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": [[50, 60, 70, 60, 70, 70, 50, 70]]},
            {},  # mouseMoved
        ]

        result = el.hover()
        assert result is el

        mouse_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Input.dispatchMouseEvent"
        ]
        assert len(mouse_calls) == 1
        assert mouse_calls[0][0][1]["type"] == "mouseMoved"
        assert mouse_calls[0][0][1]["x"] == 60.0  # quad centroid x
        assert mouse_calls[0][0][1]["y"] == 65.0  # quad centroid y

    def test_hover_raises_when_no_position(self):
        el, page, cdp = _make_element()
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": []},  # getContentQuads: no quad
            {"result": {"value": None}},  # no bounding rect
        ]

        with pytest.raises(RuntimeError, match="Cannot determine element position"):
            el.hover()

    def test_hover_raises_on_zero_area_box_never_dispatches(self):
        # Mirror of the click guard (#1083): a zero-area / unrendered element
        # must make hover() raise rather than move the mouse to (0, 0).
        el, page, cdp = _make_element()
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": []},  # getContentQuads: no quad
            {"result": {"value": {"x": 0, "y": 0, "width": 0, "height": 0}}},
        ]

        with pytest.raises(RuntimeError, match="Cannot determine element position"):
            el.hover()

        mouse_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Input.dispatchMouseEvent"
        ]
        assert mouse_calls == []


# ═════════════════════════════════════════════════════════════════════════════
# Type
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserElementType:
    """Text input tests."""

    def test_type_sends_key_events(self):
        el, page, cdp = _make_element()
        cdp.send.return_value = {"result": {"value": None}}

        result = el.type("ab")
        assert result is el

        key_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Input.dispatchKeyEvent"
        ]
        # 2 chars * 2 events each (keyDown + keyUp)
        assert len(key_calls) == 4
        assert key_calls[0][0][1] == {"type": "keyDown", "text": "a"}
        assert key_calls[1][0][1] == {"type": "keyUp", "text": "a"}
        assert key_calls[2][0][1] == {"type": "keyDown", "text": "b"}
        assert key_calls[3][0][1] == {"type": "keyUp", "text": "b"}

    def test_type_with_clear_first(self):
        el, page, cdp = _make_element()
        cdp.send.return_value = {"result": {"value": None}}

        el.type("new", clear_first=True)

        # Should have: focus call, clear call, then key events
        func_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Runtime.callFunctionOn"
        ]
        # First: focus, second: clear value
        assert len(func_calls) >= 2
        assert "focus" in func_calls[0][0][1]["functionDeclaration"]
        assert "value = ''" in func_calls[1][0][1]["functionDeclaration"]

    def test_type_empty_string(self):
        el, page, cdp = _make_element()
        cdp.send.return_value = {"result": {"value": None}}

        el.type("")
        key_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Input.dispatchKeyEvent"
        ]
        assert len(key_calls) == 0


# ═════════════════════════════════════════════════════════════════════════════
# Scroll into view
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserElementScroll:
    """Scroll into view tests."""

    def test_scroll_into_view_calls_js(self):
        el, page, cdp = _make_element()
        cdp.send.return_value = {"result": {"value": None}}

        result = el.scroll_into_view()
        assert result is el

        func_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Runtime.callFunctionOn"
        ]
        assert any("scrollIntoView" in c[0][1]["functionDeclaration"] for c in func_calls)


# ═════════════════════════════════════════════════════════════════════════════
# Child finding
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserElementFind:
    """Child element finding tests."""

    def test_find_css_uses_querySelector(self):
        el, page, cdp = _make_element()
        cdp.send.return_value = {
            "result": {"objectId": "child-1", "description": "span"}
        }

        child = el.find(".child")
        assert child.object_id == "child-1"

        func_calls = [
            c for c in cdp.send.call_args_list
            if c[0][0] == "Runtime.callFunctionOn"
        ]
        assert any("querySelector" in c[0][1]["functionDeclaration"] for c in func_calls)

    def test_find_raises_when_not_found(self):
        el, page, cdp = _make_element()
        cdp.send.return_value = {"result": {"subtype": "null"}}

        with pytest.raises(RuntimeError, match="No element found"):
            el.find(".missing")

    def test_find_xpath_delegates_to_page(self):
        el, page, cdp = _make_element()
        page._find_within.return_value = BrowserElement(page, "xpath-el")

        child = el.find("xpath://span")
        page._find_within.assert_called_once()
        assert child.object_id == "xpath-el"

    def test_find_all_css_uses_querySelectorAll(self):
        el, page, cdp = _make_element()
        # callFunctionOn returns array objectId
        cdp.send.side_effect = [
            {"result": {"objectId": "arr-1"}},
            {
                "result": [
                    {"name": "0", "value": {"objectId": "c-0", "description": "li"}},
                    {"name": "1", "value": {"objectId": "c-1", "description": "li"}},
                ]
            },
        ]

        children = el.find_all("li.item")
        assert len(children) == 2

    def test_find_all_xpath_delegates_to_page(self):
        el, page, cdp = _make_element()
        page._find_all_within.return_value = [
            BrowserElement(page, "x1"),
            BrowserElement(page, "x2"),
        ]

        children = el.find_all("xpath://li")
        assert len(children) == 2
        page._find_all_within.assert_called_once()


# ═════════════════════════════════════════════════════════════════════════════
# Click point calculation
# ═════════════════════════════════════════════════════════════════════════════


class TestGetClickPoint:
    """Content-quad and coordinate calculation tests (#1080)."""

    def test_center_point_from_quad(self):
        el, page, cdp = _make_element()
        # Quad TL(10,20) TR(110,20) BR(110,70) BL(10,70) -> centroid (60,45).
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": [[10, 20, 110, 20, 110, 70, 10, 70]]},
        ]
        point = el._get_click_point()
        assert point == (60.0, 45.0)

    def test_offset_point_from_quad(self):
        el, page, cdp = _make_element()
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": [[10, 20, 110, 20, 110, 70, 10, 70]]},
        ]
        # Offset measured from the top-left quad vertex (10,20).
        point = el._get_click_point(offset_x=5, offset_y=10)
        assert point == (15, 30)

    def test_falls_back_to_bounding_rect_without_quad(self):
        el, page, cdp = _make_element()
        # getContentQuads returns no quad -> getBoundingClientRect fallback.
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": []},  # no quad
            {"result": {"value": {"x": 10, "y": 20, "width": 100, "height": 50}}},
        ]
        point = el._get_click_point()
        assert point == (60.0, 45.0)  # 10+50, 20+25

    def test_returns_none_when_no_box(self):
        el, page, cdp = _make_element()
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": []},  # no quad
            {"result": {"value": None}},  # no rect
        ]
        assert el._get_click_point() is None

    def test_returns_none_when_box_not_dict(self):
        el, page, cdp = _make_element()
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": []},  # no quad
            {"result": {"value": "not-a-dict"}},
        ]
        assert el._get_click_point() is None

    def test_returns_none_on_zero_area_box(self):
        # #1083: an unrendered element yields no quad and an all-zeros rect.
        # _get_click_point must return None (not the origin (0, 0)) so the
        # click/hover guards raise instead of dispatching at the wrong spot.
        el, page, cdp = _make_element()
        cdp.send.side_effect = [
            {"result": {"value": None}},  # scrollIntoView
            {"quads": []},  # no quad
            {"result": {"value": {"x": 0, "y": 0, "width": 0, "height": 0}}},
        ]
        assert el._get_click_point() is None


# ═════════════════════════════════════════════════════════════════════════════
# Repr
# ═════════════════════════════════════════════════════════════════════════════


class TestBrowserElementRepr:
    """String representation tests."""

    def test_repr_with_description(self):
        el = BrowserElement(MagicMock(), "obj-123", description="input#email")
        assert repr(el) == "<BrowserElement input#email>"

    def test_repr_without_description_uses_oid(self):
        el = BrowserElement(MagicMock(), "obj-ABCDEFGHIJKLMNOPQRSTUVWX", description="")
        # __repr__ uses object_id[:20] when no description
        r = repr(el)
        assert "BrowserElement" in r
        assert "obj-ABCDEFGHIJKLMNOP" in r
