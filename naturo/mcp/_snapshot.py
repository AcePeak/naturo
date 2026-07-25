"""MCP tools for UI snapshot management."""
from __future__ import annotations


def register_snapshot_tools(server, _get_backend, _safe_tool):
    """Register snapshot MCP tools."""

    @server.tool()
    @_safe_tool
    def get_snapshot(snapshot_id: str) -> dict:
        """Retrieve a previously created snapshot.

        Args:
            snapshot_id: The snapshot ID returned by a snapshot-creating tool.

        Returns:
            Dict with snapshot details including UI tree and screenshot path.
        """
        from naturo.models.snapshot import SnapshotNotFoundError
        from naturo.snapshot import get_snapshot_manager

        manager = get_snapshot_manager()
        try:
            snapshot = manager.get_snapshot(snapshot_id)
        except SnapshotNotFoundError:
            return {"success": False, "error": {"code": "SNAPSHOT_NOT_FOUND", "message": f"Snapshot '{snapshot_id}' not found"}}

        response = {
            "success": True,
            "snapshot_id": snapshot.snapshot_id,
            "last_update_time": snapshot.last_update_time.isoformat(),
            "screenshot_path": snapshot.screenshot_path,
            "window_title": snapshot.window_title,
            "application_name": snapshot.application_name,
        }

        # Include element map summary
        if snapshot.ui_map:
            response["element_count"] = len(snapshot.ui_map)
            response["elements"] = [
                {
                    "id": el.id,
                    "role": el.role,
                    "title": el.title,
                    "frame": list(el.frame),
                }
                for el in snapshot.ui_map.values()
            ]

        return response

    @server.tool()
    @_safe_tool
    def list_snapshots(limit: int = 10) -> dict:
        """List recent snapshots.

        Args:
            limit: Maximum number of snapshots to return (default 10).

        Returns:
            Dict with list of snapshot summaries.
        """
        if limit < 1:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"limit must be >= 1, got {limit}"}}

        from naturo.snapshot import get_snapshot_manager
        manager = get_snapshot_manager()
        snapshots = manager.list_snapshots(limit=limit)

        return {
            "success": True,
            "session": manager.session,
            "snapshots": [
                {
                    "id": s.id,
                    "created_at": s.created_at.isoformat(),
                    "last_accessed_at": s.last_accessed_at.isoformat(),
                    "size_bytes": s.size_in_bytes,
                    "screenshot_count": s.screenshot_count,
                    "application_name": s.application_name,
                }
                for s in snapshots
            ],
        }
