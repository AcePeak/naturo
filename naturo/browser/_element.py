"""BrowserElement — wraps a CDP DOM node for interaction.

Each BrowserElement holds a CDP ``Runtime.RemoteObject`` reference
(objectId) and provides methods to read properties, click, type, etc.
All DOM operations are performed via CDP commands on the associated page.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from naturo.browser._page import BrowserPage

logger = logging.getLogger(__name__)


class BrowserElement:
    """A single DOM element accessible via Chrome DevTools Protocol.

    Args:
        page: The parent BrowserPage that owns this element.
        object_id: CDP ``Runtime.RemoteObject.objectId``.
        backend_node_id: CDP backend node ID (optional, for DOM operations).
        description: Human-readable description of the element.
    """

    def __init__(
        self,
        page: BrowserPage,
        object_id: str,
        backend_node_id: int = 0,
        description: str = "",
    ) -> None:
        self._page = page
        self._object_id = object_id
        self._backend_node_id = backend_node_id
        self._description = description

    @property
    def object_id(self) -> str:
        """CDP RemoteObject ID for this element."""
        return self._object_id

    @property
    def text(self) -> str:
        """Get the textContent of this element.

        Returns:
            The text content string, or empty string if unavailable.
        """
        result = self._call_function("function() { return this.textContent || ''; }")
        return str(result) if result is not None else ""

    @property
    def inner_html(self) -> str:
        """Get the innerHTML of this element."""
        result = self._call_function("function() { return this.innerHTML || ''; }")
        return str(result) if result is not None else ""

    @property
    def outer_html(self) -> str:
        """Get the outerHTML of this element."""
        result = self._call_function("function() { return this.outerHTML || ''; }")
        return str(result) if result is not None else ""

    @property
    def tag_name(self) -> str:
        """Get the tag name (e.g. 'DIV', 'INPUT')."""
        result = self._call_function("function() { return this.tagName || ''; }")
        return str(result) if result is not None else ""

    @property
    def value(self) -> str:
        """Get the value property (for input/textarea/select elements)."""
        result = self._call_function("function() { return this.value || ''; }")
        return str(result) if result is not None else ""

    def attr(self, name: str) -> Optional[str]:
        """Get an attribute value.

        Args:
            name: Attribute name (e.g. ``"href"``, ``"class"``).

        Returns:
            Attribute value, or ``None`` if the attribute does not exist.
        """
        escaped = name.replace("\\", "\\\\").replace("'", "\\'")
        result = self._call_function(
            f"function() {{ return this.getAttribute('{escaped}'); }}"
        )
        return str(result) if result is not None else None

    def click(self, offset_x: int = 0, offset_y: int = 0) -> BrowserElement:
        """Click this element.

        Scrolls the element into view, calculates its center (or offset)
        coordinates, and dispatches a full mouse click sequence via CDP
        ``Input.dispatchMouseEvent``.

        Args:
            offset_x: Horizontal offset from element's top-left corner.
                When 0, clicks the element center.
            offset_y: Vertical offset from element's top-left corner.
                When 0, clicks the element center.

        Returns:
            self (for method chaining).
        """
        box = self._get_click_point(offset_x, offset_y)
        if box is None:
            raise RuntimeError("Cannot determine element position for click")

        x, y = box
        cdp = self._page._cdp
        for event_type in ("mousePressed", "mouseReleased"):
            cdp.send("Input.dispatchMouseEvent", {
                "type": event_type,
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1,
            })
        return self

    def hover(self) -> BrowserElement:
        """Move the mouse to this element's center.

        Returns:
            self (for method chaining).
        """
        box = self._get_click_point(0, 0)
        if box is None:
            raise RuntimeError("Cannot determine element position for hover")

        x, y = box
        self._page._cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": x,
            "y": y,
        })
        return self

    def type(self, text: str, clear_first: bool = False) -> BrowserElement:
        """Type text into this element.

        Focuses the element, optionally clears it, then dispatches
        key events for each character.

        Args:
            text: Text to type.
            clear_first: If True, clear the element value before typing.

        Returns:
            self (for method chaining).
        """
        self._call_function("function() { this.focus(); }")

        if clear_first:
            self._call_function("function() { this.value = ''; }")

        cdp = self._page._cdp
        for char in text:
            cdp.send("Input.dispatchKeyEvent", {"type": "keyDown", "text": char})
            cdp.send("Input.dispatchKeyEvent", {"type": "keyUp", "text": char})
        return self

    def select(self, value: str) -> BrowserElement:
        """Select an option in a ``<select>`` dropdown.

        Sets the value and dispatches ``change`` + ``input`` events so
        frameworks (React, Vue, etc.) detect the change.

        Args:
            value: The ``value`` attribute of the ``<option>`` to select.

        Returns:
            self (for method chaining).

        Raises:
            RuntimeError: If no matching option is found.
        """
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        result = self._call_function(f"""function() {{
            var opt = Array.from(this.options).find(o => o.value === '{escaped}');
            if (!opt) {{
                opt = Array.from(this.options).find(
                    o => o.textContent.trim() === '{escaped}'
                );
            }}
            if (!opt) return 'NOT_FOUND';
            this.value = opt.value;
            this.dispatchEvent(new Event('change', {{bubbles: true}}));
            this.dispatchEvent(new Event('input', {{bubbles: true}}));
            return opt.value;
        }}""")
        if result == "NOT_FOUND":
            raise RuntimeError(
                f"No <option> with value or text '{value}' found in <select>"
            )
        return self

    def scroll_into_view(self) -> BrowserElement:
        """Scroll this element into the viewport.

        Returns:
            self (for method chaining).
        """
        self._call_function(
            "function() { this.scrollIntoView({block: 'center', inline: 'center'}); }"
        )
        return self

    def find(self, selector: str) -> BrowserElement:
        """Find a child element matching the selector.

        Args:
            selector: CSS/XPath/text selector (auto-detected).

        Returns:
            BrowserElement for the first match.

        Raises:
            RuntimeError: If no matching element is found.
        """
        from naturo.browser._selectors import parse_selector, SelectorType

        parsed = parse_selector(selector)
        if parsed.type == SelectorType.CSS:
            escaped = parsed.expression.replace("\\", "\\\\").replace("'", "\\'")
            result = self._call_function_returning_element(
                f"function() {{ return this.querySelector('{escaped}'); }}"
            )
        else:
            result = self._page._find_within(self, parsed)

        if result is None:
            raise RuntimeError(f"No element found for selector: {selector}")
        return result

    def find_all(self, selector: str) -> List[BrowserElement]:
        """Find all child elements matching the selector.

        Args:
            selector: CSS/XPath/text selector (auto-detected).

        Returns:
            List of matching BrowserElement instances.
        """
        from naturo.browser._selectors import parse_selector, SelectorType

        parsed = parse_selector(selector)
        if parsed.type == SelectorType.CSS:
            escaped = parsed.expression.replace("\\", "\\\\").replace("'", "\\'")
            return self._call_function_returning_elements(
                f"function() {{ return Array.from(this.querySelectorAll('{escaped}')); }}"
            )
        return self._page._find_all_within(self, parsed)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _call_function(self, function_declaration: str) -> Any:
        """Call a JS function with `this` bound to this element.

        Args:
            function_declaration: JavaScript function source.

        Returns:
            The function's return value (primitive).
        """
        result = self._page._cdp.send("Runtime.callFunctionOn", {
            "objectId": self._object_id,
            "functionDeclaration": function_declaration,
            "returnByValue": True,
        })
        value = result.get("result", {}).get("value")
        return value

    def _call_function_returning_element(
        self, function_declaration: str
    ) -> Optional[BrowserElement]:
        """Call a JS function that returns a DOM element.

        Args:
            function_declaration: JavaScript function source.

        Returns:
            BrowserElement wrapping the returned node, or None.
        """
        result = self._page._cdp.send("Runtime.callFunctionOn", {
            "objectId": self._object_id,
            "functionDeclaration": function_declaration,
            "returnByValue": False,
        })
        remote_obj = result.get("result", {})
        oid = remote_obj.get("objectId")
        if oid and remote_obj.get("subtype") != "null":
            return BrowserElement(
                self._page, oid,
                description=remote_obj.get("description", ""),
            )
        return None

    def _call_function_returning_elements(
        self, function_declaration: str
    ) -> List[BrowserElement]:
        """Call a JS function that returns an array of DOM elements.

        Args:
            function_declaration: JavaScript function source.

        Returns:
            List of BrowserElement instances.
        """
        result = self._page._cdp.send("Runtime.callFunctionOn", {
            "objectId": self._object_id,
            "functionDeclaration": function_declaration,
            "returnByValue": False,
        })
        remote_obj = result.get("result", {})
        oid = remote_obj.get("objectId")
        if not oid:
            return []

        props = self._page._cdp.send("Runtime.getProperties", {
            "objectId": oid,
            "ownProperties": True,
        })
        elements = []
        for prop in props.get("result", []):
            if prop.get("name", "").isdigit():
                val = prop.get("value", {})
                val_oid = val.get("objectId")
                if val_oid:
                    elements.append(BrowserElement(
                        self._page, val_oid,
                        description=val.get("description", ""),
                    ))
        return elements

    def _is_displayed(self) -> bool:
        """Return whether this element is currently rendered and visible.

        Visibility here means the documented :meth:`BrowserPage.wait_for`
        contract: the node is in the document, is not ``display:none`` /
        ``visibility:hidden`` / ``visibility:collapse``, and has a non-zero
        layout box. This deliberately does **not** reuse
        :meth:`_get_click_point`, whose ``getBoundingClientRect`` fallback
        returns a valid all-zeros point ``(0, 0)`` for an unrendered element
        (the click-path quirk tracked in #1083) and so cannot distinguish a
        hidden node from a visible one.

        Returns:
            True if the element is connected and visibly rendered, else False.
        """
        result = self._call_function(
            "function() {"
            "  if (!this.isConnected) { return false; }"
            "  var style = window.getComputedStyle(this);"
            "  if (style.display === 'none'"
            "      || style.visibility === 'hidden'"
            "      || style.visibility === 'collapse') { return false; }"
            "  var rect = this.getBoundingClientRect();"
            "  return rect.width > 0 && rect.height > 0;"
            "}"
        )
        return bool(result)

    def _get_click_point(
        self, offset_x: int = 0, offset_y: int = 0
    ) -> Optional[tuple[float, float]]:
        """Get the click coordinates for this element, in top-document space.

        Scrolls the element into view, then resolves its position with CDP
        ``DOM.getContentQuads``, whose vertices are in **top-level viewport** CSS
        pixels at any iframe depth — the same coordinate space
        ``Input.dispatchMouseEvent`` uses. This is what lets a click/hover land
        on an element nested inside one or more iframes; a JS
        ``getBoundingClientRect`` is frame-relative and would point at the wrong
        spot in the top document (#1080).

        Falls back to ``getBoundingClientRect`` only when the node exposes no
        content quad (e.g. an unrendered or zero-area box) — that path is
        already correct for top-level elements and is the best available
        estimate when no layout box exists.

        Args:
            offset_x: X offset from top-left (0 = center).
            offset_y: Y offset from top-left (0 = center).

        Returns:
            (x, y) top-document coordinates, or None if no box model is
            available at all.
        """
        self.scroll_into_view()

        quad = self._content_quad()
        if quad is not None:
            xs = quad[0::2]
            ys = quad[1::2]
            if offset_x == 0 and offset_y == 0:
                return (sum(xs) / 4.0, sum(ys) / 4.0)
            # Offsets are measured from the element's top-left corner, which is
            # the first quad vertex (top-left, top-right, bottom-right,
            # bottom-left order per the CDP spec).
            return (xs[0] + offset_x, ys[0] + offset_y)

        # Fallback: no content quad (unrendered/zero-area). getBoundingClientRect
        # is frame-relative, but for a top-level element it coincides with the
        # dispatch coordinate space, and it is the only estimate left here.
        box = self._call_function(
            "function() {"
            "  var r = this.getBoundingClientRect();"
            "  return {x: r.x, y: r.y, width: r.width, height: r.height};"
            "}"
        )
        if not box or not isinstance(box, dict):
            return None

        if offset_x == 0 and offset_y == 0:
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
        else:
            x = box["x"] + offset_x
            y = box["y"] + offset_y

        return (x, y)

    def _content_quad(self) -> Optional[List[float]]:
        """Return this element's first content quad in top-document CSS pixels.

        Uses CDP ``DOM.getContentQuads``, which reports quad vertices relative
        to the top-level viewport regardless of how deeply the node is nested in
        iframes — so the result is directly usable as
        ``Input.dispatchMouseEvent`` coordinates.

        Returns:
            The first quad as ``[x1, y1, x2, y2, x3, y3, x4, y4]``, or ``None``
            when the node has no layout box (CDP raises) or returns no quads.
        """
        try:
            result = self._page._cdp.send(
                "DOM.getContentQuads", {"objectId": self._object_id}
            )
        except Exception as exc:
            # No layout box (display:none, detached, zero-area) — CDP raises
            # "could not compute content quads". Caller falls back gracefully.
            logger.debug("getContentQuads failed for %r: %s", self, exc)
            return None
        quads = result.get("quads") or []
        if not quads:
            return None
        return [float(v) for v in quads[0]]

    def __repr__(self) -> str:
        desc = self._description or self._object_id[:20]
        return f"<BrowserElement {desc}>"
