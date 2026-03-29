"""MCP tools for UI snapshot management."""
from __future__ import annotations

import base64
import os
from typing import Optional


def _iter_elements(el):
    """Iterate over all elements in a tree."""
    if el is None:
        return
    yield el
    for c in (el.children or []):
        yield from _iter_elements(c)


def register_snapshot_tools(server, _get_backend, _safe_tool):
    """Register snapshot MCP tools."""

    @server.tool()
    @_safe_tool
    def create_snapshot(
        window_title: Optional[str] = None,
        depth: int = 7,
    ) -> dict:
        """Create a snapshot of the current UI state (screenshot + element tree).

        Captures a screenshot and the UI accessibility tree, storing them together
        for later reference. Essential for AI workflows that need to track UI state
        changes over time.

        Args:
            window_title: Target window (partial match). None = foreground window.
            depth: How deep to traverse the UI tree (1-10, default 7).

        Returns:
            Dict with snapshot_id, screenshot_path (base64), and element tree summary.
        """
        if depth < 1 or depth > 10:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"depth must be between 1 and 10, got {depth}"}}

        from naturo.snapshot import get_snapshot_manager
        backend = _get_backend()
        manager = get_snapshot_manager()

        # Create snapshot and capture
        snapshot_id = manager.create_snapshot()

        # Capture screenshot
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
        try:
            backend.capture_window(window_title=window_title, output_path=temp_path)
            manager.store_screenshot(snapshot_id, temp_path, metadata={
                "window_title": window_title or "foreground",
            })
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        # Capture UI tree
        tree = backend.get_element_tree(window_title=window_title, depth=depth)
        if tree:
            def _convert_elements(el, parent_id=None):
                from naturo.models.snapshot import UIElement
                elem = UIElement(
                    element_id=el.id,
                    role=el.role,
                    name=el.name,
                    value=el.value or "",
                    bounds=(el.x, el.y, el.width, el.height),
                    parent_id=parent_id,
                    children=[_convert_elements(c, el.id) for c in (el.children or [])],
                )
                return elem
            root_elem = _convert_elements(tree)
            manager.store_ui_tree(snapshot_id, root_elem)

        # Load the full snapshot
        snapshot = manager.get_snapshot(snapshot_id)

        response = {
            "success": True,
            "snapshot_id": snapshot_id,
            "screenshot_path": snapshot.screenshot_path,
            "element_count": sum(1 for _ in _iter_elements(tree)) if tree else 0,
        }

        # Include base64 if screenshot exists
        if snapshot.screenshot_path and os.path.exists(snapshot.screenshot_path):
            with open(snapshot.screenshot_path, "rb") as f:
                response["screenshot_base64"] = base64.b64encode(f.read()).decode("ascii")

        return response

    @server.tool()
    @_safe_tool
    def get_snapshot(snapshot_id: str) -> dict:
        """Retrieve a previously created snapshot.

        Args:
            snapshot_id: The snapshot ID returned by create_snapshot.

        Returns:
            Dict with snapshot details including UI tree and screenshot path.
        """
        from naturo.snapshot import get_snapshot_manager
        from naturo.models.snapshot import SnapshotNotFoundError

        manager = get_snapshot_manager()
        try:
            snapshot = manager.get_snapshot(snapshot_id)
        except SnapshotNotFoundError:
            return {"success": False, "error": {"code": "SNAPSHOT_NOT_FOUND", "message": f"Snapshot '{snapshot_id}' not found"}}

        response = {
            "success": True,
            "snapshot_id": snapshot.snapshot_id,
            "created_at": snapshot.created_at,
            "screenshot_path": snapshot.screenshot_path,
            "window_title": snapshot.window_title,
            "application_name": snapshot.application_name,
        }

        # Include element tree summary
        if snapshot.ui_tree:
            def _serialize(el) -> dict:
                d = {
                    "id": el.element_id,
                    "role": el.role,
                    "name": el.name,
                    "bounds": el.bounds,
                }
                if el.children:
                    d["children"] = [_serialize(c) for c in el.children]
                return d
            response["ui_tree"] = _serialize(snapshot.ui_tree)

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
            "snapshots": [
                {
                    "snapshot_id": s.snapshot_id,
                    "created_at": s.created_at,
                    "window_title": s.window_title,
                    "application_name": s.application_name,
                    "is_valid": s.is_valid,
                }
                for s in snapshots
            ],
        }
