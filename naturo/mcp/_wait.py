"""MCP tools for waiting on UI elements and windows."""
from __future__ import annotations

from typing import Optional


def register_wait_tools(server, _get_backend, _safe_tool):
    """Register wait-related MCP tools."""

    @server.tool()
    @_safe_tool
    def wait_for_element(
        selector: str,
        timeout: float = 10.0,
        interval: float = 0.5,
        window_title: Optional[str] = None,
    ) -> dict:
        """Wait for a UI element to appear.

        Polls the UI tree until the element matching the selector is found or timeout.
        Essential for automation flows that need to wait for UI state changes.

        Args:
            selector: Element selector (e.g. "Button:Save", "Dialog:*").
            timeout: Maximum wait time in seconds (default 10).
            interval: Poll interval in seconds (default 0.5).
            window_title: Target window (partial match, optional).

        Returns:
            Dict with success, found element info, and wait_time.
        """
        if timeout < 0:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"timeout must be >= 0, got {timeout}"}}
        if interval <= 0:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"interval must be > 0, got {interval}"}}

        from naturo.wait import wait_for_element as _wait_element
        backend = _get_backend()
        result = _wait_element(
            selector=selector,
            timeout=timeout,
            poll_interval=interval,
            window_title=window_title,
            backend=backend,
        )
        if result.found and result.element:
            return {
                "success": True,
                "found": True,
                "wait_time": round(result.wait_time, 3),
                "element": {
                    "id": result.element.id,
                    "role": result.element.role,
                    "name": result.element.name,
                    "bounds": {
                        "x": result.element.x, "y": result.element.y,
                        "width": result.element.width, "height": result.element.height,
                    },
                },
            }
        return {
            "success": False,
            "found": False,
            "wait_time": round(result.wait_time, 3),
            "error": {"code": "TIMEOUT", "message": f"Element '{selector}' not found within {timeout}s"},
        }

    @server.tool()
    @_safe_tool
    def wait_for_window(
        title: str,
        timeout: float = 10.0,
        interval: float = 0.5,
    ) -> dict:
        """Wait for a window to appear.

        Polls until a window matching the title is found or timeout.

        Args:
            title: Window title to wait for (partial match).
            timeout: Maximum wait time in seconds (default 10).
            interval: Poll interval in seconds (default 0.5).

        Returns:
            Dict with success flag and wait_time.
        """
        if timeout < 0:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"timeout must be >= 0, got {timeout}"}}
        if interval <= 0:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"interval must be > 0, got {interval}"}}

        from naturo.wait import wait_for_window as _wait_window
        backend = _get_backend()
        result = _wait_window(
            title=title,
            timeout=timeout,
            poll_interval=interval,
            backend=backend,
        )
        if result.found:
            return {
                "success": True,
                "found": True,
                "wait_time": round(result.wait_time, 3),
            }
        return {
            "success": False,
            "found": False,
            "wait_time": round(result.wait_time, 3),
            "error": {"code": "TIMEOUT", "message": f"Window '{title}' not found within {timeout}s"},
        }

    @server.tool()
    @_safe_tool
    def wait_until_gone(
        selector: str,
        timeout: float = 10.0,
        interval: float = 0.5,
        window_title: Optional[str] = None,
    ) -> dict:
        """Wait for a UI element to disappear.

        Polls until the element matching the selector is no longer found, or timeout.
        Useful for waiting for loading dialogs or progress bars to vanish.

        Args:
            selector: Element selector to wait for disappearance.
            timeout: Maximum wait time in seconds (default 10).
            interval: Poll interval in seconds (default 0.5).
            window_title: Target window (partial match, optional).

        Returns:
            Dict with success flag and wait_time.
        """
        if timeout < 0:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"timeout must be >= 0, got {timeout}"}}
        if interval <= 0:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"interval must be > 0, got {interval}"}}

        from naturo.wait import wait_until_gone as _wait_gone
        backend = _get_backend()
        result = _wait_gone(
            selector=selector,
            timeout=timeout,
            poll_interval=interval,
            window_title=window_title,
            backend=backend,
        )
        if result.found:
            return {
                "success": True,
                "gone": True,
                "wait_time": round(result.wait_time, 3),
            }
        return {
            "success": False,
            "gone": False,
            "wait_time": round(result.wait_time, 3),
            "error": {"code": "TIMEOUT", "message": f"Element '{selector}' still present after {timeout}s"},
        }
