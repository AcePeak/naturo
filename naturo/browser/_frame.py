"""BrowserFrame — iframe interaction via CDP execution contexts.

Provides access to elements inside iframes through the Chrome DevTools
Protocol. Each ``BrowserFrame`` is scoped to a specific frame's execution
context, allowing find/click/type/evaluate operations within that frame.

Usage::

    from naturo.browser import BrowserPage

    page = BrowserPage(port=9222)
    page.navigate("https://example.com")

    # List all frames
    frames = page.frames()

    # Switch to an iframe by CSS selector
    frame = page.frame("iframe#payment")
    frame.find("#card-number").type("4111111111111111")

    # Switch by name or URL substring
    frame = page.frame(name="checkout")
    frame = page.frame(url="payment.example.com")

    # Nested iframes
    outer = page.frame("iframe.outer")
    inner = outer.frame("iframe.inner")
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from naturo.browser._page import BrowserPage

from naturo.cdp import CDPError

logger = logging.getLogger(__name__)


def _get_frame_tree(page: BrowserPage) -> Dict[str, Any]:
    """Retrieve the frame tree from CDP.

    Args:
        page: The BrowserPage to query.

    Returns:
        The ``Page.getFrameTree`` result dict.
    """
    result = page._cdp.send("Page.getFrameTree")
    return result.get("frameTree", {})


def _flatten_frame_tree(
    tree: Dict[str, Any],
    depth: int = 0,
) -> List[Dict[str, Any]]:
    """Flatten a frame tree into a list of frame info dicts.

    Args:
        tree: Frame tree node from CDP.
        depth: Current nesting depth.

    Returns:
        List of dicts with keys: ``id``, ``name``, ``url``,
        ``parentId``, ``depth``.
    """
    frames: List[Dict[str, Any]] = []
    frame = tree.get("frame", {})

    frames.append({
        "id": frame.get("id", ""),
        "name": frame.get("name", ""),
        "url": frame.get("url", ""),
        "parentId": frame.get("parentId", ""),
        "securityOrigin": frame.get("securityOrigin", ""),
        "depth": depth,
    })

    for child in tree.get("childFrames", []):
        frames.extend(_flatten_frame_tree(child, depth=depth + 1))

    return frames


class BrowserFrame:
    """A frame (iframe) context for CDP-based element interaction.

    Wraps a CDP frame and provides methods to find and interact with
    elements inside that frame. Operations are scoped to the frame's
    execution context.

    Args:
        page: The parent BrowserPage.
        frame_id: CDP frame ID.
        frame_name: Human-readable name of the frame.
        frame_url: URL of the frame.
    """

    def __init__(
        self,
        page: BrowserPage,
        frame_id: str,
        frame_name: str = "",
        frame_url: str = "",
    ) -> None:
        self._page = page
        self._frame_id = frame_id
        self._frame_name = frame_name
        self._frame_url = frame_url
        self._context_id: Optional[int] = None

    @property
    def frame_id(self) -> str:
        """The CDP frame ID."""
        return self._frame_id

    @property
    def name(self) -> str:
        """The frame's name attribute."""
        return self._frame_name

    @property
    def url(self) -> str:
        """The frame's current URL."""
        return self._frame_url

    def _ensure_context(self) -> int:
        """Get or create an execution context for this frame.

        Uses ``Page.createIsolatedWorld`` to get a context ID that can
        evaluate JavaScript within the frame.

        Returns:
            The execution context ID.

        Raises:
            CDPError: If context creation fails.
        """
        if self._context_id is not None:
            return self._context_id

        result = self._page._cdp.send("Page.createIsolatedWorld", {
            "frameId": self._frame_id,
            "worldName": "__naturo_frame_ctx__",
            "grantUniveralAccess": True,
        })
        self._context_id = result.get("executionContextId")
        if self._context_id is None:
            raise CDPError(
                f"Failed to create execution context for frame {self._frame_id}",
                code="FRAME_CONTEXT_ERROR",
            )
        return self._context_id

    def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript in this frame's context.

        Args:
            expression: JavaScript expression to evaluate.

        Returns:
            The evaluation result value.

        Raises:
            CDPError: If evaluation fails.
        """
        context_id = self._ensure_context()
        result = self._page._cdp.send("Runtime.evaluate", {
            "expression": expression,
            "contextId": context_id,
            "returnByValue": True,
            "awaitPromise": True,
        })

        remote_obj = result.get("result", {})

        if result.get("exceptionDetails"):
            exc_details = result["exceptionDetails"]
            text = exc_details.get("text", "JavaScript error")
            exception = exc_details.get("exception", {})
            desc = exception.get("description", text)
            raise CDPError(f"JavaScript error in frame: {desc}", code="JS_ERROR")

        return remote_obj.get("value")

    def find(self, selector: str) -> Any:
        """Find an element in this frame by CSS selector.

        Args:
            selector: CSS selector string.

        Returns:
            A BrowserElement scoped to this frame.

        Raises:
            RuntimeError: If element not found.
        """
        from naturo.browser._element import BrowserElement

        context_id = self._ensure_context()
        js = f"document.querySelector({json.dumps(selector)})"
        result = self._page._cdp.send("Runtime.evaluate", {
            "expression": js,
            "contextId": context_id,
            "returnByValue": False,
        })
        remote_obj = result.get("result", {})
        oid = remote_obj.get("objectId")
        if oid and remote_obj.get("subtype") != "null":
            return BrowserElement(
                self._page, oid,
                description=remote_obj.get("description", ""),
            )
        raise RuntimeError(f"Element not found in frame: {selector}")

    def find_all(self, selector: str) -> List[Any]:
        """Find all elements in this frame matching a CSS selector.

        Args:
            selector: CSS selector string.

        Returns:
            List of BrowserElement instances.
        """
        from naturo.browser._element import BrowserElement

        context_id = self._ensure_context()
        js = f"Array.from(document.querySelectorAll({json.dumps(selector)}))"
        result = self._page._cdp.send("Runtime.evaluate", {
            "expression": js,
            "contextId": context_id,
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

    def frame(
        self,
        selector: Optional[str] = None,
        name: Optional[str] = None,
        url: Optional[str] = None,
    ) -> BrowserFrame:
        """Get a nested iframe within this frame.

        Args:
            selector: CSS selector for the iframe element.
            name: Frame name attribute to match.
            url: URL substring to match.

        Returns:
            A BrowserFrame for the nested iframe.

        Raises:
            RuntimeError: If no matching frame found.
        """
        # Get child frames from the frame tree
        tree = _get_frame_tree(self._page)
        all_frames = _flatten_frame_tree(tree)

        # Find child frames of this frame
        child_frames = [f for f in all_frames if f["parentId"] == self._frame_id]

        if name is not None:
            for f in child_frames:
                if f["name"] == name:
                    return BrowserFrame(
                        self._page, f["id"],
                        frame_name=f["name"], frame_url=f["url"],
                    )
            raise RuntimeError(f"No child frame with name '{name}' in frame '{self._frame_name}'")

        if url is not None:
            for f in child_frames:
                if url in f["url"]:
                    return BrowserFrame(
                        self._page, f["id"],
                        frame_name=f["name"], frame_url=f["url"],
                    )
            raise RuntimeError(f"No child frame matching URL '{url}' in frame '{self._frame_name}'")

        if selector is not None:
            frame_info = self._resolve_frame_by_selector(selector, child_frames)
            if frame_info is not None:
                return BrowserFrame(
                    self._page, frame_info["id"],
                    frame_name=frame_info["name"],
                    frame_url=frame_info["url"],
                )
            raise RuntimeError(f"No child frame matching selector '{selector}'")

        raise RuntimeError("Specify selector, name, or url to identify the frame")

    def _resolve_frame_by_selector(
        self,
        selector: str,
        child_frames: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Resolve an iframe CSS selector to a frame info dict.

        Evaluates JS in this frame's context to find the iframe element
        and match it to a known child frame by src/name.

        Args:
            selector: CSS selector for the iframe element.
            child_frames: Known child frames from the frame tree.

        Returns:
            Matching frame info dict, or None.
        """
        # Get the iframe's name and src attributes
        js = f"""
        (() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el || el.tagName.toLowerCase() !== 'iframe') return null;
            return {{
                name: el.name || '',
                src: el.src || '',
            }};
        }})()
        """
        info = self.evaluate(js)
        if info is None:
            return None

        iframe_name = info.get("name", "")
        iframe_src = info.get("src", "")

        # Match by name first, then by URL
        for f in child_frames:
            if iframe_name and f["name"] == iframe_name:
                return f
            if iframe_src and iframe_src in f["url"]:
                return f
            if iframe_src and f["url"] in iframe_src:
                return f

        # If only one child frame, assume it matches
        if len(child_frames) == 1:
            return child_frames[0]

        return None

    @property
    def title(self) -> str:
        """Get the frame's document title.

        Returns:
            The document title string.
        """
        return self.evaluate("document.title") or ""

    def __repr__(self) -> str:
        name = self._frame_name or self._frame_id[:12]
        return f"<BrowserFrame name={name!r} url={self._frame_url!r}>"
