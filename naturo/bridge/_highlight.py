"""Win32 GDI and UIA-based element highlighting."""

from __future__ import annotations

import ctypes
import logging
import platform
from typing import Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# Depth-based colors (BGR for GDI)
_DEPTH_COLORS_BGR = [
    0x0000FF,  # Red
    0x00A000,  # Green
    0xFF5000,  # Blue
    0x00A0FF,  # Orange
    0xC800A0,  # Purple
    0xB4B400,  # Teal
    0x6400C8,  # Crimson
    0xFF5050,  # Indigo
]

# Type alias: (ref, label, x, y, w, h, depth_level)
DrawElement = Tuple[str, str, int, int, int, int, int]


def _set_dpi_awareness() -> Optional[int]:
    """Set per-monitor DPI awareness on the current thread.

    Returns the previous context handle so it can be restored, or None if
    the call was unavailable / failed.
    """
    if platform.system() != "Windows":
        return None
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        _set_thread = user32.SetThreadDpiAwarenessContext
        _set_thread.restype = ctypes.c_void_p
        _set_thread.argtypes = [ctypes.c_void_p]
        old_ctx = _set_thread(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        return old_ctx if old_ctx else None
    except (OSError, AttributeError):
        return None


def _restore_dpi_awareness(old_ctx: Optional[int]) -> None:
    """Restore a previously saved DPI awareness context."""
    if old_ctx is None:
        return
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(old_ctx))
    except (OSError, AttributeError):
        pass


def flatten_element_tree(
    tree,
    refs: Optional[list] = None,
    show_all: bool = False,
    role_filter: Optional[str] = None,
) -> list[DrawElement]:
    """Flatten a backend ElementInfo tree into a list suitable for GDI drawing.

    Walks the tree in DFS order (matching ``see`` ref assignment) and returns
    a flat list of ``(ref, label, x, y, w, h, depth_level)`` tuples.

    Args:
        tree: Root ElementInfo from ``backend.get_element_tree()``.
        refs: If set, only include these refs.
        show_all: If False, only include actionable elements.
        role_filter: If set, only include elements whose role contains this.

    Returns:
        List of DrawElement tuples ready for ``_draw_gdi_overlay()``.
    """
    from naturo.annotate import ACTIONABLE_ROLES

    elements: list[DrawElement] = []
    counter = [0]

    def _collect(el, depth_level: int = 0) -> None:
        counter[0] += 1
        ref = f"e{counter[0]}"
        if el.width > 0 and el.height > 0:
            if refs is None or ref in refs:
                # Actionable filter
                role = getattr(el, "role", "")
                if not show_all and refs is None:
                    is_actionable = getattr(el, "is_actionable", False)
                    if not is_actionable and role not in ACTIONABLE_ROLES:
                        for child in (el.children or []):
                            _collect(child, depth_level + 1)
                        return
                # Role filter
                if role_filter and role_filter.lower() not in role.lower():
                    for child in (el.children or []):
                        _collect(child, depth_level + 1)
                    return
                label = getattr(el, "name", "") or role
                if len(label) > 20:
                    label = label[:18] + ".."
                x = getattr(el, "x", 0)
                y = getattr(el, "y", 0)
                w = getattr(el, "width", 0)
                h = getattr(el, "height", 0)
                elements.append((ref, label, x, y, w, h, depth_level))
        for child in (el.children or []):
            _collect(child, depth_level + 1)

    _collect(tree)
    return elements


