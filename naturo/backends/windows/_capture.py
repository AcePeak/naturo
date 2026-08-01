"""Screen and window capture via GDI + Pillow conversion."""

from __future__ import annotations

import logging
from typing import Optional

from naturo.backends.base import (MonitorInfo, CaptureResult)

logger = logging.getLogger(__name__)


class CaptureMixin:
    """Screen and window capture via GDI + Pillow conversion."""

    # Window classes that are always transient popups/menus and must be
    # composited on top of everything else (#843).  Matched case-insensitively.
    # ``#32768`` is the standard Win32 menu class; ``tooltips_class32`` is the
    # common tooltip class; the remainder are popup/dropdown classes used by
    # the shell, list-view dropdowns, and autocomplete panels.
    _POPUP_WINDOW_CLASSES = frozenset(
        c.lower() for c in (
            "#32768",              # standard menus (File menu, context menu)
            "tooltips_class32",    # tooltips
            "ComboLBox",           # combo-box dropdown list
            "DropDown",            # generic dropdown
            "Auto-Suggest Dropdown",  # edit-control autocomplete
            "ListBox",             # transient list popups
        )
    )

    # === Capture (Phase 1) ===

    @staticmethod
    def _order_hwnds_for_composite(
        hwnds: list[int],
        class_of,
        zorder_rank_of,
    ) -> list[int]:
        """Order *hwnds* bottom→top for compositing (#843).

        The composite must paste windows from the bottom of the Z-order to the
        top, so that the top-most windows — including popup menus and tooltips
        that overlap full-size sibling windows — are painted last and survive
        in the final image.

        Ordering rules (stable):

        1. Non-popup windows come before popup/menu windows, so popups always
           land on top regardless of their reported Z-order (a freshly opened
           menu is normally top-most, but this guards against stale/odd
           Z-order reporting).
        2. Within each group, windows are sorted by Z-order rank where a
           *higher* rank means closer to the top of the Z-order, so the
           bottom-most window is pasted first and the top-most window last.
        3. Ties (equal rank) preserve the input order for determinism.

        Args:
            hwnds: Window handles to order.
            class_of: Callable ``hwnd -> str`` returning the window class name.
            zorder_rank_of: Callable ``hwnd -> int`` returning a Z-order rank
                where a larger value is closer to the top of the Z-order.

        Returns:
            The handles ordered so the first element should be pasted first
            (bottom) and the last element pasted last (top).
        """
        popup_classes = CaptureMixin._POPUP_WINDOW_CLASSES

        def _is_popup(h: int) -> bool:
            try:
                name = (class_of(h) or "").strip().lower()
            except Exception:
                return False
            return name in popup_classes

        decorated = []
        for idx, h in enumerate(hwnds):
            try:
                rank = zorder_rank_of(h)
            except Exception:
                rank = 0
            decorated.append((1 if _is_popup(h) else 0, rank, idx, h))

        # Sort by (popup-flag asc, z-order rank asc, original index asc) so the
        # last element is the top-most popup (or top-most non-popup if none).
        decorated.sort(key=lambda t: (t[0], t[1], t[2]))
        return [h for _, _, _, h in decorated]

    @staticmethod
    def _window_class_name(hwnd: int) -> str:
        """Return the Win32 window class name for *hwnd* (empty on failure)."""
        import ctypes

        buf = ctypes.create_unicode_buffer(256)
        n = ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
        return buf.value if n else ""

    @staticmethod
    def _window_zorder_rank(hwnd: int) -> int:
        """Return a Z-order rank for *hwnd*; larger means closer to the top.

        Walks the Z-order downward from *hwnd* via ``GetWindow(GW_HWNDNEXT)``
        and counts the windows below it.  More windows below ⇒ closer to the
        top, so the returned rank sorts bottom→top when used as a sort key.
        """
        import ctypes

        GW_HWNDNEXT = 2  # next window toward the bottom of the Z-order
        rank = 0
        cur = hwnd
        # Bound the walk to avoid pathological loops on a corrupt Z-order list.
        for _ in range(10000):
            nxt = ctypes.windll.user32.GetWindow(cur, GW_HWNDNEXT)
            if not nxt:
                break
            rank += 1
            cur = nxt
        return rank

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

    @staticmethod
    def _image_is_blank(path: str, tolerance: int = 6) -> bool:
        """True if the image is a near-uniform single colour (a blank frame).

        A GPU-composited window that PrintWindow failed to capture comes back as
        one flat colour (usually white). Downsample and check that every channel's
        spread is within *tolerance*, so a real (varied) screenshot is never
        mistaken for blank.
        """
        try:
            from PIL import Image

            img = Image.open(path).convert("RGB")
            w, h = img.size
            if w == 0 or h == 0:
                return True
            small = img.resize((min(48, w), min(48, h)))
            extrema = small.getextrema()  # ((rmin,rmax),(gmin,gmax),(bmin,bmax))
            return all((mx - mn) <= tolerance for mn, mx in extrema)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("blank-image check failed for %s: %s", path, exc)
            return False

    def _window_is_unoccluded_onscreen(self, hwnd: int) -> bool:
        """True if *hwnd* is visible, on a monitor, and unoccluded — i.e. a plain
        screen BitBlt cropped to its rect would read the window's own pixels.

        Deterministic (documented Win32 APIs only): not minimized, visible, its
        centre lies on a monitor, and every point of an inset grid over its rect
        resolves (via ``WindowFromPoint`` → ``GA_ROOT``) back to this top-level
        window — so nothing is painted on top of it. Conservative: any ambiguity
        (a probe hitting another window, a click-through/layered pass-through,
        off-screen) returns ``False`` so capture falls back to PrintWindow.
        """
        try:
            import ctypes
            import ctypes.wintypes as wt

            user32 = ctypes.windll.user32
            if user32.IsIconic(hwnd) or not user32.IsWindowVisible(hwnd):
                return False
            rect = wt.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return False
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w <= 0 or h <= 0:
                return False
            cx = (rect.left + rect.right) // 2
            cy = (rect.top + rect.bottom) // 2
            if self.find_monitor_for_point(cx, cy) is None:
                return False

            class _POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            # Locally-prototyped so the HWND return isn't truncated to 32-bit on
            # x64 and POINT is passed by value — without mutating the shared
            # user32 function attributes (other callers rely on the defaults).
            _window_from_point = ctypes.WINFUNCTYPE(
                ctypes.c_void_p, _POINT)(("WindowFromPoint", user32))
            _get_ancestor = ctypes.WINFUNCTYPE(
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint)(
                    ("GetAncestor", user32))

            def _norm(handle_val: int) -> int:
                # Window handles fit in 32 bits; normalize so a sign-extended
                # value and an unsigned one compare equal.
                return (handle_val or 0) & 0xFFFFFFFF

            target = _norm(hwnd)
            _GA_ROOT = 2
            inset_x = max(2, w // 10)
            inset_y = max(2, h // 10)
            xs = (rect.left + inset_x, cx, rect.right - inset_x)
            ys = (rect.top + inset_y, cy, rect.bottom - inset_y)
            for py in ys:
                for px in xs:
                    top = _window_from_point(_POINT(px, py))
                    if not top:
                        return False
                    if _norm(_get_ancestor(top, _GA_ROOT)) != target:
                        return False
            return True
        except Exception as exc:  # pragma: no cover - platform guard
            logger.debug("occlusion check failed for %s: %s", hwnd, exc)
            return False

    @staticmethod
    def _force_foreground(hwnd: int) -> None:
        """Raise *hwnd* above other windows and give it the foreground.

        A background process can't normally steal the foreground (Win32 foreground
        lock), so this attaches to the current foreground thread's input queue
        (``AttachThreadInput``) for the duration — the reliable way to bring an
        occluded window to the top so a plain screen BitBlt can capture it
        non-destructively (instead of the destructive PrintWindow). Best-effort:
        any failure leaves the caller to fall back to PrintWindow.
        """
        try:
            import ctypes

            user32 = ctypes.windll.user32
            fg = user32.GetForegroundWindow()
            if fg == hwnd:
                return
            t_target = user32.GetWindowThreadProcessId(hwnd, None)
            t_fg = user32.GetWindowThreadProcessId(fg, None) if fg else 0
            attached = False
            if t_fg and t_target and t_fg != t_target:
                attached = bool(user32.AttachThreadInput(t_target, t_fg, True))
            try:
                user32.BringWindowToTop(hwnd)
                user32.ShowWindow(hwnd, 5)  # SW_SHOW (no size/state change)
                user32.SetForegroundWindow(hwnd)
            finally:
                if attached:
                    user32.AttachThreadInput(t_target, t_fg, False)
        except Exception as exc:  # pragma: no cover - platform guard
            logger.debug("force-foreground failed for %s: %s", hwnd, exc)

    @staticmethod
    def _window_is_minimized(hwnd: int) -> bool:
        try:
            import ctypes

            return bool(ctypes.windll.user32.IsIconic(hwnd))
        except Exception:  # pragma: no cover - platform guard
            return False

    @staticmethod
    def _heal_window_repaint(hwnd: int) -> None:
        """Force a GPU-composited window blanked by PrintWindow to re-present.

        A minimize→restore cycle makes the compositor (Chromium/DirectComposition)
        push a fresh frame, undoing the blank that PrintWindow left on screen.
        """
        try:
            import ctypes
            import time

            user32 = ctypes.windll.user32
            _SW_MINIMIZE, _SW_RESTORE = 6, 9
            user32.ShowWindow(hwnd, _SW_MINIMIZE)
            time.sleep(0.05)
            user32.ShowWindow(hwnd, _SW_RESTORE)
            time.sleep(0.1)
        except Exception as exc:  # pragma: no cover - platform guard
            logger.debug("window repaint heal failed for %s: %s", hwnd, exc)

    def _capture_window_via_screen(self, hwnd: int,
                                   output_path: str) -> tuple[int, int, str]:
        """Non-destructive window capture: BitBlt the screen, crop to the window.

        Reads the real composited pixels of a visible window (works for GPU/
        DirectComposition windows that PrintWindow blanks). Only sees the on-screen
        (unoccluded) content, which is the honest "what's visible" screenshot.
        """
        import ctypes
        import ctypes.wintypes as wt
        import os
        import tempfile

        from PIL import Image

        rect = wt.RECT()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError("GetWindowRect failed")

        monitor = self.find_monitor_for_point(rect.left, rect.top)
        mon_x = monitor.x if monitor else 0
        mon_y = monitor.y if monitor else 0
        mon_index = monitor.index if monitor else 0

        fd, tmp_bmp = tempfile.mkstemp(suffix=".bmp")
        os.close(fd)
        try:
            self.capture_screen(screen_index=mon_index, output_path=tmp_bmp)
            img = Image.open(tmp_bmp).convert("RGB")
            left = max(0, rect.left - mon_x)
            top = max(0, rect.top - mon_y)
            right = min(img.width, rect.right - mon_x)
            bottom = min(img.height, rect.bottom - mon_y)
            if right <= left or bottom <= top:
                raise RuntimeError("empty crop rectangle")
            crop = img.crop((left, top, right, bottom))
            ext = output_path.rsplit(".", 1)[-1].lower() if "." in output_path else "png"
            fmt = {"jpg": "JPEG", "jpeg": "JPEG", "bmp": "BMP"}.get(ext, "PNG")
            crop.save(output_path, fmt)
            return crop.width, crop.height, ext
        finally:
            if os.path.exists(tmp_bmp):
                try:
                    os.remove(tmp_bmp)
                except OSError:
                    pass

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
                       output_path: str = "capture.png",
                       raise_if_occluded: bool = True) -> CaptureResult:
        """Capture a screenshot of a specific window.

        Prefers a non-destructive screen BitBlt (which reads real composited
        pixels and never blanks GPU/self-drawn windows) whenever the window is
        visible. When the window is occluded and ``raise_if_occluded`` is set, it
        is first brought to the foreground so the BitBlt can see it; only a window
        that still cannot be made visible (or a minimized one) falls back to the
        legacy PrintWindow path.

        Args:
            window_title: Window title to search for (not yet implemented — use hwnd).
            hwnd: Window handle. 0 or None for the foreground window.
            output_path: File path for the output image.
            raise_if_occluded: When True (default), bring an occluded target to the
                foreground so it can be captured non-destructively via BitBlt
                instead of the destructive PrintWindow. Pass False for quiet
                background capture that must not change window Z-order/focus (e.g.
                multi-window compositing).

        Returns:
            CaptureResult with the output path and dimensions.
        """
        import tempfile
        import os
        core = self._ensure_core()
        handle = hwnd if hwnd else 0

        # Resolve the concrete window handle (foreground if unspecified) so the
        # visibility check and monitor math below have a real target.
        check_hwnd = handle
        if not check_hwnd:
            try:
                import ctypes
                check_hwnd = ctypes.windll.user32.GetForegroundWindow()
            except Exception:
                check_hwnd = 0

        width = height = 0
        fmt = "png"
        captured = False

        # Visibility-first (avoids the destructive PrintWindow path proactively).
        # PrintWindow (WM_PRINT) is destructive on GPU-composited windows
        # (Chromium/Electron, custom DirectComposition skins): it blanks both the
        # returned bitmap AND the live on-screen window until it repaints. When the
        # target is fully visible and unoccluded, a plain screen BitBlt cropped to
        # the window reads the real composited pixels non-destructively and works
        # for EVERY window type — so prefer it and never issue PrintWindow. There is
        # no reliable a-priori "is this GPU-composited?" test (custom skins evade
        # class-name/module/DWM heuristics), but "is it visible and unoccluded?" is
        # deterministic — and that is exactly the condition under which BitBlt is
        # both safe and sufficient. PrintWindow is kept below for the cases only it
        # can serve: occluded, background-without-raising, minimized, or off-screen.
        if check_hwnd and self._window_is_unoccluded_onscreen(check_hwnd):
            try:
                width, height, fmt = self._capture_window_via_screen(
                    check_hwnd, output_path)
                captured = True
            except Exception as exc:
                logger.debug(
                    "Visibility-first screen capture failed, using PrintWindow: %s",
                    exc)

        # Occluded target: rather than PrintWindow it (which blanks self-drawn/GPU
        # windows), raise it to the foreground so a non-destructive BitBlt can see
        # it. Bringing a background window to the front reliably requires defeating
        # the Win32 foreground lock (AttachThreadInput). Costs a focus change —
        # acceptable when capturing a specific window, and far better than leaving
        # it blanked. Skipped when raise_if_occluded=False (quiet compositing) or
        # for minimized windows (nothing on screen to BitBlt).
        if (not captured and raise_if_occluded and check_hwnd
                and not self._window_is_minimized(check_hwnd)):
            import time as _time
            self._force_foreground(check_hwnd)
            _time.sleep(0.2)
            if self._window_is_unoccluded_onscreen(check_hwnd):
                try:
                    width, height, fmt = self._capture_window_via_screen(
                        check_hwnd, output_path)
                    captured = True
                except Exception as exc:
                    logger.debug(
                        "Post-foreground screen capture failed, using PrintWindow: %s",
                        exc)

        if not captured:
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

            # Last-resort safety net: if PrintWindow still returned a blank frame
            # (a GPU window that was occluded/background, so the visibility-first
            # path above was skipped), heal it (minimize/restore forces a
            # re-present) and re-capture from screen. Only triggers on an actual
            # blank frame, so normal captures are unaffected.
            if check_hwnd and self._image_is_blank(output_path) \
                    and not self._window_is_minimized(check_hwnd):
                logger.info(
                    "capture_window: PrintWindow returned a blank frame for hwnd %s "
                    "(GPU-composited window); healing and re-capturing from screen.",
                    check_hwnd,
                )
                self._heal_window_repaint(check_hwnd)
                try:
                    width, height, fmt = self._capture_window_via_screen(
                        check_hwnd, output_path)
                except Exception as exc:
                    logger.debug("Screen-region capture fallback failed: %s", exc)

                # Ultimate fallback: if the screen-region heal ALSO came back blank,
                # the content is GPU/DirectComposition-composited in a way GDI cannot
                # read at all (a hardware overlay / DXGI swap-chain absent from the
                # desktop GDI surface — some Chromium/CEF message panes, custom skins).
                # WGC (Windows.Graphics.Capture) captures through the DWM's real
                # composition and DOES see that content. Only runs when every GDI path
                # already blanked, so normal captures never pay for it.
                if self._image_is_blank(output_path):
                    logger.info(
                        "capture_window: GDI paths all blank for hwnd %s; falling back "
                        "to WGC (Windows.Graphics.Capture).", check_hwnd)
                    fd_wgc, tmp_wgc = tempfile.mkstemp(suffix=".bmp")
                    os.close(fd_wgc)
                    try:
                        core.capture_window_wgc(handle, tmp_wgc)
                        width, height, fmt = self._convert_bmp(tmp_wgc, output_path)
                    except Exception as exc:
                        logger.debug("WGC capture fallback failed: %s", exc)
                        try:
                            os.remove(tmp_wgc)
                        except OSError:
                            pass

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

        # (#843) Order windows bottom→top of the actual Z-order so the top-most
        # windows — including popup menus that overlap full-size siblings — are
        # pasted last and survive in the composite.  The bare ``list_windows()``
        # order pasted the main window first then siblings, so a full-size
        # sibling pasted after a small popup would overpaint it.
        all_hwnds = self._order_hwnds_for_composite(
            [main_hwnd] + sibling_hwnds,
            class_of=self._window_class_name,
            zorder_rank_of=self._window_zorder_rank,
        )

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

            # Composite: ``captures`` is already ordered bottom→top of the
            # Z-order (popups last), so pasting in sequence leaves popups/menus
            # painted on top of any overlapping full-size sibling windows.
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

