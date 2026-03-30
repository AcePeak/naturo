"""Tests for naturo.cli.desktop_cmd — virtual desktop list, switch, create, close, move-window."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.desktop_cmd import desktop


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    return MagicMock()


def _patch_pyvda_and_backend(mock_backend):
    """Context manager that patches both _ensure_pyvda and get_backend."""
    return (
        patch("naturo.cli.desktop_cmd._ensure_pyvda"),
        patch("naturo.cli.desktop_cmd.get_backend", return_value=mock_backend, create=True),
        patch("naturo.backends.base.get_backend", return_value=mock_backend),
    )


# ---------------------------------------------------------------------------
# desktop list
# ---------------------------------------------------------------------------

class TestDesktopList:
    """Tests for 'naturo desktop list' command."""

    def test_list_desktops(self, runner, mock_backend):
        mock_backend.virtual_desktop_list.return_value = [
            {"index": 0, "name": "Desktop 1", "is_current": True},
            {"index": 1, "name": "Desktop 2", "is_current": False},
        ]
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["list"])
        assert result.exit_code == 0
        assert "Desktop 1" in result.output
        assert "[current]" in result.output

    def test_list_empty(self, runner, mock_backend):
        mock_backend.virtual_desktop_list.return_value = []
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["list"])
        assert result.exit_code == 0
        assert "No virtual desktops found" in result.output

    def test_list_json(self, runner, mock_backend):
        mock_backend.virtual_desktop_list.return_value = [
            {"index": 0, "name": "Desktop 1", "is_current": True},
        ]
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 1

    def test_list_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.virtual_desktop_list.side_effect = NaturoError("VIRTUAL_DESKTOP_ERROR", "fail")
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["list"])
        assert result.exit_code != 0

    def test_list_generic_error(self, runner, mock_backend):
        mock_backend.virtual_desktop_list.side_effect = RuntimeError("fail")
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["list"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# desktop switch
# ---------------------------------------------------------------------------

class TestDesktopSwitch:
    """Tests for 'naturo desktop switch' command."""

    def test_switch_success(self, runner, mock_backend):
        mock_backend.virtual_desktop_switch.return_value = {"index": 1, "name": "Desktop 2"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["switch", "1"])
        assert result.exit_code == 0
        assert "Switched to desktop 1" in result.output

    def test_switch_json(self, runner, mock_backend):
        mock_backend.virtual_desktop_switch.return_value = {"index": 1, "name": "Desktop 2"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["switch", "1", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["index"] == 1

    def test_switch_negative_index(self, runner):
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"):
            result = runner.invoke(desktop, ["switch", "--", "-1"])
        assert result.exit_code != 0

    def test_switch_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.virtual_desktop_switch.side_effect = NaturoError("VIRTUAL_DESKTOP_ERROR", "out of range")
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["switch", "99"])
        assert result.exit_code != 0

    def test_switch_generic_error_json(self, runner, mock_backend):
        mock_backend.virtual_desktop_switch.side_effect = RuntimeError("fail")
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["switch", "1", "--json"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# desktop create
# ---------------------------------------------------------------------------

class TestDesktopCreate:
    """Tests for 'naturo desktop create' command."""

    def test_create_unnamed(self, runner, mock_backend):
        mock_backend.virtual_desktop_create.return_value = {"index": 2, "name": "Desktop 3"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["create"])
        assert result.exit_code == 0
        assert "Created desktop" in result.output

    def test_create_named(self, runner, mock_backend):
        mock_backend.virtual_desktop_create.return_value = {"index": 2, "name": "Work"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["create", "--name", "Work"])
        assert result.exit_code == 0
        mock_backend.virtual_desktop_create.assert_called_once_with(name="Work")

    def test_create_json(self, runner, mock_backend):
        mock_backend.virtual_desktop_create.return_value = {"index": 2, "name": "Dev"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["create", "--name", "Dev", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["name"] == "Dev"

    def test_create_error(self, runner, mock_backend):
        mock_backend.virtual_desktop_create.side_effect = RuntimeError("limit reached")
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["create"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# desktop close
# ---------------------------------------------------------------------------

class TestDesktopClose:
    """Tests for 'naturo desktop close' command."""

    def test_close_current(self, runner, mock_backend):
        mock_backend.virtual_desktop_close.return_value = {"index": 1, "name": "Desktop 2"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["close"])
        assert result.exit_code == 0
        assert "Closed desktop" in result.output

    def test_close_by_index(self, runner, mock_backend):
        mock_backend.virtual_desktop_close.return_value = {"index": 2, "name": "Desktop 3"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["close", "2"])
        assert result.exit_code == 0
        mock_backend.virtual_desktop_close.assert_called_once_with(index=2)

    def test_close_json(self, runner, mock_backend):
        mock_backend.virtual_desktop_close.return_value = {"index": 0, "name": "Desktop 1"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["close", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True

    def test_close_negative_index(self, runner):
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"):
            result = runner.invoke(desktop, ["close", "--", "-1"])
        assert result.exit_code != 0

    def test_close_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.virtual_desktop_close.side_effect = NaturoError("VIRTUAL_DESKTOP_ERROR", "last desktop")
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(desktop, ["close"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# desktop move-window
# ---------------------------------------------------------------------------

class TestDesktopMoveWindow:
    """Tests for 'naturo desktop move-window' command."""

    def test_move_window_by_app(self, runner, mock_backend):
        mock_backend.virtual_desktop_move_window.return_value = {"target_name": "Desktop 2"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend), \
             patch("naturo.cli.desktop_cmd.resolve_app_id_to_hwnd", return_value=None):
            result = runner.invoke(desktop, ["move-window", "1", "--app", "Notepad"])
        assert result.exit_code == 0
        assert "Moved window" in result.output

    def test_move_window_by_hwnd(self, runner, mock_backend):
        mock_backend.virtual_desktop_move_window.return_value = {"target_name": "Desktop 1"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend), \
             patch("naturo.cli.desktop_cmd.resolve_app_id_to_hwnd", return_value=None):
            result = runner.invoke(desktop, ["move-window", "0", "--hwnd", "12345"])
        assert result.exit_code == 0

    def test_move_window_json(self, runner, mock_backend):
        mock_backend.virtual_desktop_move_window.return_value = {"target_name": "Desktop 2"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend), \
             patch("naturo.cli.desktop_cmd.resolve_app_id_to_hwnd", return_value=None):
            result = runner.invoke(desktop, ["move-window", "1", "--app", "X", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True

    def test_move_window_negative_index(self, runner):
        with patch("naturo.cli.desktop_cmd.resolve_app_id_to_hwnd", return_value=None), \
             patch("naturo.cli.desktop_cmd._ensure_pyvda"):
            result = runner.invoke(desktop, ["move-window", "--", "-1", "--app", "X"])
        assert result.exit_code != 0

    def test_move_window_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.virtual_desktop_move_window.side_effect = NaturoError("VIRTUAL_DESKTOP_ERROR", "fail")
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend), \
             patch("naturo.cli.desktop_cmd.resolve_app_id_to_hwnd", return_value=None):
            result = runner.invoke(desktop, ["move-window", "1", "--app", "X"])
        assert result.exit_code != 0

    def test_move_foreground_window(self, runner, mock_backend):
        mock_backend.virtual_desktop_move_window.return_value = {"target_name": "Desktop 2"}
        with patch("naturo.cli.desktop_cmd._ensure_pyvda"), \
             patch("naturo.backends.base.get_backend", return_value=mock_backend), \
             patch("naturo.cli.desktop_cmd.resolve_app_id_to_hwnd", return_value=None):
            result = runner.invoke(desktop, ["move-window", "2"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

class TestDesktopHelp:
    """Tests for desktop command help text."""

    def test_desktop_help(self, runner):
        result = runner.invoke(desktop, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "switch" in result.output
        assert "create" in result.output
        assert "close" in result.output

    def test_list_help(self, runner):
        result = runner.invoke(desktop, ["list", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_switch_help(self, runner):
        result = runner.invoke(desktop, ["switch", "--help"])
        assert result.exit_code == 0
        assert "INDEX" in result.output
