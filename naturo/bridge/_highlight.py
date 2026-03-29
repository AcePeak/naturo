"""Win32 GDI and UIA-based element highlighting."""

from __future__ import annotations

import ctypes
import logging
import platform
from typing import Optional

logger = logging.getLogger(__name__)


def highlight_elements(hwnd: int, depth: int = 10, duration: float = 5.0,
                       refs: Optional[list] = None,
                       show_all: bool = False) -> None:
    """Draw colored borders and labels on Win32 child windows for visual identification.

    Uses Win32 GDI to draw directly on screen. All matching elements are drawn
    simultaneously and held for ``duration`` seconds (no flashing).

    Depth-based coloring groups elements at the same tree level by colour.
    Label collision avoidance shifts labels to avoid overlap.

    By default only highlights interactive control classes (Button, Edit,
    ComboBox, etc.). Pass ``show_all=True`` to include all elements.

    Args:
        hwnd: Parent window handle.
        depth: Max depth for enumeration.
        duration: How long to show highlights (seconds).
        refs: Optional list of specific refs to highlight (e.g. ['e5', 'e10']).
              If None, highlights all matching elements.
        show_all: If False (default), only highlight actionable Win32 classes.
    """
    from ctypes import wintypes
    import time

    if platform.system() != "Windows":
        return

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    gdi32 = ctypes.windll.gdi32  # type: ignore[attr-defined]

    # Win32 class names considered actionable (interactive controls)
    _ACTIONABLE_WIN32_CLASSES = {
        "button", "edit", "combobox", "listbox", "scrollbar",
        "syslistview32", "systreeview32", "systabcontrol32",
        "msctls_trackbar32", "msctls_updown32", "toolbarwindow32",
        "sysdatetimepick32", "sysmonthcal32", "richedit20w",
        "richedit50w", "comboboxex32",
    }

    # Collect all child windows with their info
    def _get_direct_children(parent):
        children = []
        child = user32.FindWindowExW(parent, None, None, None)
        while child:
            children.append(child)
            child = user32.FindWindowExW(parent, child, None, None)
        return children

    elements = []  # list of (ref, hwnd, title, class_name, rect, depth_level)
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

            # Skip invisible/zero-size windows
            w = rect.right - rect.left
            h_size = rect.bottom - rect.top
            if w <= 0 or h_size <= 0:
                continue
            # Skip off-screen windows
            if rect.left < -10000 or rect.top < -10000:
                continue

            if refs is None or ref in refs:
                # Actionable filter: skip non-interactive classes unless show_all
                if not show_all and refs is None:
                    base_cls = cls_name.split(".")[-1].lower() if "." in cls_name else cls_name.lower()
                    if base_cls not in _ACTIONABLE_WIN32_CLASSES:
                        _collect(child_hwnd, current_depth + 1)
                        continue

                short_cls = cls_name.split(".")[-1] if "." in cls_name else cls_name
                label = title if title else short_cls
                if len(label) > 20:
                    label = label[:18] + ".."
                elements.append((ref, child_hwnd, label, cls_name, rect, current_depth))

            _collect(child_hwnd, current_depth + 1)

    _collect(hwnd, 0)

    if not elements:
        return

    # Depth-based colors (BGR for GDI)
    DEPTH_COLORS_BGR = [
        0x0000FF,  # Red
        0x00A000,  # Green
        0xFF5000,  # Blue
        0x00A0FF,  # Orange
        0xC800A0,  # Purple
        0xB4B400,  # Teal
        0x6400C8,  # Crimson
        0xFF5050,  # Indigo
    ]

    # Compute label positions to avoid overlap
    label_rects: list[tuple[int, int, int, int]] = []  # placed label bounds
    label_positions: list[tuple[int, int]] = []  # (lx, ly) per element

    for i, (ref, child_hwnd, label, cls_name, rect, depth_level) in enumerate(elements):
        label_text = f" {ref}: {label} "
        # Approximate text width: ~8px per character at 14pt Consolas
        approx_w = len(label_text) * 8
        approx_h = 16

        rl, rt, rr, rb = rect.left, rect.top, rect.right, rect.bottom
        candidates = [
            (rl, max(0, rt - approx_h)),         # above-left
            (rr - approx_w, max(0, rt - approx_h)),  # above-right
            (rl, rb),                              # below-left
            (rr - approx_w, rb),                   # below-right
        ]

        best_pos = candidates[0]
        best_overlap = len(label_rects) + 1  # guaranteed > any real count

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

    # Get screen DC
    hdc = user32.GetDC(None)

    # Create font for labels
    font = gdi32.CreateFontW(
        14, 0, 0, 0, 700,  # height, width, escapement, orientation, weight (bold)
        0, 0, 0,  # italic, underline, strikeout
        0, 0, 0, 0, 0,  # charset, precision, clip, quality, pitch
        "Consolas"
    )

    try:
        # Draw all borders and labels simultaneously (single pass)
        for i, (ref, child_hwnd, label, cls_name, rect, depth_level) in enumerate(elements):
            color = DEPTH_COLORS_BGR[depth_level % len(DEPTH_COLORS_BGR)]
            pen = gdi32.CreatePen(0, 2, color)  # PS_SOLID, width=2
            old_pen = gdi32.SelectObject(hdc, pen)
            old_brush = gdi32.SelectObject(hdc, gdi32.GetStockObject(5))  # NULL_BRUSH

            # Draw rectangle
            gdi32.Rectangle(hdc, rect.left, rect.top, rect.right, rect.bottom)

            # Draw label
            gdi32.SelectObject(hdc, old_brush)
            label_text = f" {ref}: {label} "

            gdi32.SetBkColor(hdc, color)
            gdi32.SetTextColor(hdc, 0xFFFFFF)  # White text
            old_font = gdi32.SelectObject(hdc, font)

            lx, ly = label_positions[i]
            text_buf = ctypes.create_unicode_buffer(label_text)
            gdi32.TextOutW(hdc, lx, ly, text_buf, len(label_text))

            gdi32.SelectObject(hdc, old_font)
            gdi32.SelectObject(hdc, old_pen)
            gdi32.DeleteObject(pen)

        # Hold the display for the requested duration
        time.sleep(duration)

    finally:
        gdi32.DeleteObject(font)
        user32.ReleaseDC(None, hdc)
        # Final cleanup: redraw everything
        user32.InvalidateRect(None, None, True)


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
) -> Optional[str]:
    """Highlight UI elements using the UIA element tree from snapshot/see.

    Refs match those assigned by ``naturo see`` (sequential DFS e1, e2, ...).
    Falls back to capturing a fresh element tree if no recent snapshot exists.

    All matching elements are drawn simultaneously and held for ``duration``
    seconds (no flashing). Depth-based coloring and label collision avoidance
    produce a clean, readable overlay.

    By default only highlights actionable elements. Pass ``show_all=True``
    to include all visible elements.

    If ``annotate_path`` is set, renders the highlight onto a screenshot image
    using Pillow instead of GDI drawing, and returns the output path.

    Args:
        backend: The platform backend instance.
        app: Application name filter.
        hwnd: Parent window handle.
        depth: Max depth for element tree.
        duration: How long to show highlights (seconds).
        refs: Optional list of specific refs to highlight (e.g. ['e5', 'e10']).
              If None, highlights all matching elements.
        show_all: If False (default), only highlight actionable elements.
        annotate_path: If set, save a PIL-annotated screenshot to this path
            instead of using GDI live overlay. Returns the output path.
        role_filter: If set, only highlight elements whose role contains this string.

    Returns:
        The annotated screenshot path if ``annotate_path`` is set, else None.
    """
    import time

    from naturo.snapshot import get_snapshot_manager
    mgr = get_snapshot_manager()

    # ── Annotate mode (PIL, cross-platform) ──────────────────────────────────
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

    # ── GDI live overlay (Windows only) ──────────────────────────────────────
    if platform.system() != "Windows":
        return None

    from naturo.annotate import ACTIONABLE_ROLES

    # Try to get elements from most recent snapshot first
    elements = []  # list of (ref, name, role, x, y, w, h, depth_level)

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
                    # Actionable filter
                    if not show_all and refs is None:
                        if not el.is_actionable and el.role not in ACTIONABLE_ROLES:
                            continue
                    # Role filter
                    if role_filter and role_filter.lower() not in el.role.lower():
                        continue
                    label = el.title or el.role
                    if len(label) > 20:
                        label = label[:18] + ".."
                    # Compute depth
                    depth_level = 0
                    cur = el
                    seen: set = set()
                    while cur and cur.parent_id and cur.parent_id not in seen:
                        seen.add(cur.parent_id)
                        depth_level += 1
                        cur = snap.ui_map.get(cur.parent_id)  # type: ignore[assignment]
                    elements.append((ref_key, label, el.role, ex, ey, ew, eh, depth_level))
    except Exception as exc:
        logger.debug("Snapshot element collection failed: %s", exc)

    # If no recent snapshot, capture a fresh element tree
    if not _found_snapshot:
        try:
            tree = backend.get_element_tree(
                app=app, hwnd=hwnd, depth=depth, backend="uia",
            )
            if tree:
                counter = [0]

                def _collect_uia(el, tree_depth: int = 0) -> None:
                    counter[0] += 1
                    ref = f"e{counter[0]}"
                    if el.width > 0 and el.height > 0:
                        if refs is None or ref in refs:
                            label = el.name or el.role
                            if len(label) > 20:
                                label = label[:18] + ".."
                            elements.append((ref, label, el.role, el.x, el.y, el.width, el.height, tree_depth))
                    for child in el.children:
                        _collect_uia(child, tree_depth + 1)

                _collect_uia(tree)
        except Exception as exc:
            logger.debug("UIA element tree collection failed: %s", exc)

    if not elements:
        return None

    # Depth-based colors (BGR for GDI)
    DEPTH_COLORS_BGR = [
        0x0000FF,  # Red
        0x00A000,  # Green
        0xFF5000,  # Blue
        0x00A0FF,  # Orange
        0xC800A0,  # Purple
        0xB4B400,  # Teal
        0x6400C8,  # Crimson
        0xFF5050,  # Indigo
    ]

    # Compute label positions to avoid overlap
    label_rects: list = []
    label_positions: list = []

    for i, (ref, label, role, ex, ey, ew, eh, depth_level) in enumerate(elements):
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
        best_overlap = len(label_rects) + 1  # guaranteed > any real count

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

    # Draw highlights using GDI
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    gdi32 = ctypes.windll.gdi32  # type: ignore[attr-defined]

    hdc = user32.GetDC(None)
    font = gdi32.CreateFontW(
        14, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0, "Consolas"
    )

    try:
        # Draw all borders and labels simultaneously (single pass)
        for i, (ref, label, role, ex, ey, ew, eh, depth_level) in enumerate(elements):
            color = DEPTH_COLORS_BGR[depth_level % len(DEPTH_COLORS_BGR)]
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

        # Hold the display for the requested duration
        time.sleep(duration)

    finally:
        gdi32.DeleteObject(font)
        user32.ReleaseDC(None, hdc)
        user32.InvalidateRect(None, None, True)

    return None
