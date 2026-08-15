"""Chrome DevTools Protocol (CDP) client for browser automation.

Provides synchronous access to Chrome/Chromium/Edge browsers via the
DevTools Protocol. Requires the browser to be started with
``--remote-debugging-port=<port>`` (default 9222).

Usage::

    from naturo.cdp import CDPClient

    client = CDPClient(port=9222)
    tabs = client.list_tabs()
    client.connect(tabs[0]["id"])
    title = client.evaluate("document.title")
    client.close()

This module has no required dependencies beyond the Python stdlib for
tab listing. WebSocket communication requires the ``websocket-client``
package (``pip install naturo[cdp]``).
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CDPError(Exception):
    """Error from Chrome DevTools Protocol."""

    def __init__(self, message: str, code: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code or "CDP_ERROR"


class CDPConnectionError(CDPError):
    """Cannot connect to Chrome DevTools."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="CDP_CONNECTION_ERROR")


class CDPTimeoutError(CDPError):
    """CDP command timed out."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="CDP_TIMEOUT")


class CDPClient:
    """Synchronous Chrome DevTools Protocol client.

    Connects to a Chrome/Chromium/Edge instance via its remote debugging
    port. The browser must be started with ``--remote-debugging-port``.

    Args:
        host: DevTools host (default ``localhost``).
        port: DevTools port (default ``9222``).
        timeout: Command timeout in seconds (default ``30``).

    Example::

        client = CDPClient(port=9222)
        tabs = client.list_tabs()
        client.connect(tabs[0]["id"])
        result = client.evaluate("document.title")
        client.close()
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9222,
        timeout: float = 30.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._ws: Any = None  # websocket.WebSocket
        self._msg_id: int = 0
        self._lock = threading.Lock()

    @property
    def base_url(self) -> str:
        """HTTP base URL for the DevTools endpoint."""
        return f"http://{self.host}:{self.port}"

    @property
    def connected(self) -> bool:
        """Whether a WebSocket connection is active."""
        return self._ws is not None and self._ws.connected

    # ------------------------------------------------------------------
    # HTTP endpoints (no websocket dependency)
    # ------------------------------------------------------------------

    def _http_get(self, path: str) -> Any:
        """Send HTTP GET to the DevTools HTTP endpoint.

        Args:
            path: URL path (e.g. ``/json``).

        Returns:
            Parsed JSON response.

        Raises:
            CDPConnectionError: If the browser is not reachable.
        """
        url = f"{self.base_url}{path}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise CDPConnectionError(
                f"Cannot connect to Chrome DevTools at {self.base_url}. "
                f"Is Chrome running with --remote-debugging-port={self.port}? "
                f"Error: {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise CDPError(f"Invalid JSON from DevTools: {exc}") from exc

    def list_tabs(self) -> List[Dict[str, Any]]:
        """List open browser tabs/pages.

        Returns:
            List of tab info dicts with keys: ``id``, ``title``, ``url``,
            ``type``, ``webSocketDebuggerUrl``.

        Raises:
            CDPConnectionError: If Chrome is not reachable.
        """
        raw = self._http_get("/json")
        tabs = []
        for item in raw:
            if item.get("type") == "page":
                tabs.append({
                    "id": item.get("id", ""),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "type": item.get("type", ""),
                    "webSocketDebuggerUrl": item.get("webSocketDebuggerUrl", ""),
                })
        return tabs

    def get_version(self) -> Dict[str, str]:
        """Get browser version information.

        Returns:
            Dict with keys: ``Browser``, ``Protocol-Version``,
            ``User-Agent``, ``V8-Version``, ``WebKit-Version``.
        """
        return self._http_get("/json/version")

    # ------------------------------------------------------------------
    # WebSocket connection
    # ------------------------------------------------------------------

    def _ensure_websocket_module(self) -> Any:
        """Import websocket-client, raising a clear error if missing.

        Returns:
            The ``websocket`` module.

        Raises:
            CDPError: If ``websocket-client`` is not installed.
        """
        try:
            import websocket  # type: ignore[import-untyped]
            return websocket
        except ImportError:
            raise CDPError(
                "websocket-client is required for CDP commands. "
                "Install it with: pip install naturo[cdp]",
                code="MISSING_DEPENDENCY",
            )

    def connect(self, tab_id: Optional[str] = None) -> None:
        """Connect to a browser tab via WebSocket.

        If *tab_id* is ``None``, connects to the first available page tab.

        Args:
            tab_id: Target tab ID (from :meth:`list_tabs`).

        Raises:
            CDPConnectionError: If no tabs are available or connection fails.
            CDPError: If websocket-client is not installed.
        """
        ws_mod = self._ensure_websocket_module()

        if tab_id is None:
            tabs = self.list_tabs()
            if not tabs:
                raise CDPConnectionError(
                    "No page tabs available in Chrome. Open a tab first."
                )
            tab_id = tabs[0]["id"]

        ws_url = f"ws://{self.host}:{self.port}/devtools/page/{tab_id}"
        try:
            self._ws = ws_mod.create_connection(
                ws_url,
                timeout=self.timeout,
                enable_multithread=True,
                # Chrome/Edge 111+ reject a DevTools WebSocket handshake with
                # "403 Forbidden" when it carries an Origin header that is not
                # in --remote-allow-origins. websocket-client sends
                # "Origin: http://<host>:<port>" by default, so every attach to
                # a modern Chromium (browser *and* Electron app) was being
                # refused. Suppressing the Origin header sidesteps the origin
                # check entirely, so naturo attaches without requiring the
                # target to be launched with --remote-allow-origins.
                suppress_origin=True,
            )
        except Exception as exc:
            raise CDPConnectionError(
                f"Failed to connect to tab {tab_id}: {exc}"
            ) from exc

    def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception as exc:
                logger.debug("WebSocket close failed: %s", exc)
            self._ws = None

    # ------------------------------------------------------------------
    # CDP command execution
    # ------------------------------------------------------------------

    def send(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a CDP command and wait for the response.

        Args:
            method: CDP method name (e.g. ``Runtime.evaluate``).
            params: Method parameters.

        Returns:
            The ``result`` field from the CDP response.

        Raises:
            CDPError: If not connected, command fails, or timeout.
        """
        if not self.connected:
            raise CDPError(
                "Not connected to any tab. Call connect() first.",
                code="NOT_CONNECTED",
            )

        with self._lock:
            self._msg_id += 1
            msg_id = self._msg_id

        message = {"id": msg_id, "method": method}
        if params:
            message["params"] = params

        try:
            self._ws.send(json.dumps(message))
        except Exception as exc:
            raise CDPConnectionError(f"Failed to send command: {exc}") from exc

        # Wait for matching response
        while True:
            try:
                raw = self._ws.recv()
            except Exception as exc:
                raise CDPTimeoutError(
                    f"Timeout or connection lost waiting for response: {exc}"
                ) from exc

            try:
                response = json.loads(raw)
            except json.JSONDecodeError:
                continue  # Skip non-JSON messages

            if response.get("id") == msg_id:
                if "error" in response:
                    err = response["error"]
                    raise CDPError(
                        f"CDP error ({err.get('code', '?')}): "
                        f"{err.get('message', 'Unknown error')}",
                        code="CDP_COMMAND_ERROR",
                    )
                return response.get("result", {})

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------

    def evaluate(self, expression: str) -> Any:
        """Execute JavaScript in the page context.

        Args:
            expression: JavaScript expression to evaluate.

        Returns:
            The result value. Primitives are returned directly;
            objects are returned as their string representation.

        Raises:
            CDPError: If evaluation fails or throws an exception.
        """
        result = self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })

        remote_obj = result.get("result", {})

        if result.get("exceptionDetails"):
            exc_details = result["exceptionDetails"]
            text = exc_details.get("text", "JavaScript error")
            exception = exc_details.get("exception", {})
            desc = exception.get("description", text)
            raise CDPError(f"JavaScript error: {desc}", code="JS_ERROR")

        return remote_obj.get("value")

    def screenshot(self, format: str = "png", quality: int = 80) -> bytes:
        """Capture a screenshot of the current page.

        Args:
            format: Image format — ``png`` or ``jpeg``.
            quality: JPEG quality (1-100, ignored for PNG).

        Returns:
            Raw image bytes.

        Raises:
            CDPError: If screenshot fails.
        """
        params: Dict[str, Any] = {"format": format}
        if format == "jpeg":
            params["quality"] = max(1, min(100, quality))

        result = self.send("Page.captureScreenshot", params)
        data = result.get("data", "")
        return base64.b64decode(data)

    def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate the current page to a URL.

        Args:
            url: Target URL.

        Returns:
            Dict with ``frameId`` and ``loaderId``.

        Raises:
            CDPError: If navigation fails.
        """
        result = self.send("Page.navigate", {"url": url})
        if result.get("errorText"):
            raise CDPError(
                f"Navigation failed: {result['errorText']}",
                code="NAVIGATION_ERROR",
            )
        return result

    def get_document(self) -> Dict[str, Any]:
        """Get the root DOM node.

        Returns:
            The root node descriptor.
        """
        result = self.send("DOM.getDocument", {"depth": -1})
        return result.get("root", {})

    def query_selector(self, selector: str, node_id: int = 0) -> int:
        """Find an element by CSS selector.

        Args:
            selector: CSS selector string.
            node_id: Parent node ID (0 = document root).

        Returns:
            The matching node ID.

        Raises:
            CDPError: If element not found.
        """
        if node_id == 0:
            doc = self.send("DOM.getDocument")
            node_id = doc["root"]["nodeId"]

        result = self.send("DOM.querySelector", {
            "nodeId": node_id,
            "selector": selector,
        })
        found_id = result.get("nodeId", 0)
        if found_id == 0:
            raise CDPError(
                f"Element not found: {selector}",
                code="ELEMENT_NOT_FOUND",
            )
        return found_id

    def query_selector_all(self, selector: str, node_id: int = 0) -> List[int]:
        """Find all elements matching a CSS selector.

        Args:
            selector: CSS selector string.
            node_id: Parent node ID (0 = document root).

        Returns:
            List of matching node IDs.
        """
        if node_id == 0:
            doc = self.send("DOM.getDocument")
            node_id = doc["root"]["nodeId"]

        result = self.send("DOM.querySelectorAll", {
            "nodeId": node_id,
            "selector": selector,
        })
        return result.get("nodeIds", [])

    def get_element_text(self, selector: str) -> str:
        """Get the text content of an element.

        Args:
            selector: CSS selector.

        Returns:
            The element's ``textContent``.
        """
        return self.evaluate(
            f"document.querySelector({json.dumps(selector)})?.textContent ?? ''"
        )

    def get_element_value(self, selector: str) -> str:
        """Get the value of a form element.

        Args:
            selector: CSS selector.

        Returns:
            The element's ``value`` property.
        """
        return self.evaluate(
            f"document.querySelector({json.dumps(selector)})?.value ?? ''"
        )

    def click_element(self, selector: str) -> bool:
        """Click a DOM element by CSS selector.

        Scrolls the element into view, then dispatches a click event
        at the element's center coordinates.

        Args:
            selector: CSS selector.

        Returns:
            ``True`` on success.

        Raises:
            CDPError: If element not found.
        """
        # Get element bounding box via JS
        box = self.evaluate(f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return null;
                el.scrollIntoView({{block: 'center', inline: 'center'}});
                const rect = el.getBoundingClientRect();
                return {{
                    x: rect.x + rect.width / 2,
                    y: rect.y + rect.height / 2
                }};
            }})()
        """)

        if box is None:
            raise CDPError(
                f"Element not found: {selector}",
                code="ELEMENT_NOT_FOUND",
            )

        x, y = box["x"], box["y"]

        # Dispatch mouse events
        for event_type in ("mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent", {
                "type": event_type,
                "x": x,
                "y": y,
                "button": "left",
                "clickCount": 1,
            })

        return True

    def type_text(self, selector: str, text: str) -> bool:
        """Type text into a form field.

        Focuses the element, clears it, then types character by character
        using CDP ``Input.dispatchKeyEvent``.

        Args:
            selector: CSS selector for the input element.
            text: Text to type.

        Returns:
            ``True`` on success.

        Raises:
            CDPError: If element not found.
        """
        # Focus the element
        focused = self.evaluate(f"""
            (() => {{
                const el = document.querySelector({json.dumps(selector)});
                if (!el) return false;
                el.focus();
                el.value = '';
                return true;
            }})()
        """)

        if not focused:
            raise CDPError(
                f"Element not found: {selector}",
                code="ELEMENT_NOT_FOUND",
            )

        # Type each character
        for char in text:
            self.send("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "text": char,
            })
            self.send("Input.dispatchKeyEvent", {
                "type": "keyUp",
            })

        return True

    def get_page_html(self) -> str:
        """Get the full page HTML.

        Returns:
            The outer HTML of the document element.
        """
        return self.evaluate("document.documentElement.outerHTML") or ""

    def get_page_title(self) -> str:
        """Get the current page title.

        Returns:
            The document title.
        """
        return self.evaluate("document.title") or ""

    def get_page_url(self) -> str:
        """Get the current page URL.

        Returns:
            The document location href.
        """
        return self.evaluate("window.location.href") or ""

    def get_interactive_elements(
        self,
        selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get interactive DOM elements with bounding boxes and metadata.

        Evaluates JavaScript in the page to collect all interactive elements
        (buttons, inputs, links, etc.) along with their bounding rectangles,
        ARIA roles, labels, and tag names.

        Args:
            selector: Optional CSS selector override.  When ``None``, uses a
                built-in selector that captures common interactive elements.

        Returns:
            List of dicts, each with keys:
                - ``tagName`` (str): Lowercase HTML tag.
                - ``role`` (str): ARIA role or inferred role.
                - ``name`` (str): Accessible name (aria-label, title, text).
                - ``value`` (str | None): Form element value.
                - ``bounds`` (dict): ``{x, y, width, height}`` in viewport px.
                - ``selector`` (str): CSS selector for re-targeting.
                - ``nodeIndex`` (int): Ordinal index in the result set.

        Raises:
            CDPError: If not connected or evaluation fails.
        """
        if selector is None:
            selector = (
                # interactive controls
                "button, input, textarea, select, a[href], "
                "[role='button'], [role='checkbox'], [role='combobox'], "
                "[role='menuitem'], [role='option'], [role='tab'], "
                "[role='textbox'], [role='link'], [onclick], "
                "[tabindex]:not([tabindex='-1']), "
                # meaningful VISIBLE TEXT — headings, paragraphs, labels, list /
                # table cells, status/alert regions — so the tree mirrors what the
                # eye reads, not only what it can click (issue: web content in an
                # embedded browser was missing its titles/paragraphs/labels)
                "h1, h2, h3, h4, h5, h6, p, label, li, dt, dd, td, th, "
                "figcaption, blockquote, summary, caption, "
                "[role='heading'], [role='status'], [role='alert'], "
                "[role='note'], [role='listitem'], [role='cell'], "
                "[role='gridcell'], [role='rowheader'], [role='columnheader']"
            )

        js = f"""
        (() => {{
            const sel = {json.dumps(selector)};
            const els = Array.from(document.querySelectorAll(sel));
            const seen = new Set();
            const results = [];
            for (let i = 0; i < els.length; i++) {{
                const el = els[i];
                if (seen.has(el)) continue;
                seen.add(el);
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) continue;
                const tag = el.tagName.toLowerCase();
                const ariaRole = el.getAttribute('role') || '';
                const ariaLabel = el.getAttribute('aria-label') || '';
                const title = el.getAttribute('title') || '';
                const text = (el.innerText || '').trim().substring(0, 80);
                const name = ariaLabel || title || el.getAttribute('alt') || text;
                // Drop nameless non-form nodes — an empty heading/paragraph/label
                // adds nothing readable (form controls may be legitimately unnamed,
                // so those are kept).
                if (!name && !['input','textarea','select','button','a'].includes(tag)) continue;
                const value = ('value' in el) ? (el.value || null) : null;
                results.push({{
                    tagName: tag,
                    role: ariaRole || tag,
                    name: name,
                    value: value,
                    bounds: {{
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                    }},
                    selector: tag + (el.id ? '#' + el.id : '') +
                              (el.className && typeof el.className === 'string'
                               ? '.' + el.className.trim().split(/\\s+/).join('.')
                               : ''),
                    nodeIndex: i,
                }});
            }}
            return results;
        }})()
        """
        result = self.evaluate(js)
        if result is None:
            return []
        if not isinstance(result, list):
            return []
        return result

    def wait_for_selector(
        self,
        selector: str,
        timeout: float = 10.0,
        interval: float = 0.25,
    ) -> bool:
        """Wait for an element matching the CSS selector to appear.

        Args:
            selector: CSS selector.
            timeout: Maximum wait time in seconds.
            interval: Polling interval in seconds.

        Returns:
            ``True`` if element appeared, ``False`` if timed out.
        """
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.evaluate(
                f"!!document.querySelector({json.dumps(selector)})"
            )
            if result:
                return True
            time.sleep(interval)
        return False

    def __enter__(self) -> "CDPClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        status = "connected" if self.connected else "disconnected"
        return f"CDPClient({self.host}:{self.port}, {status})"
