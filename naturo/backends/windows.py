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
from naturo.bridge import NaturoCore, NaturoCoreError, populate_hierarchy
from naturo.errors import NaturoError
from naturo.models.menu import MenuItem
from typing import List, Optional

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
        import tempfile, os
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
        import tempfile, os
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
        if self._is_iconic(handle):
            ctypes.windll.user32.ShowWindow(handle, SW_RESTORE)
        ctypes.windll.user32.SetForegroundWindow(handle)

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

    def find_element(self, selector: str = "", window_title: Optional[str] = None) -> Optional[BaseElementInfo]:
        """Find a UI element by selector string.

        The selector format is "role:name" (e.g., "Button:OK") or just a name.

        Args:
            selector: Element selector in "role:name" or "name" format.
            window_title: Not yet used (reserved for future).

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

        result = core.find_element(hwnd=0, role=role, name=name)
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

    def _resolve_hwnd(self, app: Optional[str] = None,
                      window_title: Optional[str] = None,
                      hwnd: Optional[int] = None) -> int:
        """Resolve a window handle from app name, window title, or direct hwnd.

        Matching strategy (BUG-069/BUG-070):

        When ``app`` is provided, matches against **process name first** (with
        ``.exe`` suffix stripped), then falls back to window title.  When
        ``window_title`` is provided, matches against window title only.

        Scoring (higher = better match):
          4 — exact process-name match  (e.g. ``explorer`` == ``explorer.exe``)
          3 — process-name substring    (e.g. ``expl`` in ``explorer.exe``)
          2 — exact title match         (e.g. ``notepad`` == ``Notepad``)
          1 — title substring           (e.g. ``note`` in ``Untitled - Notepad``)

        Case-insensitive throughout.  Among equal scores the window whose
        title is shortest wins (heuristic: less noise in the title ⇒ more
        likely the "main" window).

        Args:
            app: Application/process name to search for (case-insensitive,
                partial match).  Compared against process name first, then
                window title as fallback.
            window_title: Window title pattern (case-insensitive, partial
                match).  Compared against window title only.
            hwnd: Direct window handle (takes priority).

        Returns:
            Window handle (HWND), or 0 for the foreground window.

        Raises:
            WindowNotFoundError: When no matching window is found.  The error
                message includes up to 5 candidate windows.
        """
        if hwnd:
            return hwnd

        search = app or window_title
        if not search:
            return 0  # foreground window

        search_lower = search.lower()
        windows = self.list_windows()

        # --app → match process name first; --window-title → match title only
        match_process = app is not None

        best_score = 0
        best_window = None

        for w in windows:
            score = 0
            proc_stem = w.process_name.lower()
            # Strip .exe suffix for comparison
            if proc_stem.endswith(".exe"):
                proc_stem = proc_stem[:-4]
            title_lower = w.title.lower()

            if match_process:
                # Process-name matching (priority)
                if search_lower == proc_stem:
                    score = 4  # exact process name
                elif search_lower in proc_stem:
                    score = 3  # substring in process name
                # Title fallback (lower priority)
                elif search_lower == title_lower:
                    score = 2  # exact title
                elif search_lower in title_lower:
                    score = 1  # substring in title
            else:
                # --window-title: only match window title
                if search_lower == title_lower:
                    score = 4  # exact title
                elif search_lower in title_lower:
                    score = 1  # substring in title

            if score > best_score or (
                score == best_score
                and score > 0
                and best_window is not None
                and len(w.title) < len(best_window.title)
            ):
                best_score = score
                best_window = w

        if best_window is not None:
            # UWP/WinUI apps: the real UI tree lives under
            # ApplicationFrameHost.exe, not the inner process window
            # (e.g. CalculatorApp.exe).  When we matched a non-frame
            # process, check for an ApplicationFrameHost window with the
            # same title and prefer it — its element tree is complete.
            best_proc = best_window.process_name.lower()
            if best_proc.endswith(".exe"):
                best_proc = best_proc[:-4]
            if best_proc != "applicationframehost":
                for w in windows:
                    frame_proc = w.process_name.lower()
                    if frame_proc.endswith(".exe"):
                        frame_proc = frame_proc[:-4]
                    if (
                        frame_proc == "applicationframehost"
                        and w.title == best_window.title
                        and w.handle != best_window.handle
                    ):
                        best_window = w
                        break

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

        hint = f"No window matching '{search}'."
        if candidates:
            hint += " Did you mean:\n" + "\n".join(f"  • {c}" for c in candidates)
        hint += "\nTip: use 'naturo list windows' to see all windows."

        raise WindowNotFoundError(search, suggested_action=hint)

    @staticmethod
    def _find_uwp_core_hwnd(parent_hwnd: int) -> int:
        """Find the UWP CoreWindow child HWND inside an ApplicationFrameHost window.

        UWP apps wrap their actual UI inside a ``Windows.UI.Core.CoreWindow``
        child window.  ``ElementFromHandle`` on the outer frame often returns
        an empty element tree because the ControlViewWalker does not cross
        the process boundary.  Targeting the CoreWindow directly fixes this.

        Args:
            parent_hwnd: Handle of the ApplicationFrameHost top-level window.

        Returns:
            CoreWindow child HWND if found, otherwise 0.
        """
        import sys
        if sys.platform != "win32":
            return 0
        try:
            import ctypes
            user32 = ctypes.windll.user32
            FindWindowExW = user32.FindWindowExW
            FindWindowExW.restype = ctypes.c_void_p
            FindWindowExW.argtypes = [
                ctypes.c_void_p,  # hWndParent
                ctypes.c_void_p,  # hWndChildAfter
                ctypes.c_wchar_p,  # lpszClass
                ctypes.c_void_p,  # lpszWindow (NULL = any)
            ]
            core_hwnd = FindWindowExW(parent_hwnd, None,
                                      "Windows.UI.Core.CoreWindow", None)
            return int(core_hwnd) if core_hwnd else 0
        except Exception:
            return 0

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

    def get_element_tree(self, window_title: Optional[str] = None,
                         depth: int = 3,
                         app: Optional[str] = None,
                         hwnd: Optional[int] = None,
                         backend: str = "uia") -> Optional[BaseElementInfo]:
        """Get the UI element tree for a window.

        Fills parent_id, children IDs, and keyboard_shortcut for all elements
        via Python-layer post-processing (the C++ DLL does not emit these).

        For UWP apps (Calculator, Settings, etc.) the UI tree lives inside a
        ``Windows.UI.Core.CoreWindow`` child of the ``ApplicationFrameHost``
        top-level window.  When the initial traversal returns an empty tree
        from an AFH window, this method automatically retries with the
        CoreWindow child HWND.

        Args:
            window_title: Window title pattern (partial match, case-insensitive).
            depth: Maximum depth to traverse (1-10).
            app: Application name to search for (partial match, case-insensitive).
            hwnd: Direct window handle. Overrides app/window_title.
            backend: Accessibility backend — "uia" (default), "msaa", or "auto".
                     "auto" tries UIA first, falls back to MSAA if UIA returns
                     no meaningful elements.

        Returns:
            Root ElementInfo with nested children, or None.
        """
        core = self._ensure_core()
        handle = self._resolve_hwnd(app=app, window_title=window_title, hwnd=hwnd)

        def _try_uwp_core(current_result):
            """If handle is an AFH window with empty tree, retry with CoreWindow child."""
            if (current_result is not None
                    and not current_result.children
                    and handle
                    and self._is_afh_window(handle)):
                core_hwnd = self._find_uwp_core_hwnd(handle)
                if core_hwnd:
                    logger.debug(
                        "UWP fallback: retrying element tree with CoreWindow "
                        "HWND %s (parent AFH %s)", core_hwnd, handle,
                    )
                    return core_hwnd
            return 0

        if backend == "jab":
            result = core.jab_get_element_tree(hwnd=handle, depth=depth)
        elif backend == "ia2":
            result = core.ia2_get_element_tree(hwnd=handle, depth=depth)
        elif backend == "msaa":
            result = core.msaa_get_element_tree(hwnd=handle, depth=depth)
        elif backend == "auto":
            result = core.get_element_tree(hwnd=handle, depth=depth)
            # UWP fallback: ApplicationFrameHost → CoreWindow child
            uwp_hwnd = _try_uwp_core(result)
            if uwp_hwnd:
                uwp_result = core.get_element_tree(hwnd=uwp_hwnd, depth=depth)
                if uwp_result is not None and uwp_result.children:
                    result = uwp_result
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
            result = core.get_element_tree(hwnd=handle, depth=depth)
            # UWP fallback for explicit "uia" backend too
            uwp_hwnd = _try_uwp_core(result)
            if uwp_hwnd:
                uwp_result = core.get_element_tree(hwnd=uwp_hwnd, depth=depth)
                if uwp_result is not None and uwp_result.children:
                    result = uwp_result

        if result is None:
            return None

        # Post-process: assign sequential IDs and fill parent_id
        populate_hierarchy(result)

        def convert(el) -> BaseElementInfo:
            """Convert bridge ElementInfo to backend ElementInfo."""
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
                properties={
                    k: v for k, v in {
                        "parent_id": el.parent_id,
                        "keyboard_shortcut": el.keyboard_shortcut,
                    }.items() if v is not None
                },
            )

        return convert(result)

    def get_element_value(
        self,
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
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
            from naturo.snapshot import SnapshotManager
            mgr = SnapshotManager()
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

        if window_title and not target_hwnd:
            wins = core.list_windows()
            for w in wins:
                if window_title.lower() in (w.title or "").lower():
                    target_hwnd = w.hwnd
                    break

        if not resolved_aid and not resolved_role and not resolved_name:
            raise NaturoError(
                "Must specify ref, automation_id, or role/name to get value"
            )

        result = core.get_element_value(
            hwnd=target_hwnd,
            automation_id=resolved_aid,
            role=resolved_role,
            name=resolved_name,
        )
        return result

    # === Phase 2: Input ===

    def click(self, x: Optional[int] = None, y: Optional[int] = None,
              element_id: Optional[str] = None, button: str = "left",
              double: bool = False, input_mode: str = "normal") -> None:
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

        Raises:
            ValueError: If neither coordinates nor element_id is provided.
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()

        BUTTON_MAP = {"left": 0, "right": 1, "middle": 2}
        btn = BUTTON_MAP.get(button.lower(), 0)

        if element_id is not None:
            # Find element and click its center
            el = self.find_element(selector=element_id)
            if el is None:
                from naturo.bridge import NaturoCoreError
                raise NaturoCoreError(-1, f"click: element not found ({element_id!r})")
            cx = el.x + el.width // 2
            cy = el.y + el.height // 2
            core.mouse_move(cx, cy)
        elif x is not None and y is not None:
            core.mouse_move(x, y)
        else:
            raise ValueError("click: provide either (x, y) or element_id")

        core.mouse_click(btn, double)

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
            uia = comtypes.client.CreateObject(
                "{ff48dba4-60ef-4201-aa87-54103eef594e}",
                interface=None,
            )
            # IUIAutomation interface
            from comtypes.gen.UIAutomationClient import (  # type: ignore[import-untyped]
                IUIAutomation,
                IUIAutomationElement,
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
                    kernel32.GlobalFree = kernel32.GlobalFree  # noqa: keep ref
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

    # System/framework processes to exclude from app list — these have visible
    # windows but are not user-facing applications.
    _SYSTEM_PROCESS_NAMES: set[str] = {
        "applicationframehost.exe", "textinputhost.exe", "shellexperiencehost.exe",
        "searchhost.exe", "startmenuexperiencehost.exe", "lockapp.exe",
        "systemsettings.exe", "gamebar.exe", "gamebarftserver.exe",
        "windowsinternal.composableshell.experiences.textinput.inputapp.exe",
        "widgets.exe", "widgetservice.exe", "people.exe", "cortana.exe",
        "secureinput.exe", "dwm.exe", "csrss.exe", "winlogon.exe",
        "fontdrvhost.exe", "dllhost.exe", "sihost.exe", "ctfmon.exe",
        "runtimebroker.exe", "backgroundtaskhost.exe", "taskhostw.exe",
        "smartscreen.exe", "searchui.exe", "shellhost.exe",
    }

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
        """Click a menu item. Phase 3 feature."""
        raise NotImplementedError("menu_click coming in Phase 3")

    def get_menu_items(self, window_title: Optional[str] = None) -> List[MenuItem]:
        """Get menu items using Win32 API with UIA fallback.

        Strategy:
        1. Resolve the target window via _resolve_hwnd (respects --app flag).
        2. Try Win32 GetMenu/GetMenuItemInfoW — works for native Win32 menus
           without needing to visually expand them.
        3. If Win32 returns nothing (UWP, Electron, custom menus), fall back
           to UIA MenuBar traversal.

        Args:
            window_title: Optional window title or app name filter.

        Returns:
            List of top-level MenuItem objects with nested submenus.
        """
        handle = self._resolve_hwnd(app=window_title, window_title=window_title)

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
        from ctypes import wintypes

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
        from ctypes import wintypes
        from naturo.dialog import (
            DialogInfo, DialogButton, DialogType, classify_dialog,
            _ACCEPT_BUTTONS, _DISMISS_BUTTONS,
        )

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

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
            GWL_STYLE = -16
            WS_DLGFRAME = 0x00400000
            GWL_EXSTYLE = -20
            WS_EX_DLGMODALFRAME = 0x00000001

            style = user32.GetWindowLongW(win.handle, GWL_STYLE)
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
                has_edit = has_edit_ref = any(
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
