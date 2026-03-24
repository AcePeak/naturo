"""Abstract backend interface — all platforms must implement this."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import platform


@dataclass
class WindowInfo:
    """Cross-platform window information."""
    handle: int           # HWND on Windows, window_id on macOS, XID on Linux
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
    """Cross-platform UI element information."""
    id: str               # Backend-specific element identifier
    role: str             # Button, Edit, Text, etc.
    name: str
    value: Optional[str]
    x: int
    y: int
    width: int
    height: int
    children: list        # list[ElementInfo]
    properties: dict      # Backend-specific properties


@dataclass
class MonitorInfo:
    """Cross-platform monitor/display information."""
    index: int            # Zero-based monitor index
    name: str             # Display device name (e.g., "\\\\.\\DISPLAY1")
    x: int                # Left edge in virtual screen coordinates
    y: int                # Top edge in virtual screen coordinates
    width: int            # Width in pixels
    height: int           # Height in pixels
    is_primary: bool      # Whether this is the primary monitor
    scale_factor: float   # DPI scale factor (1.0 = 100%, 1.5 = 150%, 2.0 = 200%)
    dpi: int              # Effective DPI (96 = 100%)
    work_area: Optional[dict] = None  # {"x": int, "y": int, "width": int, "height": int}


@dataclass
class CaptureResult:
    """Screenshot result."""
    path: str
    width: int
    height: int
    format: str           # png, jpg
    scale_factor: float = 1.0   # DPI scale factor of captured monitor
    dpi: int = 96               # Effective DPI of captured monitor


class Backend(ABC):
    """Abstract base for platform-specific automation backends.

    Each platform (Windows, macOS, Linux) provides a concrete implementation.
    The unified API layer calls these methods without knowing the platform.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return platform identifier: 'windows', 'macos', 'linux'."""
        ...

    @property
    def capabilities(self) -> dict:
        """Return backend capabilities and platform-specific features."""
        return {
            "platform": self.platform_name,
            "input_modes": ["normal"],  # Override to add hardware/hook
            "accessibility": [],         # Override: uia, msaa, ia2, atspi, ax
            "extensions": [],            # Override: excel, java, sap, etc.
        }

    # === Monitor ===
    @abstractmethod
    def list_monitors(self) -> list[MonitorInfo]:
        """Enumerate connected monitors/displays.

        Returns:
            List of MonitorInfo, ordered by index (primary first).
        """
        ...

    def find_monitor_for_point(self, x: int, y: int) -> Optional[MonitorInfo]:
        """Find which monitor contains the given screen coordinates.

        Uses the monitor's bounding rectangle from list_monitors().
        Returns None if the point is outside all monitors.

        Args:
            x: X coordinate in virtual screen space.
            y: Y coordinate in virtual screen space.

        Returns:
            MonitorInfo for the containing monitor, or None.
        """
        try:
            monitors = self.list_monitors()
        except (NotImplementedError, Exception):
            return None
        for m in monitors:
            if m.x <= x < m.x + m.width and m.y <= y < m.y + m.height:
                return m
        return None

    # === Capture ===
    @abstractmethod
    def capture_screen(self, screen_index: int = 0, output_path: str = "capture.png") -> CaptureResult:
        ...

    @abstractmethod
    def capture_window(self, window_title: str = None, hwnd: int = None, output_path: str = "capture.png") -> CaptureResult:
        ...

    # === Window Management ===
    @abstractmethod
    def list_windows(self) -> list[WindowInfo]:
        ...

    @abstractmethod
    def focus_window(self, title: str = None, hwnd: int = None) -> None:
        ...

    @abstractmethod
    def close_window(self, title: str = None, hwnd: int = None) -> None:
        ...

    @abstractmethod
    def minimize_window(self, title: str = None, hwnd: int = None) -> None:
        ...

    @abstractmethod
    def maximize_window(self, title: str = None, hwnd: int = None) -> None:
        ...

    @abstractmethod
    def move_window(self, x: int, y: int, title: str = None, hwnd: int = None) -> None:
        ...

    @abstractmethod
    def resize_window(self, width: int, height: int, title: str = None, hwnd: int = None) -> None:
        ...

    @abstractmethod
    def set_bounds(self, x: int, y: int, width: int, height: int,
                   title: str = None, hwnd: int = None) -> None:
        """Set window position and size in one call.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            width: Target width in pixels.
            height: Target height in pixels.
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).
        """
        ...

    @abstractmethod
    def restore_window(self, title: str = None, hwnd: int = None) -> None:
        """Restore a minimized or maximized window to its normal state.

        Args:
            title: Window title pattern (partial, case-insensitive).
            hwnd: Direct window handle (takes priority over title).
        """
        ...

    # === UI Element Inspection ===
    @abstractmethod
    def find_element(self, selector: str, window_title: str = None) -> Optional[ElementInfo]:
        ...

    @abstractmethod
    def get_element_tree(self, window_title: str = None, depth: int = 3,
                         backend: str = "uia") -> Optional[ElementInfo]:
        ...

    # === Input ===
    @abstractmethod
    def get_element_value(
        self,
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        app: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> Optional[dict]:
        """Read the current value/text of a UI element.

        Uses UIA patterns (Value, Toggle, Selection, RangeValue, Text) to
        retrieve the element's current value.

        Args:
            ref: Element ref from snapshot (e.g. ``"e47"``).
            automation_id: UIA AutomationId.
            role: Element role (e.g. ``"Edit"``).
            name: Element name.
            app: Application name (partial match) for window targeting.
            window_title: Window title for targeting.
            hwnd: Window handle.

        Returns:
            Dict with value, pattern, role, name, automation_id, and bounds;
            or ``None`` if element not found.
        """
        raise NotImplementedError

    def click(self, x: int = None, y: int = None, element_id: str = None,
              button: str = "left", double: bool = False, input_mode: str = "normal") -> None:
        ...

    def invoke_element(self, name: str, role: str) -> bool:
        """Invoke a UI element by name and role using a platform-specific pattern.

        This is a fallback for elements whose bounding rects are zero-size
        (e.g. after window state changes).  The default implementation
        returns ``False``; platform backends may override.

        Args:
            name: The element's accessible name.
            role: The element's control type / role.

        Returns:
            True if the element was found and invoked, False otherwise.
        """
        return False

    @abstractmethod
    def type_text(self, text: str, delay_ms: int = 5, profile: str = "human",
                  wpm: int = 120, input_mode: str = "normal") -> None:
        ...

    @abstractmethod
    def press_key(self, key: str, input_mode: str = "normal") -> None:
        ...

    @abstractmethod
    def hotkey(self, *keys: str, hold_duration_ms: int = 50) -> None:
        ...

    @abstractmethod
    def scroll(self, direction: str = "down", amount: int = 3,
               x: int = None, y: int = None, smooth: bool = False) -> None:
        ...

    @abstractmethod
    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int,
             duration_ms: int = 500, steps: int = 10) -> None:
        ...

    @abstractmethod
    def move_mouse(self, x: int, y: int) -> None:
        ...

    # === Clipboard ===
    @abstractmethod
    def clipboard_get(self) -> str:
        ...

    @abstractmethod
    def clipboard_set(self, text: str) -> None:
        ...

    # === Application Control ===
    @abstractmethod
    def list_apps(self) -> list[dict]:
        ...

    @abstractmethod
    def launch_app(self, name: str) -> None:
        ...

    @abstractmethod
    def quit_app(self, name: str, force: bool = False) -> None:
        ...

    # === Menu ===
    def menu_list(self, app: str = None) -> list[dict]:
        """List menu items. Not all platforms support this."""
        raise NotImplementedError(f"menu_list not supported on {self.platform_name}")

    def menu_click(self, path: str, app: str = None) -> None:
        """Click a menu item by path. Not all platforms support this."""
        raise NotImplementedError(f"menu_click not supported on {self.platform_name}")

    def get_menu_items(self, window_title: Optional[str] = None) -> list:
        """Get structured menu items from the application menu bar.

        Returns:
            List of MenuItem objects (from naturo.models.menu).
        """
        raise NotImplementedError(f"get_menu_items not supported on {self.platform_name}")

    # === Open ===
    @abstractmethod
    def open_uri(self, uri: str) -> None:
        """Open a URL or file with default application."""
        ...

    # === Dialog ===
    def detect_dialogs(
        self,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> list:
        """Detect active dialog windows.

        Args:
            app: Filter by owner application name (partial match).
            hwnd: Filter by specific dialog window handle.

        Returns:
            List of DialogInfo objects for detected dialogs.
        """
        raise NotImplementedError(f"detect_dialogs not supported on {self.platform_name}")

    def dialog_click_button(
        self,
        button: str,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Click a button in a dialog.

        Args:
            button: Button text to click (e.g., "OK", "Cancel", "Yes").
            app: Owner application name filter.
            hwnd: Specific dialog window handle.

        Returns:
            Dict with result info.
        """
        raise NotImplementedError(f"dialog_click_button not supported on {self.platform_name}")

    def dialog_set_input(
        self,
        text: str,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Type text into a dialog's input field.

        Args:
            text: Text to enter.
            app: Owner application name filter.
            hwnd: Specific dialog window handle.

        Returns:
            Dict with result info.
        """
        raise NotImplementedError(f"dialog_set_input not supported on {self.platform_name}")

    # === Taskbar ===
    def taskbar_list(self) -> list[dict]:
        """List items on the taskbar.

        Returns:
            List of dicts with keys: name, hwnd, is_active, is_pinned.
        """
        raise NotImplementedError(f"taskbar_list not supported on {self.platform_name}")

    def taskbar_click(self, name: str) -> dict:
        """Click a taskbar item by name.

        Args:
            name: Application name or window title (partial, case-insensitive).

        Returns:
            Dict with result info.
        """
        raise NotImplementedError(f"taskbar_click not supported on {self.platform_name}")

    # === System Tray ===
    def tray_list(self) -> list[dict]:
        """List system tray (notification area) icons.

        Returns:
            List of dicts with keys: name, tooltip, is_visible.
        """
        raise NotImplementedError(f"tray_list not supported on {self.platform_name}")

    def tray_click(
        self,
        name: str,
        button: str = "left",
        double: bool = False,
    ) -> dict:
        """Click a system tray icon.

        Args:
            name: Tray icon tooltip or name (partial, case-insensitive).
            button: Mouse button ('left' or 'right').
            double: Whether to double-click.

        Returns:
            Dict with result info.
        """
        raise NotImplementedError(f"tray_click not supported on {self.platform_name}")

    # === Virtual Desktop ===
    def virtual_desktop_list(self) -> list[dict]:
        """List all virtual desktops.

        Returns:
            List of dicts with keys: index, name, is_current, id.
        """
        raise NotImplementedError(f"virtual_desktop_list not supported on {self.platform_name}")

    def virtual_desktop_switch(self, index: int) -> dict:
        """Switch to a virtual desktop by index.

        Args:
            index: Zero-based desktop index.

        Returns:
            Dict with switched desktop info.
        """
        raise NotImplementedError(f"virtual_desktop_switch not supported on {self.platform_name}")

    def virtual_desktop_create(self, name: Optional[str] = None) -> dict:
        """Create a new virtual desktop.

        Args:
            name: Optional name for the new desktop.

        Returns:
            Dict with new desktop info.
        """
        raise NotImplementedError(f"virtual_desktop_create not supported on {self.platform_name}")

    def virtual_desktop_close(self, index: Optional[int] = None) -> dict:
        """Close a virtual desktop.

        Args:
            index: Zero-based desktop index. Closes current if None.

        Returns:
            Dict with closed desktop info.
        """
        raise NotImplementedError(f"virtual_desktop_close not supported on {self.platform_name}")

    def virtual_desktop_move_window(
        self,
        desktop_index: int,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Move a window to a different virtual desktop.

        Args:
            desktop_index: Target desktop index.
            app: Application name (partial match).
            hwnd: Window handle.

        Returns:
            Dict with result info.
        """
        raise NotImplementedError(f"virtual_desktop_move_window not supported on {self.platform_name}")


def get_backend() -> Backend:
    """Auto-detect platform and return the appropriate backend."""
    system = platform.system()
    if system == "Windows":
        from naturo.backends.windows import WindowsBackend
        return WindowsBackend()
    elif system == "Darwin":
        from naturo.backends.macos import MacOSBackend
        return MacOSBackend()
    elif system == "Linux":
        from naturo.backends.linux import LinuxBackend
        return LinuxBackend()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
