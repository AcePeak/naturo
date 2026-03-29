"""Tests for click --app window foreground activation (#608).

When --app is specified, the target window MUST be brought to the
foreground before clicking — otherwise the click lands on whatever
window happens to be on top at those screen coordinates.

The fix uses backend.focus_window() which employs the AttachThreadInput
workaround instead of raw SetForegroundWindow() which fails silently.
"""
from __future__ import annotations

from typing import Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from naturo.models.snapshot import Snapshot, UIElement


def _make_snapshot(
    snapshot_id: str = "test-snap-001",
    window_handle: Optional[int] = 0x12345,
) -> Snapshot:
    """Create a test snapshot with element refs."""
    elements = {
        "e10": UIElement(
            id="e10",
            element_id="element_10",
            role="Button",
            title="OK",
            frame=(100, 200, 40, 40),
        ),
    }
    return Snapshot(
        snapshot_id=snapshot_id,
        ui_map=elements,
        window_handle=window_handle,
        application_name="Notepad",
        application_pid=5678,
        window_title="Untitled - Notepad",
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


class TestClickAppForeground:
    """Verify that click --app always activates the target window (#608)."""

    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._get_backend")
    def test_en_ref_with_snapshot_hwnd_calls_focus_window(
        self, mock_get_backend, mock_get_mgr
    ):
        """eN ref with cached snapshot HWND should call focus_window()."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot(window_handle=0xABCDE)
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["e10", "--no-verify"])

        backend.focus_window.assert_called_once_with(hwnd=0xABCDE)

    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._get_backend")
    def test_en_ref_without_snapshot_hwnd_resolves_via_app(
        self, mock_get_backend, mock_get_mgr
    ):
        """eN ref without cached HWND + --app should resolve HWND and focus."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot(window_handle=None)
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        backend._resolve_hwnd.return_value = 0x99999
        backend._resolve_hwnds.return_value = [0x99999]
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["e10", "--app", "notepad", "--no-verify"])

        backend._resolve_hwnd.assert_called_once()
        backend.focus_window.assert_called_once_with(hwnd=0x99999)

    @patch("naturo.cli.interaction._auto_route")
    @patch("naturo.cli.interaction._get_backend")
    def test_coords_with_app_calls_focus_window(
        self, mock_get_backend, mock_auto_route
    ):
        """--coords + --app should resolve HWND and call focus_window()."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        backend = MagicMock()
        backend._resolve_hwnd.return_value = 0x77777
        mock_get_backend.return_value = backend
        mock_auto_route.return_value = {}

        runner = CliRunner()
        result = runner.invoke(
            click_cmd,
            ["--coords", "500", "300", "--app", "notepad", "--no-verify"],
        )

        backend._resolve_hwnd.assert_called_once()
        backend.focus_window.assert_called_once_with(hwnd=0x77777)

    @patch("naturo.cli.interaction._auto_route")
    @patch("naturo.cli.interaction._get_backend")
    def test_coords_with_hwnd_calls_focus_window(
        self, mock_get_backend, mock_auto_route
    ):
        """--coords + --hwnd should call focus_window() with the provided HWND."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        backend = MagicMock()
        backend._resolve_hwnd.return_value = 349525
        mock_get_backend.return_value = backend
        mock_auto_route.return_value = {}

        runner = CliRunner()
        result = runner.invoke(
            click_cmd,
            ["--coords", "500", "300", "--hwnd", "349525", "--no-verify"],
        )

        backend.focus_window.assert_called_once_with(hwnd=349525)

    @patch("naturo.cli.interaction._auto_route")
    @patch("naturo.cli.interaction._get_backend")
    def test_coords_with_pid_calls_focus_window(
        self, mock_get_backend, mock_auto_route
    ):
        """--coords + --pid should resolve HWND and call focus_window()."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        backend = MagicMock()
        backend._resolve_hwnd.return_value = 0x33333
        mock_get_backend.return_value = backend
        mock_auto_route.return_value = {}

        runner = CliRunner()
        result = runner.invoke(
            click_cmd,
            ["--coords", "500", "300", "--pid", "1234", "--no-verify"],
        )

        backend._resolve_hwnd.assert_called_once()
        backend.focus_window.assert_called_once_with(hwnd=0x33333)

    @patch("naturo.cli.interaction._auto_route")
    @patch("naturo.cli.interaction._get_backend")
    def test_no_app_flag_no_focus(self, mock_get_backend, mock_auto_route):
        """Without --app/--hwnd/--pid, focus_window() should NOT be called."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        backend = MagicMock()
        mock_get_backend.return_value = backend
        mock_auto_route.return_value = {}

        runner = CliRunner()
        result = runner.invoke(
            click_cmd, ["--coords", "500", "300", "--no-verify"]
        )

        backend.focus_window.assert_not_called()

    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._get_backend")
    def test_focus_failure_does_not_block_click(
        self, mock_get_backend, mock_get_mgr
    ):
        """If focus_window() raises, the click should still proceed."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot(window_handle=0xABCDE)
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        backend.focus_window.side_effect = OSError("focus failed")
        backend._is_applicationframehost.return_value = False
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["e10", "--no-verify"])

        # Click should still have been attempted despite focus failure
        backend.click.assert_called_once()
