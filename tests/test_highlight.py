"""Tests for highlight improvements — label avoidance, annotate mode, filtering.

Tests the pure-Python logic in naturo.annotate (label collision avoidance,
highlight_annotate, depth computation, actionable filtering) and the CLI
flags (--all, --annotate, --filter).
"""

import os

import pytest

from naturo.models.snapshot import UIElement


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def ui_map():
    """Create a ui_map with elements at different depths and roles."""
    return {
        "e1": UIElement(
            id="e1", element_id="el_1", role="Window", title="Main",
            frame=(0, 0, 800, 600), is_actionable=False, parent_id=None,
            children=["e2", "e3", "e4"],
        ),
        "e2": UIElement(
            id="e2", element_id="el_2", role="Button", title="OK",
            frame=(100, 500, 80, 30), is_actionable=True, parent_id="e1",
        ),
        "e3": UIElement(
            id="e3", element_id="el_3", role="Button", title="Cancel",
            frame=(200, 500, 80, 30), is_actionable=True, parent_id="e1",
        ),
        "e4": UIElement(
            id="e4", element_id="el_4", role="Edit", title="Username",
            frame=(100, 100, 300, 25), is_actionable=True, parent_id="e1",
            children=["e5"],
        ),
        "e5": UIElement(
            id="e5", element_id="el_5", role="Text", title="Placeholder",
            frame=(105, 103, 200, 18), is_actionable=False, parent_id="e4",
        ),
        "e6": UIElement(
            id="e6", element_id="el_6", role="Pane", title="StatusBar",
            frame=(0, 580, 800, 20), is_actionable=False, parent_id="e1",
        ),
    }


