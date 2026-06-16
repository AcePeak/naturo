"""Regression tests for #901 — MCP ``app_inspect`` must validate a direct PID.

Root cause: ``app_inspect({pid: <int>})`` went straight to ``detect()`` without
checking that the PID is positive and belongs to a live process.  For any
integer — including impossible values (0, -1, 999999, INT32_MAX) — it returned
``success: true`` with an empty ``exe``/``app`` plus a fabricated
``framework`` and a phantom ``interaction_methods=[{method: vision}]``.  An
agent enumerating PIDs would trust that contract and drive interactions against
a process that does not exist.

The CLI counterpart (``naturo app inspect --pid``) already validates: ``pid<=0``
→ ``INVALID_INPUT`` and a missing process → ``PROCESS_NOT_FOUND``.  These tests
lock the MCP surface to the same loud-failure contract (naturo never lies).
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:  # pragma: no cover - mcp optional
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


def _call_tool(server, tool_name: str, arguments: dict):
    """Drive an MCP tool to completion and return its result list."""
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@pytest.fixture
def server():
    """An MCP server whose backend is mocked away (app_inspect probes directly)."""
    with patch("naturo.mcp_server.get_backend", return_value=MagicMock()):
        yield create_server()


@pytest.mark.parametrize("bogus_pid", [0, -1, -2147483648])
def test_non_positive_pid_is_invalid_input(server, bogus_pid):
    """A PID <= 0 cannot exist — reject it with INVALID_INPUT, never probe."""
    with patch("naturo.detect.detect") as mock_detect:
        result = _call_tool(server, "app_inspect", {"pid": bogus_pid})
    data = json.loads(result[0].text)
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_INPUT"
    mock_detect.assert_not_called()


@pytest.mark.parametrize("missing_pid", [1, 999999, 2147483647])
def test_unknown_pid_is_process_not_found(server, missing_pid):
    """A positive but non-existent PID must surface PROCESS_NOT_FOUND, not success."""
    with (
        patch("naturo.process.find_process", return_value=None),
        patch("naturo.detect.detect") as mock_detect,
    ):
        result = _call_tool(server, "app_inspect", {"pid": missing_pid})
    data = json.loads(result[0].text)
    assert data["success"] is False
    assert data["error"]["code"] == "PROCESS_NOT_FOUND"
    # The phantom contract from the bug must never appear.
    assert "framework" not in data
    assert "interaction_methods" not in data
    mock_detect.assert_not_called()


def test_live_pid_is_inspected_and_exe_populated(server):
    """A real PID is detected normally, with exe/app resolved from the process."""
    fake_proc = MagicMock()
    fake_proc.pid = 4321
    fake_proc.path = "C:\\Windows\\System32\\notepad.exe"
    fake_proc.name = "notepad.exe"
    fake_detect_result = MagicMock()
    fake_detect_result.to_dict.return_value = {
        "frameworks": ["win32"],
        "methods": ["uia"],
        "recommended": "uia",
    }
    with (
        patch("naturo.process.find_process", return_value=fake_proc),
        patch("naturo.detect.detect", return_value=fake_detect_result) as mock_detect,
    ):
        result = _call_tool(server, "app_inspect", {"pid": 4321})
    data = json.loads(result[0].text)
    assert data["success"] is True
    assert data["recommended"] == "uia"
    mock_detect.assert_called_once()
    # The validated process feeds detect() so exe is no longer empty (#901).
    call_kwargs = mock_detect.call_args[1]
    assert call_kwargs["pid"] == 4321
    assert call_kwargs["exe"] == "C:\\Windows\\System32\\notepad.exe"
