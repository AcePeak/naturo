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

    # === Not Yet Implemented (Phase 2+) ===

    def click(self, x: Optional[int] = None, y: Optional[int] = None,
              element_id: Optional[str] = None, button: str = "left",
              double: bool = False, input_mode: str = "normal") -> None:
        """Click at coordinates or on an element."""
        raise NotImplementedError("Coming in Phase 2")

    def type_text(self, text: str = "", delay_ms: int = 5, profile: str = "human",
                  wpm: int = 120, input_mode: str = "normal") -> None:
        """Type text with configurable delay and profile."""
        raise NotImplementedError("Coming in Phase 2")

    def press_key(self, key: str = "", input_mode: str = "normal") -> None:
        """Press a single key."""
        raise NotImplementedError("Coming in Phase 2")

    def hotkey(self, *keys: str, hold_duration_ms: int = 50) -> None:
        """Press a key combination."""
        raise NotImplementedError("Coming in Phase 2")

    def scroll(self, direction: str = "down", amount: int = 3,
               x: Optional[int] = None, y: Optional[int] = None,
               smooth: bool = False) -> None:
        """Scroll the mouse wheel."""
        raise NotImplementedError("Coming in Phase 2")

    def drag(self, from_x: int = 0, from_y: int = 0, to_x: int = 0, to_y: int = 0,
             duration_ms: int = 500, steps: int = 10) -> None:
        """Drag from one point to another."""
        raise NotImplementedError("Coming in Phase 2")

    def move_mouse(self, x: int = 0, y: int = 0) -> None:
        """Move mouse to coordinates."""
        raise NotImplementedError("Coming in Phase 2")

    def clipboard_get(self) -> str:
        """Get clipboard text."""
        raise NotImplementedError("Coming in Phase 2")

    def clipboard_set(self, text: str = "") -> None:
        """Set clipboard text."""
        raise NotImplementedError("Coming in Phase 2")

    def list_apps(self) -> list[dict]:
        """List running applications."""
        raise NotImplementedError("Coming in Phase 2")

    def launch_app(self, name: str = "") -> None:
        """Launch an application."""
        raise NotImplementedError("Coming in Phase 2")

    def quit_app(self, name: str = "", force: bool = False) -> None:
        """Quit an application."""
        raise NotImplementedError("Coming in Phase 2")

    def menu_list(self, app: Optional[str] = None) -> list[dict]:
        """List menu items."""
        raise NotImplementedError("Coming in Phase 2")

    def menu_click(self, path: str = "", app: Optional[str] = None) -> None:
        """Click a menu item."""
        raise NotImplementedError("Coming in Phase 2")

    def open_uri(self, uri: str = "") -> None:
        """Open a URI with the default handler."""
        raise NotImplementedError("Coming in Phase 2")
