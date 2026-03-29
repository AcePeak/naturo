"""Bridge to naturo_core native library via ctypes.

Split into focused submodules for maintainability.  The public API is
re-exported here so that ``from naturo.bridge import NaturoCore``
and similar imports continue to work.

Submodules:
    _models     — WindowInfo, ElementInfo, parsing helpers
    _errors     — NaturoCoreError
    _tree       — Win32 enumeration, hybrid UIA+Win32, role mapping
    _highlight  — GDI and UIA element highlighting
    _core       — NaturoCore (C++ DLL bridge)
"""
from __future__ import annotations

# Re-export data models
from naturo.bridge._models import (  # noqa: F401
    ElementInfo,
    WindowInfo,
    _decode_native,
    _parse_element,
    _safe_json_loads,
    populate_hierarchy,
)

# Re-export errors
from naturo.bridge._errors import NaturoCoreError  # noqa: F401

# Re-export tree enumeration
from naturo.bridge._tree import (  # noqa: F401
    _WIN32_CLASS_ROLE_MAP,
    _HYBRID_UIA_DRILL_CLASSES,
    _get_role_from_class_name,
    _needs_uia_drill,
    _tag_uia_source,
    enumerate_child_windows,
    enumerate_hybrid_tree,
)

# Re-export highlighting
from naturo.bridge._highlight import (  # noqa: F401
    highlight_elements,
    highlight_elements_uia,
)

# Re-export the core DLL bridge
from naturo.bridge._core import NaturoCore  # noqa: F401
