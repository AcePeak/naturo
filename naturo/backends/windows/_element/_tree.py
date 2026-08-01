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
from dataclasses import dataclass
from typing import Optional

from naturo.backends.base import ElementInfo as BaseElementInfo
from naturo.backends.windows._core import heal_core_on_failure
from naturo.bridge import populate_hierarchy
from naturo.errors import NaturoError, StaleSnapshotCacheError

logger = logging.getLogger(__name__)


# Roles whose text value is worth previewing inline in the tree (#372).
_PREVIEW_ROLES = frozenset({"Document", "Edit", "Text"})


# ── get_element_tree building blocks ─────────────────────────────────────────
# Extracted from the former 250-line get_element_tree so the per-backend dispatch,
# the UWP child-window fallback, and the bridge→backend conversion are each named
# and independently readable. Module-level (not methods), taking the backend
# explicitly, so MagicMock(spec=Backend) doubles that bind only get_element_tree
# are unaffected — the same reason _resolve_hwnd's helpers are module-level.


def _convert_bridge_element(el) -> BaseElementInfo:
    """Convert a bridge ElementInfo (and its children, recursively) to a backend
    ElementInfo.

    Carries parent_id/keyboard_shortcut and — via getattr, so backends that don't
    emit them (image/OCR/UWP fallback, fixtures) simply omit them — the #1200
    accessibility states and the true per-node capability flags
    (readable/actionable/editable). Adds a truncated value preview for
    Document/Edit/Text nodes (#372).
    """
    from naturo.value_preview import PREVIEW_LEN as _PREVIEW_LEN
    props = {
        k: v for k, v in {
            "parent_id": el.parent_id,
            "keyboard_shortcut": el.keyboard_shortcut,
            "states": getattr(el, "states", None),
            "readable": getattr(el, "readable", None),
            "actionable": getattr(el, "actionable", None),
            "editable": getattr(el, "editable", None),
        }.items() if v is not None
    }
    if el.role in _PREVIEW_ROLES and el.value:
        full_text = el.value
        preview = full_text[:_PREVIEW_LEN]
        if len(full_text) > _PREVIEW_LEN:
            preview += "…"
        props["value_preview"] = preview
        props["value_length"] = len(full_text)
    return BaseElementInfo(
        id=el.id, role=el.role, name=el.name, value=el.value,
        x=el.x, y=el.y, width=el.width, height=el.height,
        children=[_convert_bridge_element(c) for c in el.children],
        properties=props,
    )


def _try_uwp_children(backend_self, handle, depth, current_result, get_tree_fn):
    """If *handle* is an AFH window with an empty tree, retry via its child HWNDs.

    Classic UWP buries content in a ``Windows.UI.Core.CoreWindow`` child of the
    ApplicationFrameHost window; WinUI 3 uses other child classes. Enumerate the
    AFH children and return the first non-empty tree, retrying deeper for WinUI
    (#394). Returns *current_result* unchanged when not applicable.
    """
    if not (current_result is not None and not current_result.children
            and handle and backend_self._is_afh_window(handle)):
        return current_result
    child_hwnds = backend_self._find_uwp_content_hwnd(handle)
    for child_hwnd in child_hwnds:
        logger.debug("UWP fallback: trying child HWND %s (parent AFH %s)",
                     child_hwnd, handle)
        child_result = get_tree_fn(child_hwnd, depth)
        if child_result is not None and child_result.children:
            logger.info("UWP fallback: found %d children via child HWND %s",
                        len(child_result.children), child_hwnd)
            return child_result
    # (#394) WinUI 3 apps may need deeper traversal. depth <= 0 is already
    # unlimited (the first pass went as deep as possible), so only retry when an
    # explicit low depth yielded nothing.
    if 0 < depth < 15:
        deeper = min(depth * 2, 20)
        logger.debug("UWP fallback: retrying children with depth=%d (was %d)",
                     deeper, depth)
        for child_hwnd in child_hwnds:
            child_result = get_tree_fn(child_hwnd, deeper)
            if child_result is not None and child_result.children:
                logger.info("UWP fallback (depth=%d): found %d children via child HWND %s",
                            deeper, len(child_result.children), child_hwnd)
                return child_result
    return current_result


