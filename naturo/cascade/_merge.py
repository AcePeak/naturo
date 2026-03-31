"""Tree merging: AI-to-UIA tree merge with IoU deduplication."""
from __future__ import annotations

import logging
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


def _merge_ai_into_tree(
    root: ElementInfo,
    ai_elements: List[ElementInfo],
    iou_threshold: float = 0.3,
) -> tuple[List[ElementInfo], int, int]:
    """Merge AI vision elements into the UIA tree, deduplicating by IoU.

    For each AI element:
    - If it overlaps an existing UIA leaf with IoU >= threshold, skip it
      (UIA already found this element).
    - Otherwise, attach it as a child of the deepest UIA node whose
      bounding box contains the AI element's center point.

    Parent lookup uses a snapshot of the UIA tree taken *before* any AI
    elements are added, so AI elements are always flat siblings under
    UIA containers and never nest inside each other.

    Returns
    -------
    (novel_elements, added_count, skipped_count)
        novel_elements: AI elements that were added (for stats).
        added_count: Number of elements inserted into tree.
        skipped_count: Number of duplicates skipped.
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

        # Check if any existing UIA element overlaps significantly
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
            skipped += 1
            logger.debug(
                "AI merge: skip '%s' (%d,%d %dx%d) IoU=%.2f with UIA '%s'",
                ai_el.name, ai_el.x, ai_el.y, ai_el.width, ai_el.height,
                best_iou, best_match.name if best_match else "?",
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
