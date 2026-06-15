"""MCP tools for window and application management."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def register_window_tools(server, _get_backend, _safe_tool):
    """Register window management MCP tools."""

    @server.tool()
    @_safe_tool
    def list_windows() -> dict:
        """List all visible windows on the desktop.

        Returns:
            Dict with success flag and list of windows (title, process, pid, bounds).
        """
        backend = _get_backend()
        windows = backend.list_windows()
        return {
            "success": True,
            "windows": [
                {
                    "handle": w.handle,
                    "title": w.title,
                    "process_name": w.process_name,
                    "pid": w.pid,
                    "x": w.x, "y": w.y,
                    "width": w.width, "height": w.height,
                    "is_visible": w.is_visible,
                    "is_minimized": w.is_minimized,
                }
                for w in windows
            ],
        }

    @server.tool()
    @_safe_tool
    def focus_window(
        title: Optional[str] = None,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Bring a window to the foreground and give it focus.

        Args:
            title: Window title (partial match).
            app: Application/process name (partial match).
            hwnd: Direct window handle.

        Returns:
            Dict with success flag.
        """
        backend = _get_backend()
        backend.focus_window(title=app or title, hwnd=hwnd)
        return {"success": True, "action": "focus"}

    @server.tool()
    @_safe_tool
    def window_close(
        app: Optional[str] = None,
        title: Optional[str] = None,
        hwnd: Optional[int] = None,
        force: bool = False,
    ) -> dict:
        """Close a window (graceful or forced).

        Args:
            app: Application/process name (partial match).
            title: Window title (partial match).
            hwnd: Direct window handle.
            force: If True, forcefully terminate the owning process.

        Returns:
            Dict with success flag.
        """
        backend = _get_backend()
        backend.close_window(title=app or title, hwnd=hwnd, force=force)
        return {"success": True, "action": "close"}

    @server.tool()
    @_safe_tool
    def window_minimize(
        app: Optional[str] = None,
        title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Minimize a window.

        Args:
            app: Application/process name (partial match).
            title: Window title (partial match).
            hwnd: Direct window handle.

        Returns:
            Dict with success flag.
        """
        backend = _get_backend()
        backend.minimize_window(title=app or title, hwnd=hwnd)
        return {"success": True, "action": "minimize"}

    @server.tool()
    @_safe_tool
    def window_maximize(
        app: Optional[str] = None,
        title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Maximize a window.

        Args:
            app: Application/process name (partial match).
            title: Window title (partial match).
            hwnd: Direct window handle.

        Returns:
            Dict with success flag.
        """
        backend = _get_backend()
        backend.maximize_window(title=app or title, hwnd=hwnd)
        return {"success": True, "action": "maximize"}

    @server.tool()
    @_safe_tool
    def window_restore(
        app: Optional[str] = None,
        title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Restore a minimized or maximized window to normal state.

        Args:
            app: Application/process name (partial match).
            title: Window title (partial match).
            hwnd: Direct window handle.

        Returns:
            Dict with success flag.
        """
        backend = _get_backend()
        backend.restore_window(title=app or title, hwnd=hwnd)
        return {"success": True, "action": "restore"}

    @server.tool()
    @_safe_tool
    def window_move(
        x: int,
        y: int,
        app: Optional[str] = None,
        title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Move a window to a position (keeps current size).

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            app: Application/process name (partial match).
            title: Window title (partial match).
            hwnd: Direct window handle.

        Returns:
            Dict with success flag.
        """
        backend = _get_backend()
        backend.move_window(x=x, y=y, title=app or title, hwnd=hwnd)
        return {"success": True, "action": "move", "x": x, "y": y}

    @server.tool()
    @_safe_tool
    def window_resize(
        width: int,
        height: int,
        app: Optional[str] = None,
        title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Resize a window (keeps current position).

        Args:
            width: Target width in pixels (must be >= 1).
            height: Target height in pixels (must be >= 1).
            app: Application/process name (partial match).
            title: Window title (partial match).
            hwnd: Direct window handle.

        Returns:
            Dict with success flag.
        """
        if width < 1 or height < 1:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"width and height must be >= 1, got {width}x{height}"}}
        backend = _get_backend()
        backend.resize_window(width=width, height=height, title=app or title, hwnd=hwnd)
        return {"success": True, "action": "resize", "width": width, "height": height}

    @server.tool()
    @_safe_tool
    def window_set_bounds(
        x: int,
        y: int,
        width: int,
        height: int,
        app: Optional[str] = None,
        title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Set window position and size in one call.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            width: Target width in pixels (must be >= 1).
            height: Target height in pixels (must be >= 1).
            app: Application/process name (partial match).
            title: Window title (partial match).
            hwnd: Direct window handle.

        Returns:
            Dict with success flag.
        """
        if width < 1 or height < 1:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"width and height must be >= 1, got {width}x{height}"}}
        backend = _get_backend()
        backend.set_bounds(x=x, y=y, width=width, height=height, title=app or title, hwnd=hwnd)
        return {"success": True, "action": "set-bounds", "x": x, "y": y, "width": width, "height": height}

    @server.tool()
    @_safe_tool
    def app_hide(name: str) -> dict:
        """Hide (minimize) all windows of an application.

        Args:
            name: Application/process name (partial match).

        Returns:
            Dict with success flag and count of minimized windows.
        """
        backend = _get_backend()
        windows = backend.list_windows()
        name_lower = name.lower()
        matched = [w for w in windows if name_lower in w.process_name.lower() or name_lower in w.title.lower()]
        if not matched:
            from naturo.errors import AppNotFoundError
            raise AppNotFoundError(name)
        count = 0
        for w in matched:
            try:
                backend.minimize_window(hwnd=w.handle)
                count += 1
            except Exception as exc:
                logger.debug("Failed to minimize window %s: %s", w.handle, exc)
        return {"success": True, "action": "hide", "app": name, "windows_minimized": count}

    @server.tool()
    @_safe_tool
    def app_unhide(name: str) -> dict:
        """Unhide (restore) all windows of an application.

        Args:
            name: Application/process name (partial match).

        Returns:
            Dict with success flag and count of restored windows.
        """
        backend = _get_backend()
        windows = backend.list_windows()
        name_lower = name.lower()
        matched = [w for w in windows if name_lower in w.process_name.lower() or name_lower in w.title.lower()]
        if not matched:
            from naturo.errors import AppNotFoundError
            raise AppNotFoundError(name)
        count = 0
        for w in matched:
            try:
                backend.restore_window(hwnd=w.handle)
                count += 1
            except Exception as exc:
                logger.debug("Failed to restore window %s: %s", w.handle, exc)
        return {"success": True, "action": "unhide", "app": name, "windows_restored": count}

    @server.tool()
    @_safe_tool
    def app_switch(name: str) -> dict:
        """Switch to (focus) the most recent window of an application.

        Args:
            name: Application/process name (partial match).

        Returns:
            Dict with success flag, window title and handle.
        """
        backend = _get_backend()
        windows = backend.list_windows()
        name_lower = name.lower()
        matched = [w for w in windows if name_lower in w.process_name.lower() or name_lower in w.title.lower()]
        if not matched:
            from naturo.errors import AppNotFoundError
            raise AppNotFoundError(name)
        target = matched[0]
        backend.focus_window(hwnd=target.handle)
        return {"success": True, "action": "switch", "app": name, "window_title": target.title, "handle": target.handle}

    @server.tool()
    @_safe_tool
    def app_inspect(
        name: Optional[str] = None,
        pid: Optional[int] = None,
        quick: bool = False,
    ) -> dict:
        """Probe an application to detect its UI framework and available interaction methods.

        Detects which UI framework the app uses (Electron, WPF, Qt, Java, etc.)
        and which interaction methods are available (CDP, UIA, MSAA, JAB, IA2, Vision).
        Returns a recommended interaction method.

        Args:
            name: Application name (partial match). Either name or pid required.
            pid: Process ID to inspect directly.
            quick: If True, stop probing at first available method (faster).

        Returns:
            Detection result with frameworks, methods, and recommendation.

        Raises:
            NoDesktopSessionError: If no interactive desktop session exists
                (#885) — otherwise this leaks live process/UI-framework info.
        """
        # (#885) app_inspect probes a live process instead of going through
        # _get_backend(), so guard it explicitly to keep it from leaking
        # running-process details in a NO_DESKTOP_SESSION environment.
        from naturo.cli.interaction import _check_desktop_session
        _check_desktop_session()

        from naturo.detect import detect

        target_pid = pid
        target_exe = ""
        target_name = name or ""

        if name and not pid:
            from naturo.process import find_process
            proc = find_process(name=name)
            if not proc:
                return {
                    "success": False,
                    "error": {
                        "code": "PROCESS_NOT_FOUND",
                        "message": f"No running process found matching '{name}'",
                    },
                }
            target_pid = proc.pid
            target_exe = proc.path or proc.name or ""
            target_name = proc.name or name

        if target_pid is None:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "Specify application name or pid",
                },
            }

        result = detect(
            pid=target_pid,
            exe=target_exe,
            app_name=target_name,
            use_cache=True,
            quick=quick,
        )
        return {"success": True, **result.to_dict()}
