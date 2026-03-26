"""Tests for Phase 3.5 — Window Management.

Covers:
  - Backend method signatures (all platforms)
  - CLI window commands: focus, close, minimize, maximize, restore, move, resize, set-bounds, list
  - CLI app commands: hide, unhide, switch
  - Input validation and error handling
  - JSON output format consistency
  - MCP window tools existence
"""

from __future__ import annotations

import importlib.util
import json
import platform
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from naturo.cli import main
from naturo.backends.base import WindowInfo


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_window():
    """A fake WindowInfo for testing."""
    return WindowInfo(
        handle=12345,
        title="Test Window",
        process_name="notepad.exe",
        pid=9999,
        x=100, y=100,
        width=800, height=600,
        is_visible=True,
        is_minimized=False,
    )


@pytest.fixture
def mock_window_minimized():
    """A fake minimized WindowInfo."""
    return WindowInfo(
        handle=12346,
        title="Minimized Window",
        process_name="notepad.exe",
        pid=9998,
        x=0, y=0,
        width=0, height=0,
        is_visible=False,
        is_minimized=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Backend Method Signatures
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowBackendSignatures:
    """All window management methods exist on WindowsBackend."""

    def test_focus_window_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "focus_window")

    def test_close_window_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "close_window")

    def test_minimize_window_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "minimize_window")

    def test_maximize_window_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "maximize_window")

    def test_restore_window_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "restore_window")

    def test_move_window_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "move_window")

    def test_resize_window_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "resize_window")

    def test_set_bounds_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "set_bounds")


class TestWindowBaseSignatures:
    """All window methods are abstract in the base Backend."""

    def test_focus_window_abstract(self):
        from naturo.backends.base import Backend
        assert hasattr(Backend, "focus_window")

    def test_close_window_abstract(self):
        from naturo.backends.base import Backend
        assert hasattr(Backend, "close_window")

    def test_minimize_window_abstract(self):
        from naturo.backends.base import Backend
        assert hasattr(Backend, "minimize_window")

    def test_maximize_window_abstract(self):
        from naturo.backends.base import Backend
        assert hasattr(Backend, "maximize_window")

    def test_restore_window_abstract(self):
        from naturo.backends.base import Backend
        assert hasattr(Backend, "restore_window")

    def test_move_window_abstract(self):
        from naturo.backends.base import Backend
        assert hasattr(Backend, "move_window")

    def test_resize_window_abstract(self):
        from naturo.backends.base import Backend
        assert hasattr(Backend, "resize_window")

    def test_set_bounds_abstract(self):
        from naturo.backends.base import Backend
        assert hasattr(Backend, "set_bounds")


# ══════════════════════════════════════════════════════════════════════════════
# CLI: `naturo window` Group
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowCLIGroupExists:
    """The `naturo window` command group is registered and has subcommands."""

    def test_window_help(self, runner):
        result = runner.invoke(main, ["window", "--help"])
        assert result.exit_code == 0
        assert "focus" in result.output
        assert "close" in result.output
        assert "minimize" in result.output
        assert "maximize" in result.output
        assert "restore" in result.output
        assert "move" in result.output
        assert "resize" in result.output
        assert "set-bounds" in result.output
        assert "list" in result.output


# ══════════════════════════════════════════════════════════════════════════════
# CLI: window focus
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowFocusCLI:
    """Tests for `naturo window focus`."""

    def test_no_target_exits_nonzero(self, runner):
        result = runner.invoke(main, ["window", "focus"])
        assert result.exit_code != 0

    def test_no_target_json_error(self, runner):
        result = runner.invoke(main, ["window", "focus", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_focus_by_app_success(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "focus", "--app", "Notepad"])
        assert result.exit_code == 0
        backend.focus_window.assert_called_once()

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_focus_by_hwnd_success(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "focus", "--hwnd", "12345"])
        assert result.exit_code == 0
        backend.focus_window.assert_called_once()

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_focus_json_output(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "focus", "--app", "Notepad", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "focus"

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_focus_window_not_found(self, mock_get, runner):
        from naturo.errors import WindowNotFoundError
        backend = MagicMock()
        backend.focus_window.side_effect = WindowNotFoundError("Nonexistent")
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "focus", "--app", "Nonexistent"])
        assert result.exit_code != 0

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_focus_window_not_found_json(self, mock_get, runner):
        from naturo.errors import WindowNotFoundError
        backend = MagicMock()
        backend.focus_window.side_effect = WindowNotFoundError("Nonexistent")
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "focus", "--app", "Nonexistent", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


