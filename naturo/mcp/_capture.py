"""MCP tools for screen and window capture."""
from __future__ import annotations

import base64
import os
from typing import Optional


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