def _draw_gdi_overlay(
    elements: Sequence[DrawElement],
    duration: float = 5.0,
) -> None:
    """Draw colored borders and labels on screen using Win32 GDI.

    Sets per-monitor DPI awareness before drawing so that coordinates
    from ``backend.get_element_tree()`` (which are physical pixels)
    map correctly to the screen DC.

    Args:
        elements: Flat list of (ref, label, x, y, w, h, depth_level).
        duration: How long to hold the overlay (seconds).
    """
    import time

    if platform.system() != "Windows" or not elements:
        return

    old_ctx = _set_dpi_awareness()
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        gdi32 = ctypes.windll.gdi32  # type: ignore[attr-defined]

        # ── Compute label positions (collision avoidance) ────────────
        label_rects: list[tuple[int, int, int, int]] = []
        label_positions: list[tuple[int, int]] = []

        for ref, label, ex, ey, ew, eh, depth_level in elements:
            label_text = f" {ref}: {label} "
            approx_w = len(label_text) * 8
            approx_h = 16

            candidates = [
                (ex, max(0, ey - approx_h)),
                (ex + ew - approx_w, max(0, ey - approx_h)),
                (ex, ey + eh),
                (ex + ew - approx_w, ey + eh),
            ]

            best_pos = candidates[0]
            best_overlap = len(label_rects) + 1

            for cx, cy in candidates:
                cx = max(0, cx)
                cy = max(0, cy)
                overlap_count = 0
                for px1, py1, px2, py2 in label_rects:
                    if cx < px2 and cx + approx_w > px1 and cy < py2 and cy + approx_h > py1:
                        overlap_count += 1
                if overlap_count < best_overlap:
                    best_overlap = overlap_count
                    best_pos = (cx, cy)
                    if overlap_count == 0:
                        break

            label_positions.append(best_pos)
            label_rects.append((best_pos[0], best_pos[1],
                                best_pos[0] + approx_w, best_pos[1] + approx_h))

        # ── GDI drawing ─────────────────────────────────────────────
        hdc = user32.GetDC(None)
        font = gdi32.CreateFontW(
            14, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0, "Consolas"
        )

        try:
            for i, (ref, label, ex, ey, ew, eh, depth_level) in enumerate(elements):
                color = _DEPTH_COLORS_BGR[depth_level % len(_DEPTH_COLORS_BGR)]
                pen = gdi32.CreatePen(0, 2, color)
                old_pen = gdi32.SelectObject(hdc, pen)
                old_brush = gdi32.SelectObject(hdc, gdi32.GetStockObject(5))

                gdi32.Rectangle(hdc, ex, ey, ex + ew, ey + eh)

                gdi32.SelectObject(hdc, old_brush)
                label_text = f" {ref}: {label} "

                gdi32.SetBkColor(hdc, color)
                gdi32.SetTextColor(hdc, 0xFFFFFF)
                old_font = gdi32.SelectObject(hdc, font)

                lx, ly = label_positions[i]
                text_buf = ctypes.create_unicode_buffer(label_text)
                gdi32.TextOutW(hdc, lx, ly, text_buf, len(label_text))

                gdi32.SelectObject(hdc, old_font)
                gdi32.SelectObject(hdc, old_pen)
                gdi32.DeleteObject(pen)

            time.sleep(duration)

        finally:
            gdi32.DeleteObject(font)
            user32.ReleaseDC(None, hdc)
            user32.InvalidateRect(None, None, True)
    finally:
        _restore_dpi_awareness(old_ctx)


def highlight_elements(
    hwnd: int,
    depth: int = 10,
    duration: float = 5.0,
    refs: Optional[list] = None,
    show_all: bool = False,
    element_tree=None,
) -> None:
    """Draw colored borders and labels on Win32 child windows.

    When ``element_tree`` is provided (from ``backend.get_element_tree()``),
    uses it directly — coordinates are already DPI-correct.  Otherwise falls
    back to local Win32 HWND enumeration (legacy path).

    Args:
        hwnd: Parent window handle.
        depth: Max depth for enumeration.
        duration: How long to show highlights (seconds).
        refs: Optional list of specific refs to highlight.
        show_all: If False, only highlight actionable elements.
        element_tree: Pre-fetched element tree from backend. When supplied,
            the function skips its own enumeration and uses these elements.
    """
    if platform.system() != "Windows":
        return

    if element_tree is not None:
        elements = flatten_element_tree(
            element_tree, refs=refs, show_all=show_all,
        )
        _draw_gdi_overlay(elements, duration=duration)
        return

    # ── Legacy fallback: self-enumerate via Win32 HWND ──────────────
    # Kept for backward compatibility when no backend is available.
    from ctypes import wintypes

    old_ctx = _set_dpi_awareness()
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        _ACTIONABLE_WIN32_CLASSES = {
            "button", "edit", "combobox", "listbox", "scrollbar",
            "syslistview32", "systreeview32", "systabcontrol32",
            "msctls_trackbar32", "msctls_updown32", "toolbarwindow32",
            "sysdatetimepick32", "sysmonthcal32", "richedit20w",
            "richedit50w", "comboboxex32",
        }

        def _get_direct_children(parent):
            children = []
            child = user32.FindWindowExW(parent, None, None, None)
            while child:
                children.append(child)
                child = user32.FindWindowExW(parent, child, None, None)
            return children

        raw_elements = []  # (ref, label, x, y, w, h, depth_level)
        counter = [1]

        def _collect(h, current_depth):
            if current_depth > depth:
                return
            for child_hwnd in _get_direct_children(h):
                ref = f"e{counter[0]}"
                counter[0] += 1

                title_buf = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(child_hwnd, title_buf, 256)
                title = title_buf.value or ""

                cls_buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(child_hwnd, cls_buf, 256)
                cls_name = cls_buf.value or ""

                rect = wintypes.RECT()
                user32.GetWindowRect(child_hwnd, ctypes.byref(rect))

                w = rect.right - rect.left
                h_size = rect.bottom - rect.top
                if w <= 0 or h_size <= 0:
                    continue
                if rect.left < -10000 or rect.top < -10000:
                    continue

                if refs is None or ref in refs:
                    if not show_all and refs is None:
                        base_cls = cls_name.split(".")[-1].lower() if "." in cls_name else cls_name.lower()
                        if base_cls not in _ACTIONABLE_WIN32_CLASSES:
                            _collect(child_hwnd, current_depth + 1)
                            continue

                    short_cls = cls_name.split(".")[-1] if "." in cls_name else cls_name
                    label = title if title else short_cls
                    if len(label) > 20:
                        label = label[:18] + ".."
                    raw_elements.append((ref, label, rect.left, rect.top, w, h_size, current_depth))

                _collect(child_hwnd, current_depth + 1)

        _collect(hwnd, 0)

        if not raw_elements:
            return

        _draw_gdi_overlay(raw_elements, duration=duration)
    finally:
        _restore_dpi_awareness(old_ctx)