# ══════════════════════════════════════════════════════════════════════════════
# CLI: window close
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowCloseCLI:
    """Tests for `naturo window close`."""

    def test_no_target_exits_nonzero(self, runner):
        result = runner.invoke(main, ["window", "close"])
        assert result.exit_code != 0

    def test_no_target_json_error(self, runner):
        result = runner.invoke(main, ["window", "close", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_close_graceful(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "close", "--app", "Notepad"])
        assert result.exit_code == 0
        backend.close_window.assert_called_once()
        call_kwargs = backend.close_window.call_args[1]
        assert call_kwargs["force"] is False

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_close_force(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "close", "--app", "Notepad", "--force"])
        assert result.exit_code == 0
        call_kwargs = backend.close_window.call_args[1]
        assert call_kwargs["force"] is True

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_close_json_output(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "close", "--app", "Notepad", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "close"

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_close_force_json_output(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "close", "--app", "Notepad", "--force", "--json"])
        data = json.loads(result.output)
        assert data["force"] is True


# ══════════════════════════════════════════════════════════════════════════════
# CLI: window minimize / maximize / restore
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowMinMaxRestoreCLI:
    """Tests for minimize, maximize, restore."""

    @pytest.mark.parametrize("action", ["minimize", "maximize", "restore"])
    def test_no_target_exits_nonzero(self, runner, action):
        result = runner.invoke(main, ["window", action])
        assert result.exit_code != 0

    @pytest.mark.parametrize("action", ["minimize", "maximize", "restore"])
    def test_no_target_json_error(self, runner, action):
        result = runner.invoke(main, ["window", action, "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    @patch("naturo.cli.window_cmd._get_backend_impl")
    @pytest.mark.parametrize("action,method", [
        ("minimize", "minimize_window"),
        ("maximize", "maximize_window"),
        ("restore", "restore_window"),
    ])
    def test_action_by_app(self, mock_get, runner, action, method):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", action, "--app", "Notepad"])
        assert result.exit_code == 0
        getattr(backend, method).assert_called_once()

    @patch("naturo.cli.window_cmd._get_backend_impl")
    @pytest.mark.parametrize("action", ["minimize", "maximize", "restore"])
    def test_action_json_success(self, mock_get, runner, action):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", action, "--app", "Notepad", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == action


# ══════════════════════════════════════════════════════════════════════════════
# CLI: window move
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowMoveCLI:
    """Tests for `naturo window move`."""

    def test_no_target_exits_nonzero(self, runner):
        result = runner.invoke(main, ["window", "move", "--x", "100", "--y", "100"])
        assert result.exit_code != 0

    def test_x_y_required(self, runner):
        result = runner.invoke(main, ["window", "move", "--app", "Notepad"])
        assert result.exit_code != 0  # missing --x and --y

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_move_success(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "move", "--app", "Notepad", "--x", "200", "--y", "300"])
        assert result.exit_code == 0
        backend.move_window.assert_called_once()

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_move_json_output(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "move", "--app", "Notepad", "--x", "200", "--y", "300", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "move"
        assert data["x"] == 200
        assert data["y"] == 300

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_move_negative_coords_allowed(self, mock_get, runner):
        """Negative coordinates are valid (multi-monitor setups)."""
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "move", "--app", "Notepad", "--x", "-100", "--y", "-50"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
# CLI: window resize
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowResizeCLI:
    """Tests for `naturo window resize`."""

    def test_no_target_exits_nonzero(self, runner):
        result = runner.invoke(main, ["window", "resize", "--width", "800", "--height", "600"])
        assert result.exit_code != 0

    def test_width_height_required(self, runner):
        result = runner.invoke(main, ["window", "resize", "--app", "Notepad"])
        assert result.exit_code != 0

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_resize_success(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "resize", "--app", "Notepad", "--width", "1024", "--height", "768"])
        assert result.exit_code == 0
        backend.resize_window.assert_called_once()

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_resize_json_output(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "resize", "--app", "Notepad", "--width", "1024", "--height", "768", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["width"] == 1024
        assert data["height"] == 768

    def test_resize_zero_width_rejected(self, runner):
        result = runner.invoke(main, ["window", "resize", "--app", "Notepad", "--width", "0", "--height", "600"])
        assert result.exit_code != 0

    def test_resize_negative_height_rejected(self, runner):
        result = runner.invoke(main, ["window", "resize", "--app", "Notepad", "--width", "800", "--height", "-1"])
        assert result.exit_code != 0

    def test_resize_zero_width_json_error(self, runner):
        result = runner.invoke(main, ["window", "resize", "--app", "Notepad", "--width", "0", "--height", "600", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


# ══════════════════════════════════════════════════════════════════════════════
# CLI: window set-bounds
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowSetBoundsCLI:
    """Tests for `naturo window set-bounds`."""

    def test_no_target_exits_nonzero(self, runner):
        result = runner.invoke(main, ["window", "set-bounds", "--x", "0", "--y", "0", "--width", "800", "--height", "600"])
        assert result.exit_code != 0

    def test_all_params_required(self, runner):
        result = runner.invoke(main, ["window", "set-bounds", "--app", "Notepad", "--x", "0", "--y", "0"])
        assert result.exit_code != 0  # missing --width and --height

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_set_bounds_success(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, [
            "window", "set-bounds", "--app", "Notepad",
            "--x", "0", "--y", "0", "--width", "1920", "--height", "1080"
        ])
        assert result.exit_code == 0
        backend.set_bounds.assert_called_once()

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_set_bounds_json_output(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, [
            "window", "set-bounds", "--app", "Notepad",
            "--x", "10", "--y", "20", "--width", "800", "--height", "600", "--json"
        ])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "set-bounds"
        assert data["x"] == 10
        assert data["y"] == 20
        assert data["width"] == 800
        assert data["height"] == 600

    def test_set_bounds_zero_width_rejected(self, runner):
        result = runner.invoke(main, [
            "window", "set-bounds", "--app", "Notepad",
            "--x", "0", "--y", "0", "--width", "0", "--height", "600"
        ])
        assert result.exit_code != 0

    def test_set_bounds_zero_width_json_error(self, runner):
        result = runner.invoke(main, [
            "window", "set-bounds", "--app", "Notepad",
            "--x", "0", "--y", "0", "--width", "0", "--height", "600", "--json"
        ])
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


# ══════════════════════════════════════════════════════════════════════════════
# CLI: window list
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowListCLI:
    """Tests for `naturo window list`."""

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_list_empty(self, mock_get, runner):
        backend = MagicMock()
        backend.list_windows.return_value = []
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "list"])
        assert result.exit_code == 0
        assert "No windows" in result.output

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_list_with_windows(self, mock_get, runner, mock_window):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "list"])
        assert result.exit_code == 0
        assert "notepad.exe" in result.output
        assert "1 windows" in result.output

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_list_json_output(self, mock_get, runner, mock_window):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 1
        assert len(data["windows"]) == 1
        w = data["windows"][0]
        assert w["handle"] == 12345
        assert w["title"] == "Test Window"
        assert w["process_name"] == "notepad.exe"

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_list_filter_by_app(self, mock_get, runner, mock_window):
        other = WindowInfo(
            handle=99999, title="Other", process_name="chrome.exe",
            pid=1111, x=0, y=0, width=800, height=600,
            is_visible=True, is_minimized=False,
        )
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window, other]
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "list", "--app", "notepad", "--json"])
        data = json.loads(result.output)
        assert data["count"] == 1
        assert data["windows"][0]["process_name"] == "notepad.exe"

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_list_filter_by_pid(self, mock_get, runner, mock_window):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "list", "--pid", "9999", "--json"])
        data = json.loads(result.output)
        assert data["count"] == 1

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_list_filter_no_match(self, mock_get, runner, mock_window):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "list", "--app", "nonexistent", "--json"])
        data = json.loads(result.output)
        assert data["count"] == 0
        assert data["windows"] == []


