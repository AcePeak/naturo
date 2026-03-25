"""Tests for issue #280 — capture UX improvements.

Verifies:
1. `naturo capture` works without requiring `live` subcommand
2. `-o` is a valid alias for `--path`
3. Zero-bounds elements give clear error message (not "not found")
4. `see` output marks zero-bounds elements with [0x0]
5. JSON output includes zero_bounds: true for such elements
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main


# ── Fixtures ─────────────────────────────────────────────────────────────────


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


# ── Test: capture without subcommand (#280.1) ────────────────────────────────


class TestCaptureWithoutSubcommand:
    """Issue #280.1: `naturo capture --app foo` should work without `live`."""

    def test_capture_help_shows_options(self):
        runner = CliRunner()
        result = runner.invoke(main, ["capture", "--help"])
        assert result.exit_code == 0
        assert "--app" in result.output
        assert "--element" in result.output
        assert "--path" in result.output

    def test_capture_without_subcommand_executes(self, tmp_path, png_200x100):
        mock_result = _mock_capture_result(png_200x100, 200, 100)
        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be:
            backend = MagicMock()
            backend.capture_screen.return_value = mock_result
            mock_be.return_value = backend
            result = runner.invoke(main, ["capture", "--no-snapshot"])
            assert result.exit_code == 0, result.output
            assert "Saved:" in result.output

    def test_capture_live_still_works(self, tmp_path, png_200x100):
        mock_result = _mock_capture_result(png_200x100, 200, 100)
        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be:
            backend = MagicMock()
            backend.capture_screen.return_value = mock_result
            mock_be.return_value = backend
            result = runner.invoke(main, ["capture", "live", "--no-snapshot"])
            assert result.exit_code == 0, result.output
            assert "Saved:" in result.output


# ── Test: -o alias for --path (#280.2) ───────────────────────────────────────


class TestOutputPathAlias:
    def test_o_flag_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["capture", "--help"])
        assert "-o" in result.output

    def test_o_flag_works(self, tmp_path, png_200x100):
        mock_result = _mock_capture_result(png_200x100, 200, 100)
        out_path = tmp_path / "output.png"
        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be:
            backend = MagicMock()
            backend.capture_screen.return_value = mock_result
            mock_be.return_value = backend
            result = runner.invoke(main, ["capture", "-o", str(out_path), "--no-snapshot"])
            assert result.exit_code == 0, result.output


# ── Test: Zero-bounds error message (#280.3) ──────────────────────────────────


class TestZeroBoundsErrorMessage:
    def test_zero_bounds_gives_clear_error(self, tmp_path, png_200x100):
        from naturo.models.snapshot import UIElement

        mock_result = _mock_capture_result(png_200x100, 200, 100)
        mock_mgr = MagicMock()
        mock_mgr.check_ref_status.return_value = {
            "status": "zero_bounds",
            "element": MagicMock(),
            "snapshot_id": "snap-123",
            "message": "Element e1 (Text 'Hidden Text') has zero-size bounds (0x0) and cannot be cropped.",
        }

        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be, \
             patch("naturo.snapshot.get_snapshot_manager", return_value=mock_mgr), \
             patch("naturo.cli.core.get_snapshot_manager", create=True, return_value=mock_mgr):
            # Patch the lazy import inside _do_capture
            import naturo.cli.core as core_mod
            orig = None
            # The function does `from naturo.snapshot import get_snapshot_manager` inside,
            # so we need to patch at the source
            with patch.dict("sys.modules", {}):
                pass
            backend = MagicMock()
            backend.capture_screen.return_value = mock_result
            mock_be.return_value = backend

            # Monkey-patch the lazy import
            import naturo.snapshot
            original_gsm = naturo.snapshot.get_snapshot_manager
            naturo.snapshot.get_snapshot_manager = lambda **kw: mock_mgr
            try:
                result = runner.invoke(main, ["capture", "--element", "e1", "--no-snapshot"])
            finally:
                naturo.snapshot.get_snapshot_manager = original_gsm

            assert result.exit_code == 1
            assert "zero" in result.output.lower() or "0x0" in result.output
            assert "not found" not in result.output.lower()

    def test_zero_bounds_json_error_code(self, tmp_path, png_200x100):
        mock_result = _mock_capture_result(png_200x100, 200, 100)
        mock_mgr = MagicMock()
        mock_mgr.check_ref_status.return_value = {
            "status": "zero_bounds",
            "element": MagicMock(),
            "snapshot_id": "snap-123",
            "message": "Element e1 has zero-size bounds.",
        }

        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be:
            backend = MagicMock()
            backend.capture_screen.return_value = mock_result
            mock_be.return_value = backend

            import naturo.snapshot
            original_gsm = naturo.snapshot.get_snapshot_manager
            naturo.snapshot.get_snapshot_manager = lambda **kw: mock_mgr
            try:
                result = runner.invoke(main, ["capture", "--element", "e1", "--json", "--no-snapshot"])
            finally:
                naturo.snapshot.get_snapshot_manager = original_gsm

            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data.get("error_code") == "ZERO_BOUNDS"


