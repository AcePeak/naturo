"""Tree merging: AI-to-UIA tree merge with IoU + text/proximity deduplication."""
from __future__ import annotations

import logging
import math
from typing import List, Optional

from naturo.backends.base import ElementInfo
from naturo.cascade._coverage import _flatten

logger = logging.getLogger(__name__)


def _iou(a: ElementInfo, b: ElementInfo) -> float:
    """Compute Intersection-over-Union of two element bounding boxes."""
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.width, b.x + b.width)
    y2 = min(a.y + a.height, b.y + b.height)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter == 0:
        return 0.0
    area_a = a.width * a.height
    area_b = b.width * b.height
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _text_proximity_match(
    ai_el: ElementInfo,
    uia_visible: List[ElementInfo],
    proximity_px: float = 200.0,
) -> Optional[ElementInfo]:
    """Check if an AI element duplicates a UIA element by text + proximity.

    Returns the matching UIA element if:
    - Both have non-empty names
    - One name contains the other (case-insensitive)
    - Their center-to-center distance is within ``proximity_px`` pixels

    This catches duplicates that IoU misses due to coordinate precision
    differences between UIA (exact pixel bounds) and AI vision (estimated
    bounds that can vary by 50-200px).

    Args:
        ai_el: The AI vision element to check.
        uia_visible: Visible UIA elements to match against.
        proximity_px: Maximum center-to-center distance for a match.

    Returns:
        The matching UIA element, or None if no match.
    """
    ai_name = (ai_el.name or "").strip().lower()
    if not ai_name:
        return None

    ai_cx = ai_el.x + ai_el.width / 2
    ai_cy = ai_el.y + ai_el.height / 2

    for uia_el in uia_visible:
        uia_name = (uia_el.name or "").strip().lower()
        if not uia_name:
            continue

        # Text match: one name contains the other
        if uia_name not in ai_name and ai_name not in uia_name:
            continue

        # Proximity check: center-to-center distance
        uia_cx = uia_el.x + uia_el.width / 2
        uia_cy = uia_el.y + uia_el.height / 2
        dist = math.hypot(ai_cx - uia_cx, ai_cy - uia_cy)
        if dist <= proximity_px:
            return uia_el

    return None


def _record_corroboration(node: ElementInfo, ai_el: ElementInfo) -> None:
    """Record that an uncertain hit corroborated a deterministic node (M1).

    The duplicate AI/image element is *not* added to the tree, but the technique
    that saw it is appended to the matched node's ``corroborated_by`` list so the
    fused node reports every technique that recognized it
    (``docs/RECOGNITION_TREE.md`` §4).  Deterministic ordering/preference is
    applied later by :mod:`naturo.cascade._correctness`.
    """
    ai_props = getattr(ai_el, "properties", {}) or {}
    technique = ai_props.get("source", "vision")
    node_props = node.properties
    if not isinstance(node_props, dict):
        return
    corroborated = node_props.setdefault("corroborated_by", [])
    if technique not in corroborated:
        corroborated.append(technique)


def _merge_ai_into_tree(
    root: ElementInfo,
    ai_elements: List[ElementInfo],
    iou_threshold: float = 0.3,
    proximity_px: float = 200.0,
) -> tuple[List[ElementInfo], int, int]:
    """Merge AI vision elements into the UIA tree, deduplicating by IoU
    and text similarity + proximity.

    For each AI element:
    1. If it overlaps an existing UIA element with IoU >= threshold, skip it.
    2. If it has similar text to a nearby UIA element (within proximity_px),
       skip it (#702).
    3. Otherwise, attach it as a child of the deepest UIA node whose
       bounding box contains the AI element's center point.

    Parent lookup uses a snapshot of the UIA tree taken *before* any AI
    elements are added, so AI elements are always flat siblings under
    UIA containers and never nest inside each other.

    Args:
        root: The UIA element tree root.
        ai_elements: AI vision elements to merge.
        iou_threshold: Minimum IoU to consider elements as duplicates.
        proximity_px: Maximum center-to-center distance for text+proximity
            dedup (#702).

    Returns:
        (novel_elements, added_count, skipped_count)
    """
    if not ai_elements:
        return [], 0, 0

    # Snapshot UIA tree before modifications — used for both IoU comparison
    # and parent lookup, so AI elements don't affect each other's placement.
    uia_flat = _flatten(root)
    uia_visible = [e for e in uia_flat if e.width > 0 and e.height > 0]

    # Build a parent lookup list: (node, depth) pairs from the original tree.
    # This is a frozen snapshot — adding AI children to nodes won't change it.
    uia_parents: list[tuple[ElementInfo, int]] = []

    def _collect_parents(node: ElementInfo, depth: int) -> None:
        uia_parents.append((node, depth))
        for child in node.children:
            _collect_parents(child, depth + 1)

    _collect_parents(root, 0)

    added: List[ElementInfo] = []
    skipped = 0

    for ai_el in ai_elements:
        if ai_el.width <= 0 or ai_el.height <= 0:
            skipped += 1
            continue

        # --- Pass 1: IoU geometric dedup (fast path) ---
        is_duplicate = False
        best_iou = 0.0
        best_match: Optional[ElementInfo] = None
        for uia_el in uia_visible:
            score = _iou(ai_el, uia_el)
            if score > best_iou:
                best_iou = score
                best_match = uia_el
            if score >= iou_threshold:
                is_duplicate = True
                break

        if is_duplicate:
            if best_match is not None:
                _record_corroboration(best_match, ai_el)
            skipped += 1
            logger.debug(
                "AI merge: skip '%s' (%d,%d %dx%d) IoU=%.2f with UIA '%s'",
                ai_el.name, ai_el.x, ai_el.y, ai_el.width, ai_el.height,
                best_iou, best_match.name if best_match else "?",
            )
            continue

        # --- Pass 2: text + proximity dedup (#702) ---
        text_match = _text_proximity_match(ai_el, uia_visible, proximity_px)
        if text_match is not None:
            _record_corroboration(text_match, ai_el)
            skipped += 1
            logger.debug(
                "AI merge: skip '%s' (%d,%d %dx%d) text+proximity match "
                "with UIA '%s' (%d,%d %dx%d)",
                ai_el.name, ai_el.x, ai_el.y, ai_el.width, ai_el.height,
                text_match.name, text_match.x, text_match.y,
                text_match.width, text_match.height,
            )
            continue

        # Find deepest UIA parent whose bounds contain the AI element's center.
        # Uses the pre-snapshot parent list, not the live (modified) tree.
        cx = ai_el.x + ai_el.width // 2
        cy = ai_el.y + ai_el.height // 2
        best_parent = root
        best_depth = -1
        for node, depth in uia_parents:
            if (node.x <= cx <= node.x + node.width
                    and node.y <= cy <= node.y + node.height
                    and depth > best_depth):
                best_parent = node
                best_depth = depth

        best_parent.children.append(ai_el)
        added.append(ai_el)

    return added, len(added), skipped


def _find_containing_node(
    root: ElementInfo, cx: int, cy: int,
) -> Optional[ElementInfo]:
    """Find the deepest tree node whose bounding box contains point (cx, cy)."""
    best: Optional[ElementInfo] = None
    best_depth = -1

    def _walk(node: ElementInfo, depth: int) -> None:
        nonlocal best, best_depth
        if (node.x <= cx <= node.x + node.width
                and node.y <= cy <= node.y + node.height):
            if depth > best_depth:
                best = node
                best_depth = depth
        for child in node.children:
            _walk(child, depth + 1)

    _walk(root, 0)
    return best
