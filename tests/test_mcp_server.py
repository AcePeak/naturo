"""Tests for MCP server tool definitions and input validation.

Tests server creation, tool registration, and input validation logic
that runs on all platforms (no Windows backend required).
Functional tests that call real backends are Windows-only.
"""

from __future__ import annotations

import json
import platform
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Skip entire module if mcp dependency is missing
mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


@pytest.fixture
def server():
    """Create an MCP server instance."""
    return create_server()


@pytest.fixture
def tools(server):
    """Get tool list from server."""
    return {t.name: t for t in server._tool_manager.list_tools()}


# 鈹€鈹€ Server Creation 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


class TestServerCreation:
    """MCP server creates correctly with all tools registered."""

    def test_server_name(self, server):
        assert server.name == "naturo"

    def test_server_version_is_naturo_version(self, server):
        """#873: serverInfo.version must be naturo's version, not the mcp SDK's.

        FastMCP does not forward a ``version=`` argument to its low-level
        ``Server``; left unset, the initialize handshake reports the installed
        ``mcp`` package version (e.g. ``1.26.0``) instead of naturo's own
        version, breaking client-side capability detection.  The reported
        ``server_version`` is exactly what populates ``serverInfo.version`` in
        the initialize response.
        """
        from naturo import __version__

        init_options = server._mcp_server.create_initialization_options()
        assert init_options.server_version == __version__
        assert init_options.server_name == "naturo"

    def test_server_has_tools(self, tools):
        assert len(tools) >= 20

    def test_expected_tools_registered(self, tools):
        expected = [
            "capture_screen", "capture_window",
            "list_windows", "focus_window",
            "window_close", "window_minimize", "window_maximize",
            "window_restore", "window_move", "window_resize", "window_set_bounds",
            "app_hide", "app_unhide", "app_switch",
            "see_ui_tree", "find_element",
            "click", "type_text", "press_key", "hotkey",
            "scroll", "drag", "move_mouse",
            "list_apps", "launch_app", "quit_app",
            "menu_inspect",
            "wait_for_element", "wait_for_window", "wait_until_gone",
            "clipboard_get", "clipboard_set", "clipboard_clear", "clipboard_info",
        ]
        for name in expected:
            assert name in tools, f"Tool '{name}' not registered"

    def test_all_tools_have_descriptions(self, tools):
        for name, tool in tools.items():
            assert tool.description, f"Tool '{name}' has no description"

    def test_server_respects_host_port(self):
        """BUG-041: host/port must be passed to FastMCP constructor."""
        srv = create_server(host="0.0.0.0", port=9999)
        assert srv.settings.host == "0.0.0.0"
        assert srv.settings.port == 9999

    def test_server_default_host_port(self):
        """Default host/port should be localhost:3100."""
        srv = create_server()
        assert srv.settings.host == "localhost"
        assert srv.settings.port == 3100


# 鈹€鈹€ Input Validation (pure logic, no backend needed) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


# 鈹€鈹€ Tool Function Unit Tests (with mocked backend) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


