"""Cascading recognition engine for the ``see`` command (issue #140).

Progressive multi-provider UI element recognition:

1. Start with UIA (fastest, works on Win32/WPF/UWP)
2. If the app is detected as Electron/CEF and a debug port is available,
   add CDP elements for web-rendered content
3. If element coverage is still below the target threshold and AI is
   available, use vision to fill remaining gaps
4. Return merged element tree with ``source`` metadata on each element

Design goals
------------
* **Zero mandatory dependencies** — every provider is optional.  If CDP/AI
  is unavailable, we degrade gracefully to UIA only.
* **Cheap default** — UIA-only path adds no latency.  CDP is only attempted
  when Electron is detected.  AI is only attempted when explicitly enabled
  via ``--fill-gaps`` or when coverage is below the target.
* **Source tagging** — each element gets a ``source`` attribute so callers
  can see which provider found it.
* **No numpy** — coverage calculation uses simple rectangle intersection
  rather than pixel canvas arithmetic.

Public API
----------
    result = run_cascade(
        backend, app=app, window_title=window_title, hwnd=hwnd,
        depth=depth, backend_name='uia',
        coverage_target=0.0,   # 0 = UIA only unless Electron detected
        fill_gaps_ai=False,
    )
    tree    = result.tree        # ElementInfo root (same as backend.get_element_tree)
    stats   = result.stats       # CascadeStats
    session = result.session     # snapshot session string (pass to SnapshotManager)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

from naturo.backends.base import ElementInfo

logger = logging.getLogger(__name__)


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class ProviderStat:
    """Per-provider statistics."""
    name: str
    elements: int = 0
    elapsed_ms: float = 0.0
    status: str = "ok"  # ok | skipped | error


@dataclass
class CascadeStats:
    """Aggregated statistics from a cascade run."""
    providers: List[ProviderStat] = field(default_factory=list)
    total_elements: int = 0
    coverage_estimate: float = 0.0  # 0.0–1.0 (rough area coverage)

    def to_dict(self) -> dict:
        return {
            "total_elements": self.total_elements,
            "coverage_estimate": round(self.coverage_estimate, 3),
            "providers": [
                {
                    "name": p.name,
                    "elements": p.elements,
                    "elapsed_ms": round(p.elapsed_ms, 1),
                    "status": p.status,
                }
                for p in self.providers
            ],
        }


@dataclass
class CascadeResult:
    """Result from :func:`run_cascade`."""
    tree: Optional[ElementInfo]  # Root element (or None if nothing found)
    stats: CascadeStats
    primary_provider: str = "uia"  # Which provider produced the root tree


# ── Coverage helpers ──────────────────────────────────────────────────────────


def _rect_area(x: int, y: int, w: int, h: int) -> int:
    return max(0, w) * max(0, h)


# Roles that are structural containers — their bounding boxes span large areas
# but they don't represent actionable content. Only count them if they are leaf
# nodes (no children), meaning no deeper inspection found inner elements.
_CONTAINER_ROLES = frozenset({
    "pane", "group", "window", "document", "custom", "frame",
    "scrollbar", "toolbar", "statusbar", "titlebar", "menubar",
    "contentsview", "browseruserview", "browserview",
})


def _is_actionable_leaf(el: ElementInfo) -> bool:
    """Return True if the element should count toward coverage.

    An element counts if it is a leaf (no children) or has an actionable role
    (Button, Edit, Link, etc.). Large container elements with children are
    excluded because their bounding boxes inflate coverage without indicating
    that the region has been deeply inspected.
    """
    role_lower = el.role.lower()
    # Leaf elements always count
    if not el.children:
        return True
    # Container roles with children — skip (children provide the real coverage)
    if role_lower in _CONTAINER_ROLES:
        return False
    # Non-container roles with children still count (e.g. TabItem with subelements)
    return True


def _covered_area(elements: List[ElementInfo]) -> int:
    """Approximate covered area using only actionable/leaf elements.

    Excludes large container elements (Pane, Group, etc.) that have children,
    since their bounding boxes inflate coverage without indicating actual
    content discovery. This prevents false 100% coverage when UIA only finds
    top-level shells around Electron/CEF content.
    """
    return sum(
        _rect_area(e.x, e.y, e.width, e.height)
        for e in elements
        if _is_actionable_leaf(e)
    )


def _window_area(tree: ElementInfo) -> int:
    return _rect_area(tree.x, tree.y, tree.width, tree.height)


def _estimate_coverage(elements: List[ElementInfo], window_area: int) -> float:
    if window_area <= 0 or not elements:
        return 0.0
    covered = _covered_area(elements)
    return min(1.0, covered / window_area)


def _flatten(root: ElementInfo) -> List[ElementInfo]:
    """Depth-first flatten of element tree."""
    result: List[ElementInfo] = []

    def _visit(el: ElementInfo) -> None:
        result.append(el)
        for child in el.children:
            _visit(child)

    _visit(root)
    return result


# ── Shallow tree detection (issue #275) ───────────────────────────────────────

#: Maximum element count to consider a tree "shallow".
SHALLOW_TREE_MAX_ELEMENTS = 5

#: Minimum ratio of elements with invalid bounds to trigger fallback.
SHALLOW_TREE_INVALID_BOUNDS_RATIO = 0.5


def _has_invalid_bounds(el: ElementInfo) -> bool:
    """Return True if the element has zero-area or negative-coordinate bounds."""
    if el.width <= 0 or el.height <= 0:
        return True
    if el.x < 0 or el.y < 0:
        return True
    return False


def _is_shallow_tree(elements: List[ElementInfo]) -> tuple[bool, int, int]:
    """Detect whether a UIA tree is too shallow to be useful.

    Returns (is_shallow, total_count, invalid_count).
    """
    if not elements:
        return True, 0, 0

    total = len(elements)
    if total > SHALLOW_TREE_MAX_ELEMENTS:
        return False, total, 0

    invalid = sum(1 for e in elements if _has_invalid_bounds(e))
    ratio = invalid / total if total > 0 else 0.0
    is_shallow = ratio >= SHALLOW_TREE_INVALID_BOUNDS_RATIO
    return is_shallow, total, invalid


# ── Tag helpers ───────────────────────────────────────────────────────────────


def _tag_source(el: ElementInfo, source: str) -> ElementInfo:
    """Return a copy of *el* with ``source`` added to its properties."""
    props = dict(getattr(el, "properties", {}) or {})
    props["source"] = source
    return ElementInfo(
        id=el.id,
        role=el.role,
        name=el.name,
        value=el.value,
        x=el.x,
        y=el.y,
        width=el.width,
        height=el.height,
        children=[_tag_source(c, source) for c in el.children],
        properties=props,
    )


# ── CDP element helper ────────────────────────────────────────────────────────


def _fetch_cdp_elements(
    pid: int,
    debug_port: int,
    parent_bounds: tuple[int, int, int, int],
) -> List[ElementInfo]:
    """Fetch DOM elements via CDP for an Electron/CEF app.

    Parameters
    ----------
    pid:
        Process ID (used only for logging).
    debug_port:
        Chrome DevTools Protocol port.
    parent_bounds:
        (x, y, w, h) of the window for coordinate offsetting.

    Returns
    -------
    List[ElementInfo]
        Flat list of interactive DOM elements (buttons, inputs, links, etc.).
        Returns empty list on any error.
    """
    try:
        from naturo.cdp import CDPClient
    except ImportError:
        logger.debug("CDP module not available; skipping CDP provider")
        return []

    try:
        client = CDPClient(port=debug_port)
        # Fetch interactive elements using DOM.querySelectorAll
        # This is a best-effort list of common interactive selectors
        SELECTOR = (
            "button, input, textarea, select, a[href], "
            "[role='button'], [role='checkbox'], [role='combobox'], "
            "[role='menuitem'], [role='option'], [role='tab'], "
            "[role='textbox'], [role='link'], [onclick], "
            "[tabindex]:not([tabindex='-1'])"
        )
        dom_elements = client.query_selector_all(SELECTOR)
        elements: List[ElementInfo] = []
        px, py = parent_bounds[0], parent_bounds[1]

        for dom_el in dom_elements:
            bounds = dom_el.get("bounds", {})
            ex = int(bounds.get("x", 0)) + px
            ey = int(bounds.get("y", 0)) + py
            ew = int(bounds.get("width", 0))
            eh = int(bounds.get("height", 0))

            if ew == 0 or eh == 0:
                continue  # Invisible element

            tag = dom_el.get("tagName", "").lower()
            role_map = {"button": "Button", "input": "Edit", "a": "Link",
                        "textarea": "Edit", "select": "ComboBox"}
            aria_role = dom_el.get("ariaRole", "")
            role = aria_role.capitalize() or role_map.get(tag, "Text")

            el_id = f"cdp_{dom_el.get('nodeId', id(dom_el))}"
            elements.append(ElementInfo(
                id=el_id,
                role=role,
                name=dom_el.get("ariaLabel") or dom_el.get("textContent", "")[:80],
                value=dom_el.get("value"),
                x=ex, y=ey, width=ew, height=eh,
                children=[],
                properties={"source": "cdp", "tag": tag, "parent_id": None},
            ))

        return elements
    except Exception as exc:
        logger.debug("CDP element fetch failed (port=%d): %s", debug_port, exc)
        return []


# ── AI vision helper ──────────────────────────────────────────────────────────


def _fetch_ai_elements(
    screenshot_path: str,
    window_bounds: tuple[int, int, int, int],
    provider_name: str = "auto",
) -> List[ElementInfo]:
    """Use AI vision to identify additional elements from a screenshot.

    Returns a flat list of elements identified by the AI provider.
    Falls back gracefully if the provider is unavailable.
    """
    try:
        from naturo.providers.base import get_vision_provider
        from naturo.errors import AIProviderUnavailableError

        try:
            provider = get_vision_provider(provider_name)
        except AIProviderUnavailableError:
            return []

        result = provider.identify_element(
            screenshot_path,
            element_description=(
                "List all visible interactive UI elements (buttons, inputs, links, "
                "checkboxes, tabs, menus). Return a JSON array where each item has: "
                "role, name, bounds (x, y, width, height)."
            ),
        )

        elements: List[ElementInfo] = []
        for i, raw in enumerate(result.elements):
            if not isinstance(raw, dict):
                continue
            b = raw.get("bounds", {})
            ex, ey = int(b.get("x", 0)), int(b.get("y", 0))
            ew, eh = int(b.get("width", 50)), int(b.get("height", 20))
            role = raw.get("role", "Unknown").capitalize()
            name = raw.get("name", "")
            elements.append(ElementInfo(
                id=f"ai_{i}",
                role=role,
                name=name,
                value=None,
                x=ex, y=ey, width=ew, height=eh,
                children=[],
                properties={"source": "vision", "confidence": raw.get("confidence", 0.5)},
            ))
        return elements
    except Exception as exc:
        logger.debug("AI vision element fetch failed: %s", exc)
        return []


# ── Hybrid tree helpers ───────────────────────────────────────────────────────

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
    win32_children = _get_hwnd_children_with_class(hwnd)
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
            cdp_elements = _try_cdp_for_hwnd(
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
    if pid is None:
        return []

    try:
        from naturo.electron import get_debug_port
        debug_port = get_debug_port(pid)
    except Exception:
        return []

    if not debug_port:
        return []

    elements = _fetch_cdp_elements(pid, debug_port, bounds)
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


# ── Main cascade entry point ──────────────────────────────────────────────────


def run_cascade(
    backend,
    *,
    app: Optional[str] = None,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    pid: Optional[int] = None,
    depth: int = 3,
    backend_name: str = "uia",
    coverage_target: float = 0.0,
    fill_gaps_ai: bool = False,
    ai_provider: str = "auto",
    screenshot_path: Optional[str] = None,
) -> CascadeResult:
    """Run progressive recognition and return a merged element tree.

    Parameters
    ----------
    backend:
        Platform backend instance (:class:`naturo.backends.base.Backend`).
    app:
        Target application name (passed to ``backend.get_element_tree``).
    window_title:
        Window title filter.
    hwnd:
        Window handle (Windows only).
    pid:
        Process ID.
    depth:
        Maximum tree depth for UIA/MSAA probes.
    backend_name:
        Base accessibility backend: ``"uia"`` | ``"msaa"`` | ``"ia2"`` | ``"jab"`` | ``"auto"``.
        When ``"auto"``, each provider is tried in cascade order.
    coverage_target:
        When >0, also run CDP if UIA coverage < this threshold (0.0–1.0).
        Ignored when ``backend_name`` is ``"auto"`` (always cascades).
    fill_gaps_ai:
        When True, add AI vision as the final fallback provider.
    ai_provider:
        AI provider name (``"auto"`` | ``"anthropic"`` | ``"openai"`` | ``"ollama"``).
    screenshot_path:
        Path to existing screenshot for AI vision (avoids re-capture).

    Returns
    -------
    CascadeResult
        Merged element tree with source-tagged elements and statistics.
    """
    # ── Hybrid mode: per-node backend selection ────────────────────────────
    if backend_name == "hybrid":
        resolved_hwnd = hwnd
        if resolved_hwnd is None:
            # Resolve app/window_title to hwnd first
            try:
                resolved_hwnd = backend._resolve_hwnd(
                    app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                )
            except Exception as exc:
                logger.debug("Hybrid: HWND resolution failed: %s", exc)
                return CascadeResult(
                    tree=None,
                    stats=CascadeStats(providers=[
                        ProviderStat(name="hybrid", status="error"),
                    ]),
                    primary_provider="hybrid",
                )

        tree, stats = build_hybrid_tree(
            backend, hwnd=resolved_hwnd, depth=depth, pid=pid,
        )
        return CascadeResult(
            tree=tree,
            stats=stats,
            primary_provider="hybrid",
        )

    stats = CascadeStats()
    merged_elements: List[ElementInfo] = []
    root_tree: Optional[ElementInfo] = None
    window_area = 0

    # ── Provider 1: UIA/MSAA/JAB/IA2 (primary accessibility) ────────────────
    providers_to_try = (
        ["uia", "msaa", "jab", "ia2"] if backend_name == "auto" else [backend_name]
    )

    for pname in providers_to_try:
        t0 = time.monotonic()
        try:
            tree = backend.get_element_tree(
                app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                depth=depth, backend=pname,
            )
            elapsed = (time.monotonic() - t0) * 1000

            if tree is not None:
                tagged = _tag_source(tree, pname)
                flat = _flatten(tagged)
                elements_count = len(flat)

                # (#394) A tree with only a root node and zero children is
                # not useful — likely a UWP/WinUI app where the backend
                # could not reach the real UI.  Record it but keep trying
                # the next provider instead of accepting it immediately.
                if not tree.children:
                    logger.info(
                        "Provider %s returned root-only tree (0 children), "
                        "trying next provider...", pname,
                    )
                    stats.providers.append(ProviderStat(
                        name=pname, elements=elements_count,
                        elapsed_ms=elapsed, status="empty_tree",
                    ))
                    # Keep as fallback in case no provider does better
                    if root_tree is None:
                        root_tree = tagged
                        window_area = _window_area(tree)
                    continue

                stats.providers.append(ProviderStat(
                    name=pname, elements=elements_count, elapsed_ms=elapsed, status="ok"
                ))
                merged_elements.extend(flat[1:])  # skip root itself (merged below)
                root_tree = tagged
                window_area = _window_area(tree)
                break  # Got a valid tree; stop trying other base providers
            else:
                stats.providers.append(ProviderStat(
                    name=pname, elapsed_ms=elapsed, status="skipped"
                ))
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            logger.debug("Provider %s failed: %s", pname, exc)
            stats.providers.append(ProviderStat(
                name=pname, elapsed_ms=elapsed, status="error"
            ))

    # ── Provider 2: CDP (Electron/CEF apps) ─────────────────────────────────
    should_try_cdp = (
        coverage_target > 0
        or backend_name == "auto"
        or backend_name in ("cdp",)
    )

    if should_try_cdp and root_tree is not None:
        current_coverage = _estimate_coverage(merged_elements, window_area) if window_area > 0 else 0.0

        # Only try CDP if coverage is below target (or always when backend_name=auto)
        if backend_name == "auto" or current_coverage < coverage_target:
            t0 = time.monotonic()
            cdp_elements: List[ElementInfo] = []
            debug_port: Optional[int] = None

            try:
                # Try to detect CDP debug port for this app
                from naturo.electron import get_debug_port
                if pid:
                    debug_port = get_debug_port(pid)
                elif app:
                    # Resolve app to PID
                    from naturo.process import find_processes
                    procs = find_processes(app)
                    if procs:
                        debug_port = get_debug_port(procs[0].pid)
            except Exception as exc:
                logger.debug("CDP port detection failed: %s", exc)

            if debug_port:
                bounds = (root_tree.x, root_tree.y, root_tree.width, root_tree.height)
                cdp_elements = _fetch_cdp_elements(
                    pid or 0, debug_port, bounds
                )

            elapsed = (time.monotonic() - t0) * 1000
            if cdp_elements:
                # Tag and add CDP elements as children of root
                for el in cdp_elements:
                    tagged_el = _tag_source(el, "cdp")
                    merged_elements.append(tagged_el)

                stats.providers.append(ProviderStat(
                    name="cdp", elements=len(cdp_elements), elapsed_ms=elapsed, status="ok"
                ))
            else:
                stats.providers.append(ProviderStat(
                    name="cdp", elapsed_ms=elapsed,
                    status="skipped" if debug_port is None else "no_elements"
                ))

    # ── Shallow tree detection (issue #275) ────────────────────────────────
    # When the UIA tree is too shallow (few elements, mostly invalid bounds),
    # automatically enable AI vision fallback even without --fill-gaps.
    shallow_fallback = False
    if root_tree is not None and not fill_gaps_ai:
        flat_all = _flatten(root_tree)
        is_shallow, total_count, invalid_count = _is_shallow_tree(flat_all)
        if is_shallow and screenshot_path:
            shallow_fallback = True
            logger.info(
                "UIA tree too shallow (%d elements, %d with invalid bounds), "
                "falling back to AI vision...",
                total_count, invalid_count,
            )

    # ── Provider 3: AI vision fallback ──────────────────────────────────────
    should_run_ai = (fill_gaps_ai or shallow_fallback) and root_tree is not None and screenshot_path
    if should_run_ai:
        current_coverage = _estimate_coverage(merged_elements, window_area) if window_area > 0 else 0.0

        if current_coverage < coverage_target or coverage_target == 0.0 or shallow_fallback:
            t0 = time.monotonic()
            bounds = (root_tree.x, root_tree.y, root_tree.width, root_tree.height)
            ai_elements = _fetch_ai_elements(screenshot_path, bounds, ai_provider)
            elapsed = (time.monotonic() - t0) * 1000

            trigger = "shallow_tree" if shallow_fallback else "fill_gaps"
            if ai_elements:
                for el in ai_elements:
                    merged_elements.append(el)
                stats.providers.append(ProviderStat(
                    name="vision", elements=len(ai_elements), elapsed_ms=elapsed,
                    status="ok",
                ))
                logger.info(
                    "AI vision added %d elements (trigger: %s)",
                    len(ai_elements), trigger,
                )
            else:
                stats.providers.append(ProviderStat(
                    name="vision", elapsed_ms=elapsed, status="skipped"
                ))

    # ── Assemble final stats ─────────────────────────────────────────────────
    stats.total_elements = len(merged_elements)
    if window_area > 0 and merged_elements:
        stats.coverage_estimate = _estimate_coverage(merged_elements, window_area)

    return CascadeResult(
        tree=root_tree,
        stats=stats,
        primary_provider=providers_to_try[0] if providers_to_try else "uia",
    )
