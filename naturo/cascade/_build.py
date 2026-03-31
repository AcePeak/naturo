"""Hybrid tree building: per-node backend selection."""
from __future__ import annotations

import logging
import time
from typing import Optional

from naturo.backends.base import ElementInfo
from naturo.cascade._types import CascadeStats, ProviderStat
from naturo.cascade._coverage import (
    _estimate_coverage,
    _flatten,
    _tag_source,
    _window_area,
)
logger = logging.getLogger(__name__)


def _get_cascade_pkg():
    """Late-bound access to the cascade package for test-patchability."""
    import naturo.cascade as _pkg
    return _pkg


# Map Win32 class names to preferred accessibility backends.
_CLASS_BACKEND_MAP: dict[str, str] = {
    # Electron / CEF — web content behind UIA opaque pane
    "Chrome_RenderWidgetHostHWND": "cdp",
    "Chrome_WidgetWin_0": "cdp",
    "Chrome_WidgetWin_1": "cdp",
    # Java — Swing/AWT use Java Access Bridge
    "SunAwtFrame": "jab",
    "SunAwtDialog": "jab",
    "SunAwtCanvas": "jab",
    "SunAwtPanel": "jab",
    # Mozilla — Firefox/Thunderbird use IAccessible2
    "MozillaWindowClass": "ia2",
    "MozillaCompositorWindowClass": "ia2",
}


def _detect_backend_for_class(cls_name: str) -> str:
    """Select the best accessibility backend for a Win32 window class.

    Args:
        cls_name: Win32 window class name (e.g. "Chrome_RenderWidgetHostHWND").

    Returns:
        Backend name: "cdp", "jab", "ia2", or "uia" (default).
    """
    if cls_name in _CLASS_BACKEND_MAP:
        return _CLASS_BACKEND_MAP[cls_name]
    # Java Access Bridge classes can have versioned names
    if cls_name.startswith("SunAwt") or cls_name.startswith("javax.swing"):
        return "jab"
    return "uia"


