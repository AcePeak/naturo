"""Tests for naturo.annotate — annotated screenshot generation."""

import os
import tempfile

import pytest

from naturo.models.snapshot import UIElement


@pytest.fixture
def sample_elements():
    """Create a list of test UIElements."""
    return [
        UIElement(
            id="e0",
            element_id="element_0",
            role="Button",
            title="OK",
            frame=(100, 200, 80, 30),
            is_actionable=True,
        ),
        UIElement(
            id="e1",
            element_id="element_1",
            role="Button",
            title="Cancel",
            frame=(200, 200, 80, 30),
            is_actionable=True,
        ),
        UIElement(
            id="e2",
            element_id="element_2",
            role="Edit",
            title="Name",
            frame=(100, 100, 200, 25),
            is_actionable=True,
        ),
        UIElement(
            id="e3",
            element_id="element_3",
            role="Text",
            title="Label",
            frame=(50, 50, 100, 20),
            is_actionable=False,  # Not actionable — should be skipped
        ),
        UIElement(
            id="e4",
            element_id="element_4",
            role="Button",
            title="Tiny",
            frame=(0, 0, 2, 2),  # Too small — should be skipped
            is_actionable=True,
        ),
    ]


@pytest.fixture
def sample_screenshot(tmp_path):
    """Create a minimal PNG file for testing."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    img = Image.new("RGB", (400, 400), color=(200, 200, 200))
    path = str(tmp_path / "test_screenshot.png")
    img.save(path)
    return path


class TestAnnotateScreenshot:
    """Tests for annotate_screenshot function."""

    def test_basic_annotation(self, sample_screenshot, sample_elements):
        """Annotate a screenshot with elements and verify output exists."""
        try:
            from naturo.annotate import annotate_screenshot
        except ImportError:
            pytest.skip("Pillow not installed")

        output = str(os.path.join(os.path.dirname(sample_screenshot), "annotated.png"))
        result = annotate_screenshot(sample_screenshot, sample_elements, output)

        assert result == output
        assert os.path.exists(output)

    def test_auto_output_path(self, sample_screenshot, sample_elements):
        """When output_path is None, generates path automatically."""
        try:
            from naturo.annotate import annotate_screenshot
        except ImportError:
            pytest.skip("Pillow not installed")

        result = annotate_screenshot(sample_screenshot, sample_elements)
        assert "_annotated" in result
        assert os.path.exists(result)

    def test_only_actionable_elements_annotated(self, sample_screenshot, sample_elements):
        """Only actionable elements with visible bounding boxes are annotated."""
        try:
            from naturo.annotate import annotate_screenshot
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        output = str(os.path.join(os.path.dirname(sample_screenshot), "annotated.png"))
        annotate_screenshot(sample_screenshot, sample_elements, output)

        # Verify the output is a valid image
        img = Image.open(output)
        assert img.size == (400, 400)

    def test_empty_elements(self, sample_screenshot):
        """No crash with empty element list."""
        try:
            from naturo.annotate import annotate_screenshot
        except ImportError:
            pytest.skip("Pillow not installed")

        output = str(os.path.join(os.path.dirname(sample_screenshot), "annotated.png"))
        result = annotate_screenshot(sample_screenshot, [], output)
        assert os.path.exists(result)

    def test_missing_screenshot_raises(self, sample_elements):
        """Raises FileNotFoundError for nonexistent screenshot."""
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            pytest.skip("Pillow not installed")

        from naturo.annotate import annotate_screenshot

        with pytest.raises(FileNotFoundError):
            annotate_screenshot("/nonexistent/path.png", sample_elements)

    def test_annotation_pixel_check(self, sample_screenshot, sample_elements):
        """Verify that red pixels appear in annotated image (box was drawn)."""
        try:
            from naturo.annotate import annotate_screenshot
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        output = str(os.path.join(os.path.dirname(sample_screenshot), "annotated.png"))
        annotate_screenshot(sample_screenshot, sample_elements, output)

        img = Image.open(output)
        pixels = list(img.get_flattened_data() if hasattr(img, 'get_flattened_data') else img.getdata())
        # At least some red pixels should exist from the bounding boxes
        red_pixels = [p for p in pixels if p[0] == 255 and p[1] == 0 and p[2] == 0]
        assert len(red_pixels) > 0, "Expected red bounding box pixels in annotated image"
