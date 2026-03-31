"""Tests for naturo.mcp._snapshot — verifying create_snapshot and get_snapshot
correctly use UIElement fields and SnapshotManager methods.

Regression tests for bug #669.
"""
from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


def _call_tool(server, tool_name: str, arguments: dict):
    """Helper to call an MCP tool function by name."""
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


def _make_element(id="e1", role="Button", name="OK", value="", x=10, y=20, width=80, height=30, children=None):
    el = MagicMock()
    el.id = id
    el.role = role
    el.name = name
    el.value = value
    el.x = x
    el.y = y
    el.width = width
    el.height = height
    el.children = children or []
    return el


@pytest.fixture
def mock_backend():
    return MagicMock()


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


class TestCreateSnapshotTreeConversion:
    """Regression tests for #669: _convert_elements used wrong UIElement fields."""

    def test_tree_stored_via_store_detection_result(self, server, mock_backend, tmp_path):
        """Verify create_snapshot calls store_detection_result (not store_ui_tree)."""
        png_file = tmp_path / "snap.png"
        png_file.write_bytes(b"\x89PNGdata")

        child = _make_element(id="e2", role="Text", name="Hello")
        root = _make_element(id="e1", role="Window", name="Main", children=[child])

        mock_manager = MagicMock()
        mock_manager.create_snapshot.return_value = "snap-001"

        mock_snapshot = MagicMock()
        mock_snapshot.screenshot_path = str(png_file)
        mock_manager.get_snapshot.return_value = mock_snapshot

        mock_backend.get_element_tree.return_value = root

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "create_snapshot", {})

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["element_count"] == 2

        # Must call store_detection_result, NOT store_ui_tree
        mock_manager.store_detection_result.assert_called_once()
        call_args = mock_manager.store_detection_result.call_args
        snapshot_id_arg = call_args[0][0]
        ui_map_arg = call_args[0][1]
        assert snapshot_id_arg == "snap-001"
        assert len(ui_map_arg) == 2
        assert "e1" in ui_map_arg
        assert "e2" in ui_map_arg

    def test_uielement_fields_correct(self, server, mock_backend, tmp_path):
        """Verify UIElement is created with correct field names (title, frame, not name, bounds)."""
        png_file = tmp_path / "snap.png"
        png_file.write_bytes(b"\x89PNGdata")

        root = _make_element(id="btn1", role="Button", name="Save", x=100, y=200, width=80, height=30)

        mock_manager = MagicMock()
        mock_manager.create_snapshot.return_value = "snap-002"
        mock_snapshot = MagicMock()
        mock_snapshot.screenshot_path = str(png_file)
        mock_manager.get_snapshot.return_value = mock_snapshot
        mock_backend.get_element_tree.return_value = root

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "create_snapshot", {})

        data = json.loads(result[0].text)
        assert data["success"] is True

        ui_map = mock_manager.store_detection_result.call_args[0][1]
        elem = ui_map["btn1"]
        # Verify correct UIElement fields
        assert elem.id == "btn1"
        assert elem.element_id == "btn1"
        assert elem.role == "Button"
        assert elem.title == "Save"
        assert elem.frame == (100, 200, 80, 30)
        assert elem.children == []

    def test_tree_with_nested_children(self, server, mock_backend, tmp_path):
        """Verify parent_id and children IDs are set correctly for nested trees."""
        png_file = tmp_path / "snap.png"
        png_file.write_bytes(b"\x89PNGdata")

        grandchild = _make_element(id="e3", role="Text", name="Label")
        child = _make_element(id="e2", role="Group", name="Panel", children=[grandchild])
        root = _make_element(id="e1", role="Window", name="Main", children=[child])

        mock_manager = MagicMock()
        mock_manager.create_snapshot.return_value = "snap-003"
        mock_snapshot = MagicMock()
        mock_snapshot.screenshot_path = str(png_file)
        mock_manager.get_snapshot.return_value = mock_snapshot
        mock_backend.get_element_tree.return_value = root

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "create_snapshot", {})

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["element_count"] == 3

        ui_map = mock_manager.store_detection_result.call_args[0][1]
        assert ui_map["e1"].parent_id is None
        assert ui_map["e1"].children == ["e2"]
        assert ui_map["e2"].parent_id == "e1"
        assert ui_map["e2"].children == ["e3"]
        assert ui_map["e3"].parent_id == "e2"
        assert ui_map["e3"].children == []


class TestGetSnapshotFieldMapping:
    """Regression tests for #669: get_snapshot used wrong Snapshot fields."""

    def test_uses_ui_map_not_ui_tree(self, server):
        """Verify get_snapshot reads snapshot.ui_map, not snapshot.ui_tree."""
        from naturo.models.snapshot import UIElement

        elem = UIElement(
            id="e1", element_id="e1", role="Button", title="OK",
            frame=(10, 20, 80, 30),
        )

        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_id = "snap-001"
        mock_snapshot.last_update_time.isoformat.return_value = "2026-03-31T00:00:00+00:00"
        mock_snapshot.screenshot_path = "/tmp/snap.png"
        mock_snapshot.window_title = "Notepad"
        mock_snapshot.application_name = "notepad.exe"
        mock_snapshot.ui_map = {"e1": elem}

        mock_manager = MagicMock()
        mock_manager.get_snapshot.return_value = mock_snapshot

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "get_snapshot", {"snapshot_id": "snap-001"})

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["element_count"] == 1
        assert data["elements"][0]["id"] == "e1"
        assert data["elements"][0]["role"] == "Button"
        assert data["elements"][0]["title"] == "OK"
        assert data["elements"][0]["frame"] == [10, 20, 80, 30]

    def test_uses_last_update_time(self, server):
        """Verify get_snapshot uses last_update_time, not created_at."""
        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_id = "snap-002"
        mock_snapshot.last_update_time.isoformat.return_value = "2026-03-31T12:00:00+00:00"
        mock_snapshot.screenshot_path = None
        mock_snapshot.window_title = None
        mock_snapshot.application_name = None
        mock_snapshot.ui_map = {}

        mock_manager = MagicMock()
        mock_manager.get_snapshot.return_value = mock_snapshot

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "get_snapshot", {"snapshot_id": "snap-002"})

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["last_update_time"] == "2026-03-31T12:00:00+00:00"
        assert "created_at" not in data

    def test_empty_ui_map_no_elements(self, server):
        """Verify empty ui_map results in no elements key."""
        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_id = "snap-003"
        mock_snapshot.last_update_time.isoformat.return_value = "2026-03-31T00:00:00+00:00"
        mock_snapshot.screenshot_path = None
        mock_snapshot.window_title = None
        mock_snapshot.application_name = None
        mock_snapshot.ui_map = {}

        mock_manager = MagicMock()
        mock_manager.get_snapshot.return_value = mock_snapshot

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "get_snapshot", {"snapshot_id": "snap-003"})

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "elements" not in data
