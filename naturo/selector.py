"""Unified Selector engine for naturo.

Provides a dual-format selector system (URI-style and XML-style) for
identifying UI elements by semantic properties rather than coordinates.

URI format:
    app://notepad.exe/Window[@name="Untitled"]/Edit[@automationid="15"]
    app://*/Button[@name="OK"]

XML format:
    <selector app="notepad.exe">
        <node role="Window" name="Untitled"/>
        <node role="Edit" automationid="15"/>
    </selector>

Both formats normalize to a common SelectorAST for resolution.
"""

from __future__ import annotations

import fnmatch
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Optional


# ── AST Definitions ───────────────────────────────────────────────────────────


@dataclass
class SelectorNode:
    """A single node in a selector path.

    Attributes:
        role: UI Automation control type (e.g., "Button", "Edit").
            Use "*" to match any role.
        attributes: Key-value attribute constraints. Supported keys:
            name, automationid, cls, idx, value.
            Values may contain wildcards (* and ?).
    """

    role: str = "*"
    attributes: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> Optional[str]:
        """Shortcut for the 'name' attribute."""
        return self.attributes.get("name")

    @property
    def automationid(self) -> Optional[str]:
        """Shortcut for the 'automationid' attribute."""
        return self.attributes.get("automationid")

    @property
    def cls(self) -> Optional[str]:
        """Shortcut for the 'cls' attribute."""
        return self.attributes.get("cls")

    @property
    def idx(self) -> Optional[int]:
        """Shortcut for the 'idx' attribute, parsed as int."""
        raw = self.attributes.get("idx")
        if raw is None:
            return None
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None

    def matches(self, role: str, attrs: dict[str, str],
                fuzzy: bool = False, fuzzy_threshold: float = 0.6) -> bool:
        """Check if a UI element matches this selector node.

        Args:
            role: The element's control type / role string.
            attrs: Dict of the element's attributes (name, automationid, etc.).
            fuzzy: If True, use approximate string matching for name.

        Returns:
            True if the element satisfies all constraints.
        """
        # Role check
        if self.role != "*" and not _wildcard_match(self.role, role):
            return False

        # Attribute checks
        for key, pattern in self.attributes.items():
            if key == "idx":
                # idx is positional — handled by the resolver, skip here
                continue
            actual = attrs.get(key, "")
            if fuzzy and key == "name":
                if not _fuzzy_match(pattern, actual, threshold=fuzzy_threshold):
                    return False
            else:
                if not _wildcard_match(pattern, actual):
                    return False
        return True


@dataclass
class SelectorAST:
    """Parsed selector — a chain of nodes to walk through the UI tree.

    Attributes:
        app: Application identifier (process name or "*" for any).
        nodes: Ordered list of selector nodes from root to target.
    """

    app: str = "*"
    nodes: list[SelectorNode] = field(default_factory=list)

    @property
    def target(self) -> Optional[SelectorNode]:
        """The final (leaf) node — the element we actually want."""
        return self.nodes[-1] if self.nodes else None

    def __repr__(self) -> str:
        nodes_repr = " / ".join(
            f"{n.role}[{', '.join(f'{k}={v!r}' for k, v in n.attributes.items())}]"
            for n in self.nodes
        )
        return f"SelectorAST(app={self.app!r}, nodes=[{nodes_repr}])"


# ── Parser ────────────────────────────────────────────────────────────────────


class SelectorParseError(Exception):
    """Raised when a selector string cannot be parsed."""
    pass


def parse(selector: str) -> SelectorAST:
    """Parse a selector string (auto-detecting URI vs XML format).

    Args:
        selector: A selector in URI or XML format.

    Returns:
        Parsed SelectorAST.

    Raises:
        SelectorParseError: If the selector cannot be parsed.
    """
    selector = selector.strip()
    if not selector:
        raise SelectorParseError("Empty selector")

    if selector.startswith("<"):
        return parse_xml(selector)
    elif selector.startswith("app://"):
        return parse_uri(selector)
    else:
        # Try as a simple "role:name" shorthand (backward compat)
        return _parse_simple(selector)