def _traverse_auto(backend_self, core, handle, depth):
    """The ``auto`` cascade: UIA → UWP child fallback → Win32 hybrid (when UIA is
    shallow, for VB6/ActiveX #308/#312) → IA2/JAB/MSAA/hybrid last resorts.
    Extracted verbatim from get_element_tree.
    """
    result = core.get_element_tree(hwnd=handle, depth=depth)
    result = _try_uwp_children(backend_self, handle, depth, result,
                               lambda h, d: core.get_element_tree(hwnd=h, depth=d))

    # Win32+UIA hybrid fallback: when UIA returns a shallow tree (only Pane
    # containers), Win32 HWND enumeration with UIA drill-down sees more.
    if result is not None and backend_self._is_shallow_tree(result):
        logger.info("UIA returned shallow tree (%d children), trying Win32+UIA "
                    "hybrid enumeration (VB6/ActiveX)", len(result.children))
        from naturo.bridge import enumerate_hybrid_tree
        hybrid_result = enumerate_hybrid_tree(hwnd=handle, depth=depth, core=core)
        if hybrid_result is not None and len(hybrid_result.children) > len(result.children):
            logger.info("Hybrid fallback found %d children (vs %d from UIA), using it",
                        len(hybrid_result.children), len(result.children))
            result = hybrid_result

    if result is None or (not result.children and not result.name):
        # Try IA2 (Firefox/Thunderbird/LibreOffice), then JAB, then MSAA, then hybrid.
        ia2_result = core.ia2_get_element_tree(hwnd=handle, depth=depth)
        if ia2_result is not None:
            return ia2_result
        jab_result = core.jab_get_element_tree(hwnd=handle, depth=depth)
        if jab_result is not None:
            return jab_result
        msaa_result = core.msaa_get_element_tree(hwnd=handle, depth=depth)
        if msaa_result is not None:
            return msaa_result
        from naturo.bridge import enumerate_hybrid_tree
        hybrid_result = enumerate_hybrid_tree(hwnd=handle, depth=depth, core=core)
        if hybrid_result is not None:
            logger.info("Auto mode: all backends failed, using Win32+UIA hybrid fallback")
            return hybrid_result
    return result


def _traverse_via_backend(backend_self, core, backend, handle, depth):
    """Run the requested accessibility backend (plus its UWP/hybrid fallbacks) and
    return the raw bridge tree. Extracted verbatim from get_element_tree's dispatch
    chain; ``auto`` delegates to :func:`_traverse_auto`.
    """
    if backend == "jab":
        # Depth is honored as-is (no per-backend offset); the unlimited default
        # (depth <= 0) is what reaches deeply-buried Swing content, not a magic +N.
        result = core.jab_get_element_tree(hwnd=handle, depth=depth)
        return _try_uwp_children(backend_self, handle, depth, result,
                                 lambda h, d: core.jab_get_element_tree(hwnd=h, depth=d))
    if backend == "ia2":
        result = core.ia2_get_element_tree(hwnd=handle, depth=depth)
        return _try_uwp_children(backend_self, handle, depth, result,
                                 lambda h, d: core.ia2_get_element_tree(hwnd=h, depth=d))
    if backend == "msaa":
        result = core.msaa_get_element_tree(hwnd=handle, depth=depth)
        return _try_uwp_children(backend_self, handle, depth, result,
                                 lambda h, d: core.msaa_get_element_tree(hwnd=h, depth=d))
    if backend == "win32":
        # Pure Win32 HWND enumeration (VB6/ActiveX fallback).
        from naturo.bridge import enumerate_child_windows
        return enumerate_child_windows(hwnd=handle, depth=depth)
    if backend == "win32hybrid":
        # Win32 HWND tree + UIA drill-down for complex controls (#312).
        from naturo.bridge import enumerate_hybrid_tree
        return enumerate_hybrid_tree(hwnd=handle, depth=depth, core=core)
    if backend == "auto":
        return _traverse_auto(backend_self, core, handle, depth)
    # Explicit "uia" (and any unrecognized value) → UIA + UWP child fallback.
    result = core.get_element_tree(hwnd=handle, depth=depth)
    return _try_uwp_children(backend_self, handle, depth, result,
                             lambda h, d: core.get_element_tree(hwnd=h, depth=d))


