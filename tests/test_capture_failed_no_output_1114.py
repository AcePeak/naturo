"""Tests for issue #1114 — a failed crop must not leave a full-screen file on disk.

``naturo capture --region`` / ``--element`` writes the *full* screenshot to the
user's ``-o``/``--path`` file before it validates the crop.  When crop validation
fails the command returns a hard error (``success:false``, exit 1) but used to
leave the full uncropped screenshot behind, so the on-disk artifact contradicted
the reported failure (a never-lie defect — SOUL.md).

These tests pin the corrected behaviour:
- every crop-validation failure path removes the pre-written output file;
- a successful crop still leaves a correctly-sized file (no regression);
- a plain full-screen capture (no crop requested) keeps its file.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.models.snapshot import UIElement


@pytest.fixture()
def png_200x100(tmp_path) -> str:
    """200×100 PNG used as the mock capture result (the 'full screenshot')."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")
    img = Image.new("RGB", (200, 100), color=(128, 128, 128))
    p = tmp_path / "screen_200x100.png"
    img.save(str(p))
    return str(p)


def _mock_capture_result(path: str, w: int = 200, h: int = 100):
    @dataclass
    class MockCaptureResult:
        path: str
        width: int
        height: int
        format: str = "png"
        scale_factor: float = 1.0
        dpi: int = 96

    return MockCaptureResult(path=path, width=w, height=h)


def _run_region(args, capture_path: str):
    """Invoke capture with a mocked backend whose screenshot is ``capture_path``."""
    mock_result = _mock_capture_result(capture_path, 200, 100)
    runner = CliRunner()
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend") as mock_be:
        be = MagicMock()
        be.capture_screen.return_value = mock_result
        be.capture_window.return_value = mock_result
        be.list_monitors.return_value = []
        mock_be.return_value = be
        return runner.invoke(main, args)


def _run_element(element_ref: str, capture_path: str, element: UIElement | None):
    """Invoke ``capture --element`` with a mocked backend + snapshot manager."""
    mock_result = _mock_capture_result(capture_path, 200, 100)
    runner = CliRunner()
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend") as mock_be, \
         patch("naturo.snapshot.SnapshotManager.resolve_ref") as mock_resolve, \
         patch("naturo.snapshot.SnapshotManager.resolve_ref_element") as mock_resolve_el:
        be = MagicMock()
        be.capture_screen.return_value = mock_result
        be.list_monitors.return_value = []
        mock_be.return_value = be
        if element is not None:
            ex, ey, ew, eh = element.frame
            mock_resolve.return_value = (ex + ew // 2, ey + eh // 2, "snap-001")
            mock_resolve_el.return_value = (element, "snap-001")
        else:
            mock_resolve.return_value = None
            mock_resolve_el.return_value = None
        return runner.invoke(
            main, ["capture", "--element", element_ref, "--no-snapshot", "--json"]
        )


class TestRegionFailureRemovesFile:
    def test_offscreen_region_removes_output_file(self, png_200x100):
        result = _run_region(
            ["capture", "--region", "5000,5000,50,50", "--no-snapshot", "--json"],
            png_200x100,
        )
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        # The pre-written full screenshot must be gone.
        assert not Path(png_200x100).exists()

    def test_non_positive_size_removes_output_file(self, png_200x100):
        result = _run_region(
            ["capture", "--region", "100,100,0,200", "--no-snapshot", "--json"],
            png_200x100,
        )
        data = json.loads(result.output)
        assert data["success"] is False
        assert "non-positive" in data["error"]["message"]
        assert not Path(png_200x100).exists()

    def test_malformed_region_removes_output_file(self, png_200x100):
        result = _run_region(
            ["capture", "--region", "not,a,region", "--no-snapshot", "--json"],
            png_200x100,
        )
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        assert not Path(png_200x100).exists()

    def test_plain_text_path_also_removes_file(self, png_200x100):
        """The non-JSON (human) path must clean up too."""
        result = _run_region(
            ["capture", "--region", "5000,5000,50,50", "--no-snapshot"],
            png_200x100,
        )
        assert result.exit_code == 1
        assert not Path(png_200x100).exists()


class TestElementFailureRemovesFile:
    def test_ref_not_found_removes_output_file(self, png_200x100):
        result = _run_element("e99", png_200x100, element=None)
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "STALE_SNAPSHOT_CACHE"
        assert not Path(png_200x100).exists()

    def test_zero_size_element_removes_output_file(self, png_200x100):
        el = UIElement(
            id="el1", element_id="el1", role="Button", title="OK", label="OK",
            value=None, frame=(20, 10, 0, 0), is_actionable=True,
            parent_id=None, children=[],
        )
        result = _run_element("e1", png_200x100, element=el)
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "ZERO_SIZE_ELEMENT"
        assert not Path(png_200x100).exists()


class TestSuccessKeepsFile:
    def test_valid_region_keeps_cropped_file(self, png_200x100):
        """Guard: a successful crop still leaves a correctly-sized file."""
        result = _run_region(
            ["capture", "--region", "10,10,80,40", "--no-snapshot", "--json"],
            png_200x100,
        )
        if "MISSING_DEPENDENCY" in result.output:
            pytest.skip("Pillow not installed")
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["width"] == 80
        assert data["height"] == 40
        assert Path(png_200x100).exists()
        from PIL import Image
        assert Image.open(png_200x100).size == (80, 40)

    def test_full_screen_capture_keeps_file(self, png_200x100):
        """Guard: a plain capture with no crop requested keeps its file."""
        result = _run_region(
            ["capture", "--no-snapshot", "--json"],
            png_200x100,
        )
        data = json.loads(result.output)
        assert data["success"] is True
        assert Path(png_200x100).exists()