class TestToolFunctionsWithMockedBackend:
    """Test tool functions by mocking the backend."""

    @pytest.fixture
    def mock_backend(self):
        """Create a comprehensive mock backend."""
        backend = MagicMock()
        # Setup return values for common methods
        # No focused ValuePattern control by default → type_text uses keystroke
        # injection (the asserted path); the IME-immune ValuePattern path (#1219)
        # is covered in tests/test_mcp_input.py.
        backend.set_focused_element_value.return_value = False
        backend.list_windows.return_value = []
        backend.list_apps.return_value = []
        backend.clipboard_get.return_value = "test"
        backend.get_menu_items.return_value = []
        backend.find_element.return_value = None
        backend.get_element_tree.return_value = None
        return backend

    @pytest.fixture
    def patched_server(self, mock_backend):
        """Create server with patched backend."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            yield srv, mock_backend

    def _call_tool(self, server, tool_name: str, arguments: dict):
        """Helper to call a tool function by name.

        Tools are registered via @server.tool() decorator,
        so we access them through the tool manager.
        """
        import asyncio

        async def _run():
            result = await server.call_tool(tool_name, arguments)
            return result

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()

    def test_list_windows_empty(self, mock_backend):
        """list_windows returns empty list when no windows."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "list_windows", {})
            # Result is a list of TextContent
            assert len(result) > 0
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["windows"] == []

    def test_list_windows_with_data(self, mock_backend):
        """list_windows returns window data correctly."""
        mock_win = MagicMock()
        mock_win.handle = 12345
        mock_win.title = "Test Window"
        mock_win.process_name = "test.exe"
        mock_win.pid = 100
        mock_win.x = 0
        mock_win.y = 0
        mock_win.width = 800
        mock_win.height = 600
        mock_win.is_visible = True
        mock_win.is_minimized = False
        mock_backend.list_windows.return_value = [mock_win]

        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "list_windows", {})
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert len(data["windows"]) == 1
            assert data["windows"][0]["title"] == "Test Window"
            assert data["windows"][0]["pid"] == 100

    def test_focus_window(self, mock_backend):
        """focus_window calls backend correctly."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "focus_window", {"title": "Notepad"})
            data = json.loads(result[0].text)
            assert data["success"] is True
            mock_backend.focus_window.assert_called_once_with(title="Notepad", hwnd=None)

    def test_close_window(self, mock_backend):
        """window_close calls backend correctly."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "window_close", {"title": "Notepad"})
            data = json.loads(result[0].text)
            assert data["success"] is True
            mock_backend.close_window.assert_called_once_with(title="Notepad", hwnd=None, force=False)

    def test_click_with_coords(self, mock_backend):
        """click with coordinates."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "click", {"x": 100, "y": 200})
            data = json.loads(result[0].text)
            assert data["success"] is True
            mock_backend.click.assert_called_once()

    def test_type_text_valid(self, mock_backend):
        """type_text passes wpm to the keystroke fallback (profile='human' so
        wpm is actually honored). Force that path by making paste unavailable."""
        mock_backend.set_focused_element_value.return_value = False
        mock_backend.clipboard_set.side_effect = RuntimeError("no clipboard")
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "type_text", {"text": "hello", "wpm": 60})
            data = json.loads(result[0].text)
            assert data["success"] is True
            mock_backend.type_text.assert_called_once_with(
                text="hello", wpm=60, input_mode="normal", profile="human")

    def test_type_text_invalid_wpm(self, mock_backend):
        """type_text with wpm=0 returns validation error."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "type_text", {"text": "hello", "wpm": 0})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"
            mock_backend.type_text.assert_not_called()

    def test_type_text_negative_wpm(self, mock_backend):
        """type_text with wpm=-1 returns validation error."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "type_text", {"text": "hello", "wpm": -1})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert "wpm" in data["error"]["message"]

    def test_press_key_valid(self, mock_backend):
        """press_key with valid count."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "press_key", {"key": "enter", "count": 3})
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert mock_backend.press_key.call_count == 3

    def test_press_key_invalid_count(self, mock_backend):
        """press_key with count=0 returns validation error."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "press_key", {"key": "enter", "count": 0})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"

    def test_scroll_valid(self, mock_backend):
        """scroll with valid amount."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "scroll", {"direction": "down", "amount": 5})
            data = json.loads(result[0].text)
            assert data["success"] is True

    def test_scroll_invalid_amount(self, mock_backend):
        """scroll with amount=0 returns validation error."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "scroll", {"amount": 0})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"

    def test_drag_valid(self, mock_backend):
        """drag with valid parameters."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "drag", {
                "from_x": 100, "from_y": 100,
                "to_x": 200, "to_y": 200,
            })
            data = json.loads(result[0].text)
            assert data["success"] is True

    def test_drag_invalid_steps(self, mock_backend):
        """drag with steps=0 returns validation error."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "drag", {
                "from_x": 100, "from_y": 100,
                "to_x": 200, "to_y": 200,
                "steps": 0,
            })
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert "steps" in data["error"]["message"]

    def test_drag_negative_duration(self, mock_backend):
        """drag with duration_ms=-1 returns validation error."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "drag", {
                "from_x": 100, "from_y": 100,
                "to_x": 200, "to_y": 200,
                "duration_ms": -1,
            })
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert "duration" in data["error"]["message"]

    def test_see_ui_tree_invalid_depth_zero(self, mock_backend):
        """see_ui_tree with depth=0 returns validation error."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "see_ui_tree", {"depth": 0})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"
            assert "depth" in data["error"]["message"]

    def test_see_ui_tree_invalid_depth_eleven(self, mock_backend):
        """see_ui_tree with depth=11 returns validation error."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "see_ui_tree", {"depth": 11})
            data = json.loads(result[0].text)
            assert data["success"] is False

    def test_see_ui_tree_no_window(self, mock_backend):
        """see_ui_tree returns WINDOW_NOT_FOUND when no matching window."""
        mock_backend.get_element_tree.return_value = None
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "see_ui_tree", {"depth": 3})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "WINDOW_NOT_FOUND"

    def test_find_element_not_found(self, mock_backend):
        """find_element returns error when element not found."""
        mock_backend.find_element.return_value = None
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "find_element", {"selector": "Button:NonExist"})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "ELEMENT_NOT_FOUND"

    def test_find_element_found(self, mock_backend):
        """find_element returns element data when found."""
        mock_el = MagicMock()
        mock_el.id = "el_1"
        mock_el.role = "Button"
        mock_el.name = "Save"
        mock_el.value = ""
        mock_el.x = 10
        mock_el.y = 20
        mock_el.width = 80
        mock_el.height = 30
        mock_el.properties = {"enabled": True}
        mock_backend.find_element.return_value = mock_el

        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "find_element", {"selector": "Button:Save"})
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["element"]["role"] == "Button"
            assert data["element"]["name"] == "Save"
            assert data["element"]["bounds"]["x"] == 10

    def test_list_apps(self, mock_backend):
        """list_apps returns app list."""
        mock_backend.list_apps.return_value = [{"name": "notepad.exe", "pid": 1234}]
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "list_apps", {})
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert len(data["apps"]) == 1

    def test_launch_app(self, mock_backend):
        """launch_app returns PID and process info (#575)."""
        from naturo.process import ProcessInfo

        mock_info = ProcessInfo(pid=12345, name="notepad", path="C:\\Windows\\notepad.exe", is_running=True, window_count=1)
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend), \
             patch("naturo.mcp_server._launch_app", return_value=mock_info) as mock_launch:
            srv = create_server()
            result = self._call_tool(srv, "launch_app", {"name": "notepad"})
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["pid"] == 12345
            assert data["name"] == "notepad"
            mock_launch.assert_called_once_with(name="notepad")

    def test_quit_app(self, mock_backend):
        """quit_app calls backend."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "quit_app", {"name": "notepad", "force": True})
            data = json.loads(result[0].text)
            assert data["success"] is True
            mock_backend.quit_app.assert_called_once_with(name="notepad", force=True)

    def test_move_mouse(self, mock_backend):
        """move_mouse calls backend."""
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "move_mouse", {"x": 500, "y": 300})
            data = json.loads(result[0].text)
            assert data["success"] is True
            mock_backend.move_mouse.assert_called_once_with(x=500, y=300)

    def test_menu_inspect_empty(self, mock_backend):
        """menu_inspect returns empty list."""
        mock_backend.get_menu_items.return_value = []
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "menu_inspect", {})
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["menu_items"] == []

class TestWaitTools:
    """Test wait_for_element, wait_for_window, wait_until_gone tools."""

    def _call_tool(self, server, tool_name: str, arguments: dict):
        import asyncio
        async def _run():
            return await server.call_tool(tool_name, arguments)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()

    def test_wait_for_element_invalid_timeout(self):
        """wait_for_element with negative timeout returns error."""
        mock_backend = MagicMock()
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "wait_for_element", {
                "selector": "Button:Save", "timeout": -1,
            })
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"

    def test_wait_for_element_invalid_interval(self):
        """wait_for_element with interval=0 returns error."""
        mock_backend = MagicMock()
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "wait_for_element", {
                "selector": "Button:Save", "interval": 0,
            })
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"

    def test_wait_for_element_timeout(self):
        """wait_for_element returns timeout when element not found."""
        mock_backend = MagicMock()
        mock_backend.find_element.return_value = None
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "wait_for_element", {
                "selector": "Button:NonExist", "timeout": 0.1, "interval": 0.05,
            })
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["found"] is False
            assert data["error"]["code"] == "TIMEOUT"

    def test_wait_for_element_found(self):
        """wait_for_element returns element when found."""
        mock_backend = MagicMock()
        mock_el = MagicMock()
        mock_el.id = "el_1"
        mock_el.role = "Button"
        mock_el.name = "Save"
        mock_el.x = 10
        mock_el.y = 20
        mock_el.width = 80
        mock_el.height = 30
        mock_backend.find_element.return_value = mock_el
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "wait_for_element", {
                "selector": "Button:Save", "timeout": 5, "interval": 0.1,
            })
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["found"] is True
            assert data["element"]["name"] == "Save"
            assert "wait_time" in data

    def test_wait_for_window_invalid_timeout(self):
        """wait_for_window with negative timeout returns error."""
        mock_backend = MagicMock()
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "wait_for_window", {
                "title": "Notepad", "timeout": -1,
            })
            data = json.loads(result[0].text)
            assert data["success"] is False

    def test_wait_for_window_timeout(self):
        """wait_for_window returns timeout."""
        mock_backend = MagicMock()
        mock_backend.list_windows.return_value = []
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "wait_for_window", {
                "title": "NonExist", "timeout": 0.1, "interval": 0.05,
            })
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "TIMEOUT"

    def test_wait_until_gone_invalid_interval(self):
        """wait_until_gone with interval=0 returns error."""
        mock_backend = MagicMock()
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "wait_until_gone", {
                "selector": "Dialog:Loading", "interval": 0,
            })
            data = json.loads(result[0].text)
            assert data["success"] is False

    def test_wait_until_gone_success(self):
        """wait_until_gone returns success when element disappears."""
        mock_backend = MagicMock()
        mock_backend.find_element.return_value = None  # already gone
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "wait_until_gone", {
                "selector": "Dialog:Loading", "timeout": 1, "interval": 0.1,
            })
            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["gone"] is True


# 鈹€鈹€ CLI Integration 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


class TestMCPCli:
    """Test MCP CLI commands."""

    @pytest.fixture
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    def test_mcp_group_in_help(self, runner):
        """mcp command group should be hidden but callable."""
        from naturo.cli import main
        # mcp is hidden, but should still work when called directly
        result = runner.invoke(main, ["mcp", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "tools" in result.output

    def test_mcp_tools_list(self, runner):
        """naturo mcp tools lists available tools."""
        from naturo.cli import main
        result = runner.invoke(main, ["mcp", "tools"])
        assert result.exit_code == 0
        assert "capture_screen" in result.output
        assert "click" in result.output

    def test_mcp_tools_json(self, runner):
        """naturo mcp tools --json outputs valid JSON."""
        from naturo.cli import main
        result = runner.invoke(main, ["mcp", "tools", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert len(data["tools"]) >= 23

    def test_mcp_start_help(self, runner):
        """naturo mcp start --help shows transport options."""
        from naturo.cli import main
        result = runner.invoke(main, ["mcp", "start", "--help"])
        assert result.exit_code == 0
        assert "stdio" in result.output
        assert "sse" in result.output

    def test_mcp_install_json_no_text_prefix(self, runner):
        """BUG-042: mcp install --json must not output text before JSON."""
        from naturo.cli import main
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = runner.invoke(main, ["mcp", "install", "--json"])
        output = result.output.strip()
        assert not output.startswith("Installing"), f"Text prefix leaked into JSON output: {output[:80]}"
        data = json.loads(output)
        assert data["success"] is True

    def test_mcp_install_no_json_shows_progress(self, runner):
        """Non-JSON mcp install should show progress text."""
        from naturo.cli import main
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = runner.invoke(main, ["mcp", "install"])
        assert "Installing MCP dependencies" in result.output

    def test_mcp_start_stdio_suppresses_logging(self, runner):
        """#810: stdio transport must suppress all logging to avoid corrupting JSON-RPC."""
        import logging

        with patch("naturo.mcp_server.run_server") as mock_run:
            from naturo.cli import main
            result = runner.invoke(main, ["mcp", "start", "--transport", "stdio"])

        mock_run.assert_called_once_with(transport="stdio", host="localhost", port=3100)
        # Root logger should have been configured to suppress output
        root = logging.getLogger()
        assert root.level >= logging.CRITICAL
        assert any(isinstance(h, logging.NullHandler) for h in root.handlers)

    def test_mcp_start_stdio_no_stdout_pollution(self, runner):
        """#810: MCP start with stdio must produce no text output on stdout."""
        with patch("naturo.mcp_server.run_server"):
            from naturo.cli import main
            result = runner.invoke(main, ["mcp", "start", "--transport", "stdio"])

        assert result.output == "", f"Unexpected stdout output: {result.output!r}"


