"""Tests for naturo.mcp._app — MCP app control and menu inspection tools.

Tests cover list_apps, launch_app, quit_app, and menu_inspect
with mocked backend. All tests run on Linux CI (no Windows dependencies).
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from types import SimpleNamespace
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
class FakeProcessInfo:
    pid: int = 1234
    name: str = "notepad.exe"
    path: str = "C:\\Windows\\notepad.exe"
    is_running: bool = True
    window_count: int = 1


@dataclass
class FakeMenuItem:
    name: str = "File"
    shortcut: Optional[str] = None
    enabled: bool = True
    checked: bool = False
    children: list = field(default_factory=list)


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.list_apps.return_value = [
        {"name": "notepad.exe", "pid": 1234, "title": "Untitled - Notepad"},
        {"name": "chrome.exe", "pid": 5678, "title": "Google Chrome"},
    ]
    backend.get_menu_items.return_value = [
        FakeMenuItem(
            name="File",
            children=[
                FakeMenuItem(name="New", shortcut="Ctrl+N"),
                FakeMenuItem(name="Open...", shortcut="Ctrl+O"),
                FakeMenuItem(name="Save", shortcut="Ctrl+S", enabled=False),
            ],
        ),
        FakeMenuItem(name="Edit"),
    ]
    return backend


@pytest.fixture
def mock_launch_app():
    return MagicMock(return_value=FakeProcessInfo())


@pytest.fixture
def server(mock_backend, mock_launch_app):
    with (
        patch("naturo.mcp_server.get_backend", return_value=mock_backend),
        patch("naturo.mcp_server._launch_app", mock_launch_app),
    ):
        yield create_server()


# ── List Apps ─────────────────────────────────────────────────────────


class TestListApps:

    def test_returns_apps(self, server, mock_backend):
        result = _call_tool(server, "list_apps", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert len(data["apps"]) == 2
        assert data["apps"][0]["name"] == "notepad.exe"

    def test_empty_apps(self, server, mock_backend):
        mock_backend.list_apps.return_value = []
        result = _call_tool(server, "list_apps", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["apps"] == []


# ── Launch App ────────────────────────────────────────────────────────


class TestLaunchApp:

    def test_launch_app(self, server, mock_backend, mock_launch_app):
        win = SimpleNamespace(handle=222, title="Untitled - Notepad")
        # The window-diff needs the new window absent before and present after,
        # so it is reported as the freshly launched window.
        mock_backend.list_windows.side_effect = [[], [win], [win], [win]]
        result = _call_tool(server, "launch_app", {"name": "notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["pid"] == 1234
        assert data["name"] == "notepad.exe"
        assert data["is_running"] is True
        assert data["window_count"] == 1
        assert data["hwnd"] == 222


# ── Launch Browser (CDP) ──────────────────────────────────────────────


class TestLaunchBrowser:

    def test_returns_hwnd_and_wires_cdp(self, server, mock_backend):
        win = SimpleNamespace(handle=888, title="Baidu - Google Chrome")
        mock_backend.list_windows.side_effect = [[], [win], [win], [win]]
        fake_chrome = SimpleNamespace(port=9222, pid=4321)
        with patch(
            "naturo.browser._launcher.launch_chrome", return_value=fake_chrome
        ) as m:
            result = _call_tool(
                server, "launch_browser", {"url": "https://example.com"}
            )
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["hwnd"] == 888
        assert data["debug_port"] == 9222
        assert data["pid"] == 4321
        assert data["url"] == "https://example.com"
        # Reuses the browser subsystem: opens the URL, waits for CDP, and uses a
        # throwaway profile so a fresh *debuggable* instance starts by default.
        _, kwargs = m.call_args
        assert kwargs["url"] == "https://example.com"
        assert kwargs["wait_ready"] is True
        assert kwargs["user_data_dir"] is not None
        # First-run suppression: a fresh profile must not open the welcome /
        # sign-in / search-engine-choice screen over the page (it steals the
        # active tab and CDP then reads an empty interstitial).
        assert "--no-first-run" in kwargs["extra_args"]
        assert "--disable-search-engine-choice-screen" in kwargs["extra_args"]

    def test_profile_uses_real_session_not_throwaway(self, server, mock_backend):
        win = SimpleNamespace(handle=999, title="Chrome")
        mock_backend.list_windows.side_effect = [[], [win], [win]]
        fake_chrome = SimpleNamespace(port=9222, pid=1)
        with patch(
            "naturo.browser._launcher.launch_chrome", return_value=fake_chrome
        ) as m:
            _call_tool(server, "launch_browser", {"profile": "Work"})
        _, kwargs = m.call_args
        assert kwargs["profile"] == "Work"
        # A named profile means the real user-data dir, not a throwaway one.
        assert kwargs["user_data_dir"] is None


# ── Quit App ──────────────────────────────────────────────────────────


class TestQuitApp:

    def test_quit_app(self, server, mock_backend):
        result = _call_tool(server, "quit_app", {"name": "notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.quit_app.assert_called_once_with(name="notepad", force=False)

    def test_quit_app_force(self, server, mock_backend):
        result = _call_tool(server, "quit_app", {"name": "chrome", "force": True})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.quit_app.assert_called_once_with(name="chrome", force=True)


# ── Menu Inspect ──────────────────────────────────────────────────────


class TestMenuInspect:

    def test_inspect_returns_menu_tree(self, server, mock_backend):
        result = _call_tool(server, "menu_inspect", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert len(data["menu_items"]) == 2
        file_menu = data["menu_items"][0]
        assert file_menu["name"] == "File"
        assert len(file_menu["children"]) == 3
        assert file_menu["children"][0]["shortcut"] == "Ctrl+N"

    def test_inspect_with_app_filter(self, server, mock_backend):
        result = _call_tool(server, "menu_inspect", {"app": "notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.get_menu_items.assert_called_once_with(window_title="notepad")

    def test_inspect_disabled_item(self, server, mock_backend):
        result = _call_tool(server, "menu_inspect", {})
        data = json.loads(result[0].text)
        save_item = data["menu_items"][0]["children"][2]
        assert save_item["name"] == "Save"
        assert save_item["enabled"] is False

    def test_inspect_empty_menu(self, server, mock_backend):
        mock_backend.get_menu_items.return_value = []
        result = _call_tool(server, "menu_inspect", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["menu_items"] == []