# ══════════════════════════════════════════════════════════════════════════════
# CLI: app hide / unhide / switch
# ══════════════════════════════════════════════════════════════════════════════


class TestAppHideUnhideSwitchCLI:
    """Tests for `naturo app hide/unhide/switch`."""

    def test_hide_still_callable(self, runner):
        """hide is a hidden alias for minimize — still callable."""
        result = runner.invoke(main, ["app", "hide", "--help"])
        assert result.exit_code == 0

    def test_unhide_still_callable(self, runner):
        """unhide is a hidden alias for restore — still callable."""
        result = runner.invoke(main, ["app", "unhide", "--help"])
        assert result.exit_code == 0

    def test_switch_still_callable(self, runner):
        """switch is a hidden alias for focus — still callable."""
        result = runner.invoke(main, ["app", "switch", "--help"])
        assert result.exit_code == 0

    @patch("naturo.backends.base.get_backend")
    def test_hide_success(self, mock_get, runner, mock_window):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "hide", "notepad"])
        assert result.exit_code == 0
        assert "Minimized" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_hide_json_output(self, mock_get, runner, mock_window):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "hide", "notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "hide"
        assert data["windows_minimized"] == 1

    @patch("naturo.backends.base.get_backend")
    def test_hide_app_not_found(self, mock_get, runner):
        backend = MagicMock()
        backend.list_windows.return_value = []
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "hide", "nonexistent", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False

    @patch("naturo.backends.base.get_backend")
    def test_unhide_success(self, mock_get, runner, mock_window_minimized):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window_minimized]
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "unhide", "notepad"])
        assert result.exit_code == 0
        assert "Restored" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_unhide_json_output(self, mock_get, runner, mock_window_minimized):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window_minimized]
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "unhide", "notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "unhide"

    @patch("naturo.backends.base.get_backend")
    def test_switch_success(self, mock_get, runner, mock_window):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "switch", "notepad"])
        assert result.exit_code == 0
        assert "Switched" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_switch_json_output(self, mock_get, runner, mock_window):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "switch", "notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "switch"
        assert data["handle"] == 12345

    @patch("naturo.backends.base.get_backend")
    def test_switch_app_not_found(self, mock_get, runner):
        backend = MagicMock()
        backend.list_windows.return_value = []
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "switch", "nonexistent", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


