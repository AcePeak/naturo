"""MCP tools for taskbar, system tray, and virtual desktops."""
from __future__ import annotations

from typing import Optional


def register_system_tools(server, _get_backend, _safe_tool):
    """Register taskbar, tray, and virtual desktop MCP tools."""

    # ── Taskbar ──────────────────────────────────

    @server.tool()
    @_safe_tool
    def taskbar_list() -> dict:
        """List items on the Windows taskbar.

        Returns running applications and pinned shortcuts visible on the
        taskbar. Use this to discover what apps are available before clicking.

        Returns:
            Dict with success, items list (name, hwnd, is_active, is_pinned),
            and count.
        """
        backend = _get_backend()
        items = backend.taskbar_list()
        return {"success": True, "items": items, "count": len(items)}

    @server.tool()
    @_safe_tool
    def taskbar_click(name: str) -> dict:
        """Click a taskbar item to activate its window.

        Finds a taskbar button matching the name (case-insensitive partial
        match) and clicks it to bring the application to the foreground.

        Args:
            name: Application name or window title (partial match).

        Returns:
            Dict with success, name of clicked item, and click coordinates.
        """
        backend = _get_backend()
        result = backend.taskbar_click(name=name)
        return {"success": True, **result}

    # ── System Tray ──────────────────────────────

    @server.tool()
    @_safe_tool
    def tray_list() -> dict:
        """List system tray (notification area) icons.

        Returns icons in the Windows notification area including both visible
        icons and those in the overflow panel. Use this to discover available
        tray icons before interacting with them.

        Returns:
            Dict with success, icons list (name, tooltip, is_visible), and count.
        """
        backend = _get_backend()
        icons = backend.tray_list()
        return {"success": True, "icons": icons, "count": len(icons)}

    @server.tool()
    @_safe_tool
    def tray_click(
        name: str,
        button: str = "left",
        double_click: bool = False,
    ) -> dict:
        """Click a system tray icon.

        Finds a tray icon matching the name (case-insensitive partial match)
        and clicks it. Use button='right' for context menus, double_click=True
        to open the application.

        Args:
            name: Tray icon tooltip or name (partial match).
            button: Mouse button — 'left' or 'right'.
            double_click: Whether to double-click the icon.

        Returns:
            Dict with success, icon name, tooltip, button used, and coordinates.
        """
        backend = _get_backend()
        result = backend.tray_click(name=name, button=button, double=double_click)
        return {"success": True, **result}

    # ── Virtual Desktop ──────────────────────────

    @server.tool()
    @_safe_tool
    def virtual_desktop_list() -> dict:
        """List all virtual desktops (Windows 10/11).

        Returns each desktop's index, name, whether it is current, and ID.
        Use this to discover available desktops before switching or moving
        windows.

        Returns:
            Dict with success, desktops list, and count.
        """
        backend = _get_backend()
        desktops = backend.virtual_desktop_list()
        return {"success": True, "desktops": desktops, "count": len(desktops)}

    @server.tool()
    @_safe_tool
    def virtual_desktop_switch(index: int) -> dict:
        """Switch to a virtual desktop by index.

        Changes the active desktop. Use virtual_desktop_list to find
        valid indices.

        Args:
            index: Zero-based desktop index.

        Returns:
            Dict with success, switched desktop index and name.
        """
        backend = _get_backend()
        result = backend.virtual_desktop_switch(index)
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def virtual_desktop_create(name: Optional[str] = None) -> dict:
        """Create a new virtual desktop.

        Creates a new desktop and optionally assigns it a name.
        The new desktop is added at the end of the desktop list.

        Args:
            name: Optional name for the new desktop.

        Returns:
            Dict with success, new desktop index, name, and id.
        """
        backend = _get_backend()
        result = backend.virtual_desktop_create(name=name)
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def virtual_desktop_close(index: Optional[int] = None) -> dict:
        """Close a virtual desktop.

        Without index, closes the current desktop. Cannot close the
        last remaining desktop. Windows on the closed desktop are moved
        to an adjacent desktop.

        Args:
            index: Zero-based desktop index. None = current desktop.

        Returns:
            Dict with success, closed desktop index and name.
        """
        backend = _get_backend()
        result = backend.virtual_desktop_close(index=index)
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def virtual_desktop_move_window(
        desktop_index: int,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Move a window to a different virtual desktop.

        Identifies the target window by app name or handle. If neither
        is provided, moves the foreground window.

        Args:
            desktop_index: Target desktop index (zero-based).
            app: Application name (partial match).
            hwnd: Window handle (integer).

        Returns:
            Dict with success, window handle, target desktop index and name.
        """
        backend = _get_backend()
        result = backend.virtual_desktop_move_window(
            desktop_index=desktop_index,
            app=app,
            hwnd=hwnd,
        )
        return {"success": True, **result}
