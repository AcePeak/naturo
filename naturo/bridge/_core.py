"""NaturoCore — ctypes wrapper around the naturo_core native DLL."""
from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path
from typing import Optional

from naturo.bridge._models import (
    ElementInfo,
    WindowInfo,
    _decode_native,
    _parse_element,
    _safe_json_loads,
)
from naturo.bridge._errors import NaturoCoreError

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

    def _bind(self, name: str, restype, argtypes) -> None:
        """Bind a single DLL function, skip silently if not exported."""
        try:
            fn = getattr(self._lib, name)
            fn.restype = restype
            fn.argtypes = argtypes
        except AttributeError:
            pass  # Function not in this DLL version — will raise at call time

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

        self._bind("naturo_mouse_down", ctypes.c_int, [ctypes.c_int])
        self._bind("naturo_mouse_up", ctypes.c_int, [ctypes.c_int])

        self._lib.naturo_mouse_scroll.restype = ctypes.c_int
        self._lib.naturo_mouse_scroll.argtypes = [ctypes.c_int, ctypes.c_int]

        # Phase 2 — Keyboard input
        self._lib.naturo_key_type.restype = ctypes.c_int
        self._lib.naturo_key_type.argtypes = [ctypes.c_char_p, ctypes.c_int]

        self._lib.naturo_key_press.restype = ctypes.c_int
        self._lib.naturo_key_press.argtypes = [ctypes.c_char_p]

        self._lib.naturo_key_hotkey.restype = ctypes.c_int
        self._lib.naturo_key_hotkey.argtypes = [ctypes.c_int, ctypes.c_char_p]

        # Phase 5B — MSAA / IAccessible
        self._lib.naturo_msaa_get_element_tree.restype = ctypes.c_int
        self._lib.naturo_msaa_get_element_tree.argtypes = [
            ctypes.c_size_t, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]

        self._lib.naturo_msaa_find_element.restype = ctypes.c_int
        self._lib.naturo_msaa_find_element.argtypes = [
            ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.c_int
        ]

        # Phase 5B.2 — IAccessible2
        self._lib.naturo_ia2_get_element_tree.restype = ctypes.c_int
        self._lib.naturo_ia2_get_element_tree.argtypes = [
            ctypes.c_size_t, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]

        self._lib.naturo_ia2_find_element.restype = ctypes.c_int
        self._lib.naturo_ia2_find_element.argtypes = [
            ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.c_int
        ]

        self._lib.naturo_ia2_check_support.restype = ctypes.c_int
        self._lib.naturo_ia2_check_support.argtypes = [ctypes.c_size_t]

        # JAB (Java Access Bridge)
        self._lib.naturo_jab_get_element_tree.restype = ctypes.c_int
        self._lib.naturo_jab_get_element_tree.argtypes = [
            ctypes.c_size_t, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]

        self._lib.naturo_jab_find_element.restype = ctypes.c_int
        self._lib.naturo_jab_find_element.argtypes = [
            ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.c_int
        ]

        self._lib.naturo_jab_check_support.restype = ctypes.c_int
        self._lib.naturo_jab_check_support.argtypes = [ctypes.c_size_t]

        # Element value reading (may be absent in older DLL builds)
        try:
            self._lib.naturo_get_element_value.restype = ctypes.c_int
            self._lib.naturo_get_element_value.argtypes = [
                ctypes.c_size_t, ctypes.c_char_p, ctypes.c_char_p,
                ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int
            ]
        except AttributeError:
            pass  # DLL lacks this export; get_element_value() will raise

        # Phase 5B.5 — Hardware-level keyboard (Phys32)
        self._lib.naturo_phys_key_type.restype = ctypes.c_int
        self._lib.naturo_phys_key_type.argtypes = [ctypes.c_char_p, ctypes.c_int]

        self._lib.naturo_phys_key_press.restype = ctypes.c_int
        self._lib.naturo_phys_key_press.argtypes = [ctypes.c_char_p]

        self._lib.naturo_phys_key_hotkey.restype = ctypes.c_int
        self._lib.naturo_phys_key_hotkey.argtypes = [ctypes.c_int, ctypes.c_char_p]

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
        pkg_dir = Path(__file__).parent.parent / "bin"
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
            from naturo.errors import DependencyMissingError
            raise DependencyMissingError(
                dependency="naturo_core",
                message=(
                    f"Native library {lib_name} not found. "
                    f"This command requires the naturo_core native engine.\n"
                    f"Install the pre-built wheel: pip install naturo\n"
                    f"Or set NATURO_CORE_PATH to the library location.\n"
                    f"Searched: {env_path}, {pkg_lib}, {cwd_lib}, system PATH"
                ),
                suggested_action=(
                    "Install naturo with the native library: pip install naturo. "
                    "Commands that don't need the native engine (--help, --version, "
                    "chrome, electron, mcp, learn) will work without it."
                ),
            )

    def version(self) -> str:
        """Get the library version string.

        Returns:
            Version string (e.g., "0.1.0").
        """
        return _decode_native(self._lib.naturo_version())

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

        data = _safe_json_loads(_decode_native(buf.value))
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

        w = _safe_json_loads(_decode_native(buf.value))
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

        data = _safe_json_loads(_decode_native(buf.value))
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

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    def get_element_value(
        self,
        hwnd: int = 0,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[dict]:
        """Read the current value of a UI element using UIA patterns.

        Queries ValuePattern, TogglePattern, SelectionPattern,
        RangeValuePattern, and TextPattern to retrieve the element's
        current value.

        Args:
            hwnd: Window handle. 0 for the foreground window.
            automation_id: AutomationId of the target element.
            role: Element role filter (used when automation_id is None).
            name: Element name filter (used when automation_id is None).

        Returns:
            Dict with keys: value, pattern, role, name, automation_id,
            x, y, width, height.  None if element not found.

        Raises:
            NaturoCoreError: On error (invalid args, COM failure, etc.).
        """
        buf_size = 4 * 1024 * 1024  # 4MB for large documents (e.g. Win11 Notepad TextPattern)
        buf = ctypes.create_string_buffer(buf_size)

        aid_bytes = automation_id.encode("utf-8") if automation_id else None
        role_bytes = role.encode("utf-8") if role else None
        name_bytes = name.encode("utf-8") if name else None

        try:
            fn = self._lib.naturo_get_element_value
        except AttributeError:
            raise NaturoCoreError(
                -1,
                "get_element_value: DLL does not export naturo_get_element_value "
                "(recompile the DLL with the latest source)",
            )

        rc = fn(hwnd, aid_bytes, role_bytes, name_bytes, buf, buf_size)

        if rc == 1:
            return None  # Not found
        if rc == -2:
            return None  # No foreground window / COM error
        if rc < 0:
            raise NaturoCoreError(rc, "get_element_value")

        return _safe_json_loads(_decode_native(buf.value))

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

    def mouse_down(self, button: int = 0) -> None:
        """Press a mouse button down without releasing.

        Used for drag operations where the button must remain held
        during cursor movement.

        Args:
            button: Mouse button: 0 = left, 1 = right, 2 = middle.

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        rc = self._lib.naturo_mouse_down(button)
        if rc != 0:
            raise NaturoCoreError(rc, "mouse_down")

    def mouse_up(self, button: int = 0) -> None:
        """Release a mouse button.

        Used to complete drag operations by releasing the held button.

        Args:
            button: Mouse button: 0 = left, 1 = right, 2 = middle.

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        rc = self._lib.naturo_mouse_up(button)
        if rc != 0:
            raise NaturoCoreError(rc, "mouse_up")

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

    # ── Phase 5B.5: Hardware-level Keyboard (Phys32) ──

    def phys_key_type(self, text: str, delay_ms: int = 0) -> None:
        """Type text using hardware scan codes (Phys32 mode).

        Uses KEYEVENTF_SCANCODE to send raw PS/2 scan codes, which
        are harder for games and anti-cheat software to detect as
        synthetic input. Characters without keyboard mappings fall
        back to Unicode input transparently.

        Args:
            text: UTF-8 string to type.
            delay_ms: Delay between keystrokes in milliseconds.

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        if not text:
            raise NaturoCoreError(-1, "phys_key_type")
        rc = self._lib.naturo_phys_key_type(text.encode("utf-8"), delay_ms)
        if rc != 0:
            raise NaturoCoreError(rc, "phys_key_type")

    def phys_key_press(self, key_name: str) -> None:
        """Press and release a key using hardware scan codes (Phys32 mode).

        Uses PS/2 Set 1 scan codes with KEYEVENTF_SCANCODE. Extended keys
        (arrows, home, end, etc.) include the E0 prefix automatically.

        Args:
            key_name: Key name (same set as key_press).

        Raises:
            NaturoCoreError: If key unrecognized or on system error.
        """
        if not key_name:
            raise NaturoCoreError(-1, "phys_key_press")
        rc = self._lib.naturo_phys_key_press(key_name.encode("utf-8"))
        if rc != 0:
            raise NaturoCoreError(rc, f"phys_key_press({key_name!r})")

    def phys_key_hotkey(self, *keys: str) -> None:
        """Press a hotkey combination using hardware scan codes (Phys32 mode).

        Uses KEYEVENTF_SCANCODE for all modifier and base key events.

        Args:
            *keys: Key names. Modifiers (ctrl, alt, shift, win) are detected
                   automatically; one non-modifier key is the base key.

        Example:
            core.phys_key_hotkey("ctrl", "a")   # Select All (hardware)
            core.phys_key_hotkey("ctrl", "c")   # Copy (hardware)

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
                    raise NaturoCoreError(
                        -1, f"phys_key_hotkey: multiple base keys ({base_key!r}, {k!r})")
                base_key = k_lower

        key_bytes = base_key.encode("utf-8") if base_key else None
        rc = self._lib.naturo_phys_key_hotkey(modifiers, key_bytes)
        if rc != 0:
            raise NaturoCoreError(rc, f"phys_key_hotkey({keys!r})")

    # ── Phase 5B: MSAA / IAccessible ─────────────────

    def msaa_get_element_tree(self, hwnd: int = 0, depth: int = 3) -> Optional[ElementInfo]:
        """Inspect the MSAA (IAccessible) element tree of a window.

        Provides element inspection for legacy applications that lack
        UIAutomation support (MFC, VB6, Delphi, native Win32, etc.).

        Args:
            hwnd: Window handle. 0 for the foreground window.
            depth: Maximum tree depth (1-10).

        Returns:
            Root ElementInfo with children, or None if no window found.

        Raises:
            NaturoCoreError: On MSAA/COM or buffer error.
        """
        buf_size = 1 << 20  # 1 MB
        buf = ctypes.create_string_buffer(buf_size)
        count = self._lib.naturo_msaa_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -4:
            buf_size = 8 << 20  # 8 MB retry
            buf = ctypes.create_string_buffer(buf_size)
            count = self._lib.naturo_msaa_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -2:
            return None
        if count < 0:
            raise NaturoCoreError(count, "msaa_get_element_tree")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    def msaa_find_element(
        self, hwnd: int = 0, role: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[ElementInfo]:
        """Find an MSAA element by role and/or name within a window.

        Uses BFS traversal of the IAccessible tree. Role matching uses
        human-readable names (e.g., "Button", "Edit", "MenuItem").

        Args:
            hwnd: Window handle. 0 for the foreground window.
            role: Element role filter (case-insensitive). None for any.
            name: Element name filter (case-insensitive). None for any.

        Returns:
            ElementInfo if found, None if not found.

        Raises:
            NaturoCoreError: On error (invalid args, COM failure, etc.).
        """
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)

        role_bytes = role.encode("utf-8") if role else None
        name_bytes = name.encode("utf-8") if name else None

        rc = self._lib.naturo_msaa_find_element(hwnd, role_bytes, name_bytes, buf, buf_size)

        if rc == 1:
            return None
        if rc == -2:
            return None
        if rc < 0:
            raise NaturoCoreError(rc, "msaa_find_element")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    # ── Phase 5B.2: IAccessible2 ─────────────────────

    def ia2_check_support(self, hwnd: int = 0) -> bool:
        """Check if a window supports IAccessible2.

        Args:
            hwnd: Window handle. 0 for the foreground window.

        Returns:
            True if the window's application implements IA2.
        """
        rc = self._lib.naturo_ia2_check_support(hwnd)
        return rc == 1

    def ia2_get_element_tree(self, hwnd: int = 0, depth: int = 3) -> Optional[ElementInfo]:
        """Inspect the IAccessible2 element tree of a window.

        Provides extended accessibility info for IA2-enabled applications
        (Firefox, Thunderbird, LibreOffice, etc.). Includes IA2-specific
        properties like object attributes, extended roles, and states.

        Args:
            hwnd: Window handle. 0 for the foreground window.
            depth: Maximum tree depth (1-10).

        Returns:
            Root ElementInfo with children, or None if no window found
            or IA2 not supported.

        Raises:
            NaturoCoreError: On COM or buffer error.
        """
        buf_size = 1 << 20  # 1 MB
        buf = ctypes.create_string_buffer(buf_size)
        count = self._lib.naturo_ia2_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -4:
            buf_size = 8 << 20  # 8 MB retry
            buf = ctypes.create_string_buffer(buf_size)
            count = self._lib.naturo_ia2_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -2:
            return None
        if count == -5:
            return None  # IA2 not supported
        if count < 0:
            raise NaturoCoreError(count, "ia2_get_element_tree")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    def ia2_find_element(
        self, hwnd: int = 0, role: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[ElementInfo]:
        """Find an IA2 element by role and/or name within a window.

        Uses BFS traversal of the IAccessible2 tree. Role matching uses
        both MSAA and IA2-extended role names (e.g., "Heading", "Paragraph",
        "Landmark").

        Args:
            hwnd: Window handle. 0 for the foreground window.
            role: Element role filter (case-insensitive). None for any.
            name: Element name filter (case-insensitive). None for any.

        Returns:
            ElementInfo if found, None if not found or IA2 not supported.

        Raises:
            NaturoCoreError: On error (invalid args, COM failure, etc.).
        """
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)

        role_bytes = role.encode("utf-8") if role else None
        name_bytes = name.encode("utf-8") if name else None

        rc = self._lib.naturo_ia2_find_element(hwnd, role_bytes, name_bytes, buf, buf_size)

        if rc == 1:
            return None
        if rc == -2 or rc == -5:
            return None
        if rc < 0:
            raise NaturoCoreError(rc, "ia2_find_element")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    # ── JAB (Java Access Bridge) ─────────────────────

    def jab_check_support(self, hwnd: int = 0) -> bool:
        """Check if a window supports Java Access Bridge.

        Args:
            hwnd: Window handle. 0 to check for any Java window.

        Returns:
            True if JAB is available for the window.
        """
        rc = self._lib.naturo_jab_check_support(hwnd)
        return rc == 1

    def jab_get_element_tree(self, hwnd: int = 0, depth: int = 3) -> Optional[ElementInfo]:
        """Inspect the Java Access Bridge element tree of a window.

        Provides element inspection for Java/Swing/AWT applications.
        Requires a JRE/JDK with accessibility enabled and
        WindowsAccessBridge-64.dll on the system PATH.

        Args:
            hwnd: Window handle. 0 for the foreground window.
            depth: Maximum tree depth (1-10). Default 3.

        Returns:
            Root ElementInfo, or None if no Java window or JAB unavailable.

        Raises:
            NaturoCoreError: On error (invalid args, buffer too small).
        """
        buf_size = 2 << 20  # 2 MB
        buf = ctypes.create_string_buffer(buf_size)

        count = self._lib.naturo_jab_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -4:
            buf_size = 8 << 20  # 8 MB retry
            buf = ctypes.create_string_buffer(buf_size)
            count = self._lib.naturo_jab_get_element_tree(hwnd, depth, buf, buf_size)

        if count == -2:
            return None
        if count == -6:
            return None  # JAB not available
        if count < 0:
            raise NaturoCoreError(count, "jab_get_element_tree")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)

    def jab_find_element(
        self, hwnd: int = 0, role: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[ElementInfo]:
        """Find a JAB element by role and/or name within a window.

        Uses BFS traversal of the Java accessibility tree. Role matching
        uses normalized role names (e.g., "Button", "Edit", "MenuItem").

        Args:
            hwnd: Window handle. 0 for the foreground window.
            role: Element role filter (case-insensitive). None for any.
            name: Element name filter (case-insensitive). None for any.

        Returns:
            ElementInfo if found, None if not found or JAB unavailable.

        Raises:
            NaturoCoreError: On error (invalid args, COM failure, etc.).
        """
        buf_size = 4096
        buf = ctypes.create_string_buffer(buf_size)

        role_bytes = role.encode("utf-8") if role else None
        name_bytes = name.encode("utf-8") if name else None

        rc = self._lib.naturo_jab_find_element(hwnd, role_bytes, name_bytes, buf, buf_size)

        if rc == 1:
            return None
        if rc == -2 or rc == -6:
            return None
        if rc < 0:
            raise NaturoCoreError(rc, "jab_find_element")

        data = _safe_json_loads(_decode_native(buf.value))
        return _parse_element(data)
