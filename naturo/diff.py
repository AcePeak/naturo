"""UI tree diff — compare element trees to detect changes.

Compares two :class:`ElementInfo` trees and reports additions, removals,
and modifications.  Useful for verifying that an interaction produced the
expected UI changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from naturo.backends.base import ElementInfo


@dataclass
class ElementChange:
    """A single change detected between two UI trees.

    Attributes:
        type: Change type — ``"added"``, ``"removed"``, or ``"modified"``.
        element_id: Element identifier.
        element_role: Element role (Button, Edit, etc.).
        element_name: Element name/label.
        old_value: Previous value (for ``"modified"``).
        new_value: New value (for ``"modified"``).
        path: Breadcrumb path to the element.
    """

    type: str  # "added", "removed", "modified"
    element_id: str
    element_role: str
    element_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    path: str = ""


@dataclass
class TreeDiff:
    """Result of comparing two UI element trees.

    Attributes:
        added: Elements present in ``after`` but not ``before``.
        removed: Elements present in ``before`` but not ``after``.
        modified: Elements present in both but with changed values.
        summary: Human-readable summary string.
    """

    added: list[ElementChange] = field(default_factory=list)
    removed: list[ElementChange] = field(default_factory=list)
    modified: list[ElementChange] = field(default_factory=list)
    summary: str = ""

    @property
    def total_changes(self) -> int:
        """Total number of changes across all categories."""
        return len(self.added) + len(self.removed) + len(self.modified)

    @property
    def has_changes(self) -> bool:
        """Whether any changes were detected."""
        return self.total_changes > 0

    def to_dict(self) -> dict:
        """Serialize to a dict for JSON output."""
        return {
            "added": [_change_to_dict(c) for c in self.added],
            "removed": [_change_to_dict(c) for c in self.removed],
            "modified": [_change_to_dict(c) for c in self.modified],
            "summary": self.summary,
            "total_changes": self.total_changes,
        }


def _change_to_dict(change: ElementChange) -> dict:
    """Serialize an ElementChange to dict."""
    d: dict = {
        "type": change.type,
        "element_id": change.element_id,
        "element_role": change.element_role,
        "element_name": change.element_name,
        "path": change.path,
    }
    if change.old_value is not None:
        d["old_value"] = change.old_value
    if change.new_value is not None:
        d["new_value"] = change.new_value
    return d


def _element_key(el: ElementInfo) -> str:
    """Create a unique key for matching elements across trees.

    Uses role + name as the primary key. Falls back to id if both are empty.
    """
    if el.role or el.name:
        return f"{el.role}:{el.name}"
    return f"id:{el.id}"


def _flatten_tree(
    root: ElementInfo, path_parts: list[str] | None = None,
) -> dict[str, tuple[ElementInfo, str]]:
    """Flatten an element tree into {key: (element, breadcrumb_path)}.

    When duplicate keys exist, appends a positional suffix to disambiguate.
    """
    if path_parts is None:
        path_parts = []

    result: dict[str, tuple[ElementInfo, str]] = {}
    _counters: dict[str, int] = {}

    def _walk(el: ElementInfo, current_path: list[str]) -> None:
        label = f"{el.role}:{el.name}" if el.name else (el.role or el.id)
        this_path = current_path + [label]
        path_str = " > ".join(this_path)

        key = _element_key(el)
        if key in result:
            # Disambiguate with counter
            count = _counters.get(key, 1)
            _counters[key] = count + 1
            key = f"{key}#{count}"
        result[key] = (el, path_str)

        for child in el.children:
            _walk(child, this_path)

    _walk(root, path_parts)
    return result


def diff_trees(before: ElementInfo, after: ElementInfo) -> TreeDiff:
    """Compare two UI element trees and return differences.

    Args:
        before: Element tree from the earlier state.
        after: Element tree from the later state.

    Returns:
        TreeDiff with added, removed, and modified elements.
    """
    before_flat = _flatten_tree(before)
    after_flat = _flatten_tree(after)

    before_keys = set(before_flat.keys())
    after_keys = set(after_flat.keys())

    added: list[ElementChange] = []
    removed: list[ElementChange] = []
    modified: list[ElementChange] = []

    # Added elements (in after but not in before)
    for key in sorted(after_keys - before_keys):
        el, path = after_flat[key]
        added.append(ElementChange(
            type="added",
            element_id=el.id,
            element_role=el.role,
            element_name=el.name,
            new_value=el.value,
            path=path,
        ))

    # Removed elements (in before but not in after)
    for key in sorted(before_keys - after_keys):
        el, path = before_flat[key]
        removed.append(ElementChange(
            type="removed",
            element_id=el.id,
            element_role=el.role,
            element_name=el.name,
            old_value=el.value,
            path=path,
        ))

    # Modified elements (in both, check for value changes)
    for key in sorted(before_keys & after_keys):
        before_el, before_path = before_flat[key]
        after_el, after_path = after_flat[key]

        if before_el.value != after_el.value:
            modified.append(ElementChange(
                type="modified",
                element_id=after_el.id,
                element_role=after_el.role,
                element_name=after_el.name,
                old_value=before_el.value,
                new_value=after_el.value,
                path=after_path,
            ))

    # Build summary
    parts: list[str] = []
    if added:
        parts.append(f"{len(added)} added")
    if removed:
        parts.append(f"{len(removed)} removed")
    if modified:
        parts.append(f"{len(modified)} modified")
    summary = ", ".join(parts) if parts else "No changes detected"

    return TreeDiff(
        added=added,
        removed=removed,
        modified=modified,
        summary=summary,
    )