def highlight_elements_uia(
    backend,
    app: Optional[str] = None,
    hwnd: int = 0,
    depth: int = 30,
    duration: float = 5.0,
    refs: Optional[list] = None,
    show_all: bool = False,
    annotate_path: Optional[str] = None,
    role_filter: Optional[str] = None,
    element_tree=None,
) -> Optional[str]:
    """Highlight UI elements using the UIA element tree.

    When ``element_tree`` is provided (from ``backend.get_element_tree()``),
    uses it directly for GDI overlay — coordinates are already DPI-correct.
    Otherwise tries the most recent snapshot, then captures a fresh tree.

    If ``annotate_path`` is set, renders the highlight onto a screenshot image
    using Pillow instead of GDI drawing, and returns the output path.

    Args:
        backend: The platform backend instance.
        app: Application name filter.
        hwnd: Parent window handle.
        depth: Max depth for element tree.
        duration: How long to show highlights (seconds).
        refs: Optional list of specific refs to highlight.
        show_all: If False, only highlight actionable elements.
        annotate_path: If set, save a PIL-annotated screenshot to this path.
        role_filter: If set, only highlight elements whose role contains this.
        element_tree: Pre-fetched element tree from backend. When supplied,
            skips snapshot lookup / fresh capture for GDI overlay.

    Returns:
        The annotated screenshot path if ``annotate_path`` is set, else None.
    """
    from naturo.snapshot import get_snapshot_manager
    mgr = get_snapshot_manager()

    # ── Annotate mode (PIL, cross-platform) ──────────────────────────
    if annotate_path is not None:
        snap = None
        try:
            snaps = mgr.list_snapshots()
            if snaps:
                snap = mgr.get_snapshot(snaps[-1].id)
        except Exception as exc:
            logger.debug("Snapshot retrieval for highlight failed: %s", exc)

        if snap and snap.ui_map and snap.screenshot_path:
            from naturo.annotate import highlight_annotate
            return highlight_annotate(
                screenshot_path=snap.screenshot_path,
                ui_map=snap.ui_map,
                output_path=annotate_path,
                refs=refs,
                actionable_only=not show_all,
                role_filter=role_filter,
            )
        return None

    # ── GDI live overlay (Windows only) ──────────────────────────────
    if platform.system() != "Windows":
        return None

    # If a pre-fetched element tree is provided, use it directly
    if element_tree is not None:
        elements = flatten_element_tree(
            element_tree, refs=refs, show_all=show_all,
            role_filter=role_filter,
        )
        _draw_gdi_overlay(elements, duration=duration)
        return None

    # Try to get elements from most recent snapshot first
    from naturo.annotate import ACTIONABLE_ROLES

    snap_elements: list[DrawElement] = []
    _found_snapshot = False
    try:
        snaps = mgr.list_snapshots()
        if snaps:
            latest = snaps[-1]
            snap = mgr.get_snapshot(latest.id)
            if snap.ui_map:
                _found_snapshot = True
                for ref_key, el in snap.ui_map.items():
                    if refs is not None and ref_key not in refs:
                        continue
                    ex, ey, ew, eh = el.frame
                    if ew <= 0 or eh <= 0:
                        continue
                    if not show_all and refs is None:
                        if not el.is_actionable and el.role not in ACTIONABLE_ROLES:
                            continue
                    if role_filter and role_filter.lower() not in el.role.lower():
                        continue
                    label = el.title or el.role
                    if len(label) > 20:
                        label = label[:18] + ".."
                    depth_level = 0
                    cur = el
                    seen: set = set()
                    while cur and cur.parent_id and cur.parent_id not in seen:
                        seen.add(cur.parent_id)
                        depth_level += 1
                        cur = snap.ui_map.get(cur.parent_id)  # type: ignore[assignment]
                    snap_elements.append((ref_key, label, ex, ey, ew, eh, depth_level))
    except Exception as exc:
        logger.debug("Snapshot element collection failed: %s", exc)

    # If no recent snapshot, capture a fresh element tree via backend
    if not _found_snapshot:
        try:
            tree = backend.get_element_tree(
                app=app, hwnd=hwnd, depth=depth, backend="uia",
            )
            if tree:
                snap_elements = flatten_element_tree(
                    tree, refs=refs, show_all=show_all,
                    role_filter=role_filter,
                )
        except Exception as exc:
            logger.debug("UIA element tree collection failed: %s", exc)

    if not snap_elements:
        return None

    _draw_gdi_overlay(snap_elements, duration=duration)
    return None
