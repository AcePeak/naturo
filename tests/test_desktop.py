"""Tests for virtual desktop management commands.

Phase 5A.3: Virtual Desktop (Windows 10/11).

Tests the CLI commands for listing, switching, creating, closing virtual desktops
and moving windows between desktops. Backend calls are mocked since virtual
desktop interaction requires a Windows desktop session with pyvda.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.errors import NaturoError


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_backend():
    """Mock backend with virtual desktop methods."""
    backend = MagicMock()
    backend.virtual_desktop_list.return_value = _sample_desktops()
    backend.virtual_desktop_switch.return_value = {"index": 1, "name": "Desktop 2"}
    backend.virtual_desktop_create.return_value = {
        "index": 2,
        "name": "Work",
        "id": "abc-123",
    }
    backend.virtual_desktop_close.return_value = {"index": 1, "name": "Desktop 2"}
    backend.virtual_desktop_move_window.return_value = {
        "hwnd": 12345,
        "target_desktop": 1,
        "target_name": "Desktop 2",
    }
    return backend


def _sample_desktops():
    """Sample virtual desktop list."""
    return [
        {"index": 0, "name": "Desktop 1", "is_current": True, "id": "id-0"},
        {"index": 1, "name": "Desktop 2", "is_current": False, "id": "id-1"},
    ]


# ── desktop list ────────────────────────────────


class TestDesktopList:
    """Tests for 'naturo desktop list'."""

    def test_list_text_output(self, runner, mock_backend):
        """List desktops in human-readable format."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "list"])
        assert result.exit_code == 0
        assert "Desktop 1" in result.output
        assert "[current]" in result.output
        assert "Desktop 2" in result.output

    def test_list_json_output(self, runner, mock_backend):
        """List desktops in JSON format."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 2
        assert len(data["desktops"]) == 2
        assert data["desktops"][0]["is_current"] is True

    def test_list_empty(self, runner, mock_backend):
        """Handle empty desktop list."""
        mock_backend.virtual_desktop_list.return_value = []
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "list"])
        assert result.exit_code == 0
        assert "No virtual desktops found" in result.output

    def test_list_empty_json(self, runner, mock_backend):
        """Handle empty desktop list in JSON mode."""
        mock_backend.virtual_desktop_list.return_value = []
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 0
        assert data["desktops"] == []

    def test_list_dependency_missing(self, runner, mock_backend):
        """Handle missing pyvda dependency."""
        mock_backend.virtual_desktop_list.side_effect = NaturoError(
            message="Virtual desktop support requires pyvda",
            code="DEPENDENCY_MISSING",
        )
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "list", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "DEPENDENCY_MISSING"

    def test_list_error_text(self, runner, mock_backend):
        """Handle error in text mode."""
        mock_backend.virtual_desktop_list.side_effect = NaturoError(
            message="Failed to enumerate",
            code="VIRTUAL_DESKTOP_ERROR",
        )
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "list"])
        assert result.exit_code != 0


# ── desktop switch ──────────────────────────────


class TestDesktopSwitch:
    """Tests for 'naturo desktop switch'."""

    def test_switch_text(self, runner, mock_backend):
        """Switch desktop with text output."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "switch", "1"])
        assert result.exit_code == 0
        assert "Switched to desktop 1" in result.output
        mock_backend.virtual_desktop_switch.assert_called_once_with(1)

    def test_switch_json(self, runner, mock_backend):
        """Switch desktop with JSON output."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "switch", "1", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["index"] == 1
        assert data["name"] == "Desktop 2"

    def test_switch_negative_index(self, runner, mock_backend):
        """Reject negative index."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "switch", "--json", "--", "-1"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_switch_out_of_range(self, runner, mock_backend):
        """Handle out-of-range index from backend."""
        mock_backend.virtual_desktop_switch.side_effect = NaturoError(
            message="Desktop index 5 out of range (0-1)",
            code="INVALID_INPUT",
        )
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "switch", "5", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "out of range" in data["error"]["message"]

    def test_switch_zero(self, runner, mock_backend):
        """Switch to index 0 is valid."""
        mock_backend.virtual_desktop_switch.return_value = {
            "index": 0,
            "name": "Desktop 1",
        }
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "switch", "0"])
        assert result.exit_code == 0
        mock_backend.virtual_desktop_switch.assert_called_once_with(0)


# ── desktop create ──────────────────────────────


