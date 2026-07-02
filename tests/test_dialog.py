"""Tests for dialog detection and interaction.

Phase 4.5.1 + 4.5.2: Dialog Detection & Interaction.

Tests the dialog classification engine, CLI commands, and backend integration.
Backend calls are mocked since dialog detection requires a Windows desktop session.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.dialog import (
    DialogType,
    DialogInfo,
    DialogButton,
    classify_dialog,
)


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_backend():
    """Mock backend with dialog methods."""
    backend = MagicMock()
    backend.detect_dialogs.return_value = []
    backend.dialog_click_button.return_value = {
        "dialog_title": "Save As",
        "button_clicked": "Save",
        "dialog_hwnd": 12345,
    }
    backend.dialog_set_input.return_value = {
        "dialog_title": "Save As",
        "text_entered": "hello.txt",
        "dialog_hwnd": 12345,
    }
    return backend


def _make_dialog(
    hwnd: int = 12345,
    title: str = "Confirm",
    dialog_type: DialogType = DialogType.CONFIRMATION,
    message: str = "Are you sure?",
    buttons: list | None = None,
    has_input: bool = False,
    input_value: str = "",
    owner_app: str = "notepad.exe",
) -> DialogInfo:
    """Helper to create a DialogInfo for testing."""
    if buttons is None:
        buttons = [
            DialogButton(name="Yes", element_id="e1", is_default=True, x=100, y=200),
            DialogButton(name="No", element_id="e2", is_cancel=True, x=200, y=200),
        ]
    return DialogInfo(
        hwnd=hwnd,
        title=title,
        dialog_type=dialog_type,
        message=message,
        buttons=buttons,
        has_input=has_input,
        input_value=input_value,
        owner_app=owner_app,
    )


# ── Dialog Classification ───────────────────────


class TestClassifyDialog:
    """Tests for classify_dialog function."""

    def test_message_box_ok(self):
        """Standard OK message box."""
        result = classify_dialog(
            title="Information",
            class_name="#32770",
            buttons=["OK"],
            has_edit=False,
            has_file_list=False,
        )
        assert result == DialogType.MESSAGE_BOX

    def test_confirmation_yes_no(self):
        """Yes/No confirmation dialog."""
        result = classify_dialog(
            title="Confirm",
            class_name="#32770",
            buttons=["Yes", "No"],
            has_edit=False,
            has_file_list=False,
        )
        assert result == DialogType.CONFIRMATION

    def test_file_open_dialog(self):
        """File open dialog with file list."""
        result = classify_dialog(
            title="Open",
            class_name="#32770",
            buttons=["Open", "Cancel"],
            has_edit=True,
            has_file_list=True,
        )
        assert result == DialogType.FILE_OPEN

    def test_file_save_dialog(self):
        """File save dialog detected by title."""
        result = classify_dialog(
            title="Save As",
            class_name="#32770",
            buttons=["Save", "Cancel"],
            has_edit=True,
            has_file_list=True,
        )
        assert result == DialogType.FILE_SAVE

    def test_folder_browse_dialog(self):
        """Folder browse dialog."""
        result = classify_dialog(
            title="Browse For Folder",
            class_name="#32770",
            buttons=["OK", "Cancel"],
            has_edit=False,
            has_file_list=True,
        )
        assert result == DialogType.FOLDER_BROWSE

    def test_print_dialog(self):
        """Print dialog detected by title."""
        result = classify_dialog(
            title="Print",
            class_name="#32770",
            buttons=["Print", "Cancel"],
            has_edit=False,
            has_file_list=False,
        )
        assert result == DialogType.PRINT

    def test_color_picker_dialog(self):
        """Color picker dialog."""
        result = classify_dialog(
            title="Color",
            class_name="#32770",
            buttons=["OK", "Cancel"],
            has_edit=False,
            has_file_list=False,
        )
        assert result == DialogType.COLOR_PICKER

    def test_font_picker_dialog(self):
        """Font picker dialog."""
        result = classify_dialog(
            title="Font",
            class_name="#32770",
            buttons=["OK", "Cancel"],
            has_edit=False,
            has_file_list=False,
        )
        assert result == DialogType.FONT_PICKER

    def test_input_dialog(self):
        """Input dialog with edit + OK."""
        result = classify_dialog(
            title="Enter Name",
            class_name="#32770",
            buttons=["OK", "Cancel"],
            has_edit=True,
            has_file_list=False,
        )
        assert result == DialogType.INPUT

    def test_custom_dialog(self):
        """Unknown dialog type falls back to custom."""
        result = classify_dialog(
            title="Custom Dialog",
            class_name="#32770",
            buttons=["Apply Changes"],
            has_edit=False,
            has_file_list=False,
        )
        assert result == DialogType.CUSTOM

    def test_chinese_confirm_dialog(self):
        """Chinese Yes/No dialog."""
        result = classify_dialog(
            title="确认",
            class_name="#32770",
            buttons=["是", "否"],
            has_edit=False,
            has_file_list=False,
        )
        assert result == DialogType.CONFIRMATION

    def test_chinese_save_dialog(self):
        """Chinese save dialog."""
        result = classify_dialog(
            title="另存为",
            class_name="#32770",
            buttons=["保存", "取消"],
            has_edit=True,
            has_file_list=True,
        )
        assert result == DialogType.FILE_SAVE

    def test_chinese_open_dialog(self):
        """Chinese open dialog."""
        result = classify_dialog(
            title="打开",
            class_name="#32770",
            buttons=["打开", "取消"],
            has_edit=True,
            has_file_list=True,
        )
        assert result == DialogType.FILE_OPEN


# ── DialogInfo ──────────────────────────────────


class TestDialogInfo:
    """Tests for DialogInfo data class."""

    def test_to_dict(self):
        """DialogInfo serializes to dict correctly."""
        d = _make_dialog()
        result = d.to_dict()

        assert result["hwnd"] == 12345
        assert result["title"] == "Confirm"
        assert result["dialog_type"] == "confirmation"
        assert result["message"] == "Are you sure?"
        assert len(result["buttons"]) == 2
        assert result["buttons"][0]["name"] == "Yes"
        assert result["buttons"][0]["is_default"] is True
        assert result["buttons"][1]["name"] == "No"
        assert result["buttons"][1]["is_cancel"] is True
        assert result["owner_app"] == "notepad.exe"

    def test_to_dict_with_input(self):
        """DialogInfo with input field serializes correctly."""
        d = _make_dialog(has_input=True, input_value="test.txt")
        result = d.to_dict()
        assert result["has_input"] is True
        assert result["input_value"] == "test.txt"


# ── CLI: dialog detect ─────────────────────────


class TestDialogDetect:
    """Tests for 'naturo dialog detect'."""

    def test_detect_no_dialogs(self, runner, mock_backend):
        """detect with no dialogs shows message."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "detect"])
        assert result.exit_code == 0
        assert "No dialogs detected" in result.output

    def test_detect_no_dialogs_json(self, runner, mock_backend):
        """detect --json with no dialogs returns empty list."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "detect", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["dialogs"] == []
        assert data["count"] == 0

    def test_detect_with_dialog(self, runner, mock_backend):
        """detect with a dialog shows info."""
        mock_backend.detect_dialogs.return_value = [_make_dialog()]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "detect"])
        assert result.exit_code == 0
        assert "Confirm" in result.output
        assert "confirmation" in result.output
        assert "Yes, No" in result.output

    def test_detect_with_dialog_json(self, runner, mock_backend):
        """detect --json with dialog returns structured data."""
        mock_backend.detect_dialogs.return_value = [_make_dialog()]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "detect", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 1
        assert data["dialogs"][0]["title"] == "Confirm"
        assert data["dialogs"][0]["dialog_type"] == "confirmation"

    def test_detect_with_app_filter(self, runner, mock_backend):
        """detect --app passes filter to backend."""
        mock_backend.detect_dialogs.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "detect", "--app", "notepad"])
        mock_backend.detect_dialogs.assert_called_once_with(app="notepad", hwnd=None)

    def test_detect_with_hwnd_filter(self, runner, mock_backend):
        """detect --hwnd passes filter to backend."""
        mock_backend.detect_dialogs.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "detect", "--hwnd", "12345"])
        mock_backend.detect_dialogs.assert_called_once_with(app=None, hwnd=12345)

    def test_detect_shows_message(self, runner, mock_backend):
        """detect displays dialog message text."""
        mock_backend.detect_dialogs.return_value = [_make_dialog(message="Save changes?")]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "detect"])
        assert "Save changes?" in result.output

    def test_detect_shows_input(self, runner, mock_backend):
        """detect displays input field value."""
        mock_backend.detect_dialogs.return_value = [
            _make_dialog(has_input=True, input_value="test.txt")
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "detect"])
        assert "Input:" in result.output


# ── CLI: dialog accept ──────────────────────────


class TestDialogAccept:
    """Tests for 'naturo dialog accept'."""

    def test_accept_no_dialog(self, runner, mock_backend):
        """accept with no dialog returns error."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "accept"])
        assert result.exit_code != 0

    def test_accept_no_dialog_json(self, runner, mock_backend):
        """accept --json with no dialog returns structured error."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "accept", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "DIALOG_NOT_FOUND"

    def test_accept_clicks_yes(self, runner, mock_backend):
        """accept clicks the Yes/OK button."""
        mock_backend.detect_dialogs.return_value = [_make_dialog()]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "accept"])
        assert result.exit_code == 0
        assert "Accepted" in result.output
        assert "Yes" in result.output
        mock_backend.click.assert_called_once()

    def test_accept_json(self, runner, mock_backend):
        """accept --json returns structured success."""
        mock_backend.detect_dialogs.return_value = [_make_dialog()]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "accept", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["button_clicked"] == "Yes"

    def test_accept_ok_button(self, runner, mock_backend):
        """accept finds OK button when no Yes available."""
        dialog = _make_dialog(
            buttons=[
                DialogButton(name="OK", element_id="e1", is_default=True, x=100, y=200),
                DialogButton(name="Cancel", element_id="e2", is_cancel=True, x=200, y=200),
            ]
        )
        mock_backend.detect_dialogs.return_value = [dialog]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "accept", "--json"])
        data = json.loads(result.output)
        assert data["button_clicked"] == "OK"


# ── CLI: dialog dismiss ─────────────────────────


class TestDialogDismiss:
    """Tests for 'naturo dialog dismiss'."""

    def test_dismiss_no_dialog(self, runner, mock_backend):
        """dismiss with no dialog returns error."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "dismiss"])
        assert result.exit_code != 0

    def test_dismiss_clicks_no(self, runner, mock_backend):
        """dismiss clicks the No/Cancel button."""
        mock_backend.detect_dialogs.return_value = [_make_dialog()]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "dismiss"])
        assert result.exit_code == 0
        assert "Dismissed" in result.output
        assert "No" in result.output
        mock_backend.click.assert_called_once()

    def test_dismiss_json(self, runner, mock_backend):
        """dismiss --json returns structured success."""
        mock_backend.detect_dialogs.return_value = [_make_dialog()]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "dismiss", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["button_clicked"] == "No"

    def test_dismiss_cancel_button(self, runner, mock_backend):
        """dismiss finds Cancel button."""
        dialog = _make_dialog(
            buttons=[
                DialogButton(name="OK", element_id="e1", is_default=True, x=100, y=200),
                DialogButton(name="Cancel", element_id="e2", is_cancel=True, x=200, y=200),
            ]
        )
        mock_backend.detect_dialogs.return_value = [dialog]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "dismiss", "--json"])
        data = json.loads(result.output)
        assert data["button_clicked"] == "Cancel"


