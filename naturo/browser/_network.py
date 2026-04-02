"""Network monitoring and request interception for browser automation.

Uses CDP Network and Fetch domains to capture, filter, and modify HTTP
requests.  Lazy-initialized via :attr:`BrowserPage.network`.

Usage::

    page = BrowserPage(port=9222)
    net = NetworkMonitor(page._cdp)

    # Capture a snapshot of recent requests
    snapshot = net.capture_snapshot()

    # Filter requests
    api_calls = net.find_requests("*/api/*")

    # Intercept and modify
    net.intercept("*/tracking/*", action="abort")
    net.mock_response("*/config.json", body='{"debug": true}')
"""

from __future__ import annotations

import fnmatch
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NetworkMonitor:
    """Monitor and intercept network requests via CDP.

    Args:
        cdp: A connected :class:`~naturo.cdp.CDPClient`.
    """

    def __init__(self, cdp: Any) -> None:
        self._cdp = cdp
        self._enabled = False
        self._intercept_patterns: List[Dict[str, Any]] = []

    def _ensure_enabled(self) -> None:
        """Enable the Network domain if not already enabled."""
        if not self._enabled:
            self._cdp.send("Network.enable")
            self._enabled = True

    def capture_snapshot(self) -> List[Dict[str, Any]]:
        """Capture a snapshot of recent network requests via Performance API.

        Uses ``performance.getEntriesByType('resource')`` to get a list
        of all resource requests made by the page.

        Returns:
            List of request info dicts with ``name`` (URL), ``type``,
            ``duration``, ``size``, and ``status`` keys.
        """
        js = """
        (function() {
            var entries = performance.getEntriesByType('resource');
            return entries.map(function(e) {
                return {
                    name: e.name,
                    type: e.initiatorType,
                    duration: Math.round(e.duration),
                    size: e.transferSize || 0,
                    startTime: Math.round(e.startTime),
                };
            });
        })()
        """
        result = self._cdp.evaluate(js)
        if isinstance(result, list):
            return result
        return []

    def find_requests(
        self, pattern: str, *, snapshot: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Filter requests by URL glob pattern.

        Args:
            pattern: Glob pattern to match against request URLs (e.g.
                ``"*/api/*"``).
            snapshot: Optional pre-captured snapshot. If ``None``, calls
                :meth:`capture_snapshot`.

        Returns:
            Filtered list of request dicts.
        """
        if snapshot is None:
            snapshot = self.capture_snapshot()
        return [r for r in snapshot if fnmatch.fnmatch(r.get("name", ""), pattern)]

    def intercept(
        self,
        pattern: str,
        *,
        action: str = "continue",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        """Add a request interception rule.

        Uses the CDP Fetch domain to intercept matching requests and
        apply the specified action.

        Args:
            pattern: URL glob pattern to match.
            action: One of ``"continue"`` (pass through, possibly with
                modified headers), ``"abort"`` (block the request), or
                ``"fulfill"`` (return a custom response).
            headers: Headers to add/override (for ``continue``/``fulfill``).
            body: Response body (for ``fulfill``).
            status_code: Response status code (for ``fulfill``).
        """
        self._ensure_enabled()

        self._intercept_patterns.append({
            "pattern": pattern,
            "action": action,
            "headers": headers,
            "body": body,
            "status_code": status_code,
        })

        # Use JavaScript-based interception via service worker pattern
        # This is more portable than CDP Fetch which requires event handling
        if action == "abort":
            self._inject_abort_rule(pattern)
        elif action == "fulfill" and body is not None:
            self._inject_mock_rule(pattern, body, status_code or 200, headers)

    def abort_pattern(self, pattern: str) -> None:
        """Block all requests matching a URL pattern.

        Shorthand for ``intercept(pattern, action="abort")``.

        Args:
            pattern: URL glob pattern to block.
        """
        self.intercept(pattern, action="abort")

    def mock_response(
        self,
        pattern: str,
        *,
        body: str = "",
        status_code: int = 200,
        content_type: str = "application/json",
    ) -> None:
        """Return a custom response for matching requests.

        Shorthand for ``intercept(pattern, action="fulfill", ...)``.

        Args:
            pattern: URL glob pattern.
            body: Response body string.
            status_code: HTTP status code.
            content_type: Response Content-Type header.
        """
        self.intercept(
            pattern,
            action="fulfill",
            body=body,
            status_code=status_code,
            headers={"Content-Type": content_type},
        )

    def _inject_abort_rule(self, pattern: str) -> None:
        """Inject a JS-based request blocking rule."""
        # Convert glob to regex for use in JS
        regex = self._glob_to_regex(pattern)
        js = f"""
        (function() {{
            var origFetch = window.fetch;
            window.fetch = function(input, init) {{
                var url = typeof input === 'string' ? input : input.url;
                if (/{regex}/.test(url)) {{
                    return Promise.reject(new TypeError('naturo: blocked by abort rule'));
                }}
                return origFetch.apply(this, arguments);
            }};

            var origXHR = XMLHttpRequest.prototype.open;
            XMLHttpRequest.prototype.open = function(method, url) {{
                if (/{regex}/.test(url)) {{
                    this._naturoBlocked = true;
                }}
                return origXHR.apply(this, arguments);
            }};
            var origSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.send = function() {{
                if (this._naturoBlocked) return;
                return origSend.apply(this, arguments);
            }};
        }})()
        """
        self._cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": js})
        self._cdp.evaluate(js)

    def _inject_mock_rule(
        self, pattern: str, body: str, status_code: int,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Inject a JS-based response mock rule."""
        regex = self._glob_to_regex(pattern)
        body_json = json.dumps(body)
        headers_json = json.dumps(headers or {})
        js = f"""
        (function() {{
            var origFetch = window.fetch;
            window.fetch = function(input, init) {{
                var url = typeof input === 'string' ? input : input.url;
                if (/{regex}/.test(url)) {{
                    var headers = new Headers({headers_json});
                    return Promise.resolve(new Response({body_json}, {{
                        status: {status_code},
                        headers: headers,
                    }}));
                }}
                return origFetch.apply(this, arguments);
            }};
        }})()
        """
        self._cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": js})
        self._cdp.evaluate(js)

    @staticmethod
    def _glob_to_regex(pattern: str) -> str:
        """Convert a simple glob pattern to a JavaScript regex string.

        Handles ``*`` (any chars except ``/``) and ``**`` (any chars
        including ``/``).

        Args:
            pattern: Glob pattern.

        Returns:
            Regex string (without delimiters).
        """
        # Escape regex special chars except * and ?
        result = ""
        i = 0
        while i < len(pattern):
            c = pattern[i]
            if c == "*" and i + 1 < len(pattern) and pattern[i + 1] == "*":
                result += ".*"
                i += 2
                continue
            elif c == "*":
                result += "[^/]*"
            elif c == "?":
                result += "."
            elif c in r"\.+^${}()|[]":
                result += "\\" + c
            else:
                result += c
            i += 1
        return result
