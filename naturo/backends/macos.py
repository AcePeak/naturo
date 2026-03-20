"""macOS backend — wraps Peekaboo CLI, with fallback to pyobjc."""
from __future__ import annotations

from naturo.backends.base import Backend, WindowInfo, ElementInfo, CaptureResult
from typing import Optional
import shutil


class MacOSBackend(Backend):
    """macOS automation via Peekaboo CLI (phase 1) or pyobjc (future).

    Strategy:
    - Phase 6: Wrap Peekaboo CLI via subprocess (easy, leverages existing tool)
    - Future: Direct pyobjc calls to Accessibility API (independent, no external dep)
    """

    def __init__(self):
        self._peekaboo_path = shutil.which("peekaboo")

    @property
    def platform_name(self) -> str:
        return "macos"

    @property
    def capabilities(self) -> dict:
        has_peekaboo = self._peekaboo_path is not None
        return {
            "platform": "macos",
            "input_modes": ["normal"],
            "accessibility": ["ax"],  # macOS Accessibility API
            "extensions": ["dock", "space", "menubar"],
            "peekaboo_available": has_peekaboo,
        }

    # All methods raise NotImplementedError — Phase 6 will implement
    def capture_screen(self, screen_index=0, output_path="capture.png") -> CaptureResult:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def capture_window(self, window_title=None, hwnd=None, output_path="capture.png") -> CaptureResult:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def list_windows(self) -> list[WindowInfo]:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def focus_window(self, title=None, hwnd=None) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def close_window(self, title=None, hwnd=None) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def minimize_window(self, title=None, hwnd=None) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def maximize_window(self, title=None, hwnd=None) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def move_window(self, x=0, y=0, title=None, hwnd=None) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def resize_window(self, width=800, height=600, title=None, hwnd=None) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def set_bounds(self, x=0, y=0, width=800, height=600, title=None, hwnd=None) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def restore_window(self, title=None, hwnd=None) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def find_element(self, selector="", window_title=None) -> Optional[ElementInfo]:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def get_element_tree(self, window_title=None, depth=3) -> Optional[ElementInfo]:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def click(self, x=None, y=None, element_id=None, button="left", double=False, input_mode="normal") -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def type_text(self, text="", delay_ms=5, profile="human", wpm=120, input_mode="normal") -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def press_key(self, key="", input_mode="normal") -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def hotkey(self, *keys, hold_duration_ms=50) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def scroll(self, direction="down", amount=3, x=None, y=None, smooth=False) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def drag(self, from_x=0, from_y=0, to_x=0, to_y=0, duration_ms=500, steps=10) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def move_mouse(self, x=0, y=0) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def clipboard_get(self) -> str:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def clipboard_set(self, text="") -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def list_apps(self) -> list[dict]:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def launch_app(self, name="") -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def quit_app(self, name="", force=False) -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")

    def open_uri(self, uri="") -> None:
        raise NotImplementedError("macOS backend coming in Phase 6")
