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
        include_base64: bool = False,
    ) -> dict:
        """Capture a screenshot of the entire screen.

        The image is saved to ``output_path`` — read that file to view it.

        Args:
            output_path: Path to save the screenshot (PNG/JPG).
            screen_index: Monitor index (0 = primary).
            include_base64: Inline the PNG as base64 in the response. Off by
                default: a full-resolution screenshot is hundreds of KB and
                floods the caller's context (and is not rendered as an image
                anyway) — prefer reading the saved ``path``. Set True only if
                you specifically need the bytes in-band.

        Returns:
            Dict with path, width, height, format, scale_factor, dpi — plus
            ``data_base64`` only when ``include_base64`` is True.
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
        if include_base64 and os.path.exists(result.path):
            with open(result.path, "rb") as f:
                response["data_base64"] = base64.b64encode(f.read()).decode("ascii")
        return response

    @server.tool()
    @_safe_tool
    def capture_window(
        window_title: Optional[str] = None,
        output_path: str = "capture.png",
        hwnd: Optional[int] = None,
        include_base64: bool = False,
    ) -> dict:
        """Capture a screenshot of a specific window.

        The image is saved to ``output_path`` — read that file to view it.

        Args:
            window_title: Window title to capture (partial match).
            output_path: Path to save the screenshot.
            hwnd: Direct window handle (from ``launch_app``/``list_windows``) —
                preferred; targets that exact window and skips title matching.
            include_base64: Inline the PNG as base64 in the response. Off by
                default: a full window screenshot is hundreds of KB and floods
                the caller's context — prefer reading the saved ``path``. Set
                True only if you specifically need the bytes in-band.

        Returns:
            Dict with path, width, height, format, scale_factor, dpi — plus
            ``data_base64`` only when ``include_base64`` is True.
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
        if hwnd is not None:
            # Direct handle from launch_app/list_windows — no title guessing.
            result = backend.capture_window(hwnd=hwnd, output_path=output_path)
        elif window_title and hasattr(backend, "_resolve_hwnd"):
            resolved = require_hwnd(backend, window_title=window_title)
            result = backend.capture_window(hwnd=resolved, output_path=output_path)
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
        if include_base64 and os.path.exists(result.path):
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
