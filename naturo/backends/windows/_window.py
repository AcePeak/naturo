"""Window enumeration and management (focus, close, move, resize)."""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from typing import Optional

from naturo.backends.base import WindowInfo as BaseWindowInfo

logger = logging.getLogger(__name__)


class WindowMixin:
    """Window enumeration and management (focus, close, move, resize)."""

    # === Window Management (Phase 1: list only) ===

    def list_windows(self) -> list[BaseWindowInfo]:
        """List all visible top-level windows.

        UWP/packaged apps hosted by ``ApplicationFrameHost.exe`` are resolved
        to their real child process, so the reported ``pid``/``process_name``
        identify the owning app rather than the host. This matches what
        ``list_apps`` reports for the same window handle (#958, mirroring the
        ``list_apps`` resolution added in #267/#276).

        Returns:
            List of WindowInfo dataclass instances.
        """
        return [self._resolve_uwp_window(w) for w in self._list_windows_unresolved()]

    def _list_windows_unresolved(self) -> list[BaseWindowInfo]:
        """Enumerate top-level windows straight from the core bridge.

        UWP windows still carry the ``ApplicationFrameHost.exe`` host PID and
        executable here — no resolution is applied. ``list_apps`` consumes this
        raw view because it performs its own UWP child resolution and naming,
        keyed off the host basename (see ``AppMixin.list_apps``); resolving here
        would hide the host marker it depends on.

        Returns:
            List of WindowInfo dataclass instances as reported by the bridge.
        """
        core = self._ensure_core()
        bridge_windows = core.list_windows()
        return [
            BaseWindowInfo(
                handle=w.hwnd,
                title=w.title,
                process_name=w.process_name,
                pid=w.pid,
                x=w.x,
                y=w.y,
                width=w.width,
                height=w.height,
                is_visible=w.is_visible,
                is_minimized=w.is_minimized,
            )
            for w in bridge_windows
        ]

    def _resolve_uwp_window(self, window: BaseWindowInfo) -> BaseWindowInfo:
        """Resolve a UWP host window to the real owning app process (#958).

        ``ApplicationFrameHost.exe`` hosts UWP apps as child windows, so the
        bridge reports the host's PID/executable for the top-level window. When
        ``window`` belongs to the host, substitute the real child PID and
        executable (resolved via ``_resolve_uwp_child_pid``). Non-UWP windows,
        and host windows whose child cannot be resolved, are returned unchanged.

        Args:
            window: A window enumerated by ``_list_windows_unresolved``.

        Returns:
            The window with the real PID/process_name when it is a resolvable
            UWP host window; otherwise the original window unchanged.
        """
        if os.path.basename(window.process_name).lower() != self._UWP_HOST_PROCESS:
            return window
        real_pid, real_exe = self._resolve_uwp_child_pid(window.handle)
        if not real_pid or not real_exe:
            return window
        return replace(window, pid=real_pid, process_name=real_exe)

    def _ensure_win32(self) -> None:
        """Verify we are running on Windows; raise NotImplementedError otherwise.

        Raises:
            NotImplementedError: When running on a non-Windows platform.
        """
        import platform as _platform
        if _platform.system() != "Windows":
            raise NotImplementedError("Window management requires Windows")

    def _get_window_rect(self, handle: int) -> tuple[int, int, int, int]:
        """Get window rectangle (left, top, right, bottom) via Win32 GetWindowRect.

        Args:
            handle: Window handle (HWND).

        Returns:
            Tuple of (left, top, right, bottom).

        Raises:
            naturo.errors.WindowNotFoundError: If the handle is invalid.
        """
        import ctypes
        import ctypes.wintypes
        rect = ctypes.wintypes.RECT()
        result = ctypes.windll.user32.GetWindowRect(handle, ctypes.byref(rect))
        if not result:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(str(handle))
        return rect.left, rect.top, rect.right, rect.bottom

    def _is_iconic(self, handle: int) -> bool:
        """Check if a window is minimized (iconic).

        Args:
            handle: Window handle (HWND).

        Returns:
            True if the window is minimized.
        """
        import ctypes
        return bool(ctypes.windll.user32.IsIconic(handle))

    def focus_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Focus a window by title or handle.

        Brings the window to the foreground. If the window is minimized,
        it is restored first.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        SW_RESTORE = 9
        SW_SHOW = 5
        if self._is_iconic(handle):
            ctypes.windll.user32.ShowWindow(handle, SW_RESTORE)

        # SetForegroundWindow is silently ignored when the caller is a
        # background process (the MCP server never holds the foreground): the
        # old single-shot attempt returned while the window did NOT come
        # forward, so subsequent keystroke/paste landed in the WRONG window.
        # Harden it: clear the foreground-lock timeout, then retry
        # AttachThreadInput + foreground + activate + focus, VERIFYING
        # GetForegroundWindow each round until the switch actually sticks.
        import time
        u = ctypes.windll.user32
        current_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        target_tid = u.GetWindowThreadProcessId(handle, None)
        # Clear SPI_SETFOREGROUNDLOCKTIMEOUT (0x2000) so a background process is
        # allowed to steal the foreground; SPIF_SENDCHANGE (0x2) broadcasts it.
        try:
            u.SystemParametersInfoW(0x2000, 0, 0, 0x2)
        except Exception:
            pass
        for _attempt in range(6):
            if u.GetForegroundWindow() == handle:
                return
            foreground_hwnd = u.GetForegroundWindow()
            fg_tid = u.GetWindowThreadProcessId(foreground_hwnd, None)
            attached_target = False
            attached_fg = False
            try:
                if current_tid != target_tid:
                    attached_target = bool(u.AttachThreadInput(current_tid, target_tid, True))
                if current_tid != fg_tid and fg_tid != target_tid:
                    attached_fg = bool(u.AttachThreadInput(current_tid, fg_tid, True))

                u.ShowWindow(handle, SW_SHOW)
                u.BringWindowToTop(handle)
                u.SetForegroundWindow(handle)
                u.SetActiveWindow(handle)
                u.SetFocus(handle)
            finally:
                if attached_target:
                    u.AttachThreadInput(current_tid, target_tid, False)
                if attached_fg:
                    u.AttachThreadInput(current_tid, fg_tid, False)

            if u.GetForegroundWindow() == handle:
                return
            time.sleep(0.04)

    def close_window(self, title: Optional[str] = None, hwnd: Optional[int] = None,
                     force: bool = False) -> None:
        """Close a window by title or handle.

        Sends WM_CLOSE for graceful close, or terminates the process if force is True.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).
            force: If True, forcefully terminate the owning process.

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")

        if force:
            # Get PID and terminate the process
            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
            PROCESS_TERMINATE = 0x0001
            proc_handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid.value)
            if proc_handle:
                ctypes.windll.kernel32.TerminateProcess(proc_handle, 1)
                ctypes.windll.kernel32.CloseHandle(proc_handle)
        else:
            WM_CLOSE = 0x0010
            ctypes.windll.user32.SendMessageW(handle, WM_CLOSE, 0, 0)

    def minimize_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Minimize a window.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        SW_MINIMIZE = 6
        ctypes.windll.user32.ShowWindow(handle, SW_MINIMIZE)

    def maximize_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Maximize a window.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        SW_MAXIMIZE = 3
        ctypes.windll.user32.ShowWindow(handle, SW_MAXIMIZE)

    def restore_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Restore a minimized or maximized window to its normal state.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        SW_RESTORE = 9
        ctypes.windll.user32.ShowWindow(handle, SW_RESTORE)

    def move_window(self, x: int = 0, y: int = 0, title: Optional[str] = None,
                    hwnd: Optional[int] = None) -> None:
        """Move a window to specified coordinates, keeping current size.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        left, top, right, bottom = self._get_window_rect(handle)
        w = right - left
        h = bottom - top
        ctypes.windll.user32.MoveWindow(handle, x, y, w, h, True)

    def resize_window(self, width: int = 800, height: int = 600,
                      title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Resize a window, keeping current position.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        left, top, _right, _bottom = self._get_window_rect(handle)
        ctypes.windll.user32.MoveWindow(handle, left, top, width, height, True)

    def set_bounds(self, x: int, y: int, width: int, height: int,
                   title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Set window position and size in one call.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            width: Target width in pixels.
            height: Target height in pixels.
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        ctypes.windll.user32.MoveWindow(handle, x, y, width, height, True)