def parse_uri(selector: str) -> SelectorAST:
    """Parse a URI-style selector.

    Format: app://process.exe/Role[@attr="value"]/Role[@attr="value"]

    Args:
        selector: URI-format selector string.

    Returns:
        Parsed SelectorAST.

    Raises:
        SelectorParseError: On invalid syntax.
    """
    if not selector.startswith("app://"):
        raise SelectorParseError(
            f"URI selector must start with 'app://', got: {selector!r}"
        )

    body = selector[6:]  # strip "app://"
    if not body:
        raise SelectorParseError("Empty URI selector body")

    # Split on "/" but respect brackets — first segment is app
    segments = _split_uri_path(body)
    if not segments:
        raise SelectorParseError(f"No path segments in: {selector!r}")

    app = segments[0]
    nodes: list[SelectorNode] = []
    for seg in segments[1:]:
        nodes.append(_parse_uri_node(seg))

    if not nodes:
        raise SelectorParseError(
            f"URI selector must have at least one node after app: {selector!r}"
        )

    return SelectorAST(app=app, nodes=nodes)


def parse_xml(selector: str) -> SelectorAST:
    """Parse an XML-style selector.

    Format:
        <selector app="notepad.exe">
            <node role="Button" name="Save"/>
        </selector>

    Args:
        selector: XML-format selector string.

    Returns:
        Parsed SelectorAST.

    Raises:
        SelectorParseError: On invalid XML or missing elements.
    """
    try:
        root = ET.fromstring(selector)
    except ET.ParseError as exc:
        raise SelectorParseError(f"Invalid XML: {exc}") from exc

    if root.tag != "selector":
        raise SelectorParseError(
            f"Root element must be <selector>, got <{root.tag}>"
        )

    app = root.attrib.get("app", "*")
    nodes: list[SelectorNode] = []

    for child in root:
        if child.tag != "node":
            continue
        attrs = dict(child.attrib)
        role = attrs.pop("role", "*")
        nodes.append(SelectorNode(role=role, attributes=attrs))

    if not nodes:
        raise SelectorParseError("XML selector must contain at least one <node>")

    return SelectorAST(app=app, nodes=nodes)


def _parse_simple(selector: str) -> SelectorAST:
    """Parse a simple 'role:name' or bare 'name' selector.

    This provides backward compatibility with the existing find_element format.

    Args:
        selector: Simple selector string.

    Returns:
        Parsed SelectorAST with a single node.
    """
    if ":" in selector and not selector.startswith("app:"):
        parts = selector.split(":", 1)
        role = parts[0] if parts[0] else "*"
        attrs: dict[str, str] = {}
        if parts[1]:
            attrs["name"] = parts[1]
        return SelectorAST(app="*", nodes=[SelectorNode(role=role, attributes=attrs)])
    else:
        attrs = {"name": selector} if selector else {}
        return SelectorAST(app="*", nodes=[SelectorNode(role="*", attributes=attrs)])


# ── URI Parsing Helpers ───────────────────────────────────────────────────────


def _split_uri_path(body: str) -> list[str]:
    """Split URI path on '/' while respecting bracketed attribute sections.

    Args:
        body: The URI body after "app://".

    Returns:
        List of path segments.
    """
    segments: list[str] = []
    current: list[str] = []
    depth = 0

    for ch in body:
        if ch == "[":
            depth += 1
            current.append(ch)
        elif ch == "]":
            depth -= 1
            current.append(ch)
        elif ch == "/" and depth == 0:
            if current:
                segments.append("".join(current))
            current = []
        else:
            current.append(ch)

    if current:
        segments.append("".join(current))

    return segments


# Regex for parsing a single attribute: @key="value" or @key='value'
_ATTR_RE = re.compile(
    r"""@(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)')""",
    re.VERBOSE,
)


def _parse_uri_node(segment: str) -> SelectorNode:
    """Parse a single URI path segment into a SelectorNode.

    Format: Role[@attr="value", @attr2="value2"]

    Args:
        segment: A single path segment string.

    Returns:
        Parsed SelectorNode.

    Raises:
        SelectorParseError: On invalid segment syntax.
    """
    bracket_start = segment.find("[")
    if bracket_start == -1:
        # No attributes — just a role
        role = segment.strip()
        return SelectorNode(role=role if role else "*")

    role = segment[:bracket_start].strip()
    if not role:
        role = "*"

    # Extract bracket content
    if not segment.endswith("]"):
        raise SelectorParseError(
            f"Unclosed bracket in selector segment: {segment!r}"
        )
    bracket_content = segment[bracket_start + 1 : -1]

    attrs: dict[str, str] = {}
    for match in _ATTR_RE.finditer(bracket_content):
        key = match.group(1).lower()
        value = match.group(2) if match.group(2) is not None else match.group(3)
        attrs[key] = value

    if not attrs and bracket_content.strip():
        raise SelectorParseError(
            f"Could not parse attributes in: [{bracket_content}]"
        )

    return SelectorNode(role=role, attributes=attrs)


