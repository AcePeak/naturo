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

