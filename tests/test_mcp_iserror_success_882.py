"""MCP transport ``isError`` must track the payload ``success`` flag (#882).

Before the fix, a naturo tool that *returns* a ``{"success": false, ...}``
envelope (rather than raising) reached the client with the transport-level
``isError: false`` — forcing agents to check both ``isError`` AND
``payload.success``. This pins the single-discriminator contract:
``isError == not success`` for every tool result.

The check runs against the real low-level ``CallToolRequest`` handler (the
transport layer that stamps ``isError``), with a mocked backend so it collects
on any platform — no desktop required.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from mcp import types
    from naturo.mcp_server import create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


@pytest.fixture
def backend() -> MagicMock:
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


def _dispatch(server, tool: str, args: dict) -> types.CallToolResult:
    """Invoke the real transport CallToolRequest handler and return its result."""
    handler = server._mcp_server.request_handlers[types.CallToolRequest]
    req = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(name=tool, arguments=args),
    )

    async def _run():
        return await handler(req)

    loop = asyncio.new_event_loop()
    try:
        server_result = loop.run_until_complete(_run())
    finally:
        loop.close()
    return server_result.root


def _payload(result: types.CallToolResult) -> dict:
    return json.loads(result.content[0].text)


def test_failure_payload_sets_iserror_true(server, backend):
    """A ``success: false`` envelope must arrive with ``isError == True``."""
    # depth=-1 is the remaining input-validation failure (#1289): the tool
    # returns a {"success": false, ...} envelope rather than raising.
    result = _dispatch(server, "see_ui_tree", {"depth": -1})
    payload = _payload(result)

    assert payload["success"] is False
    assert result.isError is True
    # The single-discriminator contract: isError == not success.
    assert result.isError == (not payload["success"])


def test_success_payload_keeps_iserror_false(server, backend):
    """A ``success: true`` result must keep ``isError == False``."""
    from naturo.backends.base import MonitorInfo

    backend.list_monitors.return_value = [
        MonitorInfo(
            index=0, name="\\\\.\\DISPLAY1", x=0, y=0, width=1920, height=1080,
            is_primary=True, scale_factor=1.0, dpi=96,
        )
    ]
    result = _dispatch(server, "list_monitors", {})
    payload = _payload(result)

    assert payload["success"] is True
    assert result.isError is False
    assert result.isError == (not payload["success"])


def test_content_reports_failure_helper():
    """Unit-pin the discriminator helper across the shapes it must handle."""
    from mcp.types import TextContent
    from naturo.mcp_server import _content_reports_failure

    fail = [TextContent(type="text", text=json.dumps({"success": False}))]
    ok = [TextContent(type="text", text=json.dumps({"success": True}))]
    assert _content_reports_failure(fail) is True
    assert _content_reports_failure(ok) is False
    # Non-JSON / no success flag → never a positive failure signal.
    assert _content_reports_failure([TextContent(type="text", text="hi")]) is False
    assert _content_reports_failure([]) is False
    # structuredContent takes precedence when it carries the flag.
    assert _content_reports_failure(ok, {"success": False}) is True
