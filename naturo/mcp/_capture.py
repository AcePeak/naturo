"""MCP tools for screen and window capture."""
from __future__ import annotations

import base64
import os
from typing import Optional

from naturo.mcp._resolve import require_hwnd


def register_capture_tools(server, _get_backend, _safe_tool):
    """Register capture-related MCP tools."""

    @server.tool()
    @_safe_tool
    def capture_screen(
        output_path: str = "capture.png",
        screen_index: int = 0,
    ) -> dict:
        """Capture a screenshot of the entire screen.

        Args:
            output_path: Path to save the screenshot (PNG/JPG).
            screen_index: Monitor index (0 = primary).

        Returns:
            Dict with path, width, height, format, and base64-encoded image data.
        """
        backend = _get_backend()
        result = backend.capture_screen(screen_index=screen_index, output_path=output_path)
        response = {
            "success": True,
            "path": result.path,
            "width": result.width,
            "height": result.height,
            "format": result.format,
            "scale_factor": result.scale_factor,
            "dpi": result.dpi,
        }
        # Include base64 data for AI vision
        if os.path.exists(result.path):
            with open(result.path, "rb") as f:
                response["data_base64"] = base64.b64encode(f.read()).decode("ascii")
        return response

    @server.tool()
    @_safe_tool
    def capture_window(
        window_title: Optional[str] = None,
        output_path: str = "capture.png",
    ) -> dict:
        """Capture a screenshot of a specific window.

        Args:
            window_title: Window title to capture (partial match).
            output_path: Path to save the screenshot.

        Returns:
            Dict with path, width, height, format, scale_factor, dpi.
        """
        backend = _get_backend()
        # (#954/#957) Resolve window_title to a concrete hwnd via the shared
        # MCP helper, so an unmatched title raises WindowNotFoundError (surfaced
        # as success:false / WINDOW_NOT_FOUND) instead of silently capturing the
        # foreground window and reporting success:true.  The Windows backend's
        # capture_window does not implement title matching (a missing hwnd means
        # the foreground window), so resolution must happen here — mirroring
        # naturo/cli/core/_capture.py — to keep the CLI and MCP contracts aligned.
        # Backends whose capture_window does its own title matching (e.g. macOS,
        # which has no _resolve_hwnd) keep receiving the raw window_title.
        if window_title and hasattr(backend, "_resolve_hwnd"):
            hwnd = require_hwnd(backend, window_title=window_title)
            result = backend.capture_window(hwnd=hwnd, output_path=output_path)
        else:
            result = backend.capture_window(window_title=window_title, output_path=output_path)
        response = {
            "success": True,
            "path": result.path,
            "width": result.width,
            "height": result.height,
            "format": result.format,
            "scale_factor": result.scale_factor,
            "dpi": result.dpi,
        }
        if os.path.exists(result.path):
            with open(result.path, "rb") as f:
                response["data_base64"] = base64.b64encode(f.read()).decode("ascii")
        return response

    @server.tool()
    @_safe_tool
    def list_monitors() -> dict:
        """List all connected monitors/displays.

        Returns monitor index, name, resolution, position in virtual screen
        coordinates, DPI, scale factor, primary flag, and work area.

        Returns:
            Dict with success flag and list of monitors.
        """
        backend = _get_backend()
        monitors = backend.list_monitors()
        return {
            "success": True,
            "monitors": [
                {
                    "index": m.index,
                    "name": m.name,
                    "x": m.x, "y": m.y,
                    "width": m.width, "height": m.height,
                    "is_primary": m.is_primary,
                    "scale_factor": m.scale_factor,
                    "dpi": m.dpi,
                    "work_area": m.work_area,
                }
                for m in monitors
            ],
        }