# ── CLI: dialog click-button ────────────────────


class TestDialogClickButton:
    """Tests for 'naturo dialog click-button'."""

    def test_click_button(self, runner, mock_backend):
        """click-button calls backend correctly."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "click-button", "Save"])
        assert result.exit_code == 0
        assert "Save" in result.output
        mock_backend.dialog_click_button.assert_called_once_with(
            button="Save", app=None, hwnd=None,
        )

    def test_click_button_json(self, runner, mock_backend):
        """click-button --json returns structured result."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "click-button", "Save", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["button_clicked"] == "Save"

    def test_click_button_empty_name(self, runner, mock_backend):
        """click-button with empty name returns error."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "click-button", "   "])
        assert result.exit_code != 0

    def test_click_button_empty_json(self, runner, mock_backend):
        """click-button with empty name returns JSON error."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "click-button", "   ", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


# ── CLI: dialog type ────────────────────────────


class TestDialogType:
    """Tests for 'naturo dialog type'."""

    def test_type_text(self, runner, mock_backend):
        """type sets input text."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "type", "hello.txt"])
        assert result.exit_code == 0
        assert "hello.txt" in result.output
        mock_backend.dialog_set_input.assert_called_once_with(
            text="hello.txt", app=None, hwnd=None,
        )

    def test_type_text_json(self, runner, mock_backend):
        """type --json returns structured result."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "type", "hello.txt", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["text_entered"] == "hello.txt"

    def test_type_and_accept(self, runner, mock_backend):
        """type --accept types then clicks OK."""
        mock_backend.detect_dialogs.return_value = [
            _make_dialog(
                dialog_type=DialogType.FILE_SAVE,
                has_input=True,
                buttons=[
                    DialogButton(name="Save", element_id="e1", is_default=True, x=100, y=200),
                    DialogButton(name="Cancel", element_id="e2", is_cancel=True, x=200, y=200),
                ],
            )
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "type", "hello.txt", "--accept", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["accepted_with"] == "Save"


# ── CLI: dialog help ────────────────────────────


class TestDialogHelp:
    """Tests for dialog command help output."""

    def test_dialog_help(self, runner):
        """dialog --help shows subcommands."""
        result = runner.invoke(main, ["dialog", "--help"])
        assert result.exit_code == 0
        assert "detect" in result.output
        assert "accept" in result.output
        assert "dismiss" in result.output
        assert "click-button" in result.output
        assert "type" in result.output

    def test_detect_help(self, runner):
        """dialog detect --help shows options."""
        result = runner.invoke(main, ["dialog", "detect", "--help"])
        assert result.exit_code == 0
        assert "--app" in result.output
        assert "--hwnd" in result.output
        assert "--json" in result.output

    def test_accept_help(self, runner):
        """dialog accept --help shows options."""
        result = runner.invoke(main, ["dialog", "accept", "--help"])
        assert result.exit_code == 0
        assert "--app" in result.output

    def test_click_button_help(self, runner):
        """dialog click-button --help shows arguments."""
        result = runner.invoke(main, ["dialog", "click-button", "--help"])
        assert result.exit_code == 0
        assert "BUTTON" in result.output

    def test_type_help(self, runner):
        """dialog type --help shows arguments and --accept."""
        result = runner.invoke(main, ["dialog", "type", "--help"])
        assert result.exit_code == 0
        assert "TEXT" in result.output
        assert "--accept" in result.output


# ── Dialog error handling ───────────────────────


class TestDialogErrors:
    """Tests for dialog error handling and edge cases."""

    def test_backend_error_json(self, runner, mock_backend):
        """Backend exception produces JSON error."""
        from naturo.errors import NaturoError
        mock_backend.detect_dialogs.side_effect = NaturoError(
            message="COM error", code="UNKNOWN_ERROR",
        )
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "detect", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "COM error" in data["error"]["message"]

    def test_backend_error_text(self, runner, mock_backend):
        """Backend exception produces text error on stderr."""
        from naturo.errors import NaturoError
        mock_backend.detect_dialogs.side_effect = NaturoError(
            message="COM error", code="UNKNOWN_ERROR",
        )
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "detect"])
        assert result.exit_code != 0

    def test_accept_no_accept_button_json(self, runner, mock_backend):
        """accept with no accept-type button returns error."""
        dialog = _make_dialog(
            buttons=[
                DialogButton(name="Retry", element_id="e1", x=100, y=200),
                DialogButton(name="Abort", element_id="e2", x=200, y=200),
            ]
        )
        mock_backend.detect_dialogs.return_value = [dialog]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "accept", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False

    def test_dismiss_no_dismiss_button_json(self, runner, mock_backend):
        """dismiss with no dismiss-type button returns error."""
        dialog = _make_dialog(
            buttons=[
                DialogButton(name="OK", element_id="e1", is_default=True, x=100, y=200),
                DialogButton(name="Retry", element_id="e2", x=200, y=200),
            ]
        )
        mock_backend.detect_dialogs.return_value = [dialog]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["dialog", "dismiss", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
