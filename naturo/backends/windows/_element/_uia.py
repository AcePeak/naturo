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
    # On-screen roles that mark real, interactive content (not window chrome).
    # Kept in the same spirit as ``naturo.cascade._appwindows._CONTENT_ROLES``
    # (the post-cascade scorer used by ``see``): the two must agree on "is this
    # window alive", but this cheap structural probe is what runs on the hot
    # path during window resolution, so it is deliberately duplicated (no import
    # of the cascade layer from the backend) and depth-bounded.
    _PROBE_CONTENT_ROLES = frozenset({
        "button", "menuitem", "checkbox", "radiobutton", "edit", "text",
        "listitem", "tab", "tabitem", "combobox", "link", "hyperlink",
        "treeitem", "cell", "slider", "spinbutton", "spinner", "document",
        "image",
    })

    def _raw_content_count(self, hwnd: int, depth: int, cap: int) -> int:
        """Count on-screen interactive nodes in ``hwnd``'s own UIA subtree.

        Low-level helper for :meth:`_window_content_probe` — it does NOT drill
        into UWP content children (the caller decides that), so it never
        recurses through :meth:`_afh_has_content_window`.  Bounded by ``depth``
        and short-circuited at ``cap`` matches so a rich window is cheap.

        Returns 0 on any failure (invalid handle, non-Windows, core error).
        """
        try:
            core = self._ensure_core()
            tree = core.get_element_tree(hwnd=hwnd, depth=depth)
        except Exception:
            return 0
        if tree is None:
            return 0
        n = 0
        stack = [tree]
        roles = self._PROBE_CONTENT_ROLES
        while stack:
            el = stack.pop()
            try:
                w = getattr(el, "width", 0) or 0
                h = getattr(el, "height", 0) or 0
                role = (getattr(el, "role", "") or "").lower()
                if w > 0 and h > 0 and role in roles:
                    n += 1
                    if n >= cap:
                        return n
                kids = getattr(el, "children", None) or []
            except Exception:
                continue
            stack.extend(kids)
        return n

    def _window_content_probe(self, hwnd: int, *, depth: int = 4,
                              cap: int = 8) -> int:
        """Cheap semantic content signal for window resolution.

        Returns an (approximate, capped) count of real on-screen interactive
        nodes for ``hwnd`` — the first-class signal that distinguishes a LIVE
        window (buttons/text with non-zero bounds) from a zombie/ghost frame
        (empty, or only off-screen 0x0 chrome).

        For UWP/WinUI host frames the app UI lives in a child
        ``Windows.UI.Core.CoreWindow`` / ``DesktopWindowXamlSource`` window that
        the frame's own shallow UIA tree does not span, so when the frame itself
        looks thin this drills into its content children (mirroring how
        ``get_element_tree`` recovers UWP content) and keeps the richest count.

        Best-effort and bounded: shallow ``depth`` + early ``cap`` keep it on the
        hot path; returns 0 on any failure.  Only ever invoked to break a tie
        between competing candidates, never for a single/unambiguous window.
        """
        import sys
        if sys.platform != "win32":
            return 0
        best = self._raw_content_count(hwnd, depth, cap)
        if best >= cap:
            return best
        # Thin own-tree: this may be a UWP host frame whose content sits in a
        # child CoreWindow/XamlSource. Probe those children and keep the max.
        try:
            children = self._find_uwp_content_hwnd(hwnd)
        except Exception:
            children = []
        for child in children:
            best = max(best, self._raw_content_count(child, depth, cap))
            if best >= cap:
                break
        return best

    def _afh_has_content_window(self, afh_hwnd: int) -> bool:
        """Check if an ApplicationFrameHost window has a *live* content child.

        A "content child" is a ``Windows.UI.Core.CoreWindow`` (classic UWP) or
        ``DesktopWindowXamlSource`` (WinUI 3) — these host the actual app UI.
        Historically this only checked that such a child EXISTS by class name
        (structural), so a zombie frame whose CoreWindow child is EMPTY passed
        and got picked as the resolved window — ``see --app calc`` then returned
        only off-screen chrome (the calc-zombie bug).

        This is now SEMANTIC: a content child must exist AND actually contain
        real UI (a non-empty shallow UIA subtree).  The class-name scan is kept
        as a cheap pre-filter so non-UWP / childless frames short-circuit before
        any UIA probe.

        Args:
            afh_hwnd: Handle of the ApplicationFrameHost top-level window.

        Returns:
            True only if the AFH has at least one content child that holds
            actual UI.
        """
        import sys
        if sys.platform != "win32":
            return False
        content_children = []
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

            WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM,
            )

            def _enum_cb(hwnd, _lparam):
                cls_buf = ctypes.create_unicode_buffer(256)
                GetClassNameW(hwnd, cls_buf, 256)
                if cls_buf.value.lower() in _CONTENT_CLASSES:
                    content_children.append(int(hwnd))
                return True

            user32.EnumChildWindows(
                wintypes.HWND(afh_hwnd), WNDENUMPROC(_enum_cb), 0,
            )
        except Exception:
            return False

        # Structural pre-filter: no CoreWindow/XamlSource child at all → dead.
        if not content_children:
            return False

        # Semantic check: at least one content child must hold real UI.  A
        # single shallow probe per child is cheap and, crucially, rejects the
        # empty-CoreWindow zombie frames the old structural check let through.
        for child in content_children:
            if self._raw_content_count(child, depth=3, cap=1) > 0:
                return True
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