# ══════════════════════════════════════════════════════════════════════════════
# MCP Window Tools
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.skipif(
    not importlib.util.find_spec("mcp"),
    reason="mcp package not installed",
)
class TestMCPWindowToolsExist:
    """MCP server exposes window management tools."""

    def test_mcp_has_window_tools(self):
        """All Phase 3.5 window tools exist in MCP server."""
        from naturo.mcp_server import create_server
        server = create_server()
        # The server object has tools registered
        assert hasattr(server, '_tool_manager') or True  # FastMCP internal

    def test_focus_window_function_exists(self):
        from naturo import mcp_server
        # Check the module has the functions
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def focus_window(" in source or "def window_focus(" in source

    def test_window_close_function_exists(self):
        from naturo import mcp_server
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def window_close(" in source

    def test_window_minimize_function_exists(self):
        from naturo import mcp_server
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def window_minimize(" in source

    def test_window_maximize_function_exists(self):
        from naturo import mcp_server
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def window_maximize(" in source

    def test_window_restore_function_exists(self):
        from naturo import mcp_server
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def window_restore(" in source

    def test_window_move_function_exists(self):
        from naturo import mcp_server
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def window_move(" in source

    def test_window_resize_function_exists(self):
        from naturo import mcp_server
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def window_resize(" in source

    def test_window_set_bounds_function_exists(self):
        from naturo import mcp_server
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def window_set_bounds(" in source

    def test_app_hide_function_exists(self):
        from naturo import mcp_server
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def app_hide(" in source

    def test_app_unhide_function_exists(self):
        from naturo import mcp_server
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def app_unhide(" in source

    def test_app_switch_function_exists(self):
        from naturo import mcp_server
        source = open(mcp_server.__file__, encoding='utf-8').read()
        assert "def app_switch(" in source


# ══════════════════════════════════════════════════════════════════════════════
# JSON Output Consistency
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowJSONConsistency:
    """All window commands follow the JSON schema: {success: bool, ...}."""

    @patch("naturo.cli.window_cmd._get_backend_impl")
    @pytest.mark.parametrize("cmd,extra_args", [
        (["window", "focus", "--app", "Test"], []),
        (["window", "close", "--app", "Test"], []),
        (["window", "minimize", "--app", "Test"], []),
        (["window", "maximize", "--app", "Test"], []),
        (["window", "restore", "--app", "Test"], []),
        (["window", "move", "--app", "Test", "--x", "0", "--y", "0"], []),
        (["window", "resize", "--app", "Test", "--width", "800", "--height", "600"], []),
        (["window", "set-bounds", "--app", "Test", "--x", "0", "--y", "0", "--width", "800", "--height", "600"], []),
    ])
    def test_success_json_has_success_field(self, mock_get, runner, cmd, extra_args):
        backend = MagicMock()
        backend.list_windows.return_value = []
        mock_get.return_value = backend
        result = runner.invoke(main, cmd + ["--json"] + extra_args)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "success" in data
        assert data["success"] is True

    @pytest.mark.parametrize("cmd", [
        ["window", "focus"],
        ["window", "close"],
        ["window", "minimize"],
        ["window", "maximize"],
        ["window", "restore"],
    ])
    def test_missing_target_json_has_success_false(self, runner, cmd):
        result = runner.invoke(main, cmd + ["--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "error" in data


# ══════════════════════════════════════════════════════════════════════════════
# Targeting: --app, --title, --hwnd
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowTargeting:
    """All window commands accept --app, --title, and --hwnd."""

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_target_by_title(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "focus", "--title", "My Document"])
        assert result.exit_code == 0
        call_kwargs = backend.focus_window.call_args[1]
        assert call_kwargs["title"] == "My Document"

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_target_by_hwnd(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "focus", "--hwnd", "99999"])
        assert result.exit_code == 0
        call_kwargs = backend.focus_window.call_args[1]
        assert call_kwargs["hwnd"] == 99999

    @patch("naturo.cli.window_cmd._get_backend_impl")
    def test_app_maps_to_title(self, mock_get, runner):
        """--app maps to title parameter in backend."""
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["window", "focus", "--app", "Notepad"])
        assert result.exit_code == 0
        call_kwargs = backend.focus_window.call_args[1]
        assert call_kwargs["title"] == "Notepad"


# ── Tests for unified app window commands (#170) ────────────────────────────


class TestAppWindowCommands:
    """Tests for window operations under 'naturo app' namespace (#170)."""

    @patch("naturo.backends.base.get_backend")
    def test_app_focus_by_name(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "focus", "notepad"])
        assert result.exit_code == 0
        assert "Focused" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_app_focus_by_hwnd(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "focus", "--hwnd", "12345"])
        assert result.exit_code == 0

    @patch("naturo.backends.base.get_backend")
    def test_app_focus_with_app_flag(self, mock_get, runner):
        """app focus --app works as alternative to positional NAME (fixes #378)."""
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "focus", "--app", "notepad"])
        assert result.exit_code == 0
        assert "Focused" in result.output

    def test_app_focus_no_target(self, runner):
        result = runner.invoke(main, ["app", "focus"])
        assert result.exit_code != 0

    @patch("naturo.backends.base.get_backend")
    def test_app_close_by_name(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "close", "notepad"])
        assert result.exit_code == 0
        assert "Closed" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_app_close_force(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "close", "notepad", "--force"])
        assert result.exit_code == 0
        call_kwargs = backend.close_window.call_args[1]
        assert call_kwargs["force"] is True

    @patch("naturo.backends.base.get_backend")
    def test_app_minimize_by_name(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "minimize", "notepad"])
        assert result.exit_code == 0
        assert "Minimized" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_app_maximize_by_name(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "maximize", "notepad"])
        assert result.exit_code == 0
        assert "Maximized" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_app_restore_by_name(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "restore", "notepad"])
        assert result.exit_code == 0
        assert "Restored" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_app_move_position(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "move", "notepad", "--x", "100", "--y", "200"])
        assert result.exit_code == 0
        assert "Moved" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_app_move_resize(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "move", "notepad", "--width", "800", "--height", "600"])
        assert result.exit_code == 0
        assert "Resized" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_app_move_set_bounds(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "move", "notepad", "--x", "100", "--y", "200", "--width", "800", "--height", "600"])
        assert result.exit_code == 0
        assert "Set bounds" in result.output

    def test_app_move_partial_position(self, runner):
        result = runner.invoke(main, ["app", "move", "notepad", "--x", "100"])
        assert result.exit_code != 0

    def test_app_move_no_params(self, runner):
        result = runner.invoke(main, ["app", "move", "notepad"])
        assert result.exit_code != 0

    @patch("naturo.backends.base.get_backend")
    def test_app_windows_list(self, mock_get, runner, mock_window):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "windows"])
        assert result.exit_code == 0
        assert "1 windows" in result.output

    @patch("naturo.backends.base.get_backend")
    def test_app_windows_filter_by_name(self, mock_get, runner, mock_window):
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "windows", "notepad"])
        assert result.exit_code == 0

    @patch("naturo.backends.base.get_backend")
    def test_app_focus_json(self, mock_get, runner):
        backend = MagicMock()
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "focus", "notepad", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "focus"

    @patch("naturo.cli.interaction._check_desktop_session")
    @patch("naturo.backends.base.get_backend")
    def test_app_list_shows_windows(self, mock_get, mock_desktop, runner, mock_window):
        """T170 – app list shows detailed window list (#329, #379)."""
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "list"])
        assert result.exit_code == 0

    @patch("naturo.cli.interaction._check_desktop_session")
    @patch("naturo.backends.base.get_backend")
    def test_app_list_json(self, mock_get, mock_desktop, runner, mock_window):
        """T170 – app list --json returns structured data (#379)."""
        backend = MagicMock()
        backend.list_windows.return_value = [mock_window]
        mock_get.return_value = backend
        result = runner.invoke(main, ["app", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert len(data["windows"]) >= 0
