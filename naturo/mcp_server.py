"""Naturo MCP Server — expose desktop automation as MCP tools.

Provides AI agents with structured access to Windows desktop automation:
capture, inspect, click, type, find elements, manage windows/apps.
"""
from __future__ import annotations

import functools
import logging

from mcp.server.fastmcp import FastMCP

from naturo.backends.base import get_backend, Backend
from naturo.errors import NaturoError
from naturo.process import launch_app as _launch_app

from naturo.mcp._capture import register_capture_tools
from naturo.mcp._window import register_window_tools
from naturo.mcp._inspect import register_inspect_tools
from naturo.mcp._input import register_input_tools
from naturo.mcp._app import register_app_tools
from naturo.mcp._wait import register_wait_tools
from naturo.mcp._snapshot import register_snapshot_tools
from naturo.mcp._clipboard import register_clipboard_tools
from naturo.mcp._dialog import register_dialog_tools
from naturo.mcp._system import register_system_tools
from naturo.mcp._excel import register_excel_tools

logger = logging.getLogger(__name__)


def create_server(host: str = "localhost", port: int = 3100) -> FastMCP:
    """Create and configure the Naturo MCP server."""
    server = FastMCP(
        name="naturo",
        host=host,
        port=port,
        instructions=(
            "Naturo — Windows desktop automation engine. "
            "Use these tools to see, click, type, and automate Windows applications. "
            "Start with capture_screen or list_windows to understand the current state, "
            "then use find_element or see_ui_tree to locate UI elements, "
            "and interact with click, type_text, press_key, etc."
        ),
    )

    def _get_backend() -> Backend:
        """Get the platform backend, raising clear errors."""
        try:
            return get_backend()
        except RuntimeError as e:
            raise NaturoError(str(e))

    def _safe_tool(fn):
        """Decorator: wraps MCP tool handlers with try/except to return structured errors."""
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except NaturoError as e:
                error_info: dict = {"code": e.code, "message": str(e)}
                if e.suggested_action:
                    error_info["suggested_action"] = e.suggested_action
                if e.is_recoverable:
                    error_info["recoverable"] = True
                return {"success": False, "error": error_info}
            except Exception as e:
                logger.exception("Unhandled error in tool %s", fn.__name__)
                return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": f"{type(e).__name__}: {e}"}}
        return wrapper

    # Register all tool groups
    register_capture_tools(server, _get_backend, _safe_tool)
    register_window_tools(server, _get_backend, _safe_tool)
    register_inspect_tools(server, _get_backend, _safe_tool)
    register_input_tools(server, _get_backend, _safe_tool)
    register_app_tools(server, _get_backend, _safe_tool, launch_app_fn=_launch_app)
    register_wait_tools(server, _get_backend, _safe_tool)
    register_snapshot_tools(server, _get_backend, _safe_tool)
    register_clipboard_tools(server, _get_backend, _safe_tool)
    register_dialog_tools(server, _get_backend, _safe_tool)
    register_system_tools(server, _get_backend, _safe_tool)
    register_excel_tools(server, _get_backend, _safe_tool)

    return server


def run_server(transport: str = "stdio", host: str = "localhost", port: int = 3100):
    """Run the MCP server with the specified transport."""
    server = create_server(host=host, port=port)
    server.run(transport=transport)
