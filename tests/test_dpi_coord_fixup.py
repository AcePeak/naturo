"""Tests for DPI coordinate fixup — fix for #613.

Verifies that _fixup_element_coords detects and corrects large negative
coordinates on UWP apps with high-DPI 4K displays.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import patch

import pytest


@dataclass
class _MockElementInfo:
    """Minimal ElementInfo mock for testing coordinate fixup."""
    id: str = ""
    role: str = ""
    name: str = ""
    value: Optional[str] = None
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    children: list = field(default_factory=list)
    parent_id: Optional[str] = None
    keyboard_shortcut: Optional[str] = None
    hwnd: Optional[int] = None


def _make_uwp_tree_negative_coords():
    """Create a mock UWP element tree with the #613 negative coords pattern.

    Simulates: Window (0,0 0x0) → Pane (-31991,-31888 2862x1370)
    Actual window is at (777,880) on a 4K display.
    """
    menuitem = _MockElementInfo(
        role="MenuItem", name="File", x=-31985, y=-31938, width=72, height=48,
    )
    document = _MockElementInfo(
        role="Document", name="Editor", x=-31991, y=-31888, width=2862, height=1370,
    )
    pane = _MockElementInfo(
        role="Pane", name="", x=-31991, y=-31888, width=2862, height=1370,
        children=[document, menuitem],
    )
    root = _MockElementInfo(
        role="Window", name="*hello - Notepad", x=0, y=0, width=0, height=0,
        children=[pane],
    )
    return root


def _make_normal_tree():
    """Create a normal Win32 app tree with correct coordinates."""
    button = _MockElementInfo(
        role="Button", name="OK", x=100, y=200, width=80, height=30,
    )
    root = _MockElementInfo(
        role="Window", name="Chrome", x=0, y=0, width=1920, height=1080,
        children=[button],
    )
    return root


def _make_zero_root_normal_children():
    """Zero-bounds root but children with small/normal coordinates."""
    button = _MockElementInfo(
        role="Button", name="OK", x=100, y=200, width=80, height=30,
    )
    root = _MockElementInfo(
        role="Window", name="App", x=0, y=0, width=0, height=0,
        children=[button],
    )
    return root


class TestFixupElementCoords:
    """Test _fixup_element_coords on WindowsBackend."""

    def _get_backend(self):
        """Create a WindowsBackend with mocked DPI init."""
        with patch.object(_WindowsBackendClass, "_ensure_dpi_awareness"):
            return _WindowsBackendClass()

    def test_32768_wrap_correction(self):
        """Negative coords from 16-bit wrap should be corrected."""
        backend = self._get_backend()
        root = _make_uwp_tree_negative_coords()

        # Window is at physical position (777, 880) with size 2862x1370
        with patch.object(backend, "_get_window_rect", return_value=(777, 880, 3639, 2250)):
            result = backend._fixup_element_coords(root, handle=12345)

        # Root should now have window bounds
        assert result.x == 777
        assert result.y == 880
        assert result.width == 2862
        assert result.height == 1370

        # Pane: -31991 + 32768 = 777
        pane = result.children[0]
        assert pane.x == 777
        assert pane.y == 880

        # Document inside pane
        doc = pane.children[0]
        assert doc.x == 777
        assert doc.y == 880

        # MenuItem: -31985 + 32768 = 783
        menu = pane.children[1]
        assert menu.x == 783
        assert menu.y == 830  # -31938 + 32768 = 830

    def test_normal_tree_no_change(self):
        """Normal tree coordinates should not be modified."""
        backend = self._get_backend()
        root = _make_normal_tree()

        result = backend._fixup_element_coords(root, handle=12345)

        assert result.x == 0
        assert result.y == 0
        assert result.width == 1920
        assert result.children[0].x == 100
        assert result.children[0].y == 200

    def test_zero_root_small_children_no_change(self):
        """Zero-bounds root with normal children should only fix root bounds."""
        backend = self._get_backend()
        root = _make_zero_root_normal_children()

        with patch.object(backend, "_get_window_rect", return_value=(50, 50, 850, 650)):
            result = backend._fixup_element_coords(root, handle=12345)

        # Root should NOT be fixed (children have normal coords > -1000)
        # Actually, children x=100, y=200, so first_child.x >= -1000 → returns early
        assert result.children[0].x == 100
        assert result.children[0].y == 200

    def test_get_window_rect_fails_gracefully(self):
        """If GetWindowRect fails, no fixup applied."""
        backend = self._get_backend()
        root = _make_uwp_tree_negative_coords()

        with patch.object(backend, "_get_window_rect", side_effect=Exception("no window")):
            result = backend._fixup_element_coords(root, handle=12345)

        # Coords should be unchanged
        assert result.children[0].x == -31991

    def test_minimized_window_no_fixup(self):
        """Minimized window (zero size rect) should not apply fixup."""
        backend = self._get_backend()
        root = _make_uwp_tree_negative_coords()

        with patch.object(backend, "_get_window_rect", return_value=(0, 0, 0, 0)):
            result = backend._fixup_element_coords(root, handle=12345)

        assert result.children[0].x == -31991

    def test_direct_offset_correction(self):
        """Non-32768 offset should use direct window position correction."""
        backend = self._get_backend()

        # Simulate a different offset pattern (not 32768 multiple)
        pane = _MockElementInfo(
            role="Pane", x=-5000, y=-3000, width=1920, height=1080,
        )
        root = _MockElementInfo(
            role="Window", x=0, y=0, width=0, height=0,
            children=[pane],
        )

        # Window at (500, 300), same size as pane
        with patch.object(backend, "_get_window_rect", return_value=(500, 300, 2420, 1380)):
            result = backend._fixup_element_coords(root, handle=12345)

        # Root gets window bounds
        assert result.x == 500
        assert result.y == 300
        # Pane: offset = 500 - (-5000) = 5500
        assert result.children[0].x == 500
        assert result.children[0].y == 300

    def test_empty_children_no_crash(self):
        """Root with no children should not crash."""
        backend = self._get_backend()
        root = _MockElementInfo(
            role="Window", x=0, y=0, width=0, height=0, children=[],
        )
        result = backend._fixup_element_coords(root, handle=12345)
        assert result is root


# Import the backend class — handle non-Windows gracefully
try:
    from naturo.backends.windows import WindowsBackend as _WindowsBackendClass
except Exception:
    # On non-Windows, WindowsBackend init might fail. Use a mock-friendly subclass.
    import sys
    # Create a minimal WindowsBackend that skips DPI init
    from naturo.backends import windows as _win_mod

    class _FakeWindowsBackend:
        """Minimal WindowsBackend for testing coordinate fixup on non-Windows."""
        _dpi_aware = False
        _core = None
        _initialized = False

        def _ensure_dpi_awareness(self):
            pass

        # Borrow the methods we need to test
        _fixup_element_coords = _win_mod.WindowsBackend._fixup_element_coords
        _iter_elements = _win_mod.WindowsBackend._iter_elements
        _get_window_rect = _win_mod.WindowsBackend._get_window_rect

    _WindowsBackendClass = _FakeWindowsBackend
