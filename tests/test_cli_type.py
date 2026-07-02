"""Tests for naturo.cli.interaction._type — type command.

Tests cover basic typing, paste mode, --on element targeting, --file input,
escape interpretation, --clear/--delete, --return/--tab/--escape suffixes,
verification, UIA value set path, and error paths. All mock-based, CI-safe.
"""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner

from naturo.cli.interaction._type import type_cmd


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.type_text.return_value = None
    backend.press_key.return_value = None
    backend.hotkey.return_value = None
    backend.clipboard_get.return_value = ""
    backend.clipboard_set.return_value = None
    backend.click.return_value = None
    backend.focus_window.return_value = None
    backend._resolve_hwnd.return_value = 12345
    backend.set_element_value.return_value = False
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


# ── Basic typing ─────────────────────────────────────────────────────


class TestBasicType:

    def test_type_text(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["Hello World"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.type_text.assert_called_once_with(
            "Hello World", delay_ms=5, profile="linear", wpm=120, input_mode="normal",
        )

    def test_type_json_output(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["test", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["action"] == "typed"
        assert data["data"]["text"] == "test"
        assert data["data"]["length"] == 4

    def test_no_text_shows_error(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output

    def test_custom_delay_and_profile(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, [
                "test", "--delay", "10", "--profile", "human", "--wpm", "60",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.type_text.assert_called_once_with(
            "test", delay_ms=10, profile="human", wpm=60, input_mode="normal",
        )

    def test_invalid_wpm_shows_error(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["test", "--wpm", "0", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output


# ── Suffix keys (--return, --tab, --escape) ──────────────────────────


class TestSuffixKeys:

    def test_press_return_after_typing(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello", "--return"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.press_key.assert_called_once_with("enter")

    def test_press_tab_after_typing(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello", "--tab", "3"], catch_exceptions=False)
        assert result.exit_code == 0
        assert mock_backend.press_key.call_count == 3
        mock_backend.press_key.assert_called_with("tab")

    def test_press_escape_after_typing(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello", "--escape"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.press_key.assert_called_once_with("escape")


# ── --clear / --delete ───────────────────────────────────────────────


class TestClearDelete:

    def test_clear_selects_all_and_deletes(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["new text", "--clear"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.hotkey.assert_any_call("ctrl", "a")
        mock_backend.press_key.assert_any_call("delete")

    def test_delete_deprecated_behaves_like_clear(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["new text", "--delete"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.hotkey.assert_any_call("ctrl", "a")
        mock_backend.press_key.assert_any_call("delete")


# ── --paste mode ─────────────────────────────────────────────────────


class TestPasteMode:

    def test_paste_mode_with_text(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["large text", "--paste"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.clipboard_set.assert_called_with("large text")
        mock_backend.hotkey.assert_any_call("ctrl", "v")
        # Should NOT call type_text
        mock_backend.type_text.assert_not_called()

    def test_paste_mode_restores_clipboard(self, runner, mock_backend):
        mock_backend.clipboard_get.return_value = "previous"
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["new", "--paste", "--restore"], catch_exceptions=False)
        assert result.exit_code == 0
        # Should restore the old clipboard content
        calls = mock_backend.clipboard_set.call_args_list
        assert call("new") in calls
        assert call("previous") in calls

    def test_paste_without_text_uses_current_clipboard(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["--paste", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["action"] == "pasted"
        mock_backend.hotkey.assert_called_with("ctrl", "v")
        # Should NOT call clipboard_set (no text to set)
        mock_backend.clipboard_set.assert_not_called()

    def test_paste_json_output(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello", "--paste", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["data"]["action"] == "pasted"


# ── --file ───────────────────────────────────────────────────────────


class TestFileInput:

    def test_file_reads_and_pastes(self, runner, mock_backend):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("file content here")
            f.flush()
            fpath = f.name
        try:
            with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
                result = runner.invoke(type_cmd, ["--file", fpath], catch_exceptions=False)
            assert result.exit_code == 0
            mock_backend.clipboard_set.assert_called_with("file content here")
            mock_backend.hotkey.assert_any_call("ctrl", "v")
        finally:
            os.unlink(fpath)

    def test_file_not_found_shows_error(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["--file", "/nonexistent.txt", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output


# ── --interpret-escapes ──────────────────────────────────────────────


class TestInterpretEscapes:

    def test_escapes_interpreted(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello\\tworld\\n", "-E"], catch_exceptions=False)
        assert result.exit_code == 0
        # (#840) Newline handling lives in the backend, not the CLI layer.
        # The CLI passes the full interpreted string (including \n) to backend.type_text.
        mock_backend.type_text.assert_called_once_with(
            "hello\tworld\n", delay_ms=5, profile="linear", wpm=120, input_mode="normal",
        )

    def test_literal_backslash_preserved_without_flag(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["C:\\Users\\test"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.type_text.assert_called_once_with(
            "C:\\Users\\test", delay_ms=5, profile="linear", wpm=120, input_mode="normal",
        )

    def test_double_backslash_becomes_single_with_flag(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["path\\\\file", "-E"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.type_text.assert_called_once_with(
            "path\\file", delay_ms=5, profile="linear", wpm=120, input_mode="normal",
        )


# ── --on element targeting ───────────────────────────────────────────


class TestOnElement:

    def test_on_ref_clicks_then_types(self, runner, mock_backend):
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref.return_value = (100, 200, "snap1")

        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route(), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = runner.invoke(type_cmd, ["hello", "--on", "e42"], catch_exceptions=False)
        assert result.exit_code == 0
        # First: click on element to focus
        mock_backend.click.assert_called_once_with(100, 200, button="left", input_mode="normal")
        # Then: type text
        mock_backend.type_text.assert_called_once()

    def test_on_ref_not_found(self, runner, mock_backend):
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref.return_value = None

        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route(), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = runner.invoke(type_cmd, ["hello", "--on", "e999", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "STALE_SNAPSHOT_CACHE" in result.output

    def test_on_text_finds_element(self, runner, mock_backend):
        mock_elem = MagicMock()
        mock_elem.x = 50
        mock_elem.y = 60
        mock_elem.width = 200
        mock_elem.height = 30
        mock_backend.find_element.return_value = mock_elem

        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello", "--on", "Username"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.find_element.assert_called_once_with("Username")
        mock_backend.click.assert_called_once_with(150, 75, button="left", input_mode="normal")

    def test_on_text_not_found(self, runner, mock_backend):
        mock_backend.find_element.return_value = None

        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello", "--on", "Missing", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "ELEMENT_NOT_FOUND" in result.output


# ── --app window focus ───────────────────────────────────────────────


class TestAppFocus:

    def test_app_focuses_window_before_typing(self, runner, mock_backend):
        with _patch_resolve_app_id(app="notepad"), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello", "--app", "notepad"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend._resolve_hwnd.assert_called()
        mock_backend.focus_window.assert_called_once_with(hwnd=12345)

    def test_focus_failure_shows_error(self, runner, mock_backend):
        mock_backend._resolve_hwnd.side_effect = Exception("window not found")

        with _patch_resolve_app_id(app="gone"), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello", "--app", "gone", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "WINDOW_FOCUS_ERROR" in result.output


# ── Backend error ────────────────────────────────────────────────────


class TestBackendError:

    def test_type_exception_shows_error(self, runner, mock_backend):
        mock_backend.type_text.side_effect = Exception("input failed")
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "input failed" in result.output


# ── Input mode ───────────────────────────────────────────────────────


class TestInputMode:

    def test_hardware_input_mode(self, runner, mock_backend):
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["test", "--input-mode", "hardware"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.type_text.assert_called_once_with(
            "test", delay_ms=5, profile="linear", wpm=120, input_mode="hardware",
        )


# ── UIA value set path ──────────────────────────────────────────────


class TestUiaValueSet:

    def test_uia_method_tries_set_element_value(self, runner, mock_backend):
        mock_backend.set_element_value.return_value = True
        route = {"method": "uia"}

        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route(route):
            result = runner.invoke(type_cmd, ["hello", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.set_element_value.assert_called_once()
        mock_backend.type_text.assert_not_called()
        data = json.loads(result.output)
        assert data["data"]["input_method"] == "uia_set_value"

    def test_uia_fallback_to_type_text(self, runner, mock_backend):
        mock_backend.set_element_value.return_value = False
        route = {"method": "uia"}

        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route(route):
            result = runner.invoke(type_cmd, ["hello", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.type_text.assert_called_once_with(
            "hello", delay_ms=5, profile="linear", wpm=120, input_mode="normal",
        )

    def test_uia_fallback_passes_newlines_to_backend(self, runner, mock_backend):
        """UIA fallback path must pass the full text (with newlines) to
        backend.type_text — newline splitting happens inside the backend,
        not the CLI layer (#840)."""
        mock_backend.set_element_value.return_value = False
        route = {"method": "uia"}

        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route(route):
            result = runner.invoke(
                type_cmd, ["line1\\nline2", "-E", "--json"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        # The CLI must hand the full multiline string to the backend as-is.
        # The backend is responsible for splitting on newlines (#840).
        mock_backend.type_text.assert_called_once_with(
            "line1\nline2", delay_ms=5, profile="linear", wpm=120, input_mode="normal",
        )


# ── --ref alias for --on ─────────────────────────────────────────────


class TestRefAlias:

    def test_ref_alias_works_as_on(self, runner, mock_backend):
        mock_elem = MagicMock()
        mock_elem.x = 50
        mock_elem.y = 60
        mock_elem.width = 100
        mock_elem.height = 20
        mock_backend.find_element.return_value = mock_elem

        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello", "--ref", "Input"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.find_element.assert_called_once_with("Input")


# ── Newline handling (#840) ─────────────────────────────────────────


class TestTypeWithNewlines:
    """#840: newline handling belongs in the backend, not the CLI layer.

    The CLI must pass the full text (including newlines) directly to
    backend.type_text().  The backend is responsible for converting
    newlines to Enter keypresses.  These tests verify the CLI passes
    the correct string; the backend-level splitting is tested in
    test_type_newline_840.py.
    """

    def test_cli_passes_text_without_newline_to_backend(self, runner, mock_backend):
        """Text without newlines is passed straight to backend.type_text."""
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(type_cmd, ["hello"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.type_text.assert_called_once_with(
            "hello", delay_ms=5, profile="linear", wpm=120, input_mode="normal",
        )

    def test_cli_passes_newline_text_to_backend(self, runner, mock_backend):
        """CLI passes the full multiline string to backend.type_text as-is.

        The backend owns the newline-splitting logic (#840); the CLI must
        not split before calling type_text.
        """
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(
                type_cmd, ["line1\\nline2", "-E"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        mock_backend.type_text.assert_called_once_with(
            "line1\nline2", delay_ms=5, profile="linear", wpm=120, input_mode="normal",
        )

    def test_cli_passes_crlf_text_to_backend(self, runner, mock_backend):
        """CRLF text is passed intact to backend.type_text."""
        with _patch_resolve_app_id(), _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(
                type_cmd, ["a\r\nb"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        mock_backend.type_text.assert_called_once_with(
            "a\r\nb", delay_ms=5, profile="linear", wpm=120, input_mode="normal",
        )
