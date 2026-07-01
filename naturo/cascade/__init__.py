"""Cascading recognition engine for the ``see`` command (issue #140).

Progressive multi-provider UI element recognition:

1. Start with UIA (fastest, works on Win32/WPF/UWP)
2. If the app is detected as Electron/CEF and a debug port is available,
   add CDP elements for web-rendered content
3. If element coverage is still below the target threshold and AI is
   available, use vision to fill remaining gaps
4. Return merged element tree with ``source`` metadata on each element

Design goals
------------
* **Zero mandatory dependencies** — every provider is optional.  If CDP/AI
  is unavailable, we degrade gracefully to UIA only.
* **Cheap default** — UIA-only path adds no latency.  CDP is only attempted
  when Electron is detected.  AI is only attempted when explicitly enabled
  via ``--fill-gaps`` or when coverage is below the target.
* **Source tagging** — each element gets a ``source`` attribute so callers
  can see which provider found it.
* **No numpy** — coverage calculation uses simple rectangle intersection
  rather than pixel canvas arithmetic.

Public API
----------
    result = run_cascade(
        backend, app=app, window_title=window_title, hwnd=hwnd,
        depth=depth, backend_name='uia',
        coverage_target=0.0,   # 0 = UIA only unless Electron detected
        fill_gaps_ai=False,
    )
    tree    = result.tree        # ElementInfo root (same as backend.get_element_tree)
    stats   = result.stats       # CascadeStats
    session = result.session     # snapshot session string (pass to SnapshotManager)
"""

from naturo.cascade._types import CascadeResult, CascadeStats, ProviderStat
from naturo.cascade._run import run_cascade, _run_cdp_only
from naturo.cascade._build import (
    build_hybrid_tree,
    find_cdp_port,
    _CLASS_BACKEND_MAP,
    _detect_backend_for_class,
    _is_java_window,
    _find_node_by_bounds,
    _get_hwnd_children_with_class,
    _try_cdp_for_hwnd,
    _try_backend_for_hwnd,
)
from naturo.cascade._merge import _merge_ai_into_tree, _iou, _find_containing_node, _text_proximity_match
from naturo.cascade._coverage import (
    _estimate_coverage,
    _flatten,
    _rect_area,
    _tag_source,
    _is_actionable_leaf,
    _covered_area,
    _window_area,
    _CONTAINER_ROLES,
    SHALLOW_TREE_MAX_ELEMENTS,
    SHALLOW_TREE_INVALID_BOUNDS_RATIO,
    _has_invalid_bounds,
    _is_shallow_tree,
)
from naturo.cascade._providers import _fetch_ai_elements, _fetch_cdp_elements
from naturo.cascade._correctness import (
    DETERMINISTIC,
    DETERMINISTIC_TECHNIQUES,
    UNCERTAIN,
    UNCERTAIN_TECHNIQUES,
    annotate,
    node_correctness,
    node_techniques,
    recognition_summary,
    technique_class,
    uncertain_warning,
)

__all__ = [
    # Types
    "CascadeResult",
    "CascadeStats",
    "ProviderStat",
    # Run
    "run_cascade",
    "_run_cdp_only",
    # Build
    "build_hybrid_tree",
    "find_cdp_port",
    "_CLASS_BACKEND_MAP",
    "_detect_backend_for_class",
    "_is_java_window",
    "_find_node_by_bounds",
    "_get_hwnd_children_with_class",
    "_try_cdp_for_hwnd",
    "_try_backend_for_hwnd",
    # Merge
    "_merge_ai_into_tree",
    "_iou",
    "_find_containing_node",
    "_text_proximity_match",
    # Coverage
    "_estimate_coverage",
    "_flatten",
    "_rect_area",
    "_tag_source",
    "_is_actionable_leaf",
    "_covered_area",
    "_window_area",
    "_CONTAINER_ROLES",
    "SHALLOW_TREE_MAX_ELEMENTS",
    "SHALLOW_TREE_INVALID_BOUNDS_RATIO",
    "_has_invalid_bounds",
    "_is_shallow_tree",
    # Providers
    "_fetch_ai_elements",
    "_fetch_cdp_elements",
    # Correctness / fusion tagging (M1 Unified Auto Element Tree)
    "DETERMINISTIC",
    "DETERMINISTIC_TECHNIQUES",
    "UNCERTAIN",
    "UNCERTAIN_TECHNIQUES",
    "annotate",
    "node_correctness",
    "node_techniques",
    "recognition_summary",
    "technique_class",
    "uncertain_warning",
]
