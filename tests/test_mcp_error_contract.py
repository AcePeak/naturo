"""MCP error contract (M3 criterion 2): every tool error returns the full
self-correcting contract — a REGISTERED code + category + recovery-hint —
never a bare string. Linux-collectable (mocked backend, no desktop).
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from naturo.errors import ElementNotFoundError, ErrorCode, category_for_code

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


def _registered_codes() -> set:
    return {
        v for k, v in vars(ErrorCode).items()
        if not k.startswith("_") and isinstance(v, str)
    }


def _call(server, tool: str, args: dict):
    async def _run():
        return await server.call_tool(tool, args)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


def _error_of(result) -> dict:
    data = json.loads(result[0].text)
    assert data["success"] is False, data
    return data["error"]


def _assert_full_contract(err: dict) -> None:
    """Every MCP error: registered code + matching category + recovery-hint key."""
    assert err["code"] in _registered_codes(), f"{err['code']!r} is not a registered ErrorCode"
    assert err["category"] == category_for_code(err["code"]), err
    assert "message" in err and err["message"]
    # recovery-hint is always present as a key (may be null for terse errors)
    assert "suggested_action" in err, err


@pytest.fixture
def backend():
    b = MagicMock()
    b._resolve_hwnd.return_value = 12345
    return b


@pytest.fixture
def snapshot_mgr(tmp_path):
    from naturo.snapshot import SnapshotManager
    return SnapshotManager(storage_root=tmp_path, session="test")


@pytest.fixture
def server(backend, snapshot_mgr):
    with patch("naturo.mcp_server.get_backend", return_value=backend), \
         patch("naturo.snapshot.get_snapshot_manager", return_value=snapshot_mgr):
        yield create_server()


def _list_tools(server):
    async def _run():
        return await server.list_tools()

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


def test_every_tool_advertises_description_and_input_schema(server):
    """M3 criterion 1: each MCP tool is a clean, agent-legible tool."""
    tools = _list_tools(server)
    assert tools, "no MCP tools registered"
    for t in tools:
        assert (t.description or "").strip(), f"tool {t.name} has no description"
        schema = t.inputSchema or {}
        assert schema.get("type") == "object", f"tool {t.name} lacks an object input schema"
        assert "properties" in schema, f"tool {t.name} input schema has no properties"


def test_unified_cascade_tree_is_reachable_via_mcp(server):
    """M3 criterion 1: the unified see --cascade tree is an MCP tool surface."""
    names = {t.name for t in _list_tools(server)}
    assert "see_ui_tree" in names
    schema = next(t for t in _list_tools(server) if t.name == "see_ui_tree").inputSchema
    assert "cascade" in schema.get("properties", {}), "see_ui_tree does not expose the cascade param"


def test_invalid_input_has_full_contract(server):
    err = _error_of(_call(server, "see_ui_tree", {"depth": 99}))
    assert err["code"] == ErrorCode.INVALID_INPUT
    assert err["category"] == "validation"
    _assert_full_contract(err)


def test_window_not_found_uses_registered_code(server, backend):
    # Formerly emitted the bare, unregistered "NO_WINDOW".
    backend.get_element_tree.return_value = None
    err = _error_of(_call(server, "see_ui_tree", {"hwnd": 999}))
    assert err["code"] == ErrorCode.WINDOW_NOT_FOUND
    assert err["category"] == "automation"
    _assert_full_contract(err)


def test_element_not_found_inline_dict_gets_category(server, backend):
    # get_element_value returns an inline {code, message} dict; the wrapper must
    # backfill category + the suggested_action key.
    backend.get_element_value.return_value = None
    err = _error_of(_call(server, "get_element_value", {"ref": "e1"}))
    assert err["code"] == ErrorCode.ELEMENT_NOT_FOUND
    assert err["category"] == "automation"
    _assert_full_contract(err)


def test_set_value_failed_is_registered_with_contract(server, backend):
    backend.set_element_value.return_value = False
    err = _error_of(_call(server, "set_element_value", {"value": "x", "ref": "e1"}))
    assert err["code"] == ErrorCode.SET_VALUE_FAILED
    assert err["category"] == "automation"
    _assert_full_contract(err)


def test_raised_naturo_error_yields_full_dict_contract(server, backend):
    # A raised NaturoError flows through e.to_dict(): category + a populated
    # recovery-hint + recoverable + context, not just {code, message}.
    backend.get_element_value.side_effect = ElementNotFoundError("Button:Save")
    err = _error_of(_call(server, "get_element_value", {"ref": "e1"}))
    assert err["code"] == ErrorCode.ELEMENT_NOT_FOUND
    assert err["category"] == "automation"
    assert err["suggested_action"]  # populated, not null
    assert err["recoverable"] is True
    assert "context" in err
    _assert_full_contract(err)
