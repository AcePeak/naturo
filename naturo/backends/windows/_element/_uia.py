"""UWP / WinUI host-window discovery for the UI Automation backend.

Modern Windows apps hide their real UI behind an ``ApplicationFrameHost``
top-level window (classic UWP) or render via ``DesktopWindowXamlSource``
child windows (WinUI 3).  :class:`UWPDiscoveryMixin` locates the content
child window, resolves the real owning process, and classifies windows as
AFH/WinUI so the element-tree code can drill into the correct handle.  Split
out of the former monolithic ``_element`` module for maintainability (#720).
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class UWPDiscoveryMixin:
    """Discover the real content window and process for UWP/WinUI apps."""

    @staticmethod
    def _find_uwp_content_hwnd(parent_hwnd: int) -> list:
        """Find content child HWNDs inside an ApplicationFrameHost window.

        UWP and WinUI 3 apps host their actual UI inside child windows of the
        ApplicationFrameHost top-level window.  Classic UWP uses
        ``Windows.UI.Core.CoreWindow``; WinUI 3 (Windows App SDK) may use
        other window classes.  This method enumerates all child windows so
        the caller can try each one for a non-empty UIA element tree.

        The children are returned in priority order: known UWP/WinUI classes
        first (CoreWindow, DesktopWindowXamlSource), then any remaining
        visible children.

        Args:
            parent_hwnd: Handle of the ApplicationFrameHost top-level window.

        Returns:
            List of child HWNDs to try, ordered by priority (best first).
        """
        import sys
        if sys.platform != "win32":
            return []
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            # Enumerate all child windows
            children = []
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM,
            )

            def _enum_cb(hwnd, _lparam):
                children.append(int(hwnd))
                return True

            user32.EnumChildWindows(
                wintypes.HWND(parent_hwnd), WNDENUMPROC(_enum_cb), 0,
            )

            if not children:
                return []

            # Classify by window class name for priority ordering
            GetClassNameW = user32.GetClassNameW
            GetClassNameW.argtypes = [wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
            GetClassNameW.restype = ctypes.c_int

            PRIORITY_CLASSES = {
                "windows.ui.core.corewindow": 0,   # Classic UWP
                "desktopwindowxamlsource": 1,       # WinUI 3
            }

            prioritized = []
            rest = []
            for hwnd in children:
                cls_buf = ctypes.create_unicode_buffer(256)
                GetClassNameW(wintypes.HWND(hwnd), cls_buf, 256)
                cls_name = cls_buf.value.lower()
                prio = PRIORITY_CLASSES.get(cls_name)
                if prio is not None:
                    prioritized.append((prio, hwnd, cls_buf.value))
                else:
                    rest.append(hwnd)

            prioritized.sort(key=lambda t: t[0])
            result = [h for _, h, _ in prioritized] + rest

            if prioritized:
                logger.debug(
                    "UWP child windows for AFH %s: priority=%s, other=%d",
                    parent_hwnd,
                    [(cls, h) for _, h, cls in prioritized],
                    len(rest),
                )

            return result
        except Exception:
            return []
    def _resolve_uwp_child_pid(
        self, afh_hwnd: int,
    ) -> tuple[Optional[int], Optional[str]]:
        """Resolve the real process PID/exe for a UWP app inside AFH (#267).

        ApplicationFrameHost.exe hosts UWP apps as child windows. The
        child CoreWindow belongs to the actual app process (e.g.,
        CalculatorApp.exe). This method finds that child and returns its
        PID and executable path so ``list_apps`` reports the same PID as
        ``app inspect``.

        Args:
            afh_hwnd: Window handle of the ApplicationFrameHost top-level window.

        Returns:
            Tuple of (pid, exe_path) for the real app process, or
            (None, None) if resolution fails.
        """
        import sys
        if sys.platform != "win32":
            return None, None
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            afh_pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(
                wintypes.HWND(afh_hwnd), ctypes.byref(afh_pid),
            )
            afh_pid_val = afh_pid.value

            # Strategy 1: Use FindWindowExW to find CoreWindow directly.
            # This is more reliable than EnumChildWindows because
            # GetWindowThreadProcessId on CoreWindow always returns the
            # real app PID, even in schtask sessions.
            FindWindowExW = user32.FindWindowExW
            FindWindowExW.argtypes = [
                wintypes.HWND, wintypes.HWND,
                wintypes.LPCWSTR, wintypes.LPCWSTR,
            ]
            FindWindowExW.restype = wintypes.HWND

            core_hwnd = FindWindowExW(
                wintypes.HWND(afh_hwnd), None,
                "Windows.UI.Core.CoreWindow", None,
            )
            if core_hwnd:
                core_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(core_hwnd, ctypes.byref(core_pid))
                if core_pid.value != afh_pid_val and core_pid.value != 0:
                    logger.debug(
                        "UWP CoreWindow found: hwnd=%s pid=%d (afh=%d)",
                        core_hwnd, core_pid.value, afh_pid_val,
                    )
                    pid = core_pid.value
                    exe_path = self._get_process_exe_path(pid)
                    return pid, exe_path

            # Strategy 2: Enumerate all child windows and find one with
            # a different PID (fallback for WinUI 3 / non-CoreWindow apps).
            children = self._find_uwp_content_hwnd(afh_hwnd)
            logger.debug(
                "UWP child PID resolution: AFH hwnd=%s pid=%d, children=%d",
                afh_hwnd, afh_pid_val, len(children),
            )
            for child_hwnd in children:
                child_pid = ctypes.wintypes.DWORD()
                user32.GetWindowThreadProcessId(
                    wintypes.HWND(child_hwnd), ctypes.byref(child_pid),
                )
                if child_pid.value != afh_pid_val and child_pid.value != 0:
                    pid = child_pid.value
                    exe_path = self._get_process_exe_path(pid)
                    return pid, exe_path

        except Exception as exc:
            logger.debug("UWP child PID resolution failed: %s", exc)

        return None, None
    @staticmethod
    def _get_process_exe_path(pid: int) -> Optional[str]:
        """Get the executable path for a process by PID.

        Tries psutil first, then falls back to Win32 QueryFullProcessImageNameW.

        Args:
            pid: Process ID.

        Returns:
            Full executable path, or None if resolution fails.
        """
        try:
            import psutil  # type: ignore[import-untyped]
            return psutil.Process(pid).exe()
        except Exception as exc:
            logger.debug("psutil exe resolution failed for pid %s: %s", pid, exc)
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if h:
                try:
                    buf = ctypes.create_unicode_buffer(1024)
                    size = wintypes.DWORD(1024)
                    if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                        return buf.value
                finally:
                    kernel32.CloseHandle(h)
        except Exception as exc:
            logger.debug("Win32 exe path resolution failed for pid %s: %s", pid, exc)
        return None
    @staticmethod
    def _afh_has_content_window(afh_hwnd: int) -> bool:
        """Check if an ApplicationFrameHost window has a content child.

        A "content child" is a ``Windows.UI.Core.CoreWindow`` (classic UWP)
        or ``DesktopWindowXamlSource`` (WinUI 3) — these host the actual
        app UI.  Stale AFH windows may only have title bar and input sink
        children, which do NOT contain actionable UI elements.

        Args:
            afh_hwnd: Handle of the ApplicationFrameHost top-level window.

        Returns:
            True if the AFH has at least one content window child.
        """
        import sys
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            GetClassNameW = user32.GetClassNameW
            GetClassNameW.argtypes = [
                wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int,
            ]
            GetClassNameW.restype = ctypes.c_int

            _CONTENT_CLASSES = {
                "windows.ui.core.corewindow",
                "desktopwindowxamlsource",
            }

            found = [False]

            WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM,
            )

            def _enum_cb(hwnd, _lparam):
                cls_buf = ctypes.create_unicode_buffer(256)
                GetClassNameW(hwnd, cls_buf, 256)
                if cls_buf.value.lower() in _CONTENT_CLASSES:
                    found[0] = True
                    return False  # stop enumeration
                return True

            user32.EnumChildWindows(
                wintypes.HWND(afh_hwnd), WNDENUMPROC(_enum_cb), 0,
            )
            return found[0]
        except Exception:
            return False
    def _is_afh_window(self, handle: int) -> bool:
        """Check if a window handle belongs to ApplicationFrameHost.exe.

        Args:
            handle: Window handle to check.

        Returns:
            True if the window process is ApplicationFrameHost.exe.
        """
        for w in self.list_windows():
            if w.handle == handle:
                proc = w.process_name.lower()
                if proc.endswith(".exe"):
                    proc = proc[:-4]
                return proc == "applicationframehost"
        return False
    @staticmethod
    def _is_winui_window(handle: int) -> bool:
        """Check if a window has DesktopWindowXamlSource children (WinUI 3).

        Standalone WinUI 3 apps (Win11 Notepad, Paint) are NOT hosted by
        ApplicationFrameHost.exe — they run as regular processes but use
        XAML rendering via DesktopWindowXamlSource child windows.  Detecting
        this enables UIA click path for menu items (#786).

        Args:
            handle: Window handle to check.

        Returns:
            True if the window has at least one DesktopWindowXamlSource child.
        """
        import sys as _sys
        if _sys.platform != "win32":
            return False
        try:
            import ctypes
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            child = user32.FindWindowExW(handle, None, "DesktopWindowXamlSource", None)
            return child != 0
        except Exception:
            return False
