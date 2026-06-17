"""The public element interface: find, snapshot the tree, and read values.

:class:`ElementTreeMixin` is the user-facing surface of the Windows element
backend — :meth:`find_element`, :meth:`get_element_tree` (with the UWP child
fallback and multi-backend UIA/MSAA/IA2/JAB/Win32 cascade), and
:meth:`get_element_value`.  It composes the window resolution from
``_app_discovery`` and the UWP discovery helpers from ``_uia`` via the shared
``WindowsBackend`` instance.  Split out of the former monolithic ``_element``
module for maintainability (#720).
"""

from __future__ import annotations

import logging
from typing import Optional

from naturo.backends.base import ElementInfo as BaseElementInfo
from naturo.bridge import populate_hierarchy
from naturo.errors import NaturoError

logger = logging.getLogger(__name__)


class ElementTreeMixin:
    """Find elements, retrieve element trees, and read element values."""

    def find_element(self, selector: str = "", window_title: Optional[str] = None,
                     hwnd: Optional[int] = None) -> Optional[BaseElementInfo]:
        """Find a UI element by selector string.

        The selector format is "role:name" (e.g., "Button:OK") or just a name.

        Args:
            selector: Element selector in "role:name" or "name" format.
            window_title: Window title pattern (partial match, case-insensitive).
                When provided, the search is scoped to the matching window.
            hwnd: Target window handle.  When provided, searches within this
                window instead of the foreground window (#525) and takes
                priority over ``window_title``.

        Returns:
            ElementInfo if found, None otherwise.

        Raises:
            WindowNotFoundError: When ``window_title`` is supplied but matches no
                window. The selector is resolved up front through
                ``_resolve_hwnd`` and the error is allowed to propagate rather
                than degrading to the foreground window — the silent-fallback
                bug #963 (sibling of #957/#964 and the same path used by
                ``get_element_value``).
        """
        core = self._ensure_core()

        # Parse selector into role and name
        role = None
        name = None
        if ":" in selector:
            parts = selector.split(":", 1)
            role = parts[0] if parts[0] else None
            name = parts[1] if parts[1] else None
        else:
            name = selector if selector else None

        # Resolve the window selector before searching. A window_title that is
        # supplied but matches nothing must fail loudly: ``_resolve_hwnd`` raises
        # WindowNotFoundError and we let it propagate instead of silently
        # searching the foreground window (HWND 0). With no selector the
        # documented foreground default is preserved.
        target_hwnd = hwnd or 0
        if window_title and not target_hwnd:
            target_hwnd = self._resolve_hwnd(window_title=window_title)

        result = core.find_element(hwnd=target_hwnd, role=role, name=name)
        if result is None:
            return None

        return BaseElementInfo(
            id=result.id,
            role=result.role,
            name=result.name,
            value=result.value,
            x=result.x,
            y=result.y,
            width=result.width,
            height=result.height,
            children=[],
            properties={},
        )
    @staticmethod
    def _is_shallow_tree(element) -> bool:
        """Check if an element tree is too shallow (VB6/ActiveX fallback signal).

        VB6/ActiveX apps often expose a tree with only a few Pane containers
        at depth 1-2, hiding all actual form controls (Static/Edit/Button).
        This heuristic detects that pattern to trigger Win32 HWND enumeration.

        Args:
            element: Root ElementInfo from get_element_tree.

        Returns:
            True if the tree is too shallow (trigger fallback).
        """
        if not element or not element.children:
            return True

        # Count actionable elements (non-Pane roles at any depth)
        actionable_count = 0
        pane_count = 0

        def count_actionable(el):
            nonlocal actionable_count, pane_count
            role = (el.role or "").lower()
            if role == "pane":
                pane_count += 1
            elif role in ("button", "edit", "text", "combobox", "checkbox", "radiobutton"):
                actionable_count += 1
            for child in el.children:
                count_actionable(child)

        count_actionable(element)

        # Shallow tree heuristic: <5 actionable elements or >80% panes
        if actionable_count < 5:
            return True
        if pane_count > 0 and actionable_count / (actionable_count + pane_count) < 0.2:
            return True

        return False
    def get_element_tree(self, window_title: Optional[str] = None,
                         depth: int = 3,
                         app: Optional[str] = None,
                         hwnd: Optional[int] = None,
                         pid: Optional[int] = None,
                         backend: str = "uia") -> Optional[BaseElementInfo]:
        """Get the UI element tree for a window.

        Fills parent_id, children IDs, and keyboard_shortcut for all elements
        via Python-layer post-processing (the C++ DLL does not emit these).

        For UWP/WinUI apps (Calculator, Settings, etc.) the UI tree lives
        inside child windows of the ``ApplicationFrameHost`` top-level window.
        Classic UWP uses ``Windows.UI.Core.CoreWindow``; WinUI 3 apps use
        other classes like ``DesktopWindowXamlSource``.  When the initial
        traversal returns an empty tree from an AFH window, this method
        enumerates all child windows and retries with each until a non-empty
        tree is found.

        Args:
            window_title: Window title pattern (partial match, case-insensitive).
            depth: Maximum depth to traverse (1-10).
            app: Application name to search for (partial match, case-insensitive).
            hwnd: Direct window handle. Overrides app/window_title.
            pid: Process ID.  Filters windows to only those owned by this
                process (#471).
            backend: Accessibility backend — "auto" (default), "uia", "msaa",
                     "win32", "win32hybrid", "ia2", or "jab".
                     "auto" tries UIA first, falls back to hybrid Win32+UIA
                     if UIA returns shallow trees, then IA2/JAB/MSAA.
                     "win32" uses pure Win32 HWND enumeration.
                     "win32hybrid" uses Win32 HWND tree with UIA drill-down
                     for complex controls like grids, list views, and tree
                     views (#312).

        Returns:
            Root ElementInfo with nested children, or None.
        """
        core = self._ensure_core()
        handle = self._resolve_hwnd(app=app, window_title=window_title, hwnd=hwnd, pid=pid)

        def _try_uwp_children(current_result, get_tree_fn):
            """If handle is an AFH window with empty tree, try child windows.

            Enumerates all child HWNDs of the ApplicationFrameHost window
            and returns the first one that yields a non-empty element tree.

            Args:
                current_result: The element tree from the AFH window itself.
                get_tree_fn: Callable(hwnd, depth) -> element tree result.

            Returns:
                A non-empty element tree from a child HWND, or current_result
                if no child yields a better result.
            """
            if (current_result is not None
                    and not current_result.children
                    and handle
                    and self._is_afh_window(handle)):
                child_hwnds = self._find_uwp_content_hwnd(handle)
                for child_hwnd in child_hwnds:
                    logger.debug(
                        "UWP fallback: trying child HWND %s "
                        "(parent AFH %s)", child_hwnd, handle,
                    )
                    child_result = get_tree_fn(child_hwnd, depth)
                    if child_result is not None and child_result.children:
                        logger.info(
                            "UWP fallback: found %d children via child "
                            "HWND %s", len(child_result.children), child_hwnd,
                        )
                        return child_result

                # (#394) WinUI 3 apps may need deeper traversal.
                # Retry child HWNDs with increased depth if original
                # depth was low and yielded nothing.
                if depth < 15:
                    deeper = min(depth * 2, 20)
                    logger.debug(
                        "UWP fallback: retrying children with depth=%d "
                        "(was %d)", deeper, depth,
                    )
                    for child_hwnd in child_hwnds:
                        child_result = get_tree_fn(child_hwnd, deeper)
                        if child_result is not None and child_result.children:
                            logger.info(
                                "UWP fallback (depth=%d): found %d children "
                                "via child HWND %s",
                                deeper, len(child_result.children), child_hwnd,
                            )
                            return child_result
            return current_result

        if backend == "jab":
            result = core.jab_get_element_tree(hwnd=handle, depth=depth)
            result = _try_uwp_children(
                result,
                lambda h, d: core.jab_get_element_tree(hwnd=h, depth=d),
            )
        elif backend == "ia2":
            result = core.ia2_get_element_tree(hwnd=handle, depth=depth)
            result = _try_uwp_children(
                result,
                lambda h, d: core.ia2_get_element_tree(hwnd=h, depth=d),
            )
        elif backend == "msaa":
            result = core.msaa_get_element_tree(hwnd=handle, depth=depth)
            result = _try_uwp_children(
                result,
                lambda h, d: core.msaa_get_element_tree(hwnd=h, depth=d),
            )
        elif backend == "win32":
            # Pure Win32 HWND enumeration (VB6/ActiveX fallback)
            from naturo.bridge import enumerate_child_windows
            result = enumerate_child_windows(hwnd=handle, depth=depth)
        elif backend == "win32hybrid":
            # Win32 HWND tree + UIA drill-down for complex controls (#312)
            from naturo.bridge import enumerate_hybrid_tree
            result = enumerate_hybrid_tree(
                hwnd=handle, depth=depth, core=core,
            )
        elif backend == "auto":
            result = core.get_element_tree(hwnd=handle, depth=depth)
            # UWP/WinUI fallback: try child windows of AFH
            result = _try_uwp_children(
                result,
                lambda h, d: core.get_element_tree(hwnd=h, depth=d),
            )
            
            # Win32+UIA hybrid fallback for VB6/ActiveX apps (#308, #312)
            # When UIA returns shallow trees (only Pane containers),
            # use hybrid enumeration: Win32 HWND tree as base with UIA
            # drill-down for complex controls (grids, list views, tree views).
            if result is not None and self._is_shallow_tree(result):
                logger.info(
                    "UIA returned shallow tree (%d children), "
                    "trying Win32+UIA hybrid enumeration (VB6/ActiveX)",
                    len(result.children)
                )
                from naturo.bridge import enumerate_hybrid_tree
                hybrid_result = enumerate_hybrid_tree(
                    hwnd=handle, depth=depth, core=core,
                )
                if hybrid_result is not None and len(hybrid_result.children) > len(result.children):
                    logger.info(
                        "Hybrid fallback found %d children (vs %d from UIA), using it",
                        len(hybrid_result.children), len(result.children)
                    )
                    result = hybrid_result
            
            if result is None or (not result.children and not result.name):
                # Try IA2 first (Firefox/Thunderbird/LibreOffice), then MSAA
                ia2_result = core.ia2_get_element_tree(hwnd=handle, depth=depth)
                if ia2_result is not None:
                    result = ia2_result
                else:
                    # Try JAB for Java applications
                    jab_result = core.jab_get_element_tree(hwnd=handle, depth=depth)
                    if jab_result is not None:
                        result = jab_result
                    else:
                        msaa_result = core.msaa_get_element_tree(hwnd=handle, depth=depth)
                        if msaa_result is not None:
                            result = msaa_result
                        else:
                            # Final fallback: hybrid Win32+UIA enumeration
                            from naturo.bridge import enumerate_hybrid_tree
                            hybrid_result = enumerate_hybrid_tree(
                                hwnd=handle, depth=depth, core=core,
                            )
                            if hybrid_result is not None:
                                logger.info("Auto mode: all backends failed, using Win32+UIA hybrid fallback")
                                result = hybrid_result
        else:
            result = core.get_element_tree(hwnd=handle, depth=depth)
            # UWP/WinUI fallback for explicit "uia" backend too
            result = _try_uwp_children(
                result,
                lambda h, d: core.get_element_tree(hwnd=h, depth=d),
            )

        if result is None:
            return None

        # (#613) Fix coordinate mismatch on UWP/high-DPI: UIA may return
        # large negative coords for UWP apps when DPI contexts conflict.
        if handle:
            result = self._fixup_element_coords(result, handle)

        # Post-process: assign sequential IDs and fill parent_id
        populate_hierarchy(result)

        # (#372) Roles that should include a text value preview
        _PREVIEW_ROLES = {"Document", "Edit", "Text"}

        def convert(el) -> BaseElementInfo:
            """Convert bridge ElementInfo to backend ElementInfo."""
            props = {
                k: v for k, v in {
                    "parent_id": el.parent_id,
                    "keyboard_shortcut": el.keyboard_shortcut,
                }.items() if v is not None
            }

            # (#372) Add value preview for Document/Edit/Text elements
            if el.role in _PREVIEW_ROLES and el.value:
                full_text = el.value
                preview = full_text[:100]
                if len(full_text) > 100:
                    preview += "…"
                props["value_preview"] = preview
                props["value_length"] = len(full_text)

            return BaseElementInfo(
                id=el.id,
                role=el.role,
                name=el.name,
                value=el.value,
                x=el.x,
                y=el.y,
                width=el.width,
                height=el.height,
                children=[convert(c) for c in el.children],
                properties=props,
            )

        return convert(result)
    def get_element_value(
        self,
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        app: Optional[str] = None,
        window_title: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> Optional[dict]:
        """Read the current value/text of a UI element via UIA patterns.

        Supports element refs (e47), AutomationId, or role+name lookup.
        Queries ValuePattern, TogglePattern, SelectionPattern,
        RangeValuePattern, and TextPattern.

        Args:
            ref: Element ref from snapshot (e.g. ``"e47"``).
            automation_id: UIA AutomationId string.
            role: Element role (e.g. ``"Edit"``).
            name: Element name.
            app: Application name (partial match) for window targeting.
            window_title: Window title for targeting.
            hwnd: Window handle.

        Returns:
            Dict with ``value``, ``pattern``, ``role``, ``name``,
            ``automation_id``, and bounding rect; or ``None`` if not found.

        Raises:
            NaturoError: If the element cannot be found or queried.
        """
        core = self._ensure_core()

        # Resolve ref to element metadata via snapshot cache
        resolved_aid = automation_id
        resolved_role = role
        resolved_name = name
        target_hwnd = hwnd or 0

        if ref and not resolved_aid:
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            result = mgr.resolve_ref_element(ref)
            if result:
                elem, _snap_id = result
                # Use the element's identifier (AutomationId) if available
                if elem.identifier:
                    resolved_aid = elem.identifier
                elif elem.role and elem.title:
                    resolved_role = elem.role
                    resolved_name = elem.title
                elif elem.role and elem.label:
                    resolved_role = elem.role
                    resolved_name = elem.label
                else:
                    raise NaturoError(
                        f"Element {ref} has no AutomationId, role, or name "
                        f"for value lookup"
                    )
            else:
                raise NaturoError(
                    f"Element ref '{ref}' not found in snapshot cache. "
                    f"Run 'naturo see' first to capture elements."
                )

        # Resolve app/window_title to HWND for targeted lookup. A selector that
        # is supplied but matches nothing must fail loudly: ``_resolve_hwnd``
        # raises WindowNotFoundError and we let it propagate, rather than
        # swallowing it and degrading to the foreground window (HWND 0). The old
        # ``except`` + manual title scan only ever reproduced ``_resolve_hwnd``'s
        # own substring matching, so a raise meant no window matched anywhere —
        # falling back to the focused window was the silent-failure bug #964
        # (the CLI analog of the MCP #957 ``require_hwnd`` contract).
        if (app or window_title) and not target_hwnd:
            target_hwnd = self._resolve_hwnd(app=app, window_title=window_title)

        if not resolved_aid and not resolved_role and not resolved_name:
            # (#242) Fallback: when no element identifiers are provided but
            # we have a target HWND (e.g., from --app notepad), auto-probe
            # common editable element roles in the window. This enables
            # verification for the common `type --app X --verify` pattern.
            if target_hwnd:
                _editable_roles = ("Edit", "Document", "RichEdit20W")
                for _probe_role in _editable_roles:
                    _probe_result = core.get_element_value(
                        hwnd=target_hwnd,
                        automation_id=None,
                        role=_probe_role,
                        name=None,
                    )
                    if _probe_result is not None:
                        _probe_result["probe_role"] = _probe_role
                        return _probe_result
                # All probes failed — still no identifiers available
                raise NaturoError(
                    "No editable element found in target window. "
                    "Tried probing roles: Edit, Document, RichEdit20W. "
                    "Use --on eN to specify the target element explicitly."
                )
            raise NaturoError(
                "Must specify ref, automation_id, or role/name to get value"
            )

        result = core.get_element_value(
            hwnd=target_hwnd,
            automation_id=resolved_aid,
            role=resolved_role,
            name=resolved_name,
        )

        # (#352) Role alias fallback: when an explicit role search fails,
        # try common aliases.  Win11 Notepad uses "Document" for its text
        # editor, but users naturally try "Edit".  This maps between roles
        # that serve similar purposes in different app frameworks.
        if result is None and resolved_role and not resolved_aid:
            _ROLE_ALIASES: dict[str, list[str]] = {
                "Edit": ["Document", "RichEdit20W"],
                "Document": ["Edit", "RichEdit20W"],
                "RichEdit20W": ["Edit", "Document"],
                "Text": ["StaticText"],
                "StaticText": ["Text"],
            }
            aliases = _ROLE_ALIASES.get(resolved_role, [])
            for alias_role in aliases:
                result = core.get_element_value(
                    hwnd=target_hwnd,
                    automation_id=resolved_aid,
                    role=alias_role,
                    name=resolved_name,
                )
                if result is not None:
                    break

        # (#521) NameProperty fallback: if the C++ core found the element but
        # no UIA pattern returned a value, use the element's Name property.
        # This handles Text/Static elements (e.g. Calculator display) where
        # the value is embedded in the UIA Name (e.g. "显示为 579").
        if isinstance(result, dict) and result.get("value") is None:
            elem_name = result.get("name")
            if elem_name:
                result["value"] = elem_name
                result["pattern"] = "NameProperty"

        # (#229) Fallback: if UIA lookup returned None but we have snapshot
        # data from the ref, return the snapshot metadata so the caller gets
        # at least role/name/bounds instead of ELEMENT_NOT_FOUND.
        if result is None and ref:
            from naturo.snapshot import get_snapshot_manager as _gsm
            _mgr = _gsm()
            _el_result = _mgr.resolve_ref_element(ref)
            if _el_result:
                _elem, _snap = _el_result
                ex, ey, ew, eh = _elem.frame
                result = {
                    "role": _elem.role,
                    "name": _elem.title or _elem.label,
                    "value": _elem.value,
                    "pattern": None,
                    "automation_id": _elem.identifier,
                    "x": ex,
                    "y": ey,
                    "width": ew,
                    "height": eh,
                    "source": "snapshot",
                }

        return result
