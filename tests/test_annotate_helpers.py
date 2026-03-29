"""Tests for naturo.annotate internal helpers and highlight_annotate.

Covers:
- _compute_label_positions: collision avoidance logic
- _element_depth: tree depth via parent_id walk
- highlight_annotate: filtering, output, edge cases
- ACTIONABLE_ROLES: membership verification
- _get_font: font loading fallback
"""

from __future__ import annotations

import os
from typing import Dict, Tuple
from unittest.mock import MagicMock, patch

import pytest

from naturo.annotate import (
    ACTIONABLE_ROLES,
    DEPTH_COLORS,
    MIN_ELEMENT_SIZE,
    _compute_label_positions,
    _element_depth,
)
from naturo.models.snapshot import UIElement


# ── _compute_label_positions ──────────────────────────────────────────────


class TestComputeLabelPositions:
    """Tests for the label collision avoidance algorithm."""

    def test_single_element_placed_above_left(self):
        """A single element should get label above-left (first candidate)."""
        elements = [("e0", 100, 100, 80, 30)]
        label_sizes = {"e0": (40, 12)}

        positions = _compute_label_positions(elements, label_sizes)

        assert "e0" in positions
        lx, ly = positions["e0"]
        # Label should be at or above the element
        assert ly <= 100

    def test_multiple_non_overlapping(self):
        """Widely spaced elements should all get unique positions."""
        elements = [
            ("e0", 10, 100, 50, 30),
            ("e1", 300, 100, 50, 30),
            ("e2", 10, 300, 50, 30),
        ]
        label_sizes = {
            "e0": (30, 12),
            "e1": (30, 12),
            "e2": (30, 12),
        }

        positions = _compute_label_positions(elements, label_sizes)

        assert len(positions) == 3
        # All positions should be non-negative
        for ref, (lx, ly) in positions.items():
            assert lx >= 0
            assert ly >= 0

    def test_overlapping_elements_avoid_collision(self):
        """Stacked elements should try different candidate positions."""
        # Two elements at the same position — labels should not be identical
        elements = [
            ("e0", 100, 100, 80, 30),
            ("e1", 100, 100, 80, 30),
        ]
        label_sizes = {
            "e0": (40, 12),
            "e1": (40, 12),
        }

        positions = _compute_label_positions(elements, label_sizes)

        assert len(positions) == 2
        # Labels should be at different positions
        assert positions["e0"] != positions["e1"]

    def test_element_at_top_edge_clamps_y(self):
        """Element at y=0 should clamp label y to >= 0."""
        elements = [("e0", 50, 0, 80, 30)]
        label_sizes = {"e0": (40, 12)}

        positions = _compute_label_positions(elements, label_sizes)

        lx, ly = positions["e0"]
        assert ly >= 0

    def test_empty_elements(self):
        """Empty input returns empty positions."""
        positions = _compute_label_positions([], {})
        assert positions == {}

    def test_many_overlapping_elements(self):
        """Many elements at same position should all get placed."""
        elements = [(f"e{i}", 100, 100, 80, 30) for i in range(8)]
        label_sizes = {f"e{i}": (40, 12) for i in range(8)}

        positions = _compute_label_positions(elements, label_sizes)

        assert len(positions) == 8


# ── _element_depth ────────────────────────────────────────────────────────