# ── Test: see marks zero-bounds elements (#280.4) ─────────────────────────────


class TestSeeZeroBoundsMarker:
    def test_see_text_output_marks_zero_bounds(self):
        from naturo.backends.base import ElementInfo

        tree = ElementInfo(
            id="root", role="Window", name="Test",
            value=None, x=0, y=0, width=800, height=600,
            children=[
                ElementInfo(
                    id="e1", role="Button", name="Normal",
                    value=None, x=10, y=10, width=100, height=30,
                    children=[], properties={},
                ),
                ElementInfo(
                    id="e2", role="Text", name="Hidden",
                    value=None, x=0, y=0, width=0, height=0,
                    children=[], properties={},
                ),
            ], properties={},
        )

        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be:
            backend = MagicMock()
            backend.get_element_tree.return_value = tree
            mock_be.return_value = backend
            result = runner.invoke(main, ["see", "--no-snapshot"])
            assert result.exit_code == 0, result.output
            assert "[0x0]" in result.output
            lines = result.output.split("\n")
            button_line = [l for l in lines if "Normal" in l][0]
            assert "[0x0]" not in button_line

    def test_see_json_output_includes_zero_bounds(self):
        from naturo.backends.base import ElementInfo

        tree = ElementInfo(
            id="root", role="Window", name="Test",
            value=None, x=0, y=0, width=800, height=600,
            children=[
                ElementInfo(
                    id="e2", role="Text", name="Hidden",
                    value=None, x=0, y=0, width=0, height=0,
                    children=[], properties={},
                ),
            ], properties={},
        )

        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be:
            backend = MagicMock()
            backend.get_element_tree.return_value = tree
            mock_be.return_value = backend
            result = runner.invoke(main, ["see", "--json", "--no-snapshot"])
            assert result.exit_code == 0, result.output
            data = json.loads(result.output)

            def find_zero_bounds(node):
                if node.get("zero_bounds"):
                    return node
                for child in node.get("children", []):
                    found = find_zero_bounds(child)
                    if found:
                        return found
                return None

            zero_node = find_zero_bounds(data)
            assert zero_node is not None, "Should find a node with zero_bounds=true"


# ── Test: snapshot.check_ref_status ───────────────────────────────────────────


class TestCheckRefStatus:
    def test_check_ref_status_found(self, tmp_path):
        from naturo.snapshot import SnapshotManager
        from naturo.models.snapshot import UIElement

        mgr = SnapshotManager(storage_root=tmp_path / "snapshots")
        snap_id = mgr.create_snapshot()
        ui_map = {
            "e1": UIElement(
                id="e1", element_id="elem_1", role="Button", title="OK",
                label="OK", value=None, identifier=None,
                frame=(100, 100, 80, 30),
                is_actionable=True, parent_id=None, children=[],
            ),
        }
        mgr.store_detection_result(snap_id, ui_map)
        mgr.store_ref_map(snap_id, {"e1": "elem_1"})

        status = mgr.check_ref_status("e1")
        assert status["status"] == "found"
        assert status["element"].frame == (100, 100, 80, 30)

    def test_check_ref_status_zero_bounds(self, tmp_path):
        from naturo.snapshot import SnapshotManager
        from naturo.models.snapshot import UIElement

        mgr = SnapshotManager(storage_root=tmp_path / "snapshots")
        snap_id = mgr.create_snapshot()
        ui_map = {
            "e1": UIElement(
                id="e1", element_id="elem_1", role="Text", title="Hidden",
                label="", value=None, identifier=None,
                frame=(0, 0, 0, 0),
                is_actionable=False, parent_id=None, children=[],
            ),
        }
        mgr.store_detection_result(snap_id, ui_map)
        mgr.store_ref_map(snap_id, {"e1": "elem_1"})

        status = mgr.check_ref_status("e1")
        assert status["status"] == "zero_bounds"
        assert "zero" in status["message"].lower() or "0x0" in status["message"]

    def test_check_ref_status_not_found(self, tmp_path):
        from naturo.snapshot import SnapshotManager
        from naturo.models.snapshot import UIElement

        mgr = SnapshotManager(storage_root=tmp_path / "snapshots")
        snap_id = mgr.create_snapshot()
        ui_map = {
            "e1": UIElement(
                id="e1", element_id="elem_1", role="Button", title="OK",
                label="OK", value=None, identifier=None,
                frame=(100, 100, 80, 30),
                is_actionable=True, parent_id=None, children=[],
            ),
        }
        mgr.store_detection_result(snap_id, ui_map)
        mgr.store_ref_map(snap_id, {"e1": "elem_1"})

        status = mgr.check_ref_status("e999")
        assert status["status"] == "not_found"

    def test_check_ref_status_no_snapshot(self, tmp_path):
        from naturo.snapshot import SnapshotManager
        mgr = SnapshotManager(storage_root=tmp_path / "snapshots")
        status = mgr.check_ref_status("e1")
        assert status["status"] == "no_snapshot"
