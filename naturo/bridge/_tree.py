"""Win32 HWND enumeration and hybrid UIA+Win32 tree building.

Contains the Win32 class-name-to-role mapping, HWND tree enumeration
(fallback for VB6/ActiveX apps), and the hybrid Win32+UIA enumerator
that grafts UIA subtrees onto Win32 nodes for complex controls.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from naturo.bridge._models import ElementInfo, populate_hierarchy

if TYPE_CHECKING:
    from naturo.bridge._core import NaturoCore

logger = logging.getLogger(__name__)


# ── Win32 HWND Enumeration Fallback (Issue #308) ──

# Win32 class name → UIA-style role mapping for VB6/ActiveX controls
_WIN32_CLASS_ROLE_MAP = {
    "Static": "Text",
    "Edit": "Edit",
    "Button": "Button",
    "ComboBox": "ComboBox",
    "ComboBoxEx32": "ComboBox",
    "ListBox": "List",
    "SysListView32": "DataGrid",
    "SysTreeView32": "Tree",
    "msctls_statusbar32": "StatusBar",
    "ThunderRT6FormDC": "Window",
    "ThunderRT6UserControlDC": "Pane",
    "ThunderRT6PictureBoxDC": "Pane",
    "ThunderRT6TextBox": "Edit",
    "ThunderRT6CommandButton": "Button",
    "ThunderRT6ComboBox": "ComboBox",
    "ThunderRT6ListBox": "List",
    "ThunderRT6Frame": "Group",
    "ThunderRT6OptionButton": "RadioButton",
    "ThunderRT6CheckBox": "CheckBox",
}


def _get_role_from_class_name(cls_name: str, is_top_level: bool = False) -> str:
    """Map Win32 class name to UIA-style role.

    Handles WindowsForms dynamic class names (e.g., WindowsForms10.EDIT.app.0.xxx).

    Args:
        cls_name: Win32 class name from GetClassName
        is_top_level: If True, default to "Window" instead of "Pane"

    Returns:
        UIA role string (Button, Edit, Text, etc.)
    """
    # Direct match (e.g., "Button", "ThunderRT6CommandButton")
    role = _WIN32_CLASS_ROLE_MAP.get(cls_name)
    if role:
        return role

    # WindowsForms class name pattern: WindowsForms10.{TYPE}.app.{version}.{hash}
    # Examples:
    #   WindowsForms10.STATIC.app.0.xxx → TYPE=STATIC → Text
    #   WindowsForms10.EDIT.app.0.xxx → TYPE=EDIT → Edit
    #   WindowsForms10.Window.8.app.0.xxx → TYPE=Window → Pane (generic container)
    if cls_name.startswith("WindowsForms10."):
        parts = cls_name.split(".")
        if len(parts) >= 3:
            inner_type = parts[1]  # e.g., "EDIT", "STATIC", "Window", "SysTreeView32"
            # Try exact match first (handles "SysTreeView32" embedded in WindowsForms)
            role = _WIN32_CLASS_ROLE_MAP.get(inner_type)
            if role:
                return role
            # Fallback: uppercase TYPE might be uppercase version of base class
            # (STATIC → Static, EDIT → Edit)
            if inner_type.isupper():
                role = _WIN32_CLASS_ROLE_MAP.get(inner_type.capitalize())
                if role:
                    return role

    return "Window" if is_top_level else "Pane"


def enumerate_child_windows(hwnd: int, depth: int = 10) -> Optional[ElementInfo]:
    """Enumerate child windows using Win32 FindWindowEx as UIA fallback.

    For VB6/ActiveX applications (e.g., \u7528\u53cbU8 ERP) where UIA/MSAA see
    controls as opaque Pane containers, this function walks the Win32 HWND
    tree directly and constructs an ElementInfo tree from GetClassName,
    GetWindowText, and GetWindowRect.

    Uses FindWindowEx (not EnumChildWindows) to enumerate only DIRECT
    children at each level, then recurses. EnumChildWindows returns ALL
    descendants which causes exponential duplication when recursing.

    Args:
        hwnd: Parent window handle. 0 for the foreground window.
        depth: Maximum recursion depth. Default 10.

    Returns:
        Root ElementInfo with children, or None if enumeration fails.
    """
    import ctypes
    from ctypes import wintypes
    import platform

    if platform.system() != "Windows":
        return None

    if depth < 1:
        depth = 1

    user32 = ctypes.windll.user32

    # Resolve foreground window if hwnd is 0
    if hwnd == 0:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

    def _get_window_info(h):
        """Get title, class name, and rect for a window handle."""
        title_buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, title_buf, 256)
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, cls_buf, 256)
        rect = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(rect))
        return title_buf.value or "", cls_buf.value or "", rect

    def _get_direct_children(parent_hwnd):
        """Get only DIRECT child HWNDs using FindWindowEx."""
        children = []
        child = user32.FindWindowExW(parent_hwnd, None, None, None)
        while child:
            children.append(child)
            child = user32.FindWindowExW(parent_hwnd, child, None, None)
        return children

    # Counter for sequential IDs
    counter = [0]

    def _build_tree(h, current_depth):
        """Recursively build ElementInfo tree from HWND hierarchy."""
        title, cls_name, rect = _get_window_info(h)
        is_top_level = (current_depth == 0)
        role = _get_role_from_class_name(cls_name, is_top_level=is_top_level)

        # Include class name in display for debugging and identification
        display_name = title
        if cls_name and cls_name not in (title, ""):
            display_name = f"{title} [{cls_name}]" if title else f"[{cls_name}]"

        elem = ElementInfo(
            id=f"e{counter[0]}",
            role=role,
            name=display_name,
            value=None,
            x=rect.left,
            y=rect.top,
            width=rect.right - rect.left,
            height=rect.bottom - rect.top,
            children=[],
            hwnd=h,
        )
        counter[0] += 1

        # Recurse into direct children
        if current_depth < depth:
            for child_hwnd in _get_direct_children(h):
                child_elem = _build_tree(child_hwnd, current_depth + 1)
                if child_elem:
                    elem.children.append(child_elem)

        return elem

    root = _build_tree(hwnd, 0)

    # Populate parent IDs
    populate_hierarchy(root)

    return root


# ── Win32+UIA Hybrid Enumeration (Issue #312) ──

# Win32 classes whose internal structure (rows, cells, tree items) is only
# visible through UIA, not as child HWNDs.  For these controls the hybrid
# enumerator calls UIA on the control's HWND and grafts the resulting
# subtree onto the Win32 node.
_HYBRID_UIA_DRILL_CLASSES: set[str] = {
    # ComponentOne VSFlexGrid \u2014 used heavily in VB6 ERP apps (e.g. \u7528\u53cbU8)
    "VSFlexGrid8N",
    "VSFlexGrid8U",
    # Windows common controls with internal item structure
    "SysListView32",
    "SysTreeView32",
    # MFC OLE container \u2014 may host ActiveX grids/spreadsheets
    "AfxOleControl42u",
    # Spread/FarPoint grid controls (common in legacy .NET/VB6 apps)
    "FarPoint.Spread",
    "fpSpread",
}


def _needs_uia_drill(cls_name: str, has_hwnd_children: bool) -> bool:
    """Decide whether a Win32 node should be enriched with UIA children.

    Returns True when:
    - The class is in the known complex-control list, OR
    - The node is a leaf (no child HWNDs) and its class looks like a
      data-bearing control (DataGrid/List/Tree role).

    Args:
        cls_name: Win32 window class name.
        has_hwnd_children: Whether this HWND has any direct child HWNDs.

    Returns:
        True if UIA drill-down should be attempted.
    """
    if cls_name in _HYBRID_UIA_DRILL_CLASSES:
        return True
    # WindowsForms variants of the above (e.g. WindowsForms10.SysListView32.app.0.xxx)
    if cls_name.startswith("WindowsForms10."):
        parts = cls_name.split(".")
        if len(parts) >= 3 and parts[1] in _HYBRID_UIA_DRILL_CLASSES:
            return True
    return False


def enumerate_hybrid_tree(
    hwnd: int,
    depth: int = 10,
    core: Optional["NaturoCore"] = None,
    uia_depth: int = 5,
) -> Optional[ElementInfo]:
    """Hybrid Win32+UIA enumeration for VB6/ActiveX applications.

    Enumerates the Win32 HWND tree using FindWindowEx (like
    ``enumerate_child_windows``).  For known complex controls whose internal
    structure is invisible to Win32 \u2014 grids, list views, tree views \u2014 calls
    UIA on that specific HWND and grafts the resulting children onto the
    Win32 node.

    This is the strategy described in Naturobot for apps like \u7528\u53cbU8 where
    Win32 finds 500+ controls but misses VSFlexGrid row/cell internals.

    Args:
        hwnd: Parent window handle.  0 for the foreground window.
        depth: Maximum HWND recursion depth.  Default 10.
        core: NaturoCore instance for UIA calls.  If None, no UIA
            drill-down is performed (degrades to pure Win32 enumeration).
        uia_depth: Depth limit for UIA sub-tree enumeration on each
            complex control.  Default 5.

    Returns:
        Root ElementInfo with merged HWND + UIA children, or None.
    """
    import ctypes
    from ctypes import wintypes
    import platform

    if platform.system() != "Windows":
        return None

    if depth < 1:
        depth = 1

    user32 = ctypes.windll.user32

    # Resolve foreground window if hwnd is 0
    if hwnd == 0:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

    def _get_window_info(h):
        """Get title, class name, and rect for a window handle."""
        title_buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, title_buf, 256)
        cls_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, cls_buf, 256)
        rect = wintypes.RECT()
        user32.GetWindowRect(h, ctypes.byref(rect))
        return title_buf.value or "", cls_buf.value or "", rect

    def _get_direct_children(parent_hwnd):
        """Get only DIRECT child HWNDs using FindWindowEx."""
        children = []
        child = user32.FindWindowExW(parent_hwnd, None, None, None)
        while child:
            children.append(child)
            child = user32.FindWindowExW(parent_hwnd, child, None, None)
        return children

    counter = [0]

    def _build_tree(h, current_depth):
        """Recursively build ElementInfo tree, with UIA drill-down."""
        title, cls_name, rect = _get_window_info(h)
        is_top_level = (current_depth == 0)
        role = _get_role_from_class_name(cls_name, is_top_level=is_top_level)

        display_name = title
        if cls_name and cls_name not in (title, ""):
            display_name = f"{title} [{cls_name}]" if title else f"[{cls_name}]"

        elem = ElementInfo(
            id=f"e{counter[0]}",
            role=role,
            name=display_name,
            value=None,
            x=rect.left,
            y=rect.top,
            width=rect.right - rect.left,
            height=rect.bottom - rect.top,
            children=[],
            hwnd=h,
        )
        counter[0] += 1

        # Get direct HWND children
        hwnd_children = _get_direct_children(h) if current_depth < depth else []

        # Decide: UIA drill-down or continue HWND recursion
        if _needs_uia_drill(cls_name, bool(hwnd_children)) and core is not None:
            # Call UIA on this specific HWND to get internal structure
            try:
                uia_subtree = core.get_element_tree(hwnd=h, depth=uia_depth)
                if uia_subtree is not None and uia_subtree.children:
                    # Tag UIA children and graft them onto the Win32 node
                    for uia_child in uia_subtree.children:
                        _tag_uia_source(uia_child)
                        elem.children.append(uia_child)
                    logger.debug(
                        "Hybrid: UIA drill-down on %s (class=%s) found %d "
                        "internal elements",
                        h, cls_name, len(uia_subtree.children),
                    )
            except Exception as exc:
                logger.debug(
                    "Hybrid: UIA drill-down failed for HWND %s (class=%s): %s",
                    h, cls_name, exc,
                )
            # Also recurse into HWND children (they may have their own structure)
            for child_hwnd in hwnd_children:
                child_elem = _build_tree(child_hwnd, current_depth + 1)
                if child_elem:
                    elem.children.append(child_elem)
        else:
            # Normal HWND recursion
            for child_hwnd in hwnd_children:
                child_elem = _build_tree(child_hwnd, current_depth + 1)
                if child_elem:
                    elem.children.append(child_elem)

        return elem

    root = _build_tree(hwnd, 0)
    populate_hierarchy(root)
    return root


def _tag_uia_source(elem: ElementInfo) -> None:
    """Mark an element and all descendants as discovered via UIA drill-down.

    Prepends "[uia] " to the name so users can distinguish UIA-discovered
    internal elements from Win32-discovered HWND nodes in the tree output.

    Args:
        elem: Root of the UIA subtree to tag.
    """
    if elem.name and not elem.name.startswith("[uia] "):
        elem.name = f"[uia] {elem.name}"
    elif not elem.name:
        elem.name = "[uia]"
    for child in elem.children:
        _tag_uia_source(child)
