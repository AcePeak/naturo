"""Tests for naturo.mcp._input — MCP input tools (click, type, press, scroll, drag, move).

Tests cover all input MCP tools with mocked backend, including eN ref
resolution, input validation, combo key parsing, and error paths.
All tests run on Linux CI (no Windows dependencies).
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


def _call_tool(server, tool_name: str, arguments: dict):
    """Helper to call an MCP tool function by name."""
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    # Default: no focused ValuePattern control, so type_text falls back to
    # keystroke injection (the path most tests assert). The IME-immune
    # ValuePattern path (#1219) is covered explicitly in TestTypeText.
    backend.set_focused_element_value.return_value = False
    return backend


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


# ── Click ─────────────────────────────────────────────────────────────


class TestClick:

    def test_click_at_coordinates(self, server, mock_backend):
        result = _call_tool(server, "click", {"x": 100, "y": 200})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.click.assert_called_once_with(
            x=100, y=200, element_id=None, button="left",
            double=False, input_mode="normal",
        )

    def test_click_right_button(self, server, mock_backend):
        result = _call_tool(server, "click", {"x": 50, "y": 50, "button": "right"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.click.assert_called_once()
        call_kwargs = mock_backend.click.call_args[1]
        assert call_kwargs["button"] == "right"

    def test_click_double(self, server, mock_backend):
        result = _call_tool(server, "click", {"x": 50, "y": 50, "double": True})
        data = json.loads(result[0].text)
        assert data["success"] is True
        call_kwargs = mock_backend.click.call_args[1]
        assert call_kwargs["double"] is True

    def test_click_element_id(self, server, mock_backend):
        result = _call_tool(server, "click", {"element_id": "btn_ok"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.click.assert_called_once()
        call_kwargs = mock_backend.click.call_args[1]
        assert call_kwargs["element_id"] == "btn_ok"

    def test_click_resolves_en_ref(self, server, mock_backend):
        """eN refs should be resolved to coordinates via snapshot manager."""
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref.return_value = (300, 400)
        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = _call_tool(server, "click", {"element_id": "e42"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_mgr.resolve_ref.assert_called_once_with("e42")
        call_kwargs = mock_backend.click.call_args[1]
        assert call_kwargs["x"] == 300
        assert call_kwargs["y"] == 400
        assert call_kwargs["element_id"] is None

    def test_click_en_ref_not_found(self, server, mock_backend):
        """Unresolvable eN ref should return ELEMENT_NOT_FOUND error."""
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref.return_value = None
        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = _call_tool(server, "click", {"element_id": "e999"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "ELEMENT_NOT_FOUND"
        mock_backend.click.assert_not_called()

    def test_click_hardware_mode(self, server, mock_backend):
        result = _call_tool(server, "click", {"x": 10, "y": 20, "input_mode": "hardware"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        call_kwargs = mock_backend.click.call_args[1]
        assert call_kwargs["input_mode"] == "hardware"


# ── Type ──────────────────────────────────────────────────────────────


class TestTypeText:

    def test_type_text_basic(self, server, mock_backend):
        result = _call_tool(server, "type_text", {"text": "hello world"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        # Normal mode with no writable ValuePattern → atomic clipboard paste.
        assert data["method"] == "clipboard_paste"
        mock_backend.clipboard_set.assert_any_call("hello world")

    def test_type_text_custom_wpm(self, server, mock_backend):
        # wpm only applies to the keystroke fallback; force it by making paste
        # unavailable, then confirm wpm reaches the backend.
        mock_backend.clipboard_set.side_effect = RuntimeError("no clipboard")
        result = _call_tool(server, "type_text", {"text": "fast", "wpm": 300})
        data = json.loads(result[0].text)
        assert data["success"] is True
        call_kwargs = mock_backend.type_text.call_args[1]
        assert call_kwargs["wpm"] == 300

    def test_type_text_invalid_wpm(self, server, mock_backend):
        result = _call_tool(server, "type_text", {"text": "x", "wpm": 0})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        mock_backend.type_text.assert_not_called()

    def test_type_text_unicode(self, server, mock_backend):
        result = _call_tool(server, "type_text", {"text": "日本語テスト 🎉"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.clipboard_set.assert_any_call("日本語テスト 🎉")

    def test_type_text_hardware_mode(self, server, mock_backend):
        result = _call_tool(server, "type_text", {"text": "hw", "input_mode": "hardware"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        call_kwargs = mock_backend.type_text.call_args[1]
        assert call_kwargs["input_mode"] == "hardware"

    def test_type_text_prefers_value_pattern_when_available(self, server, mock_backend):
        """#1219: focused control with a writable ValuePattern → IME-immune
        direct write, no keystroke injection."""
        mock_backend.set_focused_element_value.return_value = True
        result = _call_tool(server, "type_text", {"text": "naturo"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["method"] == "value_pattern"
        mock_backend.set_focused_element_value.assert_called_once_with("naturo", append=True)
        mock_backend.type_text.assert_not_called()

    def test_type_text_falls_back_to_clipboard_paste_without_value_pattern(self, server, mock_backend):
        """No writable ValuePattern (default) → clipboard paste: atomic and
        IME-immune. A fast per-key SendInput drops chars on heavy controls like
        Win11 Notepad ("hello from naturo" -> "hello      turo")."""
        result = _call_tool(server, "type_text", {"text": "naturo"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["method"] == "clipboard_paste"
        mock_backend.set_focused_element_value.assert_called_once()
        # paste path used → no per-key keystroke injection
        mock_backend.type_text.assert_not_called()

    def test_type_text_falls_back_to_keystroke_when_paste_unavailable(self, server, mock_backend):
        """Neither ValuePattern nor clipboard paste can apply → keystroke."""
        mock_backend.clipboard_set.side_effect = RuntimeError("no clipboard")
        result = _call_tool(server, "type_text", {"text": "naturo"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["method"] == "keystroke"
        mock_backend.type_text.assert_called_once()

    def test_type_text_hardware_mode_skips_value_pattern(self, server, mock_backend):
        """Explicit 'hardware' scan-code mode is keystroke-only — ValuePattern
        is not attempted."""
        mock_backend.set_focused_element_value.return_value = True
        result = _call_tool(server, "type_text", {"text": "hw", "input_mode": "hardware"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["method"] == "keystroke"
        mock_backend.set_focused_element_value.assert_not_called()
        mock_backend.type_text.assert_called_once()

    def test_type_text_with_hwnd_focuses_target_first(self, server, mock_backend):
        """A target hwnd focuses that window first (atomic focus+type), so the
        agent doesn't need a separate focus_window call and there's no
        cross-call focus race."""
        result = _call_tool(server, "type_text", {"text": "naturo", "hwnd": 4242})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.focus_window.assert_called_once_with(hwnd=4242, title=None)

    def test_type_text_without_target_does_not_focus(self, server, mock_backend):
        """No target → type into the focused window; focus_window is not called."""
        _call_tool(server, "type_text", {"text": "naturo"})
        mock_backend.focus_window.assert_not_called()


# ── Press Key ─────────────────────────────────────────────────────────


class TestPressKey:

    def test_press_single_key(self, server, mock_backend):
        result = _call_tool(server, "press_key", {"key": "enter"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.press_key.assert_called_once_with(key="enter", input_mode="normal")

    def test_press_key_combo(self, server, mock_backend):
        result = _call_tool(server, "press_key", {"key": "ctrl+c"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "hotkey"
        assert data["combo"] == "ctrl+c"
        mock_backend.hotkey.assert_called_once_with("ctrl", "c", input_mode="normal")

    def test_press_key_triple_combo(self, server, mock_backend):
        result = _call_tool(server, "press_key", {"key": "ctrl+shift+s"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.hotkey.assert_called_once_with("ctrl", "shift", "s", input_mode="normal")

    def test_press_key_count(self, server, mock_backend):
        result = _call_tool(server, "press_key", {"key": "tab", "count": 3})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert mock_backend.press_key.call_count == 3

    def test_press_key_combo_count(self, server, mock_backend):
        """Combo keys repeated by count."""
        result = _call_tool(server, "press_key", {"key": "ctrl+z", "count": 2})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert mock_backend.hotkey.call_count == 2

    def test_press_key_invalid_count(self, server, mock_backend):
        result = _call_tool(server, "press_key", {"key": "enter", "count": 0})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        mock_backend.press_key.assert_not_called()

    def test_press_key_with_hwnd_focuses_target_first(self, server, mock_backend):
        """A target hwnd focuses that window first, so the keys land there —
        no separate focus_window call and no foreground race."""
        result = _call_tool(server, "press_key", {"key": "enter", "hwnd": 4242})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.focus_window.assert_called_once_with(hwnd=4242, title=None)
        mock_backend.press_key.assert_called_once()

    def test_press_key_without_target_does_not_focus(self, server, mock_backend):
        _call_tool(server, "press_key", {"key": "enter"})
        mock_backend.focus_window.assert_not_called()


# ── Scroll ────────────────────────────────────────────────────────────


class TestScroll:

    def test_scroll_down_default(self, server, mock_backend):
        result = _call_tool(server, "scroll", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.scroll.assert_called_once_with(
            direction="down", amount=3, x=None, y=None,
        )

    def test_scroll_up(self, server, mock_backend):
        result = _call_tool(server, "scroll", {"direction": "up", "amount": 5})
        data = json.loads(result[0].text)
        assert data["success"] is True
        call_kwargs = mock_backend.scroll.call_args[1]
        assert call_kwargs["direction"] == "up"
        assert call_kwargs["amount"] == 5

    def test_scroll_at_position(self, server, mock_backend):
        result = _call_tool(server, "scroll", {"x": 100, "y": 200, "amount": 2})
        data = json.loads(result[0].text)
        assert data["success"] is True
        call_kwargs = mock_backend.scroll.call_args[1]
        assert call_kwargs["x"] == 100
        assert call_kwargs["y"] == 200

    def test_scroll_invalid_amount(self, server, mock_backend):
        result = _call_tool(server, "scroll", {"amount": 0})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        mock_backend.scroll.assert_not_called()


# ── Drag ──────────────────────────────────────────────────────────────


class TestDrag:

    def test_drag_basic(self, server, mock_backend):
        result = _call_tool(server, "drag", {
            "from_x": 10, "from_y": 20, "to_x": 100, "to_y": 200,
        })
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.drag.assert_called_once_with(
            from_x=10, from_y=20, to_x=100, to_y=200,
            duration_ms=500, steps=10,
        )

    def test_drag_custom_params(self, server, mock_backend):
        result = _call_tool(server, "drag", {
            "from_x": 0, "from_y": 0, "to_x": 50, "to_y": 50,
            "duration_ms": 1000, "steps": 20,
        })
        data = json.loads(result[0].text)
        assert data["success"] is True
        call_kwargs = mock_backend.drag.call_args[1]
        assert call_kwargs["duration_ms"] == 1000
        assert call_kwargs["steps"] == 20

    def test_drag_invalid_steps(self, server, mock_backend):
        result = _call_tool(server, "drag", {
            "from_x": 0, "from_y": 0, "to_x": 1, "to_y": 1, "steps": 0,
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        mock_backend.drag.assert_not_called()

    def test_drag_invalid_duration(self, server, mock_backend):
        result = _call_tool(server, "drag", {
            "from_x": 0, "from_y": 0, "to_x": 1, "to_y": 1, "duration_ms": -1,
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        mock_backend.drag.assert_not_called()

    def test_drag_zero_duration_ok(self, server, mock_backend):
        result = _call_tool(server, "drag", {
            "from_x": 0, "from_y": 0, "to_x": 1, "to_y": 1, "duration_ms": 0,
        })
        data = json.loads(result[0].text)
        assert data["success"] is True


# ── Move Mouse ────────────────────────────────────────────────────────


class TestMoveMouse:

    def test_move_basic(self, server, mock_backend):
        result = _call_tool(server, "move_mouse", {"x": 500, "y": 300})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.move_mouse.assert_called_once_with(x=500, y=300)
