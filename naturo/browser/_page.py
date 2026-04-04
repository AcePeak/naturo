"""BrowserPage — high-level CDP page abstraction.

Wraps :class:`naturo.cdp.CDPClient` to provide a user-friendly API for
browser automation: navigate, find elements, click, type, wait, etc.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from naturo.browser._frame import BrowserFrame
    from naturo.browser._network import NetworkMonitor

from naturo.cdp import CDPClient, CDPError, CDPConnectionError
from naturo.browser._element import BrowserElement
from naturo.browser._selectors import (
    ParsedSelector,
    parse_selector,
    to_cdp_expression,
    to_cdp_expression_all,
)

logger = logging.getLogger(__name__)


class BrowserPage:
    """High-level browser page for CDP-based automation.

    Connects to a running Chrome/Chromium instance via the DevTools
    Protocol and provides methods for navigation, element interaction,
    and page inspection.

    Args:
        port: CDP debug port (default 9222).
        host: CDP host (default ``localhost``).
        tab_index: Which tab to connect to (default 0 = first tab).
        timeout: Default timeout in seconds for operations.
        profile: Chrome profile name. When provided, automatically
            launches Chrome with this profile via :func:`launch_chrome`.
        headless: Run Chrome in headless mode (only when *profile* is set).
        stealth: Apply anti-detection flags (only when *profile* is set).
        chrome_path: Explicit Chrome binary path (only when *profile* is set).

    Example::

        page = BrowserPage(port=9222)
        page.navigate("https://example.com")
        page.find("#search").type("hello")
        page.find("button.submit").click()
        print(page.title)
        page.close()

    Auto-launch example::

        page = BrowserPage(profile="xhs-account1")
        page.navigate("https://www.xiaohongshu.com/explore")
    """

    def __init__(
        self,
        port: int = 9222,
        host: str = "localhost",
        tab_index: int = 0,
        timeout: float = 30.0,
        profile: Optional[str] = None,
        headless: bool = False,
        stealth: bool = False,
        chrome_path: Optional[str] = None,
    ) -> None:
        self._chrome_process = None
        self._timeout = timeout

        if profile is not None:
            from naturo.browser._launcher import launch_chrome
            extra_args = None
            if stealth:
                from naturo.browser._stealth import STEALTH_FLAGS
                extra_args = list(STEALTH_FLAGS)
            self._chrome_process = launch_chrome(
                port=port,
                headless=headless,
                profile=profile,
                extra_args=extra_args,
                chrome_path=chrome_path,
                timeout=timeout,
            )
            port = self._chrome_process.port

        self._cdp = CDPClient(host=host, port=port, timeout=timeout)
        self._connect(tab_index)

    def _connect(self, tab_index: int = 0) -> None:
        """Connect to a browser tab via WebSocket.

        Args:
            tab_index: Index of the tab to connect to.

        Raises:
            CDPConnectionError: If no tabs are available or connection fails.
        """
        tabs = self._cdp.list_tabs()
        if not tabs:
            raise CDPConnectionError("No browser tabs found")
        if tab_index >= len(tabs):
            raise CDPConnectionError(
                f"Tab index {tab_index} out of range (only {len(tabs)} tabs open)"
            )
        tab_id = tabs[tab_index]["id"]
        self._cdp.connect(tab_id)
        logger.info("Connected to tab: %s", tabs[tab_index].get("title", tab_id))

    @property
    def url(self) -> str:
        """Get the current page URL."""
        result = self._cdp.evaluate("window.location.href")
        return str(result) if result else ""

    @property
    def title(self) -> str:
        """Get the current page title."""
        result = self._cdp.evaluate("document.title")
        return str(result) if result else ""

    @property
    def network(self) -> NetworkMonitor:
        """Lazy-initialized network monitor for this page.

        Returns:
            :class:`~naturo.browser._network.NetworkMonitor` instance.
        """
        if not hasattr(self, "_network"):
            from naturo.browser._network import NetworkMonitor
            self._network = NetworkMonitor(self._cdp)
        return self._network

    # ── Navigation ────────────────────────────────────────────────────────

    def navigate(self, url: str, wait_until: str = "load") -> None:
        """Navigate to a URL and wait for the page to load.

        Args:
            url: The URL to navigate to.
            wait_until: Wait strategy: ``"load"`` (default), ``"domcontentloaded"``,
                or ``"networkidle"``.
        """
        self._cdp.send("Page.enable")
        self._cdp.send("Page.navigate", {"url": url})

        if wait_until == "domcontentloaded":
            self._wait_for_event("Page.domContentEventFired")
        elif wait_until == "networkidle":
            self._wait_for_network_idle()
        else:
            self._wait_for_event("Page.loadEventFired")

    def reload(self) -> None:
        """Reload the current page."""
        self._cdp.send("Page.enable")
        self._cdp.send("Page.reload")
        self._wait_for_event("Page.loadEventFired")

    def back(self) -> None:
        """Navigate back in history."""
        self._cdp.evaluate("window.history.back()")

    def forward(self) -> None:
        """Navigate forward in history."""
        self._cdp.evaluate("window.history.forward()")

    # ── Element finding ───────────────────────────────────────────────────

    def find(self, selector: str) -> BrowserElement:
        """Find the first element matching a selector.

        Args:
            selector: CSS, XPath, or text selector (auto-detected).
                Use ``css:``, ``xpath:``, or ``text:`` prefix for explicit type.

        Returns:
            BrowserElement for the first match.

        Raises:
            RuntimeError: If no matching element is found.
        """
        parsed = parse_selector(selector)
        element = self._resolve_element(parsed)
        if element is None:
            raise RuntimeError(f"No element found for selector: {selector}")
        return element

    def find_all(self, selector: str) -> List[BrowserElement]:
        """Find all elements matching a selector.

        Args:
            selector: CSS, XPath, or text selector (auto-detected).

        Returns:
            List of BrowserElement instances (may be empty).
        """
        parsed = parse_selector(selector)
        return self._resolve_elements(parsed)

    # ── Waiting ───────────────────────────────────────────────────────────

    def wait_for(
        self,
        selector: str,
        timeout: Optional[float] = None,
        state: str = "attached",
    ) -> BrowserElement:
        """Wait for an element matching the selector to appear.

        Polls the DOM until the element is found or the timeout expires.

        Args:
            selector: CSS/XPath/text selector.
            timeout: Max wait time in seconds (default: page timeout).
            state: Expected state: ``"attached"`` (in DOM), ``"visible"``
                (in DOM and has non-zero size), ``"hidden"`` (not visible),
                ``"detached"`` (not in DOM).

        Returns:
            The matching BrowserElement.

        Raises:
            TimeoutError: If the element does not reach the expected state
                within the timeout.
        """
        if timeout is None:
            timeout = self._timeout

        parsed = parse_selector(selector)
        deadline = time.monotonic() + timeout
        poll_interval = 0.1

        while True:
            element = self._resolve_element(parsed)
            if state in ("attached", "visible") and element is not None:
                if state == "visible":
                    box = element._get_click_point()
                    if box is not None:
                        return element
                else:
                    return element
            elif state == "detached" and element is None:
                # Return a dummy element since the element is gone
                return BrowserElement(self, "", description="<detached>")
            elif state == "hidden":
                if element is None:
                    return BrowserElement(self, "", description="<hidden>")
                box = element._get_click_point()
                if box is None:
                    return element

            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Timeout waiting for '{selector}' to be {state} "
                    f"(waited {timeout}s)"
                )
            time.sleep(poll_interval)
            # Exponential backoff up to 1s
            poll_interval = min(poll_interval * 1.5, 1.0)

    def wait_for_load(self, timeout: Optional[float] = None) -> None:
        """Wait for the page load event.

        Args:
            timeout: Max wait time in seconds.
        """
        self._cdp.send("Page.enable")
        self._wait_for_event("Page.loadEventFired", timeout=timeout)

    def wait_for_navigation(self, timeout: Optional[float] = None) -> str:
        """Wait for a navigation to complete (URL change + page load).

        Captures the current URL, then polls until the URL changes and
        ``document.readyState`` reaches ``"complete"``.

        Args:
            timeout: Max wait time in seconds (default: page timeout).

        Returns:
            The new URL after navigation.

        Raises:
            TimeoutError: If no navigation occurs within the timeout.
        """
        if timeout is None:
            timeout = self._timeout
        deadline = time.monotonic() + timeout
        poll_interval = 0.1

        original_url = self.url

        while time.monotonic() < deadline:
            current_url = self.url
            if current_url != original_url:
                # URL changed — wait for load to complete
                try:
                    state = self._cdp.evaluate("document.readyState")
                    if state == "complete":
                        return current_url
                except CDPError:
                    pass
            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 1.0)

        raise TimeoutError(
            f"Timeout waiting for navigation from {original_url!r} "
            f"(waited {timeout}s)"
        )

    def wait_for_url(
        self,
        pattern: str,
        *,
        regex: bool = False,
        timeout: Optional[float] = None,
    ) -> str:
        """Wait until the page URL matches a pattern.

        Args:
            pattern: Substring to match (or regex if *regex* is True).
            regex: If True, treat *pattern* as a regular expression.
            timeout: Max wait time in seconds (default: page timeout).

        Returns:
            The matching URL.

        Raises:
            TimeoutError: If the URL does not match within the timeout.
        """
        if timeout is None:
            timeout = self._timeout
        deadline = time.monotonic() + timeout
        poll_interval = 0.1
        compiled = re.compile(pattern) if regex else None

        while time.monotonic() < deadline:
            current_url = self.url
            if compiled is not None:
                if compiled.search(current_url):
                    return current_url
            elif pattern in current_url:
                return current_url
            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 1.0)

        raise TimeoutError(
            f"Timeout waiting for URL to match {pattern!r} "
            f"(waited {timeout}s)"
        )

    def wait_for_function(
        self,
        expression: str,
        *,
        timeout: Optional[float] = None,
    ) -> Any:
        """Wait until a JavaScript expression returns a truthy value.

        Polls the expression repeatedly until it evaluates to a truthy
        result or the timeout expires.

        Args:
            expression: JavaScript expression to evaluate.
            timeout: Max wait time in seconds (default: page timeout).

        Returns:
            The truthy result of the expression.

        Raises:
            TimeoutError: If the expression does not become truthy
                within the timeout.
        """
        if timeout is None:
            timeout = self._timeout
        deadline = time.monotonic() + timeout
        poll_interval = 0.1

        while time.monotonic() < deadline:
            try:
                result = self._cdp.evaluate(expression)
                if result:
                    return result
            except CDPError:
                pass
            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 1.0)

        raise TimeoutError(
            f"Timeout waiting for expression to be truthy: {expression!r} "
            f"(waited {timeout}s)"
        )

    def wait_for_network_idle(
        self,
        idle_time: float = 0.5,
        timeout: Optional[float] = None,
    ) -> None:
        """Wait until network activity has settled.

        Uses ``performance.getEntriesByType('resource')`` to detect when
        no new resources have been fetched for *idle_time* seconds.

        Args:
            idle_time: Seconds of network silence to consider "idle".
            timeout: Max wait time in seconds (default: page timeout).

        Raises:
            TimeoutError: If the network does not become idle within
                the timeout.
        """
        if timeout is None:
            timeout = self._timeout
        deadline = time.monotonic() + timeout

        last_count: Optional[int] = None
        stable_since: Optional[float] = None

        while time.monotonic() < deadline:
            try:
                count = self._cdp.evaluate(
                    "performance.getEntriesByType('resource').length"
                )
                count = int(count) if count is not None else 0
            except (CDPError, TypeError, ValueError):
                count = 0

            now = time.monotonic()
            if last_count is not None and count == last_count:
                if stable_since is None:
                    stable_since = now
                elif now - stable_since >= idle_time:
                    return
            else:
                stable_since = None
                last_count = count

            time.sleep(0.1)

        raise TimeoutError(
            f"Timeout waiting for network idle (waited {timeout}s)"
        )

    # ── Page operations ───────────────────────────────────────────────────

    def screenshot(self, path: str, full_page: bool = False) -> str:
        """Take a screenshot of the page.

        Args:
            path: File path to save the screenshot (PNG).
            full_page: If True, capture the full scrollable page.

        Returns:
            The path where the screenshot was saved.
        """
        params: Dict[str, Any] = {"format": "png"}
        if full_page:
            # Get full page dimensions
            metrics = self._cdp.send("Page.getLayoutMetrics")
            content_size = metrics.get("contentSize", {})
            params["clip"] = {
                "x": 0,
                "y": 0,
                "width": content_size.get("width", 1920),
                "height": content_size.get("height", 1080),
                "scale": 1,
            }

        result = self._cdp.send("Page.captureScreenshot", **params)
        data = result.get("data", "")

        import base64
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))

        return path

    def evaluate(self, expression: str) -> Any:
        """Evaluate a JavaScript expression in the page context.

        Args:
            expression: JavaScript expression to evaluate.

        Returns:
            The evaluation result.
        """
        return self._cdp.evaluate(expression)

    # ── Frame (iframe) support ───────────────────────────────────────────

    def frames(self) -> List[Dict[str, Any]]:
        """List all frames (including the main frame and iframes).

        Returns:
            List of dicts with keys: ``id``, ``name``, ``url``,
            ``parentId``, ``depth``.
        """
        from naturo.browser._frame import _get_frame_tree, _flatten_frame_tree
        tree = _get_frame_tree(self)
        return _flatten_frame_tree(tree)

    def frame(
        self,
        selector: Optional[str] = None,
        name: Optional[str] = None,
        url: Optional[str] = None,
    ) -> "BrowserFrame":
        """Get a frame (iframe) for scoped element interaction.

        Identify the target frame by CSS selector, name attribute, or
        URL substring. Returns a :class:`BrowserFrame` whose ``find``,
        ``evaluate``, ``find_all`` methods operate inside that frame.

        Args:
            selector: CSS selector for the ``<iframe>`` element.
            name: Frame ``name`` attribute to match.
            url: URL substring to match against the frame's URL.

        Returns:
            A :class:`BrowserFrame` scoped to the target iframe.

        Raises:
            RuntimeError: If no matching frame is found.

        Example::

            frame = page.frame("iframe#payment")
            frame.find("#card-number").type("4111111111111111")
        """
        from naturo.browser._frame import (
            BrowserFrame,
            _get_frame_tree,
            _flatten_frame_tree,
        )

        tree = _get_frame_tree(self)
        all_frames = _flatten_frame_tree(tree)

        # Main frame is depth 0; look in child frames (depth >= 1)
        main_id = all_frames[0]["id"] if all_frames else ""
        child_frames = [f for f in all_frames if f["id"] != main_id]

        if name is not None:
            for f in child_frames:
                if f["name"] == name:
                    return BrowserFrame(
                        self, f["id"],
                        frame_name=f["name"], frame_url=f["url"],
                    )
            raise RuntimeError(f"No frame with name '{name}'")

        if url is not None:
            for f in child_frames:
                if url in f["url"]:
                    return BrowserFrame(
                        self, f["id"],
                        frame_name=f["name"], frame_url=f["url"],
                    )
            raise RuntimeError(f"No frame matching URL '{url}'")

        if selector is not None:
            # Evaluate JS to find the iframe element and match to a frame
            main_frame = BrowserFrame(self, main_id)
            info = main_frame._resolve_frame_by_selector(selector, child_frames)
            if info is not None:
                return BrowserFrame(
                    self, info["id"],
                    frame_name=info["name"], frame_url=info["url"],
                )
            raise RuntimeError(f"No frame matching selector '{selector}'")

        raise RuntimeError("Specify selector, name, or url to identify the frame")

    # ── Tab management ────────────────────────────────────────────────────

    def tabs(self) -> List[Dict[str, str]]:
        """List all open browser tabs.

        Returns:
            List of dicts with ``id``, ``title``, ``url`` keys.
        """
        return self._cdp.list_tabs()

    def switch_tab(self, tab_id: str) -> None:
        """Switch to a different browser tab.

        Args:
            tab_id: Tab ID from :meth:`tabs`.
        """
        self._cdp.close()
        self._cdp.connect(tab_id)

    # ── Scrolling ─────────────────────────────────────────────────────────

    def scroll_to_bottom(self) -> None:
        """Scroll the page to the bottom."""
        self._cdp.evaluate(
            "window.scrollTo(0, document.body.scrollHeight)"
        )

    def scroll_to_top(self) -> None:
        """Scroll the page to the top."""
        self._cdp.evaluate("window.scrollTo(0, 0)")

    def scroll_by(self, pixels: int) -> None:
        """Scroll the page by a number of pixels.

        Args:
            pixels: Positive scrolls down, negative scrolls up.
        """
        self._cdp.evaluate(f"window.scrollBy(0, {pixels})")

    def scroll_to_element(self, selector: str) -> None:
        """Scroll an element into view.

        Args:
            selector: CSS/XPath/text selector for the target element.
        """
        el = self.find(selector)
        el.scroll_into_view()

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the CDP connection and terminate auto-launched Chrome."""
        self._cdp.close()
        if self._chrome_process is not None:
            self._chrome_process.terminate()
            self._chrome_process = None

    # ── Internal ──────────────────────────────────────────────────────────

    def _resolve_element(self, parsed: ParsedSelector) -> Optional[BrowserElement]:
        """Resolve a parsed selector to a single BrowserElement.

        Args:
            parsed: Parsed selector.

        Returns:
            BrowserElement or None if not found.
        """
        js = to_cdp_expression(parsed)
        result = self._cdp.send("Runtime.evaluate", {
            "expression": js,
            "returnByValue": False,
        })
        remote_obj = result.get("result", {})
        oid = remote_obj.get("objectId")
        if oid and remote_obj.get("subtype") != "null":
            return BrowserElement(
                self, oid,
                description=remote_obj.get("description", ""),
            )
        return None

    def _resolve_elements(self, parsed: ParsedSelector) -> List[BrowserElement]:
        """Resolve a parsed selector to a list of BrowserElements.

        Args:
            parsed: Parsed selector.

        Returns:
            List of BrowserElement instances.
        """
        js = to_cdp_expression_all(parsed)
        result = self._cdp.send("Runtime.evaluate", {
            "expression": js,
            "returnByValue": False,
        })
        remote_obj = result.get("result", {})
        oid = remote_obj.get("objectId")
        if not oid:
            return []

        props = self._cdp.send("Runtime.getProperties", {
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
                        self, val_oid,
                        description=val.get("description", ""),
                    ))
        return elements

    def _find_within(
        self, parent: BrowserElement, parsed: ParsedSelector
    ) -> Optional[BrowserElement]:
        """Find an element within a parent's subtree.

        Used for XPath/text selectors that need scoped evaluation.

        Args:
            parent: The parent element to search within.
            parsed: Parsed selector.

        Returns:
            BrowserElement or None.
        """
        # For simplicity, evaluate in page context with DOM constraint
        # A more complete implementation would scope the XPath/text search
        return self._resolve_element(parsed)

    def _find_all_within(
        self, parent: BrowserElement, parsed: ParsedSelector
    ) -> List[BrowserElement]:
        """Find all elements within a parent's subtree.

        Args:
            parent: The parent element.
            parsed: Parsed selector.

        Returns:
            List of BrowserElement instances.
        """
        return self._resolve_elements(parsed)

    def _wait_for_event(
        self, event_name: str, timeout: Optional[float] = None
    ) -> None:
        """Wait for a CDP event (best-effort with polling fallback).

        Args:
            event_name: CDP event name (e.g. ``"Page.loadEventFired"``).
            timeout: Max wait time in seconds.
        """
        # Simple polling approach: check document.readyState
        if timeout is None:
            timeout = self._timeout
        deadline = time.monotonic() + timeout

        if "load" in event_name.lower():
            while time.monotonic() < deadline:
                try:
                    state = self._cdp.evaluate("document.readyState")
                    if state == "complete":
                        return
                except CDPError:
                    pass
                time.sleep(0.1)
        elif "domcontent" in event_name.lower():
            while time.monotonic() < deadline:
                try:
                    state = self._cdp.evaluate("document.readyState")
                    if state in ("interactive", "complete"):
                        return
                except CDPError:
                    pass
                time.sleep(0.1)
        else:
            # Generic wait
            time.sleep(min(1.0, timeout))

    def _wait_for_network_idle(
        self, idle_time: float = 0.5, timeout: Optional[float] = None
    ) -> None:
        """Wait until no network requests are in flight.

        Args:
            idle_time: Seconds of network silence to consider "idle".
            timeout: Max wait time in seconds.
        """
        if timeout is None:
            timeout = self._timeout

        # Simple approach: wait for load then a short delay
        self._wait_for_event("Page.loadEventFired", timeout=timeout)
        time.sleep(idle_time)

    def __repr__(self) -> str:
        return f"<BrowserPage port={self._cdp.port}>"

    def __enter__(self) -> BrowserPage:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
