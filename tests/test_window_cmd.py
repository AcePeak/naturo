"""Tests for naturo.cli.window_cmd — focus, close, minimize, maximize, restore, move, resize, set-bounds, list."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.window_cmd import window


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    return MagicMock()


# ---------------------------------------------------------------------------
# Helper: common window action commands (focus, close, minimize, maximize, restore)
# ---------------------------------------------------------------------------

_SIMPLE_ACTIONS = ["focus", "minimize", "maximize", "restore"]


class TestWindowSimpleActions:
    """Tests for simple window actions: focus, minimize, maximize, restore."""

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_success_with_app(self, runner, mock_backend, action):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [action, "--app", "Notepad"])
        assert result.exit_code == 0
        assert "notepad" in result.output.lower() or action in result.output.lower()

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_success_with_title(self, runner, mock_backend, action):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [action, "--title", "Untitled"])
        assert result.exit_code == 0

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_success_with_hwnd(self, runner, mock_backend, action):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [action, "--hwnd", "12345"])
        assert result.exit_code == 0

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_success_with_positional_name(self, runner, mock_backend, action):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [action, "Notepad"])
        assert result.exit_code == 0

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_no_target_error(self, runner, action):
        result = runner.invoke(window, [action])
        assert result.exit_code != 0

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_no_target_error_json(self, runner, action):
        result = runner.invoke(window, [action, "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_json_output(self, runner, mock_backend, action):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [action, "--app", "Notepad", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == action

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_naturo_error(self, runner, mock_backend, action):
        from naturo.errors import NaturoError
        backend_method = getattr(mock_backend, f"{action}_window")
        backend_method.side_effect = NaturoError("WINDOW_NOT_FOUND", "not found")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [action, "--app", "X"])
        assert result.exit_code != 0

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_naturo_error_json(self, runner, mock_backend, action):
        from naturo.errors import NaturoError
        backend_method = getattr(mock_backend, f"{action}_window")
        backend_method.side_effect = NaturoError("WINDOW_NOT_FOUND", "not found")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [action, "--app", "X", "--json"])
        assert result.exit_code != 0
        assert "WINDOW_NOT_FOUND" in result.output

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_generic_error(self, runner, mock_backend, action):
        backend_method = getattr(mock_backend, f"{action}_window")
        backend_method.side_effect = RuntimeError("unexpected")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [action, "--app", "X"])
        assert result.exit_code != 0

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_generic_error_json(self, runner, mock_backend, action):
        backend_method = getattr(mock_backend, f"{action}_window")
        backend_method.side_effect = RuntimeError("unexpected")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [action, "--app", "X", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "UNKNOWN_ERROR"

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_deprecation_warning(self, runner, mock_backend, action):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [action, "--app", "X"])
        assert "deprecated" in result.output.lower()


# ---------------------------------------------------------------------------
# close (has --force flag)
# ---------------------------------------------------------------------------

class TestWindowClose:
    """Tests for 'naturo window close' command."""

    def test_close_success(self, runner, mock_backend):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["close", "--app", "Notepad"])
        assert result.exit_code == 0
        mock_backend.close_window.assert_called_once()

    def test_close_force(self, runner, mock_backend):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["close", "--app", "Notepad", "--force"])
        assert result.exit_code == 0
        call_kwargs = mock_backend.close_window.call_args[1]
        assert call_kwargs["force"] is True

    def test_close_json_force(self, runner, mock_backend):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["close", "--app", "X", "--force", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["force"] is True

    def test_close_no_target(self, runner):
        result = runner.invoke(window, ["close"])
        assert result.exit_code != 0

    def test_close_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.close_window.side_effect = NaturoError("WINDOW_NOT_FOUND", "nope")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["close", "--app", "X"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# move
# ---------------------------------------------------------------------------

class TestWindowMove:
    """Tests for 'naturo window move' command."""

    def test_move_success(self, runner, mock_backend):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["move", "--app", "Notepad", "--x", "100", "--y", "200"])
        assert result.exit_code == 0
        assert "100" in result.output and "200" in result.output

    def test_move_json(self, runner, mock_backend):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["move", "--app", "X", "--x", "10", "--y", "20", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["x"] == 10 and data["y"] == 20

    def test_move_missing_x(self, runner):
        result = runner.invoke(window, ["move", "--app", "X", "--y", "10"])
        assert result.exit_code != 0

    def test_move_missing_y(self, runner):
        result = runner.invoke(window, ["move", "--app", "X", "--x", "10"])
        assert result.exit_code != 0

    def test_move_missing_xy(self, runner):
        result = runner.invoke(window, ["move", "--app", "X"])
        assert result.exit_code != 0

    def test_move_no_target(self, runner):
        result = runner.invoke(window, ["move", "--x", "10", "--y", "20"])
        assert result.exit_code != 0

    def test_move_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.move_window.side_effect = NaturoError("WINDOW_NOT_FOUND", "nope")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["move", "--app", "X", "--x", "0", "--y", "0"])
        assert result.exit_code != 0

    def test_move_generic_error_json(self, runner, mock_backend):
        mock_backend.move_window.side_effect = RuntimeError("fail")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["move", "--app", "X", "--x", "0", "--y", "0", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "UNKNOWN_ERROR"


# ---------------------------------------------------------------------------
# resize
# ---------------------------------------------------------------------------

class TestWindowResize:
    """Tests for 'naturo window resize' command."""

    def test_resize_success(self, runner, mock_backend):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["resize", "--app", "X", "--width", "800", "--height", "600"])
        assert result.exit_code == 0
        assert "800" in result.output and "600" in result.output

    def test_resize_json(self, runner, mock_backend):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["resize", "--app", "X", "--width", "800", "--height", "600", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["width"] == 800 and data["height"] == 600

    def test_resize_missing_width(self, runner):
        result = runner.invoke(window, ["resize", "--app", "X", "--height", "600"])
        assert result.exit_code != 0

    def test_resize_missing_height(self, runner):
        result = runner.invoke(window, ["resize", "--app", "X", "--width", "800"])
        assert result.exit_code != 0

    def test_resize_invalid_dimensions(self, runner):
        result = runner.invoke(window, ["resize", "--app", "X", "--width", "0", "--height", "600"])
        assert result.exit_code != 0

    def test_resize_no_target(self, runner):
        result = runner.invoke(window, ["resize", "--width", "100", "--height", "100"])
        assert result.exit_code != 0

    def test_resize_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.resize_window.side_effect = NaturoError("WINDOW_NOT_FOUND", "nope")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["resize", "--app", "X", "--width", "100", "--height", "100"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# set-bounds
# ---------------------------------------------------------------------------

class TestWindowSetBounds:
    """Tests for 'naturo window set-bounds' command."""

    def test_set_bounds_success(self, runner, mock_backend):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [
                "set-bounds", "--app", "X",
                "--x", "10", "--y", "20", "--width", "800", "--height", "600",
            ])
        assert result.exit_code == 0

    def test_set_bounds_json(self, runner, mock_backend):
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [
                "set-bounds", "--app", "X",
                "--x", "10", "--y", "20", "--width", "800", "--height", "600", "--json",
            ])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["x"] == 10 and data["width"] == 800

    def test_set_bounds_missing_options(self, runner):
        result = runner.invoke(window, ["set-bounds", "--app", "X", "--x", "10"])
        assert result.exit_code != 0

    def test_set_bounds_invalid_dimensions(self, runner):
        result = runner.invoke(window, [
            "set-bounds", "--app", "X",
            "--x", "0", "--y", "0", "--width", "0", "--height", "100",
        ])
        assert result.exit_code != 0

    def test_set_bounds_no_target(self, runner):
        result = runner.invoke(window, [
            "set-bounds", "--x", "0", "--y", "0", "--width", "100", "--height", "100",
        ])
        assert result.exit_code != 0

    def test_set_bounds_naturo_error_json(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.set_bounds.side_effect = NaturoError("WINDOW_NOT_FOUND", "nope")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, [
                "set-bounds", "--app", "X",
                "--x", "0", "--y", "0", "--width", "100", "--height", "100", "--json",
            ])
        assert result.exit_code != 0
        assert "WINDOW_NOT_FOUND" in result.output


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

class TestWindowList:
    """Tests for 'naturo window list' command."""

    def _make_window(self, handle=100, title="Test", process_name="test.exe",
                     pid=1234, x=0, y=0, width=800, height=600,
                     is_visible=True, is_minimized=False):
        return SimpleNamespace(
            handle=handle, title=title, process_name=process_name,
            pid=pid, x=x, y=y, width=width, height=height,
            is_visible=is_visible, is_minimized=is_minimized,
        )

    def test_list_windows(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            self._make_window(handle=1, title="Notepad", process_name="notepad.exe"),
            self._make_window(handle=2, title="Chrome", process_name="chrome.exe"),
        ]
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["list"])
        assert result.exit_code == 0
        assert "2 windows" in result.output

    def test_list_empty(self, runner, mock_backend):
        mock_backend.list_windows.return_value = []
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["list"])
        assert result.exit_code == 0
        assert "No windows found" in result.output

    def test_list_json(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            self._make_window(handle=1, title="Notepad", process_name="notepad.exe"),
        ]
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 1
        assert data["windows"][0]["title"] == "Notepad"

    def test_list_filter_by_app(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            self._make_window(handle=1, title="Notepad", process_name="notepad.exe"),
            self._make_window(handle=2, title="Chrome", process_name="chrome.exe"),
        ]
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["list", "--app", "notepad"])
        assert result.exit_code == 0
        assert "1 windows" in result.output

    def test_list_filter_by_pid(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            self._make_window(handle=1, pid=111),
            self._make_window(handle=2, pid=222),
        ]
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["list", "--pid", "111"])
        assert result.exit_code == 0
        assert "1 windows" in result.output

    def test_list_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.list_windows.side_effect = NaturoError("BACKEND_ERROR", "fail")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["list"])
        assert result.exit_code != 0

    def test_list_generic_error_json(self, runner, mock_backend):
        mock_backend.list_windows.side_effect = RuntimeError("fail")
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(window, ["list", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "UNKNOWN_ERROR"


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

class TestWindowHelp:
    """Tests for window command help text."""

    def test_window_help(self, runner):
        result = runner.invoke(window, ["--help"])
        assert result.exit_code == 0

    def test_focus_help(self, runner):
        result = runner.invoke(window, ["focus", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_list_help(self, runner):
        result = runner.invoke(window, ["list", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# App ID promotion (#776): --app aN must be promoted to --app-id
# ---------------------------------------------------------------------------

class TestAppIdPromotion:
    """Verify --app aN is promoted to --app-id in window commands (#776)."""

    @pytest.mark.parametrize("action", _SIMPLE_ACTIONS)
    def test_app_a1_promoted_in_simple_actions(self, runner, mock_backend, action):
        """--app a1 should be treated as --app-id a1, resolving via app ID map."""
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend), \
             patch("naturo.cli.window_cmd.resolve_app_id_to_hwnd", return_value=99999) as mock_resolve:
            result = runner.invoke(window, [action, "--app", "a1"])
        # resolve_app_id_to_hwnd must receive app_id="a1" (promoted from --app)
        mock_resolve.assert_called_once_with("a1", None, False)
        assert result.exit_code == 0

    def test_app_a1_promoted_in_window_move(self, runner, mock_backend):
        """--app a1 should be promoted in window move command."""
        with patch("naturo.cli.window_cmd._get_backend", return_value=mock_backend), \
             patch("naturo.cli.window_cmd.resolve_app_id_to_hwnd", return_value=99999) as mock_resolve:
            result = runner.invoke(window, ["move", "--app", "a1", "--x", "0", "--y", "0"])
        mock_resolve.assert_called_once_with("a1", None, False)
        assert result.exit_code == 0
