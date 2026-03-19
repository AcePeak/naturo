"""Bridge to naturo_core native library via ctypes.

Provides a Pythonic interface to the C++ core DLL, handling type
conversions, JSON parsing, and error code translation.
"""

from __future__ import annotations

import ctypes
import json
import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class WindowInfo:
    """Information about a top-level window.

    Attributes:
        hwnd: Window handle (HWND on Windows).
        title: Window title text.
        process_name: Full path of the owning process.
        pid: Process ID.
        x: Window left edge X coordinate.
        y: Window top edge Y coordinate.
        width: Window width in pixels.
        height: Window height in pixels.
        is_visible: Whether the window is visible.
        is_minimized: Whether the window is minimized (iconic).
    """
    hwnd: int
    title: str
    process_name: str
    pid: int
    x: int
    y: int
    width: int
    height: int
    is_visible: bool
    is_minimized: bool


@dataclass
class ElementInfo:
    """Information about a UI automation element.

    Attributes:
        id: Automation ID of the element.
        role: Control type / role (e.g., "Button", "Edit").
        name: Element name (accessible name).
        value: Element value, if any.
        x: Bounding rectangle left edge.
        y: Bounding rectangle top edge.
        width: Bounding rectangle width.
        height: Bounding rectangle height.
        children: Child elements.
    """
    id: str
    role: str
    name: str
    value: Optional[str]
    x: int
    y: int
    width: int
    height: int
    children: list["ElementInfo"] = field(default_factory=list)


def _parse_element(data: dict) -> ElementInfo:
    """Parse a JSON dict into an ElementInfo, recursively processing children.

    Args:
        data: Dictionary from parsed JSON.

    Returns:
        An ElementInfo instance.
    """
    children = [_parse_element(c) for c in data.get("children", [])]
    return ElementInfo(
        id=data.get("id", ""),
        role=data.get("role", ""),
        name=data.get("name", ""),
        value=data.get("value"),
        x=data.get("x", 0),
        y=data.get("y", 0),
        width=data.get("width", 0),
        height=data.get("height", 0),
        children=children,
    )


class NaturoCoreError(Exception):
    """Error raised when a naturo_core function fails.

    Attributes:
        code: The native error code returned by the C function.
    """

    ERROR_MESSAGES = {
        -1: "Invalid argument",
        -2: "System/COM error",
        -3: "File I/O error",
        -4: "Buffer too small",
    }

    def __init__(self, code: int, context: str = ""):
        self.code = code
        msg = self.ERROR_MESSAGES.get(code, f"Unknown error ({code})")
        if context:
            msg = f"{context}: {msg}"
        super().__init__(msg)


