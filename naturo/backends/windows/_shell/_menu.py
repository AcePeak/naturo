"""Menu enumeration via Win32 API and UIA fallback."""

from __future__ import annotations

from typing import List, Optional

from naturo.bridge import populate_hierarchy
from naturo.models.menu import MenuItem


class MenuMixin:
    """List and interact with application menus."""

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
            sub = MenuMixin._element_to_menu_item(child)
            if sub:
                submenu.append(sub)

        return MenuItem(
            name=el.name or "",
            shortcut=el.keyboard_shortcut,
            submenu=submenu if submenu else None,
            enabled=True,  # UIA doesn't easily expose this without caching
            checked=False,
        )
