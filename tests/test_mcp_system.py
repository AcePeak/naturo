"""Tests for naturo.mcp._system — MCP taskbar, tray, and virtual desktop tools.

Tests cover taskbar_list/click, tray_list/click, and virtual desktop
list/switch/create/close/move_window with mocked backend.
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
    backend.taskbar_list.return_value = [
        {"name": "Notepad", "hwnd": 12345, "is_active": True, "is_pinned": False},
        {"name": "Chrome", "hwnd": 67890, "is_active": False, "is_pinned": True},
    ]
    backend.taskbar_click.return_value = {"name": "Notepad", "x": 100, "y": 1060}
    backend.tray_list.return_value = [
        {"name": "Volume", "tooltip": "Speakers (80%)", "is_visible": True},
        {"name": "WiFi", "tooltip": "Connected", "is_visible": True},
    ]
    backend.tray_click.return_value = {
        "name": "Volume", "tooltip": "Speakers (80%)",
        "button": "left", "x": 1800, "y": 1060,
    }
    backend.virtual_desktop_list.return_value = [
        {"index": 0, "name": "Desktop 1", "is_current": True, "id": "d1"},
        {"index": 1, "name": "Desktop 2", "is_current": False, "id": "d2"},
    ]
    backend.virtual_desktop_switch.return_value = {"index": 1, "name": "Desktop 2"}
    backend.virtual_desktop_create.return_value = {"index": 2, "name": "Desktop 3", "id": "d3"}
    backend.virtual_desktop_close.return_value = {"index": 1, "name": "Desktop 2"}
    backend.virtual_desktop_move_window.return_value = {
        "hwnd": 12345, "desktop_index": 1, "name": "Desktop 2",
    }
    return backend


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


# ── Taskbar ───────────────────────────────────────────────────────────


class TestTaskbarList:

    def test_returns_items(self, server, mock_backend):
        result = _call_tool(server, "taskbar_list", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["count"] == 2
        assert data["items"][0]["name"] == "Notepad"
        assert data["items"][1]["is_pinned"] is True

    def test_empty_taskbar(self, server, mock_backend):
        mock_backend.taskbar_list.return_value = []
        result = _call_tool(server, "taskbar_list", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["count"] == 0
        assert data["items"] == []


class TestTaskbarClick:

    def test_clicks_by_name(self, server, mock_backend):
        result = _call_tool(server, "taskbar_click", {"name": "Notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["name"] == "Notepad"
        mock_backend.taskbar_click.assert_called_once_with(name="Notepad")


# ── System Tray ───────────────────────────────────────────────────────


class TestTrayList:

    def test_returns_icons(self, server, mock_backend):
        result = _call_tool(server, "tray_list", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["count"] == 2
        assert data["icons"][0]["name"] == "Volume"

    def test_empty_tray(self, server, mock_backend):
        mock_backend.tray_list.return_value = []
        result = _call_tool(server, "tray_list", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["count"] == 0


class TestTrayClick:

    def test_left_click(self, server, mock_backend):
        result = _call_tool(server, "tray_click", {"name": "Volume"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["name"] == "Volume"
        mock_backend.tray_click.assert_called_once_with(
            name="Volume", button="left", double=False,
        )

    def test_right_click(self, server, mock_backend):
        result = _call_tool(server, "tray_click", {"name": "WiFi", "button": "right"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.tray_click.assert_called_once_with(
            name="WiFi", button="right", double=False,
        )

    def test_double_click(self, server, mock_backend):
        result = _call_tool(server, "tray_click", {"name": "Volume", "double_click": True})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.tray_click.assert_called_once_with(
            name="Volume", button="left", double=True,
        )


# ── Virtual Desktop ──────────────────────────────────────────────────


class TestVirtualDesktopList:

    def test_returns_desktops(self, server, mock_backend):
        result = _call_tool(server, "virtual_desktop_list", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["count"] == 2
        assert data["desktops"][0]["is_current"] is True
        assert data["desktops"][1]["name"] == "Desktop 2"


class TestVirtualDesktopSwitch:

    def test_switch_by_index(self, server, mock_backend):
        result = _call_tool(server, "virtual_desktop_switch", {"index": 1})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["index"] == 1
        assert data["name"] == "Desktop 2"
        mock_backend.virtual_desktop_switch.assert_called_once_with(1)


class TestVirtualDesktopCreate:

    def test_create_with_name(self, server, mock_backend):
        result = _call_tool(server, "virtual_desktop_create", {"name": "Work"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.virtual_desktop_create.assert_called_once_with(name="Work")

    def test_create_without_name(self, server, mock_backend):
        result = _call_tool(server, "virtual_desktop_create", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.virtual_desktop_create.assert_called_once_with(name=None)


class TestVirtualDesktopClose:

    def test_close_by_index(self, server, mock_backend):
        result = _call_tool(server, "virtual_desktop_close", {"index": 1})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.virtual_desktop_close.assert_called_once_with(index=1)

    def test_close_current(self, server, mock_backend):
        result = _call_tool(server, "virtual_desktop_close", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.virtual_desktop_close.assert_called_once_with(index=None)


class TestVirtualDesktopMoveWindow:

    def test_move_by_app(self, server, mock_backend):
        result = _call_tool(server, "virtual_desktop_move_window", {
            "desktop_index": 1, "app": "Notepad",
        })
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["desktop_index"] == 1
        mock_backend.virtual_desktop_move_window.assert_called_once_with(
            desktop_index=1, app="Notepad", hwnd=None,
        )

    def test_move_by_hwnd(self, server, mock_backend):
        result = _call_tool(server, "virtual_desktop_move_window", {
            "desktop_index": 0, "hwnd": 12345,
        })
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.virtual_desktop_move_window.assert_called_once_with(
            desktop_index=0, app=None, hwnd=12345,
        )

    def test_move_foreground_window(self, server, mock_backend):
        result = _call_tool(server, "virtual_desktop_move_window", {"desktop_index": 1})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.virtual_desktop_move_window.assert_called_once_with(
            desktop_index=1, app=None, hwnd=None,
        )
