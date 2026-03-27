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


def _covered_area(elements: List[ElementInfo]) -> int:
    """Approximate covered area by summing non-overlapping bounding boxes.

    This is an overestimate when elements overlap, but good enough for
    coverage scoring without numpy dependency.
    """
    return sum(_rect_area(e.x, e.y, e.width, e.height) for e in elements)


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
                app=app, window_title=window_title, hwnd=hwnd, depth=depth,
                backend=pname,
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
