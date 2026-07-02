"""UI element inspection — find elements and build element trees."""
from __future__ import annotations

from typing import Optional

from naturo.backends.base import ElementInfo
from naturo.backends.macos._peekaboo import PeekabooError


class ElementMixin:
    """UI element inspection via Peekaboo ``see`` output."""

    def get_element_value(
        self,
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        app: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> Optional[dict]:
        """Read element value — not yet supported on macOS.

        Returns:
            None (macOS does not yet support UIA pattern value reading).
        """
        return None

    def find_element(
        self,
        selector: str = "",
        window_title: str = None,
    ) -> Optional[ElementInfo]:
        """Find a UI element by selector.

        Args:
            selector: Element selector (role:name format).
            window_title: Application name to scope the search.

        Returns:
            ElementInfo if found, None otherwise.
        """
        # Use Peekaboo see --json to get element tree, then search
        args = ["see"]
        if window_title:
            args += ["--app", window_title]

        try:
            data = self._run(args, timeout=20)
        except PeekabooError:
            return None

        elements = data.get("data", {}).get("elements", data.get("elements", []))
        return self._search_elements(elements, selector)

    def _search_elements(
        self,
        elements: list[dict],
        selector: str,
    ) -> Optional[ElementInfo]:
        """Recursively search element tree for a matching element.

        Args:
            elements: List of element dicts from Peekaboo.
            selector: Search string (matches role:name or name).

        Returns:
            ElementInfo if found, None otherwise.
        """
        selector_lower = selector.lower()
        for el in elements:
            name = el.get("name", el.get("title", ""))
            role = el.get("role", el.get("type", ""))
            full = f"{role}:{name}"

            if (selector_lower in name.lower()
                    or selector_lower in full.lower()
                    or selector_lower in role.lower()):
                frame = el.get("frame", {})
                return ElementInfo(
                    id=str(el.get("id", el.get("peekabooId", ""))),
                    role=role,
                    name=name,
                    value=el.get("value"),
                    x=int(frame.get("x", el.get("x", 0))),
                    y=int(frame.get("y", el.get("y", 0))),
                    width=int(frame.get("width", el.get("width", 0))),
                    height=int(frame.get("height", el.get("height", 0))),
                    children=[],
                    properties=el,
                )

            # Search children
            children = el.get("children", [])
            if children:
                found = self._search_elements(children, selector)
                if found:
                    return found

        return None

    def get_element_tree(
        self,
        window_title: str = None,
        depth: int = 3,
        backend: str = "ax",
    ) -> Optional[ElementInfo]:
        """Get the UI element tree for a window.

        Args:
            window_title: Application name or window title.
            depth: Maximum depth to traverse.
            backend: Accessibility backend (ignored on macOS, always 'ax').

        Returns:
            Root ElementInfo with children populated.
        """
        args = ["see"]
        if window_title:
            args += ["--app", window_title]

        try:
            data = self._run(args, timeout=20)
        except PeekabooError:
            return None

        elements = data.get("data", {}).get("elements", data.get("elements", []))
        if not elements:
            return None

        return self._parse_element_tree(elements, depth)

    def _parse_element_tree(
        self,
        elements: list[dict],
        max_depth: int,
        current_depth: int = 0,
    ) -> Optional[ElementInfo]:
        """Parse Peekaboo element tree into ElementInfo hierarchy.

        Args:
            elements: List of element dicts.
            max_depth: Maximum depth to traverse.
            current_depth: Current recursion depth.

        Returns:
            Root ElementInfo, or None if elements is empty.
        """
        if not elements or current_depth > max_depth:
            return None

        # Build a virtual root containing all top-level elements
        children = []
        for el in elements:
            frame = el.get("frame", {})
            child_elements = el.get("children", [])
            parsed_children = []
            if child_elements and current_depth < max_depth:
                for c in child_elements:
                    parsed = self._parse_element_tree([c], max_depth, current_depth + 1)
                    if parsed:
                        parsed_children.append(parsed)

            children.append(ElementInfo(
                id=str(el.get("id", el.get("peekabooId", ""))),
                role=el.get("role", el.get("type", "")),
                name=el.get("name", el.get("title", "")),
                value=el.get("value"),
                x=int(frame.get("x", el.get("x", 0))),
                y=int(frame.get("y", el.get("y", 0))),
                width=int(frame.get("width", el.get("width", 0))),
                height=int(frame.get("height", el.get("height", 0))),
                children=parsed_children,
                properties=el,
            ))

        if len(children) == 1:
            return children[0]

        # Multiple top-level elements: wrap in a root
        return ElementInfo(
            id="root",
            role="Application",
            name="",
            value=None,
            x=0, y=0, width=0, height=0,
            children=children,
            properties={},
        )