# 鈹€鈹€ Response Format Consistency 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


class TestResponseFormat:
    """All tool responses follow consistent JSON schema."""

    def _call_tool(self, server, tool_name: str, arguments: dict):
        import asyncio
        async def _run():
            return await server.call_tool(tool_name, arguments)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()

    def test_error_responses_have_error_object(self):
        """All validation error responses include error.code and error.message."""
        mock_backend = MagicMock()

        error_cases = [
            ("type_text", {"text": "x", "wpm": 0}),
            ("press_key", {"key": "a", "count": 0}),
            ("scroll", {"amount": 0}),
            ("drag", {"from_x": 0, "from_y": 0, "to_x": 1, "to_y": 1, "steps": 0}),
            ("drag", {"from_x": 0, "from_y": 0, "to_x": 1, "to_y": 1, "duration_ms": -1}),
            ("see_ui_tree", {"depth": 0}),
            ("see_ui_tree", {"depth": 11}),
        ]

        for tool_name, args in error_cases:
            with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
                srv = create_server()
                result = self._call_tool(srv, tool_name, args)
                data = json.loads(result[0].text)
                assert data.get("success") is False, f"{tool_name}({args}) should fail"
                assert "error" in data, f"{tool_name}({args}) missing error object"
                assert "code" in data["error"], f"{tool_name}({args}) missing error.code"
                assert "message" in data["error"], f"{tool_name}({args}) missing error.message"


