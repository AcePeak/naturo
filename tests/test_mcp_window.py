"""Tests for naturo.mcp._window — MCP window and app management tools.

Tests cover list_windows, focus_window, window_close/minimize/maximize/restore,
window_move/resize/set_bounds, app_hide/unhide/switch, and app_inspect
with mocked backend. All tests run on Linux CI (no Windows dependencies).
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Optional
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


@dataclass
class FakeWindowInfo:
    handle: int = 12345
    title: str = "Untitled - Notepad"
    process_name: str = "notepad.exe"
    pid: int = 1000
    x: int = 100
    y: int = 100
    width: int = 800
    height: int = 600
    is_visible: bool = True
    is_minimized: bool = False


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.list_windows.return_value = [
        FakeWindowInfo(),
        FakeWindowInfo(
            handle=67890, title="Google Chrome",
            process_name="chrome.exe", pid=2000,
            x=200, y=200, width=1200, height=800,
        ),
    ]
    return backend


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


# ── List Windows ──────────────────────────────────────────────────────


class TestListWindows:

    def test_returns_windows(self, server, mock_backend):
        result = _call_tool(server, "list_windows", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert len(data["windows"]) == 2
        win = data["windows"][0]
        assert win["handle"] == 12345
        assert win["title"] == "Untitled - Notepad"
        assert win["process_name"] == "notepad.exe"
        assert win["pid"] == 1000
        assert win["width"] == 800

    def test_empty_windows(self, server, mock_backend):
        mock_backend.list_windows.return_value = []
        result = _call_tool(server, "list_windows", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["windows"] == []


# ── Focus Window ──────────────────────────────────────────────────────


class TestFocusWindow:

    def test_focus_by_title(self, server, mock_backend):
        result = _call_tool(server, "focus_window", {"title": "Notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "focus"
        mock_backend.focus_window.assert_called_once_with(title="Notepad", hwnd=None)

    def test_focus_by_hwnd(self, server, mock_backend):
        result = _call_tool(server, "focus_window", {"hwnd": 12345})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.focus_window.assert_called_once_with(title=None, hwnd=12345)

    def test_focus_by_app(self, server, mock_backend):
        """When app is provided, it takes priority over title."""
        result = _call_tool(server, "focus_window", {"app": "chrome", "title": "ignored"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.focus_window.assert_called_once_with(title="chrome", hwnd=None)


# ── Window Close ──────────────────────────────────────────────────────


class TestWindowClose:

    def test_close_by_app(self, server, mock_backend):
        result = _call_tool(server, "window_close", {"app": "notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "close"
        mock_backend.close_window.assert_called_once_with(
            title="notepad", hwnd=None, force=False,
        )

    def test_close_force(self, server, mock_backend):
        result = _call_tool(server, "window_close", {"hwnd": 12345, "force": True})
        data = json.loads(result[0].text)
        assert data["success"] is True
        call_kwargs = mock_backend.close_window.call_args[1]
        assert call_kwargs["force"] is True


# ── Window Minimize/Maximize/Restore ─────────────────────────────────


class TestWindowMinimize:

    def test_minimize_by_app(self, server, mock_backend):
        result = _call_tool(server, "window_minimize", {"app": "notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "minimize"

    def test_minimize_by_hwnd(self, server, mock_backend):
        result = _call_tool(server, "window_minimize", {"hwnd": 12345})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.minimize_window.assert_called_once_with(title=None, hwnd=12345)


class TestWindowMaximize:

    def test_maximize(self, server, mock_backend):
        result = _call_tool(server, "window_maximize", {"app": "chrome"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "maximize"


class TestWindowRestore:

    def test_restore(self, server, mock_backend):
        result = _call_tool(server, "window_restore", {"hwnd": 12345})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "restore"


# ── Window Move/Resize/SetBounds ─────────────────────────────────────


class TestWindowMove:

    def test_move_to_position(self, server, mock_backend):
        result = _call_tool(server, "window_move", {"x": 50, "y": 100, "app": "notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "move"
        assert data["x"] == 50
        assert data["y"] == 100


class TestWindowResize:

    def test_resize(self, server, mock_backend):
        result = _call_tool(server, "window_resize", {"width": 1024, "height": 768})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "resize"
        assert data["width"] == 1024

    def test_resize_invalid_width(self, server, mock_backend):
        result = _call_tool(server, "window_resize", {"width": 0, "height": 100})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        mock_backend.resize_window.assert_not_called()

    def test_resize_invalid_height(self, server, mock_backend):
        result = _call_tool(server, "window_resize", {"width": 100, "height": -1})
        data = json.loads(result[0].text)
        assert data["success"] is False
        mock_backend.resize_window.assert_not_called()


class TestWindowSetBounds:

    def test_set_bounds(self, server, mock_backend):
        result = _call_tool(server, "window_set_bounds", {
            "x": 0, "y": 0, "width": 1920, "height": 1080,
        })
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "set-bounds"

    def test_set_bounds_invalid_size(self, server, mock_backend):
        result = _call_tool(server, "window_set_bounds", {
            "x": 0, "y": 0, "width": 0, "height": 100,
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


# ── App Hide/Unhide/Switch ───────────────────────────────────────────


class TestAppHide:

    def test_hide_matches_by_process(self, server, mock_backend):
        result = _call_tool(server, "app_hide", {"name": "notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "hide"
        assert data["windows_minimized"] == 1

    def test_hide_no_match(self, server, mock_backend):
        """When no windows match, should raise AppNotFoundError caught by _safe_tool."""
        result = _call_tool(server, "app_hide", {"name": "nonexistent_app"})
        data = json.loads(result[0].text)
        # _safe_tool wraps exceptions into error responses
        assert data["success"] is False


class TestAppUnhide:

    def test_unhide_matches(self, server, mock_backend):
        result = _call_tool(server, "app_unhide", {"name": "notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "unhide"
        assert data["windows_restored"] == 1

    def test_unhide_no_match(self, server, mock_backend):
        result = _call_tool(server, "app_unhide", {"name": "nonexistent_app"})
        data = json.loads(result[0].text)
        assert data["success"] is False


class TestAppSwitch:

    def test_switch_to_app(self, server, mock_backend):
        result = _call_tool(server, "app_switch", {"name": "notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["action"] == "switch"
        assert data["window_title"] == "Untitled - Notepad"
        assert data["handle"] == 12345
        mock_backend.focus_window.assert_called_once_with(hwnd=12345)

    def test_switch_no_match(self, server, mock_backend):
        result = _call_tool(server, "app_switch", {"name": "nonexistent_app"})
        data = json.loads(result[0].text)
        assert data["success"] is False


# ── App Inspect ───────────────────────────────────────────────────────


class TestAppInspect:

    def test_inspect_no_name_or_pid(self, server, mock_backend):
        result = _call_tool(server, "app_inspect", {})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_inspect_process_not_found(self, server, mock_backend):
        with patch("naturo.process.find_process", return_value=None):
            result = _call_tool(server, "app_inspect", {"name": "nonexistent"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "PROCESS_NOT_FOUND"

    def test_inspect_by_pid(self, server, mock_backend):
        # A directly-supplied PID must belong to a live process (#901); mock it
        # so the validation passes and detection proceeds.
        fake_proc = MagicMock()
        fake_proc.pid = 1234
        fake_proc.path = "C:\\app.exe"
        fake_proc.name = "app.exe"
        fake_detect_result = MagicMock()
        fake_detect_result.to_dict.return_value = {
            "frameworks": ["wpf"],
            "methods": ["uia"],
            "recommended": "uia",
        }
        with (
            patch("naturo.process.find_process", return_value=fake_proc),
            patch("naturo.detect.detect", return_value=fake_detect_result),
        ):
            result = _call_tool(server, "app_inspect", {"pid": 1234})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["recommended"] == "uia"

    def test_inspect_by_name(self, server, mock_backend):
        fake_proc = MagicMock()
        fake_proc.pid = 5678
        fake_proc.path = "C:\\notepad.exe"
        fake_proc.name = "notepad.exe"
        fake_detect_result = MagicMock()
        fake_detect_result.to_dict.return_value = {
            "frameworks": ["win32"],
            "methods": ["uia", "msaa"],
            "recommended": "uia",
        }
        with (
            patch("naturo.process.find_process", return_value=fake_proc),
            patch("naturo.detect.detect", return_value=fake_detect_result) as mock_detect,
        ):
            result = _call_tool(server, "app_inspect", {"name": "notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_detect.assert_called_once()
        call_kwargs = mock_detect.call_args[1]
        assert call_kwargs["pid"] == 5678