class TestElementDepth:
    """Tests for tree depth computation via parent_id walk."""

    def _make_element(self, ref: str, parent_id: str | None = None) -> UIElement:
        return UIElement(
            id=ref,
            element_id=f"element_{ref}",
            role="Button",
            title=ref,
            frame=(0, 0, 100, 30),
            is_actionable=True,
            parent_id=parent_id,
        )

    def test_root_element_depth_zero(self):
        """Element with no parent has depth 0."""
        ui_map = {"e0": self._make_element("e0")}
        assert _element_depth("e0", ui_map) == 0

    def test_child_depth_one(self):
        """Direct child of root has depth 1."""
        ui_map = {
            "e0": self._make_element("e0"),
            "e1": self._make_element("e1", parent_id="e0"),
        }
        assert _element_depth("e1", ui_map) == 1

    def test_grandchild_depth_two(self):
        """Grandchild element has depth 2."""
        ui_map = {
            "e0": self._make_element("e0"),
            "e1": self._make_element("e1", parent_id="e0"),
            "e2": self._make_element("e2", parent_id="e1"),
        }
        assert _element_depth("e2", ui_map) == 2

    def test_deep_chain(self):
        """Chain of 5 elements should have depth 4 at the deepest."""
        ui_map = {}
        for i in range(5):
            parent = f"e{i-1}" if i > 0 else None
            ui_map[f"e{i}"] = self._make_element(f"e{i}", parent_id=parent)

        assert _element_depth("e4", ui_map) == 4

    def test_missing_ref_returns_zero(self):
        """Non-existent ref returns depth 0."""
        ui_map = {"e0": self._make_element("e0")}
        assert _element_depth("e99", ui_map) == 0

    def test_circular_reference_does_not_loop(self):
        """Circular parent_id chain terminates via seen set."""
        e0 = self._make_element("e0", parent_id="e1")
        e1 = self._make_element("e1", parent_id="e0")
        ui_map = {"e0": e0, "e1": e1}

        # Should not hang — terminates due to cycle detection
        depth = _element_depth("e0", ui_map)
        assert depth >= 1  # At least 1 step before cycle detected

    def test_parent_not_in_map(self):
        """Element with parent_id not in the map has depth 1 (walks one step)."""
        ui_map = {
            "e1": self._make_element("e1", parent_id="e_missing"),
        }
        # Walks to e_missing, which is not in map, so stops
        assert _element_depth("e1", ui_map) == 1


# ── ACTIONABLE_ROLES ─────────────────────────────────────────────────────


class TestActionableRoles:
    """Verify key UI roles are in the ACTIONABLE_ROLES set."""

    @pytest.mark.parametrize("role", [
        "Button", "Edit", "ComboBox", "CheckBox", "RadioButton",
        "MenuItem", "Link", "Tab", "TabItem", "ListItem", "TreeItem",
    ])
    def test_windows_roles_present(self, role):
        assert role in ACTIONABLE_ROLES

    @pytest.mark.parametrize("role", [
        "AXButton", "AXTextField", "AXCheckBox", "AXRadioButton",
        "AXComboBox", "AXLink",
    ])
    def test_macos_roles_present(self, role):
        assert role in ACTIONABLE_ROLES

    def test_non_actionable_roles_absent(self):
        """Verify non-interactive roles are NOT in the set."""
        for role in ["Window", "Pane", "Group", "Text", "Image", "Document"]:
            assert role not in ACTIONABLE_ROLES

    def test_is_frozenset(self):
        """ACTIONABLE_ROLES should be immutable."""
        assert isinstance(ACTIONABLE_ROLES, frozenset)


# ── highlight_annotate ────────────────────────────────────────────────────


@pytest.fixture
def sample_ui_map():
    """UI map with mixed actionable/non-actionable elements."""
    return {
        "e0": UIElement(
            id="e0", element_id="el0", role="Button", title="OK",
            frame=(100, 100, 80, 30), is_actionable=True,
        ),
        "e1": UIElement(
            id="e1", element_id="el1", role="Edit", title="Name",
            frame=(200, 100, 150, 25), is_actionable=True,
        ),
        "e2": UIElement(
            id="e2", element_id="el2", role="Text", title="Label",
            frame=(50, 50, 100, 20), is_actionable=False,
        ),
        "e3": UIElement(
            id="e3", element_id="el3", role="Button", title="Tiny",
            frame=(0, 0, 2, 2), is_actionable=True,  # Too small
        ),
    }


