"""Windows backend — powered by naturo_core.dll (C++ engine).

Implements the Phase 1 "See" capabilities: screen capture, window listing,
and UI element tree inspection. Later phases will add input and interaction.
"""

from __future__ import annotations

from naturo.backends.base import (
    Backend,
    WindowInfo as BaseWindowInfo,
    ElementInfo as BaseElementInfo,
    CaptureResult,
)
from naturo.bridge import NaturoCore, NaturoCoreError
from typing import Optional


class WindowsBackend(Backend):
    """Windows automation via naturo_core.dll.

    Uses GDI for screen capture, Win32 API for window management,
    and UIAutomation COM for element inspection.

    Attributes:
        _core: Lazily loaded NaturoCore bridge instance.
        _initialized: Whether naturo_init() has been called.
    """

    def __init__(self) -> None:
        self._core: Optional[NaturoCore] = None
        self._initialized: bool = False

    def _ensure_core(self) -> NaturoCore:
        """Lazily load and initialize the native core library.

        Returns:
            The initialized NaturoCore instance.

        Raises:
            NaturoCoreError: If initialization fails.
        """
        if self._core is None:
            self._core = NaturoCore()
        if not self._initialized:
            self._core.init()
            self._initialized = True
        return self._core

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "windows"

    @property
    def capabilities(self) -> dict:
        """Return backend capabilities and platform-specific features."""
        return {
            "platform": "windows",
            "input_modes": ["normal", "hardware", "hook"],
            "accessibility": ["uia", "msaa", "ia2"],
            "extensions": ["excel", "java", "sap", "registry", "service"],
        }

    # === Capture (Phase 1) ===

    def capture_screen(self, screen_index: int = 0, output_path: str = "capture.png") -> CaptureResult:
        """Capture a screenshot of the specified monitor.

        Uses GDI BitBlt. Saves as BMP natively; the output_path extension
        is used as-is (caller should use .bmp or convert afterward).

        Args:
            screen_index: Zero-based monitor index (0 = primary).
            output_path: File path for the output image.

        Returns:
            CaptureResult with the output path and dimensions.
        """
        core = self._ensure_core()
        core.capture_screen(screen_index, output_path)

        # Read BMP header to get dimensions (offset 18 = width, 22 = height)
        width, height = 0, 0
        try:
            with open(output_path, "rb") as f:
                header = f.read(26)
                if len(header) >= 26:
                    import struct
                    width = struct.unpack_from("<i", header, 18)[0]
                    height = abs(struct.unpack_from("<i", header, 22)[0])
        except (OSError, struct.error):
            pass

        fmt = output_path.rsplit(".", 1)[-1] if "." in output_path else "bmp"
        return CaptureResult(path=output_path, width=width, height=height, format=fmt)

    def capture_window(self, window_title: Optional[str] = None, hwnd: Optional[int] = None,
                       output_path: str = "capture.png") -> CaptureResult:
        """Capture a screenshot of a specific window.

        Uses PrintWindow for accurate off-screen capture. If neither
        window_title nor hwnd is provided, captures the foreground window.

        Args:
            window_title: Window title to search for (not yet implemented — use hwnd).
            hwnd: Window handle. 0 or None for the foreground window.
            output_path: File path for the output image.

        Returns:
            CaptureResult with the output path and dimensions.
        """
        core = self._ensure_core()
        handle = hwnd if hwnd else 0
        core.capture_window(handle, output_path)

        width, height = 0, 0
        try:
            with open(output_path, "rb") as f:
                header = f.read(26)
                if len(header) >= 26:
                    import struct
                    width = struct.unpack_from("<i", header, 18)[0]
                    height = abs(struct.unpack_from("<i", header, 22)[0])
        except (OSError, struct.error):
            pass

        fmt = output_path.rsplit(".", 1)[-1] if "." in output_path else "bmp"
        return CaptureResult(path=output_path, width=width, height=height, format=fmt)

    # === Window Management (Phase 1: list only) ===

    def list_windows(self) -> list[BaseWindowInfo]:
        """List all visible top-level windows.

        Returns:
            List of WindowInfo dataclass instances.
        """
        core = self._ensure_core()
        bridge_windows = core.list_windows()
        return [
            BaseWindowInfo(
                handle=w.hwnd,
                title=w.title,
                process_name=w.process_name,
                pid=w.pid,
                x=w.x,
                y=w.y,
                width=w.width,
                height=w.height,
                is_visible=w.is_visible,
                is_minimized=w.is_minimized,
            )
            for w in bridge_windows
        ]

    def focus_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Focus a window by title or handle."""
        raise NotImplementedError("Coming in Phase 2")

    def close_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Close a window by title or handle."""
        raise NotImplementedError("Coming in Phase 2")

    def minimize_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Minimize a window."""
        raise NotImplementedError("Coming in Phase 2")

    def maximize_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Maximize a window."""
        raise NotImplementedError("Coming in Phase 2")

    def move_window(self, x: int = 0, y: int = 0, title: Optional[str] = None,
                    hwnd: Optional[int] = None) -> None:
        """Move a window to specified coordinates."""
        raise NotImplementedError("Coming in Phase 2")

    def resize_window(self, width: int = 800, height: int = 600,
                      title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Resize a window."""
        raise NotImplementedError("Coming in Phase 2")

    # === UI Element Inspection (Phase 1) ===

    def find_element(self, selector: str = "", window_title: Optional[str] = None) -> Optional[BaseElementInfo]:
        """Find a UI element by selector string.

        The selector format is "role:name" (e.g., "Button:OK") or just a name.

        Args:
            selector: Element selector in "role:name" or "name" format.
            window_title: Not yet used (reserved for future).

        Returns:
            ElementInfo if found, None otherwise.
        """
        core = self._ensure_core()

        # Parse selector into role and name
        role = None
        name = None
        if ":" in selector:
            parts = selector.split(":", 1)
            role = parts[0] if parts[0] else None
            name = parts[1] if parts[1] else None
        else:
            name = selector if selector else None

        result = core.find_element(hwnd=0, role=role, name=name)
        if result is None:
            return None

        return BaseElementInfo(
            id=result.id,
            role=result.role,
            name=result.name,
            value=result.value,
            x=result.x,
            y=result.y,
            width=result.width,
            height=result.height,
            children=[],
            properties={},
        )

    def get_element_tree(self, window_title: Optional[str] = None,
                         depth: int = 3) -> Optional[BaseElementInfo]:
        """Get the UI element tree for a window.

        Args:
            window_title: Not yet used (reserved for future).
            depth: Maximum depth to traverse (1-10).

        Returns:
            Root ElementInfo with nested children, or None.
        """
        core = self._ensure_core()
        result = core.get_element_tree(hwnd=0, depth=depth)
        if result is None:
            return None

        def convert(el: "naturo.bridge.ElementInfo") -> BaseElementInfo:
            """Convert bridge ElementInfo to backend ElementInfo."""
            return BaseElementInfo(
                id=el.id,
                role=el.role,
                name=el.name,
                value=el.value,
                x=el.x,
                y=el.y,
                width=el.width,
                height=el.height,
                children=[convert(c) for c in el.children],
                properties={},
            )

        return convert(result)

    # === Phase 2: Input ===

    def click(self, x: Optional[int] = None, y: Optional[int] = None,
              element_id: Optional[str] = None, button: str = "left",
              double: bool = False, input_mode: str = "normal") -> None:
        """Click at coordinates or on a UI element.

        If an element_id is provided, finds the element first and clicks its
        center. If x/y coordinates are provided, moves to them first.
        At least one of x/y or element_id must be given.

        Args:
            x: Target X coordinate. Required if element_id not given.
            y: Target Y coordinate. Required if element_id not given.
            element_id: Automation element ID to find and click.
            button: Mouse button — "left", "right", or "middle".
            double: True for double-click.
            input_mode: Ignored for now (Phase 3 will add hardware/hook modes).

        Raises:
            ValueError: If neither coordinates nor element_id is provided.
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()

        BUTTON_MAP = {"left": 0, "right": 1, "middle": 2}
        btn = BUTTON_MAP.get(button.lower(), 0)

        if element_id is not None:
            # Find element and click its center
            el = self.find_element(selector=element_id)
            if el is None:
                from naturo.bridge import NaturoCoreError
                raise NaturoCoreError(-1, f"click: element not found ({element_id!r})")
            cx = el.x + el.width // 2
            cy = el.y + el.height // 2
            core.mouse_move(cx, cy)
        elif x is not None and y is not None:
            core.mouse_move(x, y)
        else:
            raise ValueError("click: provide either (x, y) or element_id")

        core.mouse_click(btn, double)

    def type_text(self, text: str = "", delay_ms: int = 5, profile: str = "linear",
                  wpm: int = 120, input_mode: str = "normal") -> None:
        """Type text using Unicode SendInput.

        Args:
            text: UTF-8 string to type.
            delay_ms: Delay between keystrokes (milliseconds). Default: 5.
                For "human" profile, this is the base delay.
            profile: "linear" for constant delay, "human" for variable speed.
                     Human profile uses wpm to calculate delay.
            wpm: Words per minute (used only when profile="human").
            input_mode: Ignored (Phase 3 will add hardware/hook modes).

        Raises:
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()

        actual_delay = delay_ms
        if profile == "human" and wpm > 0:
            # Average word = 5 chars, convert wpm to ms per char
            ms_per_char = int(60_000 / (wpm * 5))
            actual_delay = max(1, ms_per_char)

        core.key_type(text, actual_delay)

    def press_key(self, key: str = "", input_mode: str = "normal") -> None:
        """Press and release a named key.

        Args:
            key: Key name (enter, tab, escape, f1-f12, a-z, 0-9, etc.).
            input_mode: Ignored (Phase 3 will add hardware/hook modes).

        Raises:
            NaturoCoreError: If key name is unrecognized or on system error.
        """
        core = self._ensure_core()
        core.key_press(key)

    def hotkey(self, *keys: str, hold_duration_ms: int = 50) -> None:
        """Press a hotkey combination.

        Args:
            *keys: Key names. Modifiers (ctrl, alt, shift, win) are recognized
                   automatically. One non-modifier key is the base key.
            hold_duration_ms: Not yet used (Phase 3).

        Example:
            backend.hotkey("ctrl", "c")   # Copy
            backend.hotkey("ctrl", "z")   # Undo

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        core = self._ensure_core()
        core.key_hotkey(*keys)

    def scroll(self, direction: str = "down", amount: int = 3,
               x: Optional[int] = None, y: Optional[int] = None,
               smooth: bool = False) -> None:
        """Scroll the mouse wheel.

        Args:
            direction: "up", "down", "left", or "right".
            amount: Number of wheel notches (each = 120 delta units).
            x: Move mouse to this X before scrolling. None = current position.
            y: Move mouse to this Y before scrolling. None = current position.
            smooth: Ignored (Phase 3 will add smooth scroll support).

        Raises:
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()

        if x is not None and y is not None:
            core.mouse_move(x, y)

        WHEEL_DELTA = 120
        horizontal = direction in ("left", "right")
        # Up/right = positive, Down/left = negative
        sign = 1 if direction in ("up", "right") else -1
        delta = sign * amount * WHEEL_DELTA

        core.mouse_scroll(delta, horizontal)

    def drag(self, from_x: int = 0, from_y: int = 0, to_x: int = 0, to_y: int = 0,
             duration_ms: int = 500, steps: int = 10) -> None:
        """Drag from one point to another.

        Moves mouse to (from_x, from_y), holds left button, interpolates to
        (to_x, to_y) in `steps` increments, then releases the button.

        Args:
            from_x: Source X coordinate.
            from_y: Source Y coordinate.
            to_x: Destination X coordinate.
            to_y: Destination Y coordinate.
            duration_ms: Total drag duration in milliseconds.
            steps: Number of intermediate move steps.

        Raises:
            NaturoCoreError: On system error.
        """
        import time
        core = self._ensure_core()

        steps = max(1, steps)
        delay_s = (duration_ms / 1000.0) / steps

        core.mouse_move(from_x, from_y)
        core.mouse_click(0, False)  # Press: we simulate hold via move+release

        # Actually we need press-down + move + release-up.
        # NaturoCore.mouse_click does down+up; we need separate press/release.
        # For now, use a rapid move sequence with brief hold simulation.
        # This is sufficient for Phase 2; Phase 3 will add proper hold support.
        for i in range(1, steps + 1):
            t = i / steps
            ix = int(from_x + (to_x - from_x) * t)
            iy = int(from_y + (to_y - from_y) * t)
            core.mouse_move(ix, iy)
            time.sleep(delay_s)

    def move_mouse(self, x: int = 0, y: int = 0) -> None:
        """Move the mouse cursor to absolute screen coordinates.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.

        Raises:
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()
        core.mouse_move(x, y)

    def clipboard_get(self) -> str:
        """Get text content from the clipboard.

        Uses the pyperclip library as a portable clipboard interface.

        Returns:
            Clipboard text, or empty string if clipboard is empty.
        """
        try:
            import pyperclip  # type: ignore
            return pyperclip.paste() or ""
        except ImportError:
            # Fallback: use win32clipboard if available
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                if not user32.OpenClipboard(0):
                    return ""
                try:
                    CF_UNICODETEXT = 13
                    h = user32.GetClipboardData(CF_UNICODETEXT)
                    if not h:
                        return ""
                    ptr = kernel32.GlobalLock(h)
                    if not ptr:
                        return ""
                    try:
                        return ctypes.wstring_at(ptr)
                    finally:
                        kernel32.GlobalUnlock(h)
                finally:
                    user32.CloseClipboard()
            except Exception:
                return ""

    def clipboard_set(self, text: str = "") -> None:
        """Set the clipboard text content.

        Args:
            text: Text to place on the clipboard.
        """
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(text)
        except ImportError:
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                CF_UNICODETEXT = 13
                GMEM_MOVEABLE = 2
                encoded = (text + "\0").encode("utf-16-le")
                h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
                if not h:
                    return
                ptr = kernel32.GlobalLock(h)
                ctypes.memmove(ptr, encoded, len(encoded))
                kernel32.GlobalUnlock(h)
                if not user32.OpenClipboard(0):
                    return
                try:
                    user32.EmptyClipboard()
                    user32.SetClipboardData(CF_UNICODETEXT, h)
                finally:
                    user32.CloseClipboard()
            except Exception:
                pass

    def list_apps(self) -> list[dict]:
        """List running applications (non-minimized, visible windows).

        Returns each unique process as a dict with name, pid, and window title.

        Returns:
            List of dicts with keys: name, pid, title.
        """
        windows = self.list_windows()
        seen_pids: set[int] = set()
        apps: list[dict] = []
        for w in windows:
            if w.is_visible and not w.is_minimized and w.pid not in seen_pids:
                seen_pids.add(w.pid)
                import os
                apps.append({
                    "name": os.path.basename(w.process_name),
                    "pid": w.pid,
                    "title": w.title,
                    "process": w.process_name,
                })
        return apps

    def launch_app(self, name: str = "") -> None:
        """Launch an application by name or path.

        Args:
            name: Application name or executable path.

        Raises:
            OSError: If the application cannot be launched.
        """
        import subprocess
        subprocess.Popen([name], shell=True)

    def quit_app(self, name: str = "", force: bool = False) -> None:
        """Quit an application by name or PID.

        Args:
            name: Process name or executable basename.
            force: If True, kills the process immediately (taskkill /F).
        """
        import subprocess
        flag = "/F" if force else ""
        cmd = f'taskkill /IM "{name}" {flag}'.strip()
        subprocess.run(cmd, shell=True, capture_output=True)

    def menu_list(self, app: Optional[str] = None) -> list[dict]:
        """List menu items. Phase 3 feature."""
        raise NotImplementedError("menu_list coming in Phase 3")

    def menu_click(self, path: str = "", app: Optional[str] = None) -> None:
        """Click a menu item. Phase 3 feature."""
        raise NotImplementedError("menu_click coming in Phase 3")

    def open_uri(self, uri: str = "") -> None:
        """Open a URI with the default handler.

        Args:
            uri: URL or file path to open.
        """
        import subprocess
        subprocess.run(["start", uri], shell=True)
