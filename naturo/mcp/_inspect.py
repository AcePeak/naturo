"""MCP tools for UI inspection and element manipulation."""
from __future__ import annotations

import logging
from typing import Optional

from naturo.mcp._resolve import require_hwnd

logger = logging.getLogger(__name__)


def register_inspect_tools(server, _get_backend, _safe_tool):
    """Register UI inspection MCP tools."""

    @server.tool()
    @_safe_tool
    def see_ui_tree(
        window_title: Optional[str] = None,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
        pid: Optional[int] = None,
        depth: int = 7,
        accessibility_backend: str = "uia",
        cascade: bool = False,
    ) -> dict:
        """Inspect the UI accessibility tree of a window.

        Returns the hierarchical tree of UI elements (buttons, text fields, etc.)
        with their roles, names, bounds, and properties. Element IDs (eN) can be
        used in subsequent ``click``, ``type_text``, and other tool calls.

        Args:
            window_title: Target window (partial match). None = foreground window.
            app: Target application name (partial match). When provided without
                hwnd, enumerates ALL windows of the app and merges their trees.
            hwnd: Window handle (integer). Overrides app/window_title.
            pid: Process ID. Filters windows to this process only.
            depth: How deep to traverse the tree (1-10).
            accessibility_backend: "uia" (default), "msaa" (for legacy apps like
                MFC, VB6, Delphi), "ia2" (for Firefox, Thunderbird, LibreOffice),
                "jab" (for Java/Swing/AWT), or "auto" (try UIA → IA2 → JAB → MSAA).
            cascade: When True, run the unified multi-framework cascade (UIA plus
                the CDP/JAB/COM additive providers) and tag every node with
                ``techniques[]`` + ``correctness`` (deterministic vs uncertain) +
                ``confidence``; deterministic sources are preferred. Also returns
                a top-level ``recognition_summary``. This is the moat: it recovers
                web (CDP), Java (JAB) and Excel-cell (COM) content that UIA
                collapses, so the agent sees one fused, correctness-tagged tree.

        Returns:
            Dict with the element tree structure.
        """
        if depth < 1 or depth > 10:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"depth must be between 1 and 10, got {depth}"}}
        if accessibility_backend not in ("uia", "msaa", "ia2", "jab", "auto"):
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"accessibility_backend must be uia, msaa, ia2, jab, or auto, got {accessibility_backend}"}}
        backend = _get_backend()

        cascade_result = None
        if cascade:
            # (M3) Expose the unified see --cascade fused tree over MCP: run the
            # multi-framework cascade so every node carries techniques[] +
            # correctness + confidence and the caller gets a recognition_summary.
            from naturo.cascade import run_cascade
            cascade_result = run_cascade(
                backend, app=app, window_title=window_title,
                hwnd=hwnd, pid=pid, depth=depth, backend_name="auto",
            )
            tree = cascade_result.tree
        # (#737) When --app is used without --hwnd, enumerate ALL windows
        # of the application and merge their UI trees (matching CLI behavior).
        elif app and not hwnd and hasattr(backend, "_resolve_hwnds"):
            hwnds = backend._resolve_hwnds(app=app)
            if not hwnds:
                return {"success": False, "error": {"code": "NO_WINDOW", "message": f"No windows found for app '{app}'"}}

            from naturo.backends.base import ElementInfo as BaseElementInfo
            window_trees = []
            for h in hwnds:
                subtree = backend.get_element_tree(
                    hwnd=h, depth=depth, backend=accessibility_backend,
                )
                if subtree:
                    window_trees.append((h, subtree))

            if not window_trees:
                return {"success": False, "error": {"code": "NO_WINDOW", "message": "All windows have empty UI trees"}}

            # Single window: use its tree directly
            if len(window_trees) == 1:
                tree = window_trees[0][1]
            else:
                # Merge into a virtual root with each window as a child
                tree = BaseElementInfo(
                    id="app_root", role="Application", name=app,
                    value=None, x=0, y=0, width=0, height=0,
                    children=[], properties={},
                )
                for h, subtree in window_trees:
                    window_node = BaseElementInfo(
                        id=f"window_{h}", role="WindowGroup",
                        name=f"{subtree.name} (HWND:{h})",
                        value=None, x=subtree.x, y=subtree.y,
                        width=subtree.width, height=subtree.height,
                        children=[subtree], properties={},
                    )
                    tree.children.append(window_node)
        else:
            tree = backend.get_element_tree(
                app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                depth=depth, backend=accessibility_backend,
            )
        if tree is None:
            return {"success": False, "error": {"code": "NO_WINDOW", "message": "No matching window found"}}

        # (#682) Store element tree in the snapshot manager so eN refs can be
        # resolved by subsequent click/type_text calls in the same session.
        from naturo.refs import assign_stable_refs
        from naturo.models.snapshot import UIElement
        from naturo.snapshot import get_snapshot_manager

        element_obj_to_ref: dict[int, str] = {}
        ui_map, ref_map = assign_stable_refs(
            tree, UIElement, element_obj_to_ref=element_obj_to_ref,
        )

        mgr = get_snapshot_manager()
        snapshot_id = mgr.create_snapshot()
        mgr.store_detection_result(snapshot_id, ui_map)
        mgr.store_ref_map(snapshot_id, ref_map)

        # Store window metadata in the snapshot for coordinate resolution.
        try:
            snap_obj = mgr.get_snapshot(snapshot_id)
            snap_obj.window_bounds = (tree.x, tree.y, tree.width, tree.height)
            snap_obj.application_name = window_title
            snap_obj.window_title = window_title
            mgr._write_json_atomic(
                mgr._snap_dir(snapshot_id) / "snapshot.json",
                snap_obj.to_dict(),
            )
        except Exception as exc:
            logger.debug("Snapshot metadata write failed: %s", exc)

        # Build display ref map: sequential e1,e2,… → stable hash-based refs.
        # The serialized tree uses stable refs; this mapping lets click resolve
        # both sequential and stable refs.
        display_ref_map: dict[str, str] = {}
        _counter = [1]

        # (M3) Cascade nodes carry a ``source``; annotate derives techniques[] +
        # correctness + confidence. Non-cascade nodes have no source, so annotate
        # returns None and no fusion fields are added (behavior unchanged).
        from naturo.cascade import annotate as _annotate_correctness

        def _serialize(el) -> dict:
            stable_ref = element_obj_to_ref.get(id(el), el.id)
            display_ref = f"e{_counter[0]}"
            _counter[0] += 1
            display_ref_map[display_ref] = stable_ref
            d = {
                "id": stable_ref,
                "role": el.role,
                "name": el.name,
                "value": el.value,
                "bounds": {"x": el.x, "y": el.y, "width": el.width, "height": el.height},
                "properties": el.properties,
            }
            _fusion = _annotate_correctness(el.properties or {})
            if _fusion is not None:
                d["techniques"] = _fusion["techniques"]
                d["correctness"] = _fusion["correctness"]
                d["confidence"] = _fusion["confidence"]
            if el.children:
                d["children"] = [_serialize(c) for c in el.children]
            return d

        result = {"success": True, "tree": _serialize(tree), "snapshot_id": snapshot_id}

        # (M3) Expose the structured recognition summary alongside the fused tree
        # so an agent can branch on correctness without walking every node.
        if cascade_result is not None:
            from naturo.cascade import recognition_summary
            _summary = recognition_summary(tree)
            if _summary["total_nodes"] > 0:
                result["recognition_summary"] = _summary

        # Store display ref mapping so sequential refs from tree output
        # can be translated to stable refs during click resolution.
        if display_ref_map:
            mgr.store_display_ref_map(snapshot_id, display_ref_map)

        return result

    @server.tool()
    @_safe_tool
    def find_element(
        selector: str,
        window_title: Optional[str] = None,
    ) -> dict:
        """Find a UI element by selector.

        Selector format: "Role:Name" (e.g. "Button:Save", "Edit:*search*").
        Supports fuzzy matching with wildcards.

        Args:
            selector: Element selector string.
            window_title: Target window (partial match).

        Returns:
            Dict with the found element's info or error.
        """
        backend = _get_backend()
        element = backend.find_element(selector=selector, window_title=window_title)
        if element is None:
            return {"success": False, "error": {"code": "ELEMENT_NOT_FOUND", "message": f"No element matching '{selector}'"}}
        return {
            "success": True,
            "element": {
                "id": element.id,
                "role": element.role,
                "name": element.name,
                "value": element.value,
                "bounds": {"x": element.x, "y": element.y, "width": element.width, "height": element.height},
                "properties": element.properties,
            },
        }

    @server.tool()
    @_safe_tool
    def get_element_value(
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Read the current value/text of a UI element.

        Queries UIA patterns (ValuePattern, TogglePattern, SelectionPattern,
        RangeValuePattern, TextPattern) to retrieve the element's current
        value. Use after ``see_elements`` to get element refs.

        Args:
            ref: Element ref from snapshot (e.g. ``"e47"``).
            automation_id: UIA AutomationId string.
            role: Element role filter (e.g. ``"Edit"``).
            name: Element name filter.
            window_title: Target window title (partial match).
            hwnd: Target window handle.

        Returns:
            Dict with value, pattern, role, name, automation_id, and bounds.
        """
        backend = _get_backend()
        result = backend.get_element_value(
            ref=ref,
            automation_id=automation_id,
            role=role,
            name=name,
            window_title=window_title,
            hwnd=hwnd,
        )
        if result is None:
            return {
                "success": False,
                "error": {
                    "code": "ELEMENT_NOT_FOUND",
                    "message": "Element not found for value reading",
                },
            }
        return {
            "success": True,
            "ref": ref,
            "value": result.get("value"),
            "pattern": result.get("pattern"),
            "role": result.get("role"),
            "name": result.get("name"),
            "automation_id": result.get("automation_id"),
            "bounds": {
                "x": result.get("x"),
                "y": result.get("y"),
                "width": result.get("width"),
                "height": result.get("height"),
            },
        }

    @server.tool()
    @_safe_tool
    def set_element_value(
        value: str,
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Set the value/text of a UI element via UIA ValuePattern.

        Directly writes to the element's value through accessibility
        interfaces, bypassing SendInput. Works in schtasks / remote
        session contexts.

        Args:
            value: Text value to set on the element.
            ref: Element ref from snapshot (e.g. ``"e47"``).
            automation_id: UIA AutomationId string.
            role: Element role filter (e.g. ``"Edit"``).
            name: Element name filter.
            window_title: Target window title (partial match).
            hwnd: Target window handle.

        Returns:
            Dict with success flag.
        """
        backend = _get_backend()

        # Resolve ref to identifiers
        resolved_aid = automation_id
        resolved_role = role
        resolved_name = name

        if ref and not resolved_aid:
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            result = mgr.resolve_ref_element(ref)
            if result:
                elem, _snap_id = result
                if elem.identifier:
                    resolved_aid = elem.identifier
                elif elem.role and (elem.title or elem.label):
                    resolved_role = resolved_role or elem.role
                    resolved_name = resolved_name or elem.title or elem.label

        # (#957) Resolve the window selector through the shared helper: an
        # unmatched window_title raises WindowNotFoundError (mapped to a
        # WINDOW_NOT_FOUND envelope) rather than silently targeting the
        # foreground window and reporting success on the wrong window.
        target_hwnd = require_hwnd(backend, window_title=window_title, hwnd=hwnd)

        success = backend.set_element_value(
            text=value,
            hwnd=target_hwnd,
            name=resolved_name,
            automation_id=resolved_aid,
            role=resolved_role,
        )
        if not success:
            return {
                "success": False,
                "error": {
                    "code": "SET_VALUE_FAILED",
                    "message": "Failed to set element value. The element may "
                    "not support ValuePattern or may be read-only.",
                },
            }
        return {"success": True, "action": "set_value", "value": value}

    @server.tool()
    @_safe_tool
    def toggle_element(
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Toggle a checkbox or toggle button via UIA TogglePattern.

        Args:
            ref: Element ref from snapshot (e.g. ``"e12"``).
            automation_id: UIA AutomationId string.
            role: Element role (e.g. ``"CheckBox"``).
            name: Element name.
            window_title: Target window title (partial match).
            hwnd: Target window handle.

        Returns:
            Dict with success flag and new toggle state.
        """
        backend = _get_backend()
        # (#957) Loud window resolution — see set_element_value for rationale.
        target_hwnd = require_hwnd(backend, window_title=window_title, hwnd=hwnd)

        new_state = backend.toggle_element(
            hwnd=target_hwnd,
            automation_id=automation_id,
            role=role,
            name=name,
        )
        if new_state is None:
            return {
                "success": False,
                "error": {
                    "code": "TOGGLE_FAILED",
                    "message": "Failed to toggle element. It may not support "
                    "TogglePattern.",
                },
            }
        return {"success": True, "action": "toggle", "new_state": new_state}

    @server.tool()
    @_safe_tool
    def select_element(
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Select a list item, radio button, or tab via SelectionItemPattern.

        Args:
            ref: Element ref from snapshot (e.g. ``"e8"``).
            automation_id: UIA AutomationId string.
            role: Element role (e.g. ``"ListItem"``, ``"RadioButton"``).
            name: Element name.
            window_title: Target window title (partial match).
            hwnd: Target window handle.

        Returns:
            Dict with success flag.
        """
        backend = _get_backend()
        # (#957) Loud window resolution — see set_element_value for rationale.
        target_hwnd = require_hwnd(backend, window_title=window_title, hwnd=hwnd)

        success = backend.select_element(
            hwnd=target_hwnd,
            automation_id=automation_id,
            role=role,
            name=name,
        )
        if not success:
            return {
                "success": False,
                "error": {
                    "code": "SELECT_FAILED",
                    "message": "Failed to select element. It may not support "
                    "SelectionItemPattern.",
                },
            }
        return {"success": True, "action": "select"}

    @server.tool()
    @_safe_tool
    def expand_collapse_element(
        expand: bool = True,
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Expand or collapse a combo box or tree item via ExpandCollapsePattern.

        Args:
            expand: True to expand, False to collapse.
            ref: Element ref from snapshot (e.g. ``"e5"``).
            automation_id: UIA AutomationId string.
            role: Element role (e.g. ``"ComboBox"``, ``"TreeItem"``).
            name: Element name.
            window_title: Target window title (partial match).
            hwnd: Target window handle.

        Returns:
            Dict with success flag and action performed.
        """
        backend = _get_backend()
        # (#957) Loud window resolution — see set_element_value for rationale.
        target_hwnd = require_hwnd(backend, window_title=window_title, hwnd=hwnd)

        success = backend.expand_collapse_element(
            hwnd=target_hwnd,
            automation_id=automation_id,
            role=role,
            name=name,
            expand=expand,
        )
        action = "expand" if expand else "collapse"
        if not success:
            return {
                "success": False,
                "error": {
                    "code": f"{action.upper()}_FAILED",
                    "message": f"Failed to {action} element. It may not "
                    f"support ExpandCollapsePattern.",
                },
            }
        return {"success": True, "action": action}
