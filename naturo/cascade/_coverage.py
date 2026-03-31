"""Coverage estimation helpers for the cascade engine."""
from __future__ import annotations

from typing import List

from naturo.backends.base import ElementInfo


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


# ── Shallow tree detection (issue #275) ───────────────────────────────────

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


# ── Tag helpers ───────────────────────────────────────────────────────────


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
