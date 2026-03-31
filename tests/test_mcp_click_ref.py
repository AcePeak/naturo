"""Tests for MCP click eN ref resolution (fixes #682).

Verifies that element refs (eN) returned by see_ui_tree can be used
in subsequent click calls within the same MCP session. The snapshot
manager bridges the two calls by persisting the element tree.
"""
from __future__ import annotations

import asyncio
import json
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


def _make_element(**overrides):
    """Create a mock element with standard attributes."""
    el = MagicMock()
    el.id = overrides.get("id", "btn_ok")
    el.role = overrides.get("role", "Button")
    el.name = overrides.get("name", "OK")
    el.value = overrides.get("value", None)
    el.x = overrides.get("x", 100)
    el.y = overrides.get("y", 200)
    el.width = overrides.get("width", 80)
    el.height = overrides.get("height", 30)
    el.properties = overrides.get("properties", {})
    el.children = overrides.get("children", [])
    el.is_actionable = overrides.get("is_actionable", False)
    return el


@pytest.fixture
def snapshot_mgr(tmp_path):
    """Real SnapshotManager using a temp directory."""
    from naturo.snapshot import SnapshotManager
    return SnapshotManager(storage_root=tmp_path, session="test")


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.get_element_tree.return_value = _make_element()
    return backend


@pytest.fixture
def server(mock_backend, snapshot_mgr):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend), \
         patch("naturo.snapshot.get_snapshot_manager", return_value=snapshot_mgr):
        yield create_server()


class TestClickWithEnRef:
    """Test that click can resolve eN refs from see_ui_tree."""

    def test_see_then_click_resolves_ref(self, server, mock_backend):
        """Core workflow: see_ui_tree → click(element_id=eN) succeeds."""
        # Step 1: Call see_ui_tree to capture the element tree
        see_result = _call_tool(server, "see_ui_tree", {})
        see_data = json.loads(see_result[0].text)
        assert see_data["success"] is True

        # Get the element ID from the tree
        element_ref = see_data["tree"]["id"]
        assert element_ref.startswith("e")

        # Step 2: Click using the element ref
        click_result = _call_tool(server, "click", {"element_id": element_ref})
        click_data = json.loads(click_result[0].text)
        assert click_data["success"] is True

        # Verify backend.click was called with resolved coordinates (center of 100,200 80x30)
        mock_backend.click.assert_called_once()
        call_kwargs = mock_backend.click.call_args
        assert call_kwargs.kwargs.get("x") == 140  # 100 + 80/2
        assert call_kwargs.kwargs.get("y") == 215  # 200 + 30/2
        assert call_kwargs.kwargs.get("element_id") is None  # ref resolved to coords

    def test_see_then_click_child_element(self, server, mock_backend):
        """Click on a child element ref from see_ui_tree."""
        child = _make_element(id="save_btn", role="Button", name="Save",
                              x=300, y=400, width=100, height=40)
        parent = _make_element(id="toolbar", role="ToolBar", name="Main",
                               x=0, y=0, width=800, height=50, children=[child])
        mock_backend.get_element_tree.return_value = parent

        # Capture tree
        see_result = _call_tool(server, "see_ui_tree", {})
        see_data = json.loads(see_result[0].text)
        child_ref = see_data["tree"]["children"][0]["id"]

        # Click child
        click_result = _call_tool(server, "click", {"element_id": child_ref})
        click_data = json.loads(click_result[0].text)
        assert click_data["success"] is True

        # Verify coordinates are center of child (300,400 100x40)
        call_kwargs = mock_backend.click.call_args
        assert call_kwargs.kwargs.get("x") == 350  # 300 + 100/2
        assert call_kwargs.kwargs.get("y") == 420  # 400 + 40/2

    def test_click_unknown_ref_returns_error(self, server, mock_backend):
        """Click with an eN ref that doesn't exist returns ELEMENT_NOT_FOUND."""
        click_result = _call_tool(server, "click", {"element_id": "e9999"})
        click_data = json.loads(click_result[0].text)
        assert click_data["success"] is False
        assert click_data["error"]["code"] == "ELEMENT_NOT_FOUND"
        assert "e9999" in click_data["error"]["message"]

    def test_click_non_ref_passes_to_backend(self, server, mock_backend):
        """Click with a non-eN element_id passes through to backend."""
        _call_tool(server, "click", {"element_id": "Button:Save"})
        call_kwargs = mock_backend.click.call_args
        assert call_kwargs.kwargs.get("element_id") == "Button:Save"

    def test_click_coordinates_bypass_ref_resolution(self, server, mock_backend):
        """Click with explicit (x, y) coordinates doesn't touch snapshot manager."""
        click_result = _call_tool(server, "click", {"x": 500, "y": 300})
        click_data = json.loads(click_result[0].text)
        assert click_data["success"] is True
        call_kwargs = mock_backend.click.call_args
        assert call_kwargs.kwargs.get("x") == 500
        assert call_kwargs.kwargs.get("y") == 300

    def test_see_stores_snapshot_id(self, server, mock_backend):
        """see_ui_tree response includes a snapshot_id."""
        result = _call_tool(server, "see_ui_tree", {})
        data = json.loads(result[0].text)
        assert "snapshot_id" in data
        assert isinstance(data["snapshot_id"], str)
        assert len(data["snapshot_id"]) > 0

    def test_click_right_button_with_ref(self, server, mock_backend):
        """Right-click using an eN ref."""
        see_result = _call_tool(server, "see_ui_tree", {})
        see_data = json.loads(see_result[0].text)
        element_ref = see_data["tree"]["id"]

        click_result = _call_tool(server, "click", {
            "element_id": element_ref,
            "button": "right",
        })
        click_data = json.loads(click_result[0].text)
        assert click_data["success"] is True
        assert mock_backend.click.call_args.kwargs.get("button") == "right"

    def test_click_double_with_ref(self, server, mock_backend):
        """Double-click using an eN ref."""
        see_result = _call_tool(server, "see_ui_tree", {})
        see_data = json.loads(see_result[0].text)
        element_ref = see_data["tree"]["id"]

        click_result = _call_tool(server, "click", {
            "element_id": element_ref,
            "double": True,
        })
        click_data = json.loads(click_result[0].text)
        assert click_data["success"] is True
        assert mock_backend.click.call_args.kwargs.get("double") is True
