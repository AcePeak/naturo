"""Tests for naturo.cli.core._capture — capture command.

Tests cover full screen capture, window capture, --element crop,
--region crop, --format, --screen validation, snapshot storage,
JSON output, and error paths. All mock-based, CI-safe.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.core._capture import capture


@dataclass
class FakeCaptureResult:
    path: str = "/tmp/test.png"
    width: int = 1920
    height: int = 1080
    format: str = "png"
    scale_factor: float = 1.0
    dpi: int = 96


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.capture_screen.return_value = FakeCaptureResult()
    backend.capture_window.return_value = FakeCaptureResult()
    backend._resolve_hwnd.return_value = 12345
    backend.list_monitors.return_value = [
        MagicMock(index=0), MagicMock(index=1),
    ]
    return backend


def _patch_backend(mock_backend):
    return patch("naturo.cli.core._common._get_backend", return_value=mock_backend)


def _patch_platform(supports=True):
    return patch("naturo.cli.core._common._platform_supports_gui", return_value=supports)


# Note: Most tests use --no-snapshot to avoid snapshot manager trying
# to read the fake file path from FakeCaptureResult.


# ── Full screen capture ─────────────────────────────────────────────


class TestFullScreenCapture:

    def test_basic_capture(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "-p", "/tmp/out.png", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.capture_screen.assert_called_once_with(screen_index=0, output_path="/tmp/out.png")

    def test_json_output(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "-p", "/tmp/out.png", "--json", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["width"] == 1920
        assert data["height"] == 1080
        assert data["format"] == "png"

    def test_default_path_generated(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, ["--no-snapshot"], catch_exceptions=False)
        assert result.exit_code == 0
        call_args = mock_backend.capture_screen.call_args
        assert call_args.kwargs["output_path"].startswith("naturo-screen-")
        assert call_args.kwargs["output_path"].endswith(".png")

    def test_plain_output_shows_path(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "-p", "/tmp/out.png", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Saved:" in result.output
        assert "1920x1080" in result.output


# ── Screen index validation ──────────────────────────────────────────


class TestScreenValidation:

    def test_negative_screen_index_error(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "-s", "-1", "--json", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output

    def test_screen_index_out_of_range(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "-s", "5", "--json", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output


# ── Window capture ───────────────────────────────────────────────────


class TestWindowCapture:

    def test_capture_by_hwnd(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "--hwnd", "12345", "-p", "/tmp/out.png", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.capture_window.assert_called_once()

    def test_capture_by_app(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "--app", "notepad", "-p", "/tmp/out.png", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend._resolve_hwnd.assert_called()
        mock_backend.capture_window.assert_called_once()


# ── Region crop ──────────────────────────────────────────────────────


class TestRegionCrop:

    def test_invalid_region_format(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "-p", "/tmp/out.png", "--region", "bad", "--json", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output

    def test_region_wrong_count(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "-p", "/tmp/out.png", "--region", "1,2,3", "--json", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output


# ── Element crop ─────────────────────────────────────────────────────


class TestElementCrop:

    def test_element_ref_not_found(self, runner, mock_backend):
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref.return_value = None

        with _patch_platform(), _patch_backend(mock_backend), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = runner.invoke(capture, [
                "-p", "/tmp/out.png", "--element", "e999", "--json", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code != 0
        assert "REF_NOT_FOUND" in result.output

    def test_element_zero_size_error(self, runner, mock_backend):
        mock_elem = MagicMock()
        mock_elem.frame = (0, 0, 0, 0)
        mock_elem.role = "Button"
        mock_elem.name = "Hidden"
        mock_mgr = MagicMock()
        mock_mgr.resolve_ref.return_value = (0, 0, "snap1")
        mock_mgr.resolve_ref_element.return_value = (mock_elem, "snap1")

        with _patch_platform(), _patch_backend(mock_backend), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = runner.invoke(capture, [
                "-p", "/tmp/out.png", "--element", "e5", "--json", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code != 0
        assert "ZERO_SIZE_ELEMENT" in result.output


# ── Format option ────────────────────────────────────────────────────


class TestFormatOption:

    def test_jpg_format(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "--format", "jpg", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        call_args = mock_backend.capture_screen.call_args
        assert call_args.kwargs["output_path"].endswith(".jpg")


# ── Platform check ───────────────────────────────────────────────────


class TestPlatformCheck:

    def test_unsupported_platform(self, runner):
        with _patch_platform(supports=False):
            result = runner.invoke(capture, ["--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "PLATFORM_ERROR" in result.output

    def test_unsupported_platform_plain(self, runner):
        with _patch_platform(supports=False):
            result = runner.invoke(capture, [], catch_exceptions=False)
        assert result.exit_code != 0


# ── Backend error ────────────────────────────────────────────────────


class TestBackendError:

    def test_capture_exception_json(self, runner, mock_backend):
        mock_backend.capture_screen.side_effect = Exception("capture failed")
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(capture, [
                "-p", "/tmp/out.png", "--json", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code != 0
        assert "CAPTURE_ERROR" in result.output


# ── Snapshot storage ─────────────────────────────────────────────────


class TestSnapshotStorage:

    def test_json_includes_snapshot_id(self, runner, mock_backend):
        mock_mgr = MagicMock()
        mock_mgr.create_snapshot.return_value = "snap_abc"

        with _patch_platform(), _patch_backend(mock_backend), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr):
            result = runner.invoke(capture, [
                "-p", "/tmp/out.png", "--json",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["snapshot_id"] == "snap_abc"
        mock_mgr.create_snapshot.assert_called_once()
        mock_mgr.store_screenshot.assert_called_once()