# ── Serialization (Builder) ───────────────────────────────────────────────────


class SelectorBuilder:
    """Builds selector strings from UI element properties.

    Generates the shortest unique selector path by analyzing element
    attributes and ancestor chain.

    Attribute priority for discrimination:
        automationid > name > cls + idx
    """

    def build_uri(self, element: dict[str, Any],
                  ancestors: Optional[list[dict[str, Any]]] = None,
                  app: str = "*") -> str:
        """Build a URI-style selector for a UI element.

        Args:
            element: Dict with keys: role, name, automationid, cls, etc.
            ancestors: Optional list of ancestor element dicts (root-first).
            app: Application identifier (process name).

        Returns:
            URI selector string like "app://notepad.exe/Button[@name='Save']".
        """
        nodes = self._build_node_chain(element, ancestors)
        parts = [f"app://{app}"]
        for node in nodes:
            parts.append(self._node_to_uri_segment(node))
        return "/".join(parts)

    def build_xml(self, element: dict[str, Any],
                  ancestors: Optional[list[dict[str, Any]]] = None,
                  app: str = "*") -> str:
        """Build an XML-style selector for a UI element.

        Args:
            element: Dict with keys: role, name, automationid, cls, etc.
            ancestors: Optional list of ancestor element dicts (root-first).
            app: Application identifier (process name).

        Returns:
            XML selector string.
        """
        nodes = self._build_node_chain(element, ancestors)
        parts = [f'<selector app="{_xml_escape(app)}">']
        for node in nodes:
            attr_strs = [f'role="{_xml_escape(node.role)}"']
            for key, val in node.attributes.items():
                attr_strs.append(f'{key}="{_xml_escape(val)}"')
            parts.append(f'  <node {" ".join(attr_strs)}/>')
        parts.append("</selector>")
        return "\n".join(parts)

    def _build_node_chain(self, element: dict[str, Any],
                          ancestors: Optional[list[dict[str, Any]]] = None
                          ) -> list[SelectorNode]:
        """Build the minimal node chain for an element.

        Includes ancestors only if they add discrimination value.

        Args:
            element: Target element dict.
            ancestors: Optional ancestor chain (root-first).

        Returns:
            List of SelectorNodes forming the selector path.
        """
        nodes: list[SelectorNode] = []

        # Include discriminating ancestors
        if ancestors:
            for anc in ancestors:
                node = self._element_to_node(anc)
                # Skip nodes that don't add discrimination value
                if node.automationid or node.name:
                    nodes.append(node)

        # Always include the target element
        nodes.append(self._element_to_node(element))
        return nodes

    def _element_to_node(self, element: dict[str, Any]) -> SelectorNode:
        """Convert an element dict to a SelectorNode.

        Uses attribute priority: automationid > name > cls + idx.

        Args:
            element: Element properties dict.

        Returns:
            SelectorNode with the most discriminating attributes.
        """
        role = element.get("role", "*")
        attrs: dict[str, str] = {}

        # Priority 1: automationid (most specific)
        aid = element.get("automationid", "")
        if aid:
            attrs["automationid"] = str(aid)

        # Priority 2: name
        name = element.get("name", "")
        if name:
            attrs["name"] = str(name)

        # Priority 3: cls (className) — only if no automationid and no name
        if not attrs:
            cls = element.get("cls", "") or element.get("className", "")
            if cls:
                attrs["cls"] = str(cls)
            # Add idx if available to disambiguate
            idx = element.get("idx")
            if idx is not None:
                attrs["idx"] = str(idx)

        return SelectorNode(role=role, attributes=attrs)

    @staticmethod
    def _node_to_uri_segment(node: SelectorNode) -> str:
        """Convert a SelectorNode to a URI path segment.

        Args:
            node: The selector node.

        Returns:
            URI segment string like 'Button[@name="Save"]'.
        """
        if not node.attributes:
            return node.role

        attr_parts = []
        for key, val in node.attributes.items():
            escaped = val.replace('"', '\\"')
            attr_parts.append(f'@{key}="{escaped}"')
        return f"{node.role}[{', '.join(attr_parts)}]"


# ── Resolver ──────────────────────────────────────────────────────────────────


@dataclass
class ResolvedElement:
    """Result of resolving a selector against the UI tree.

    Attributes:
        element: The matched element dict from the backend.
        selector: The selector that was resolved.
        match_quality: Quality of the match — "exact", "relaxed", or "fuzzy".
    """

    element: dict[str, Any]
    selector: str
    match_quality: str = "exact"