# ── get_element_value building blocks ────────────────────────────────────────
# Extracted from the former 242-line get_element_value so its ref-metadata
# resolution and the several documented value fallbacks are each named and
# testable. Module-level (backend/core passed explicitly) for the same reason as
# the get_element_tree helpers above.


@dataclass
class _RefMeta:
    """Metadata resolved from a snapshot ref (e47), threaded back into
    get_element_value. *early* carries a value dict to return immediately (a live
    Scintilla re-read); when set, the other fields are unused."""
    aid: Optional[str]
    role: Optional[str]
    name: Optional[str]
    coords: Optional[tuple]
    snap_hwnd: Optional[int]
    target_hwnd: int
    early: Optional[dict] = None


def _resolve_ref_metadata(backend, ref: str, aid: Optional[str], role: Optional[str],
                          name: Optional[str], target_hwnd: int) -> _RefMeta:
    """Resolve a snapshot *ref* to element metadata + its source window.

    Prefers the element's AutomationId, then role+title/label, then a cached
    centre point (#1208). Synthetic Scintilla nodes are re-read live and returned
    via :attr:`_RefMeta.early` (#Notepad++). Raises StaleSnapshotCacheError for an
    unknown ref, NaturoError when the element has no usable identifier/location.
    """
    from naturo.snapshot import get_snapshot_manager
    mgr = get_snapshot_manager()
    result = mgr.resolve_ref_element(ref)
    if not result:
        raise StaleSnapshotCacheError(ref)
    elem, _snap_id = result
    coords = None
    snap_hwnd = None

    # Scintilla nodes (Notepad++/SciTE) are synthetic — no live UIA element. A
    # normal lookup would return the value captured at ``see`` time (stale on the
    # next edit); re-read live from the Scintilla child HWND in the node id.
    _sci = backend._read_scintilla_ref_live(elem)
    if _sci is not None:
        return _RefMeta(aid, role, name, coords, snap_hwnd, target_hwnd, early=_sci)

    # Cache the element's own centre as a disambiguation hint (several role+name
    # peers can match; the point picks the exact one the snapshot meant).
    _hint_frame = getattr(elem, "frame", None)
    if _hint_frame and (_hint_frame[2] > 0 or _hint_frame[3] > 0):
        coords = (_hint_frame[0] + _hint_frame[2] // 2,
                  _hint_frame[1] + _hint_frame[3] // 2)

    if elem.identifier:
        aid = elem.identifier
    elif elem.role and elem.title:
        role, name = elem.role, elem.title
    elif elem.role and elem.label:
        role, name = elem.role, elem.label
    else:
        # (#1208) No identifier/name: keep the cached point + source window so the
        # value can be read live from the element's own window, instead of
        # refusing for an element naturo already found.
        frame = getattr(elem, "frame", None)
        if frame and (frame[2] > 0 or frame[3] > 0):
            coords = (frame[0] + frame[2] // 2, frame[1] + frame[3] // 2)
        try:
            snap_hwnd = getattr(mgr.get_snapshot(_snap_id), "window_handle", None)
        except Exception:
            snap_hwnd = None
        if coords is None:
            raise NaturoError(
                f"Element {ref} has no AutomationId, name, or location for value lookup")

    # Target the ref's OWN window: `get eN` must read from the window the snapshot
    # came from, not whatever is foreground now (#964).
    if not target_hwnd:
        try:
            _wh = getattr(mgr.get_snapshot(_snap_id), "window_handle", None)
            if _wh:
                target_hwnd = _wh
        except Exception:
            pass
    return _RefMeta(aid, role, name, coords, snap_hwnd, target_hwnd)


def _probe_editable_roles(core, target_hwnd: int) -> dict:
    """(#242) When no identifiers were given, probe common editable roles
    (Edit/Document/RichEdit20W) in the target window so ``type --app X --verify``
    can read back. Returns the first hit (with ``probe_role`` set); raises if none
    match."""
    for probe_role in ("Edit", "Document", "RichEdit20W"):
        r = core.get_element_value(
            hwnd=target_hwnd, automation_id=None, role=probe_role, name=None)
        if r is not None:
            r["probe_role"] = probe_role
            return r
    raise NaturoError(
        "No editable element found in target window. "
        "Tried probing roles: Edit, Document, RichEdit20W. "
        "Use --on eN to specify the target element explicitly.")


def _role_alias_retry(core, *, target_hwnd: int, resolved_aid: Optional[str],
                      resolved_role: str, resolved_name: Optional[str],
                      coords: Optional[tuple]) -> Optional[dict]:
    """(#352) Retry the value read against common role aliases (Edit↔Document↔
    RichEdit20W, Text↔StaticText) when the exact role found nothing — Win11 Notepad
    exposes its editor as Document but users type Edit. First hit, or None."""
    _ROLE_ALIASES = {
        "Edit": ["Document", "RichEdit20W"],
        "Document": ["Edit", "RichEdit20W"],
        "RichEdit20W": ["Edit", "Document"],
        "Text": ["StaticText"],
        "StaticText": ["Text"],
    }
    for alias_role in _ROLE_ALIASES.get(resolved_role, []):
        result = core.get_element_value(
            hwnd=target_hwnd, automation_id=resolved_aid, role=alias_role,
            name=resolved_name,
            hint_x=coords[0] if coords else None,
            hint_y=coords[1] if coords else None)
        if result is not None:
            return result
    return None


def _finalize_value(result: Optional[dict], ref: Optional[str]) -> Optional[dict]:
    """Apply the value read's tail fallbacks: NameProperty (#521), snapshot
    metadata (#229), and lone-CR normalization (#Win11 Notepad)."""
    # (#521) NameProperty: core found the element but no pattern gave a value
    # (e.g. Calculator's display embeds the value in the UIA Name).
    if isinstance(result, dict) and result.get("value") is None:
        elem_name = result.get("name")
        if elem_name:
            result["value"] = elem_name
            result["pattern"] = "NameProperty"

    # (#229) UIA found nothing but the ref carries snapshot data — return
    # role/name/bounds instead of ELEMENT_NOT_FOUND.
    if result is None and ref:
        from naturo.snapshot import get_snapshot_manager
        _el_result = get_snapshot_manager().resolve_ref_element(ref)
        if _el_result:
            _elem, _snap = _el_result
            ex, ey, ew, eh = _elem.frame
            result = {
                "role": _elem.role,
                "name": _elem.title or _elem.label,
                "value": _elem.value,
                "pattern": None,
                "automation_id": _elem.identifier,
                "x": ex, "y": ey, "width": ew, "height": eh,
                "source": "snapshot",
            }

    # Normalize document line endings — a text control's TextPattern can return
    # lone \r (Win11 Notepad's line break), which renders as one mangled line.
    if isinstance(result, dict) and isinstance(result.get("value"), str) \
            and "\r" in result["value"]:
        result["value"] = result["value"].replace("\r\n", "\n").replace("\r", "\n")
    return result


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
    @heal_core_on_failure(retry=True)
    def get_element_tree(self, window_title: Optional[str] = None,
                         depth: int = 0,
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

        result = _traverse_via_backend(self, core, backend, handle, depth)
        if result is None:
            return None

        # (#613) Fix coordinate mismatch on UWP/high-DPI: UIA may return large
        # negative coords for UWP apps when DPI contexts conflict.
        if handle:
            result = self._fixup_element_coords(result, handle)

        # Post-process: assign sequential IDs + parent_id, then convert the bridge
        # tree to backend ElementInfo (states, capabilities, value previews).
        populate_hierarchy(result)
        return _convert_bridge_element(result)
    @staticmethod
    def _read_scintilla_ref_live(elem) -> Optional[dict]:
        """Live-read a Scintilla node's text, or ``None`` if not a Scintilla ref.

        Scintilla nodes carry ``identifier == "scintilla_<child_hwnd>"`` (the id
        the cascade provider assigned). We recover the HWND and read the current
        document across the process boundary, so ``get eN`` reflects live edits
        instead of the value snapshotted at ``see`` time. Returns ``None`` when
        the ref is not a Scintilla node or the control can no longer be read
        (caller then falls through to the normal path / snapshot fallback).
        """
        ident = getattr(elem, "identifier", None) or ""
        if not ident.startswith("scintilla_"):
            return None
        try:
            sci_hwnd = int(ident.split("_", 1)[1])
        except (ValueError, IndexError):
            return None
        try:
            from naturo.cascade._scintilla import _read_scintilla_text
            text = _read_scintilla_text(sci_hwnd)
        except Exception:
            text = None
        if text is None:  # control gone — let the caller degrade gracefully
            return None
        if "\r" in text:
            text = text.replace("\r\n", "\n").replace("\r", "\n")
        ex, ey, ew, eh = elem.frame
        return {
            "role": elem.role,
            "name": elem.title or elem.label,
            "value": text,
            "pattern": "Scintilla",
            "automation_id": None,
            "x": ex,
            "y": ey,
            "width": ew,
            "height": eh,
            "source": "scintilla",
        }

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

        resolved_aid = automation_id
        resolved_role = role
        resolved_name = name
        target_hwnd = hwnd or 0
        coords = None
        snap_hwnd = None

        # Resolve a snapshot ref (e47) to element metadata + its source window.
        if ref and not resolved_aid:
            meta = _resolve_ref_metadata(
                self, ref, resolved_aid, resolved_role, resolved_name, target_hwnd)
            if meta.early is not None:
                return meta.early  # live Scintilla re-read
            resolved_aid, resolved_role, resolved_name = meta.aid, meta.role, meta.name
            coords, snap_hwnd, target_hwnd = meta.coords, meta.snap_hwnd, meta.target_hwnd

        # Resolve app/window_title to HWND. A supplied selector that matches
        # nothing must fail loudly — _resolve_hwnd raises WindowNotFoundError and
        # we let it propagate rather than degrade to the foreground window (#964).
        if (app or window_title) and not target_hwnd:
            target_hwnd = self._resolve_hwnd(app=app, window_title=window_title)

        # (#1208) Cached-point live read for an element with no AutomationId and
        # no name: read the value from the element inside its own window's UIA
        # tree (a Python/comtypes fallback layered on the C++ core reader below).
        if coords is not None and not resolved_aid and not (
                resolved_role and resolved_name):
            if not target_hwnd and snap_hwnd:
                target_hwnd = snap_hwnd
            if hasattr(self, "get_element_value_uia"):
                _uia_val = self.get_element_value_uia(
                    hwnd=target_hwnd or 0, x=coords[0], y=coords[1])
                if _uia_val is not None:
                    return _uia_val

        if not resolved_aid and not resolved_role and not resolved_name:
            if target_hwnd:
                return _probe_editable_roles(core, target_hwnd)  # (#242)
            raise NaturoError("Must specify ref, automation_id, or role/name to get value")

        result = core.get_element_value(
            hwnd=target_hwnd, automation_id=resolved_aid, role=resolved_role,
            name=resolved_name,
            hint_x=coords[0] if coords else None,
            hint_y=coords[1] if coords else None)

        if result is None and resolved_role and not resolved_aid:
            result = _role_alias_retry(
                core, target_hwnd=target_hwnd, resolved_aid=resolved_aid,
                resolved_role=resolved_role, resolved_name=resolved_name, coords=coords)

        return _finalize_value(result, ref)
