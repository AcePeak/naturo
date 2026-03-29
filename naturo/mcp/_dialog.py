"""MCP tools for dialog detection and interaction."""
from __future__ import annotations

from typing import Optional


def register_dialog_tools(server, _get_backend, _safe_tool):
    """Register dialog MCP tools."""

    @server.tool()
    @_safe_tool
    def dialog_detect(
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Detect active dialog windows (message boxes, file pickers, etc.).

        Scans for system dialogs and returns their type, title, message text,
        available buttons, and whether an input field is present. Essential for
        handling dialogs that block automation workflows.

        Args:
            app: Filter by owner application name (partial match).
            hwnd: Filter by specific dialog window handle.

        Returns:
            Dict with success, dialogs list, and count.
        """
        backend = _get_backend()
        dialogs = backend.detect_dialogs(app=app, hwnd=hwnd)
        return {
            "success": True,
            "dialogs": [d.to_dict() for d in dialogs],
            "count": len(dialogs),
        }

    @server.tool()
    @_safe_tool
    def dialog_accept(
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Accept (confirm) the active dialog by clicking OK/Yes/Open/Save.

        Finds the first accept-type button and clicks it. Use when a dialog
        is blocking the workflow and you want to proceed.

        Args:
            app: Filter by owner application name.
            hwnd: Filter by specific dialog window handle.

        Returns:
            Dict with dialog title and button clicked.
        """
        backend = _get_backend()
        from naturo.dialog import _ACCEPT_BUTTONS

        dialogs = backend.detect_dialogs(app=app, hwnd=hwnd)
        if not dialogs:
            return {
                "success": False,
                "error": {"code": "DIALOG_NOT_FOUND", "message": "No dialog detected"},
            }

        target = dialogs[0]
        if hwnd:
            target = next((d for d in dialogs if d.hwnd == hwnd), dialogs[0])

        for btn in target.buttons:
            if btn.name.lower() in _ACCEPT_BUTTONS or btn.is_default:
                backend.click(x=btn.x, y=btn.y)
                return {
                    "success": True,
                    "dialog_title": target.title,
                    "button_clicked": btn.name,
                    "dialog_hwnd": target.hwnd,
                }

        available = ", ".join(b.name for b in target.buttons)
        return {
            "success": False,
            "error": {
                "code": "ELEMENT_NOT_FOUND",
                "message": f"No accept button found. Available: [{available}]",
            },
        }

    @server.tool()
    @_safe_tool
    def dialog_dismiss(
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Dismiss (cancel) the active dialog by clicking Cancel/No/Close.

        Finds the first dismiss-type button and clicks it. Use when you want
        to cancel a dialog without proceeding.

        Args:
            app: Filter by owner application name.
            hwnd: Filter by specific dialog window handle.

        Returns:
            Dict with dialog title and button clicked.
        """
        backend = _get_backend()
        from naturo.dialog import _DISMISS_BUTTONS

        dialogs = backend.detect_dialogs(app=app, hwnd=hwnd)
        if not dialogs:
            return {
                "success": False,
                "error": {"code": "DIALOG_NOT_FOUND", "message": "No dialog detected"},
            }

        target = dialogs[0]
        if hwnd:
            target = next((d for d in dialogs if d.hwnd == hwnd), dialogs[0])

        for btn in target.buttons:
            if btn.name.lower() in _DISMISS_BUTTONS or btn.is_cancel:
                backend.click(x=btn.x, y=btn.y)
                return {
                    "success": True,
                    "dialog_title": target.title,
                    "button_clicked": btn.name,
                    "dialog_hwnd": target.hwnd,
                }

        available = ", ".join(b.name for b in target.buttons)
        return {
            "success": False,
            "error": {
                "code": "ELEMENT_NOT_FOUND",
                "message": f"No dismiss button found. Available: [{available}]",
            },
        }

    @server.tool()
    @_safe_tool
    def dialog_click_button(
        button: str,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Click a specific button in the active dialog by name.

        Supports exact and partial name matching (case-insensitive).
        Use 'dialog_detect' first to see available buttons.

        Args:
            button: Button text to click (e.g., "Save", "Don't Save", "Retry").
            app: Filter by owner application name.
            hwnd: Filter by specific dialog window handle.

        Returns:
            Dict with dialog title and button clicked.
        """
        backend = _get_backend()
        result = backend.dialog_click_button(button=button, app=app, hwnd=hwnd)
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def dialog_type(
        text: str,
        accept: bool = False,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Type text into a dialog's input field.

        Finds the dialog's input/edit control, clears it, and types the text.
        With accept=True, also clicks the OK/Save button afterward.

        Args:
            text: Text to type in the input field.
            accept: Click the accept button after typing.
            app: Filter by owner application name.
            hwnd: Filter by specific dialog window handle.

        Returns:
            Dict with dialog title, text entered, and optional accept button.
        """
        backend = _get_backend()
        result = backend.dialog_set_input(text=text, app=app, hwnd=hwnd)
        response = {"success": True, **result}

        if accept:
            from naturo.dialog import _ACCEPT_BUTTONS
            dialogs = backend.detect_dialogs(app=app, hwnd=hwnd)
            if dialogs:
                for btn in dialogs[0].buttons:
                    if btn.name.lower() in _ACCEPT_BUTTONS or btn.is_default:
                        backend.click(x=btn.x, y=btn.y)
                        response["accepted_with"] = btn.name
                        break

        return response
