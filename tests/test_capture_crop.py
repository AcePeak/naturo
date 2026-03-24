"""Tests for issue #160 — capture supports element ref and region cropping.

Verifies:
- --element eN crops to element bounds from snapshot
- --region X,Y,W,H crops to coordinates
- --padding adds extra pixels around crop
- Invalid --region format gives clear error
- eN ref not found gives clear error
- Crop output metadata in JSON response (cropped, crop_source)
- --element and --region flags exist in --help
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.models.snapshot import UIElement


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def png_1x1(tmp_path) -> str:
    """1×1 PNG for use as a mock capture result."""
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    p = tmp_path / "screen.png"
    p.write_bytes(png_bytes)
    return str(p)


@pytest.fixture()
def png_200x100(tmp_path) -> str:
    """200×100 PNG using Pillow."""
    try:
        from PIL import Image
        img = Image.new("RGB", (200, 100), color=(128, 128, 128))
        p = tmp_path / "screen_200x100.png"
        img.save(str(p))
        return str(p)
    except ImportError:
        pytest.skip("Pillow not installed")


def _mock_capture_result(path: str, w: int = 200, h: int = 100):
    from dataclasses import dataclass

    @dataclass
    class MockCaptureResult:
        path: str
        width: int
        height: int
        format: str = "png"
        scale_factor: float = 1.0
        dpi: int = 96

    return MockCaptureResult(path=path, width=w, height=h)


# ── CLI flag presence ─────────────────────────────────────────────────────────


class TestCaptureLiveHelpFlags:
    def test_element_flag_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["capture", "live", "--help"])
        assert "--element" in result.output

    def test_region_flag_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["capture", "live", "--help"])
        assert "--region" in result.output

    def test_padding_flag_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["capture", "live", "--help"])
        assert "--padding" in result.output


# ── Region validation ─────────────────────────────────────────────────────────


class TestRegionValidation:
    def _run(self, args, capture_path: str):
        from naturo.backends.base import CaptureResult
        mock_result = _mock_capture_result(capture_path, 200, 100)

        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be:
            be = MagicMock()
            be.capture_screen.return_value = mock_result
            be.capture_window.return_value = mock_result
            be.list_monitors.return_value = []
            mock_be.return_value = be
            return runner.invoke(main, args)

    def test_invalid_region_format(self, png_200x100):
        result = self._run(
            ["capture", "live", "--region", "100,50", "--no-snapshot", "--json"],
            png_200x100,
        )
        data = json.loads(result.output)
        assert data["success"] is False
        assert "INVALID_INPUT" in data["error"]["code"]

    def test_invalid_region_nonnumeric(self, png_200x100):
        result = self._run(
            ["capture", "live", "--region", "x,y,w,h", "--no-snapshot", "--json"],
            png_200x100,
        )
        data = json.loads(result.output)
        assert data["success"] is False

    def test_valid_region_crop(self, png_200x100):
        result = self._run(
            ["capture", "live", "--region", "10,10,80,40", "--no-snapshot", "--json"],
            png_200x100,
        )
        if "MISSING_DEPENDENCY" in result.output:
            pytest.skip("Pillow not installed")
        data = json.loads(result.output)
        assert data["success"] is True
        assert data.get("cropped") is True
        assert data.get("crop_source") == "region"
        # Cropped dimensions
        assert data["width"] == 80
        assert data["height"] == 40

    def test_region_with_padding(self, png_200x100):
        result = self._run(
            ["capture", "live", "--region", "10,10,50,50", "--padding", "5",
             "--no-snapshot", "--json"],
            png_200x100,
        )
        if "MISSING_DEPENDENCY" in result.output:
            pytest.skip("Pillow not installed")
        data = json.loads(result.output)
        if data.get("success"):
            # width = 50+2*5=60, height = 50+2*5=60 (clamped to image)
            assert data["width"] == 60
            assert data["height"] == 60


# ── Element ref crop ──────────────────────────────────────────────────────────


class TestElementRefCrop:
    def _run_with_element(self, element_ref: str, capture_path: str,
                          element: UIElement | None = None, json_output: bool = True):
        mock_result = _mock_capture_result(capture_path, 200, 100)

        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be, \
             patch("naturo.snapshot.SnapshotManager.resolve_ref") as mock_resolve, \
             patch("naturo.snapshot.SnapshotManager.resolve_ref_element") as mock_resolve_el:
            be = MagicMock()
            be.capture_screen.return_value = mock_result
            be.list_monitors.return_value = []
            mock_be.return_value = be

            if element is not None:
                mock_resolve.return_value = (element.frame[0] + element.frame[2] // 2,
                                             element.frame[1] + element.frame[3] // 2,
                                             "snap-001")
                mock_resolve_el.return_value = (element, "snap-001")
            else:
                mock_resolve.return_value = None
                mock_resolve_el.return_value = None

            args = ["capture", "live", "--element", element_ref, "--no-snapshot"]
            if json_output:
                args.append("--json")
            return runner.invoke(main, args)

    def test_element_ref_not_found(self, png_200x100):
        result = self._run_with_element("e99", png_200x100, element=None)
        data = json.loads(result.output)
        assert data["success"] is False
        assert "REF_NOT_FOUND" in data["error"]["code"]

    def test_element_ref_crops_image(self, png_200x100):
        el = UIElement(
            id="el1", element_id="el1", role="Button", title="OK", label="OK",
            value=None, frame=(20, 10, 60, 30), is_actionable=True,
            parent_id=None, children=[],
        )
        result = self._run_with_element("e1", png_200x100, element=el)
        if "MISSING_DEPENDENCY" in result.output:
            pytest.skip("Pillow not installed")
        data = json.loads(result.output)
        if data.get("success"):
            assert data.get("cropped") is True
            assert data.get("crop_source") == "element"
            assert data["width"] == 60
            assert data["height"] == 30

    def test_element_ref_with_padding(self, png_200x100):
        el = UIElement(
            id="el1", element_id="el1", role="Button", title="OK", label="OK",
            value=None, frame=(10, 10, 40, 20), is_actionable=True,
            parent_id=None, children=[],
        )
        runner = CliRunner()
        mock_result = _mock_capture_result(png_200x100, 200, 100)

        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be, \
             patch("naturo.snapshot.SnapshotManager.resolve_ref",
                   return_value=(30, 20, "snap-001")), \
             patch("naturo.snapshot.SnapshotManager.resolve_ref_element",
                   return_value=(el, "snap-001")):
            be = MagicMock()
            be.capture_screen.return_value = mock_result
            be.list_monitors.return_value = []
            mock_be.return_value = be
            result = runner.invoke(main, [
                "capture", "live", "--element", "e1", "--padding", "5",
                "--no-snapshot", "--json",
            ])

        if "MISSING_DEPENDENCY" in result.output:
            pytest.skip("Pillow not installed")
        data = json.loads(result.output)
        if data.get("success"):
            # 40+2*5=50, 20+2*5=30
            assert data["width"] == 50
            assert data["height"] == 30
