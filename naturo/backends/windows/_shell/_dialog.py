"""URI opening, dialog detection, and dialog interaction."""

from __future__ import annotations

from typing import Optional

from naturo.errors import NaturoError


class DialogMixin:
    """Open URIs, detect dialogs, click buttons, and set input fields."""

    def open_uri(self, uri: str = "") -> None:
        """Open a URI with the default handler.

        Args:
            uri: URL or file path to open.

        Raises:
            NaturoError: If target is a file path that does not exist,
                or if the open command times out.
        """
        import os
        import subprocess

        # BUG-067: Check file existence for non-URL targets to avoid
        # Windows 'start' blocking on an error dialog
        is_url = uri.startswith(("http://", "https://", "ftp://", "mailto:"))
        if not is_url and not os.path.exists(uri):
            raise NaturoError(
                f"File not found: {uri}",
                code="FILE_NOT_FOUND",
            )

        if is_url:
            # URLs: fire-and-forget — don't wait for browser process
            subprocess.Popen(
                ["start", "", uri], shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            # Files/apps: wait briefly for the handler to launch
            try:
                subprocess.run(
                    ["start", "", uri], shell=True, timeout=15,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired:
                raise NaturoError(
                    f"Open command timed out for: {uri}",
                    code="OPEN_TIMEOUT",
                )

    # === Phase 4.5: Dialog Detection & Interaction ===

    def detect_dialogs(
        self,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> list:
        """Detect active dialog windows using Win32 API + UIA.

        Identifies standard Win32 dialogs (#32770 class), modal windows,
        and common dialog types (file pickers, message boxes, etc.).

        Args:
            app: Filter by owner application name (partial match, case-insensitive).
            hwnd: Filter by specific dialog window handle.

        Returns:
            List of DialogInfo objects for detected dialogs.
        """
        self._ensure_win32()
        import ctypes
        from naturo.dialog import (
            DialogInfo, DialogButton, classify_dialog,
        )

        user32 = ctypes.windll.user32

        # Get all visible top-level windows
        all_windows = self.list_windows()

        # If specific hwnd requested, filter
        if hwnd:
            all_windows = [w for w in all_windows if w.handle == hwnd]

        # If app filter, narrow down
        if app:
            app_lower = app.lower()
            all_windows = [
                w for w in all_windows
                if app_lower in w.title.lower() or app_lower in w.process_name.lower()
            ]

        dialogs: list[DialogInfo] = []

        for win in all_windows:
            # Get window class name
            class_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(win.handle, class_buf, 256)
            class_name = class_buf.value

            # Check if this is a dialog window
            is_dialog = False

            # Method 1: Standard dialog class name
            if class_name == "#32770":
                is_dialog = True

            # Method 2: Check window style for DS_MODALFRAME (dialog style)
            GWL_EXSTYLE = -20
            WS_EX_DLGMODALFRAME = 0x00000001

            ex_style = user32.GetWindowLongW(win.handle, GWL_EXSTYLE)

            if ex_style & WS_EX_DLGMODALFRAME:
                is_dialog = True

            # Method 3: Check if window has an owner (modal dialogs typically do)
            owner_hwnd = user32.GetWindow(win.handle, 4)  # GW_OWNER = 4
            if owner_hwnd and class_name == "#32770":
                is_dialog = True

            if not is_dialog:
                continue

            # Inspect the dialog's UI tree to find buttons, text, inputs
            try:
                tree = self.get_element_tree(hwnd=win.handle, depth=4)
            except Exception:
                tree = None

            buttons: list[DialogButton] = []
            message_parts: list[str] = []
            has_edit = False
            edit_value = ""
            has_file_list = False

            if tree:
                self._scan_dialog_elements(
                    tree, buttons, message_parts, has_edit_ref=[False],
                    edit_value_ref=[""], has_file_list_ref=[False],
                )
                has_edit = any(
                    el.role.lower() in ("edit", "combobox", "editable text")
                    for el in self._flatten_elements(tree)
                )
                for el in self._flatten_elements(tree):
                    if el.role.lower() in ("edit", "editable text"):
                        edit_value = el.value or ""
                        has_edit = True
                    if el.role.lower() in ("list", "listview", "tree"):
                        # Could be a file list in file dialogs
                        has_file_list = True

            # Classify dialog type
            button_names = [b.name for b in buttons]
            dialog_type = classify_dialog(
                title=win.title,
                class_name=class_name,
                buttons=button_names,
                has_edit=has_edit,
                has_file_list=has_file_list,
            )

            # Find owner app
            owner_app = ""
            if owner_hwnd:
                for ow in self.list_windows():
                    if ow.handle == owner_hwnd:
                        owner_app = ow.process_name
                        break

            message = " ".join(message_parts).strip()

            dialogs.append(DialogInfo(
                hwnd=win.handle,
                title=win.title,
                dialog_type=dialog_type,
                message=message,
                buttons=buttons,
                has_input=has_edit,
                input_value=edit_value,
                owner_app=owner_app,
                owner_hwnd=owner_hwnd or 0,
            ))

        return dialogs

    def _flatten_elements(self, element) -> list:
        """Recursively flatten an element tree into a list.

        Args:
            element: Root ElementInfo node.

        Returns:
            Flat list of all ElementInfo nodes.
        """
        result = [element]
        for child in (element.children or []):
            result.extend(self._flatten_elements(child))
        return result

    def _scan_dialog_elements(
        self,
        element,
        buttons: list,
        message_parts: list[str],
        has_edit_ref: list[bool],
        edit_value_ref: list[str],
        has_file_list_ref: list[bool],
    ) -> None:
        """Recursively scan dialog elements to extract buttons, text, and inputs.

        Args:
            element: Current ElementInfo node.
            buttons: Accumulator for DialogButton objects.
            message_parts: Accumulator for message text.
            has_edit_ref: Mutable ref — [True] if an edit control was found.
            edit_value_ref: Mutable ref — [value] of the first edit control.
            has_file_list_ref: Mutable ref — [True] if a file list was found.
        """
        from naturo.dialog import DialogButton, _ACCEPT_BUTTONS, _DISMISS_BUTTONS

        role = (element.role or "").lower()
        name = element.name or ""

        if role == "button" and name:
            name_lower = name.lower()
            is_default = name_lower in _ACCEPT_BUTTONS
            is_cancel = name_lower in _DISMISS_BUTTONS
            buttons.append(DialogButton(
                name=name,
                element_id=element.id,
                is_default=is_default,
                is_cancel=is_cancel,
                x=element.x + element.width // 2,
                y=element.y + element.height // 2,
            ))
        elif role in ("text", "static text", "label") and name:
            message_parts.append(name)
        elif role in ("edit", "editable text"):
            has_edit_ref[0] = True
            if element.value:
                edit_value_ref[0] = element.value
        elif role in ("list", "listview", "tree", "list view"):
            has_file_list_ref[0] = True

        for child in (element.children or []):
            self._scan_dialog_elements(
                child, buttons, message_parts,
                has_edit_ref, edit_value_ref, has_file_list_ref,
            )

    def dialog_click_button(
        self,
        button: str,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Click a button in a detected dialog.

        Finds the dialog, locates the button by name, and clicks it.

        Args:
            button: Button text to click (case-insensitive partial match).
            app: Owner application name filter.
            hwnd: Specific dialog window handle.

        Returns:
            Dict with action result: {"dialog_title", "button_clicked", "dialog_hwnd"}.

        Raises:
            NaturoError: If no dialog or button found.
        """
        from naturo.errors import ElementNotFoundError

        dialogs = self.detect_dialogs(app=app, hwnd=hwnd)
        if not dialogs:
            raise NaturoError(
                message="No dialog detected",
                code="DIALOG_NOT_FOUND",
                category="automation",
                suggested_action="No active dialog found. Use 'naturo dialog detect' to check for dialogs, "
                                 "or 'naturo wait --element \"Button:OK\"' to wait for one to appear.",
                is_recoverable=True,
            )

        # Use first dialog if no hwnd specified
        dialog = dialogs[0]
        if hwnd:
            dialog = next((d for d in dialogs if d.hwnd == hwnd), dialogs[0])

        # Find the button
        button_lower = button.lower()
        target_btn = None
        for btn in dialog.buttons:
            if button_lower == btn.name.lower():
                target_btn = btn
                break
        if not target_btn:
            # Try partial match
            for btn in dialog.buttons:
                if button_lower in btn.name.lower():
                    target_btn = btn
                    break

        if not target_btn:
            available = ", ".join(b.name for b in dialog.buttons)
            raise ElementNotFoundError(
                f"Button:{button}",
                suggested_action=f"Button '{button}' not found in dialog. "
                                 f"Available buttons: [{available}]. "
                                 f"Use 'naturo dialog detect --json' to see all buttons.",
            )

        # Click the button
        self.click(x=target_btn.x, y=target_btn.y)

        return {
            "dialog_title": dialog.title,
            "button_clicked": target_btn.name,
            "dialog_hwnd": dialog.hwnd,
        }

    def dialog_set_input(
        self,
        text: str,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Type text into a dialog's input field.

        Finds the dialog, focuses the first edit control, clears it,
        and types the provided text.

        Args:
            text: Text to enter in the dialog's input field.
            app: Owner application name filter.
            hwnd: Specific dialog window handle.

        Returns:
            Dict with action result: {"dialog_title", "text_entered", "dialog_hwnd"}.

        Raises:
            NaturoError: If no dialog or input field found.
        """
        dialogs = self.detect_dialogs(app=app, hwnd=hwnd)
        if not dialogs:
            raise NaturoError(
                message="No dialog detected",
                code="DIALOG_NOT_FOUND",
                category="automation",
                suggested_action="No active dialog found.",
                is_recoverable=True,
            )

        dialog = dialogs[0]
        if hwnd:
            dialog = next((d for d in dialogs if d.hwnd == hwnd), dialogs[0])

        if not dialog.has_input:
            raise NaturoError(
                message="Dialog has no input field",
                code="ELEMENT_NOT_FOUND",
                category="automation",
                suggested_action="This dialog does not have a text input field. "
                                 "Use 'naturo dialog detect --json' to inspect the dialog.",
            )

        # Focus the dialog window first
        self.focus_window(hwnd=dialog.hwnd)

        # Find the edit control and click it
        tree = self.get_element_tree(hwnd=dialog.hwnd, depth=4)
        if tree:
            for el in self._flatten_elements(tree):
                if (el.role or "").lower() in ("edit", "editable text"):
                    # Click the edit control to focus it
                    cx = el.x + el.width // 2
                    cy = el.y + el.height // 2
                    self.click(x=cx, y=cy)
                    # Select all existing text and replace
                    self.hotkey("ctrl", "a")
                    self.type_text(text)
                    return {
                        "dialog_title": dialog.title,
                        "text_entered": text,
                        "dialog_hwnd": dialog.hwnd,
                    }

        raise NaturoError(
            message="Could not find input field in dialog",
            code="ELEMENT_NOT_FOUND",
            category="automation",
        )
