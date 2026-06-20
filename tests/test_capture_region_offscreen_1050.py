"""Tests for issue #1050 — capture --region off-screen error clarity.

When ``naturo capture --region X,Y,W,H`` targets a region that lies entirely
off-screen, the zero-size error used to echo the internal *clamped* PIL crop
box ``(left, top, right, bottom)``, which reads like an ``X,Y,W,H`` the user
never typed (the W/H columns silently became the image's right/bottom edges).

These tests pin the corrected behaviour:
- the message echoes the user's requested ``X,Y,W,H``;
- it names the captured image bounds separately;
- ``error.context`` carries ``requested_region`` and ``image_size``;
- a non-positive width/height is reported as such rather than as "off-screen".
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main


@pytest.fixture()
def png_200x100(tmp_path) -> str:
    """200×100 PNG used as the mock capture result."""
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


def _run(args, capture_path: str):
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


class TestOffScreenRegionMessage:
    def test_message_echoes_requested_region_not_clamped_box(self, png_200x100):
        result = _run(
            ["capture", "--region", "5000,5000,50,50", "--no-snapshot", "--json"],
            png_200x100,
        )
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        message = data["error"]["message"]
        # Echoes the user's actual X,Y,W,H ...
        assert "5000,5000,50,50" in message
        # ... and never the misleading clamped box that reads as W=200,H=100.
        assert "5000,5000,200,100" not in message
        # Names the image bounds explicitly so "off-screen" is obvious.
        assert "200x100" in message

    def test_context_carries_requested_region_and_image_size(self, png_200x100):
        result = _run(
            ["capture", "--region", "9999,9999,100,100", "--no-snapshot", "--json"],
            png_200x100,
        )
        data = json.loads(result.output)
        ctx = data["error"]["context"]
        assert ctx["requested_region"] == [9999, 9999, 100, 100]
        assert ctx["image_size"] == [200, 100]

    def test_non_positive_size_reported_distinctly(self, png_200x100):
        result = _run(
            ["capture", "--region", "10,10,0,0", "--no-snapshot", "--json"],
            png_200x100,
        )
        data = json.loads(result.output)
        assert data["success"] is False
        message = data["error"]["message"]
        assert "non-positive" in message
        assert "10,10,0,0" in message
        assert data["error"]["context"]["requested_region"] == [10, 10, 0, 0]

    def test_plain_text_error_echoes_user_input(self, png_200x100):
        result = _run(
            ["capture", "--region", "5000,5000,50,50", "--no-snapshot"],
            png_200x100,
        )
        # Non-JSON path writes to stderr; CliRunner merges it into output.
        assert "5000,5000,50,50" in result.output
        assert "200x100" in result.output

    def test_valid_onscreen_region_still_succeeds(self, png_200x100):
        """Guard: the fix must not regress the valid crop path."""
        result = _run(
            ["capture", "--region", "10,10,80,40", "--no-snapshot", "--json"],
            png_200x100,
        )
        if "MISSING_DEPENDENCY" in result.output:
            pytest.skip("Pillow not installed")
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["width"] == 80
        assert data["height"] == 40
