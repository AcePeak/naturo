"""Tests for click --app validation with eN refs (#533).

When `click --app doesnotexist e1` is run, it must error with
WINDOW_NOT_FOUND instead of silently clicking the cached element.
"""
from __future__ import annotations

from typing import Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from naturo.models.snapshot import Snapshot, UIElement


def _make_snapshot(
    snapshot_id: str = "test-snap-001",
    window_handle: Optional[int] = 0x12345,
    elements: Optional[Dict[str, UIElement]] = None,
) -> Snapshot:
    """Create a test snapshot with element refs."""
    if elements is None:
        elements = {
            "e1": UIElement(
                id="e1",
                element_id="element_1",
                role="Button",
                title="OK",
                frame=(100, 200, 40, 40),
            ),
        }
    return Snapshot(
        snapshot_id=snapshot_id,
        ui_map=elements,
        window_handle=window_handle,
        application_name="Calculator",
        application_pid=1234,
        window_title="Calculator",
    )


def _make_mock_snapshot_manager(snapshot: Snapshot) -> MagicMock:
    """Create a mock SnapshotManager that resolves refs from the snapshot."""
    mgr = MagicMock()

    def resolve_ref(ref: str):
        el = snapshot.ui_map.get(ref)
        if el is None:
            return None
        ex, ey, ew, eh = el.frame
        if ew == 0 and eh == 0:
            return None
        cx = ex + ew // 2
        cy = ey + eh // 2
        return (cx, cy, snapshot.snapshot_id)

    def resolve_ref_element(ref: str):
        el = snapshot.ui_map.get(ref)
        if el is None:
            return None
        return (el, snapshot.snapshot_id)

    mgr.resolve_ref.side_effect = resolve_ref
    mgr.resolve_ref_element.side_effect = resolve_ref_element
    mgr.get_snapshot.return_value = snapshot
    return mgr


class TestClickAppValidation:
    """Verify --app is validated even when eN ref resolves from cache (#533)."""

    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._get_backend")
    def test_nonexistent_app_with_en_ref_errors(
        self, mock_get_backend, mock_get_mgr
    ):
        """click --app doesnotexist e1 must fail with WINDOW_NOT_FOUND."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot()
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        backend._resolve_hwnds.return_value = []  # No windows found
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, [
            "e1", "--app", "doesnotexist", "--no-verify",
        ])

        assert result.exit_code != 0
        assert "No windows found" in (result.output or "")

    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._get_backend")
    def test_nonexistent_app_with_en_ref_json_errors(
        self, mock_get_backend, mock_get_mgr
    ):
        """click --app doesnotexist e1 --json must return WINDOW_NOT_FOUND."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot()
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        backend._resolve_hwnds.return_value = []
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, [
            "e1", "--app", "doesnotexist", "--no-verify", "--json",
        ])

        assert result.exit_code != 0
        assert "WINDOW_NOT_FOUND" in (result.output or "")

    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._get_backend")
    def test_valid_app_with_en_ref_succeeds(
        self, mock_get_backend, mock_get_mgr
    ):
        """click --app calculator e1 must succeed when app windows exist."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot()
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        backend._resolve_hwnds.return_value = [0x12345]  # Found a window
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, [
            "e1", "--app", "calculator", "--no-verify",
        ])

        # Should NOT error with WINDOW_NOT_FOUND
        assert "No windows found" not in (result.output or "")

    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._get_backend")
    def test_en_ref_without_app_flag_still_works(
        self, mock_get_backend, mock_get_mgr
    ):
        """click e1 (no --app) must work as before — no app validation."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot()
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["e1", "--no-verify"])

        # _resolve_hwnds should NOT be called when --app is not provided
        backend._resolve_hwnds.assert_not_called()