class TestStdioLogging:
    """#810: MCP stdio transport must not emit debug text to stdout."""

    def test_suppress_stdout_logging(self):
        """_suppress_stdout_logging redirects stdout handlers to stderr."""
        import logging
        import sys

        from naturo.mcp_server import _suppress_stdout_logging

        root = logging.getLogger()
        stdout_handler = logging.StreamHandler(sys.stdout)
        root.addHandler(stdout_handler)
        try:
            _suppress_stdout_logging()
            assert stdout_handler.stream is sys.stderr
        finally:
            root.removeHandler(stdout_handler)


# 鈹€鈹€ Pydantic ValidationError leak (#844) 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€


class TestValidationErrorSanitization:
    """#844: MCP tool validation errors must not leak Pydantic internals."""

    def _call_tool(self, srv, name, args):
        import asyncio

        async def _run():
            return await srv.call_tool(name, args)

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()

    def test_validation_error_returns_invalid_input(self):
        """Pydantic-style ValidationError returns INVALID_INPUT, not INTERNAL_ERROR."""
        # The _is_validation_error check uses type(exc).__name__ == "ValidationError"
        # so we must name our class accordingly.
        class ValidationError(Exception):
            def errors(self):
                return [
                    {"loc": ("body", "x"), "msg": "value is not a valid integer", "type": "type_error.integer"},
                    {"loc": ("body", "y"), "msg": "field required", "type": "value_error.missing"},
                ]

        mock_backend = MagicMock()
        mock_backend.capture_screen.side_effect = ValidationError("2 validation errors")

        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "capture_screen", {})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"
            assert "body" in data["error"]["message"]
            assert "x" in data["error"]["message"]
            # Must NOT contain internal type info
            assert "type_error.integer" not in data["error"]["message"]
            assert "value_error.missing" not in data["error"]["message"]

    def test_validation_error_fallback_on_broken_errors_method(self):
        """If .errors() itself fails, still returns INVALID_INPUT safely."""
        class ValidationError(Exception):
            def errors(self):
                raise RuntimeError("errors() broke")

        mock_backend = MagicMock()
        mock_backend.capture_screen.side_effect = ValidationError("bad")

        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "capture_screen", {})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INVALID_INPUT"
            assert "invalid input" in data["error"]["message"].lower() or "validation" in data["error"]["message"].lower()

    def test_regular_exception_still_returns_internal_error(self):
        """Non-validation exceptions still return INTERNAL_ERROR."""
        mock_backend = MagicMock()
        mock_backend.capture_screen.side_effect = RuntimeError("disk full")

        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = self._call_tool(srv, "capture_screen", {})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INTERNAL_ERROR"
            assert "disk full" in data["error"]["message"]
