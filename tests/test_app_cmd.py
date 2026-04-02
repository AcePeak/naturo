"""Tests for naturo.cli.app_cmd — launch, quit, relaunch, list, find, inspect, hide, unhide, switch, focus, close, minimize, maximize, restore, move, windows."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.app_ids import AppIdEntry
from naturo.cli.app_cmd import (
    app_close,
    app_find,
    app_focus,
    app_hide,
    app_inspect,
    app_launch,
    app_list,
    app_maximize,
    app_minimize,
    app_move,
    app_quit,
    app_relaunch,
    app_restore,
    app_switch,
    app_unhide,
    app_windows,
    _match_windows,
    _resolve_app_id,
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    return MagicMock()


def _make_process_info(pid=1234, name="notepad.exe", path="C:\\notepad.exe",
                       is_running=True, window_count=1):
    return SimpleNamespace(
        pid=pid, name=name, path=path,
        is_running=is_running, window_count=window_count,
    )


def _make_window(handle=100, title="Test", process_name="test.exe",
                 pid=1234, x=0, y=0, width=800, height=600,
                 is_visible=True, is_minimized=False):
    return SimpleNamespace(
        handle=handle, title=title, process_name=process_name,
        pid=pid, x=x, y=y, width=width, height=height,
        is_visible=is_visible, is_minimized=is_minimized,
    )


# ---------------------------------------------------------------------------
# _match_windows helper
# ---------------------------------------------------------------------------

class TestMatchWindows:
    """Tests for the _match_windows helper function."""

    def test_match_by_process_name(self):
        windows = [_make_window(process_name="notepad.exe", title="Untitled", pid=100)]
        result = _match_windows(windows, "notepad")
        assert len(result) == 1

    def test_match_by_title(self):
        windows = [_make_window(process_name="app.exe", title="My Notepad", pid=100)]
        result = _match_windows(windows, "notepad")
        assert len(result) == 1

    def test_excludes_own_pid(self):
        import os
        windows = [_make_window(process_name="notepad.exe", pid=os.getpid())]
        result = _match_windows(windows, "notepad")
        assert len(result) == 0

    def test_process_matches_before_title(self):
        windows = [
            _make_window(process_name="other.exe", title="notepad doc", pid=100),
            _make_window(process_name="notepad.exe", title="Untitled", pid=200),
        ]
        result = _match_windows(windows, "notepad")
        assert len(result) == 2
        assert result[0].process_name == "notepad.exe"

    def test_no_match(self):
        windows = [_make_window(process_name="chrome.exe", title="Google", pid=100)]
        result = _match_windows(windows, "notepad")
        assert len(result) == 0


# ---------------------------------------------------------------------------
# app launch
# ---------------------------------------------------------------------------

class TestAppLaunch:
    """Tests for 'naturo app launch' command."""

    def test_launch_by_name(self, runner):
        info = _make_process_info()
        with patch("naturo.process.launch_app", return_value=info):
            result = runner.invoke(app_launch, ["notepad"])
        assert result.exit_code == 0
        assert "Launched" in result.output

    def test_launch_by_path(self, runner):
        info = _make_process_info()
        with patch("naturo.process.launch_app", return_value=info):
            result = runner.invoke(app_launch, ["--path", "/usr/bin/app"])
        assert result.exit_code == 0

    def test_launch_json(self, runner):
        info = _make_process_info()
        with patch("naturo.process.launch_app", return_value=info):
            result = runner.invoke(app_launch, ["notepad", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["process"]["pid"] == 1234

    def test_launch_no_args(self, runner):
        result = runner.invoke(app_launch, [])
        assert result.exit_code != 0

    def test_launch_naturo_error(self, runner):
        from naturo.errors import NaturoError
        with patch("naturo.process.launch_app", side_effect=NaturoError("APP_NOT_FOUND", "not found")):
            result = runner.invoke(app_launch, ["badapp"])
        assert result.exit_code != 0

    def test_launch_with_app_flag(self, runner):
        info = _make_process_info()
        with patch("naturo.process.launch_app", return_value=info):
            result = runner.invoke(app_launch, ["--app", "notepad"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# app quit
# ---------------------------------------------------------------------------

class TestAppQuit:
    """Tests for 'naturo app quit' command."""

    def test_quit_by_name(self, runner):
        with patch("naturo.process.quit_app"):
            result = runner.invoke(app_quit, ["notepad"])
        assert result.exit_code == 0
        assert "Quit" in result.output

    def test_quit_by_pid(self, runner):
        with patch("naturo.process.quit_app"):
            result = runner.invoke(app_quit, ["--pid", "1234"])
        # positional NAME is required=False with default=None
        # but --pid alone should work
        assert result.exit_code == 0

    def test_quit_force(self, runner):
        with patch("naturo.process.quit_app") as mock_quit:
            result = runner.invoke(app_quit, ["notepad", "--force"])
        assert result.exit_code == 0
        mock_quit.assert_called_once()
        assert mock_quit.call_args[1]["force"] is True

    def test_quit_json(self, runner):
        with patch("naturo.process.quit_app"):
            result = runner.invoke(app_quit, ["notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True

    def test_quit_no_args(self, runner):
        result = runner.invoke(app_quit, [])
        assert result.exit_code != 0

    def test_quit_naturo_error(self, runner):
        from naturo.errors import NaturoError
        with patch("naturo.process.quit_app", side_effect=NaturoError("APP_NOT_FOUND", "nope")):
            result = runner.invoke(app_quit, ["badapp"])
        assert result.exit_code != 0

    def test_quit_with_app_flag(self, runner):
        with patch("naturo.process.quit_app"):
            result = runner.invoke(app_quit, ["--app", "notepad"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# app relaunch
# ---------------------------------------------------------------------------

class TestAppRelaunch:
    """Tests for 'naturo app relaunch' command."""

    def test_relaunch(self, runner):
        info = _make_process_info()
        with patch("naturo.process.relaunch_app", return_value=info):
            result = runner.invoke(app_relaunch, ["notepad"])
        assert result.exit_code == 0
        assert "Relaunched" in result.output

    def test_relaunch_json(self, runner):
        info = _make_process_info()
        with patch("naturo.process.relaunch_app", return_value=info):
            result = runner.invoke(app_relaunch, ["notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True

    def test_relaunch_no_name(self, runner):
        result = runner.invoke(app_relaunch, [])
        assert result.exit_code != 0

    def test_relaunch_naturo_error(self, runner):
        from naturo.errors import NaturoError
        with patch("naturo.process.relaunch_app", side_effect=NaturoError("APP_NOT_FOUND", "nope")):
            result = runner.invoke(app_relaunch, ["badapp"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# app find
# ---------------------------------------------------------------------------

class TestAppFind:
    """Tests for 'naturo app find' command."""

    def test_find_success(self, runner):
        proc = _make_process_info()
        with patch("naturo.process.find_process", return_value=proc):
            result = runner.invoke(app_find, ["notepad"])
        assert result.exit_code == 0
        assert "Found" in result.output

    def test_find_not_found(self, runner):
        with patch("naturo.process.find_process", return_value=None):
            result = runner.invoke(app_find, ["badapp"])
        assert result.exit_code != 0
        assert "Not found" in result.output

    def test_find_json(self, runner):
        proc = _make_process_info()
        with patch("naturo.process.find_process", return_value=proc):
            result = runner.invoke(app_find, ["notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["process"]["pid"] == 1234

    def test_find_not_found_json(self, runner):
        with patch("naturo.process.find_process", return_value=None):
            result = runner.invoke(app_find, ["badapp", "--json"])
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "PROCESS_NOT_FOUND"


# ---------------------------------------------------------------------------
# app hide / unhide
# ---------------------------------------------------------------------------

class TestAppHideUnhide:
    """Tests for 'naturo app hide' and 'naturo app unhide' commands."""

    def test_hide_success(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(process_name="notepad.exe", pid=100),
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_hide, ["notepad"])
        assert result.exit_code == 0
        assert "Minimized" in result.output
        mock_backend.minimize_window.assert_called_once()

    def test_hide_json(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(process_name="notepad.exe", pid=100),
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_hide, ["notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "hide"

    def test_hide_no_name(self, runner):
        result = runner.invoke(app_hide, [])
        assert result.exit_code != 0

    def test_hide_app_not_found(self, runner, mock_backend):
        mock_backend.list_windows.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_hide, ["badapp"])
        assert result.exit_code != 0

    def test_unhide_success(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(process_name="notepad.exe", pid=100),
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_unhide, ["notepad"])
        assert result.exit_code == 0
        assert "Restored" in result.output

    def test_unhide_json(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(process_name="notepad.exe", pid=100),
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_unhide, ["notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "unhide"

    def test_unhide_no_name(self, runner):
        result = runner.invoke(app_unhide, [])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# app switch
# ---------------------------------------------------------------------------

class TestAppSwitch:
    """Tests for 'naturo app switch' command."""

    def test_switch_success(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(process_name="notepad.exe", title="Untitled", handle=999, pid=100),
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_switch, ["notepad"])
        assert result.exit_code == 0
        assert "Switched to" in result.output
        mock_backend.focus_window.assert_called_once_with(hwnd=999)

    def test_switch_json(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(process_name="notepad.exe", title="Doc", handle=999, pid=100),
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_switch, ["notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "switch"

    def test_switch_not_found(self, runner, mock_backend):
        mock_backend.list_windows.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_switch, ["badapp"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# app focus / close / minimize / maximize / restore (unified window ops)
# ---------------------------------------------------------------------------

_APP_WINDOW_ACTIONS = [
    (app_focus, "focus", "focus_window"),
    (app_minimize, "minimize", "minimize_window"),
    (app_maximize, "maximize", "maximize_window"),
    (app_restore, "restore", "restore_window"),
]


class TestAppWindowActions:
    """Tests for unified window actions under app: focus, minimize, maximize, restore."""

    @pytest.mark.parametrize("cmd,action_name,backend_method", _APP_WINDOW_ACTIONS)
    def test_success_by_name(self, runner, mock_backend, cmd, action_name, backend_method):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(cmd, ["Notepad"])
        assert result.exit_code == 0

    @pytest.mark.parametrize("cmd,action_name,backend_method", _APP_WINDOW_ACTIONS)
    def test_success_by_hwnd(self, runner, mock_backend, cmd, action_name, backend_method):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(cmd, ["--hwnd", "12345"])
        assert result.exit_code == 0

    @pytest.mark.parametrize("cmd,action_name,backend_method", _APP_WINDOW_ACTIONS)
    def test_json_output(self, runner, mock_backend, cmd, action_name, backend_method):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(cmd, ["Notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == action_name

    @pytest.mark.parametrize("cmd,action_name,backend_method", _APP_WINDOW_ACTIONS)
    def test_no_target(self, runner, cmd, action_name, backend_method):
        result = runner.invoke(cmd, [])
        assert result.exit_code != 0

    @pytest.mark.parametrize("cmd,action_name,backend_method", _APP_WINDOW_ACTIONS)
    def test_naturo_error(self, runner, mock_backend, cmd, action_name, backend_method):
        from naturo.errors import NaturoError
        getattr(mock_backend, backend_method).side_effect = NaturoError("WINDOW_NOT_FOUND", "nope")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(cmd, ["Notepad"])
        assert result.exit_code != 0

    @pytest.mark.parametrize("cmd,action_name,backend_method", _APP_WINDOW_ACTIONS)
    def test_generic_error_json(self, runner, mock_backend, cmd, action_name, backend_method):
        getattr(mock_backend, backend_method).side_effect = RuntimeError("unexpected")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(cmd, ["Notepad", "--json"])
        data = json.loads(result.output)
        assert data["error"]["code"] == "UNKNOWN_ERROR"

    @pytest.mark.parametrize("cmd,action_name,backend_method", _APP_WINDOW_ACTIONS)
    def test_with_app_flag(self, runner, mock_backend, cmd, action_name, backend_method):
        # Only app_focus has --app flag
        if cmd is app_focus:
            with patch("naturo.backends.base.get_backend", return_value=mock_backend):
                result = runner.invoke(cmd, ["--app", "Notepad"])
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# app close (has --force)
# ---------------------------------------------------------------------------

class TestAppClose:
    """Tests for 'naturo app close' command."""

    def test_close_success(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_close, ["notepad"])
        assert result.exit_code == 0
        assert "Closed" in result.output

    def test_close_force(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_close, ["notepad", "--force"])
        assert result.exit_code == 0
        call_kwargs = mock_backend.close_window.call_args[1]
        assert call_kwargs["force"] is True

    def test_close_json(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_close, ["notepad", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "close"

    def test_close_no_target(self, runner):
        result = runner.invoke(app_close, [])
        assert result.exit_code != 0

    def test_close_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.close_window.side_effect = NaturoError("WINDOW_NOT_FOUND", "nope")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_close, ["notepad"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# app move (combined move/resize/set-bounds)
# ---------------------------------------------------------------------------

class TestAppMove:
    """Tests for 'naturo app move' command."""

    def test_move_position(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_move, ["notepad", "--x", "100", "--y", "200"])
        assert result.exit_code == 0
        mock_backend.move_window.assert_called_once()

    def test_move_resize(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_move, ["notepad", "--width", "800", "--height", "600"])
        assert result.exit_code == 0
        mock_backend.resize_window.assert_called_once()

    def test_move_set_bounds(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_move, [
                "notepad", "--x", "10", "--y", "20", "--width", "800", "--height", "600",
            ])
        assert result.exit_code == 0
        mock_backend.set_bounds.assert_called_once()

    def test_move_json_position(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_move, ["notepad", "--x", "10", "--y", "20", "--json"])
        data = json.loads(result.output)
        assert data["action"] == "move"
        assert data["x"] == 10

    def test_move_json_resize(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_move, ["notepad", "--width", "800", "--height", "600", "--json"])
        data = json.loads(result.output)
        assert data["action"] == "resize"

    def test_move_json_set_bounds(self, runner, mock_backend):
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_move, [
                "notepad", "--x", "0", "--y", "0", "--width", "800", "--height", "600", "--json",
            ])
        data = json.loads(result.output)
        assert data["action"] == "set-bounds"

    def test_move_partial_position_x_only(self, runner):
        result = runner.invoke(app_move, ["notepad", "--x", "100"])
        assert result.exit_code != 0

    def test_move_partial_position_y_only(self, runner):
        result = runner.invoke(app_move, ["notepad", "--y", "100"])
        assert result.exit_code != 0

    def test_move_partial_size_width_only(self, runner):
        result = runner.invoke(app_move, ["notepad", "--width", "800"])
        assert result.exit_code != 0

    def test_move_no_dimensions(self, runner):
        result = runner.invoke(app_move, ["notepad"])
        assert result.exit_code != 0

    def test_move_invalid_size(self, runner):
        result = runner.invoke(app_move, ["notepad", "--width", "0", "--height", "600"])
        assert result.exit_code != 0

    def test_move_no_target(self, runner):
        result = runner.invoke(app_move, ["--x", "10", "--y", "20"])
        assert result.exit_code != 0

    def test_move_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.move_window.side_effect = NaturoError("WINDOW_NOT_FOUND", "nope")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_move, ["notepad", "--x", "0", "--y", "0"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# app windows
# ---------------------------------------------------------------------------

class TestAppWindows:
    """Tests for 'naturo app windows' command."""

    def test_list_all(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(handle=1, title="Notepad", process_name="notepad.exe"),
            _make_window(handle=2, title="Chrome", process_name="chrome.exe"),
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_windows, [])
        assert result.exit_code == 0
        assert "2 windows" in result.output

    def test_list_empty(self, runner, mock_backend):
        mock_backend.list_windows.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_windows, [])
        assert result.exit_code == 0
        assert "No windows found" in result.output

    def test_filter_by_name(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(handle=1, title="Notepad", process_name="notepad.exe"),
            _make_window(handle=2, title="Chrome", process_name="chrome.exe"),
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_windows, ["notepad"])
        assert result.exit_code == 0
        assert "1 windows" in result.output

    def test_filter_by_pid(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(handle=1, pid=111),
            _make_window(handle=2, pid=222),
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_windows, ["--pid", "111"])
        assert result.exit_code == 0

    def test_json_output(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(handle=1, title="Test", process_name="test.exe"),
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_windows, ["--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 1

    def test_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.list_windows.side_effect = NaturoError("BACKEND_ERROR", "fail")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_windows, [])
        assert result.exit_code != 0

    def test_generic_error_json(self, runner, mock_backend):
        mock_backend.list_windows.side_effect = RuntimeError("fail")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(app_windows, ["--json"])
        data = json.loads(result.output)
        assert data["error"]["code"] == "UNKNOWN_ERROR"


# ---------------------------------------------------------------------------
# app inspect
# ---------------------------------------------------------------------------

class TestAppInspect:
    """Tests for 'naturo app inspect' command."""

    def test_inspect_no_args(self, runner):
        result = runner.invoke(app_inspect, [])
        assert result.exit_code != 0

    def test_inspect_invalid_pid(self, runner):
        result = runner.invoke(app_inspect, ["--pid", "0"])
        assert result.exit_code != 0

    def test_inspect_no_args_json(self, runner):
        result = runner.invoke(app_inspect, ["--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"


# ---------------------------------------------------------------------------
# Help texts
# ---------------------------------------------------------------------------

class TestAppHelp:
    """Tests for app command help text."""

    def test_launch_help(self, runner):
        result = runner.invoke(app_launch, ["--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_quit_help(self, runner):
        result = runner.invoke(app_quit, ["--help"])
        assert result.exit_code == 0
        assert "--force" in result.output

    def test_find_help(self, runner):
        result = runner.invoke(app_find, ["--help"])
        assert result.exit_code == 0

    def test_inspect_help(self, runner):
        result = runner.invoke(app_inspect, ["--help"])
        assert result.exit_code == 0
        assert "--all" in result.output

    def test_focus_help(self, runner):
        result = runner.invoke(app_focus, ["--help"])
        assert result.exit_code == 0

    def test_move_help(self, runner):
        result = runner.invoke(app_move, ["--help"])
        assert result.exit_code == 0
        assert "--width" in result.output

    def test_windows_help(self, runner):
        result = runner.invoke(app_windows, ["--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# App ID resolution (#776)
# ---------------------------------------------------------------------------

def _make_app_id_entry(app_id="a1", pid=1234, handle=5678,
                       process_name="notepad.exe", title="Untitled"):
    import time
    return AppIdEntry(
        app_id=app_id, pid=pid, handle=handle,
        process_name=process_name, title=title,
        timestamp=time.time(),
    )


class TestResolveAppId:
    """Tests for _resolve_app_id helper."""

    def test_non_app_id_returns_none(self):
        assert _resolve_app_id("notepad", False) is None

    def test_none_returns_none(self):
        assert _resolve_app_id(None, False) is None

    @patch("naturo.app_ids.get_app_id_map")
    def test_valid_id_returns_entry(self, mock_map):
        entry = _make_app_id_entry()
        mock_map.return_value.resolve.return_value = entry
        result = _resolve_app_id("a1", False)
        assert result is entry

    @patch("naturo.app_ids.get_app_id_map")
    def test_expired_id_returns_false(self, mock_map):
        mock_map.return_value.resolve.return_value = None
        result = _resolve_app_id("a1", False)
        assert result is False


class TestAppIdInCommands:
    """Tests that app ID resolution works in actual CLI commands (#776)."""

    def test_launch_rejects_app_id(self, runner):
        result = runner.invoke(app_launch, ["a1"])
        assert result.exit_code != 0
        assert "Cannot launch by app ID" in result.output

    def test_launch_rejects_app_id_json(self, runner):
        result = runner.invoke(app_launch, ["a1", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"

    @patch("naturo.app_ids.get_app_id_map")
    @patch("naturo.process.quit_app")
    def test_quit_resolves_app_id(self, mock_quit, mock_map, runner):
        entry = _make_app_id_entry()
        mock_map.return_value.resolve.return_value = entry
        result = runner.invoke(app_quit, ["a1"])
        assert result.exit_code == 0
        mock_quit.assert_called_once_with(
            name="notepad.exe", pid=1234, force=False, timeout=10.0,
        )

    @patch("naturo.app_ids.get_app_id_map")
    def test_quit_expired_app_id(self, mock_map, runner):
        mock_map.return_value.resolve.return_value = None
        result = runner.invoke(app_quit, ["a1"])
        assert result.exit_code != 0
        assert "not found or expired" in result.output

    @patch("naturo.app_ids.get_app_id_map")
    def test_quit_expired_app_id_json(self, mock_map, runner):
        mock_map.return_value.resolve.return_value = None
        result = runner.invoke(app_quit, ["a1", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "APP_ID_NOT_FOUND"

    @patch("naturo.app_ids.get_app_id_map")
    @patch("naturo.process.relaunch_app")
    def test_relaunch_resolves_app_id(self, mock_relaunch, mock_map, runner):
        entry = _make_app_id_entry()
        mock_map.return_value.resolve.return_value = entry
        mock_relaunch.return_value = _make_process_info()
        result = runner.invoke(app_relaunch, ["a1"])
        assert result.exit_code == 0
        mock_relaunch.assert_called_once()
        assert mock_relaunch.call_args.kwargs["name"] == "notepad.exe"

    @patch("naturo.app_ids.get_app_id_map")
    @patch("naturo.backends.base.get_backend")
    def test_focus_resolves_app_id_to_hwnd(self, mock_get_backend, mock_map, runner):
        entry = _make_app_id_entry(handle=9999)
        mock_map.return_value.resolve.return_value = entry
        backend = MagicMock()
        mock_get_backend.return_value = backend
        result = runner.invoke(app_focus, ["a1"])
        assert result.exit_code == 0
        backend.focus_window.assert_called_once_with(title=None, hwnd=9999)

    @patch("naturo.app_ids.get_app_id_map")
    @patch("naturo.backends.base.get_backend")
    def test_close_resolves_app_id_to_hwnd(self, mock_get_backend, mock_map, runner):
        entry = _make_app_id_entry(handle=9999)
        mock_map.return_value.resolve.return_value = entry
        backend = MagicMock()
        mock_get_backend.return_value = backend
        result = runner.invoke(app_close, ["a1"])
        assert result.exit_code == 0
        backend.close_window.assert_called_once_with(title=None, hwnd=9999, force=False)

    @patch("naturo.app_ids.get_app_id_map")
    @patch("naturo.backends.base.get_backend")
    def test_minimize_resolves_app_id_to_hwnd(self, mock_get_backend, mock_map, runner):
        entry = _make_app_id_entry(handle=9999)
        mock_map.return_value.resolve.return_value = entry
        backend = MagicMock()
        mock_get_backend.return_value = backend
        result = runner.invoke(app_minimize, ["a1"])
        assert result.exit_code == 0
        backend.minimize_window.assert_called_once_with(title=None, hwnd=9999)

    @patch("naturo.app_ids.get_app_id_map")
    @patch("naturo.backends.base.get_backend")
    def test_maximize_resolves_app_id_to_hwnd(self, mock_get_backend, mock_map, runner):
        entry = _make_app_id_entry(handle=9999)
        mock_map.return_value.resolve.return_value = entry
        backend = MagicMock()
        mock_get_backend.return_value = backend
        result = runner.invoke(app_maximize, ["a1"])
        assert result.exit_code == 0
        backend.maximize_window.assert_called_once_with(title=None, hwnd=9999)

    @patch("naturo.app_ids.get_app_id_map")
    @patch("naturo.backends.base.get_backend")
    def test_restore_resolves_app_id_to_hwnd(self, mock_get_backend, mock_map, runner):
        entry = _make_app_id_entry(handle=9999)
        mock_map.return_value.resolve.return_value = entry
        backend = MagicMock()
        mock_get_backend.return_value = backend
        result = runner.invoke(app_restore, ["a1"])
        assert result.exit_code == 0
        backend.restore_window.assert_called_once_with(title=None, hwnd=9999)

    @patch("naturo.app_ids.get_app_id_map")
    @patch("naturo.backends.base.get_backend")
    def test_move_resolves_app_id_to_hwnd(self, mock_get_backend, mock_map, runner):
        entry = _make_app_id_entry(handle=9999)
        mock_map.return_value.resolve.return_value = entry
        backend = MagicMock()
        mock_get_backend.return_value = backend
        result = runner.invoke(app_move, ["a1", "--x", "100", "--y", "200"])
        assert result.exit_code == 0
        backend.move_window.assert_called_once_with(x=100, y=200, title=None, hwnd=9999)

    def test_normal_name_not_treated_as_app_id(self, runner):
        """Names like 'app' or 'acrobat' should NOT match the a<N> pattern."""
        # 'acrobat' starts with 'a' but has letters after digits — should not match
        result = runner.invoke(app_launch, ["acrobat", "--help"])
        # --help should work — the name is not rejected as an app ID
        assert result.exit_code == 0

    @patch("naturo.app_ids.get_app_id_map")
    @patch("naturo.process.find_process")
    def test_find_resolves_app_id(self, mock_find, mock_map, runner):
        entry = _make_app_id_entry()
        mock_map.return_value.resolve.return_value = entry
        mock_find.return_value = _make_process_info()
        result = runner.invoke(app_find, ["a1"])
        assert result.exit_code == 0
        mock_find.assert_called_once_with(name="notepad.exe", pid=1234)