class SelectorResolver:
    """Resolves selectors to UI elements by walking the element tree.

    Resolution strategy (fallback chain):
        1. Exact — all attributes must match exactly (with wildcard support)
        2. Relaxed — drop idx constraints, match remaining attributes
        3. Fuzzy — use approximate string matching on name attribute

    The resolver operates on a tree of element dicts as returned by
    ``Backend.get_element_tree()``.
    """

    def resolve(self, ast: SelectorAST,
                element_tree: list[dict[str, Any]]) -> Optional[ResolvedElement]:
        """Resolve a selector AST against an element tree.

        Args:
            ast: Parsed selector AST.
            element_tree: List of root-level element dicts with 'children' lists.

        Returns:
            ResolvedElement if found, None otherwise.
        """
        # Strategy 1: Exact match
        result = self._walk_tree(ast.nodes, element_tree, fuzzy=False,
                                 drop_idx=False)
        if result is not None:
            return ResolvedElement(element=result, selector=str(ast),
                                  match_quality="exact")

        # Strategy 2: Relaxed (drop idx)
        has_idx = any(n.idx is not None for n in ast.nodes)
        if has_idx:
            result = self._walk_tree(ast.nodes, element_tree, fuzzy=False,
                                     drop_idx=True)
            if result is not None:
                return ResolvedElement(element=result, selector=str(ast),
                                      match_quality="relaxed")

        # Strategy 3: Fuzzy name matching
        has_name = any(n.name is not None for n in ast.nodes)
        if not has_name:
            return None
        result = self._walk_tree(ast.nodes, element_tree, fuzzy=True,
                                 drop_idx=True)
        if result is not None:
            return ResolvedElement(element=result, selector=str(ast),
                                  match_quality="fuzzy")

        return None

    def resolve_all(self, ast: SelectorAST,
                    element_tree: list[dict[str, Any]]) -> list[ResolvedElement]:
        """Resolve a selector AST and return all matching elements.

        Args:
            ast: Parsed selector AST.
            element_tree: List of root-level element dicts.

        Returns:
            List of all matching ResolvedElements.
        """
        results: list[ResolvedElement] = []
        self._collect_all(ast.nodes, 0, element_tree, results, str(ast))
        return results

    def exists(self, ast: SelectorAST,
               element_tree: list[dict[str, Any]]) -> bool:
        """Check if a selector matches any element in the tree.

        Args:
            ast: Parsed selector AST.
            element_tree: List of root-level element dicts.

        Returns:
            True if at least one element matches.
        """
        return self.resolve(ast, element_tree) is not None

    def _walk_tree(self, nodes: list[SelectorNode],
                   tree: list[dict[str, Any]],
                   fuzzy: bool = False,
                   drop_idx: bool = False) -> Optional[dict[str, Any]]:
        """Walk the element tree matching selector nodes in sequence.

        For single-node selectors, searches the entire tree depth-first.
        For multi-node selectors, matches nodes in order through the hierarchy.

        Args:
            nodes: List of selector nodes to match.
            tree: Current level of the element tree.
            fuzzy: Whether to use fuzzy matching.
            drop_idx: Whether to ignore idx constraints.

        Returns:
            The matched element dict, or None.
        """
        if not nodes:
            return None

        if len(nodes) == 1:
            # Single node — search entire tree depth-first
            return self._find_in_tree(nodes[0], tree, fuzzy, drop_idx)

        # Multi-node — match first node, then recurse into children
        target_node = nodes[0]
        remaining = nodes[1:]

        for element in tree:
            if self._element_matches(element, target_node, fuzzy, drop_idx):
                children = element.get("children", [])
                result = self._walk_tree(remaining, children, fuzzy, drop_idx)
                if result is not None:
                    return result

            # Also search children for the first node (skip intermediate)
            children = element.get("children", [])
            if children:
                result = self._walk_tree(nodes, children, fuzzy, drop_idx)
                if result is not None:
                    return result

        return None

    def _find_in_tree(self, node: SelectorNode,
                      tree: list[dict[str, Any]],
                      fuzzy: bool, drop_idx: bool) -> Optional[dict[str, Any]]:
        """Find first element matching a single node, depth-first.

        Args:
            node: The selector node to match.
            tree: Elements to search.
            fuzzy: Whether to use fuzzy matching.
            drop_idx: Whether to ignore idx constraints.

        Returns:
            Matched element dict or None.
        """
        idx_target = node.idx if not drop_idx else None
        current_idx = 0

        for element in tree:
            if self._element_matches(element, node, fuzzy, drop_idx):
                if idx_target is not None:
                    if current_idx == idx_target:
                        return element
                    current_idx += 1
                else:
                    return element

            # Recurse into children
            children = element.get("children", [])
            if children:
                result = self._find_in_tree(node, children, fuzzy, drop_idx)
                if result is not None:
                    return result

        return None

    def _collect_all(self, nodes: list[SelectorNode], node_idx: int,
                     tree: list[dict[str, Any]],
                     results: list[ResolvedElement],
                     selector_str: str) -> None:
        """Collect all elements matching the selector path.

        Args:
            nodes: Full list of selector nodes.
            node_idx: Current position in the node chain.
            tree: Current tree level.
            results: Accumulator for matched elements.
            selector_str: Original selector string for result metadata.
        """
        if node_idx >= len(nodes):
            return

        target_node = nodes[node_idx]
        is_last = node_idx == len(nodes) - 1

        for element in tree:
            if self._element_matches(element, target_node, fuzzy=False,
                                     drop_idx=False):
                if is_last:
                    results.append(ResolvedElement(
                        element=element,
                        selector=selector_str,
                        match_quality="exact",
                    ))
                else:
                    children = element.get("children", [])
                    self._collect_all(nodes, node_idx + 1, children,
                                      results, selector_str)

            # Search children for current node too (skip intermediate levels)
            children = element.get("children", [])
            if children:
                self._collect_all(nodes, node_idx, children,
                                  results, selector_str)

    @staticmethod
    def _element_matches(element: dict[str, Any], node: SelectorNode,
                         fuzzy: bool, drop_idx: bool) -> bool:
        """Check if a tree element matches a selector node.

        Args:
            element: Element dict with role, name, automationid, etc.
            node: Selector node to match against.
            fuzzy: Whether to use fuzzy name matching.
            drop_idx: Whether to skip idx constraint.

        Returns:
            True if the element matches.
        """
        attrs: dict[str, str] = {}
        for key in ("name", "automationid", "cls", "value"):
            val = element.get(key, "")
            if val:
                attrs[key] = str(val)

        # Build a modified node if we need to drop idx
        check_node = node
        if drop_idx and "idx" in node.attributes:
            filtered = {k: v for k, v in node.attributes.items() if k != "idx"}
            check_node = SelectorNode(role=node.role, attributes=filtered)

        return check_node.matches(
            role=element.get("role", ""),
            attrs=attrs,
            fuzzy=fuzzy,
        )


