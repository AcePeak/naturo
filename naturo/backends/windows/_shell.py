"""Application control, menus, dialogs, taskbar, tray, and virtual desktops."""

from __future__ import annotations

import logging
from typing import List, Optional

from naturo.backends.base import ElementInfo as BaseElementInfo
from naturo.bridge import populate_hierarchy
from naturo.errors import NaturoError
from naturo.models.menu import MenuItem

logger = logging.getLogger(__name__)


class ShellMixin:
    """Application control, menus, dialogs, taskbar, tray, and virtual desktops."""

    def list_apps(self) -> list[dict]:
        """List running applications with visible, non-minimized windows.

        Filters out known system/framework host processes that have visible
        windows but are not user-facing applications.

        Returns:
            List of dicts with keys: name, pid, title, path, process.
        """
        import os

        windows = self.list_windows()
        seen_pids: set[int] = set()
        seen_uwp: set[tuple[int, str]] = set()
        apps: list[dict] = []
        for w in windows:
            if not w.is_visible or w.is_minimized or w.pid in seen_pids:
                continue
            basename = os.path.basename(w.process_name).lower()
            if basename in self._SYSTEM_PROCESS_NAMES:
                continue
            # Skip windows with empty titles (likely invisible/utility windows)
            if not w.title or not w.title.strip():
                continue
            # UWP apps hosted by ApplicationFrameHost.exe: resolve the
            # real child process PID so it matches `app inspect` output
            # (#267).  The AFH window hosts the UWP app's CoreWindow as a
            # child; that child belongs to the actual app process.
            if basename == self._UWP_HOST_PROCESS:
                real_pid, real_exe = self._resolve_uwp_child_pid(w.handle)
                app_pid = real_pid or w.pid
                app_exe = real_exe or w.process_name
                key = (app_pid, w.title)
                if key in seen_uwp:
                    continue
                seen_uwp.add(key)
                apps.append({
                    "name": w.title,
                    "pid": app_pid,
                    "title": w.title,
                    "path": app_exe,
                    "process": app_exe,
                })
                continue
            seen_pids.add(w.pid)
            apps.append({
                "name": os.path.basename(w.process_name),
                "pid": w.pid,
                "title": w.title,
                "path": w.process_name,
                "process": w.process_name,
            })
        return apps

    def launch_app(self, name: str = "") -> None:
        """Launch an application by name or path.

        Args:
            name: Application name or executable path.

        Raises:
            OSError: If the application cannot be launched.
        """
        import subprocess
        subprocess.Popen([name], shell=True)

    def quit_app(self, name: str = "", force: bool = False) -> None:
        """Quit an application by name or PID.

        Args:
            name: Process name or executable basename.
            force: If True, kills the process immediately (taskkill /F).
        """
        import subprocess
        flag = "/F" if force else ""
        cmd = f'taskkill /IM "{name}" {flag}'.strip()
        subprocess.run(cmd, shell=True, capture_output=True)

    def menu_list(self, app: Optional[str] = None) -> list[dict]:
        """List menu items for an application.

        Uses Win32 Menu API for native menus (reliable, no expansion needed),
        with UIA tree traversal as fallback for custom/non-native menus.

        Args:
            app: Optional application name filter.

        Returns:
            List of dicts representing menu items.
        """
        items = self.get_menu_items(window_title=app)
        return [item.to_dict() for item in items]

    def menu_click(self, path: str = "", app: Optional[str] = None) -> None:
        """Click a menu item. Planned for a future release."""
        raise NotImplementedError("menu_click is not yet implemented")

    def get_menu_items(self, window_title: Optional[str] = None,
                       hwnd: Optional[int] = None) -> List[MenuItem]:
        """Get menu items using Win32 API with UIA fallback.

        Strategy:
        1. Resolve the target window via _resolve_hwnd (respects --app flag).
        2. Try Win32 GetMenu/GetMenuItemInfoW — works for native Win32 menus
           without needing to visually expand them.
        3. If Win32 returns nothing (UWP, Electron, custom menus), fall back
           to UIA MenuBar traversal.

        Args:
            window_title: Optional window title or app name filter.
            hwnd: Optional direct window handle (overrides window_title).

        Returns:
            List of top-level MenuItem objects with nested submenus.
        """
        handle = self._resolve_hwnd(app=window_title, window_title=window_title,
                                    hwnd=hwnd)

        # Strategy 1: Win32 Menu API (native menus)
        items = self._get_menu_items_win32(handle)
        if items:
            return items

        # Strategy 2: UIA tree traversal (custom/non-native menus)
        return self._get_menu_items_uia(handle)

    def _get_menu_items_win32(self, hwnd: int) -> List[MenuItem]:
        """Enumerate menu items via Win32 GetMenu API.

        Uses GetMenu(hwnd) to get the menu bar handle, then recursively
        walks submenus with GetMenuItemCount/GetMenuItemInfoW. This reads
        all items without expanding menus visually.

        Args:
            hwnd: Window handle (0 for foreground window).

        Returns:
            List of MenuItem objects, or empty list if no native menu found.
        """
        import ctypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        # Resolve foreground window if hwnd is 0
        if hwnd == 0:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return []

        menu_handle = user32.GetMenu(hwnd)
        if not menu_handle:
            return []

        return self._walk_win32_menu(menu_handle)

    def _walk_win32_menu(self, hmenu: int) -> List[MenuItem]:
        """Recursively walk a Win32 menu handle and extract items.

        Args:
            hmenu: Win32 HMENU handle.

        Returns:
            List of MenuItem objects.
        """
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        # MENUITEMINFOW structure
        MIIM_STRING = 0x00000040
        MIIM_SUBMENU = 0x00000004
        MIIM_STATE = 0x00000001
        MIIM_FTYPE = 0x00000100
        MFT_SEPARATOR = 0x00000800
        MFS_DISABLED = 0x00000003
        MFS_CHECKED = 0x00000008

        class MENUITEMINFOW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("fMask", wintypes.UINT),
                ("fType", wintypes.UINT),
                ("fState", wintypes.UINT),
                ("wID", wintypes.UINT),
                ("hSubMenu", wintypes.HANDLE),
                ("hbmpChecked", wintypes.HANDLE),
                ("hbmpUnchecked", wintypes.HANDLE),
                ("dwItemData", ctypes.POINTER(ctypes.c_ulong)),
                ("dwTypeData", ctypes.c_wchar_p),
                ("cch", wintypes.UINT),
                ("hbmpItem", wintypes.HANDLE),
            ]

        count = user32.GetMenuItemCount(hmenu)
        if count <= 0:
            return []

        result: List[MenuItem] = []

        for i in range(count):
            mii = MENUITEMINFOW()
            mii.cbSize = ctypes.sizeof(MENUITEMINFOW)
            mii.fMask = MIIM_STRING | MIIM_SUBMENU | MIIM_STATE | MIIM_FTYPE

            # First call: get required buffer size
            mii.dwTypeData = None
            mii.cch = 0
            user32.GetMenuItemInfoW(hmenu, i, True, ctypes.byref(mii))

            if mii.fType & MFT_SEPARATOR:
                continue  # Skip separators

            # Second call: get the actual string
            buf_size = mii.cch + 1
            buf = ctypes.create_unicode_buffer(buf_size)
            mii.dwTypeData = ctypes.cast(buf, ctypes.c_wchar_p)
            mii.cch = buf_size
            mii.fMask = MIIM_STRING | MIIM_SUBMENU | MIIM_STATE | MIIM_FTYPE
            user32.GetMenuItemInfoW(hmenu, i, True, ctypes.byref(mii))

            raw_name = buf.value
            if not raw_name:
                continue

            # Parse accelerator key from name (e.g., "Save\tCtrl+S")
            name = raw_name
            shortcut = None
            if "\t" in raw_name:
                parts = raw_name.split("\t", 1)
                name = parts[0]
                shortcut = parts[1]

            # Strip Win32 ampersand mnemonics (e.g., "&File" -> "File")
            name = name.replace("&", "")

            enabled = not bool(mii.fState & MFS_DISABLED)
            checked = bool(mii.fState & MFS_CHECKED)

            # Recurse into submenus
            submenu = None
            if mii.hSubMenu:
                submenu = self._walk_win32_menu(mii.hSubMenu) or None

            result.append(MenuItem(
                name=name,
                shortcut=shortcut,
                submenu=submenu,
                enabled=enabled,
                checked=checked,
            ))

        return result

    def _get_menu_items_uia(self, hwnd: int) -> List[MenuItem]:
        """Get menu items via UIA MenuBar tree traversal (fallback).

        Used for applications with non-native menus (UWP, Electron, WPF
        with custom menu controls) where Win32 GetMenu returns NULL.

        Args:
            hwnd: Window handle (0 for foreground window).

        Returns:
            List of MenuItem objects from UIA MenuBar elements.
        """
        core = self._ensure_core()
        tree = core.get_element_tree(hwnd=hwnd, depth=6)
        if tree is None:
            return []

        populate_hierarchy(tree)

        menu_bars: list = []
        self._find_by_role(tree, "MenuBar", menu_bars)

        if not menu_bars:
            return []

        result: List[MenuItem] = []
        for bar in menu_bars:
            for child in bar.children:
                item = self._element_to_menu_item(child)
                if item:
                    result.append(item)
        return result

    def _find_by_role(self, el, role: str, results: list) -> None:
        """Recursively find elements matching a role."""
        if el.role == role:
            results.append(el)
        for child in el.children:
            self._find_by_role(child, role, results)

    @staticmethod
    def _element_to_menu_item(el) -> Optional[MenuItem]:
        """Convert a bridge ElementInfo (MenuItem role) to a MenuItem model."""
        if not el.name and el.role not in ("MenuItem", "Menu"):
            return None

        submenu: List[MenuItem] = []
        for child in el.children:
            sub = ShellMixin._element_to_menu_item(child)
            if sub:
                submenu.append(sub)

        return MenuItem(
            name=el.name or "",
            shortcut=el.keyboard_shortcut,
            submenu=submenu if submenu else None,
            enabled=True,  # UIA doesn't easily expose this without caching
            checked=False,
        )

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
            from naturo.errors import NaturoError
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
                from naturo.errors import NaturoError
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
        from naturo.errors import NaturoError, ElementNotFoundError

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
        from naturo.errors import NaturoError

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

    # === Taskbar (Phase 4.5.4) ===

    @staticmethod
    def _find_taskbar_hwnd() -> int:
        """Find the Windows taskbar window handle via FindWindowW.

        Returns:
            HWND of the taskbar (Shell_TrayWnd), or 0 if not found.
        """
        import ctypes
        return ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None) or 0

    @staticmethod
    def _find_child_hwnd(parent: int, class_name: str) -> int:
        """Find a child window by class name using FindWindowExW.

        Args:
            parent: Parent window handle.
            class_name: Window class name to search for.

        Returns:
            HWND of the child window, or 0 if not found.
        """
        import ctypes
        return ctypes.windll.user32.FindWindowExW(parent, 0, class_name, None) or 0

    def taskbar_list(self) -> list[dict]:
        """List items on the Windows taskbar (running apps and pinned shortcuts).

        Scopes the search to the task list area of the taskbar
        (MSTaskListWClass / MSTaskSwWClass inside ReBarWindow32) to avoid
        returning notification-area icons. Falls back to the full taskbar
        tree if the task list sub-window is not found.

        Returns:
            List of dicts with keys: name, hwnd, is_active, is_pinned, x, y,
            width, height.
        """
        core = self._ensure_core()
        taskbar_hwnd = self._find_taskbar_hwnd()
        if taskbar_hwnd == 0:
            return []

        # Locate the task-list area: Shell_TrayWnd → ReBarWindow32 → MSTaskSwWClass → MSTaskListWClass
        target_hwnd = 0
        rebar = self._find_child_hwnd(taskbar_hwnd, "ReBarWindow32")
        if rebar:
            task_sw = self._find_child_hwnd(rebar, "MSTaskSwWClass")
            if task_sw:
                task_list = self._find_child_hwnd(task_sw, "MSTaskListWClass")
                target_hwnd = task_list or task_sw
            else:
                target_hwnd = rebar

        if target_hwnd == 0:
            # Fallback: use full taskbar tree (Windows 11 may differ)
            target_hwnd = taskbar_hwnd

        tree = core.get_element_tree(hwnd=target_hwnd, depth=5)
        if tree is None:
            return []

        items: list[dict] = []
        self._collect_taskbar_buttons(tree, items)
        return items

    def _collect_taskbar_buttons(self, element: BaseElementInfo, items: list) -> None:
        """Recursively collect taskbar button elements from ElementInfo tree.

        Args:
            element: ElementInfo node from get_element_tree.
            items: Accumulator list.
        """
        role = (element.role or "").lower()
        name = element.name or ""

        # Taskbar buttons are Button elements with a non-empty name
        if role == "button" and name:
            items.append({
                "name": name,
                "hwnd": 0,
                "is_active": False,
                "is_pinned": False,
                "x": element.x,
                "y": element.y,
                "width": element.width,
                "height": element.height,
            })

        for child in element.children:
            self._collect_taskbar_buttons(child, items)

    def taskbar_click(self, name: str) -> dict:
        """Click a taskbar item by name.

        Finds a taskbar button matching the name (case-insensitive partial
        match) and clicks its center point. This activates the corresponding
        window.

        Args:
            name: Application name or window title (partial, case-insensitive).

        Returns:
            Dict with dialog_title and button_clicked.

        Raises:
            NaturoError: If no matching taskbar item is found.
        """
        items = self.taskbar_list()
        name_lower = name.lower()

        target = None
        for item in items:
            if name_lower in item["name"].lower():
                target = item
                break

        if target is None:
            available = ", ".join(i["name"] for i in items[:10])
            raise NaturoError(
                message=f"Taskbar item not found: {name}",
                code="TASKBAR_ITEM_NOT_FOUND",
                category="automation",
                suggested_action=f"Available items: [{available}]. "
                                 "Use 'naturo taskbar list' to see all items.",
            )

        cx = target["x"] + target["width"] // 2
        cy = target["y"] + target["height"] // 2
        self.click(x=cx, y=cy)

        return {
            "name": target["name"],
            "clicked_at": {"x": cx, "y": cy},
        }

    # === System Tray (Phase 4.5.5) ===

    def tray_list(self) -> list[dict]:
        """List system tray (notification area) icons.

        Scopes the search to the notification area sub-window
        (TrayNotifyWnd inside Shell_TrayWnd) instead of walking the entire
        taskbar tree. Also checks the overflow panel
        (NotifyIconOverflowWindow) for hidden tray icons.

        Returns:
            List of dicts with keys: name, tooltip, is_visible, x, y, width,
            height.
        """
        import ctypes

        core = self._ensure_core()
        icons: list[dict] = []

        # Primary notification area: Shell_TrayWnd → TrayNotifyWnd
        taskbar_hwnd = self._find_taskbar_hwnd()
        if taskbar_hwnd:
            tray_notify = self._find_child_hwnd(taskbar_hwnd, "TrayNotifyWnd")
            target_hwnd = tray_notify or taskbar_hwnd
            tree = core.get_element_tree(hwnd=target_hwnd, depth=6)
            if tree is not None:
                self._collect_tray_icons(tree, icons)

        # Overflow panel is a separate top-level window
        overflow_hwnd = ctypes.windll.user32.FindWindowW(
            "NotifyIconOverflowWindow", None
        ) or 0
        if overflow_hwnd:
            overflow_tree = core.get_element_tree(hwnd=overflow_hwnd, depth=4)
            if overflow_tree is not None:
                self._collect_tray_icons(overflow_tree, icons)

        return icons

    def _collect_tray_icons(self, element: BaseElementInfo, icons: list) -> None:
        """Recursively collect system tray icon elements from ElementInfo tree.

        Args:
            element: ElementInfo node from get_element_tree.
            icons: Accumulator list.
        """
        role = (element.role or "").lower()
        name = element.name or ""

        # Tray icons appear as Button elements with a name
        if role == "button" and name:
            icons.append({
                "name": name,
                "tooltip": name,
                "is_visible": bool(element.width > 0),
                "x": element.x,
                "y": element.y,
                "width": element.width,
                "height": element.height,
            })

        for child in element.children:
            self._collect_tray_icons(child, icons)

    def tray_click(
        self,
        name: str,
        button: str = "left",
        double: bool = False,
    ) -> dict:
        """Click a system tray icon.

        Finds a tray icon matching the name (case-insensitive partial match)
        and clicks it. Supports left/right click and double-click.

        Args:
            name: Tray icon tooltip or name (partial, case-insensitive).
            button: Mouse button ('left' or 'right').
            double: Whether to double-click.

        Returns:
            Dict with result info.

        Raises:
            NaturoError: If no matching tray icon is found.
        """
        icons = self.tray_list()
        name_lower = name.lower()

        target = None
        for icon in icons:
            if name_lower in icon["name"].lower() or name_lower in icon.get("tooltip", "").lower():
                target = icon
                break

        if target is None:
            available = ", ".join(i["name"] for i in icons[:10])
            raise NaturoError(
                message=f"Tray icon not found: {name}",
                code="TRAY_ICON_NOT_FOUND",
                category="automation",
                suggested_action=f"Available icons: [{available}]. "
                                 "Use 'naturo tray list' to see all icons.",
            )

        cx = target["x"] + target["width"] // 2
        cy = target["y"] + target["height"] // 2
        self.click(x=cx, y=cy, button=button, double=double)

        return {
            "name": target["name"],
            "tooltip": target.get("tooltip", ""),
            "button": button,
            "double_click": double,
            "clicked_at": {"x": cx, "y": cy},
        }

    # === Virtual Desktop (Phase 5A.3) ===

    def virtual_desktop_list(self) -> list[dict]:
        """List all virtual desktops.

        Uses IVirtualDesktopManagerInternal COM interface via the pyvda library
        when available, otherwise falls back to registry-based detection.

        Returns:
            List of dicts with keys: index, name, is_current, id.
        """
        try:
            import pyvda
            desktops = pyvda.get_virtual_desktops()
            current = pyvda.VirtualDesktop.current()
            result = []
            for i, d in enumerate(desktops):
                result.append({
                    "index": i,
                    "name": d.name or f"Desktop {i + 1}",
                    "is_current": d.number == current.number,
                    "id": str(d.id) if hasattr(d, "id") else str(i),
                })
            return result
        except ImportError:
            raise NaturoError(
                message="Virtual desktop support requires pyvda. Install: pip install naturo[desktop]",
                code="DEPENDENCY_MISSING",
                category="system",
                suggested_action="Run 'pip install naturo[desktop]' to enable virtual desktop features.",
            )
        except Exception as e:
            raise NaturoError(
                message=f"Failed to enumerate virtual desktops: {e}",
                code="VIRTUAL_DESKTOP_ERROR",
                category="system",
                suggested_action="Ensure running on Windows 10/11 with virtual desktop support.",
            )

    def virtual_desktop_switch(self, index: int) -> dict:
        """Switch to a virtual desktop by index.

        Args:
            index: Zero-based desktop index.

        Returns:
            Dict with switched desktop info.
        """
        try:
            import pyvda
            desktops = pyvda.get_virtual_desktops()
            if index < 0 or index >= len(desktops):
                raise NaturoError(
                    message=f"Desktop index {index} out of range (0-{len(desktops) - 1})",
                    code="INVALID_INPUT",
                    category="input",
                    suggested_action=f"Use index 0-{len(desktops) - 1}. "
                                     "Run 'naturo desktop list' to see available desktops.",
                )
            target = desktops[index]
            target.go()
            return {
                "index": index,
                "name": target.name or f"Desktop {index + 1}",
            }
        except ImportError:
            raise NaturoError(
                message="Virtual desktop support requires pyvda. Install: pip install naturo[desktop]",
                code="DEPENDENCY_MISSING",
                category="system",
                suggested_action="Run 'pip install naturo[desktop]' to enable virtual desktop features.",
            )
        except NaturoError:
            raise
        except Exception as e:
            raise NaturoError(
                message=f"Failed to switch desktop: {e}",
                code="VIRTUAL_DESKTOP_ERROR",
                category="system",
            )

    def virtual_desktop_create(self, name: Optional[str] = None) -> dict:
        """Create a new virtual desktop.

        Args:
            name: Optional name for the new desktop.

        Returns:
            Dict with new desktop info.
        """
        try:
            import pyvda
            new_desktop = pyvda.VirtualDesktop.create()
            if name and hasattr(new_desktop, "rename"):
                new_desktop.rename(name)
            desktops = pyvda.get_virtual_desktops()
            new_index = len(desktops) - 1
            return {
                "index": new_index,
                "name": name or f"Desktop {new_index + 1}",
                "id": str(new_desktop.id) if hasattr(new_desktop, "id") else str(new_index),
            }
        except ImportError:
            raise NaturoError(
                message="Virtual desktop support requires pyvda. Install: pip install naturo[desktop]",
                code="DEPENDENCY_MISSING",
                category="system",
                suggested_action="Run 'pip install naturo[desktop]' to enable virtual desktop features.",
            )
        except Exception as e:
            raise NaturoError(
                message=f"Failed to create desktop: {e}",
                code="VIRTUAL_DESKTOP_ERROR",
                category="system",
            )

    def virtual_desktop_close(self, index: Optional[int] = None) -> dict:
        """Close a virtual desktop.

        Args:
            index: Zero-based desktop index. Closes current if None.

        Returns:
            Dict with closed desktop info.
        """
        try:
            import pyvda
            desktops = pyvda.get_virtual_desktops()

            if len(desktops) <= 1:
                raise NaturoError(
                    message="Cannot close the last virtual desktop",
                    code="VIRTUAL_DESKTOP_ERROR",
                    category="system",
                    suggested_action="At least one desktop must remain.",
                )

            if index is not None:
                if index < 0 or index >= len(desktops):
                    raise NaturoError(
                        message=f"Desktop index {index} out of range (0-{len(desktops) - 1})",
                        code="INVALID_INPUT",
                        category="input",
                    )
                target = desktops[index]
            else:
                target = pyvda.VirtualDesktop.current()
                index = next(
                    (i for i, d in enumerate(desktops) if d.number == target.number),
                    0,
                )

            target_name = target.name or f"Desktop {index + 1}"
            target.remove()
            return {
                "index": index,
                "name": target_name,
            }
        except ImportError:
            raise NaturoError(
                message="Virtual desktop support requires pyvda. Install: pip install naturo[desktop]",
                code="DEPENDENCY_MISSING",
                category="system",
                suggested_action="Run 'pip install naturo[desktop]' to enable virtual desktop features.",
            )
        except NaturoError:
            raise
        except Exception as e:
            raise NaturoError(
                message=f"Failed to close desktop: {e}",
                code="VIRTUAL_DESKTOP_ERROR",
                category="system",
            )

    def virtual_desktop_move_window(
        self,
        desktop_index: int,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Move a window to a different virtual desktop.

        Args:
            desktop_index: Target desktop index.
            app: Application name (partial match).
            hwnd: Window handle.

        Returns:
            Dict with result info.
        """
        try:
            import pyvda
            desktops = pyvda.get_virtual_desktops()

            if desktop_index < 0 or desktop_index >= len(desktops):
                raise NaturoError(
                    message=f"Desktop index {desktop_index} out of range (0-{len(desktops) - 1})",
                    code="INVALID_INPUT",
                    category="input",
                )

            # Resolve window handle
            handle = hwnd
            if not handle and app:
                handle = self._resolve_hwnd(app=app)

            if not handle:
                import ctypes
                handle = ctypes.windll.user32.GetForegroundWindow()

            if not handle:
                raise NaturoError(
                    message="No window found to move",
                    code="WINDOW_NOT_FOUND",
                    category="automation",
                )

            target = desktops[desktop_index]
            window = pyvda.AppView(handle)
            window.move(target)

            return {
                "hwnd": handle,
                "target_desktop": desktop_index,
                "target_name": target.name or f"Desktop {desktop_index + 1}",
            }
        except ImportError:
            raise NaturoError(
                message="Virtual desktop support requires pyvda. Install: pip install naturo[desktop]",
                code="DEPENDENCY_MISSING",
                category="system",
                suggested_action="Run 'pip install naturo[desktop]' to enable virtual desktop features.",
            )
        except NaturoError:
            raise
        except Exception as e:
            raise NaturoError(
                message=f"Failed to move window: {e}",
                code="VIRTUAL_DESKTOP_ERROR",
                category="system",
            )
