"""MCP tools for UI inspection and element manipulation."""
from __future__ import annotations

import logging
from typing import Optional

from naturo.mcp._resolve import require_hwnd
from naturo.value_preview import bounded_value

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
        format: str = "compact",
        match: Optional[str] = None,
        full_text: bool = False,
    ) -> dict:
        """Read a window's UI as a structured element tree — naturo's core "see" tool.

        format="compact" (default) returns ``tree_text``: one indented line per
        actionable/named element as ``eN <role> "<name>" [=value]`` — ~10x fewer
        tokens than the JSON tree (no bounds/nulls/raw properties), and directly
        readable by the LLM. Click/type by the same ``eN`` ref. Use format="json"
        only when you need bounds, raw properties, or the nested structure.

        match="<intent text>" returns ONLY the elements whose role or name matches
        (case-insensitive substring, or all words present) — e.g. match="save"
        yields just the Save controls with their eN refs. Use it when you already
        know what you're looking for: fewer tokens, fewer turns (target directly
        instead of reading + scanning the whole tree). (compact format only.)

        Text elements (Document/Edit/Text) include their content as ``=<value>``.
        Long values are truncated to a preview with a ``…(+N chars)`` marker to
        stay token-lean — read the whole thing with ``get eN`` (returns the full
        document). full_text=true inlines every value in full instead, for a
        one-shot "dump all visible text and search it" read.

        Returns the hierarchy of UI elements (buttons, text fields, etc.) with
        their roles, names, bounds, and properties; element IDs (eN) feed into
        ``click``, ``type_text``, and other calls. With ``cascade=true`` it fuses
        ONE tree across desktop UIA plus web (CDP), Java/Swing (JAB) and Excel
        cells (COM) — rendered, behind-login, Java, or spreadsheet content that
        plain accessibility (or a web fetch) cannot reach — each node tagged
        deterministic vs uncertain.

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
            tree = None
            # (calc-zombie) --app can resolve to several UWP windows (empty ghost
            # frames + the live CoreWindow). Gather all of them, cascade each, and
            # keep only content-bearing ones so we never return a chrome-only ghost.
            # Shared with the `see` CLI.
            if app and hwnd is None and not window_title and pid is None:
                from naturo.cascade._appwindows import app_content_tree
                tree, _ = app_content_tree(
                    backend, app, depth=depth, backend_name="auto",
                )
            if tree is None:
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
                return {"success": False, "error": {"code": "WINDOW_NOT_FOUND", "message": f"No windows found for app '{app}'"}}

            from naturo.backends.base import ElementInfo as BaseElementInfo
            window_trees = []
            for h in hwnds:
                subtree = backend.get_element_tree(
                    hwnd=h, depth=depth, backend=accessibility_backend,
                )
                if subtree:
                    window_trees.append((h, subtree))

            if not window_trees:
                return {"success": False, "error": {"code": "WINDOW_NOT_FOUND", "message": "All windows have empty UI trees"}}

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
            # Auto-JAB fallback: UIA renders Java/Swing (and some other toolkits)
            # as an opaque frame, so a default read sees ~nothing and the agent
            # falls back to a screenshot — losing the whole point of structured
            # reading (and naturo's Java moat). When the default UIA tree is that
            # sparse, transparently re-read via the Java Access Bridge and adopt
            # it if it recovers substantially more content.
            if accessibility_backend == "uia" and tree is not None:
                def _n(el) -> int:
                    return 1 + sum(_n(c) for c in (getattr(el, "children", None) or []))
                if _n(tree) < 12:
                    try:
                        _jab = backend.get_element_tree(
                            app=app, window_title=window_title, hwnd=hwnd,
                            pid=pid, depth=depth, backend="jab",
                        )
                        if _jab is not None and _n(_jab) > _n(tree):
                            tree = _jab
                    except Exception as _exc:
                        logger.debug("auto-JAB fallback skipped: %s", _exc)
        if tree is None:
            return {"success": False, "error": {"code": "WINDOW_NOT_FOUND", "message": "No matching window found"}}

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

        _ACTIONABLE = {
            "button", "hyperlink", "link", "edit", "text", "checkbox",
            "radiobutton", "combobox", "menuitem", "listitem", "tab", "tabitem",
            "treeitem", "slider", "spinner", "document", "datagrid", "dataitem",
        }

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

        # Compact rendering: assign the SAME eN refs in the SAME DFS order (so
        # click/type still resolve), but emit one text line per actionable/named
        # node — dropping bounds, null fields and raw properties the LLM doesn't
        # need to choose its next action. ~10x fewer tokens than the JSON tree.
        _compact_lines: list[str] = []
        _q = (match or "").strip().lower()
        _q_tokens = _q.split()

        def _match_node(name: str, role: str) -> bool:
            if not _q:
                return True
            hay = f"{name} {role}".lower()
            return _q in hay or all(t in hay for t in _q_tokens)

        def _walk_compact(el, depth: int) -> None:
            display_ref = f"e{_counter[0]}"
            _counter[0] += 1
            display_ref_map[display_ref] = element_obj_to_ref.get(id(el), el.id)
            role = el.role or ""
            name = (el.name or "").strip()
            value = el.value
            if (name or role.lower() in _ACTIONABLE or value) and _match_node(name, role):
                # flat list when filtering to an intent; indented tree otherwise
                indent = "" if _q else "  " * min(depth, 8)
                line = f"{indent}{display_ref} {role}"
                if name:
                    line += f' "{name}"'
                if value:
                    _shown, _elided = bounded_value(value, full=full_text)
                    line += f" ={_shown!r}"
                    if _elided:
                        line += f" …(+{_elided} chars)"
                _fusion = _annotate_correctness(el.properties or {})
                if _fusion is not None and _fusion.get("correctness") != "deterministic":
                    line += " ~"  # uncertain (vision/image) — verify before trusting
                _compact_lines.append(line)
            for c in (el.children or []):
                _walk_compact(c, depth + 1)

        if format == "json":
            result = {"success": True, "tree": _serialize(tree), "snapshot_id": snapshot_id}
        else:
            _walk_compact(tree, 0)
            result = {
                "success": True,
                "tree_text": "\n".join(_compact_lines),
                "element_count": _counter[0] - 1,
                "snapshot_id": snapshot_id,
                "format": "compact",
            }
            if _q:
                result["match"] = match
                result["matched"] = len(_compact_lines)

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
    def read_web_text(
        hwnd: Optional[int] = None,
        window_title: Optional[str] = None,
        selector: Optional[str] = None,
        max_chars: int = 20000,
    ) -> dict:
        """Read rendered text from a browser page via CDP — the static text that
        see_ui_tree / find_element miss.

        see_ui_tree(cascade) surfaces *interactive* elements (buttons, inputs,
        links); the visible text of a result — a translation output, an article
        body, a price, a status line — usually lives in a plain element the
        interactive tree skips, which otherwise forces a screenshot. This returns
        that text straight from the rendered DOM (``innerText``), so it reads
        JS-rendered or logged-in content a web fetch cannot. Point it at a
        browser opened with ``launch_browser``. A dynamic result may need a
        moment to appear — read again if the first call comes back empty.

        Args:
            hwnd: Browser window handle (from ``launch_browser``/``list_windows``).
            window_title: Browser window title (partial) if ``hwnd`` is unknown.
            selector: CSS selector to read one element's text; omit to read the
                whole page's visible text.
            max_chars: Truncate the returned text to this many characters.

        Returns:
            Dict with ``text``, ``selector``, ``char_count``, ``truncated``.
        """
        import json as _json

        backend = _get_backend()
        if hwnd is None and window_title is not None and hasattr(backend, "_resolve_hwnd"):
            hwnd = backend._resolve_hwnd(window_title=window_title)
        if hwnd is None:
            return {"success": False, "error": {
                "code": "INVALID_INPUT",
                "message": "Provide hwnd or window_title of the browser window.",
            }}

        # Prefer the exact port launch_browser recorded for this window — a blind
        # CDP probe returns the wrong browser when several debuggable ones are
        # alive (cross-talk). Fall back to PID-based discovery for windows we did
        # not open ourselves.
        from naturo.browser._registry import lookup as _lookup_port
        port = _lookup_port(hwnd)
        if not port:
            pid = None
            try:
                import ctypes
                import ctypes.wintypes
                _pid = ctypes.wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(_pid))
                pid = _pid.value or None
            except Exception:
                pid = None

            from naturo.cascade import find_cdp_port
            port = find_cdp_port(pid)
        if not port:
            return {"success": False, "error": {
                "code": "CDP_NOT_AVAILABLE",
                "message": "No DevTools endpoint for this window.",
                "suggested_action": "Open the page with launch_browser (it enables CDP), then read it with the returned hwnd.",
                "recoverable": True,
            }}

        if selector:
            expr = (
                "(function(){var el=document.querySelector(" + _json.dumps(selector)
                + ");return el?el.innerText:'';})()"
            )
        else:
            expr = "document.body?document.body.innerText:''"

        from naturo.cdp import CDPClient
        client = CDPClient(port=port)
        try:
            client.connect()
            text = client.evaluate(expr)
        finally:
            try:
                client.close()
            except Exception:
                pass

        text = text if isinstance(text, str) else ("" if text is None else str(text))
        full_len = len(text)
        return {
            "success": True,
            "text": text[:max_chars],
            "selector": selector,
            "char_count": full_len,
            "truncated": full_len > max_chars,
        }

    @server.tool()
    @_safe_tool
    def find_element(
        selector: str,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Find a UI element by selector.

        Selector format: "Role:Name" (e.g. "Button:Save", "Edit:*search*").
        Supports fuzzy matching with wildcards.

        Args:
            selector: Element selector string.
            window_title: Target window (partial match).
            hwnd: Direct window handle (from ``launch_app``/``list_windows``) —
                preferred; searches that exact window, no title matching.

        Returns:
            Dict with the found element's info or error.
        """
        backend = _get_backend()
        element = backend.find_element(selector=selector, window_title=window_title, hwnd=hwnd)
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
