"""Tests for naturo.backends.windows._core — CoreMixin DPI and coordinate logic."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# We can't instantiate CoreMixin directly (it calls ctypes.windll on __init__),
# so we create a test subclass that skips the DPI init on non-Windows.
class _TestCoreMixin:
    """Minimal CoreMixin for testing without Windows DLL calls."""

    def __init__(self):
        self._core = None
        self._initialized = False
        self._dpi_aware = False

    # Import the methods we want to test
    from naturo.backends.windows._core import CoreMixin as _CM

    get_dpi_scale = _CM.get_dpi_scale
    physical_to_logical = _CM.physical_to_logical
    logical_to_physical = _CM.logical_to_physical
    _fixup_element_coords = _CM._fixup_element_coords
    _iter_elements = staticmethod(_CM._iter_elements)
    platform_name = _CM.platform_name
    capabilities = _CM.capabilities


def _make_element(x=0, y=0, width=100, height=50, children=None):
    """Create a mock ElementInfo-like object."""
    el = SimpleNamespace(x=x, y=y, width=width, height=height,
                         children=children or [])
    return el


@pytest.fixture
def mixin():
    return _TestCoreMixin()


# ── Properties ───────────────────────────────────


class TestCoreProperties:
    def test_platform_name(self, mixin):
        assert mixin.platform_name == "windows"

    def test_capabilities(self, mixin):
        caps = mixin.capabilities
        assert caps["platform"] == "windows"
        assert "normal" in caps["input_modes"]
        assert "hardware" in caps["input_modes"]
        assert "uia" in caps["accessibility"]
        assert "msaa" in caps["accessibility"]


# ── get_dpi_scale ────────────────────────────────


class TestGetDpiScale:
    def test_returns_scale_from_monitors(self, mixin):
        monitor = SimpleNamespace(scale_factor=1.5)
        mixin.list_monitors = MagicMock(return_value=[monitor])
        assert mixin.get_dpi_scale(0) == 1.5

    def test_returns_1_for_invalid_index(self, mixin):
        monitor = SimpleNamespace(scale_factor=2.0)
        mixin.list_monitors = MagicMock(return_value=[monitor])
        assert mixin.get_dpi_scale(5) == 1.0

    def test_returns_1_on_exception(self, mixin):
        mixin.list_monitors = MagicMock(side_effect=RuntimeError("no monitors"))
        assert mixin.get_dpi_scale(0) == 1.0


# ── Coordinate conversion ───────────────────────


class TestCoordinateConversion:
    def test_physical_to_logical_at_150(self, mixin):
        mixin.list_monitors = MagicMock(
            return_value=[SimpleNamespace(scale_factor=1.5)]
        )
        lx, ly = mixin.physical_to_logical(300, 150, screen_index=0)
        assert lx == 200
        assert ly == 100

    def test_physical_to_logical_at_100_passthrough(self, mixin):
        mixin.list_monitors = MagicMock(
            return_value=[SimpleNamespace(scale_factor=1.0)]
        )
        lx, ly = mixin.physical_to_logical(300, 150, screen_index=0)
        assert (lx, ly) == (300, 150)

    def test_logical_to_physical_at_200(self, mixin):
        mixin.list_monitors = MagicMock(
            return_value=[SimpleNamespace(scale_factor=2.0)]
        )
        px, py = mixin.logical_to_physical(100, 75, screen_index=0)
        assert px == 200
        assert py == 150

    def test_logical_to_physical_at_100_passthrough(self, mixin):
        mixin.list_monitors = MagicMock(
            return_value=[SimpleNamespace(scale_factor=1.0)]
        )
        px, py = mixin.logical_to_physical(100, 75, screen_index=0)
        assert (px, py) == (100, 75)

    def test_zero_scale_returns_unchanged(self, mixin):
        mixin.list_monitors = MagicMock(
            return_value=[SimpleNamespace(scale_factor=0)]
        )
        assert mixin.physical_to_logical(100, 200) == (100, 200)
        assert mixin.logical_to_physical(100, 200) == (100, 200)


# ── _iter_elements ───────────────────────────────


class TestIterElements:
    def test_single_element(self):
        root = _make_element()
        elements = list(_TestCoreMixin._iter_elements(root))
        assert len(elements) == 1
        assert elements[0] is root

    def test_tree_traversal(self):
        child1 = _make_element(x=10)
        child2 = _make_element(x=20)
        grandchild = _make_element(x=30)
        child1.children = [grandchild]
        root = _make_element(children=[child1, child2])

        elements = list(_TestCoreMixin._iter_elements(root))
        assert len(elements) == 4
        assert elements[0] is root
        # Depth-first: child1, grandchild, child2
        assert elements[1] is child1
        assert elements[2] is grandchild
        assert elements[3] is child2


# ── _fixup_element_coords ───────────────────────


class TestFixupElementCoords:
    def test_no_fixup_when_root_has_nonzero_bounds(self, mixin):
        root = _make_element(x=100, y=200, width=800, height=600)
        result = mixin._fixup_element_coords(root, handle=12345)
        assert result.x == 100  # Unchanged

    def test_no_fixup_when_no_children(self, mixin):
        root = _make_element(x=0, y=0, width=0, height=0, children=[])
        result = mixin._fixup_element_coords(root, handle=12345)
        assert result is root

    def test_no_fixup_when_children_have_normal_coords(self, mixin):
        child = _make_element(x=50, y=60)
        root = _make_element(x=0, y=0, width=0, height=0, children=[child])
        result = mixin._fixup_element_coords(root, handle=12345)
        assert child.x == 50  # Unchanged

    def test_fixup_32768_wrap(self, mixin):
        # Simulate UWP 16-bit coordinate wrap: child at -31991 should be ~777
        child = _make_element(x=-31991, y=-32268, width=800, height=600)
        root = _make_element(x=0, y=0, width=0, height=0, children=[child])

        # Window is at (777, 500, 1577, 1100)
        mixin._get_window_rect = MagicMock(return_value=(777, 500, 1577, 1100))
        result = mixin._fixup_element_coords(root, handle=12345)

        # Root should get window bounds
        assert result.x == 777
        assert result.y == 500
        assert result.width == 800
        assert result.height == 600

        # Child should be offset by 32768
        assert child.x == -31991 + 32768  # 777
        assert child.y == -32268 + 32768  # 500

    def test_fixup_direct_offset(self, mixin):
        # Child has large negative coords but 32768 multiples don't work
        child = _make_element(x=-5000, y=-5000, width=800, height=600)
        root = _make_element(x=0, y=0, width=0, height=0, children=[child])

        mixin._get_window_rect = MagicMock(return_value=(100, 100, 900, 700))
        result = mixin._fixup_element_coords(root, handle=12345)

        # Should use direct offset: win_left - child_x = 100 - (-5000) = 5100
        assert child.x == 100
        assert child.y == 100

    def test_fixup_skipped_when_window_rect_fails(self, mixin):
        child = _make_element(x=-31991, y=-32268)
        root = _make_element(x=0, y=0, width=0, height=0, children=[child])

        mixin._get_window_rect = MagicMock(side_effect=RuntimeError("no rect"))
        result = mixin._fixup_element_coords(root, handle=12345)
        assert child.x == -31991  # Unchanged

    def test_fixup_skipped_when_window_minimized(self, mixin):
        child = _make_element(x=-31991, y=-32268)
        root = _make_element(x=0, y=0, width=0, height=0, children=[child])

        # Minimized window: zero-size rect
        mixin._get_window_rect = MagicMock(return_value=(0, 0, 0, 0))
        result = mixin._fixup_element_coords(root, handle=12345)
        assert child.x == -31991  # Unchanged
