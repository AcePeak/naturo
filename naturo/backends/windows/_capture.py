"""Screen and window capture via GDI + Pillow conversion."""

from __future__ import annotations

import logging
from typing import Optional

from naturo.backends.base import (MonitorInfo, CaptureResult)

logger = logging.getLogger(__name__)


class CaptureMixin:
    """Screen and window capture via GDI + Pillow conversion."""

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
                    except Exception as exc:
                        logger.debug("GetDpiForMonitor failed: %s", exc)

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

        # DLL writes BMP to the system temp dir (always ASCII-safe on
        # Windows) then Pillow converts to the final output_path which may
        # contain Chinese/Unicode characters (#693, #728).
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
        except Exception as exc:
            logger.debug("Monitor info lookup failed for screen %s: %s", screen_index, exc)

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

        # DLL writes BMP to the system temp dir (always ASCII-safe on
        # Windows) then Pillow converts to the final output_path (#728).
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
        except Exception as exc:
            logger.debug("Window monitor info lookup failed: %s", exc)

        return CaptureResult(
            path=output_path, width=width, height=height, format=fmt,
            scale_factor=scale_factor, dpi=dpi,
        )

    def capture_app_windows(self, main_hwnd: int, output_path: str = "capture.png") -> CaptureResult:
        """Capture a window and any sibling popup/menu windows from the same process.

        When an application opens a popup menu, dropdown, or tooltip, Windows
        creates separate top-level windows owned by the same process.  This
        method captures the main window plus any visible sibling windows and
        composites them into a single image, preserving screen positions.

        If no sibling windows are found, falls back to ``capture_window``.

        Args:
            main_hwnd: Handle of the primary application window (from
                ``_resolve_hwnd``).
            output_path: File path for the output image.

        Returns:
            CaptureResult with the composited image path and dimensions.
        """
        import ctypes
        import ctypes.wintypes as wt
        import os
        import tempfile

        # Get PID of the main window
        target_pid = ctypes.c_ulong(0)
        ctypes.windll.user32.GetWindowThreadProcessId(
            main_hwnd, ctypes.byref(target_pid),
        )
        pid = target_pid.value
        if pid == 0:
            # Could not determine PID — fall back to single-window capture
            return self.capture_window(hwnd=main_hwnd, output_path=output_path)

        # Find all visible windows belonging to this PID (excluding the main one)
        sibling_hwnds: list[int] = []
        all_windows = self.list_windows()
        for w in all_windows:
            if w.pid == pid and w.handle != main_hwnd and w.is_visible and not w.is_minimized:
                sibling_hwnds.append(w.handle)

        if not sibling_hwnds:
            # No popup/menu windows — single capture is sufficient
            return self.capture_window(hwnd=main_hwnd, output_path=output_path)

        # Capture each window individually and composite them
        from PIL import Image

        core = self._ensure_core()
        all_hwnds = [main_hwnd] + sibling_hwnds

        # Gather window rects and captures
        captures: list[tuple[int, int, Image.Image]] = []  # (screen_x, screen_y, img)
        tmp_files: list[str] = []

        try:
            for h in all_hwnds:
                rect = wt.RECT()
                if not ctypes.windll.user32.GetWindowRect(h, ctypes.byref(rect)):
                    continue
                # Skip zero-size windows
                w = rect.right - rect.left
                hh = rect.bottom - rect.top
                if w <= 0 or hh <= 0:
                    continue

                fd, tmp_bmp = tempfile.mkstemp(suffix=".bmp")
                os.close(fd)
                tmp_files.append(tmp_bmp)

                try:
                    core.capture_window(h, tmp_bmp)
                    img = Image.open(tmp_bmp)
                    captures.append((rect.left, rect.top, img.copy()))
                    img.close()
                except Exception as exc:
                    logger.debug("Failed to capture window %s: %s", h, exc)
                    continue

            if not captures:
                # All captures failed — fall back to single-window capture
                return self.capture_window(hwnd=main_hwnd, output_path=output_path)

            # Compute bounding box of all captured windows
            min_x = min(c[0] for c in captures)
            min_y = min(c[1] for c in captures)
            max_x = max(c[0] + c[2].width for c in captures)
            max_y = max(c[1] + c[2].height for c in captures)

            canvas_w = max_x - min_x
            canvas_h = max_y - min_y

            # Composite: paint main window first, then overlays (popups on top)
            canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
            for screen_x, screen_y, img in captures:
                canvas.paste(img, (screen_x - min_x, screen_y - min_y))

            ext = output_path.rsplit(".", 1)[-1].lower() if "." in output_path else "png"
            fmt = {"jpg": "JPEG", "jpeg": "JPEG", "bmp": "BMP"}.get(ext, "PNG")
            canvas.save(output_path, fmt)
            width, height = canvas.size
        finally:
            for tmp in tmp_files:
                try:
                    os.remove(tmp)
                except OSError:
                    pass

        # DPI from the main window's monitor
        scale_factor = 1.0
        dpi = 96
        try:
            rect = wt.RECT()
            if ctypes.windll.user32.GetWindowRect(main_hwnd, ctypes.byref(rect)):
                monitor = self.find_monitor_for_point(rect.left, rect.top)
                if monitor:
                    scale_factor = monitor.scale_factor
                    dpi = monitor.dpi
        except Exception as exc:
            logger.debug("Window monitor info lookup failed: %s", exc)

        return CaptureResult(
            path=output_path, width=width, height=height, format=ext,
            scale_factor=scale_factor, dpi=dpi,
        )