class NaturoCore:
    """Wrapper around naturo_core.dll/.so native library.

    Provides Python methods for all exported C functions, handling ctypes
    setup, buffer management, and JSON parsing.

    Args:
        lib_path: Explicit path to the native library. If None, searches
            standard locations (env var, package bin/, cwd, system PATH).
    """

    def __init__(self, lib_path: str | None = None):
        self._lib = self._load(lib_path)
        self._setup_signatures()

    def _setup_signatures(self) -> None:
        """Configure ctypes function signatures for all exported functions."""
        # Version
        self._lib.naturo_version.restype = ctypes.c_char_p
        self._lib.naturo_version.argtypes = []

        # Lifecycle
        self._lib.naturo_init.restype = ctypes.c_int
        self._lib.naturo_init.argtypes = []
        self._lib.naturo_shutdown.restype = ctypes.c_int
        self._lib.naturo_shutdown.argtypes = []

        # Screen capture
        self._lib.naturo_capture_screen.restype = ctypes.c_int
        self._lib.naturo_capture_screen.argtypes = [ctypes.c_int, ctypes.c_char_p]

        # Window capture
        self._lib.naturo_capture_window.restype = ctypes.c_int
        self._lib.naturo_capture_window.argtypes = [ctypes.c_size_t, ctypes.c_char_p]

        # Window listing
        self._lib.naturo_list_windows.restype = ctypes.c_int
        self._lib.naturo_list_windows.argtypes = [ctypes.c_char_p, ctypes.c_int]

        # Window info
        self._lib.naturo_get_window_info.restype = ctypes.c_int
        self._lib.naturo_get_window_info.argtypes = [ctypes.c_size_t, ctypes.c_char_p, ctypes.c_int]

        # Element tree
        self._lib.naturo_get_element_tree.restype = ctypes.c_int
        self._lib.naturo_get_element_tree.argtypes = [
            ctypes.c_size_t, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]

        # Find element
        self._lib.naturo_find_element.restype = ctypes.c_int
        self._lib.naturo_find_element.argtypes = [
            ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.c_int
        ]

        # Phase 2 — Mouse input
        self._lib.naturo_mouse_move.restype = ctypes.c_int
        self._lib.naturo_mouse_move.argtypes = [ctypes.c_int, ctypes.c_int]

        self._lib.naturo_mouse_click.restype = ctypes.c_int
        self._lib.naturo_mouse_click.argtypes = [ctypes.c_int, ctypes.c_int]

        self._lib.naturo_mouse_scroll.restype = ctypes.c_int
        self._lib.naturo_mouse_scroll.argtypes = [ctypes.c_int, ctypes.c_int]

        # Phase 2 — Keyboard input
        self._lib.naturo_key_type.restype = ctypes.c_int
        self._lib.naturo_key_type.argtypes = [ctypes.c_char_p, ctypes.c_int]

        self._lib.naturo_key_press.restype = ctypes.c_int
        self._lib.naturo_key_press.argtypes = [ctypes.c_char_p]

        self._lib.naturo_key_hotkey.restype = ctypes.c_int
        self._lib.naturo_key_hotkey.argtypes = [ctypes.c_int, ctypes.c_char_p]

    def _load(self, lib_path: str | None) -> ctypes.CDLL:
        """Load the native library from the given path or search standard locations.

        Args:
            lib_path: Explicit path, or None to search.

        Returns:
            Loaded ctypes.CDLL instance.

        Raises:
            FileNotFoundError: If the library cannot be found.
        """
        if lib_path:
            return ctypes.CDLL(lib_path)

        # Search order:
        # 1. NATURO_CORE_PATH env var
        # 2. Package bin/ directory (bundled in wheel)
        # 3. Current directory
        # 4. System PATH

        env_path = os.environ.get("NATURO_CORE_PATH")
        if env_path and os.path.exists(env_path):
            return ctypes.CDLL(env_path)

        system = platform.system()
        if system == "Windows":
            lib_name = "naturo_core.dll"
        elif system == "Linux":
            lib_name = "libnaturo_core.so"
        elif system == "Darwin":
            lib_name = "libnaturo_core.dylib"
        else:
            raise OSError(f"Unsupported platform: {system}")

        # Check package bin/ directory
        pkg_dir = Path(__file__).parent / "bin"
        pkg_lib = pkg_dir / lib_name
        if pkg_lib.exists():
            return ctypes.CDLL(str(pkg_lib))

        # Check current directory
        cwd_lib = Path.cwd() / lib_name
        if cwd_lib.exists():
            return ctypes.CDLL(str(cwd_lib))

        # Fall back to system search
        try:
            return ctypes.CDLL(lib_name)
        except OSError:
            raise FileNotFoundError(
                f"Cannot find {lib_name}. Set NATURO_CORE_PATH or install the native library.\n"
                f"Searched: {env_path}, {pkg_lib}, {cwd_lib}, system PATH"
            )

    def version(self) -> str:
        """Get the library version string.

        Returns:
            Version string (e.g., "0.1.0").
        """
        return self._lib.naturo_version().decode("utf-8")

    def init(self) -> int:
        """Initialize the native library.

        Returns:
            0 on success.

        Raises:
            NaturoCoreError: On initialization failure.
        """
        rc = self._lib.naturo_init()
        if rc != 0:
            raise NaturoCoreError(rc, "naturo_init")
        return rc

    def shutdown(self) -> int:
        """Shut down the native library.

        Returns:
            0 on success.
        """
        return self._lib.naturo_shutdown()

    def capture_screen(self, screen_index: int = 0, output_path: str = "capture.bmp") -> str:
        """Capture a screenshot of the entire screen or a specific monitor.

        Args:
            screen_index: Zero-based monitor index. 0 for primary screen.
            output_path: File path to save the screenshot (BMP format).

        Returns:
            The output file path.

        Raises:
            NaturoCoreError: On capture failure or invalid arguments.
        """
        if output_path is None:
            raise NaturoCoreError(-1, "capture_screen")
        rc = self._lib.naturo_capture_screen(
            screen_index, output_path.encode("utf-8")
        )
        if rc != 0:
            raise NaturoCoreError(rc, "capture_screen")
        return output_path

    def capture_window(self, hwnd: int = 0, output_path: str = "capture.bmp") -> str:
        """Capture a screenshot of a specific window.

        Args:
            hwnd: Window handle. Pass 0 to capture the foreground window.
            output_path: File path to save the screenshot (BMP format).

        Returns:
            The output file path.

        Raises:
            NaturoCoreError: On capture failure or invalid arguments.
        """
        if output_path is None:
            raise NaturoCoreError(-1, "capture_window")
        rc = self._lib.naturo_capture_window(
            hwnd, output_path.encode("utf-8")
        )
        if rc != 0:
            raise NaturoCoreError(rc, "capture_window")
        return output_path

    def list_windows(self) -> list[WindowInfo]:
        """List all visible top-level windows.

        Returns:
            List of WindowInfo objects.

        Raises:
            NaturoCoreError: On enumeration failure.
        """
        buf_size = 1 << 20  # 1 MB initial buffer
        buf = ctypes.create_string_buffer(buf_size)
        count = self._lib.naturo_list_windows(buf, buf_size)

        if count == -4:
            # Buffer too small — retry with larger buffer
            buf_size = 4 << 20  # 4 MB
            buf = ctypes.create_string_buffer(buf_size)
            count = self._lib.naturo_list_windows(buf, buf_size)

        if count < 0:
            raise NaturoCoreError(count, "list_windows")

        data = json.loads(buf.value.decode("utf-8"))
        return [
            WindowInfo(
                hwnd=w["hwnd"],
                title=w["title"],
                process_name=w["process_name"],
                pid=w["pid"],
                x=w["x"],
                y=w["y"],
                width=w["width"],
                height=w["height"],
                is_visible=w["is_visible"],
                is_minimized=w["is_minimized"],
            )
            for w in data
        ]

    def get_window_info(self, hwnd: int) -> WindowInfo:
        """Get information about a specific window.

        Args:
            hwnd: Window handle.

        Returns:
            WindowInfo for the specified window.

        Raises:
            NaturoCoreError: If the window is not found or on error.
        """
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)
        rc = self._lib.naturo_get_window_info(hwnd, buf, buf_size)
        if rc != 0:
            raise NaturoCoreError(rc, "get_window_info")

        w = json.loads(buf.value.decode("utf-8"))
        return WindowInfo(
            hwnd=w["hwnd"],
            title=w["title"],
            process_name=w["process_name"],
            pid=w["pid"],
            x=w["x"],
            y=w["y"],
            width=w["width"],
            height=w["height"],
            is_visible=w["is_visible"],
            is_minimized=w["is_minimized"],
        )

    def get_element_tree(self, hwnd: int = 0, depth: int = 3) -> Optional[ElementInfo]:
        """Inspect the UI element tree of a window.

        Args:
            hwnd: Window handle. 0 for the foreground window.
            depth: Maximum tree depth (1-10).

        Returns:
            Root ElementInfo with children, or None if no window found.

        Raises:
            NaturoCoreError: On UIAutomation or buffer error.
        """
        buf_size = 1 << 20  # 1 MB
        buf = ctypes.create_string_buffer(buf_size)
        count = self._lib.naturo_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -4:
            buf_size = 8 << 20  # 8 MB retry
            buf = ctypes.create_string_buffer(buf_size)
            count = self._lib.naturo_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -2:
            return None  # No foreground window or COM error
        if count < 0:
            raise NaturoCoreError(count, "get_element_tree")

        data = json.loads(buf.value.decode("utf-8"))
        return _parse_element(data)

    def find_element(
        self, hwnd: int = 0, role: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[ElementInfo]:
        """Find a UI element by role and/or name within a window.

        Args:
            hwnd: Window handle. 0 for the foreground window.
            role: Element role filter (e.g., "Button"). None for any.
            name: Element name filter. None for any.

        Returns:
            ElementInfo if found, None if not found.

        Raises:
            NaturoCoreError: On error (invalid args, COM failure, etc.).
        """
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)

        role_bytes = role.encode("utf-8") if role else None
        name_bytes = name.encode("utf-8") if name else None

        rc = self._lib.naturo_find_element(hwnd, role_bytes, name_bytes, buf, buf_size)

        if rc == 1:
            return None  # Not found
        if rc == -2:
            return None  # No foreground window
        if rc < 0:
            raise NaturoCoreError(rc, "find_element")

        data = json.loads(buf.value.decode("utf-8"))
        return _parse_element(data)

    # ── Phase 2: Mouse Input ─────────────────────────

    def mouse_move(self, x: int, y: int) -> None:
        """Move the mouse cursor to absolute screen coordinates.

        Args:
            x: Target X coordinate (screen pixels, top-left origin).
            y: Target Y coordinate.

        Raises:
            NaturoCoreError: On system error.
        """
        rc = self._lib.naturo_mouse_move(x, y)
        if rc != 0:
            raise NaturoCoreError(rc, "mouse_move")

    def mouse_click(self, button: int = 0, double: bool = False) -> None:
        """Click the mouse at the current cursor position.

        Args:
            button: Mouse button (0=left, 1=right, 2=middle).
            double: True for double-click.

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        rc = self._lib.naturo_mouse_click(button, 1 if double else 0)
        if rc != 0:
            raise NaturoCoreError(rc, "mouse_click")

    def mouse_scroll(self, delta: int, horizontal: bool = False) -> None:
        """Scroll the mouse wheel.

        Args:
            delta: Scroll amount. Positive = up/forward, negative = down/backward.
                   One standard notch = 120 (Windows WHEEL_DELTA).
            horizontal: True for horizontal scroll.

        Raises:
            NaturoCoreError: On system error.
        """
        rc = self._lib.naturo_mouse_scroll(delta, 1 if horizontal else 0)
        if rc != 0:
            raise NaturoCoreError(rc, "mouse_scroll")

    # ── Phase 2: Keyboard Input ──────────────────────

    def key_type(self, text: str, delay_ms: int = 0) -> None:
        """Type a string using Unicode SendInput.

        Args:
            text: UTF-8 string to type.
            delay_ms: Delay between keystrokes in milliseconds.

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        if text is None:
            raise NaturoCoreError(-1, "key_type")
        rc = self._lib.naturo_key_type(text.encode("utf-8"), delay_ms)
        if rc != 0:
            raise NaturoCoreError(rc, "key_type")

    def key_press(self, key_name: str) -> None:
        """Press and release a named key.

        Args:
            key_name: Key name (e.g., "enter", "tab", "f5", "escape").

        Raises:
            NaturoCoreError: If the key name is unknown or on system error.
        """
        if not key_name:
            raise NaturoCoreError(-1, "key_press")
        rc = self._lib.naturo_key_press(key_name.encode("utf-8"))
        if rc != 0:
            raise NaturoCoreError(rc, f"key_press({key_name!r})")

    def key_hotkey(self, *keys: str) -> None:
        """Press a hotkey combination.

        Args:
            *keys: Key names. Modifier keys (ctrl, alt, shift, win) are
                   detected automatically; one non-modifier key is the base key.

        Example:
            core.key_hotkey("ctrl", "a")   # Select All
            core.key_hotkey("ctrl", "shift", "z")  # Redo

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        MODIFIER_MAP = {"ctrl": 0, "alt": 1, "shift": 2, "win": 3}
        modifiers = 0
        base_key: Optional[str] = None

        for k in keys:
            k_lower = k.lower()
            if k_lower in MODIFIER_MAP:
                modifiers |= (1 << MODIFIER_MAP[k_lower])
            else:
                if base_key is not None:
                    raise NaturoCoreError(-1, f"key_hotkey: multiple base keys ({base_key!r}, {k!r})")
                base_key = k_lower

        key_bytes = base_key.encode("utf-8") if base_key else None
        rc = self._lib.naturo_key_hotkey(modifiers, key_bytes)
        if rc != 0:
            raise NaturoCoreError(rc, f"key_hotkey({keys!r})")