def _get_hwnd_children_with_class(hwnd: int) -> list[tuple[int, str, str, tuple[int, int, int, int]]]:
    """Enumerate direct child HWNDs with class name and bounds.

    Returns list of (child_hwnd, class_name, title, (x, y, w, h)).
    Runs only on Windows; returns empty list on other platforms.
    """
    import platform as _plat
    if _plat.system() != "Windows":
        return []

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    children: list[tuple[int, str, str, tuple[int, int, int, int]]] = []

    child = user32.FindWindowExW(hwnd, None, None, None)
    while child:
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(child, cls_buf, 256)
        title_buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(child, title_buf, 256)
        rect = wintypes.RECT()
        user32.GetWindowRect(child, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        children.append((child, cls_buf.value, title_buf.value, (rect.left, rect.top, w, h)))
        child = user32.FindWindowExW(hwnd, child, None, None)

    return children


def build_hybrid_tree(
    backend,
    *,
    hwnd: int,
    depth: int = 3,
    pid: Optional[int] = None,
) -> tuple[Optional[ElementInfo], CascadeStats]:
    """Build a hybrid element tree with per-node backend selection.

    Instead of running one backend for the entire tree, this function:

    1. Gets the UIA tree for the root window (fast, single DLL call).
    2. Enumerates Win32 child HWNDs to discover the window hierarchy.
    3. For each child HWND, detects the best backend by class name:
       - ``Chrome_RenderWidgetHostHWND`` -> CDP
       - ``SunAwt*`` -> JAB (Java Access Bridge)
       - ``MozillaWindowClass`` -> IA2 (IAccessible2)
       - Default -> UIA
    4. For UIA leaf nodes that have Win32 children, enriches the tree by
       fetching subtrees from the appropriate backend per child HWND.
    5. Tags every element with its discovery backend in ``properties["source"]``.

    This produces a mixed-backend tree like Naturobot's selector format::

        [win32] Window 'Feishu' hwnd=198164
          [uia] TitleBar 'Feishu'
          [win32] ChildWindow class='Chrome_RenderWidgetHostHWND'
            [cdp] div.nav-item 'Messages'
            [cdp] div.nav-item 'Calendar'

    Args:
        backend: Platform backend instance.
        hwnd: Root window handle.
        depth: Maximum tree depth for each backend probe.
        pid: Process ID (used for CDP port detection).

    Returns:
        Tuple of (root ElementInfo or None, CascadeStats).
    """
    stats = CascadeStats()

    # ── Phase 1: Get UIA tree as primary structure ──────────────────────────
    t0 = time.monotonic()
    try:
        uia_tree = backend.get_element_tree(hwnd=hwnd, depth=depth, backend="uia")
    except Exception as exc:
        logger.debug("Hybrid: UIA tree failed: %s", exc)
        uia_tree = None
    uia_elapsed = (time.monotonic() - t0) * 1000

    if uia_tree is None:
        stats.providers.append(ProviderStat(name="uia", elapsed_ms=uia_elapsed, status="error"))
        return None, stats

    uia_tree = _tag_source(uia_tree, "uia")
    uia_flat = _flatten(uia_tree)
    stats.providers.append(ProviderStat(
        name="uia", elements=len(uia_flat), elapsed_ms=uia_elapsed, status="ok",
    ))

    # ── Phase 2: Enumerate Win32 child HWNDs ────────────────────────────────
    t0 = time.monotonic()
    win32_children = _get_cascade_pkg()._get_hwnd_children_with_class(hwnd)
    win32_elapsed = (time.monotonic() - t0) * 1000

    if not win32_children:
        # No child HWNDs — UIA tree is all we have
        stats.total_elements = len(uia_flat)
        window_area = _window_area(uia_tree)
        if window_area > 0:
            stats.coverage_estimate = _estimate_coverage(uia_flat[1:], window_area)
        return uia_tree, stats

    # ── Phase 3: Per-HWND backend enrichment ────────────────────────────────
    # Find UIA leaf nodes (no children or only Pane children) that correspond
    # to Win32 child HWNDs where a different backend would be better.
    enriched_count = 0
    cdp_count = 0
    jab_count = 0
    ia2_count = 0

    for child_hwnd, cls_name, title, (cx, cy, cw, ch) in win32_children:
        preferred = _detect_backend_for_class(cls_name)
        if preferred == "uia":
            continue  # UIA tree already covers this

        # Find the UIA node that contains this HWND's bounds
        target_node = _find_node_by_bounds(uia_tree, cx, cy, cw, ch)

        if preferred == "cdp":
            # Try CDP for Electron/CEF content
            cdp_elements = _get_cascade_pkg()._try_cdp_for_hwnd(
                child_hwnd, pid, (cx, cy, cw, ch),
            )
            if cdp_elements and target_node is not None:
                target_node.children.extend(cdp_elements)
                cdp_count += len(cdp_elements)
                enriched_count += len(cdp_elements)
            elif cdp_elements:
                # No matching UIA node — append to root
                uia_tree.children.extend(cdp_elements)
                cdp_count += len(cdp_elements)
                enriched_count += len(cdp_elements)

        elif preferred == "jab":
            jab_elements = _try_backend_for_hwnd(
                backend, child_hwnd, "jab", depth, cls_name, title,
            )
            if jab_elements and target_node is not None:
                target_node.children.extend(jab_elements)
                jab_count += len(jab_elements)
                enriched_count += len(jab_elements)

        elif preferred == "ia2":
            ia2_elements = _try_backend_for_hwnd(
                backend, child_hwnd, "ia2", depth, cls_name, title,
            )
            if ia2_elements and target_node is not None:
                target_node.children.extend(ia2_elements)
                ia2_count += len(ia2_elements)
                enriched_count += len(ia2_elements)

    # Record Win32 scan + enrichment stats
    total_enrichment_elapsed = (time.monotonic() - t0) * 1000
    if win32_children:
        stats.providers.append(ProviderStat(
            name="win32_scan", elements=len(win32_children),
            elapsed_ms=win32_elapsed, status="ok",
        ))
    if cdp_count > 0:
        stats.providers.append(ProviderStat(
            name="cdp", elements=cdp_count,
            elapsed_ms=total_enrichment_elapsed - win32_elapsed, status="ok",
        ))
    if jab_count > 0:
        stats.providers.append(ProviderStat(
            name="jab", elements=jab_count,
            elapsed_ms=total_enrichment_elapsed - win32_elapsed, status="ok",
        ))
    if ia2_count > 0:
        stats.providers.append(ProviderStat(
            name="ia2", elements=ia2_count,
            elapsed_ms=total_enrichment_elapsed - win32_elapsed, status="ok",
        ))

    # Final stats
    all_flat = _flatten(uia_tree)
    stats.total_elements = len(all_flat)
    window_area = _window_area(uia_tree)
    if window_area > 0:
        stats.coverage_estimate = _estimate_coverage(all_flat[1:], window_area)

    return uia_tree, stats


def _find_node_by_bounds(
    root: ElementInfo,
    x: int, y: int, w: int, h: int,
    tolerance: int = 5,
) -> Optional[ElementInfo]:
    """Find the deepest tree node whose bounds contain or closely match the target.

    Walks the tree depth-first, preferring deeper matches.  A node "matches" if
    its bounding box overlaps with the target by at least 80% of the target area.

    Args:
        root: Root of the element tree to search.
        x, y, w, h: Target bounding rectangle.
        tolerance: Pixel tolerance for bounds comparison.

    Returns:
        The best matching ElementInfo, or None.
    """
    if w <= 0 or h <= 0:
        return None

    target_area = w * h
    best: Optional[ElementInfo] = None
    best_depth = -1

    def _walk(node: ElementInfo, depth: int) -> None:
        nonlocal best, best_depth

        # Check if node bounds overlap significantly with target
        nx, ny, nw, nh = node.x, node.y, node.width, node.height
        overlap_x = max(0, min(nx + nw, x + w) - max(nx, x))
        overlap_y = max(0, min(ny + nh, y + h) - max(ny, y))
        overlap_area = overlap_x * overlap_y

        if overlap_area >= target_area * 0.5:
            # Prefer deeper nodes (more specific containers)
            if depth > best_depth:
                best = node
                best_depth = depth

        for child in node.children:
            _walk(child, depth + 1)

    _walk(root, 0)
    return best


def _try_cdp_for_hwnd(
    child_hwnd: int,
    pid: Optional[int],
    bounds: tuple[int, int, int, int],
) -> list[ElementInfo]:
    """Try CDP to get elements for a Chrome_RenderWidgetHostHWND.

    Args:
        child_hwnd: HWND of the render widget.
        pid: Process ID for debug port detection.
        bounds: (x, y, w, h) of the child window.

    Returns:
        List of tagged CDP elements, or empty list.
    """
    _pkg = _get_cascade_pkg()
    debug_port = _pkg.find_cdp_port(pid)
    if not debug_port:
        return []

    elements = _pkg._fetch_cdp_elements(pid or 0, debug_port, bounds)
    return [_tag_source(el, "cdp") for el in elements]


def _try_backend_for_hwnd(
    backend,
    child_hwnd: int,
    backend_name: str,
    depth: int,
    cls_name: str,
    title: str,
) -> list[ElementInfo]:
    """Try a specific backend for a child HWND and return tagged children.

    Args:
        backend: Platform backend instance.
        child_hwnd: HWND to probe.
        backend_name: Backend to use ("jab", "ia2", "msaa").
        depth: Max tree depth.
        cls_name: Win32 class name (for logging).
        title: Window title (for logging).

    Returns:
        List of tagged child elements (not including root), or empty list.
    """
    try:
        tree = backend.get_element_tree(
            hwnd=child_hwnd, depth=depth, backend=backend_name,
        )
    except Exception as exc:
        logger.debug(
            "Hybrid: %s failed for HWND %s (%s '%s'): %s",
            backend_name, child_hwnd, cls_name, title, exc,
        )
        return []

    if tree is None or not tree.children:
        return []

    tagged = _tag_source(tree, backend_name)
    # Return children of the root (the root itself is the HWND container)
    return tagged.children


# ── CDP port discovery ───────────────────────────────────────────────────────


def find_cdp_port(pid: Optional[int] = None) -> Optional[int]:
    """Find an active CDP debug port for a process or on common ports.

    Checks the process command line for ``--remote-debugging-port=<N>``,
    then falls back to probing common ports (9222, 9229, 9333).

    Args:
        pid: Process ID to check.  When ``None``, only probes common ports.

    Returns:
        Port number if a CDP endpoint responds, ``None`` otherwise.
    """
    import platform

    # Phase 1: check process command line (Windows only)
    if pid is not None and platform.system() == "Windows":
        try:
            import subprocess

            result = subprocess.run(
                ["wmic", "process", "where", f"ProcessId={pid}",
                 "get", "CommandLine", "/format:list"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "--remote-debugging-port=" in line:
                        for part in line.split():
                            if part.startswith("--remote-debugging-port="):
                                port_str = part.split("=", 1)[1]
                                return int(port_str)
        except Exception as exc:
            logger.debug("Failed to get command line for PID %d: %s", pid, exc)

    # Phase 2: probe common debug ports via HTTP
    for port in [9222, 9229, 9333]:
        try:
            import urllib.request
            import urllib.error

            url = f"http://127.0.0.1:{port}/json/version"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return port
        except Exception as exc:
            logger.debug("CDP port check failed for port %s: %s", port, exc)

    return None
