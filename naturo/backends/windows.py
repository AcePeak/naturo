"""Windows backend — powered by naturo_core.dll (C++ engine).

Implements the Phase 1 "See" capabilities: screen capture, window listing,
and UI element tree inspection. Later phases will add input and interaction.
"""

from __future__ import annotations

import logging

from naturo.backends.base import (
    Backend,
    WindowInfo as BaseWindowInfo,
    ElementInfo as BaseElementInfo,
    MonitorInfo,
    CaptureResult,
)
from naturo.bridge import NaturoCore, populate_hierarchy
from naturo.errors import NaturoError
from naturo.models.menu import MenuItem
from typing import ClassVar, List, Optional

logger = logging.getLogger(__name__)


class WindowsBackend(Backend):
    """Windows automation via naturo_core.dll.

    Uses GDI for screen capture, Win32 API for window management,
    and UIAutomation COM for element inspection.

    Attributes:
        _core: Lazily loaded NaturoCore bridge instance.
        _initialized: Whether naturo_init() has been called.
    """

    def __init__(self) -> None:
        self._core: Optional[NaturoCore] = None
        self._initialized: bool = False
        self._dpi_aware: bool = False
        self._ensure_dpi_awareness()

    def _ensure_dpi_awareness(self) -> None:
        """Set per-monitor DPI awareness for accurate coordinates and capture.

        Strategy (BUG-073):
        1. First, try ``SetThreadDpiAwarenessContext`` (Win10 1607+) which
           always succeeds regardless of process-level manifest or prior
           ``SetProcessDpiAwareness`` calls.  This is the recommended
           approach because Python.exe may ship with a DPI manifest that
           blocks process-level changes.
        2. As fallback, try process-level APIs for older Windows versions.

        The thread-level context is inherited by child threads, so setting
        it once on the main thread covers all subsequent Win32 calls.
        """
        if self._dpi_aware:
            return
        try:
            import ctypes

            user32 = ctypes.windll.user32

            # ── Thread-level DPI (Win10 1607+) — preferred ──
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
            # SetThreadDpiAwarenessContext returns the old context on
            # success, or NULL (0) on failure.
            try:
                _set_thread = user32.SetThreadDpiAwarenessContext
                _set_thread.restype = ctypes.c_void_p
                _set_thread.argtypes = [ctypes.c_void_p]
                old_ctx = _set_thread(-4)
                if old_ctx:
                    self._dpi_aware = True
                    logger.debug(
                        "DPI: SetThreadDpiAwarenessContext(-4) succeeded "
                        "(previous context=%s)",
                        old_ctx,
                    )
                    return
            except (OSError, AttributeError):
                pass

            # ── Process-level fallbacks ──

            # Per-Monitor v2 process-level (may fail if already set)
            try:
                user32.SetProcessDpiAwarenessContext(-4)
                self._dpi_aware = True
                return
            except (OSError, AttributeError):
                pass

            # Per-Monitor v1 (Win8.1+)
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
                self._dpi_aware = True
                return
            except (OSError, AttributeError):
                pass

            # System DPI aware (Vista+)
            try:
                user32.SetProcessDPIAware()
                self._dpi_aware = True
            except (OSError, AttributeError):
                pass
        except Exception:
            pass  # Non-Windows or no ctypes — skip silently

    def get_dpi_scale(self, screen_index: int = 0) -> float:
        """Get the DPI scale factor for a specific monitor.

        Args:
            screen_index: Zero-based monitor index (0 = primary).

        Returns:
            Scale factor (1.0 = 100%, 1.5 = 150%, 2.0 = 200%).
            Returns 1.0 if monitor not found or API unavailable.
        """
        try:
            monitors = self.list_monitors()
            if 0 <= screen_index < len(monitors):
                return monitors[screen_index].scale_factor
        except Exception:
            pass
        return 1.0

    def physical_to_logical(self, x: int, y: int, screen_index: int = 0) -> tuple[int, int]:
        """Convert physical (pixel) coordinates to logical (DPI-scaled) coordinates.

        Args:
            x: Physical X coordinate.
            y: Physical Y coordinate.
            screen_index: Monitor index for scale factor lookup.

        Returns:
            Tuple of (logical_x, logical_y).
        """
        scale = self.get_dpi_scale(screen_index)
        if scale <= 0 or scale == 1.0:
            return x, y
        return int(x / scale), int(y / scale)

    def logical_to_physical(self, x: int, y: int, screen_index: int = 0) -> tuple[int, int]:
        """Convert logical (DPI-scaled) coordinates to physical (pixel) coordinates.

        Args:
            x: Logical X coordinate.
            y: Logical Y coordinate.
            screen_index: Monitor index for scale factor lookup.

        Returns:
            Tuple of (physical_x, physical_y).
        """
        scale = self.get_dpi_scale(screen_index)
        if scale <= 0 or scale == 1.0:
            return x, y
        return int(x * scale), int(y * scale)

    def _ensure_core(self) -> NaturoCore:
        """Lazily load and initialize the native core library.

        Returns:
            The initialized NaturoCore instance.

        Raises:
            NaturoCoreError: If initialization fails.
        """
        if self._core is None:
            self._core = NaturoCore()
        if not self._initialized:
            self._core.init()
            self._initialized = True
        return self._core

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "windows"

    @property
    def capabilities(self) -> dict:
        """Return backend capabilities and platform-specific features."""
        return {
            "platform": "windows",
            "input_modes": ["normal", "hardware", "hook"],
            "accessibility": ["uia", "msaa", "ia2", "jab"],
            "extensions": ["excel", "java", "sap", "registry", "service"],
        }

    # === Capture (Phase 1) ===

    @staticmethod
    def _convert_bmp(bmp_path: str, output_path: str) -> tuple[int, int, str]:
        """Convert a BMP file to the format implied by *output_path* extension.

        Uses Pillow so we always deliver PNG/JPEG/etc. to users, regardless
        of the native BMP format produced by the C++ DLL (GDI BitBlt).

        Returns:
            (width, height, format_name) tuple.
        """
        import os
        from PIL import Image

        img = Image.open(bmp_path)
        width, height = img.size
        ext = output_path.rsplit(".", 1)[-1].lower() if "." in output_path else "png"
        fmt = {"jpg": "JPEG", "jpeg": "JPEG", "bmp": "BMP"}.get(ext, "PNG")

        if os.path.abspath(bmp_path) != os.path.abspath(output_path) or fmt != "BMP":
            img.save(output_path, fmt)
            # Remove the temp BMP if it differs from the final path
            if os.path.abspath(bmp_path) != os.path.abspath(output_path):
                try:
                    os.remove(bmp_path)
                except OSError:
                    pass

        return width, height, ext

    # ── Monitor Enumeration ────────────────────────

    def list_monitors(self) -> list[MonitorInfo]:
        """Enumerate connected monitors using Win32 API.

        Uses EnumDisplayMonitors + GetMonitorInfoW for geometry, and
        GetDpiForMonitor (Win8.1+) for per-monitor DPI. Falls back to
        system DPI when per-monitor API is unavailable.

        Returns:
            List of MonitorInfo sorted by index (primary = 0).
        """
        import ctypes
        import ctypes.wintypes as wt

        user32 = ctypes.windll.user32
        shcore = None
        try:
            shcore = ctypes.windll.shcore
        except OSError:
            pass

        monitors: list[dict] = []

        # MONITORINFOEXW structure
        class MONITORINFOEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wt.DWORD),
                ("rcMonitor", wt.RECT),
                ("rcWork", wt.RECT),
                ("dwFlags", wt.DWORD),
                ("szDevice", ctypes.c_wchar * 32),
            ]

        MONITORINFOF_PRIMARY = 0x00000001

        def _enum_callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(MONITORINFOEXW)
            if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                rc = info.rcMonitor
                wk = info.rcWork

                # Per-monitor DPI (available on Win8.1+)
                dpi_x = ctypes.c_uint(96)
                dpi_y = ctypes.c_uint(96)
                if shcore:
                    try:
                        # MDT_EFFECTIVE_DPI = 0
                        shcore.GetDpiForMonitor(
                            hMonitor, 0,
                            ctypes.byref(dpi_x), ctypes.byref(dpi_y),
                        )
                    except Exception:
                        pass

                dpi = dpi_x.value
                scale = round(dpi / 96.0, 2)

                monitors.append({
                    "hMonitor": hMonitor,
                    "name": info.szDevice.rstrip("\x00"),
                    "x": rc.left,
                    "y": rc.top,
                    "width": rc.right - rc.left,
                    "height": rc.bottom - rc.top,
                    "is_primary": bool(info.dwFlags & MONITORINFOF_PRIMARY),
                    "scale_factor": scale,
                    "dpi": dpi,
                    "work_area": {
                        "x": wk.left,
                        "y": wk.top,
                        "width": wk.right - wk.left,
                        "height": wk.bottom - wk.top,
                    },
                })
            return 1  # Continue enumeration

        MONITORENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,   # hMonitor
            ctypes.c_void_p,   # hdcMonitor
            ctypes.POINTER(wt.RECT),  # lprcMonitor
            ctypes.POINTER(wt.LONG),  # dwData
        )

        callback = MONITORENUMPROC(_enum_callback)
        user32.EnumDisplayMonitors(None, None, callback, 0)

        # Sort: primary first, then by x coordinate (left to right)
        monitors.sort(key=lambda m: (not m["is_primary"], m["x"], m["y"]))

        result: list[MonitorInfo] = []
        for idx, m in enumerate(monitors):
            result.append(MonitorInfo(
                index=idx,
                name=m["name"],
                x=m["x"],
                y=m["y"],
                width=m["width"],
                height=m["height"],
                is_primary=m["is_primary"],
                scale_factor=m["scale_factor"],
                dpi=m["dpi"],
                work_area=m["work_area"],
            ))

        return result

    # ── Screen Capture ────────────────────────────

    def capture_screen(self, screen_index: int = 0, output_path: str = "capture.png") -> CaptureResult:
        """Capture a screenshot of the specified monitor.

        The C++ DLL captures via GDI BitBlt to a temporary BMP, then Pillow
        converts to the requested format (PNG by default, matching Peekaboo).

        Args:
            screen_index: Zero-based monitor index (0 = primary).
            output_path: File path for the output image.

        Returns:
            CaptureResult with the output path and dimensions.
        """
        import tempfile
        import os
        core = self._ensure_core()

        # DLL writes BMP; use a temp file in a safe directory to avoid
        # encoding issues with Chinese/Unicode paths on Windows
        output_dir = os.path.dirname(os.path.abspath(output_path)) or "."
        try:
            fd, tmp_bmp = tempfile.mkstemp(suffix=".bmp", dir=output_dir)
            os.close(fd)
        except OSError:
            # Fallback to system temp dir if output dir fails
            fd, tmp_bmp = tempfile.mkstemp(suffix=".bmp")
            os.close(fd)

        try:
            core.capture_screen(screen_index, tmp_bmp)
            width, height, fmt = self._convert_bmp(tmp_bmp, output_path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.remove(tmp_bmp)
            except OSError:
                pass
            raise

        # Attach DPI metadata from the captured monitor
        scale_factor = 1.0
        dpi = 96
        try:
            monitors = self.list_monitors()
            if 0 <= screen_index < len(monitors):
                scale_factor = monitors[screen_index].scale_factor
                dpi = monitors[screen_index].dpi
        except Exception:
            pass

        return CaptureResult(
            path=output_path, width=width, height=height, format=fmt,
            scale_factor=scale_factor, dpi=dpi,
        )

    def capture_window(self, window_title: Optional[str] = None, hwnd: Optional[int] = None,
                       output_path: str = "capture.png") -> CaptureResult:
        """Capture a screenshot of a specific window.

        Uses PrintWindow for accurate off-screen capture. If neither
        window_title nor hwnd is provided, captures the foreground window.
        Output is PNG by default (matching Peekaboo).

        Args:
            window_title: Window title to search for (not yet implemented — use hwnd).
            hwnd: Window handle. 0 or None for the foreground window.
            output_path: File path for the output image.

        Returns:
            CaptureResult with the output path and dimensions.
        """
        import tempfile
        import os
        core = self._ensure_core()
        handle = hwnd if hwnd else 0

        # Use a safe temp file to avoid encoding issues with Unicode paths
        output_dir = os.path.dirname(os.path.abspath(output_path)) or "."
        try:
            fd, tmp_bmp = tempfile.mkstemp(suffix=".bmp", dir=output_dir)
            os.close(fd)
        except OSError:
            fd, tmp_bmp = tempfile.mkstemp(suffix=".bmp")
            os.close(fd)

        try:
            core.capture_window(handle, tmp_bmp)
            width, height, fmt = self._convert_bmp(tmp_bmp, output_path)
        except Exception:
            try:
                os.remove(tmp_bmp)
            except OSError:
                pass
            raise

        # Determine DPI from the window's monitor position
        scale_factor = 1.0
        dpi = 96
        try:
            # Get the window's position to find which monitor it's on
            import ctypes
            import ctypes.wintypes as wt
            rect = wt.RECT()
            actual_handle = handle or ctypes.windll.user32.GetForegroundWindow()
            if actual_handle and ctypes.windll.user32.GetWindowRect(actual_handle, ctypes.byref(rect)):
                monitor = self.find_monitor_for_point(rect.left, rect.top)
                if monitor:
                    scale_factor = monitor.scale_factor
                    dpi = monitor.dpi
        except Exception:
            pass

        return CaptureResult(
            path=output_path, width=width, height=height, format=fmt,
            scale_factor=scale_factor, dpi=dpi,
        )

    # === Window Management (Phase 1: list only) ===

    def list_windows(self) -> list[BaseWindowInfo]:
        """List all visible top-level windows.

        Returns:
            List of WindowInfo dataclass instances.
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

        # SetForegroundWindow fails silently when caller is not the foreground
        # process. Use AttachThreadInput trick to work around this Windows
        # restriction: attach to the target window's thread, set foreground,
        # then detach.
        foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
        current_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        target_tid = ctypes.windll.user32.GetWindowThreadProcessId(handle, None)
        fg_tid = ctypes.windll.user32.GetWindowThreadProcessId(foreground_hwnd, None)

        attached_target = False
        attached_fg = False
        try:
            if current_tid != target_tid:
                attached_target = bool(ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, True))
            if current_tid != fg_tid and fg_tid != target_tid:
                attached_fg = bool(ctypes.windll.user32.AttachThreadInput(current_tid, fg_tid, True))

            ctypes.windll.user32.ShowWindow(handle, SW_SHOW)
            ctypes.windll.user32.BringWindowToTop(handle)
            ctypes.windll.user32.SetForegroundWindow(handle)
        finally:
            if attached_target:
                ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, False)
            if attached_fg:
                ctypes.windll.user32.AttachThreadInput(current_tid, fg_tid, False)

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

    # === UI Element Inspection (Phase 1) ===

    def find_element(self, selector: str = "", window_title: Optional[str] = None,
                     hwnd: Optional[int] = None) -> Optional[BaseElementInfo]:
        """Find a UI element by selector string.

        The selector format is "role:name" (e.g., "Button:OK") or just a name.

        Args:
            selector: Element selector in "role:name" or "name" format.
            window_title: Not yet used (reserved for future).
            hwnd: Target window handle.  When provided, searches within this
                window instead of the foreground window (#525).

        Returns:
            ElementInfo if found, None otherwise.
        """
        core = self._ensure_core()

        # Parse selector into role and name
        role = None
        name = None
        if ":" in selector:
            parts = selector.split(":", 1)
            role = parts[0] if parts[0] else None
            name = parts[1] if parts[1] else None
        else:
            name = selector if selector else None

        result = core.find_element(hwnd=hwnd or 0, role=role, name=name)
        if result is None:
            return None

        return BaseElementInfo(
            id=result.id,
            role=result.role,
            name=result.name,
            value=result.value,
            x=result.x,
            y=result.y,
            width=result.width,
            height=result.height,
            children=[],
            properties={},
        )

    # Cross-locale alias map for --app matching (#469).
    # Maps lowercase alias → set of lowercase process-name stems that
    # should be considered a match.  Values must be English process names
    # (without .exe) since Windows process names are always in English.
    _APP_ALIASES: dict[str, set[str]] = {
        # Calculator
        "calculator": {"calc", "calculatorapp"},
        "calc": {"calc", "calculatorapp"},
        "计算器": {"calc", "calculatorapp"},
        # Notepad
        "notepad": {"notepad"},
        "记事本": {"notepad"},
        # Settings
        "settings": {"systemsettings"},
        "设置": {"systemsettings"},
        # Paint
        "paint": {"mspaint"},
        "画图": {"mspaint"},
        # File Explorer
        "explorer": {"explorer"},
        "file explorer": {"explorer"},
        "文件资源管理器": {"explorer"},
        # Edge
        "edge": {"msedge"},
        "microsoft edge": {"msedge"},
        # Task Manager
        "task manager": {"taskmgr"},
        "任务管理器": {"taskmgr"},
        # Command Prompt
        "command prompt": {"cmd"},
        "命令提示符": {"cmd"},
        # Terminal
        "terminal": {"windowsterminal"},
        "终端": {"windowsterminal"},
        # WordPad
        "wordpad": {"wordpad"},
        "写字板": {"wordpad"},
        # Snipping Tool / Screen Sketch
        "snipping tool": {"snippingtool", "screensketch"},
        "截图工具": {"snippingtool", "screensketch"},
    }

    @staticmethod
    def _get_console_session_id() -> int:
        """Get the active console (interactive desktop) session ID.

        Uses WTSGetActiveConsoleSessionId to determine which Windows session
        owns the physical console.  Returns -1 if the call fails.

        Returns:
            Active console session ID, or -1 on failure.
        """
        try:
            import ctypes
            session_id = ctypes.windll.kernel32.WTSGetActiveConsoleSessionId()
            # WTSGetActiveConsoleSessionId returns 0xFFFFFFFF on failure
            if session_id == 0xFFFFFFFF:
                return -1
            return session_id
        except Exception:
            return -1

    @staticmethod
    def _get_process_session_id(pid: int) -> int:
        """Get the Windows session ID for a given process.

        Uses ProcessIdToSessionId to determine which session a process
        belongs to.  Session 0 is the non-interactive services session;
        session 1+ are interactive user sessions.

        Args:
            pid: Process ID.

        Returns:
            Session ID, or -1 on failure.
        """
        try:
            import ctypes
            session_id = ctypes.wintypes.DWORD()
            success = ctypes.windll.kernel32.ProcessIdToSessionId(
                pid, ctypes.byref(session_id)
            )
            if success:
                return session_id.value
            return -1
        except Exception:
            return -1

    @staticmethod
    def _get_foreground_hwnd() -> int:
        """Get the currently focused foreground window handle.

        Returns:
            HWND of the foreground window, or 0 on failure.
        """
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            return hwnd or 0
        except Exception:
            return 0

    @staticmethod
    def _get_window_class_name(hwnd: int) -> str:
        """Get the window class name for a given HWND.

        Used to identify special windows like Program Manager ("Progman")
        which should be deprioritized during app resolution (#524).

        Args:
            hwnd: Window handle.

        Returns:
            Window class name, or empty string on failure.
        """
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
            return buf.value
        except Exception:
            return ""

    # Window classes that represent the desktop shell rather than real
    # application windows.  explorer.exe hosts both the desktop and File
    # Explorer; when --app explorer is used, these should be deprioritized
    # so actual File Explorer windows are preferred (#524).
    _DESKTOP_SHELL_CLASSES: ClassVar[frozenset[str]] = frozenset({
        "Progman",   # Program Manager (desktop icons)
        "WorkerW",   # Desktop worker window (wallpaper layer)
    })

    def _resolve_hwnd(self, app: Optional[str] = None,
                      window_title: Optional[str] = None,
                      hwnd: Optional[int] = None,
                      pid: Optional[int] = None) -> int:
        """Resolve a window handle from app name, window title, pid, or direct hwnd.

        Matching strategy (BUG-069/BUG-070):

        When ``app`` is provided, matches against **process name and aliases
        only** (``.exe`` suffix stripped).  Title matching is not used for
        ``--app`` to prevent cross-process contamination (#465).  When
        ``window_title`` is provided, matches against window title only.

        When ``pid`` is provided (alone or combined with app/window_title),
        only windows belonging to that process are considered (#471).  Among
        matching PID windows, the largest-area window in the interactive
        session is preferred.

        Scoring for ``--app`` (higher = better match):
          4 — exact process-name match  (e.g. ``explorer`` == ``explorer.exe``)
          3 — process-name substring    (e.g. ``expl`` in ``explorer.exe``)
        Alias matches (e.g. ``calculator`` → ``calculatorapp``) use the same
        scores as direct process-name matches.

        Session awareness (#230): When multiple windows match with equal
        scores, windows in the active console session are strongly preferred
        over windows in Session 0 (the non-interactive services session).
        This prevents schtasks/remote contexts from targeting ghost windows.

        Foreground preference (#449): When multiple windows match with equal
        scores and session status, the foreground (focused) window is
        preferred.  This ensures consecutive commands (``type`` then
        ``capture``) target the same window deterministically.

        Case-insensitive throughout.  Among equal scores the window with
        the largest area wins (#440: popup menus are tiny top-level windows
        that should not beat the main application window).

        Args:
            app: Application/process name to search for (case-insensitive,
                partial match).  Compared against process name first, then
                window title as fallback.
            window_title: Window title pattern (case-insensitive, partial
                match).  Compared against window title only.
            hwnd: Direct window handle (takes priority).
            pid: Process ID.  When provided, only windows owned by this
                process are considered.  Can be combined with app/window_title
                for additional filtering, or used alone (#471).

        Returns:
            Window handle (HWND), or 0 for the foreground window.

        Raises:
            WindowNotFoundError: When no matching window is found.  The error
                message includes up to 5 candidate windows.
        """
        if hwnd:
            return hwnd

        search = app or window_title
        if not search and not pid:
            return 0  # foreground window

        search_lower = search.lower() if search else ""
        windows = self.list_windows()

        # (#471) Filter by PID when provided — only consider windows owned
        # by the specified process.  This is applied before scoring so that
        # PID-based targeting is never overridden by a higher-scoring window
        # from a different process.
        if pid is not None:
            windows = [w for w in windows if w.pid == pid]
            if not windows:
                from naturo.errors import WindowNotFoundError
                raise WindowNotFoundError(
                    f"PID {pid}",
                    suggested_action=(
                        f"No visible window found for PID {pid}. "
                        "The process may have exited or has no visible windows.\n"
                        "Tip: use 'naturo list windows' to see all windows."
                    ),
                )

        # Get console session for session-aware ranking (#230)
        console_session = self._get_console_session_id()

        # Get foreground HWND for deterministic tie-breaking (#449)
        fg_hwnd = self._get_foreground_hwnd()

        # --app → match process name first; --window-title → match title only
        match_process = app is not None

        # (#471) When only --pid is given (no app/window_title), all windows
        # belonging to the PID are valid candidates — assign a base score of 1
        # so that the best-window selection logic (session, foreground, area)
        # picks the most appropriate one.
        pid_only = pid is not None and not search

        best_score = 0
        best_session_bonus = False  # True if best_window is in console session
        best_is_foreground = False  # True if best_window is the foreground window
        best_window = None

        for w in windows:
            score = 0
            proc_stem = w.process_name.lower()
            # Strip .exe suffix for comparison
            if proc_stem.endswith(".exe"):
                proc_stem = proc_stem[:-4]
            title_lower = w.title.lower()

            if pid_only:
                # All PID-filtered windows are valid candidates
                score = 1
            elif match_process:
                # Process-name matching (priority)
                if search_lower == proc_stem:
                    score = 4  # exact process name
                elif search_lower in proc_stem:
                    score = 3  # substring in process name
                # (#465) Title-only fallback removed from --app matching.
                # When --app is used, we only match by process name or alias.
                # Title-only matches caused cross-process contamination: e.g.
                # --app notepad picking a Chrome window titled "help with notepad".
                # Use --window-title for title-based matching.
                #
                # Alias matching: cross-locale app name resolution
                if score == 0:
                    aliases = self._APP_ALIASES.get(search_lower, set())
                    for alias in aliases:
                        if alias == proc_stem:
                            score = 4  # alias → exact process name
                            break
                        if alias in proc_stem:
                            score = 3  # alias → substring in process name
                            break
            else:
                # --window-title: only match window title
                if search_lower == title_lower:
                    score = 4  # exact title
                elif search_lower in title_lower:
                    score = 1  # substring in title

            if score == 0:
                continue

            # (#524) Desktop shell deprioritization: explorer.exe hosts both
            # File Explorer and the desktop (Program Manager, class "Progman").
            # When --app explorer is used, users expect File Explorer, not the
            # desktop.  Detect shell windows by class name and reduce their
            # score to 1, so any real File Explorer window (score 3-4) wins.
            # If no File Explorer windows exist, the desktop still matches.
            if match_process:
                wclass = self._get_window_class_name(w.handle)
                if wclass in self._DESKTOP_SHELL_CLASSES:
                    score = 1  # demote desktop shell windows

            # Session-aware ranking (#230): prefer windows in the active
            # console session over windows in Session 0 (services session).
            # This prevents schtasks-launched commands from targeting ghost
            # processes that exist in the non-interactive session.
            in_console = False
            if console_session >= 0:
                w_session = self._get_process_session_id(w.pid)
                in_console = (w_session == console_session)

            # (#449) Check if this window is the foreground window
            is_foreground = (fg_hwnd != 0 and w.handle == fg_hwnd)

            # Decision: pick this window if it has a higher score, or if
            # scores are equal but this window is in the console session
            # while the current best is not.  Among equal score + session,
            # prefer the foreground window (#449: consecutive commands
            # should target the same window deterministically).  Finally,
            # prefer the larger window area (#440: popup menus are tiny
            # top-level windows that should not beat the main window).
            if score > best_score:
                best_score = score
                best_session_bonus = in_console
                best_is_foreground = is_foreground
                best_window = w
            elif score == best_score and best_window is not None:
                if in_console and not best_session_bonus:
                    # Same score but this one is in the interactive session
                    best_session_bonus = in_console
                    best_is_foreground = is_foreground
                    best_window = w
                elif in_console == best_session_bonus:
                    # (#449) Prefer the foreground window for deterministic
                    # resolution when multiple windows match equally.
                    if is_foreground and not best_is_foreground:
                        best_is_foreground = True
                        best_window = w
                    elif is_foreground == best_is_foreground:
                        w_area = w.width * w.height
                        best_area = best_window.width * best_window.height
                        if w_area > best_area:
                            best_window = w

        if best_window is not None:
            # UWP/WinUI apps: the real UI tree lives under
            # ApplicationFrameHost.exe, not the inner process window
            # (e.g. CalculatorApp.exe).  When we matched a non-frame
            # process, check for an ApplicationFrameHost window with the
            # same title and prefer it — its element tree is complete.
            # Extract basename for comparison — process_name may be a
            # full path (e.g. "C:\...\CalculatorApp.exe")
            import os as _os
            best_proc = _os.path.basename(best_window.process_name).lower()
            if best_proc.endswith(".exe"):
                best_proc = best_proc[:-4]
            if best_proc != "applicationframehost":
                # (#394) Collect ALL AFH windows with matching title, then
                # prefer one that actually has a CoreWindow child (live UI).
                # Stale AFH windows (e.g., from schtasks-launched instances)
                # may linger without a CoreWindow child, producing empty
                # UIA trees.
                afh_candidates = []
                for w in windows:
                    frame_proc = _os.path.basename(w.process_name).lower()
                    if frame_proc.endswith(".exe"):
                        frame_proc = frame_proc[:-4]
                    if (
                        frame_proc == "applicationframehost"
                        and w.title == best_window.title
                        and w.handle != best_window.handle
                    ):
                        afh_candidates.append(w)

                if afh_candidates:
                    # (#394 v2) Prefer AFH window with a CoreWindow or
                    # DesktopWindowXamlSource child — these host the actual
                    # app UI.  Stale AFH windows may have title bar and
                    # input sink children but no content window, yielding
                    # empty UIA trees.
                    chosen_afh = None
                    for afh_w in afh_candidates:
                        if self._afh_has_content_window(afh_w.handle):
                            chosen_afh = afh_w
                            logger.debug(
                                "UWP fixup: AFH hwnd=%s has content "
                                "window (CoreWindow/XAML), selecting it",
                                afh_w.handle,
                            )
                            break
                    if chosen_afh is None:
                        # No AFH has content children — fall back to first
                        chosen_afh = afh_candidates[0]
                        logger.debug(
                            "UWP fixup: no AFH has content children, "
                            "falling back to first AFH hwnd=%s",
                            chosen_afh.handle,
                        )
                    best_window = chosen_afh

            return best_window.handle

        # (#569) UWP fallback: UWP apps (Calculator, Settings, etc.) have
        # their windows owned by ApplicationFrameHost.exe, not by the
        # actual app process (e.g. CalculatorApp.exe).  When process-name
        # matching finds nothing, probe each AFH window's content child
        # to find the real app process and match against that.
        if match_process and best_window is None:
            best_window = self._uwp_afh_fallback(
                search_lower, windows, console_session,
            )
            if best_window is not None:
                return best_window.handle

        # No match — build candidate suggestions (BUG-070)
        from naturo.errors import WindowNotFoundError

        candidates = []
        seen = set()
        for w in windows:
            label = f"{w.process_name} — \"{w.title}\""
            if label not in seen and w.title:
                seen.add(label)
                candidates.append(label)
            if len(candidates) >= 5:
                break

        search_label = search or f"PID {pid}"
        hint = f"No window matching '{search_label}'."
        if candidates:
            hint += " Did you mean:\n" + "\n".join(f"  • {c}" for c in candidates)
        hint += "\nTip: use 'naturo list windows' to see all windows."

        raise WindowNotFoundError(search_label, suggested_action=hint)

    def _resolve_hwnds(self, app: Optional[str] = None,
                       window_title: Optional[str] = None) -> list[int]:
        """Resolve ALL window handles matching app name or window title.

        Same matching logic as _resolve_hwnd, but returns ALL windows that
        match (score > 0), sorted by score descending.

        Used by `see --app` to enumerate all windows of an application (#304).

        Args:
            app: Application/process name (case-insensitive, partial match).
            window_title: Window title pattern (case-insensitive, partial match).

        Returns:
            List of window handles (HWNDs), sorted by match quality (best first).
            Empty list if no matches found.

        Note:
            Does NOT accept `hwnd` parameter (use [hwnd] if you have a handle).
            Skips foreground window fallback (returns [] if no search term).
        """
        search = app or window_title
        if not search:
            return []

        search_lower = search.lower()
        windows = self.list_windows()
        console_session = self._get_console_session_id()
        match_process = app is not None

        # Collect all matching windows with their scores
        matches = []  # [(score, in_console, title_len, WindowInfo), ...]

        for w in windows:
            score = 0
            proc_stem = w.process_name.lower()
            if proc_stem.endswith(".exe"):
                proc_stem = proc_stem[:-4]
            title_lower = w.title.lower()

            if match_process:
                # Process-name matching
                if search_lower == proc_stem:
                    score = 4
                elif search_lower in proc_stem:
                    score = 3
                # (#465) No title fallback for --app (see _resolve_hwnd)
                # Alias matching
                if score == 0:
                    aliases = self._APP_ALIASES.get(search_lower, set())
                    for alias in aliases:
                        if alias == proc_stem:
                            score = 4
                            break
                        if alias in proc_stem:
                            score = 3
                            break
            else:
                # --window-title: only match window title
                if search_lower == title_lower:
                    score = 4
                elif search_lower in title_lower:
                    score = 1

            if score == 0:
                continue

            # Session-aware ranking
            in_console = False
            if console_session >= 0:
                w_session = self._get_process_session_id(w.pid)
                in_console = (w_session == console_session)

            matches.append((score, in_console, len(w.title), w))

        # Sort by: score desc, console first, shorter title first
        # (in_console: True > False, so negate for descending)
        matches.sort(key=lambda x: (x[0], x[1], -x[2]), reverse=True)

        # Extract HWNDs
        hwnds = [m[3].handle for m in matches]

        # UWP/ApplicationFrameHost fixup: prefer frame windows when available.
        # Search ALL windows (not just scored matches) for AFH counterparts,
        # matching the same logic as _resolve_hwnd (#559).  UWP apps like
        # Calculator run under CalculatorApp.exe but their UI tree lives
        # under the ApplicationFrameHost.exe window.  The AFH window may
        # not score any points for the search term (e.g. "计算器") so we
        # must search the full window list.
        import os as _os
        fixed_hwnds = []
        for hwnd in hwnds:
            # Find the WindowInfo for this hwnd
            w_info = next((m[3] for m in matches if m[3].handle == hwnd), None)
            if not w_info:
                fixed_hwnds.append(hwnd)
                continue

            proc = _os.path.basename(w_info.process_name).lower()
            if proc.endswith(".exe"):
                proc = proc[:-4]

            if proc != "applicationframehost":
                # (#559) Search ALL windows for AFH with matching title,
                # then prefer one with a CoreWindow child (live UI),
                # mirroring _resolve_hwnd logic (#394).
                afh_candidates = []
                for w in windows:
                    frame_proc = _os.path.basename(w.process_name).lower()
                    if frame_proc.endswith(".exe"):
                        frame_proc = frame_proc[:-4]
                    if (
                        frame_proc == "applicationframehost"
                        and w.title == w_info.title
                        and w.handle != hwnd
                    ):
                        afh_candidates.append(w)

                if afh_candidates:
                    # Prefer AFH with content window (CoreWindow/XAML)
                    chosen_afh = None
                    for afh_w in afh_candidates:
                        if self._afh_has_content_window(afh_w.handle):
                            chosen_afh = afh_w
                            break
                    if chosen_afh is None:
                        chosen_afh = afh_candidates[0]
                    fixed_hwnds.append(chosen_afh.handle)
                else:
                    fixed_hwnds.append(hwnd)
            else:
                fixed_hwnds.append(hwnd)

        # Deduplicate (in case of frame window replacements)
        seen = set()
        result = []
        for h in fixed_hwnds:
            if h not in seen:
                seen.add(h)
                result.append(h)

        # (#569) UWP fallback: when no windows matched by process name,
        # probe AFH windows' content children for the real app process.
        if not result and match_process:
            console_session = self._get_console_session_id()
            afh_match = self._uwp_afh_fallback(
                search_lower, windows, console_session,
            )
            if afh_match is not None:
                result.append(afh_match.handle)

        return result

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
            children = self._find_uwp_content_children(afh_hwnd)
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
        except Exception:
            pass
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
        except Exception:
            pass
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

    def _uwp_afh_fallback(
        self,
        search_lower: str,
        windows: list,
        console_session: int,
    ) -> Optional["BaseWindowInfo"]:
        """UWP fallback: find an AFH window whose child process matches (#569).

        UWP apps (Calculator, Settings, etc.) have their top-level windows
        owned by ApplicationFrameHost.exe.  Normal process-name matching
        cannot find these because the AFH process name never matches
        user-facing app names like "calculator".

        This method probes each AFH window's content child (CoreWindow) to
        discover the real app process (e.g. CalculatorApp.exe), then checks
        if that process name matches the search term or its aliases.

        Only called when the primary scoring loop found no matches.

        Args:
            search_lower: Lowercase search term from ``--app``.
            windows: Full window list from ``list_windows()``.
            console_session: Console session ID for session-aware ranking.

        Returns:
            The best matching AFH WindowInfo, or None if no match.
        """
        import os as _os

        # Build the set of process stems to match against (search + aliases)
        target_stems: set[str] = {search_lower}
        aliases = self._APP_ALIASES.get(search_lower, set())
        target_stems.update(aliases)

        best_afh = None
        best_in_console = False

        for w in windows:
            proc = _os.path.basename(w.process_name).lower()
            if proc.endswith(".exe"):
                proc = proc[:-4]
            if proc != "applicationframehost":
                continue
            if not self._afh_has_content_window(w.handle):
                continue

            # Resolve the real app PID/exe inside this AFH window
            child_pid, child_exe = self._resolve_uwp_child_pid(w.handle)
            if child_pid is None or child_exe is None:
                continue

            child_stem = _os.path.basename(child_exe).lower()
            if child_stem.endswith(".exe"):
                child_stem = child_stem[:-4]

            # Check if the child process matches any target stem
            matched = False
            for stem in target_stems:
                if stem == child_stem or stem in child_stem:
                    matched = True
                    break
            if not matched:
                continue

            # Session-aware ranking: prefer console session
            in_console = False
            if console_session >= 0:
                w_session = self._get_process_session_id(w.pid)
                in_console = (w_session == console_session)

            if best_afh is None or (in_console and not best_in_console):
                best_afh = w
                best_in_console = in_console

        if best_afh is not None:
            logger.debug(
                "UWP AFH fallback (#569): matched AFH hwnd=%s for "
                "search '%s'",
                best_afh.handle, search_lower,
            )

        return best_afh

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
    def _is_shallow_tree(element) -> bool:
        """Check if an element tree is too shallow (VB6/ActiveX fallback signal).

        VB6/ActiveX apps often expose a tree with only a few Pane containers
        at depth 1-2, hiding all actual form controls (Static/Edit/Button).
        This heuristic detects that pattern to trigger Win32 HWND enumeration.

        Args:
            element: Root ElementInfo from get_element_tree.

        Returns:
            True if the tree is too shallow (trigger fallback).
        """
        if not element or not element.children:
            return True

        # Count actionable elements (non-Pane roles at any depth)
        actionable_count = 0
        pane_count = 0

        def count_actionable(el):
            nonlocal actionable_count, pane_count
            role = (el.role or "").lower()
            if role == "pane":
                pane_count += 1
            elif role in ("button", "edit", "text", "combobox", "checkbox", "radiobutton"):
                actionable_count += 1
            for child in el.children:
                count_actionable(child)

        count_actionable(element)

        # Shallow tree heuristic: <5 actionable elements or >80% panes
        if actionable_count < 5:
            return True
        if pane_count > 0 and actionable_count / (actionable_count + pane_count) < 0.2:
            return True

        return False

    def get_element_tree(self, window_title: Optional[str] = None,
                         depth: int = 3,
                         app: Optional[str] = None,
                         hwnd: Optional[int] = None,
                         pid: Optional[int] = None,
                         backend: str = "uia") -> Optional[BaseElementInfo]:
        """Get the UI element tree for a window.

        Fills parent_id, children IDs, and keyboard_shortcut for all elements
        via Python-layer post-processing (the C++ DLL does not emit these).

        For UWP/WinUI apps (Calculator, Settings, etc.) the UI tree lives
        inside child windows of the ``ApplicationFrameHost`` top-level window.
        Classic UWP uses ``Windows.UI.Core.CoreWindow``; WinUI 3 apps use
        other classes like ``DesktopWindowXamlSource``.  When the initial
        traversal returns an empty tree from an AFH window, this method
        enumerates all child windows and retries with each until a non-empty
        tree is found.

        Args:
            window_title: Window title pattern (partial match, case-insensitive).
            depth: Maximum depth to traverse (1-10).
            app: Application name to search for (partial match, case-insensitive).
            hwnd: Direct window handle. Overrides app/window_title.
            pid: Process ID.  Filters windows to only those owned by this
                process (#471).
            backend: Accessibility backend — "auto" (default), "uia", "msaa",
                     "win32", "win32hybrid", "ia2", or "jab".
                     "auto" tries UIA first, falls back to hybrid Win32+UIA
                     if UIA returns shallow trees, then IA2/JAB/MSAA.
                     "win32" uses pure Win32 HWND enumeration.
                     "win32hybrid" uses Win32 HWND tree with UIA drill-down
                     for complex controls like grids, list views, and tree
                     views (#312).

        Returns:
            Root ElementInfo with nested children, or None.
        """
        core = self._ensure_core()
        handle = self._resolve_hwnd(app=app, window_title=window_title, hwnd=hwnd, pid=pid)

        def _try_uwp_children(current_result, get_tree_fn):
            """If handle is an AFH window with empty tree, try child windows.

            Enumerates all child HWNDs of the ApplicationFrameHost window
            and returns the first one that yields a non-empty element tree.

            Args:
                current_result: The element tree from the AFH window itself.
                get_tree_fn: Callable(hwnd, depth) -> element tree result.

            Returns:
                A non-empty element tree from a child HWND, or current_result
                if no child yields a better result.
            """
            if (current_result is not None
                    and not current_result.children
                    and handle
                    and self._is_afh_window(handle)):
                child_hwnds = self._find_uwp_content_hwnd(handle)
                for child_hwnd in child_hwnds:
                    logger.debug(
                        "UWP fallback: trying child HWND %s "
                        "(parent AFH %s)", child_hwnd, handle,
                    )
                    child_result = get_tree_fn(child_hwnd, depth)
                    if child_result is not None and child_result.children:
                        logger.info(
                            "UWP fallback: found %d children via child "
                            "HWND %s", len(child_result.children), child_hwnd,
                        )
                        return child_result

                # (#394) WinUI 3 apps may need deeper traversal.
                # Retry child HWNDs with increased depth if original
                # depth was low and yielded nothing.
                if depth < 15:
                    deeper = min(depth * 2, 20)
                    logger.debug(
                        "UWP fallback: retrying children with depth=%d "
                        "(was %d)", deeper, depth,
                    )
                    for child_hwnd in child_hwnds:
                        child_result = get_tree_fn(child_hwnd, deeper)
                        if child_result is not None and child_result.children:
                            logger.info(
                                "UWP fallback (depth=%d): found %d children "
                                "via child HWND %s",
                                deeper, len(child_result.children), child_hwnd,
                            )
                            return child_result
            return current_result

        if backend == "jab":
            result = core.jab_get_element_tree(hwnd=handle, depth=depth)
            result = _try_uwp_children(
                result,
                lambda h, d: core.jab_get_element_tree(hwnd=h, depth=d),
            )
        elif backend == "ia2":
            result = core.ia2_get_element_tree(hwnd=handle, depth=depth)
            result = _try_uwp_children(
                result,
                lambda h, d: core.ia2_get_element_tree(hwnd=h, depth=d),
            )
        elif backend == "msaa":
            result = core.msaa_get_element_tree(hwnd=handle, depth=depth)
            result = _try_uwp_children(
                result,
                lambda h, d: core.msaa_get_element_tree(hwnd=h, depth=d),
            )
        elif backend == "win32":
            # Pure Win32 HWND enumeration (VB6/ActiveX fallback)
            from naturo.bridge import enumerate_child_windows
            result = enumerate_child_windows(hwnd=handle, depth=depth)
        elif backend == "win32hybrid":
            # Win32 HWND tree + UIA drill-down for complex controls (#312)
            from naturo.bridge import enumerate_hybrid_tree
            result = enumerate_hybrid_tree(
                hwnd=handle, depth=depth, core=core,
            )
        elif backend == "auto":
            result = core.get_element_tree(hwnd=handle, depth=depth)
            # UWP/WinUI fallback: try child windows of AFH
            result = _try_uwp_children(
                result,
                lambda h, d: core.get_element_tree(hwnd=h, depth=d),
            )
            
            # Win32+UIA hybrid fallback for VB6/ActiveX apps (#308, #312)
            # When UIA returns shallow trees (only Pane containers),
            # use hybrid enumeration: Win32 HWND tree as base with UIA
            # drill-down for complex controls (grids, list views, tree views).
            if result is not None and self._is_shallow_tree(result):
                logger.info(
                    "UIA returned shallow tree (%d children), "
                    "trying Win32+UIA hybrid enumeration (VB6/ActiveX)",
                    len(result.children)
                )
                from naturo.bridge import enumerate_hybrid_tree
                hybrid_result = enumerate_hybrid_tree(
                    hwnd=handle, depth=depth, core=core,
                )
                if hybrid_result is not None and len(hybrid_result.children) > len(result.children):
                    logger.info(
                        "Hybrid fallback found %d children (vs %d from UIA), using it",
                        len(hybrid_result.children), len(result.children)
                    )
                    result = hybrid_result
            
            if result is None or (not result.children and not result.name):
                # Try IA2 first (Firefox/Thunderbird/LibreOffice), then MSAA
                ia2_result = core.ia2_get_element_tree(hwnd=handle, depth=depth)
                if ia2_result is not None:
                    result = ia2_result
                else:
                    # Try JAB for Java applications
                    jab_result = core.jab_get_element_tree(hwnd=handle, depth=depth)
                    if jab_result is not None:
                        result = jab_result
                    else:
                        msaa_result = core.msaa_get_element_tree(hwnd=handle, depth=depth)
                        if msaa_result is not None:
                            result = msaa_result
                        else:
                            # Final fallback: hybrid Win32+UIA enumeration
                            from naturo.bridge import enumerate_hybrid_tree
                            hybrid_result = enumerate_hybrid_tree(
                                hwnd=handle, depth=depth, core=core,
                            )
                            if hybrid_result is not None:
                                logger.info("Auto mode: all backends failed, using Win32+UIA hybrid fallback")
                                result = hybrid_result
        else:
            result = core.get_element_tree(hwnd=handle, depth=depth)
            # UWP/WinUI fallback for explicit "uia" backend too
            result = _try_uwp_children(
                result,
                lambda h, d: core.get_element_tree(hwnd=h, depth=d),
            )

        if result is None:
            return None

        # Post-process: assign sequential IDs and fill parent_id
        populate_hierarchy(result)

        # (#372) Roles that should include a text value preview
        _PREVIEW_ROLES = {"Document", "Edit", "Text"}

        def convert(el) -> BaseElementInfo:
            """Convert bridge ElementInfo to backend ElementInfo."""
            props = {
                k: v for k, v in {
                    "parent_id": el.parent_id,
                    "keyboard_shortcut": el.keyboard_shortcut,
                }.items() if v is not None
            }

            # (#372) Add value preview for Document/Edit/Text elements
            if el.role in _PREVIEW_ROLES and el.value:
                full_text = el.value
                preview = full_text[:100]
                if len(full_text) > 100:
                    preview += "…"
                props["value_preview"] = preview
                props["value_length"] = len(full_text)

            return BaseElementInfo(
                id=el.id,
                role=el.role,
                name=el.name,
                value=el.value,
                x=el.x,
                y=el.y,
                width=el.width,
                height=el.height,
                children=[convert(c) for c in el.children],
                properties=props,
            )

        return convert(result)

    def get_element_value(
        self,
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        app: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> Optional[dict]:
        """Read the current value/text of a UI element via UIA patterns.

        Supports element refs (e47), AutomationId, or role+name lookup.
        Queries ValuePattern, TogglePattern, SelectionPattern,
        RangeValuePattern, and TextPattern.

        Args:
            ref: Element ref from snapshot (e.g. ``"e47"``).
            automation_id: UIA AutomationId string.
            role: Element role (e.g. ``"Edit"``).
            name: Element name.
            app: Application name (partial match) for window targeting.
            window_title: Window title for targeting.
            hwnd: Window handle.

        Returns:
            Dict with ``value``, ``pattern``, ``role``, ``name``,
            ``automation_id``, and bounding rect; or ``None`` if not found.

        Raises:
            NaturoError: If the element cannot be found or queried.
        """
        core = self._ensure_core()

        # Resolve ref to element metadata via snapshot cache
        resolved_aid = automation_id
        resolved_role = role
        resolved_name = name
        target_hwnd = hwnd or 0

        if ref and not resolved_aid:
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            result = mgr.resolve_ref_element(ref)
            if result:
                elem, _snap_id = result
                # Use the element's identifier (AutomationId) if available
                if elem.identifier:
                    resolved_aid = elem.identifier
                elif elem.role and elem.title:
                    resolved_role = elem.role
                    resolved_name = elem.title
                elif elem.role and elem.label:
                    resolved_role = elem.role
                    resolved_name = elem.label
                else:
                    raise NaturoError(
                        f"Element {ref} has no AutomationId, role, or name "
                        f"for value lookup"
                    )
            else:
                raise NaturoError(
                    f"Element ref '{ref}' not found in snapshot cache. "
                    f"Run 'naturo see' first to capture elements."
                )

        # Resolve app/window_title to HWND for targeted lookup
        if (app or window_title) and not target_hwnd:
            try:
                target_hwnd = self._resolve_hwnd(
                    app=app, window_title=window_title
                )
            except Exception:
                # Fall back to scanning windows manually
                if window_title:
                    wins = core.list_windows()
                    for w in wins:
                        if window_title.lower() in (w.title or "").lower():
                            target_hwnd = w.hwnd
                            break

        if not resolved_aid and not resolved_role and not resolved_name:
            # (#242) Fallback: when no element identifiers are provided but
            # we have a target HWND (e.g., from --app notepad), auto-probe
            # common editable element roles in the window. This enables
            # verification for the common `type --app X --verify` pattern.
            if target_hwnd:
                _editable_roles = ("Edit", "Document", "RichEdit20W")
                for _probe_role in _editable_roles:
                    _probe_result = core.get_element_value(
                        hwnd=target_hwnd,
                        automation_id=None,
                        role=_probe_role,
                        name=None,
                    )
                    if _probe_result is not None:
                        _probe_result["probe_role"] = _probe_role
                        return _probe_result
                # All probes failed — still no identifiers available
                raise NaturoError(
                    "No editable element found in target window. "
                    "Tried probing roles: Edit, Document, RichEdit20W. "
                    "Use --on eN to specify the target element explicitly."
                )
            raise NaturoError(
                "Must specify ref, automation_id, or role/name to get value"
            )

        result = core.get_element_value(
            hwnd=target_hwnd,
            automation_id=resolved_aid,
            role=resolved_role,
            name=resolved_name,
        )

        # (#352) Role alias fallback: when an explicit role search fails,
        # try common aliases.  Win11 Notepad uses "Document" for its text
        # editor, but users naturally try "Edit".  This maps between roles
        # that serve similar purposes in different app frameworks.
        if result is None and resolved_role and not resolved_aid:
            _ROLE_ALIASES: dict[str, list[str]] = {
                "Edit": ["Document", "RichEdit20W"],
                "Document": ["Edit", "RichEdit20W"],
                "RichEdit20W": ["Edit", "Document"],
                "Text": ["StaticText"],
                "StaticText": ["Text"],
            }
            aliases = _ROLE_ALIASES.get(resolved_role, [])
            for alias_role in aliases:
                result = core.get_element_value(
                    hwnd=target_hwnd,
                    automation_id=resolved_aid,
                    role=alias_role,
                    name=resolved_name,
                )
                if result is not None:
                    break

        # (#521) NameProperty fallback: if the C++ core found the element but
        # no UIA pattern returned a value, use the element's Name property.
        # This handles Text/Static elements (e.g. Calculator display) where
        # the value is embedded in the UIA Name (e.g. "显示为 579").
        if isinstance(result, dict) and result.get("value") is None:
            elem_name = result.get("name")
            if elem_name:
                result["value"] = elem_name
                result["pattern"] = "NameProperty"

        # (#229) Fallback: if UIA lookup returned None but we have snapshot
        # data from the ref, return the snapshot metadata so the caller gets
        # at least role/name/bounds instead of ELEMENT_NOT_FOUND.
        if result is None and ref:
            from naturo.snapshot import get_snapshot_manager as _gsm
            _mgr = _gsm()
            _el_result = _mgr.resolve_ref_element(ref)
            if _el_result:
                _elem, _snap = _el_result
                ex, ey, ew, eh = _elem.frame
                result = {
                    "role": _elem.role,
                    "name": _elem.title or _elem.label,
                    "value": _elem.value,
                    "pattern": None,
                    "automation_id": _elem.identifier,
                    "x": ex,
                    "y": ey,
                    "width": ew,
                    "height": eh,
                    "source": "snapshot",
                }

        return result

    # === Phase 2: Input ===

    def click(self, x: Optional[int] = None, y: Optional[int] = None,
              element_id: Optional[str] = None, button: str = "left",
              double: bool = False, input_mode: str = "normal",
              hwnd: Optional[int] = None) -> None:
        """Click at coordinates or on a UI element.

        If an element_id is provided, finds the element first and clicks its
        center. If x/y coordinates are provided, moves to them first.
        At least one of x/y or element_id must be given.

        Args:
            x: Target X coordinate. Required if element_id not given.
            y: Target Y coordinate. Required if element_id not given.
            element_id: Automation element ID to find and click.
            button: Mouse button — "left", "right", or "middle".
            double: True for double-click.
            input_mode: Ignored for now (Phase 3 will add hardware/hook modes).
            hwnd: Target window handle for element search.  When provided,
                searches within this window instead of the foreground
                window (#525).

        Raises:
            ValueError: If neither coordinates nor element_id is provided.
            ElementNotFoundError: When element_id is given but not found.
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()

        BUTTON_MAP = {"left": 0, "right": 1, "middle": 2}
        btn = BUTTON_MAP.get(button.lower(), 0)

        if element_id is not None:
            # Find element and click its center
            el = self.find_element(selector=element_id, hwnd=hwnd)
            if el is None:
                from naturo.errors import ElementNotFoundError
                raise ElementNotFoundError(element_id)
            cx = el.x + el.width // 2
            cy = el.y + el.height // 2
            core.mouse_move(cx, cy)
        elif x is not None and y is not None:
            core.mouse_move(x, y)
        else:
            raise ValueError("click: provide either (x, y) or element_id")

        core.mouse_click(btn, double)

    def click_element_uia(
        self,
        x: int,
        y: int,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> bool:
        """Click a UI element at (x, y) using UIA patterns instead of SendInput.

        For UWP apps hosted by ApplicationFrameHost.exe, SendInput clicks
        don't reach the inner content.  This method uses UIA to find the
        element at the given point and invokes it via InvokePattern,
        TogglePattern, or SelectionItemPattern (#248).

        Args:
            x: Screen X coordinate of the target element center.
            y: Screen Y coordinate of the target element center.
            app: Application name (used to resolve window handle).
            hwnd: Direct window handle.

        Returns:
            True if UIA invoke succeeded, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception) as exc:
            logger.debug("comtypes not available for UIA click: %s", exc)
            return False

        try:
            from ctypes import wintypes
            from comtypes import COMError  # type: ignore[import-untyped]

            # Use UIA.ElementFromPoint to find the element at coordinates
            point = wintypes.POINT(x, y)
            element = uia.ElementFromPoint(point)
            if element is None:
                logger.debug("UIA click: no element found at (%d, %d)", x, y)
                return False

            elem_name = element.CurrentName or ""
            logger.debug("UIA click: found element %r at (%d, %d)", elem_name, x, y)

            # Try InvokePattern first (buttons, links, menu items)
            try:
                pattern = element.GetCurrentPattern(mod.UIA_InvokePatternId)
                if pattern is not None:
                    invoke = pattern.QueryInterface(mod.IUIAutomationInvokePattern)
                    invoke.Invoke()
                    logger.info("UIA click: invoked %r via InvokePattern", elem_name)
                    return True
            except (COMError, AttributeError):
                pass

            # Try TogglePattern (checkboxes, toggle buttons)
            try:
                pattern = element.GetCurrentPattern(mod.UIA_TogglePatternId)
                if pattern is not None:
                    toggle = pattern.QueryInterface(mod.IUIAutomationTogglePattern)
                    toggle.Toggle()
                    logger.info("UIA click: toggled %r via TogglePattern", elem_name)
                    return True
            except (COMError, AttributeError):
                pass

            # Try SelectionItemPattern (radio buttons, list items)
            try:
                pattern = element.GetCurrentPattern(mod.UIA_SelectionItemPatternId)
                if pattern is not None:
                    sel = pattern.QueryInterface(mod.IUIAutomationSelectionItemPattern)
                    sel.Select()
                    logger.info("UIA click: selected %r via SelectionItemPattern", elem_name)
                    return True
            except (COMError, AttributeError):
                pass

            logger.debug(
                "UIA click: element %r at (%d, %d) supports no invoke/toggle/select pattern",
                elem_name, x, y,
            )
            return False

        except Exception as exc:
            logger.debug("UIA click failed at (%d, %d): %s", x, y, exc)
            return False

    def invoke_element(self, name: str, role: str) -> bool:
        """Invoke a UI element by name and role using UIA InvokePattern.

        This is a fallback for elements whose bounding rects are zero-size
        (e.g. TitleBar buttons after a window state change).  Instead of
        coordinate-based clicking, it searches the UIA tree for a matching
        element and calls ``IUIAutomationInvokePattern::Invoke()``.

        Args:
            name: The element's accessible name (e.g. "Minimize", "Close").
            role: The element's UIA control type (e.g. "Button").

        Returns:
            True if the element was found and Invoke succeeded, False otherwise.
        """
        try:
            import comtypes.client  # type: ignore[import-untyped]
            from comtypes import COMError  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("comtypes not available — cannot use Invoke fallback")
            return False

        try:
            # Ensure comtypes gen modules are initialized before importing
            # from comtypes.gen.UIAutomationClient (#200).  GetModule triggers
            # type-library code generation on first use.
            try:
                from comtypes.gen.UIAutomationClient import IUIAutomation  # type: ignore[import-untyped]
            except (ImportError, ModuleNotFoundError):
                comtypes.client.GetModule("UIAutomationCore.dll")

            uia = comtypes.client.CreateObject(
                "{ff48dba4-60ef-4201-aa87-54103eef594e}",
                interface=None,
            )
            # IUIAutomation interface
            from comtypes.gen.UIAutomationClient import (  # type: ignore[import-untyped]
                IUIAutomation,
                TreeScope_Descendants,
                UIA_NamePropertyId,
                UIA_InvokePatternId,
            )
            uia = uia.QueryInterface(IUIAutomation)
            root = uia.GetRootElement()

            # Build a condition: Name == name
            name_cond = uia.CreatePropertyCondition(UIA_NamePropertyId, name)
            found = root.FindFirst(TreeScope_Descendants, name_cond)
            if found is None:
                logger.warning("Invoke fallback: element %r not found in UIA tree", name)
                return False

            # Try InvokePattern
            pattern = found.GetCurrentPattern(UIA_InvokePatternId)
            if pattern is None:
                logger.warning("Invoke fallback: element %r does not support InvokePattern", name)
                return False

            from comtypes.gen.UIAutomationClient import IUIAutomationInvokePattern  # type: ignore[import-untyped]
            invoke = pattern.QueryInterface(IUIAutomationInvokePattern)
            invoke.Invoke()
            logger.info("Invoke fallback: successfully invoked %r (%s)", name, role)
            return True

        except (COMError, OSError, AttributeError) as exc:
            logger.warning("Invoke fallback failed for %r: %s", name, exc)
            return False
        except Exception as exc:
            logger.warning("Invoke fallback unexpected error for %r: %s", name, exc)
            return False

    def _init_comtypes_uia(self):
        """Initialize comtypes UIA and return (uia, module) tuple.

        Ensures comtypes gen modules are generated before importing from them.
        Returns a tuple of (IUIAutomation instance, module reference).

        Raises:
            ImportError: If comtypes is not available.
            Exception: If UIA COM initialization fails.
        """
        import comtypes.client  # type: ignore[import-untyped]
        try:
            from comtypes.gen import UIAutomationClient as mod  # type: ignore[import-untyped]
        except (ImportError, ModuleNotFoundError):
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient as mod  # type: ignore[import-untyped]

        uia = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}",
            interface=mod.IUIAutomation,
        )
        return uia, mod

    def _find_uia_element(self, uia, mod, hwnd: int = 0,
                          name: Optional[str] = None,
                          automation_id: Optional[str] = None,
                          role: Optional[str] = None):
        """Find a UIA element in the tree by name, automationId, or role.

        Searches under the given window (by hwnd) or the entire desktop.

        Args:
            uia: IUIAutomation instance from _init_comtypes_uia.
            mod: UIAutomationClient module.
            hwnd: Window handle to scope the search.  0 = desktop root.
            name: Accessible name of the element.
            automation_id: UIA AutomationId of the element.
            role: UIA control type name (e.g. "Edit", "Button").

        Returns:
            IUIAutomationElement if found, None otherwise.
        """

        if hwnd:
            root = uia.ElementFromHandle(hwnd)
        else:
            root = uia.GetRootElement()

        conditions = []
        if automation_id:
            conditions.append(
                uia.CreatePropertyCondition(mod.UIA_AutomationIdPropertyId, automation_id)
            )
        if name:
            conditions.append(
                uia.CreatePropertyCondition(mod.UIA_NamePropertyId, name)
            )

        if not conditions:
            return None

        # Combine conditions with AND
        if len(conditions) == 1:
            cond = conditions[0]
        else:
            cond = conditions[0]
            for c in conditions[1:]:
                cond = uia.CreateAndCondition(cond, c)

        return root.FindFirst(mod.TreeScope_Descendants, cond)

    def set_element_value(
        self,
        text: str,
        hwnd: int = 0,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> bool:
        """Set text on a UI element using UIA ValuePattern.SetValue().

        This bypasses SendInput entirely, directly setting the element's
        value through the UIA accessibility interface. Works reliably in
        schtasks / remote session contexts where SendInput has no effect.

        Args:
            text: Text to set on the element.
            hwnd: Window handle to scope the search. 0 = desktop root.
            name: Accessible name of the target element.
            automation_id: UIA AutomationId of the target element.
            role: UIA control type (e.g. "Edit").

        Returns:
            True if SetValue succeeded, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use SetValue")
            return False

        try:
            elem = self._find_uia_element(uia, mod, hwnd=hwnd, name=name,
                                          automation_id=automation_id, role=role)
            if elem is None:
                # If targeting by name/automation_id failed, try finding the
                # first editable element (e.g. Edit control) in the window
                if hwnd and role:
                    root = uia.ElementFromHandle(hwnd)
                    # Map common role names to UIA ControlTypeId
                    role_map = {
                        "Edit": 50004, "Document": 50030, "Text": 50020,
                    }
                    ctl_type_id = role_map.get(role)
                    if ctl_type_id:
                        cond = uia.CreatePropertyCondition(
                            mod.UIA_ControlTypePropertyId, ctl_type_id
                        )
                        elem = root.FindFirst(mod.TreeScope_Descendants, cond)

                if elem is None:
                    logger.debug("SetValue: target element not found (name=%r, aid=%r, role=%r)",
                                 name, automation_id, role)
                    return False

            # Try ValuePattern
            pat_unk = elem.GetCurrentPattern(mod.UIA_ValuePatternId)
            if pat_unk is None:
                logger.debug("SetValue: element does not support ValuePattern")
                return False

            vp = pat_unk.QueryInterface(mod.IUIAutomationValuePattern)

            # Check if the value is read-only
            if vp.CurrentIsReadOnly:
                logger.debug("SetValue: element's ValuePattern is read-only")
                return False

            vp.SetValue(text)
            logger.info("SetValue: successfully set text on element (name=%r, len=%d)",
                        name, len(text))
            return True

        except (OSError, AttributeError) as exc:
            logger.debug("SetValue failed: %s", exc)
            return False
        except Exception as exc:
            logger.debug("SetValue unexpected error: %s", exc)
            return False

    def toggle_element(
        self,
        hwnd: int = 0,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[str]:
        """Toggle a UI element via UIA TogglePattern.

        Args:
            hwnd: Window handle to scope the search.  0 = desktop root.
            automation_id: UIA AutomationId.
            role: Element role (e.g. ``"CheckBox"``).
            name: Element name.

        Returns:
            New toggle state string (``"On"``, ``"Off"``, or
            ``"Indeterminate"``), or ``None`` if the element was not found
            or does not support TogglePattern.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use TogglePattern")
            return None

        try:
            from comtypes import COMError  # type: ignore[import-untyped]

            elem = self._find_uia_element(uia, mod, hwnd=hwnd, name=name,
                                          automation_id=automation_id, role=role)
            if elem is None:
                logger.debug("Toggle: target element not found")
                return None

            pat_unk = elem.GetCurrentPattern(mod.UIA_TogglePatternId)
            if pat_unk is None:
                logger.debug("Toggle: element does not support TogglePattern")
                return None

            tp = pat_unk.QueryInterface(mod.IUIAutomationTogglePattern)
            tp.Toggle()

            # Read new state: 0=Off, 1=On, 2=Indeterminate
            state_map = {0: "Off", 1: "On", 2: "Indeterminate"}
            new_state = state_map.get(tp.CurrentToggleState, "Unknown")
            logger.info("Toggle: toggled element (name=%r) → %s", name, new_state)
            return new_state

        except (COMError, OSError, AttributeError) as exc:
            logger.debug("Toggle failed: %s", exc)
            return None
        except Exception as exc:
            logger.debug("Toggle unexpected error: %s", exc)
            return None

    def select_element(
        self,
        hwnd: int = 0,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
    ) -> bool:
        """Select a UI element via UIA SelectionItemPattern.

        Args:
            hwnd: Window handle to scope the search.  0 = desktop root.
            automation_id: UIA AutomationId.
            role: Element role (e.g. ``"ListItem"``, ``"RadioButton"``).
            name: Element name.

        Returns:
            True if the element was selected, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use SelectionItemPattern")
            return False

        try:
            from comtypes import COMError  # type: ignore[import-untyped]

            elem = self._find_uia_element(uia, mod, hwnd=hwnd, name=name,
                                          automation_id=automation_id, role=role)
            if elem is None:
                logger.debug("Select: target element not found")
                return False

            pat_unk = elem.GetCurrentPattern(mod.UIA_SelectionItemPatternId)
            if pat_unk is None:
                logger.debug("Select: element does not support SelectionItemPattern")
                return False

            sp = pat_unk.QueryInterface(mod.IUIAutomationSelectionItemPattern)
            sp.Select()
            logger.info("Select: selected element (name=%r)", name)
            return True

        except (COMError, OSError, AttributeError) as exc:
            logger.debug("Select failed: %s", exc)
            return False
        except Exception as exc:
            logger.debug("Select unexpected error: %s", exc)
            return False

    def expand_collapse_element(
        self,
        hwnd: int = 0,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        expand: bool = True,
    ) -> bool:
        """Expand or collapse a UI element via UIA ExpandCollapsePattern.

        Args:
            hwnd: Window handle to scope the search.  0 = desktop root.
            automation_id: UIA AutomationId.
            role: Element role (e.g. ``"ComboBox"``, ``"TreeItem"``).
            name: Element name.
            expand: True to expand, False to collapse.

        Returns:
            True if the operation succeeded, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use ExpandCollapsePattern")
            return False

        try:
            from comtypes import COMError  # type: ignore[import-untyped]

            elem = self._find_uia_element(uia, mod, hwnd=hwnd, name=name,
                                          automation_id=automation_id, role=role)
            if elem is None:
                logger.debug("ExpandCollapse: target element not found")
                return False

            pat_unk = elem.GetCurrentPattern(mod.UIA_ExpandCollapsePatternId)
            if pat_unk is None:
                logger.debug("ExpandCollapse: element does not support ExpandCollapsePattern")
                return False

            ecp = pat_unk.QueryInterface(mod.IUIAutomationExpandCollapsePattern)
            if expand:
                ecp.Expand()
                logger.info("ExpandCollapse: expanded element (name=%r)", name)
            else:
                ecp.Collapse()
                logger.info("ExpandCollapse: collapsed element (name=%r)", name)
            return True

        except (COMError, OSError, AttributeError) as exc:
            logger.debug("ExpandCollapse failed: %s", exc)
            return False
        except Exception as exc:
            logger.debug("ExpandCollapse unexpected error: %s", exc)
            return False

    def focus_element_uia(
        self,
        hwnd: int = 0,
        name: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> bool:
        """Focus a UI element using UIA SetFocus().

        Directly sets keyboard focus on a UIA element. Works in schtasks
        context where SetForegroundWindow + mouse click may not deliver
        actual focus.

        Args:
            hwnd: Window handle to scope the search.
            name: Accessible name of the target element.
            automation_id: UIA AutomationId.
            role: UIA control type.

        Returns:
            True if SetFocus succeeded, False otherwise.
        """
        try:
            uia, mod = self._init_comtypes_uia()
        except (ImportError, Exception):
            logger.debug("comtypes not available — cannot use UIA SetFocus")
            return False

        try:
            elem = self._find_uia_element(uia, mod, hwnd=hwnd, name=name,
                                          automation_id=automation_id, role=role)

            # (#441) When called with only hwnd (no name/role/automationId),
            # _find_uia_element returns None because there are no conditions.
            # Fall back to finding the first Edit or Document control in the
            # window — this restores keyboard focus to the main content area
            # after menu interactions or other focus-stealing events.
            if elem is None and hwnd and not name and not automation_id and not role:
                root = uia.ElementFromHandle(hwnd)
                for ctl_type_id in (50004, 50030):  # Edit, Document
                    cond = uia.CreatePropertyCondition(
                        mod.UIA_ControlTypePropertyId, ctl_type_id
                    )
                    elem = root.FindFirst(mod.TreeScope_Descendants, cond)
                    if elem is not None:
                        break

            if elem is None:
                logger.debug("UIA SetFocus: element not found (name=%r, role=%r)", name, role)
                return False

            elem.SetFocus()
            logger.info("UIA SetFocus: focused element (name=%r, role=%r)", name, role)
            return True

        except (OSError, AttributeError) as exc:
            logger.debug("UIA SetFocus failed: %s", exc)
            return False
        except Exception as exc:
            logger.debug("UIA SetFocus unexpected error: %s", exc)
            return False

    def type_text(self, text: str = "", delay_ms: int = 5, profile: str = "linear",
                  wpm: int = 120, input_mode: str = "normal") -> None:
        """Type text using SendInput.

        Args:
            text: UTF-8 string to type.
            delay_ms: Delay between keystrokes (milliseconds). Default: 5.
                For "human" profile, this is the base delay.
            profile: "linear" for constant delay, "human" for variable speed.
                     Human profile uses wpm to calculate delay.
            wpm: Words per minute (used only when profile="human").
            input_mode: Input method — "normal" (virtual key / Unicode) or
                "hardware" (scan code / Phys32, bypasses game anti-cheat).

        Raises:
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()

        actual_delay = delay_ms
        if profile == "human" and wpm > 0:
            # Average word = 5 chars, convert wpm to ms per char
            ms_per_char = int(60_000 / (wpm * 5))
            actual_delay = max(1, ms_per_char)

        if input_mode == "hardware":
            core.phys_key_type(text, actual_delay)
        else:
            core.key_type(text, actual_delay)

    def press_key(self, key: str = "", input_mode: str = "normal") -> None:
        """Press and release a named key.

        Args:
            key: Key name (enter, tab, escape, f1-f12, a-z, 0-9, etc.).
            input_mode: Input method — "normal" (virtual key) or
                "hardware" (scan code / Phys32).

        Raises:
            NaturoCoreError: If key name is unrecognized or on system error.
        """
        core = self._ensure_core()
        if input_mode == "hardware":
            core.phys_key_press(key)
        else:
            core.key_press(key)

    def hotkey(self, *keys: str, hold_duration_ms: int = 50,
              input_mode: str = "normal") -> None:
        """Press a hotkey combination.

        Args:
            *keys: Key names. Modifiers (ctrl, alt, shift, win) are recognized
                   automatically. One non-modifier key is the base key.
            hold_duration_ms: Not yet used.
            input_mode: Input method — "normal" (virtual key) or
                "hardware" (scan code / Phys32).

        Example:
            backend.hotkey("ctrl", "c")   # Copy
            backend.hotkey("ctrl", "z")   # Undo

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        core = self._ensure_core()
        if input_mode == "hardware":
            core.phys_key_hotkey(*keys)
        else:
            core.key_hotkey(*keys)

    def scroll(self, direction: str = "down", amount: int = 3,
               x: Optional[int] = None, y: Optional[int] = None,
               smooth: bool = False) -> None:
        """Scroll the mouse wheel.

        Args:
            direction: "up", "down", "left", or "right".
            amount: Number of wheel notches (each = 120 delta units).
            x: Move mouse to this X before scrolling. None = current position.
            y: Move mouse to this Y before scrolling. None = current position.
            smooth: Ignored (Phase 3 will add smooth scroll support).

        Raises:
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()

        if x is not None and y is not None:
            core.mouse_move(x, y)

        WHEEL_DELTA = 120
        horizontal = direction in ("left", "right")
        # Up/right = positive, Down/left = negative
        sign = 1 if direction in ("up", "right") else -1
        delta = sign * amount * WHEEL_DELTA

        core.mouse_scroll(delta, horizontal)

    def drag(self, from_x: int = 0, from_y: int = 0, to_x: int = 0, to_y: int = 0,
             duration_ms: int = 500, steps: int = 10) -> None:
        """Drag from one point to another.

        Moves mouse to (from_x, from_y), holds left button, interpolates to
        (to_x, to_y) in `steps` increments, then releases the button.

        Args:
            from_x: Source X coordinate.
            from_y: Source Y coordinate.
            to_x: Destination X coordinate.
            to_y: Destination Y coordinate.
            duration_ms: Total drag duration in milliseconds.
            steps: Number of intermediate move steps.

        Raises:
            NaturoCoreError: On system error.
        """
        import time
        core = self._ensure_core()

        steps = max(1, steps)
        delay_s = (duration_ms / 1000.0) / steps

        core.mouse_move(from_x, from_y)
        time.sleep(0.05)  # Brief settle before pressing
        core.mouse_down(0)  # Press and hold left button

        try:
            for i in range(1, steps + 1):
                t = i / steps
                ix = int(from_x + (to_x - from_x) * t)
                iy = int(from_y + (to_y - from_y) * t)
                core.mouse_move(ix, iy)
                time.sleep(delay_s)
        finally:
            core.mouse_up(0)  # Always release, even on error

    def move_mouse(self, x: int = 0, y: int = 0) -> None:
        """Move the mouse cursor to absolute screen coordinates.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.

        Raises:
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()
        core.mouse_move(x, y)

    def clipboard_get(self) -> str:
        """Get text content from the clipboard.

        Uses the pyperclip library as a portable clipboard interface.

        Returns:
            Clipboard text, or empty string if clipboard is empty.
        """
        try:
            import pyperclip  # type: ignore
            return pyperclip.paste() or ""
        except ImportError:
            # Fallback: use ctypes Win32 API directly
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                # Set proper restype/argtypes for 64-bit pointer safety
                user32.GetClipboardData.restype = ctypes.c_void_p
                kernel32.GlobalLock.restype = ctypes.c_void_p
                kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                if not user32.OpenClipboard(0):
                    raise NaturoError("Failed to open clipboard")
                try:
                    CF_UNICODETEXT = 13
                    h = user32.GetClipboardData(CF_UNICODETEXT)
                    if not h:
                        return ""
                    ptr = kernel32.GlobalLock(h)
                    if not ptr:
                        raise NaturoError("Failed to lock clipboard memory")
                    try:
                        return ctypes.wstring_at(ptr)
                    finally:
                        kernel32.GlobalUnlock(h)
                finally:
                    user32.CloseClipboard()
            except NaturoError:
                raise
            except Exception as exc:
                raise NaturoError(f"Clipboard read failed: {exc}") from exc

    def clipboard_set(self, text: str = "") -> None:
        """Set the clipboard text content.

        Args:
            text: Text to place on the clipboard.
        """
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(text)
        except ImportError:
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                # Set proper restype/argtypes for 64-bit pointer safety
                kernel32.GlobalAlloc.restype = ctypes.c_void_p
                kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
                kernel32.GlobalLock.restype = ctypes.c_void_p
                kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                user32.SetClipboardData.restype = ctypes.c_void_p
                user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
                CF_UNICODETEXT = 13
                GMEM_MOVEABLE = 2
                encoded = (text + "\0").encode("utf-16-le")
                h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
                if not h:
                    raise NaturoError("Failed to allocate clipboard memory")
                ptr = kernel32.GlobalLock(h)
                if not ptr:
                    kernel32.GlobalFree = kernel32.GlobalFree  # noqa: E731
                    raise NaturoError("Failed to lock clipboard memory")
                ctypes.memmove(ptr, encoded, len(encoded))
                kernel32.GlobalUnlock(h)
                if not user32.OpenClipboard(0):
                    raise NaturoError("Failed to open clipboard")
                try:
                    user32.EmptyClipboard()
                    user32.SetClipboardData(CF_UNICODETEXT, h)
                finally:
                    user32.CloseClipboard()
            except NaturoError:
                raise
            except Exception as exc:
                raise NaturoError(f"Clipboard write failed: {exc}") from exc

    def clipboard_clear(self) -> None:
        """Clear the clipboard contents."""
        try:
            import pyperclip  # type: ignore
            pyperclip.copy("")
        except ImportError:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                if not user32.OpenClipboard(0):
                    raise NaturoError("Failed to open clipboard")
                try:
                    user32.EmptyClipboard()
                finally:
                    user32.CloseClipboard()
            except NaturoError:
                raise
            except Exception as exc:
                raise NaturoError(f"Clipboard clear failed: {exc}") from exc

    def clipboard_info(self) -> dict:
        """Return information about the current clipboard contents.

        Checks for text, image (CF_DIB/CF_BITMAP), and file (CF_HDROP)
        formats using the Win32 API.

        Returns:
            Dictionary with format, size, has_text, has_image, has_files.
        """
        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.GetClipboardData.restype = ctypes.c_void_p
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalSize.restype = ctypes.c_size_t
            kernel32.GlobalSize.argtypes = [ctypes.c_void_p]

            if not user32.OpenClipboard(0):
                raise NaturoError("Failed to open clipboard")
            try:
                CF_UNICODETEXT = 13
                CF_BITMAP = 2
                CF_DIB = 8
                CF_HDROP = 15

                has_text = bool(user32.IsClipboardFormatAvailable(CF_UNICODETEXT))
                has_image = bool(
                    user32.IsClipboardFormatAvailable(CF_BITMAP)
                    or user32.IsClipboardFormatAvailable(CF_DIB)
                )
                has_files = bool(user32.IsClipboardFormatAvailable(CF_HDROP))

                size = 0
                if has_text:
                    fmt = "text"
                    h = user32.GetClipboardData(CF_UNICODETEXT)
                    if h:
                        size = kernel32.GlobalSize(h)
                elif has_image:
                    fmt = "image"
                    h = user32.GetClipboardData(CF_DIB)
                    if h:
                        size = kernel32.GlobalSize(h)
                elif has_files:
                    fmt = "files"
                else:
                    fmt = "empty"

                return {
                    "format": fmt,
                    "size": size,
                    "has_text": has_text,
                    "has_image": has_image,
                    "has_files": has_files,
                }
            finally:
                user32.CloseClipboard()
        except NaturoError:
            raise
        except Exception as exc:
            raise NaturoError(f"Clipboard info failed: {exc}") from exc

    # System/framework processes to exclude from app list — these have visible
    # windows but are not user-facing applications.
    _SYSTEM_PROCESS_NAMES: set[str] = {
        "textinputhost.exe", "shellexperiencehost.exe",
        "searchhost.exe", "startmenuexperiencehost.exe", "lockapp.exe",
        "systemsettings.exe", "gamebar.exe", "gamebarftserver.exe",
        "windowsinternal.composableshell.experiences.textinput.inputapp.exe",
        "widgets.exe", "widgetservice.exe", "people.exe", "cortana.exe",
        "secureinput.exe", "dwm.exe", "csrss.exe", "winlogon.exe",
        "fontdrvhost.exe", "dllhost.exe", "sihost.exe", "ctfmon.exe",
        "runtimebroker.exe", "backgroundtaskhost.exe", "taskhostw.exe",
        "smartscreen.exe", "searchui.exe", "shellhost.exe",
    }

    # ApplicationFrameHost.exe hosts UWP apps (Calculator, Settings, etc.).
    # Unlike other system processes, AFH windows with non-empty titles are
    # real user-facing apps that should appear in app list.
    _UWP_HOST_PROCESS: str = "applicationframehost.exe"

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
            sub = WindowsBackend._element_to_menu_item(child)
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
