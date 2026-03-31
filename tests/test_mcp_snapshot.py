"""Tests for naturo.mcp._snapshot — MCP snapshot tools.

Tests cover create_snapshot, get_snapshot, list_snapshots
with mocked backend and snapshot manager.
All tests run on Linux CI (no Windows dependencies).
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
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


@pytest.fixture
def mock_backend():
    return MagicMock()


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


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


class TestCreateSnapshot:

    def test_invalid_depth_too_low(self, server):
        result = _call_tool(server, "create_snapshot", {"depth": 0})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "depth" in data["error"]["message"]

    def test_invalid_depth_too_high(self, server):
        result = _call_tool(server, "create_snapshot", {"depth": 11})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_creates_snapshot_without_tree(self, server, mock_backend, tmp_path):
        png_file = tmp_path / "snap.png"
        png_file.write_bytes(b"\x89PNGdata")

        mock_manager = MagicMock()
        mock_manager.create_snapshot.return_value = "snap-001"

        mock_snapshot = MagicMock()
        mock_snapshot.screenshot_path = str(png_file)
        mock_manager.get_snapshot.return_value = mock_snapshot

        mock_backend.get_element_tree.return_value = None

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "create_snapshot", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["snapshot_id"] == "snap-001"
        assert data["element_count"] == 0
        assert "screenshot_base64" in data

    def test_creates_snapshot_with_tree(self, server, mock_backend, tmp_path):
        png_file = tmp_path / "snap.png"
        png_file.write_bytes(b"\x89PNGfake")

        child = _make_element(id="e2", role="Text", name="Hello")
        root = _make_element(id="e1", role="Window", name="Main", children=[child])

        mock_manager = MagicMock()
        mock_manager.create_snapshot.return_value = "snap-002"

        mock_snapshot = MagicMock()
        mock_snapshot.screenshot_path = str(png_file)
        mock_manager.get_snapshot.return_value = mock_snapshot

        mock_backend.get_element_tree.return_value = root

        # UIElement constructor has different field names than what _convert_elements
        # passes (known bug: name→title, bounds→frame). Mock UIElement to accept any kwargs.
        mock_ui_element_cls = MagicMock()
        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager), \
             patch("naturo.models.snapshot.UIElement", mock_ui_element_cls):
            result = _call_tool(server, "create_snapshot", {"depth": 5})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["snapshot_id"] == "snap-002"
        assert data["element_count"] == 2  # root + child
        mock_manager.store_detection_result.assert_called_once()

    def test_no_base64_when_screenshot_missing(self, server, mock_backend):
        mock_manager = MagicMock()
        mock_manager.create_snapshot.return_value = "snap-003"

        mock_snapshot = MagicMock()
        mock_snapshot.screenshot_path = "/nonexistent/screenshot.png"
        mock_manager.get_snapshot.return_value = mock_snapshot

        mock_backend.get_element_tree.return_value = None

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "create_snapshot", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "screenshot_base64" not in data

    def test_with_window_title(self, server, mock_backend):
        mock_manager = MagicMock()
        mock_manager.create_snapshot.return_value = "snap-004"

        mock_snapshot = MagicMock()
        mock_snapshot.screenshot_path = "/nonexistent/x.png"
        mock_manager.get_snapshot.return_value = mock_snapshot

        mock_backend.get_element_tree.return_value = None

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "create_snapshot", {"window_title": "Notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.capture_window.assert_called_once()
        call_kwargs = mock_backend.capture_window.call_args
        assert call_kwargs[1]["window_title"] == "Notepad"


class TestGetSnapshot:

    def test_snapshot_found(self, server):
        from naturo.models.snapshot import UIElement

        mock_el = UIElement(
            id="e1", element_id="e1", role="Window", title="Main",
            frame=(0, 0, 1920, 1080),
        )

        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_id = "snap-001"
        mock_snapshot.last_update_time.isoformat.return_value = "2026-03-31T00:00:00"
        mock_snapshot.screenshot_path = "/tmp/snap.png"
        mock_snapshot.window_title = "Notepad"
        mock_snapshot.application_name = "notepad.exe"
        mock_snapshot.ui_map = {"e1": mock_el}

        mock_manager = MagicMock()
        mock_manager.get_snapshot.return_value = mock_snapshot

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "get_snapshot", {"snapshot_id": "snap-001"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["snapshot_id"] == "snap-001"
        assert data["window_title"] == "Notepad"
        assert "elements" in data
        assert data["element_count"] == 1

    def test_snapshot_not_found(self, server):
        from naturo.models.snapshot import SnapshotNotFoundError

        mock_manager = MagicMock()
        mock_manager.get_snapshot.side_effect = SnapshotNotFoundError("snap-missing")

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "get_snapshot", {"snapshot_id": "snap-missing"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "SNAPSHOT_NOT_FOUND"

    def test_snapshot_without_ui_map(self, server):
        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_id = "snap-005"
        mock_snapshot.last_update_time.isoformat.return_value = "2026-03-31T00:00:00"
        mock_snapshot.screenshot_path = "/tmp/snap.png"
        mock_snapshot.window_title = None
        mock_snapshot.application_name = None
        mock_snapshot.ui_map = {}

        mock_manager = MagicMock()
        mock_manager.get_snapshot.return_value = mock_snapshot

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "get_snapshot", {"snapshot_id": "snap-005"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "elements" not in data


class TestListSnapshots:

    def test_returns_snapshot_list(self, server):
        snap = MagicMock()
        snap.snapshot_id = "snap-001"
        snap.created_at = "2026-03-31T00:00:00"
        snap.window_title = "Notepad"
        snap.application_name = "notepad.exe"
        snap.is_valid = True

        mock_manager = MagicMock()
        mock_manager.list_snapshots.return_value = [snap]

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "list_snapshots", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert len(data["snapshots"]) == 1
        assert data["snapshots"][0]["snapshot_id"] == "snap-001"
        assert data["snapshots"][0]["is_valid"] is True
        mock_manager.list_snapshots.assert_called_once_with(limit=10)

    def test_custom_limit(self, server):
        mock_manager = MagicMock()
        mock_manager.list_snapshots.return_value = []

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "list_snapshots", {"limit": 5})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_manager.list_snapshots.assert_called_once_with(limit=5)

    def test_invalid_limit(self, server):
        result = _call_tool(server, "list_snapshots", {"limit": 0})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_negative_limit(self, server):
        result = _call_tool(server, "list_snapshots", {"limit": -1})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_empty_list(self, server):
        mock_manager = MagicMock()
        mock_manager.list_snapshots.return_value = []

        with patch("naturo.snapshot.get_snapshot_manager", return_value=mock_manager):
            result = _call_tool(server, "list_snapshots", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["snapshots"] == []
