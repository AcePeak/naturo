"""Shared value-target resolution for BOTH the CLI ``set`` and the MCP
``set_element_value`` surface.

The CLI ``set`` resolved a snapshot ref to (automation_id, role, name, cached
coords, source window) — the #1208 fallback that lets set/toggle/select act on
elements with no AutomationId/name by resolving them inside their own window's
UIA tree via cached coordinates. The MCP ``set_element_value`` had a weaker
inline copy that dropped the coords fallback and com_ Excel routing. This module
is the single resolver both call, so the MCP surface gains the same reach.
"""
from __future__ import annotations

from naturo.errors import NaturoError, StaleSnapshotCacheError


def resolve_element_identifiers(ref, automation_id, role, name):
    """Resolve a snapshot ref to element identifiers.

    Args:
        ref: Element ref from snapshot (e.g. ``"e47"``).
        automation_id: UIA AutomationId (passthrough if already set).
        role: Element role (passthrough if already set).
        name: Element name (passthrough if already set).

    Returns:
        Tuple of (automation_id, role, name, coords, window_handle) with ref
        resolved, where ``coords`` is the cached ``(x, y)`` element centre (or
        ``None``) and ``window_handle`` is the source window's HWND (or
        ``None``) — both used to resolve the element inside its own window's
        UIA tree when it has no AutomationId/name (#1208).

    Raises:
        NaturoError: If ref resolves to an element with no AutomationId, name,
            *or* usable coordinates.
        StaleSnapshotCacheError: If the ref is not in the current snapshot.
    """
    coords = None
    snap_hwnd = None
    if ref and not automation_id:
        from naturo.snapshot import get_snapshot_manager
        mgr = get_snapshot_manager()
        result = mgr.resolve_ref_element(ref)
        if result:
            elem, _snap_id = result
            # Source window handle: lets the backend resolve the element inside
            # that window's own UIA tree (occlusion-independent), instead of a
            # screen-point hit test that an overlapping window would hijack.
            try:
                _snap = mgr.get_snapshot(_snap_id)
                snap_hwnd = getattr(_snap, "window_handle", None)
            except Exception:
                snap_hwnd = None
            # naturo already located this element, so capture its cached
            # bounding-box centre. This lets set/toggle/select/expand act on
            # elements that have no AutomationId and no name (e.g. an unnamed
            # Edit or ComboBox) by resolving them live inside their source
            # window's own UIA tree, instead of refusing and pushing identifier
            # discovery onto the user (#1208).
            frame = getattr(elem, "frame", None)
            if frame and (frame[2] > 0 or frame[3] > 0):
                coords = (frame[0] + frame[2] // 2, frame[1] + frame[3] // 2)
            if elem.identifier:
                automation_id = elem.identifier
            elif elem.role and (elem.title or elem.label):
                role = role or elem.role
                name = name or elem.title or elem.label
            elif coords is not None:
                # Unnamed element with a known location: keep its role as a hint
                # for pattern selection; resolution falls back to the point.
                role = role or elem.role
            else:
                raise NaturoError(
                    f"Element {ref} has no AutomationId, name, or location "
                    f"for value setting"
                )
        else:
            raise StaleSnapshotCacheError(ref)
    return automation_id, role, name, coords, snap_hwnd
