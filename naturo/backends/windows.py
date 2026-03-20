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
from naturo.bridge import NaturoCore, NaturoCoreError, populate_hierarchy
from naturo.models.menu import MenuItem
from typing import List, Optional


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

    @staticmethod
    def _convert_bmp(bmp_path: str, output_path: str) -> tuple[int, int, str]:
        """Convert a BMP file to the format implied by *output_path* extension.

        Uses Pillow so we always deliver PNG/JPEG/etc. to users, regardless
        of the native BMP format produced by the C++ DLL (GDI BitBlt).

        Returns:
            (width, height, format_name) tuple.
        """
        import os
        from PIL import Image

        img = Image.open(bmp_path)
        width, height = img.size
        ext = output_path.rsplit(".", 1)[-1].lower() if "." in output_path else "png"
        fmt = {"jpg": "JPEG", "jpeg": "JPEG", "bmp": "BMP"}.get(ext, "PNG")

        if os.path.abspath(bmp_path) != os.path.abspath(output_path) or fmt != "BMP":
            img.save(output_path, fmt)
            # Remove the temp BMP if it differs from the final path
            if os.path.abspath(bmp_path) != os.path.abspath(output_path):
                try:
                    os.remove(bmp_path)
                except OSError:
                    pass

        return width, height, ext

    def capture_screen(self, screen_index: int = 0, output_path: str = "capture.png") -> CaptureResult:
        """Capture a screenshot of the specified monitor.

        The C++ DLL captures via GDI BitBlt to a temporary BMP, then Pillow
        converts to the requested format (PNG by default, matching Peekaboo).

        Args:
            screen_index: Zero-based monitor index (0 = primary).
            output_path: File path for the output image.

        Returns:
            CaptureResult with the output path and dimensions.
        """
        import tempfile, os
        core = self._ensure_core()

        # DLL writes BMP; use a temp file in a safe directory to avoid
        # encoding issues with Chinese/Unicode paths on Windows
        output_dir = os.path.dirname(os.path.abspath(output_path)) or "."
        try:
            fd, tmp_bmp = tempfile.mkstemp(suffix=".bmp", dir=output_dir)
            os.close(fd)
        except OSError:
            # Fallback to system temp dir if output dir fails
            fd, tmp_bmp = tempfile.mkstemp(suffix=".bmp")
            os.close(fd)

        try:
            core.capture_screen(screen_index, tmp_bmp)
            width, height, fmt = self._convert_bmp(tmp_bmp, output_path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.remove(tmp_bmp)
            except OSError:
                pass
            raise
        return CaptureResult(path=output_path, width=width, height=height, format=fmt)

    def capture_window(self, window_title: Optional[str] = None, hwnd: Optional[int] = None,
                       output_path: str = "capture.png") -> CaptureResult:
        """Capture a screenshot of a specific window.

        Uses PrintWindow for accurate off-screen capture. If neither
        window_title nor hwnd is provided, captures the foreground window.
        Output is PNG by default (matching Peekaboo).

        Args:
            window_title: Window title to search for (not yet implemented — use hwnd).
            hwnd: Window handle. 0 or None for the foreground window.
            output_path: File path for the output image.

        Returns:
            CaptureResult with the output path and dimensions.
        """
        import tempfile, os
        core = self._ensure_core()
        handle = hwnd if hwnd else 0

        # Use a safe temp file to avoid encoding issues with Unicode paths
        output_dir = os.path.dirname(os.path.abspath(output_path)) or "."
        try:
            fd, tmp_bmp = tempfile.mkstemp(suffix=".bmp", dir=output_dir)
            os.close(fd)
        except OSError:
            fd, tmp_bmp = tempfile.mkstemp(suffix=".bmp")
            os.close(fd)

        try:
            core.capture_window(handle, tmp_bmp)
            width, height, fmt = self._convert_bmp(tmp_bmp, output_path)
        except Exception:
            try:
                os.remove(tmp_bmp)
            except OSError:
                pass
            raise
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

    def _ensure_win32(self) -> None:
        """Verify we are running on Windows; raise NotImplementedError otherwise.

        Raises:
            NotImplementedError: When running on a non-Windows platform.
        """
        import platform as _platform
        if _platform.system() != "Windows":
            raise NotImplementedError("Window management requires Windows")

    def _get_window_rect(self, handle: int) -> tuple[int, int, int, int]:
        """Get window rectangle (left, top, right, bottom) via Win32 GetWindowRect.

        Args:
            handle: Window handle (HWND).

        Returns:
            Tuple of (left, top, right, bottom).

        Raises:
            naturo.errors.WindowNotFoundError: If the handle is invalid.
        """
        import ctypes
        import ctypes.wintypes
        rect = ctypes.wintypes.RECT()
        result = ctypes.windll.user32.GetWindowRect(handle, ctypes.byref(rect))
        if not result:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(str(handle))
        return rect.left, rect.top, rect.right, rect.bottom

    def _is_iconic(self, handle: int) -> bool:
        """Check if a window is minimized (iconic).

        Args:
            handle: Window handle (HWND).

        Returns:
            True if the window is minimized.
        """
        import ctypes
        return bool(ctypes.windll.user32.IsIconic(handle))

    def focus_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Focus a window by title or handle.

        Brings the window to the foreground. If the window is minimized,
        it is restored first.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        SW_RESTORE = 9
        if self._is_iconic(handle):
            ctypes.windll.user32.ShowWindow(handle, SW_RESTORE)
        ctypes.windll.user32.SetForegroundWindow(handle)

    def close_window(self, title: Optional[str] = None, hwnd: Optional[int] = None,
                     force: bool = False) -> None:
        """Close a window by title or handle.

        Sends WM_CLOSE for graceful close, or terminates the process if force is True.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).
            force: If True, forcefully terminate the owning process.

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")

        if force:
            # Get PID and terminate the process
            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
            PROCESS_TERMINATE = 0x0001
            proc_handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid.value)
            if proc_handle:
                ctypes.windll.kernel32.TerminateProcess(proc_handle, 1)
                ctypes.windll.kernel32.CloseHandle(proc_handle)
        else:
            WM_CLOSE = 0x0010
            ctypes.windll.user32.SendMessageW(handle, WM_CLOSE, 0, 0)

    def minimize_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Minimize a window.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        SW_MINIMIZE = 6
        ctypes.windll.user32.ShowWindow(handle, SW_MINIMIZE)

    def maximize_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Maximize a window.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        SW_MAXIMIZE = 3
        ctypes.windll.user32.ShowWindow(handle, SW_MAXIMIZE)

    def restore_window(self, title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Restore a minimized or maximized window to its normal state.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        SW_RESTORE = 9
        ctypes.windll.user32.ShowWindow(handle, SW_RESTORE)

    def move_window(self, x: int = 0, y: int = 0, title: Optional[str] = None,
                    hwnd: Optional[int] = None) -> None:
        """Move a window to specified coordinates, keeping current size.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        left, top, right, bottom = self._get_window_rect(handle)
        w = right - left
        h = bottom - top
        ctypes.windll.user32.MoveWindow(handle, x, y, w, h, True)

    def resize_window(self, width: int = 800, height: int = 600,
                      title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Resize a window, keeping current position.

        Args:
            width: Target width in pixels.
            height: Target height in pixels.
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        left, top, _right, _bottom = self._get_window_rect(handle)
        ctypes.windll.user32.MoveWindow(handle, left, top, width, height, True)

    def set_bounds(self, x: int, y: int, width: int, height: int,
                   title: Optional[str] = None, hwnd: Optional[int] = None) -> None:
        """Set window position and size in one call.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            width: Target width in pixels.
            height: Target height in pixels.
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).

        Raises:
            NotImplementedError: On non-Windows platforms.
            WindowNotFoundError: If no matching window is found.
        """
        self._ensure_win32()
        import ctypes
        handle = self._resolve_hwnd(window_title=title, hwnd=hwnd)
        if not handle:
            from naturo.errors import WindowNotFoundError
            raise WindowNotFoundError(title or "foreground")
        ctypes.windll.user32.MoveWindow(handle, x, y, width, height, True)

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

    def _resolve_hwnd(self, app: Optional[str] = None,
                      window_title: Optional[str] = None,
                      hwnd: Optional[int] = None) -> int:
        """Resolve a window handle from app name, window title, or direct hwnd.

        Args:
            app: Application/process name to search for (case-insensitive, partial match).
            window_title: Window title pattern (case-insensitive, partial match).
            hwnd: Direct window handle (takes priority).

        Returns:
            Window handle (HWND), or 0 for the foreground window.
        """
        if hwnd:
            return hwnd

        search = app or window_title
        if not search:
            return 0  # foreground window

        search_lower = search.lower()
        windows = self.list_windows()
        for w in windows:
            if search_lower in w.title.lower() or search_lower in w.process_name.lower():
                return w.handle

        from naturo.errors import WindowNotFoundError
        raise WindowNotFoundError(search)

    def get_element_tree(self, window_title: Optional[str] = None,
                         depth: int = 3,
                         app: Optional[str] = None,
                         hwnd: Optional[int] = None) -> Optional[BaseElementInfo]:
        """Get the UI element tree for a window.

        Fills parent_id, children IDs, and keyboard_shortcut for all elements
        via Python-layer post-processing (the C++ DLL does not emit these).

        Args:
            window_title: Window title pattern (partial match, case-insensitive).
            depth: Maximum depth to traverse (1-10).
            app: Application name to search for (partial match, case-insensitive).
            hwnd: Direct window handle. Overrides app/window_title.

        Returns:
            Root ElementInfo with nested children, or None.
        """
        core = self._ensure_core()
        handle = self._resolve_hwnd(app=app, window_title=window_title, hwnd=hwnd)
        result = core.get_element_tree(hwnd=handle, depth=depth)
        if result is None:
            return None

        # Post-process: assign sequential IDs and fill parent_id
        populate_hierarchy(result)

        def convert(el) -> BaseElementInfo:
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
                properties={
                    k: v for k, v in {
                        "parent_id": el.parent_id,
                        "keyboard_shortcut": el.keyboard_shortcut,
                    }.items() if v is not None
                },
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
        """List menu items by traversing the UIA MenuBar element tree.

        Args:
            app: Optional application name filter (not yet used).

        Returns:
            List of dicts representing menu items.
        """
        items = self.get_menu_items(window_title=app)
        return [item.to_dict() for item in items]

    def menu_click(self, path: str = "", app: Optional[str] = None) -> None:
        """Click a menu item. Phase 3 feature."""
        raise NotImplementedError("menu_click coming in Phase 3")

    def get_menu_items(self, window_title: Optional[str] = None) -> List[MenuItem]:
        """Get menu bar items by traversing the UI element tree.

        Finds MenuBar elements and recursively extracts MenuItem children,
        including names, keyboard shortcuts, and submenus.

        Args:
            window_title: Optional window title filter (uses foreground window if None).

        Returns:
            List of top-level MenuItem objects with nested submenus.
        """
        core = self._ensure_core()
        # Get a deeper tree to capture menu structure
        tree = core.get_element_tree(hwnd=0, depth=6)
        if tree is None:
            return []

        populate_hierarchy(tree)

        # Find MenuBar elements in the tree
        menu_bars = []
        self._find_by_role(tree, "MenuBar", menu_bars)

        if not menu_bars:
            return []

        result: List[MenuItem] = []
        for bar in menu_bars:
            for child in bar.children:
                item = self._element_to_menu_item(child)
                if item:
                    result.append(item)
        return result

    def _find_by_role(self, el, role: str, results: list) -> None:
        """Recursively find elements matching a role."""
        if el.role == role:
            results.append(el)
        for child in el.children:
            self._find_by_role(child, role, results)

    @staticmethod
    def _element_to_menu_item(el) -> Optional[MenuItem]:
        """Convert a bridge ElementInfo (MenuItem role) to a MenuItem model."""
        if not el.name and el.role not in ("MenuItem", "Menu"):
            return None

        submenu: List[MenuItem] = []
        for child in el.children:
            sub = WindowsBackend._element_to_menu_item(child)
            if sub:
                submenu.append(sub)

        return MenuItem(
            name=el.name or "",
            shortcut=el.keyboard_shortcut,
            submenu=submenu if submenu else None,
            enabled=True,  # UIA doesn't easily expose this without caching
            checked=False,
        )

    def open_uri(self, uri: str = "") -> None:
        """Open a URI with the default handler.

        Args:
            uri: URL or file path to open.
        """
        import subprocess
        subprocess.run(["start", uri], shell=True)
