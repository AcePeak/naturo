"""Tests for naturo.mcp._dialog — MCP dialog tools.

Tests cover dialog_detect, dialog_accept, dialog_dismiss,
dialog_click_button, dialog_type with mocked backend.
All tests run on Linux CI (no Windows dependencies).
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


def _call_tool(server, tool_name: str, arguments: dict):
    """Helper to call an MCP tool function by name."""
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


def _make_button(name="OK", is_default=False, is_cancel=False, x=200, y=300):
    btn = MagicMock()
    btn.name = name
    btn.is_default = is_default
    btn.is_cancel = is_cancel
    btn.x = x
    btn.y = y
    return btn


def _make_dialog(hwnd=12345, title="Save Changes?", buttons=None):
    dialog = MagicMock()
    dialog.hwnd = hwnd
    dialog.title = title
    dialog.buttons = buttons or []
    dialog.to_dict.return_value = {
        "hwnd": hwnd,
        "title": title,
        "buttons": [{"name": b.name} for b in (buttons or [])],
    }
    return dialog


@pytest.fixture
def mock_backend():
    return MagicMock()


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


class TestDialogDetect:

    def test_returns_dialogs(self, server, mock_backend):
        ok_btn = _make_button("OK", is_default=True)
        dialog = _make_dialog(title="Alert", buttons=[ok_btn])
        mock_backend.detect_dialogs.return_value = [dialog]

        result = _call_tool(server, "dialog_detect", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["count"] == 1
        assert data["dialogs"][0]["title"] == "Alert"

    def test_no_dialogs(self, server, mock_backend):
        mock_backend.detect_dialogs.return_value = []
        result = _call_tool(server, "dialog_detect", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["count"] == 0
        assert data["dialogs"] == []

    def test_filters_by_app(self, server, mock_backend):
        mock_backend.detect_dialogs.return_value = []
        _call_tool(server, "dialog_detect", {"app": "notepad"})
        mock_backend.detect_dialogs.assert_called_once_with(app="notepad", hwnd=None)

    def test_filters_by_hwnd(self, server, mock_backend):
        mock_backend.detect_dialogs.return_value = []
        _call_tool(server, "dialog_detect", {"hwnd": 99999})
        mock_backend.detect_dialogs.assert_called_once_with(app=None, hwnd=99999)


class TestDialogAccept:

    def test_clicks_ok_button(self, server, mock_backend):
        ok_btn = _make_button("OK", is_default=True, x=150, y=250)
        cancel_btn = _make_button("Cancel", is_cancel=True, x=250, y=250)
        dialog = _make_dialog(title="Confirm", buttons=[ok_btn, cancel_btn])
        mock_backend.detect_dialogs.return_value = [dialog]

        result = _call_tool(server, "dialog_accept", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["button_clicked"] == "OK"
        assert data["dialog_title"] == "Confirm"
        mock_backend.click.assert_called_once_with(x=150, y=250)

    def test_clicks_yes_button(self, server, mock_backend):
        yes_btn = _make_button("Yes", x=100, y=200)
        no_btn = _make_button("No", x=200, y=200)
        dialog = _make_dialog(title="Are you sure?", buttons=[yes_btn, no_btn])
        mock_backend.detect_dialogs.return_value = [dialog]

        result = _call_tool(server, "dialog_accept", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["button_clicked"] == "Yes"

    def test_clicks_default_button(self, server, mock_backend):
        custom_btn = _make_button("Proceed", is_default=True, x=150, y=200)
        dialog = _make_dialog(buttons=[custom_btn])
        mock_backend.detect_dialogs.return_value = [dialog]

        result = _call_tool(server, "dialog_accept", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["button_clicked"] == "Proceed"

    def test_no_dialog_found(self, server, mock_backend):
        mock_backend.detect_dialogs.return_value = []
        result = _call_tool(server, "dialog_accept", {})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "DIALOG_NOT_FOUND"

    def test_no_accept_button_available(self, server, mock_backend):
        custom_btn = _make_button("CustomAction", is_default=False)
        dialog = _make_dialog(buttons=[custom_btn])
        mock_backend.detect_dialogs.return_value = [dialog]

        result = _call_tool(server, "dialog_accept", {})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "ELEMENT_NOT_FOUND"
        assert "CustomAction" in data["error"]["message"]

    def test_targets_specific_hwnd(self, server, mock_backend):
        ok1 = _make_button("OK", is_default=True, x=100, y=100)
        ok2 = _make_button("OK", is_default=True, x=200, y=200)
        dialog1 = _make_dialog(hwnd=111, title="First", buttons=[ok1])
        dialog2 = _make_dialog(hwnd=222, title="Second", buttons=[ok2])
        mock_backend.detect_dialogs.return_value = [dialog1, dialog2]

        result = _call_tool(server, "dialog_accept", {"hwnd": 222})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["dialog_title"] == "Second"
        mock_backend.click.assert_called_once_with(x=200, y=200)


class TestDialogDismiss:

    def test_clicks_cancel_button(self, server, mock_backend):
        ok_btn = _make_button("OK", is_default=True, x=100, y=200)
        cancel_btn = _make_button("Cancel", is_cancel=True, x=200, y=200)
        dialog = _make_dialog(title="Save?", buttons=[ok_btn, cancel_btn])
        mock_backend.detect_dialogs.return_value = [dialog]

        result = _call_tool(server, "dialog_dismiss", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["button_clicked"] == "Cancel"
        mock_backend.click.assert_called_once_with(x=200, y=200)

    def test_clicks_no_button(self, server, mock_backend):
        yes_btn = _make_button("Yes", x=100, y=200)
        no_btn = _make_button("No", x=200, y=200)
        dialog = _make_dialog(title="Continue?", buttons=[yes_btn, no_btn])
        mock_backend.detect_dialogs.return_value = [dialog]

        result = _call_tool(server, "dialog_dismiss", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["button_clicked"] == "No"

    def test_clicks_is_cancel_button(self, server, mock_backend):
        custom_btn = _make_button("Abort", is_cancel=True, x=300, y=300)
        dialog = _make_dialog(buttons=[custom_btn])
        mock_backend.detect_dialogs.return_value = [dialog]

        result = _call_tool(server, "dialog_dismiss", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["button_clicked"] == "Abort"

    def test_no_dialog_found(self, server, mock_backend):
        mock_backend.detect_dialogs.return_value = []
        result = _call_tool(server, "dialog_dismiss", {})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "DIALOG_NOT_FOUND"

    def test_no_dismiss_button_available(self, server, mock_backend):
        btn = _make_button("Retry", is_default=False, is_cancel=False)
        dialog = _make_dialog(buttons=[btn])
        mock_backend.detect_dialogs.return_value = [dialog]

        result = _call_tool(server, "dialog_dismiss", {})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "ELEMENT_NOT_FOUND"


class TestDialogClickButton:

    def test_clicks_named_button(self, server, mock_backend):
        mock_backend.dialog_click_button.return_value = {
            "dialog_title": "Save",
            "button_clicked": "Don't Save",
        }
        result = _call_tool(server, "dialog_click_button", {"button": "Don't Save"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["button_clicked"] == "Don't Save"
        mock_backend.dialog_click_button.assert_called_once_with(
            button="Don't Save", app=None, hwnd=None,
        )

    def test_with_app_filter(self, server, mock_backend):
        mock_backend.dialog_click_button.return_value = {"dialog_title": "T", "button_clicked": "OK"}
        _call_tool(server, "dialog_click_button", {"button": "OK", "app": "word"})
        mock_backend.dialog_click_button.assert_called_once_with(
            button="OK", app="word", hwnd=None,
        )

    def test_with_hwnd_filter(self, server, mock_backend):
        mock_backend.dialog_click_button.return_value = {"dialog_title": "T", "button_clicked": "OK"}
        _call_tool(server, "dialog_click_button", {"button": "OK", "hwnd": 55555})
        mock_backend.dialog_click_button.assert_called_once_with(
            button="OK", app=None, hwnd=55555,
        )


class TestDialogType:

    def test_types_text(self, server, mock_backend):
        mock_backend.dialog_set_input.return_value = {
            "dialog_title": "File Name",
            "text_entered": "report.txt",
        }
        mock_backend.detect_dialogs.return_value = []

        result = _call_tool(server, "dialog_type", {"text": "report.txt"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["text_entered"] == "report.txt"
        mock_backend.dialog_set_input.assert_called_once_with(
            text="report.txt", app=None, hwnd=None,
        )

    def test_types_and_accepts(self, server, mock_backend):
        mock_backend.dialog_set_input.return_value = {
            "dialog_title": "Save As",
            "text_entered": "doc.txt",
        }
        ok_btn = _make_button("Save", is_default=True, x=300, y=400)
        dialog = _make_dialog(title="Save As", buttons=[ok_btn])
        mock_backend.detect_dialogs.return_value = [dialog]

        result = _call_tool(server, "dialog_type", {"text": "doc.txt", "accept": True})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["accepted_with"] == "Save"
        mock_backend.click.assert_called_once_with(x=300, y=400)

    def test_accept_no_dialog_after_type(self, server, mock_backend):
        mock_backend.dialog_set_input.return_value = {"dialog_title": "X", "text_entered": "Y"}
        mock_backend.detect_dialogs.return_value = []

        result = _call_tool(server, "dialog_type", {"text": "Y", "accept": True})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "accepted_with" not in data
        mock_backend.click.assert_not_called()

    def test_with_app_and_hwnd(self, server, mock_backend):
        mock_backend.dialog_set_input.return_value = {"dialog_title": "X", "text_entered": "Z"}
        mock_backend.detect_dialogs.return_value = []

        _call_tool(server, "dialog_type", {
            "text": "Z", "app": "excel", "hwnd": 77777,
        })
        mock_backend.dialog_set_input.assert_called_once_with(
            text="Z", app="excel", hwnd=77777,
        )
