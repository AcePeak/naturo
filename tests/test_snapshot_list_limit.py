"""Regression tests for #890 — ``list_snapshots`` limit handling.

The MCP ``list_snapshots`` wrapper calls
``SnapshotManager.list_snapshots(limit=...)``, but the manager method did not
accept a ``limit`` parameter, so every MCP call failed with
``TypeError: ... got an unexpected keyword argument 'limit'``. These tests pin
down the contract:

* ``SnapshotManager.list_snapshots`` accepts an optional ``limit`` and slices the
  result newest-first.
* The MCP wrapper returns a CLI-shaped success payload using the real
  ``SnapshotInfo`` fields.

All tests use a temporary on-disk snapshot store and require no real desktop /
UI Automation DLL, so they are intentionally NOT marked ``@pytest.mark.desktop``.
"""
from __future__ import annotations

import asyncio
import json
import time

import pytest

from naturo.snapshot import SnapshotManager


def _make_manager(tmp_path) -> SnapshotManager:
    """Build a SnapshotManager backed by an isolated temporary store."""
    return SnapshotManager(storage_root=tmp_path, session="test-890")


def _populate(manager: SnapshotManager, count: int) -> list[str]:
    """Create ``count`` snapshots with distinct creation times, oldest first."""
    ids: list[str] = []
    for _ in range(count):
        ids.append(manager.create_snapshot())
        # Ensure distinct directory timestamps so ordering is deterministic.
        time.sleep(0.01)
    return ids


class TestSnapshotManagerLimit:
    """Direct unit tests for SnapshotManager.list_snapshots(limit=...)."""

    def test_accepts_limit_kwarg(self, tmp_path):
        """Reproduces #890: passing ``limit=`` must not raise TypeError."""
        manager = _make_manager(tmp_path)
        _populate(manager, 3)

        # Before the fix this raised:
        #   TypeError: list_snapshots() got an unexpected keyword argument 'limit'
        result = manager.list_snapshots(limit=2)

        assert len(result) == 2

    def test_limit_slices_newest_first(self, tmp_path):
        """A limit returns exactly the newest N entries, consistent with the
        unlimited (newest-first) ordering."""
        manager = _make_manager(tmp_path)
        _populate(manager, 4)

        full = manager.list_snapshots()
        limited = manager.list_snapshots(limit=2)

        assert len(full) == 4
        assert limited == full[:2]

    def test_no_limit_returns_all(self, tmp_path):
        """``limit=None`` keeps behaviour identical to the original API."""
        manager = _make_manager(tmp_path)
        _populate(manager, 3)

        assert len(manager.list_snapshots()) == 3
        assert len(manager.list_snapshots(limit=None)) == 3

    def test_limit_larger_than_count_returns_all(self, tmp_path):
        """A limit exceeding the store size returns every snapshot."""
        manager = _make_manager(tmp_path)
        _populate(manager, 2)

        assert len(manager.list_snapshots(limit=10)) == 2

    def test_empty_store(self, tmp_path):
        """An empty store returns an empty list regardless of limit."""
        manager = _make_manager(tmp_path)

        assert manager.list_snapshots() == []
        assert manager.list_snapshots(limit=5) == []


def _call_tool(server, tool_name: str, arguments: dict):
    """Invoke an MCP tool function by name and return its raw result list."""
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:
    mcp_available = False


@pytest.mark.skipif(not mcp_available, reason="mcp package not installed")
class TestMcpListSnapshotsEndToEnd:
    """End-to-end MCP wrapper tests against a real SnapshotManager.

    These would have caught #890 (and the latent field-name mismatch) because
    they exercise the real manager instead of a fully mocked one.
    """

    def test_list_snapshots_succeeds_with_real_manager(self, tmp_path):
        from unittest.mock import patch

        manager = _make_manager(tmp_path)
        _populate(manager, 3)

        with patch("naturo.mcp_server.get_backend"), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=manager):
            server = create_server()
            result = _call_tool(server, "list_snapshots", {"limit": 2})

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["session"] == "test-890"
        assert len(data["snapshots"]) == 2
        # Payload must use the real SnapshotInfo fields (CLI-shaped).
        first = data["snapshots"][0]
        assert "id" in first
        assert "created_at" in first
        assert "application_name" in first

    def test_list_snapshots_empty_store(self, tmp_path):
        from unittest.mock import patch

        manager = _make_manager(tmp_path)

        with patch("naturo.mcp_server.get_backend"), \
             patch("naturo.snapshot.get_snapshot_manager", return_value=manager):
            server = create_server()
            result = _call_tool(server, "list_snapshots", {})

        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["snapshots"] == []
