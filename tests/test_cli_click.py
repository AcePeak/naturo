"""Tests for naturo.cli.interaction._click — click command.

Tests cover coordinate clicks, element ref clicks, text query clicks,
right/double click, clipboard modifiers, UWP fallback, zero-bounds
invoke, verification, and error paths. All mock-based, CI-safe.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner

from naturo.cli.interaction._click import click_cmd


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.click.return_value = None
    backend.focus_window.return_value = None
    backend._resolve_hwnd.return_value = 12345
    backend._resolve_hwnds.return_value = [12345]
    backend._is_afh_window.return_value = False
    return backend


def _patch_backend(mock_backend):
    return patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend)


def _patch_resolve_app_id(app=None, hwnd=None, pid=None):
    return patch(
        "naturo.cli.interaction._common._resolve_app_id",
        return_value=(app, hwnd, pid),
    )


def _patch_auto_route(route=None):
    return patch(
        "naturo.cli.interaction._common._auto_route",
        return_value=route or {},
    )


# ── Coordinate clicks ───────────────────────────────────────────────


class TestCoordinateClick:

    def test_click_by_coords(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "500", "300"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.click.assert_called_once_with(x=500, y=300, button="left", double=False, input_mode="normal")

    def test_right_click_by_coords(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "100", "200", "--right"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.click.assert_called_once_with(x=100, y=200, button="right", double=False, input_mode="normal")

    def test_double_click_by_coords(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "100", "200", "--double"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.click.assert_called_once_with(x=100, y=200, button="left", double=True, input_mode="normal")

    def test_json_output(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "10", "20", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["action"] == "clicked"
        assert data["data"]["button"] == "left"


# ── No target → error ───────────────────────────────────────────────


class TestNoTarget:

    def test_no_target_shows_error(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, [], catch_exceptions=False)
        assert result.exit_code != 0

    def test_no_target_json_shows_error(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output


# ── Element ID click ─────────────────────────────────────────────────


class TestElementIdClick:

    def test_click_by_element_id(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--id", "button_ok"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.click.assert_called_once_with(
            element_id="button_ok", button="left", double=False, input_mode="normal", hwnd=None,
        )


# ── eN ref click ─────────────────────────────────────────────────────


class TestRefClick:

    def test_click_ref_resolves_from_snapshot(self, runner, mock_backend):
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref.return_value = (150, 250, "snap1")
        mock_mgr.get_snapshot.return_value = MagicMock(window_handle=None)

        with _patch_resolve_app_id(), _patch_backend(mock_backend), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = runner.invoke(click_cmd, ["e42"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.click.assert_called_once_with(x=150, y=250, button="left", double=False, input_mode="normal")

    def test_click_ref_not_found_shows_error(self, runner, mock_backend):
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref.return_value = None
        mock_mgr.resolve_ref_element.return_value = None

        with _patch_resolve_app_id(), _patch_backend(mock_backend), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = runner.invoke(click_cmd, ["e999", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "STALE_SNAPSHOT_CACHE" in result.output

    def test_click_ref_zero_bounds_invokes_uia(self, runner, mock_backend):
        mock_elem = MagicMock()
        mock_elem.frame = (0, 0, 0, 0)
        mock_elem.title = "Clear"
        mock_elem.role = "Button"
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref.return_value = None
        mock_mgr.resolve_ref_element.return_value = (mock_elem, "snap1")
        mock_backend.invoke_element.return_value = True

        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route(), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = runner.invoke(click_cmd, ["e5"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.invoke_element.assert_called_once_with(name="Clear", role="Button")


# ── --on text query ──────────────────────────────────────────────────


class TestOnTextClick:

    def test_click_on_text_query(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--on", "Save"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.click.assert_called_once_with(
            element_id="Save", button="left", double=False, input_mode="normal", hwnd=None,
        )

    def test_click_positional_query(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["Cancel"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.click.assert_called_once_with(
            element_id="Cancel", button="left", double=False, input_mode="normal", hwnd=None,
        )


# ── --app window focus ───────────────────────────────────────────────


class TestAppFocus:

    def test_app_resolves_and_focuses_window(self, runner, mock_backend):
        with _patch_resolve_app_id(app="notepad"), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "50", "50", "--app", "notepad"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend._resolve_hwnd.assert_called()
        mock_backend.focus_window.assert_called_once_with(hwnd=12345)

    def test_app_with_ref_validates_windows_exist(self, runner, mock_backend):
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref.return_value = (100, 200, "snap1")
        mock_mgr.get_snapshot.return_value = MagicMock(window_handle=None)
        mock_backend._resolve_hwnds.return_value = []  # No windows found

        with _patch_resolve_app_id(app="nonexistent"), _patch_backend(mock_backend), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = runner.invoke(click_cmd, ["e1", "--app", "nonexistent", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "WINDOW_NOT_FOUND" in result.output


# ── Clipboard modifiers ─────────────────────────────────────────────


class TestClipboardModifiers:

    def test_paste_after_click(self, runner, mock_backend):
        mock_backend.clipboard_get.return_value = "old"
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "10", "20", "--paste"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.hotkey.assert_called_with("ctrl", "v")

    def test_copy_after_click(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "10", "20", "--copy"], catch_exceptions=False)
        assert result.exit_code == 0
        calls = mock_backend.hotkey.call_args_list
        assert call("ctrl", "a") in calls
        assert call("ctrl", "c") in calls

    def test_cut_after_click(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "10", "20", "--cut"], catch_exceptions=False)
        assert result.exit_code == 0
        calls = mock_backend.hotkey.call_args_list
        assert call("ctrl", "a") in calls
        assert call("ctrl", "x") in calls

    def test_clipboard_action_in_json(self, runner, mock_backend):
        mock_backend.clipboard_get.return_value = ""
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "10", "20", "--paste", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["clipboard_action"] == "paste"


# ── Backend error ────────────────────────────────────────────────────


class TestBackendError:

    def test_click_exception_shows_error(self, runner, mock_backend):
        mock_backend.click.side_effect = Exception("click failed")
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "10", "20", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "click failed" in result.output

    def test_click_element_fallback_on_exception(self, runner, mock_backend):
        mock_backend.click.side_effect = [Exception("UIA Name mismatch"), None]
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route(), \
             patch("naturo.cli.interaction._common._find_element_by_text_fallback", return_value=(300, 400)):
            result = runner.invoke(click_cmd, ["--on", "C"], catch_exceptions=False)
        assert result.exit_code == 0
        # Second click call with resolved coordinates
        assert mock_backend.click.call_count == 2


# ── Input mode ───────────────────────────────────────────────────────


class TestInputMode:

    def test_hardware_input_mode(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--coords", "10", "20", "--input-mode", "hardware"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.click.assert_called_once_with(x=10, y=20, button="left", double=False, input_mode="hardware")


# ── --ref alias for --on ─────────────────────────────────────────────


class TestRefAlias:

    def test_ref_alias_works_as_on(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(click_cmd, ["--ref", "Save"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.click.assert_called_once_with(
            element_id="Save", button="left", double=False, input_mode="normal", hwnd=None,
        )


# ── Coordinate bounds validation (#787) ────────────────────────────


class TestCoordsBoundsValidation:

    def test_negative_x_rejected(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), \
             patch("naturo.cli.interaction._click._get_screen_bound", return_value=1920):
            result = runner.invoke(click_cmd, ["--coords", "-10", "500", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "COORDS_OUT_OF_BOUNDS"
        mock_backend.click.assert_not_called()

    def test_negative_y_rejected(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), \
             patch("naturo.cli.interaction._click._get_screen_bound", return_value=1920):
            result = runner.invoke(click_cmd, ["--coords", "500", "-10", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "COORDS_OUT_OF_BOUNDS"
        mock_backend.click.assert_not_called()

    def test_exceeds_max_bound_rejected(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), \
             patch("naturo.cli.interaction._click._get_screen_bound", return_value=1920):
            result = runner.invoke(click_cmd, ["--coords", "99999", "500", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["error"]["code"] == "COORDS_OUT_OF_BOUNDS"
        mock_backend.click.assert_not_called()

    def test_valid_coords_accepted(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route(), \
             patch("naturo.cli.interaction._click._get_screen_bound", return_value=1920):
            result = runner.invoke(click_cmd, ["--coords", "500", "300"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.click.assert_called_once()