# ── String Matching Utilities ─────────────────────────────────────────────────


def _wildcard_match(pattern: str, text: str) -> bool:
    """Case-insensitive wildcard matching using fnmatch.

    Supports * (any chars) and ? (single char).

    Args:
        pattern: Pattern string, possibly with wildcards.
        text: Text to match against.

    Returns:
        True if text matches pattern.
    """
    return fnmatch.fnmatch(text.lower(), pattern.lower())


def _fuzzy_match(pattern: str, text: str, threshold: float = 0.7) -> bool:
    """Approximate string matching using normalized Levenshtein similarity.

    Args:
        pattern: Expected string.
        text: Actual string to compare.
        threshold: Minimum similarity ratio (0.0–1.0).

    Returns:
        True if similarity >= threshold.
    """
    if not pattern and not text:
        return True
    if not pattern or not text:
        return False

    # Try exact / wildcard first
    if _wildcard_match(pattern, text):
        return True

    # Levenshtein similarity
    similarity = _levenshtein_similarity(pattern.lower(), text.lower())
    return similarity >= threshold


def _levenshtein_similarity(s1: str, s2: str) -> float:
    """Compute normalized Levenshtein similarity between two strings.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        Similarity ratio between 0.0 and 1.0.
    """
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    max_len = max(len1, len2)
    if max_len == 0:
        return 1.0

    # Wagner-Fischer algorithm
    prev = list(range(len2 + 1))
    curr = [0] * (len2 + 1)

    for i in range(1, len1 + 1):
        curr[0] = i
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,       # deletion
                curr[j - 1] + 1,   # insertion
                prev[j - 1] + cost  # substitution
            )
        prev, curr = curr, prev

    distance = prev[len2]
    return 1.0 - (distance / max_len)


def _xml_escape(text: str) -> str:
    """Escape special characters for XML attribute values.

    Args:
        text: Raw text.

    Returns:
        XML-safe text.
    """
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))