class TestDesktopCreate:
    """Tests for 'naturo desktop create'."""

    def test_create_unnamed_text(self, runner, mock_backend):
        """Create desktop without name."""
        mock_backend.virtual_desktop_create.return_value = {
            "index": 2,
            "name": "Desktop 3",
            "id": "new-id",
        }
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "create"])
        assert result.exit_code == 0
        assert "Created desktop 2" in result.output
        mock_backend.virtual_desktop_create.assert_called_once_with(name=None)

    def test_create_named_json(self, runner, mock_backend):
        """Create named desktop with JSON output."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "create", "--name", "Work", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["name"] == "Work"
        mock_backend.virtual_desktop_create.assert_called_once_with(name="Work")

    def test_create_error(self, runner, mock_backend):
        """Handle creation failure."""
        mock_backend.virtual_desktop_create.side_effect = NaturoError(
            message="Failed to create desktop",
            code="VIRTUAL_DESKTOP_ERROR",
        )
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "create", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


# ── desktop close ───────────────────────────────


class TestDesktopClose:
    """Tests for 'naturo desktop close'."""

    def test_close_current_text(self, runner, mock_backend):
        """Close current desktop (no index)."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "close"])
        assert result.exit_code == 0
        assert "Closed desktop" in result.output
        mock_backend.virtual_desktop_close.assert_called_once_with(index=None)

    def test_close_by_index_json(self, runner, mock_backend):
        """Close specific desktop by index."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "close", "1", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["index"] == 1
        mock_backend.virtual_desktop_close.assert_called_once_with(index=1)

    def test_close_last_desktop(self, runner, mock_backend):
        """Cannot close the last desktop."""
        mock_backend.virtual_desktop_close.side_effect = NaturoError(
            message="Cannot close the last virtual desktop",
            code="VIRTUAL_DESKTOP_ERROR",
        )
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "close", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "last" in data["error"]["message"]

    def test_close_negative_index(self, runner, mock_backend):
        """Reject negative close index."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "close", "--json", "--", "-1"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


# ── desktop move-window ─────────────────────────


class TestDesktopMoveWindow:
    """Tests for 'naturo desktop move-window'."""

    def test_move_by_app_text(self, runner, mock_backend):
        """Move window by app name."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "move-window", "1", "--app", "Notepad"])
        assert result.exit_code == 0
        assert "Moved window to Desktop 2" in result.output
        mock_backend.virtual_desktop_move_window.assert_called_once_with(
            desktop_index=1, app="Notepad", hwnd=None,
        )

    def test_move_by_hwnd_json(self, runner, mock_backend):
        """Move window by handle with JSON output."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(
                main, ["desktop", "move-window", "1", "--hwnd", "12345", "--json"]
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["hwnd"] == 12345
        assert data["target_desktop"] == 1

    def test_move_foreground_window(self, runner, mock_backend):
        """Move foreground window when no app/hwnd specified."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["desktop", "move-window", "0"])
        assert result.exit_code == 0
        mock_backend.virtual_desktop_move_window.assert_called_once_with(
            desktop_index=0, app=None, hwnd=None,
        )

    def test_move_negative_index(self, runner, mock_backend):
        """Reject negative desktop index."""
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(
                main, ["desktop", "move-window", "--json", "--", "-1"]
            )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_move_window_not_found(self, runner, mock_backend):
        """Handle window not found error."""
        mock_backend.virtual_desktop_move_window.side_effect = NaturoError(
            message="No window found to move",
            code="WINDOW_NOT_FOUND",
        )
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(
                main, ["desktop", "move-window", "1", "--app", "nonexistent", "--json"]
            )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "WINDOW_NOT_FOUND"

    def test_move_out_of_range(self, runner, mock_backend):
        """Handle desktop index out of range."""
        mock_backend.virtual_desktop_move_window.side_effect = NaturoError(
            message="Desktop index 5 out of range (0-1)",
            code="INVALID_INPUT",
        )
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(
                main, ["desktop", "move-window", "5", "--json"]
            )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


# ── Help output ─────────────────────────────────


class TestDesktopHelp:
    """Verify help text and command registration."""

    def test_desktop_group_help(self, runner):
        """Desktop command group shows subcommands."""
        result = runner.invoke(main, ["desktop", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "switch" in result.output
        assert "create" in result.output
        assert "close" in result.output
        assert "move-window" in result.output

    def test_desktop_list_help(self, runner):
        """Desktop list shows help."""
        result = runner.invoke(main, ["desktop", "list", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_desktop_switch_help(self, runner):
        """Desktop switch shows help."""
        result = runner.invoke(main, ["desktop", "switch", "--help"])
        assert result.exit_code == 0
        assert "INDEX" in result.output

    def test_desktop_move_window_help(self, runner):
        """Desktop move-window shows help."""
        result = runner.invoke(main, ["desktop", "move-window", "--help"])
        assert result.exit_code == 0
        assert "--app" in result.output
        assert "--hwnd" in result.output


# ── MCP tools ───────────────────────────────────


class TestDesktopMCP:
    """Test MCP server virtual desktop tools registration."""

    def test_mcp_tools_exist(self):
        """Virtual desktop MCP tools are registered."""
        pytest.importorskip("mcp")
        from naturo.mcp_server import create_server

        with patch("naturo.mcp_server.get_backend") as mock_get:
            mock_get.return_value = MagicMock()
            server = create_server()

        # Check tool names are registered
        tool_names = [t.name for t in server._tool_manager.list_tools()]
        assert "virtual_desktop_list" in tool_names
        assert "virtual_desktop_switch" in tool_names
        assert "virtual_desktop_create" in tool_names
        assert "virtual_desktop_close" in tool_names
        assert "virtual_desktop_move_window" in tool_names
