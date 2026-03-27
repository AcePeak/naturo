"""Stable element reference assignment for UI snapshots.

Generates deterministic ``eN`` refs based on element identity (AutomationId,
role, name, parent chain) so the same UI element receives the same ref across
consecutive snapshots — even when the tree changes slightly (e.g. Calculator
display update after pressing Clear).

Replaces the old sequential assignment (e1, e2, e3 in DFS order) which caused
refs to shift whenever elements were added, removed, or reordered (#456).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Tuple, Type

_TREE_ASSIGNED_RE = re.compile(r"e\d+")


def _get_real_automation_id(el: Any) -> str | None:
    """Extract a real UIA AutomationId, filtering out tree-assigned eN IDs.

    ``populate_hierarchy`` in ``bridge.py`` assigns ``"eN"`` IDs to elements
    with empty ids.  Those are not real AutomationIds and must be excluded
    (#229).
    """
    raw = str(el.id) if el.id else None
    if raw and _TREE_ASSIGNED_RE.fullmatch(raw):
        return None
    return raw


def _build_identity_path(el: Any, parent_path: str, sibling_index: int) -> str:
    """Build a stable identity path for an element.

    Uses AutomationId when available, falls back to role + name + sibling
    index for disambiguation.
    """
    auto_id = _get_real_automation_id(el)
    if auto_id:
        segment = f"{el.role}:{auto_id}"
    else:
        name = el.name or ""
        segment = f"{el.role}:{name}[{sibling_index}]"
    return f"{parent_path}/{segment}"


def _hash_to_ref_number(path: str) -> int:
    """Hash an identity path to a deterministic ref number in [1, 9999]."""
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 9999 + 1


def assign_stable_refs(
    tree: Any,
    ui_element_cls: Type,
    element_obj_to_ref: Dict[int, str] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Traverse an element tree and assign stable ``eN`` refs.

    Each element receives a deterministic ref based on a hash of its identity
    path (AutomationId / role / name / parent chain / sibling position).  The
    same element in two consecutive snapshots of the same app will receive the
    same ``eN`` ref, even if other parts of the tree change.

    Parameters
    ----------
    tree:
        Root of the backend element tree.
    ui_element_cls:
        The ``UIElement`` dataclass to instantiate for each element.
    element_obj_to_ref:
        Optional dict that will be populated with ``id(el)`` → ``eN`` ref
        mappings.  Used by the ``find`` command to correlate search results
        back to snapshot refs.

    Returns
    -------
    tuple[dict[str, UIElement], dict[str, str]]
        ``(ui_map, ref_map)`` — the snapshot element map keyed by ``eN`` refs,
        and the ref → backend element id mapping for persistence.
    """
    ui_map: Dict[str, Any] = {}
    ref_map: Dict[str, str] = {}
    used_numbers: set[int] = set()

    def _resolve_number(path: str) -> int:
        """Get a unique ref number for the given path, handling collisions."""
        n = _hash_to_ref_number(path)
        while n in used_numbers:
            n = n % 9999 + 1
        used_numbers.add(n)
        return n

    def _walk(el: Any, identity_path: str, parent_ref: str | None) -> str:
        """DFS: assign stable ref, build UIElement, recurse into children."""
        auto_id = _get_real_automation_id(el)
        ref_num = _resolve_number(identity_path)
        ref = f"e{ref_num}"
        if element_obj_to_ref is not None:
            element_obj_to_ref[id(el)] = ref
        props = getattr(el, "properties", {})

        # Track sibling (role, identity) counts to disambiguate children
        # that share the same role + name under this parent.
        sibling_counts: dict[tuple[str, str], int] = {}
        child_refs: list[str] = []
        for child in el.children:
            child_auto = _get_real_automation_id(child)
            child_key = (child.role, child_auto) if child_auto else (child.role, child.name or "")
            idx = sibling_counts.get(child_key, 0)
            sibling_counts[child_key] = idx + 1
            child_path = _build_identity_path(child, identity_path, sibling_index=idx)
            child_refs.append(_walk(child, child_path, parent_ref=ref))

        ui_map[ref] = ui_element_cls(
            id=ref,
            element_id=f"element_{ref}",
            role=el.role,
            title=el.name,
            label=el.name,
            value=el.value,
            identifier=auto_id,
            frame=(el.x, el.y, el.width, el.height),
            is_actionable=getattr(el, "is_actionable", False),
            parent_id=parent_ref,
            children=child_refs,
            keyboard_shortcut=props.get("keyboard_shortcut"),
        )
        ref_map[ref] = el.id
        return ref

    root_path = _build_identity_path(tree, parent_path="", sibling_index=0)
    _walk(tree, root_path, parent_ref=None)
    return ui_map, ref_map
