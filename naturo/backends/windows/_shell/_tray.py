"""System tray (notification area) enumeration and interaction."""

from __future__ import annotations

from naturo.backends.base import ElementInfo as BaseElementInfo
from naturo.errors import NaturoError


class TrayMixin:
    """List and click system tray icons."""

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
