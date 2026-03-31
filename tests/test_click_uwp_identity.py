"""Tests for UWP click identity-based element lookup (#681).

When clicking an eN ref on a UWP app, click_element_uia should use the
element's name and AutomationId from the snapshot to find the live UIA
element — rather than relying solely on ElementFromPoint(x, y) which
can resolve to the wrong element when cached coordinates are stale.
"""
from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from naturo.models.snapshot import Snapshot, UIElement


def _make_snapshot(
    snapshot_id: str = "test-snap-uwp",
    window_handle: Optional[int] = 0x12345,
) -> Snapshot:
    """Create a test snapshot with a MenuItem element (like UWP Notepad menu)."""
    elements = {
        "e13": UIElement(
            id="e13",
            element_id="element_13",
            role="MenuItem",
            title="File",
            identifier="MenuItemFile",
            frame=(100, 50, 60, 30),
            is_actionable=True,
        ),
        "e5": UIElement(
            id="e5",
            element_id="element_5",
            role="Button",
            title="Bold",
            identifier="BoldButton",
            frame=(200, 100, 30, 30),
            is_actionable=True,
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


class TestUwpClickIdentityLookup:
    """Verify that UWP click passes element metadata for identity-based lookup (#681)."""

    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._common._get_backend")
    def test_uwp_click_passes_element_metadata(
        self, mock_get_backend, mock_get_mgr
    ):
        """When clicking eN on a UWP app, element name/id/role should be
        passed to click_element_uia for identity-based lookup."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot(window_handle=0xABCDE)
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        backend._is_afh_window.return_value = True  # UWP app
        backend._resolve_hwnds.return_value = [0xABCDE]
        backend.click_element_uia.return_value = True
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["e13", "--app", "notepad", "--no-verify"])

        assert result.exit_code == 0, result.output

        # Verify click_element_uia was called with element metadata
        backend.click_element_uia.assert_called_once()
        call_kwargs = backend.click_element_uia.call_args
        # Check coordinates
        assert call_kwargs.kwargs["x"] == 130  # 100 + 60//2
        assert call_kwargs.kwargs["y"] == 65   # 50 + 30//2
        # Check identity metadata from snapshot
        assert call_kwargs.kwargs["element_name"] == "File"
        assert call_kwargs.kwargs["element_automation_id"] == "MenuItemFile"
        assert call_kwargs.kwargs["element_role"] == "MenuItem"

    @patch("naturo.snapshot.get_snapshot_manager")
    @patch("naturo.cli.interaction._common._get_backend")
    def test_non_uwp_click_does_not_use_uia(
        self, mock_get_backend, mock_get_mgr
    ):
        """Non-UWP apps should use regular coordinate click, not click_element_uia."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        snapshot = _make_snapshot(window_handle=0xABCDE)
        mgr = _make_mock_snapshot_manager(snapshot)
        mock_get_mgr.return_value = mgr

        backend = MagicMock()
        backend._is_afh_window.return_value = False  # NOT UWP
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, ["e13", "--no-verify"])

        assert result.exit_code == 0, result.output

        # click_element_uia should NOT be called for non-UWP
        backend.click_element_uia.assert_not_called()
        # Regular click should be called with coordinates
        backend.click.assert_called_once()

    @patch("naturo.cli.interaction._common._auto_route")
    @patch("naturo.cli.interaction._common._get_backend")
    def test_uwp_click_without_ref_no_element_metadata(
        self, mock_get_backend, mock_auto_route
    ):
        """Coordinate-based click on UWP (no eN ref) should not pass element metadata."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        mock_auto_route.return_value = {}

        backend = MagicMock()
        backend._is_afh_window.return_value = True  # UWP
        backend._resolve_hwnd.return_value = 0xABCDE
        backend.click_element_uia.return_value = True
        mock_get_backend.return_value = backend

        runner = CliRunner()
        result = runner.invoke(click_cmd, [
            "--coords", "200", "300", "--app", "notepad", "--no-verify",
        ])

        assert result.exit_code == 0, result.output

        # click_element_uia called but WITHOUT element metadata
        backend.click_element_uia.assert_called_once()
        call_kwargs = backend.click_element_uia.call_args
        assert call_kwargs.kwargs.get("element_name") is None
        assert call_kwargs.kwargs.get("element_automation_id") is None


class TestClickElementUiaSignature:
    """Verify click_element_uia accepts the new element identity parameters."""

    def test_click_element_uia_accepts_element_metadata_params(self):
        """click_element_uia signature should accept element_name,
        element_automation_id, and element_role keyword arguments."""
        from naturo.backends.windows._input import InputMixin
        import inspect

        sig = inspect.signature(InputMixin.click_element_uia)
        param_names = list(sig.parameters.keys())
        assert "element_name" in param_names
        assert "element_automation_id" in param_names
        assert "element_role" in param_names

    def test_click_element_uia_defaults_to_none(self):
        """New element identity params should default to None."""
        from naturo.backends.windows._input import InputMixin
        import inspect

        sig = inspect.signature(InputMixin.click_element_uia)
        assert sig.parameters["element_name"].default is None
        assert sig.parameters["element_automation_id"].default is None
        assert sig.parameters["element_role"].default is None
