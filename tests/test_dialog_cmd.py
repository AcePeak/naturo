"""Tests for naturo.cli.dialog_cmd — dialog detect, accept, dismiss, click-button, type."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.dialog_cmd import dialog
from naturo.dialog import DialogButton, DialogInfo, DialogType


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    return MagicMock()


def _make_dialog(
    title="Save As",
    dialog_type=DialogType.MESSAGE_BOX,
    buttons=None,
    hwnd=12345,
    message="Do you want to save?",
    has_input=False,
    input_value="",
    owner_app="notepad.exe",
):
    if buttons is None:
        buttons = [
            DialogButton(name="OK", element_id="btn1", is_default=True, x=100, y=200),
            DialogButton(name="Cancel", element_id="btn2", is_cancel=True, x=200, y=200),
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


# ---------------------------------------------------------------------------
# dialog detect
# ---------------------------------------------------------------------------

class TestDialogDetect:
    """Tests for 'naturo dialog detect' command."""

    def test_detect_no_dialogs(self, runner, mock_backend):
        mock_backend.detect_dialogs.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["detect"])
        assert result.exit_code == 0
        assert "No dialogs detected." in result.output

    def test_detect_with_dialog(self, runner, mock_backend):
        d = _make_dialog()
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["detect"])
        assert result.exit_code == 0
        assert "Save As" in result.output
        assert "message_box" in result.output
        assert "OK, Cancel" in result.output
        assert "notepad.exe" in result.output

    def test_detect_json_output(self, runner, mock_backend):
        d = _make_dialog()
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["detect", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 1
        assert data["dialogs"][0]["title"] == "Save As"

    def test_detect_json_empty(self, runner, mock_backend):
        mock_backend.detect_dialogs.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["detect", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 0

    def test_detect_with_app_filter(self, runner, mock_backend):
        mock_backend.detect_dialogs.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["detect", "--app", "notepad"])
        mock_backend.detect_dialogs.assert_called_once_with(app="notepad", hwnd=None)

    def test_detect_dialog_with_input(self, runner, mock_backend):
        d = _make_dialog(has_input=True, input_value="test.txt")
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["detect"])
        assert result.exit_code == 0
        assert "Input:" in result.output
        assert "test.txt" in result.output

    def test_detect_multiple_dialogs(self, runner, mock_backend):
        d1 = _make_dialog(title="Dialog 1", hwnd=100)
        d2 = _make_dialog(title="Dialog 2", hwnd=200)
        mock_backend.detect_dialogs.return_value = [d1, d2]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["detect"])
        assert "Dialog 1" in result.output
        assert "Dialog 2" in result.output


# ---------------------------------------------------------------------------
# dialog accept
# ---------------------------------------------------------------------------

class TestDialogAccept:
    """Tests for 'naturo dialog accept' command."""

    def test_accept_clicks_ok(self, runner, mock_backend):
        d = _make_dialog()
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["accept"])
        assert result.exit_code == 0
        assert "Accepted" in result.output
        assert "OK" in result.output
        mock_backend.click.assert_called_once_with(x=100, y=200)

    def test_accept_json_output(self, runner, mock_backend):
        d = _make_dialog()
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["accept", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["button_clicked"] == "OK"

    def test_accept_no_dialog(self, runner, mock_backend):
        mock_backend.detect_dialogs.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["accept"])
        # Should report error about no dialog found
        assert result.exit_code != 0 or "error" in result.output.lower() or "DIALOG_NOT_FOUND" in result.output


# ---------------------------------------------------------------------------
# dialog dismiss
# ---------------------------------------------------------------------------

class TestDialogDismiss:
    """Tests for 'naturo dialog dismiss' command."""

    def test_dismiss_clicks_cancel(self, runner, mock_backend):
        d = _make_dialog()
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["dismiss"])
        assert result.exit_code == 0
        assert "Dismissed" in result.output
        assert "Cancel" in result.output
        mock_backend.click.assert_called_once_with(x=200, y=200)

    def test_dismiss_json_output(self, runner, mock_backend):
        d = _make_dialog()
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["dismiss", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["button_clicked"] == "Cancel"

    def test_dismiss_no_dialog(self, runner, mock_backend):
        mock_backend.detect_dialogs.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["dismiss"])
        assert result.exit_code != 0 or "error" in result.output.lower() or "DIALOG_NOT_FOUND" in result.output


# ---------------------------------------------------------------------------
# dialog click-button
# ---------------------------------------------------------------------------

class TestDialogClickButton:
    """Tests for 'naturo dialog click-button' command."""

    def test_click_button_success(self, runner, mock_backend):
        mock_backend.dialog_click_button.return_value = {
            "dialog_title": "Save As",
            "button_clicked": "Save",
        }
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["click-button", "Save"])
        assert result.exit_code == 0
        assert "Clicked 'Save'" in result.output
        assert "Save As" in result.output

    def test_click_button_json(self, runner, mock_backend):
        mock_backend.dialog_click_button.return_value = {
            "dialog_title": "Save As",
            "button_clicked": "Save",
        }
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["click-button", "Save", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True

    def test_click_button_missing_argument(self, runner):
        result = runner.invoke(dialog, ["click-button"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# dialog type
# ---------------------------------------------------------------------------

class TestDialogType:
    """Tests for 'naturo dialog type' command."""

    def test_type_text(self, runner, mock_backend):
        mock_backend.dialog_set_input.return_value = {
            "dialog_title": "Open",
            "typed_text": "hello.txt",
        }
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["type", "hello.txt"])
        assert result.exit_code == 0
        assert "Typed 'hello.txt'" in result.output
        mock_backend.dialog_set_input.assert_called_once_with(text="hello.txt", app=None, hwnd=None)

    def test_type_with_accept(self, runner, mock_backend):
        mock_backend.dialog_set_input.return_value = {
            "dialog_title": "Open",
            "typed_text": "hello.txt",
        }
        d = _make_dialog(title="Open")
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["type", "hello.txt", "--accept"])
        assert result.exit_code == 0
        assert "accepted" in result.output.lower() or "OK" in result.output
        # Should have called click for the OK button
        mock_backend.click.assert_called_once()

    def test_type_json_output(self, runner, mock_backend):
        mock_backend.dialog_set_input.return_value = {
            "dialog_title": "Open",
            "typed_text": "hello.txt",
        }
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["type", "hello.txt", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True

    def test_type_missing_text(self, runner):
        result = runner.invoke(dialog, ["type"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

class TestDialogHelp:
    """Tests for dialog command help text."""

    def test_dialog_help(self, runner):
        result = runner.invoke(dialog, ["--help"])
        assert result.exit_code == 0
        assert "detect" in result.output
        assert "accept" in result.output
        assert "dismiss" in result.output

    def test_detect_help(self, runner):
        result = runner.invoke(dialog, ["detect", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "--app" in result.output

    def test_accept_help(self, runner):
        result = runner.invoke(dialog, ["accept", "--help"])
        assert result.exit_code == 0

    def test_dismiss_help(self, runner):
        result = runner.invoke(dialog, ["dismiss", "--help"])
        assert result.exit_code == 0
