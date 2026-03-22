"""macOS backend — wraps Peekaboo CLI for native macOS automation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Any, Optional

from naturo.backends.base import (
    Backend,
    CaptureResult,
    ElementInfo,
    MonitorInfo,
    WindowInfo,
)
from naturo.errors import (
    NaturoError,
    WindowNotFoundError,
)


class PeekabooError(NaturoError):
    """Error from Peekaboo CLI execution."""

    def __init__(self, message: str, code: str = "PEEKABOO_ERROR"):
        super().__init__(message)
        self.code = code


class MacOSBackend(Backend):
    """macOS automation via Peekaboo CLI wrapper.

    Delegates all operations to the Peekaboo CLI (``peekaboo``), parsing
    JSON output for structured results. Falls back to helpful error
    messages when Peekaboo is not installed.
    """

    def __init__(self) -> None:
        self._peekaboo_path = shutil.which("peekaboo")

    def _require_peekaboo(self) -> str:
        """Ensure Peekaboo is available, raising a clear error if not.

        Returns:
            Path to the peekaboo executable.

        Raises:
            NaturoError: If peekaboo is not found on PATH.
        """
        if not self._peekaboo_path:
            raise NaturoError(
                "Peekaboo is not installed. Install it from "
                "https://github.com/AcePeak/peekaboo or via Homebrew."
            )
        return self._peekaboo_path

    def _run(
        self,
        args: list[str],
        *,
        timeout: int = 30,
        check: bool = True,
    ) -> dict[str, Any]:
        """Run a Peekaboo CLI command and parse JSON output.

        Args:
            args: Command arguments (without 'peekaboo' prefix).
            timeout: Command timeout in seconds.
            check: If True, raise on non-zero exit or error response.

        Returns:
            Parsed JSON response dict.

        Raises:
            PeekabooError: On command failure or invalid output.
        """
        peekaboo = self._require_peekaboo()
        cmd = [peekaboo] + args + ["--json"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise PeekabooError(
                f"Peekaboo command timed out after {timeout}s: {' '.join(args)}",
                code="TIMEOUT",
            )
        except OSError as e:
            raise PeekabooError(f"Failed to run Peekaboo: {e}")

        # Try to parse JSON from stdout
        output = result.stdout.strip()
        if not output:
            # Some commands output to stderr on error
            stderr = result.stderr.strip()
            if result.returncode != 0:
                raise PeekabooError(
                    stderr or f"Peekaboo command failed with exit code {result.returncode}",
                    code="COMMAND_FAILED",
                )
            return {"success": True}

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            if result.returncode != 0:
                raise PeekabooError(
                    output or result.stderr.strip(),
                    code="COMMAND_FAILED",
                )
            raise PeekabooError(
                f"Invalid JSON from Peekaboo: {output[:200]}",
                code="PARSE_ERROR",
            )

        # Check for error in response
        if check and isinstance(data, dict):
            if data.get("success") is False:
                error = data.get("error", {})
                msg = error.get("message", str(data)) if isinstance(error, dict) else str(error)
                code = error.get("code", "PEEKABOO_ERROR") if isinstance(error, dict) else "PEEKABOO_ERROR"
                raise PeekabooError(msg, code=code)

        return data

    def _run_raw(
        self,
        args: list[str],
        *,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess:
        """Run a Peekaboo CLI command without JSON parsing.

        Args:
            args: Command arguments (without 'peekaboo' prefix).
            timeout: Command timeout in seconds.

        Returns:
            CompletedProcess result.
        """
        peekaboo = self._require_peekaboo()
        cmd = [peekaboo] + args

        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise PeekabooError(
                f"Peekaboo command timed out after {timeout}s: {' '.join(args)}",
                code="TIMEOUT",
            )

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "macos"

    @property
    def capabilities(self) -> dict:
        """Return backend capabilities."""
        has_peekaboo = self._peekaboo_path is not None
        return {
            "platform": "macos",
            "input_modes": ["normal"],
            "accessibility": ["ax"],
            "extensions": ["dock", "space", "menubar"],
            "peekaboo_available": has_peekaboo,
        }

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

    # === Window Management ===

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

    # === UI Element Inspection ===

    def get_element_value(
        self,
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> Optional[dict]:
        """Read element value — not yet supported on macOS.

        Returns:
            None (macOS does not yet support UIA pattern value reading).
        """
        return None

    def find_element(
        self,
        selector: str = "",
        window_title: str = None,
    ) -> Optional[ElementInfo]:
        """Find a UI element by selector.

        Args:
            selector: Element selector (role:name format).
            window_title: Application name to scope the search.

        Returns:
            ElementInfo if found, None otherwise.
        """
        # Use Peekaboo see --json to get element tree, then search
        args = ["see"]
        if window_title:
            args += ["--app", window_title]

        try:
            data = self._run(args, timeout=20)
        except PeekabooError:
            return None

        elements = data.get("data", {}).get("elements", data.get("elements", []))
        return self._search_elements(elements, selector)

    def _search_elements(
        self,
        elements: list[dict],
        selector: str,
    ) -> Optional[ElementInfo]:
        """Recursively search element tree for a matching element.

        Args:
            elements: List of element dicts from Peekaboo.
            selector: Search string (matches role:name or name).

        Returns:
            ElementInfo if found, None otherwise.
        """
        selector_lower = selector.lower()
        for el in elements:
            name = el.get("name", el.get("title", ""))
            role = el.get("role", el.get("type", ""))
            full = f"{role}:{name}"

            if (selector_lower in name.lower()
                    or selector_lower in full.lower()
                    or selector_lower in role.lower()):
                frame = el.get("frame", {})
                return ElementInfo(
                    id=str(el.get("id", el.get("peekabooId", ""))),
                    role=role,
                    name=name,
                    value=el.get("value"),
                    x=int(frame.get("x", el.get("x", 0))),
                    y=int(frame.get("y", el.get("y", 0))),
                    width=int(frame.get("width", el.get("width", 0))),
                    height=int(frame.get("height", el.get("height", 0))),
                    children=[],
                    properties=el,
                )

            # Search children
            children = el.get("children", [])
            if children:
                found = self._search_elements(children, selector)
                if found:
                    return found

        return None

    def get_element_tree(
        self,
        window_title: str = None,
        depth: int = 3,
        backend: str = "ax",
    ) -> Optional[ElementInfo]:
        """Get the UI element tree for a window.

        Args:
            window_title: Application name or window title.
            depth: Maximum depth to traverse.
            backend: Accessibility backend (ignored on macOS, always 'ax').

        Returns:
            Root ElementInfo with children populated.
        """
        args = ["see"]
        if window_title:
            args += ["--app", window_title]

        try:
            data = self._run(args, timeout=20)
        except PeekabooError:
            return None

        elements = data.get("data", {}).get("elements", data.get("elements", []))
        if not elements:
            return None

        return self._parse_element_tree(elements, depth)

    def _parse_element_tree(
        self,
        elements: list[dict],
        max_depth: int,
        current_depth: int = 0,
    ) -> Optional[ElementInfo]:
        """Parse Peekaboo element tree into ElementInfo hierarchy.

        Args:
            elements: List of element dicts.
            max_depth: Maximum depth to traverse.
            current_depth: Current recursion depth.

        Returns:
            Root ElementInfo, or None if elements is empty.
        """
        if not elements or current_depth > max_depth:
            return None

        # Build a virtual root containing all top-level elements
        children = []
        for el in elements:
            frame = el.get("frame", {})
            child_elements = el.get("children", [])
            parsed_children = []
            if child_elements and current_depth < max_depth:
                for c in child_elements:
                    parsed = self._parse_element_tree([c], max_depth, current_depth + 1)
                    if parsed:
                        parsed_children.append(parsed)

            children.append(ElementInfo(
                id=str(el.get("id", el.get("peekabooId", ""))),
                role=el.get("role", el.get("type", "")),
                name=el.get("name", el.get("title", "")),
                value=el.get("value"),
                x=int(frame.get("x", el.get("x", 0))),
                y=int(frame.get("y", el.get("y", 0))),
                width=int(frame.get("width", el.get("width", 0))),
                height=int(frame.get("height", el.get("height", 0))),
                children=parsed_children,
                properties=el,
            ))

        if len(children) == 1:
            return children[0]

        # Multiple top-level elements: wrap in a root
        return ElementInfo(
            id="root",
            role="Application",
            name="",
            value=None,
            x=0, y=0, width=0, height=0,
            children=children,
            properties={},
        )

    # === Input ===

    def click(
        self,
        x: int = None,
        y: int = None,
        element_id: str = None,
        button: str = "left",
        double: bool = False,
        input_mode: str = "normal",
    ) -> None:
        """Click at coordinates or on an element.

        Args:
            x: X coordinate for click.
            y: Y coordinate for click.
            element_id: Peekaboo element ID to click.
            button: Mouse button ('left', 'right', 'middle').
            double: Whether to double-click.
            input_mode: Input mode (only 'normal' on macOS).

        Raises:
            NaturoError: If neither coordinates nor element_id is provided.
        """
        args = ["click"]
        if element_id:
            args += [element_id]
        elif x is not None and y is not None:
            args += ["--x", str(x), "--y", str(y)]
        else:
            raise NaturoError("Either coordinates (x, y) or element_id must be specified")

        if button == "right":
            args.append("--right")
        if double:
            args.append("--double")

        self._run(args)

    def type_text(
        self,
        text: str = "",
        delay_ms: int = 5,
        profile: str = "human",
        wpm: int = 120,
        input_mode: str = "normal",
    ) -> None:
        """Type text using keyboard simulation.

        Args:
            text: Text to type.
            delay_ms: Delay between keystrokes in milliseconds.
            profile: Typing profile (ignored on macOS).
            wpm: Words per minute (ignored on macOS).
            input_mode: Input mode (only 'normal' on macOS).
        """
        if not text:
            return
        args = ["type", text]
        if delay_ms > 0:
            # Peekaboo uses --delay in seconds
            args += ["--delay", str(delay_ms / 1000.0)]
        self._run(args)

    def press_key(self, key: str = "", input_mode: str = "normal") -> None:
        """Press a single key or key combination.

        Args:
            key: Key name (e.g., 'enter', 'tab', 'escape').
            input_mode: Input mode (only 'normal' on macOS).
        """
        if not key:
            return
        self._run(["press", key])

    def hotkey(self, *keys: str, hold_duration_ms: int = 50) -> None:
        """Press a keyboard shortcut.

        Args:
            *keys: Key names to press simultaneously (e.g., 'cmd', 's').
            hold_duration_ms: Duration to hold keys in milliseconds.
        """
        if not keys:
            return
        # Peekaboo hotkey expects keys joined with +
        combo = "+".join(keys)
        self._run(["hotkey", combo])

    def scroll(
        self,
        direction: str = "down",
        amount: int = 3,
        x: int = None,
        y: int = None,
        smooth: bool = False,
    ) -> None:
        """Scroll the mouse wheel.

        Args:
            direction: Scroll direction ('up', 'down', 'left', 'right').
            amount: Number of scroll steps.
            x: X coordinate for scroll location.
            y: Y coordinate for scroll location.
            smooth: Whether to use smooth scrolling.
        """
        args = ["scroll", "--direction", direction, "--amount", str(amount)]
        if x is not None and y is not None:
            args += ["--x", str(x), "--y", str(y)]
        self._run(args)

    def drag(
        self,
        from_x: int = 0,
        from_y: int = 0,
        to_x: int = 0,
        to_y: int = 0,
        duration_ms: int = 500,
        steps: int = 10,
    ) -> None:
        """Drag from one point to another.

        Args:
            from_x: Starting X coordinate.
            from_y: Starting Y coordinate.
            to_x: Ending X coordinate.
            to_y: Ending Y coordinate.
            duration_ms: Drag duration in milliseconds.
            steps: Number of intermediate steps.
        """
        args = [
            "drag",
            "--from-x", str(from_x), "--from-y", str(from_y),
            "--to-x", str(to_x), "--to-y", str(to_y),
        ]
        if duration_ms > 0:
            args += ["--duration", str(duration_ms / 1000.0)]
        self._run(args)

    def move_mouse(self, x: int = 0, y: int = 0) -> None:
        """Move the mouse cursor to coordinates.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
        """
        self._run(["move", "--x", str(x), "--y", str(y)])

    # === Clipboard ===

    def clipboard_get(self) -> str:
        """Get clipboard text content.

        Returns:
            Current clipboard text.
        """
        data = self._run(["clipboard", "-a", "get"])
        return data.get("data", {}).get("text", data.get("text", ""))

    def clipboard_set(self, text: str = "") -> None:
        """Set clipboard text content.

        Args:
            text: Text to copy to clipboard.
        """
        self._run(["clipboard", "-a", "set", "--text", text])

    # === Application Control ===

    def list_apps(self) -> list[dict]:
        """List running applications.

        Returns:
            List of dicts with app info (name, pid, bundleIdentifier, etc.).
        """
        data = self._run(["app", "list"])
        data_section = data.get("data", {})
        apps = (
            data_section.get("apps")
            or data_section.get("applications")
            or data.get("apps")
            or data.get("applications", [])
        )
        result = []
        for app in apps:
            result.append({
                "name": app.get("name", ""),
                "pid": app.get("processIdentifier", app.get("pid", 0)),
                "bundle_id": app.get("bundleIdentifier", app.get("bundle_id", "")),
                "bundle_path": app.get("bundlePath", app.get("bundle_path", "")),
                "is_active": app.get("isActive", app.get("is_active", False)),
                "is_hidden": app.get("isHidden", app.get("is_hidden", False)),
                "window_count": app.get("windowCount", app.get("window_count", 0)),
            })
        return result

    def launch_app(self, name: str = "") -> None:
        """Launch an application by name.

        Args:
            name: Application name (e.g., 'Safari', 'Terminal').

        Raises:
            NaturoError: If the application cannot be found.
        """
        if not name:
            raise NaturoError("Application name is required")
        try:
            self._run(["app", "launch", name])
        except PeekabooError as e:
            if "not found" in str(e).lower():
                raise NaturoError(f"Application not found: {name}") from e
            raise

    def quit_app(self, name: str = "", force: bool = False) -> None:
        """Quit an application.

        Args:
            name: Application name.
            force: If True, force-quit the application.
        """
        if not name:
            raise NaturoError("Application name is required")
        args = ["app", "quit", "--app", name]
        if force:
            args.append("--force")
        self._run(args)

    # === Open ===

    def open_uri(self, uri: str = "") -> None:
        """Open a URL or file with the default application.

        Args:
            uri: URL or file path to open.
        """
        if not uri:
            raise NaturoError("URI is required")
        self._run(["open", uri])

    # === Menu ===

    def get_menu_items(self, window_title: Optional[str] = None) -> list:
        """Get menu items from the application menu bar.

        Args:
            window_title: Application name to inspect menus for.

        Returns:
            List of menu item dicts.
        """
        args = ["menu", "list"]
        if window_title:
            args += ["--app", window_title]
        data = self._run(args, timeout=15)
        return data.get("data", {}).get("menuItems", data.get("menu_items", []))

    # === Dialog ===

    def detect_dialogs(
        self,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> list:
        """Detect active dialog windows.

        Args:
            app: Filter by owner application name.
            hwnd: Filter by specific dialog window handle.

        Returns:
            List of dialog info dicts.
        """
        args = ["dialog", "detect"]
        if app:
            args += ["--app", app]
        try:
            data = self._run(args, timeout=10)
            return data.get("data", {}).get("dialogs", data.get("dialogs", []))
        except PeekabooError:
            return []

    def dialog_click_button(
        self,
        button: str,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Click a button in a dialog.

        Args:
            button: Button text to click (e.g., "OK", "Cancel").
            app: Owner application name.
            hwnd: Specific dialog window handle.

        Returns:
            Dict with result info.
        """
        if button.lower() in ("ok", "yes", "accept"):
            args = ["dialog", "accept"]
        elif button.lower() in ("cancel", "no", "dismiss"):
            args = ["dialog", "dismiss"]
        else:
            args = ["dialog", "click-button", button]

        if app:
            args += ["--app", app]
        data = self._run(args)
        return data.get("data", data)

    def dialog_set_input(
        self,
        text: str,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Type text into a dialog input field.

        Args:
            text: Text to enter.
            app: Owner application name.
            hwnd: Specific dialog window handle.

        Returns:
            Dict with result info.
        """
        args = ["dialog", "type", text]
        if app:
            args += ["--app", app]
        data = self._run(args)
        return data.get("data", data)