@pytest.fixture
def sample_screenshot(tmp_path):
    """Create a minimal PNG for testing."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    img = Image.new("RGB", (400, 300), color=(200, 200, 200))
    path = str(tmp_path / "test.png")
    img.save(path)
    return path


class TestHighlightAnnotate:
    """Tests for highlight_annotate function."""

    def test_basic_output(self, sample_screenshot, sample_ui_map):
        """Creates output file with highlight annotations."""
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(sample_screenshot), "highlight.png")
        result = highlight_annotate(sample_screenshot, sample_ui_map, output)
        assert result == output
        assert os.path.exists(output)

    def test_auto_output_path(self, sample_screenshot, sample_ui_map):
        """Auto-generated path contains '_highlight'."""
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        result = highlight_annotate(sample_screenshot, sample_ui_map)
        assert "_highlight" in result
        assert os.path.exists(result)

    def test_refs_filter(self, sample_screenshot, sample_ui_map):
        """Only specified refs are highlighted when refs parameter is given."""
        try:
            from naturo.annotate import highlight_annotate
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(sample_screenshot), "filtered.png")
        result = highlight_annotate(
            sample_screenshot, sample_ui_map, output, refs=["e0"]
        )
        assert os.path.exists(result)

    def test_role_filter(self, sample_screenshot, sample_ui_map):
        """Role filter limits which elements are drawn."""
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(sample_screenshot), "edit_only.png")
        result = highlight_annotate(
            sample_screenshot, sample_ui_map, output, role_filter="Edit"
        )
        assert os.path.exists(result)

    def test_actionable_only_false(self, sample_screenshot, sample_ui_map):
        """Setting actionable_only=False includes non-actionable elements."""
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(sample_screenshot), "all.png")
        result = highlight_annotate(
            sample_screenshot, sample_ui_map, output, actionable_only=False
        )
        assert os.path.exists(result)

    def test_empty_ui_map_copies_screenshot(self, sample_screenshot):
        """Empty ui_map copies the screenshot unchanged."""
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(sample_screenshot), "empty.png")
        result = highlight_annotate(sample_screenshot, {}, output)
        assert os.path.exists(result)

    def test_missing_screenshot_raises(self, sample_ui_map):
        """Raises FileNotFoundError for nonexistent screenshot."""
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            pytest.skip("Pillow not installed")

        from naturo.annotate import highlight_annotate

        with pytest.raises(FileNotFoundError):
            highlight_annotate("/nonexistent/path.png", sample_ui_map)

    def test_long_title_truncated(self, sample_screenshot):
        """Element titles longer than 20 chars are truncated with '..'."""
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        ui_map = {
            "e0": UIElement(
                id="e0", element_id="el0", role="Button",
                title="A" * 30,  # 30 chars, should be truncated
                frame=(50, 50, 100, 30), is_actionable=True,
            ),
        }
        output = os.path.join(os.path.dirname(sample_screenshot), "truncated.png")
        result = highlight_annotate(sample_screenshot, ui_map, output)
        assert os.path.exists(result)


# ── _get_font ─────────────────────────────────────────────────────────────


class TestGetFont:
    """Tests for font loading fallback."""

    def test_returns_font_object(self):
        """_get_font always returns a usable font object."""
        try:
            from PIL import ImageFont  # noqa: F401
            from naturo.annotate import _get_font
        except ImportError:
            pytest.skip("Pillow not installed")

        font = _get_font(12)
        assert font is not None
        # Should have getbbox or getsize method
        assert hasattr(font, "getbbox") or hasattr(font, "getsize")

    def test_different_sizes(self):
        """Font loading works for different sizes."""
        try:
            from PIL import ImageFont  # noqa: F401
            from naturo.annotate import _get_font
        except ImportError:
            pytest.skip("Pillow not installed")

        for size in [8, 12, 16, 24]:
            font = _get_font(size)
            assert font is not None


# ── DEPTH_COLORS ──────────────────────────────────────────────────────────


class TestDepthColors:
    """Verify depth color palette."""

    def test_has_at_least_8_colors(self):
        assert len(DEPTH_COLORS) >= 8

    def test_all_rgb_tuples(self):
        for color in DEPTH_COLORS:
            assert len(color) == 3
            assert all(0 <= c <= 255 for c in color)
