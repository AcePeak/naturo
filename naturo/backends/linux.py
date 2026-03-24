"""Linux backend — AT-SPI2 + xdotool/ydotool."""
from __future__ import annotations

from naturo.backends.base import Backend, WindowInfo, ElementInfo, CaptureResult
from typing import Optional


class LinuxBackend(Backend):
    """Linux automation via AT-SPI2 (accessibility) + xdotool/ydotool (input).

    Strategy:
    - X11: xdotool for input, AT-SPI2 for element inspection
    - Wayland: ydotool for input, AT-SPI2 for element inspection
    - Compatible with GNOME, KDE, and national OS (UOS/Kylin/openEuler)
    """

    @property
    def platform_name(self) -> str:
        return "linux"

    @property
    def capabilities(self) -> dict:
        return {
            "platform": "linux",
            "input_modes": ["normal"],
            "accessibility": ["atspi"],  # AT-SPI2
            "extensions": [],
            "display_server": self._detect_display_server(),
        }

    def _detect_display_server(self) -> str:
        import os
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        elif os.environ.get("DISPLAY"):
            return "x11"
        return "headless"

    # All methods raise NotImplementedError — Phase 7 will implement
    def list_monitors(self):
        raise NotImplementedError("Linux backend coming in Phase 7")

    def capture_screen(self, screen_index=0, output_path="capture.png") -> CaptureResult:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def capture_window(self, window_title=None, hwnd=None, output_path="capture.png") -> CaptureResult:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def list_windows(self) -> list[WindowInfo]:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def focus_window(self, title=None, hwnd=None) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def close_window(self, title=None, hwnd=None) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def minimize_window(self, title=None, hwnd=None) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def maximize_window(self, title=None, hwnd=None) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def move_window(self, x=0, y=0, title=None, hwnd=None) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def resize_window(self, width=800, height=600, title=None, hwnd=None) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def set_bounds(self, x=0, y=0, width=800, height=600, title=None, hwnd=None) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def restore_window(self, title=None, hwnd=None) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def find_element(self, selector="", window_title=None) -> Optional[ElementInfo]:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def get_element_tree(self, window_title=None, depth=3) -> Optional[ElementInfo]:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def click(self, x=None, y=None, element_id=None, button="left", double=False, input_mode="normal") -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def type_text(self, text="", delay_ms=5, profile="human", wpm=120, input_mode="normal") -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def press_key(self, key="", input_mode="normal") -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def hotkey(self, *keys, hold_duration_ms=50) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def scroll(self, direction="down", amount=3, x=None, y=None, smooth=False) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def drag(self, from_x=0, from_y=0, to_x=0, to_y=0, duration_ms=500, steps=10) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def move_mouse(self, x=0, y=0) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def clipboard_get(self) -> str:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def clipboard_set(self, text="") -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def list_apps(self) -> list[dict]:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def launch_app(self, name="") -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def quit_app(self, name="", force=False) -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def open_uri(self, uri="") -> None:
        raise NotImplementedError("Linux backend coming in Phase 7")

    def get_element_value(self, ref=None, automation_id=None, role=None,
                          name=None, app=None, window_title=None, hwnd=None) -> Optional[dict]:
        raise NotImplementedError("Linux backend coming in Phase 7")
