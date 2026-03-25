"""Element search and query — flexible UI element finding.

Supports fuzzy name matching, role filtering, actionable filtering,
and combined queries like ``role:Button name:Save`` or ``Button:*Save*``.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import List, Optional

from naturo.bridge import ElementInfo


@dataclass
class SearchResult:
    """A search result with the matched element and its breadcrumb path.

    Attributes:
        element: The matched ElementInfo.
        breadcrumb: List of (role, name) tuples from root to this element.
        breadcrumb_str: Human-readable breadcrumb string.
    """

    element: ElementInfo
    breadcrumb: List[tuple]
    breadcrumb_str: str = ""

    def __post_init__(self):
        if not self.breadcrumb_str and self.breadcrumb:
            parts = []
            for role, name in self.breadcrumb:
                label = f"{role}:{name}" if name else role
                parts.append(label)
            self.breadcrumb_str = " > ".join(parts)


def search_elements(
    root: ElementInfo,
    query: str,
    role_filter: Optional[str] = None,
    actionable_only: bool = False,
    max_results: int = 50,
) -> List[SearchResult]:
    """Search the element tree for elements matching the query.

    Query syntax:
        - Simple text: fuzzy match against element name (case-insensitive contains)
        - ``role:Button``: filter by role
        - ``name:Save``: filter by name (contains)
        - ``role:Button name:Save``: combined filters
        - ``Button:Save``: shorthand for role:Button name:Save
        - ``Button:*Save*``: wildcard glob pattern on name
        - ``*``: match all elements

    Args:
        root: Root element of the UI tree.
        query: Search query string.
        role_filter: Additional role filter (overrides role in query).
        actionable_only: If True, only return actionable elements.
        max_results: Maximum number of results to return.

    Returns:
        List of SearchResult objects, ordered by tree traversal order.
    """
    parsed_role, parsed_name = _parse_query(query)

    # Explicit role_filter overrides parsed role
    if role_filter:
        parsed_role = role_filter

    results: List[SearchResult] = []
    _search_recursive(root, parsed_role, parsed_name, actionable_only, [], results, max_results)
    return results


def _parse_query(query: str) -> tuple:
    """Parse a query string into (role_filter, name_filter) tuple.

    Returns:
        (role, name) where each can be None or a string pattern.
    """
    query = query.strip()
    if not query or query == "*":
        return (None, None)

    role = None
    name = None

    # Check for key:value pairs (role:Button name:Save)
    kv_pattern = re.compile(r'(role|name):(\S+)', re.IGNORECASE)
    matches = kv_pattern.findall(query)

    if matches:
        for key, value in matches:
            if key.lower() == "role":
                role = value
            elif key.lower() == "name":
                name = value
        return (role, name)

    # Check for Role:Name shorthand (e.g., Button:Save or Button:*Save*)
    if ":" in query:
        parts = query.split(":", 1)
        candidate_role = parts[0].strip()
        candidate_name = parts[1].strip()
        # Heuristic: if the left side looks like a role name (capitalized, no spaces)
        if candidate_role and candidate_role[0].isupper() and " " not in candidate_role:
            return (candidate_role, candidate_name if candidate_name else None)

    # Plain text: fuzzy name search
    return (None, query)


def _matches_name(element_name: str, pattern: str) -> bool:
    """Check if an element name matches a search pattern.

    Supports:
        - Simple substring match (case-insensitive)
        - Glob patterns with * and ?
    """
    if not pattern:
        return True
    if not element_name:
        return False

    # If pattern contains glob chars, use fnmatch
    if "*" in pattern or "?" in pattern:
        return fnmatch.fnmatch(element_name.lower(), pattern.lower())

    # Default: case-insensitive substring match
    return pattern.lower() in element_name.lower()


def _matches_role(element_role: str, role_filter: str) -> bool:
    """Check if an element role matches the filter (case-insensitive)."""
    if not role_filter:
        return True
    return element_role.lower() == role_filter.lower()


def _is_actionable(el: ElementInfo) -> bool:
    """Heuristic: determine if an element is likely actionable."""
    actionable_roles = {
        "button", "edit", "checkbox", "radiobutton", "combobox",
        "listitem", "menuitem", "tab", "link", "hyperlink",
        "slider", "spinbutton", "scrollbar", "treeitem",
    }
    return el.role.lower() in actionable_roles


def _search_recursive(
    el: ElementInfo,
    role_filter: Optional[str],
    name_filter: Optional[str],
    actionable_only: bool,
    path: List[tuple],
    results: List[SearchResult],
    max_results: int,
) -> None:
    """Recursively search the element tree."""
    if len(results) >= max_results:
        return

    current_path = path + [(el.role, el.name)]

    # Check match
    # Issue #281: when role_filter is not specified but name_filter is,
    # match against BOTH role and name (fuzzy search).
    if role_filter:
        role_match = _matches_role(el.role, role_filter)
        name_match = _matches_name(el.name, name_filter) if name_filter else True
        match_any = role_match and name_match
    elif name_filter:
        # Fuzzy all-fields search: match if name OR role OR value contains pattern
        role_match_fuzzy = _matches_name(el.role, name_filter)
        name_match_fuzzy = _matches_name(el.name, name_filter)
        value_match_fuzzy = _matches_name(el.value, name_filter) if el.value else False
        # At least one must match
        match_any = role_match_fuzzy or name_match_fuzzy or value_match_fuzzy
    else:
        match_any = True

    actionable_match = (not actionable_only) or _is_actionable(el)

    if match_any and actionable_match:
        # For "match all" queries (no filters), skip if both name and role empty
        if role_filter or name_filter or (el.name or el.role):
            results.append(SearchResult(element=el, breadcrumb=current_path))

    for child in el.children:
        _search_recursive(child, role_filter, name_filter, actionable_only, current_path, results, max_results)
