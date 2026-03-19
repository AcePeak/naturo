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
class CaptureResult:
    """Screenshot result."""
    path: str
    width: int
    height: int
    format: str           # png, jpg


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

    # === UI Element Inspection ===
    @abstractmethod
    def find_element(self, selector: str, window_title: str = None) -> Optional[ElementInfo]:
        ...

    @abstractmethod
    def get_element_tree(self, window_title: str = None, depth: int = 3) -> Optional[ElementInfo]:
        ...

    # === Input ===
    @abstractmethod
    def click(self, x: int = None, y: int = None, element_id: str = None,
              button: str = "left", double: bool = False, input_mode: str = "normal") -> None:
        ...

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