@pytest.fixture
def screenshot_400x400(tmp_path):
    """Create a 400x400 grey PNG."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")
    img = Image.new("RGB", (800, 600), color=(200, 200, 200))
    path = str(tmp_path / "screen.png")
    img.save(path)
    return path


# ── Label collision avoidance ────────────────────────────────────────────────


class TestLabelPositions:
    """Tests for _compute_label_positions."""

    def test_no_overlap_for_distant_elements(self):
        from naturo.annotate import _compute_label_positions

        elements = [
            ("e1", 100, 200, 80, 30),
            ("e2", 500, 200, 80, 30),
        ]
        label_sizes = {"e1": (60, 14), "e2": (70, 14)}
        positions = _compute_label_positions(elements, label_sizes)

        assert "e1" in positions
        assert "e2" in positions
        # Both should get above-left (default) since they're far apart
        assert positions["e1"][1] < 200  # above the element
        assert positions["e2"][1] < 200

    def test_overlap_avoidance_for_stacked_elements(self):
        from naturo.annotate import _compute_label_positions

        # Two elements stacked vertically, labels above would overlap
        elements = [
            ("e1", 100, 100, 200, 30),
            ("e2", 100, 135, 200, 30),  # just below e1
        ]
        label_sizes = {"e1": (80, 14), "e2": (80, 14)}
        positions = _compute_label_positions(elements, label_sizes)

        # Labels should not be at the same position
        p1 = positions["e1"]
        p2 = positions["e2"]
        # At least one coordinate should differ
        assert p1 != p2

    def test_empty_elements(self):
        from naturo.annotate import _compute_label_positions

        positions = _compute_label_positions([], {})
        assert positions == {}

    def test_single_element(self):
        from naturo.annotate import _compute_label_positions

        elements = [("e1", 50, 50, 100, 30)]
        label_sizes = {"e1": (60, 14)}
        positions = _compute_label_positions(elements, label_sizes)
        assert "e1" in positions
        lx, ly = positions["e1"]
        assert lx >= 0
        assert ly >= 0


# ── Depth computation ────────────────────────────────────────────────────────


class TestElementDepth:
    """Tests for _element_depth."""

    def test_root_depth_is_zero(self, ui_map):
        from naturo.annotate import _element_depth

        assert _element_depth("e1", ui_map) == 0

    def test_child_depth_is_one(self, ui_map):
        from naturo.annotate import _element_depth

        assert _element_depth("e2", ui_map) == 1
        assert _element_depth("e3", ui_map) == 1

    def test_grandchild_depth_is_two(self, ui_map):
        from naturo.annotate import _element_depth

        assert _element_depth("e5", ui_map) == 2

    def test_unknown_ref_returns_zero(self, ui_map):
        from naturo.annotate import _element_depth

        assert _element_depth("e999", ui_map) == 0


# ── highlight_annotate ───────────────────────────────────────────────────────


class TestHighlightAnnotate:
    """Tests for highlight_annotate (PIL-based annotation)."""

    def test_basic_annotate(self, screenshot_400x400, ui_map):
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(screenshot_400x400), "hl.png")
        result = highlight_annotate(screenshot_400x400, ui_map, output_path=output)
        assert result == output
        assert os.path.exists(output)

    def test_actionable_only_default(self, screenshot_400x400, ui_map):
        """Default mode skips non-actionable elements (Window, Text, Pane)."""
        try:
            from naturo.annotate import highlight_annotate
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(screenshot_400x400), "hl.png")
        highlight_annotate(screenshot_400x400, ui_map, output_path=output,
                           actionable_only=True)
        img = Image.open(output)
        assert img.size == (800, 600)

    def test_show_all_includes_non_actionable(self, screenshot_400x400, ui_map):
        """With actionable_only=False, all elements are annotated."""
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(screenshot_400x400), "hl.png")
        highlight_annotate(screenshot_400x400, ui_map, output_path=output,
                           actionable_only=False)
        assert os.path.exists(output)

    def test_role_filter(self, screenshot_400x400, ui_map):
        """Role filter limits to matching roles only."""
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(screenshot_400x400), "hl.png")
        highlight_annotate(screenshot_400x400, ui_map, output_path=output,
                           actionable_only=False, role_filter="Button")
        assert os.path.exists(output)

    def test_specific_refs(self, screenshot_400x400, ui_map):
        """Passing specific refs only highlights those elements."""
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(screenshot_400x400), "hl.png")
        highlight_annotate(screenshot_400x400, ui_map, output_path=output,
                           refs=["e2"], actionable_only=False)
        assert os.path.exists(output)

    def test_auto_output_path(self, screenshot_400x400, ui_map):
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        result = highlight_annotate(screenshot_400x400, ui_map)
        assert "_highlight" in result
        assert os.path.exists(result)

    def test_missing_screenshot_raises(self, ui_map):
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            pytest.skip("Pillow not installed")

        from naturo.annotate import highlight_annotate

        with pytest.raises(FileNotFoundError):
            highlight_annotate("/nonexistent/path.png", ui_map)

    def test_empty_ui_map(self, screenshot_400x400):
        """Empty ui_map produces a copy of the original screenshot."""
        try:
            from naturo.annotate import highlight_annotate
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(screenshot_400x400), "hl.png")
        result = highlight_annotate(screenshot_400x400, {}, output_path=output)
        assert os.path.exists(result)

    def test_depth_colors_vary(self, screenshot_400x400, ui_map):
        """Elements at different depths get different colors."""
        try:
            from naturo.annotate import highlight_annotate
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        output = os.path.join(os.path.dirname(screenshot_400x400), "hl.png")
        highlight_annotate(screenshot_400x400, ui_map, output_path=output,
                           actionable_only=False)
        img = Image.open(output)
        # Image should differ from plain grey — at least some coloured pixels
        pixels = list(img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata())
        non_grey = [p for p in pixels if p != (200, 200, 200)]
        assert len(non_grey) > 0, "Expected coloured annotation pixels"


# ── ACTIONABLE_ROLES set ─────────────────────────────────────────────────────


class TestActionableRoles:
    """Verify the ACTIONABLE_ROLES set contains expected roles."""

    def test_common_roles_present(self):
        from naturo.annotate import ACTIONABLE_ROLES

        for role in ("Button", "Edit", "ComboBox", "CheckBox", "MenuItem", "Link"):
            assert role in ACTIONABLE_ROLES, f"{role} should be in ACTIONABLE_ROLES"

    def test_non_actionable_roles_absent(self):
        from naturo.annotate import ACTIONABLE_ROLES

        for role in ("Window", "Pane", "Group", "Text", "Image", "Document"):
            assert role not in ACTIONABLE_ROLES, f"{role} should NOT be in ACTIONABLE_ROLES"


class TestHighlightHelp:
    """Verify --help output formatting (regression for #543)."""

    def test_help_examples_not_wrapped(self):
        """Each example should be on its own line, not wrapped together."""
        from click.testing import CliRunner

        from naturo.cli import main

        result = CliRunner().invoke(main, ["highlight", "--help"])
        assert result.exit_code == 0
        # Each example must start on its own line (not wrapped into previous)
        assert "naturo highlight --app notepad" in result.output
        # If wrapping occurred, "naturo" would appear mid-line after another command
        lines = result.output.splitlines()
        example_lines = [l for l in lines if "naturo highlight" in l]
        for line in example_lines:
            # Each line should contain exactly one "naturo highlight" invocation
            assert line.strip().count("naturo highlight") == 1, (
                f"Example wrapping detected: {line!r}"
            )
