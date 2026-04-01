"""Tests for naturo.cli.system._dialog — dialog detect, accept, dismiss, click-button, type."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.system import dialog
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

    def test_accept_hwnd_filter_matches(self, runner, mock_backend):
        """--hwnd selects the matching dialog, not the first one."""
        d1 = _make_dialog(title="Wrong", hwnd=111)
        d2 = _make_dialog(title="Right", hwnd=222)
        mock_backend.detect_dialogs.return_value = [d1, d2]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["accept", "--hwnd", "222"])
        assert result.exit_code == 0
        assert "Right" in result.output

    def test_accept_hwnd_no_match_falls_back(self, runner, mock_backend):
        """--hwnd with no match falls back to first dialog."""
        d1 = _make_dialog(title="First", hwnd=111)
        mock_backend.detect_dialogs.return_value = [d1]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["accept", "--hwnd", "999"])
        assert result.exit_code == 0
        assert "First" in result.output

    def test_accept_no_accept_button(self, runner, mock_backend):
        """Dialog with buttons that don't match accept patterns."""
        custom_buttons = [
            DialogButton(name="Retry", element_id="b1", is_default=False, x=100, y=200),
            DialogButton(name="Help", element_id="b2", is_default=False, x=200, y=200),
        ]
        d = _make_dialog(buttons=custom_buttons)
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["accept"])
        assert result.exit_code != 0 or "ELEMENT_NOT_FOUND" in result.output
        mock_backend.click.assert_not_called()

    def test_accept_is_default_button(self, runner, mock_backend):
        """Button with is_default=True should be picked even if name isn't in _ACCEPT_BUTTONS."""
        custom_buttons = [
            DialogButton(name="Confirm", element_id="b1", is_default=True, x=150, y=200),
            DialogButton(name="Abort", element_id="b2", is_cancel=True, x=250, y=200),
        ]
        d = _make_dialog(buttons=custom_buttons)
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["accept"])
        assert result.exit_code == 0
        assert "Confirm" in result.output
        mock_backend.click.assert_called_once_with(x=150, y=200)

    def test_accept_no_accept_button_json(self, runner, mock_backend):
        """JSON output when no accept button found."""
        custom_buttons = [
            DialogButton(name="Retry", element_id="b1", is_default=False, x=100, y=200),
        ]
        d = _make_dialog(buttons=custom_buttons)
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["accept", "--json"])
        data = json.loads(result.output)
        assert data.get("success") is not True or "ELEMENT_NOT_FOUND" in result.output


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

    def test_dismiss_no_dismiss_button(self, runner, mock_backend):
        """Dialog with buttons that don't match dismiss patterns (no cancel/close)."""
        custom_buttons = [
            DialogButton(name="Retry", element_id="b1", is_default=True, x=100, y=200),
            DialogButton(name="Continue", element_id="b2", is_default=False, x=200, y=200),
        ]
        d = _make_dialog(buttons=custom_buttons)
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["dismiss"])
        assert result.exit_code != 0 or "ELEMENT_NOT_FOUND" in result.output
        # Verify available buttons are listed in error message
        assert "Retry" in result.output or result.exit_code != 0
        mock_backend.click.assert_not_called()

    def test_dismiss_is_cancel_button(self, runner, mock_backend):
        """Button with is_cancel=True should be picked even if name isn't in _DISMISS_BUTTONS."""
        custom_buttons = [
            DialogButton(name="Discard", element_id="b1", is_default=False, is_cancel=True, x=300, y=200),
            DialogButton(name="Save", element_id="b2", is_default=True, x=100, y=200),
        ]
        d = _make_dialog(buttons=custom_buttons)
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["dismiss"])
        assert result.exit_code == 0
        assert "Discard" in result.output
        mock_backend.click.assert_called_once_with(x=300, y=200)

    def test_dismiss_hwnd_filter(self, runner, mock_backend):
        """--hwnd selects the matching dialog for dismiss."""
        d1 = _make_dialog(title="Other", hwnd=100)
        d2 = _make_dialog(title="Target", hwnd=200)
        mock_backend.detect_dialogs.return_value = [d1, d2]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["dismiss", "--hwnd", "200"])
        assert result.exit_code == 0
        assert "Target" in result.output


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

    def test_click_button_empty_name(self, runner, mock_backend):
        """Empty button name triggers INVALID_INPUT error."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["click-button", "   "])
        assert result.exit_code != 0 or "INVALID_INPUT" in result.output
        mock_backend.dialog_click_button.assert_not_called()

    def test_click_button_naturo_error(self, runner, mock_backend):
        """NaturoError from backend is emitted as structured error."""
        from naturo.errors import NaturoError
        mock_backend.dialog_click_button.side_effect = NaturoError("ELEMENT_NOT_FOUND", "Button not found")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["click-button", "Nonexistent"])
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_click_button_generic_error(self, runner, mock_backend):
        """Generic exception from backend is emitted with UNKNOWN_ERROR."""
        mock_backend.dialog_click_button.side_effect = RuntimeError("unexpected")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["click-button", "OK"])
        assert result.exit_code != 0 or "error" in result.output.lower()


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

    def test_type_accept_no_dialog_after_typing(self, runner, mock_backend):
        """--accept flag but no dialog found after typing: silently succeeds with no accept."""
        mock_backend.dialog_set_input.return_value = {
            "dialog_title": "Open",
            "typed_text": "file.txt",
        }
        mock_backend.detect_dialogs.return_value = []  # No dialog after typing
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["type", "file.txt", "--accept"])
        assert result.exit_code == 0
        assert "Typed 'file.txt'" in result.output
        # No accept button mentioned since no dialog was found
        assert "accepted" not in result.output.lower()
        mock_backend.click.assert_not_called()

    def test_type_accept_no_accept_button_in_dialog(self, runner, mock_backend):
        """--accept with dialog found but no accept button: silently succeeds."""
        mock_backend.dialog_set_input.return_value = {
            "dialog_title": "Custom",
            "typed_text": "input",
        }
        custom_buttons = [
            DialogButton(name="Retry", element_id="b1", is_default=False, x=100, y=200),
        ]
        d = _make_dialog(title="Custom", buttons=custom_buttons)
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["type", "input", "--accept"])
        assert result.exit_code == 0
        assert "Typed 'input'" in result.output
        mock_backend.click.assert_not_called()

    def test_type_accept_json_includes_accepted_with(self, runner, mock_backend):
        """JSON output includes accepted_with when accept succeeds."""
        mock_backend.dialog_set_input.return_value = {
            "dialog_title": "Open",
            "typed_text": "hello.txt",
        }
        d = _make_dialog(title="Open")
        mock_backend.detect_dialogs.return_value = [d]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["type", "hello.txt", "--accept", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["accepted_with"] == "OK"

    def test_type_accept_json_no_accepted_with(self, runner, mock_backend):
        """JSON output omits accepted_with when no dialog found after typing."""
        mock_backend.dialog_set_input.return_value = {
            "dialog_title": "Open",
            "typed_text": "file.txt",
        }
        mock_backend.detect_dialogs.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["type", "file.txt", "--accept", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "accepted_with" not in data

    def test_type_naturo_error(self, runner, mock_backend):
        """NaturoError from dialog_set_input is emitted."""
        from naturo.errors import NaturoError
        mock_backend.dialog_set_input.side_effect = NaturoError("DIALOG_NOT_FOUND", "No dialog")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(dialog, ["type", "text"])
        assert result.exit_code != 0 or "error" in result.output.lower()


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


# ---------------------------------------------------------------------------
# App ID promotion (#776): --app aN must be promoted to --app-id
# ---------------------------------------------------------------------------

class TestDialogAppIdPromotion:
    """Verify --app aN is promoted to --app-id in dialog commands (#776)."""

    def test_app_a1_promoted_in_detect(self, runner, mock_backend):
        """--app a1 should be treated as --app-id a1 in dialog detect."""
        mock_backend.detect_dialogs.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend), \
             patch("naturo.cli.system._dialog.resolve_app_id_to_hwnd", return_value=99999) as mock_resolve:
            result = runner.invoke(dialog, ["detect", "--app", "a1"])
        mock_resolve.assert_called_once_with("a1", None, False)
        assert result.exit_code == 0
