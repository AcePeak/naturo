"""Monitor enumeration and screen/window capture via Peekaboo."""
from __future__ import annotations

from naturo.backends.base import CaptureResult, MonitorInfo
from naturo.backends.macos._peekaboo import PeekabooError
from naturo.errors import WindowNotFoundError


class CaptureMixin:
    """Monitor enumeration and screen/window capture via Peekaboo."""

    # === Monitor ===

    def list_monitors(self) -> list[MonitorInfo]:
        """Enumerate connected monitors via Peekaboo.

        Returns:
            List of MonitorInfo for each display.
        """
        data = self._run(["list", "screens"])
        screens = []
        raw_screens = data.get("data", {}).get("screens", data.get("screens", []))
        for i, s in enumerate(raw_screens):
            screens.append(MonitorInfo(
                index=s.get("index", i),
                name=s.get("name", f"Display {i}"),
                x=s.get("x", s.get("frame", {}).get("x", 0)),
                y=s.get("y", s.get("frame", {}).get("y", 0)),
                width=s.get("width", s.get("frame", {}).get("width", 0)),
                height=s.get("height", s.get("frame", {}).get("height", 0)),
                is_primary=s.get("isPrimary", s.get("is_primary", i == 0)),
                scale_factor=s.get("scaleFactor", s.get("scale_factor", 1.0)),
                dpi=int(s.get("dpi", 72 * s.get("scaleFactor", s.get("scale_factor", 1.0)))),
            ))
        return screens

    # === Capture ===

    def capture_screen(
        self,
        screen_index: int = 0,
        output_path: str = "capture.png",
    ) -> CaptureResult:
        """Capture a screenshot of the specified screen.

        Args:
            screen_index: Zero-based monitor index.
            output_path: Path to save the PNG screenshot.

        Returns:
            CaptureResult with path and dimensions.
        """
        args = ["image", "--path", output_path, "--screen-index", str(screen_index)]
        data = self._run(args, timeout=20)
        img_data = data.get("data", data)
        return CaptureResult(
            path=img_data.get("path", output_path),
            width=img_data.get("width", 0),
            height=img_data.get("height", 0),
            format=img_data.get("format", "png"),
        )

    def capture_window(
        self,
        window_title: str = None,
        hwnd: int = None,
        output_path: str = "capture.png",
    ) -> CaptureResult:
        """Capture a screenshot of a specific window.

        Args:
            window_title: Application name or window title.
            hwnd: Window ID (CoreGraphics window_id on macOS).
            output_path: Path to save the PNG screenshot.

        Returns:
            CaptureResult with path and dimensions.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        args = ["image", "--path", output_path]
        if hwnd is not None:
            args += ["--window-id", str(hwnd)]
        elif window_title:
            args += ["--app", window_title]
        else:
            args += ["--mode", "frontmost"]

        try:
            data = self._run(args, timeout=20)
        except PeekabooError as e:
            if "not found" in str(e).lower() or "WINDOW_NOT_FOUND" in getattr(e, "code", ""):
                raise WindowNotFoundError(
                    f"Window not found: {window_title or hwnd}"
                ) from e
            raise

        img_data = data.get("data", data)
        return CaptureResult(
            path=img_data.get("path", output_path),
            width=img_data.get("width", 0),
            height=img_data.get("height", 0),
            format=img_data.get("format", "png"),
        )
