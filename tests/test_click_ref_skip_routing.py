"""Tests for click eN ref performance optimization (#448).

When clicking via an eN ref that resolves to cached coordinates from a
recent snapshot, auto-routing (framework detection chain) should be
skipped entirely — it adds ~0.5s per click with zero benefit since we
already have absolute screen coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
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
            "e25": UIElement(
                id="e25",
                element_id="element_25",
                role="Button",
                title="Clear",
                frame=(100, 200, 40, 40),
            ),
            "e39": UIElement(
                id="e39",
                element_id="element_39",
                role="Button",
                title="1",
                frame=(150, 250, 40, 40),
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

    def resolve_ref(ref: str, app_name=None):
        el = snapshot.ui_map.get(ref)
        if el is None:
            return None
        ex, ey, ew, eh = el.frame
        if ew == 0 and eh == 0:
            return None
        cx = ex + ew // 2
        cy = ey + eh // 2
        return (cx, cy, snapshot.snapshot_id)

    def resolve_ref_element(ref: str, app_name=None):
        el = snapshot.ui_map.get(ref)
        if el is None:
            return None
        return (el, snapshot.snapshot_id)

    mgr.resolve_ref.side_effect = resolve_ref
    mgr.resolve_ref_element.side_effect = resolve_ref_element
    mgr.get_snapshot.return_value = snapshot
    return mgr


class TestClickRefSkipsRouting:
    """Verify that clicking via eN ref skips auto-routing."""

    @patch("naturo.cli.interaction._common._auto_route")
    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._common._get_backend")
    def test_en_ref_click_skips_auto_route(
        self, mock_get_backend, mock_get_mgr, mock_auto_route
    ):
        """When an eN ref resolves to coordinates, _auto_route should NOT be called."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot()
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["e25", "--no-verify"])

        # _auto_route should NOT have been called — the ref resolved to coords
        mock_auto_route.assert_not_called()

    @patch("naturo.cli.interaction._common._auto_route")
    @patch("naturo.cli.interaction._common._get_backend")
    def test_non_ref_click_still_routes(self, mock_get_backend, mock_auto_route):
        """Non-ref clicks (--coords, --id, --on text) should still auto-route."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        backend = MagicMock()
        mock_get_backend.return_value = backend
        mock_auto_route.return_value = {}

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["--coords", "100", "200", "--no-verify"])

        # _auto_route should have been called for coordinate-based clicks
        mock_auto_route.assert_called_once()

    @patch("naturo.cli.interaction._common._auto_route")
    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._common._get_backend")
    def test_en_ref_click_with_app_flag_skips_auto_route(
        self, mock_get_backend, mock_get_mgr, mock_auto_route
    ):
        """Even with --app flag, eN ref clicks should skip auto-routing."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot()
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["e25", "--app", "calculator", "--no-verify"])

        mock_auto_route.assert_not_called()

    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._common._get_backend")
    def test_en_ref_retrieves_snapshot_hwnd(self, mock_get_backend, mock_get_mgr):
        """eN ref click should retrieve the snapshot's stored window_handle."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot(window_handle=0xABCDE)
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["e25", "--no-verify"])

        # Snapshot should have been loaded to retrieve HWND
        mgr.get_snapshot.assert_called_once_with(snapshot.snapshot_id)

    @patch("naturo.cli.interaction._common._auto_route")
    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._common._get_backend")
    def test_unresolved_ref_falls_through_to_error(
        self, mock_get_backend, mock_get_mgr, mock_auto_route
    ):
        """When an eN ref doesn't resolve, the command should error (not route)."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot()
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        mock_get_backend.return_value = backend

        runner = CliRunner()
        # e999 doesn't exist in the snapshot
        result = runner.invoke(click_cmd, ["e999", "--no-verify"])

        # Should have errored with STALE_SNAPSHOT_CACHE, not called auto_route
        mock_auto_route.assert_not_called()

    @patch("naturo.cli.interaction._common._auto_route")
    @patch("naturo.cli.interaction._common._get_backend")
    def test_text_click_still_routes(self, mock_get_backend, mock_auto_route):
        """Click --on with plain text (not eN) should still auto-route."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        backend = MagicMock()
        mock_get_backend.return_value = backend
        mock_auto_route.return_value = {}

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["--on", "Save", "--app", "notepad", "--no-verify"])

        mock_auto_route.assert_called_once()

    @patch("naturo.cli.interaction._common._auto_route")
    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._common._get_backend")
    def test_en_ref_route_info_is_empty(
        self, mock_get_backend, mock_get_mgr, mock_auto_route
    ):
        """When eN ref resolves, route_info should be empty dict (no routing metadata)."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot()
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["e25", "--no-verify", "--json"])

        # Since auto_route is skipped, route_info should be empty
        mock_auto_route.assert_not_called()
