"""Windows taskbar enumeration and interaction."""

from __future__ import annotations

from naturo.backends.base import ElementInfo as BaseElementInfo
from naturo.errors import NaturoError


class TaskbarMixin:
    """List and click Windows taskbar items."""

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
