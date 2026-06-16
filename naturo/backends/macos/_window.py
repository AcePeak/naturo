"""Window enumeration and management (focus, move, resize, restore)."""
from __future__ import annotations

from typing import Optional

from naturo.backends.base import WindowInfo
from naturo.backends.macos._peekaboo import PeekabooError
from naturo.errors import NaturoError, WindowNotFoundError


class WindowMixin:
    """Window enumeration and management via Peekaboo."""

    def list_windows(self) -> list[WindowInfo]:
        """List all visible windows across applications.

        Returns:
            List of WindowInfo for each visible window.
        """
        # Peekaboo requires --app for window list; iterate apps
        apps_data = self._run(["app", "list"])
        data_section = apps_data.get("data", {})
        apps = (
            data_section.get("apps")
            or data_section.get("applications")
            or apps_data.get("apps")
            or apps_data.get("applications", [])
        )

        windows = []
        for app in apps:
            app_name = app.get("name", "")
            if not app_name:
                continue
            pid = app.get("processIdentifier", app.get("pid", 0))
            # Skip hidden apps — they typically have no visible windows
            if app.get("isHidden", app.get("is_hidden", False)):
                continue
            # If windowCount is known and zero, skip (avoids unnecessary calls)
            wc = app.get("windowCount", app.get("window_count"))
            if wc is not None and wc == 0:
                continue

            try:
                win_data = self._run(["window", "list", "--app", app_name], check=False)
                raw_windows = win_data.get("data", {}).get("windows", win_data.get("windows", []))
                for w in raw_windows:
                    # Peekaboo uses 'bounds' (snake_case) or 'frame' (camelCase)
                    frame = w.get("bounds", w.get("frame", {}))
                    windows.append(WindowInfo(
                        handle=w.get("window_id", w.get("windowId", 0)),
                        title=w.get("window_title", w.get("title", w.get("name", ""))),
                        process_name=app_name,
                        pid=w.get("pid", pid),
                        x=int(frame.get("x", w.get("x", 0))),
                        y=int(frame.get("y", w.get("y", 0))),
                        width=int(frame.get("width", w.get("width", 0))),
                        height=int(frame.get("height", w.get("height", 0))),
                        is_visible=w.get("is_on_screen", not w.get("isMinimized", w.get("is_minimized", False))),
                        is_minimized=w.get("isMinimized", w.get("is_minimized", False)),
                    ))
            except PeekabooError:
                # Skip apps that can't list windows
                continue

        return windows

    def _window_args(
        self,
        title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> list[str]:
        """Build window targeting arguments for Peekaboo.

        Args:
            title: Application name or window title.
            hwnd: Window ID.

        Returns:
            List of CLI arguments.

        Raises:
            NaturoError: If neither title nor hwnd is provided.
        """
        if hwnd is not None:
            return ["--window-id", str(hwnd)]
        elif title:
            return ["--app", title]
        else:
            raise NaturoError("Either window title or window ID must be specified")

    def focus_window(self, title: str = None, hwnd: int = None) -> None:
        """Bring a window to the foreground.

        Args:
            title: Application name or window title.
            hwnd: Window ID.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        args = ["window", "focus"] + self._window_args(title, hwnd)
        try:
            self._run(args)
        except PeekabooError as e:
            if "not found" in str(e).lower():
                raise WindowNotFoundError(f"Window not found: {title or hwnd}") from e
            raise

    def close_window(self, title: str = None, hwnd: int = None) -> None:
        """Close a window.

        Args:
            title: Application name or window title.
            hwnd: Window ID.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        args = ["window", "close"] + self._window_args(title, hwnd)
        try:
            self._run(args)
        except PeekabooError as e:
            if "not found" in str(e).lower():
                raise WindowNotFoundError(f"Window not found: {title or hwnd}") from e
            raise

    def minimize_window(self, title: str = None, hwnd: int = None) -> None:
        """Minimize a window to the Dock.

        Args:
            title: Application name or window title.
            hwnd: Window ID.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        args = ["window", "minimize"] + self._window_args(title, hwnd)
        try:
            self._run(args)
        except PeekabooError as e:
            if "not found" in str(e).lower():
                raise WindowNotFoundError(f"Window not found: {title or hwnd}") from e
            raise

    def maximize_window(self, title: str = None, hwnd: int = None) -> None:
        """Maximize a window (full screen on macOS).

        Args:
            title: Application name or window title.
            hwnd: Window ID.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        args = ["window", "maximize"] + self._window_args(title, hwnd)
        try:
            self._run(args)
        except PeekabooError as e:
            if "not found" in str(e).lower():
                raise WindowNotFoundError(f"Window not found: {title or hwnd}") from e
            raise

    def move_window(
        self,
        x: int = 0,
        y: int = 0,
        title: str = None,
        hwnd: int = None,
    ) -> None:
        """Move a window to a new position.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            title: Application name or window title.
            hwnd: Window ID.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        args = ["window", "move"] + self._window_args(title, hwnd)
        args += ["--x", str(x), "--y", str(y)]
        try:
            self._run(args)
        except PeekabooError as e:
            if "not found" in str(e).lower():
                raise WindowNotFoundError(f"Window not found: {title or hwnd}") from e
            raise

    def resize_window(
        self,
        width: int = 800,
        height: int = 600,
        title: str = None,
        hwnd: int = None,
    ) -> None:
        """Resize a window.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.
            title: Application name or window title.
            hwnd: Window ID.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        args = ["window", "resize"] + self._window_args(title, hwnd)
        args += ["--width", str(width), "--height", str(height)]
        try:
            self._run(args)
        except PeekabooError as e:
            if "not found" in str(e).lower():
                raise WindowNotFoundError(f"Window not found: {title or hwnd}") from e
            raise

    def set_bounds(
        self,
        x: int = 0,
        y: int = 0,
        width: int = 800,
        height: int = 600,
        title: str = None,
        hwnd: int = None,
    ) -> None:
        """Set window position and size in one call.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            width: Target width in pixels.
            height: Target height in pixels.
            title: Application name or window title.
            hwnd: Window ID.

        Raises:
            WindowNotFoundError: If the window cannot be found.
        """
        args = ["window", "set-bounds"] + self._window_args(title, hwnd)
        args += ["--x", str(x), "--y", str(y), "--width", str(width), "--height", str(height)]
        try:
            self._run(args)
        except PeekabooError as e:
            if "not found" in str(e).lower():
                raise WindowNotFoundError(f"Window not found: {title or hwnd}") from e
            raise

    def restore_window(self, title: str = None, hwnd: int = None) -> None:
        """Restore a minimized window.

        On macOS, this unhides/deminimizes via the app unhide command.

        Args:
            title: Application name or window title.
            hwnd: Window ID.
        """
        # macOS doesn't have a direct "restore" — unhide the app
        if title:
            try:
                self._run(["app", "unhide", "--app", title])
            except PeekabooError as e:
                if "not found" in str(e).lower():
                    raise WindowNotFoundError(f"Window not found: {title}") from e
                raise
        elif hwnd is not None:
            # Can't restore by window ID in Peekaboo easily
            raise NaturoError("Restore by window ID not supported on macOS; use app name")
        else:
            raise NaturoError("Either window title or window ID must be specified")
