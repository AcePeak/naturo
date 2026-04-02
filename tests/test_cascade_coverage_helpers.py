"""Tests for cascade coverage and shallow-tree helpers.

Covers the pure functions in naturo.cascade._coverage and
naturo.cascade._types that had zero test coverage:
- _is_actionable_leaf
- _covered_area
- _has_invalid_bounds
- _is_shallow_tree
- CascadeStats.to_dict
- CascadeResult fields
- ProviderStat defaults
"""
from __future__ import annotations

from naturo.backends.base import ElementInfo
from naturo.cascade._coverage import (
    _is_actionable_leaf,
    _covered_area,
    _has_invalid_bounds,
    _is_shallow_tree,
    _rect_area,
    _window_area,
    _estimate_coverage,
    _CONTAINER_ROLES,
    SHALLOW_TREE_MAX_ELEMENTS,
    SHALLOW_TREE_INVALID_BOUNDS_RATIO,
)
from naturo.cascade._types import CascadeResult, CascadeStats, ProviderStat


def _el(
    role: str = "Button",
    name: str = "",
    x: int = 10,
    y: int = 10,
    w: int = 100,
    h: int = 30,
    children: list | None = None,
) -> ElementInfo:
    return ElementInfo(
        id="",
        role=role,
        name=name,
        value=None,
        x=x,
        y=y,
        width=w,
        height=h,
        children=children or [],
        properties={},
    )


# ── _is_actionable_leaf ─────────────────────────────────────────────────────


class TestIsActionableLeaf:
    def test_leaf_button_is_actionable(self):
        assert _is_actionable_leaf(_el(role="Button")) is True

    def test_leaf_text_is_actionable(self):
        assert _is_actionable_leaf(_el(role="Text")) is True

    def test_leaf_pane_is_actionable(self):
        """Leaf container (no children) still counts."""
        assert _is_actionable_leaf(_el(role="Pane")) is True

    def test_container_pane_with_children_excluded(self):
        child = _el(role="Button")
        parent = _el(role="Pane", children=[child])
        assert _is_actionable_leaf(parent) is False

    def test_container_group_with_children_excluded(self):
        parent = _el(role="Group", children=[_el()])
        assert _is_actionable_leaf(parent) is False

    def test_container_window_with_children_excluded(self):
        parent = _el(role="Window", children=[_el()])
        assert _is_actionable_leaf(parent) is False

    def test_non_container_with_children_counts(self):
        """TabItem with children still counts as actionable."""
        parent = _el(role="TabItem", children=[_el()])
        assert _is_actionable_leaf(parent) is True

    def test_all_container_roles_excluded_with_children(self):
        for role in _CONTAINER_ROLES:
            parent = _el(role=role.capitalize(), children=[_el()])
            # _CONTAINER_ROLES stores lowercase; the function lowercases
            assert _is_actionable_leaf(parent) is False, f"{role} should be excluded"

    def test_case_insensitive_role_matching(self):
        parent = _el(role="PANE", children=[_el()])
        assert _is_actionable_leaf(parent) is False


# ── _covered_area ────────────────────────────────────────────────────────────


class TestCoveredArea:
    def test_single_leaf(self):
        els = [_el(x=0, y=0, w=100, h=50)]
        assert _covered_area(els) == 5000

    def test_excludes_container_with_children(self):
        child = _el(x=0, y=0, w=50, h=50)
        container = _el(role="Pane", x=0, y=0, w=1000, h=1000, children=[child])
        # Only child counted (50*50=2500), not the container
        assert _covered_area([container, child]) == 2500

    def test_empty_list(self):
        assert _covered_area([]) == 0

    def test_multiple_leaves(self):
        els = [_el(x=0, y=0, w=10, h=10), _el(x=20, y=20, w=10, h=10)]
        assert _covered_area(els) == 200


# ── _has_invalid_bounds ──────────────────────────────────────────────────────


class TestHasInvalidBounds:
    def test_valid_bounds(self):
        assert _has_invalid_bounds(_el(x=10, y=10, w=100, h=50)) is False

    def test_zero_width(self):
        assert _has_invalid_bounds(_el(x=10, y=10, w=0, h=50)) is True

    def test_zero_height(self):
        assert _has_invalid_bounds(_el(x=10, y=10, w=100, h=0)) is True

    def test_negative_x(self):
        assert _has_invalid_bounds(_el(x=-1, y=10, w=100, h=50)) is True

    def test_negative_y(self):
        assert _has_invalid_bounds(_el(x=10, y=-1, w=100, h=50)) is True

    def test_zero_coords_valid(self):
        assert _has_invalid_bounds(_el(x=0, y=0, w=100, h=50)) is False


# ── _is_shallow_tree ─────────────────────────────────────────────────────────


class TestIsShallowTree:
    def test_empty_list_is_shallow(self):
        is_shallow, total, invalid = _is_shallow_tree([])
        assert is_shallow is True
        assert total == 0
        assert invalid == 0

    def test_many_elements_not_shallow(self):
        els = [_el() for _ in range(SHALLOW_TREE_MAX_ELEMENTS + 1)]
        is_shallow, total, invalid = _is_shallow_tree(els)
        assert is_shallow is False
        assert total == SHALLOW_TREE_MAX_ELEMENTS + 1

    def test_few_valid_elements_not_shallow(self):
        els = [_el(x=10, y=10, w=100, h=50) for _ in range(3)]
        is_shallow, total, invalid = _is_shallow_tree(els)
        assert is_shallow is False
        assert total == 3
        assert invalid == 0

    def test_few_elements_mostly_invalid_is_shallow(self):
        # 3 elements, all with zero width → 100% invalid > threshold
        els = [_el(x=0, y=0, w=0, h=0) for _ in range(3)]
        is_shallow, total, invalid = _is_shallow_tree(els)
        assert is_shallow is True
        assert total == 3
        assert invalid == 3

    def test_mixed_elements_at_threshold(self):
        # SHALLOW_TREE_INVALID_BOUNDS_RATIO = 0.5
        # 4 elements, 2 invalid → ratio = 0.5 ≥ threshold → shallow
        valid = [_el(x=10, y=10, w=100, h=50) for _ in range(2)]
        invalid = [_el(x=0, y=0, w=0, h=0) for _ in range(2)]
        is_shallow, total, inv_count = _is_shallow_tree(valid + invalid)
        assert is_shallow is True
        assert total == 4
        assert inv_count == 2

    def test_mixed_elements_below_threshold(self):
        # 4 elements, 1 invalid → ratio = 0.25 < 0.5 → not shallow
        valid = [_el(x=10, y=10, w=100, h=50) for _ in range(3)]
        invalid = [_el(x=0, y=0, w=0, h=0)]
        is_shallow, total, inv_count = _is_shallow_tree(valid + invalid)
        assert is_shallow is False
        assert total == 4
        assert inv_count == 1

    def test_exactly_max_elements_still_checked(self):
        # Exactly SHALLOW_TREE_MAX_ELEMENTS with all invalid
        els = [_el(x=0, y=0, w=0, h=0) for _ in range(SHALLOW_TREE_MAX_ELEMENTS)]
        is_shallow, total, invalid = _is_shallow_tree(els)
        assert is_shallow is True


# ── CascadeStats.to_dict ────────────────────────────────────────────────────


class TestCascadeStatsToDict:
    def test_empty_stats(self):
        stats = CascadeStats()
        d = stats.to_dict()
        assert d == {
            "total_elements": 0,
            "coverage_estimate": 0.0,
            "providers": [],
        }

    def test_with_providers(self):
        stats = CascadeStats(
            providers=[
                ProviderStat(name="uia", elements=42, elapsed_ms=12.345),
                ProviderStat(name="cdp", elements=10, elapsed_ms=55.678, status="ok"),
            ],
            total_elements=52,
            coverage_estimate=0.7891,
        )
        d = stats.to_dict()
        assert d["total_elements"] == 52
        assert d["coverage_estimate"] == 0.789  # rounded to 3
        assert len(d["providers"]) == 2
        assert d["providers"][0]["name"] == "uia"
        assert d["providers"][0]["elements"] == 42
        assert d["providers"][0]["elapsed_ms"] == 12.3  # rounded to 1
        assert d["providers"][1]["name"] == "cdp"


# ── ProviderStat defaults ───────────────────────────────────────────────────


class TestProviderStat:
    def test_defaults(self):
        ps = ProviderStat(name="uia")
        assert ps.elements == 0
        assert ps.elapsed_ms == 0.0
        assert ps.status == "ok"

    def test_error_status(self):
        ps = ProviderStat(name="cdp", status="error")
        assert ps.status == "error"


# ── CascadeResult ───────────────────────────────────────────────────────────


class TestCascadeResult:
    def test_none_tree(self):
        r = CascadeResult(tree=None, stats=CascadeStats())
        assert r.tree is None
        assert r.primary_provider == "uia"

    def test_with_tree(self):
        tree = _el(role="Window")
        r = CascadeResult(tree=tree, stats=CascadeStats(), primary_provider="cdp")
        assert r.tree is tree
        assert r.primary_provider == "cdp"


# ── _rect_area edge cases ───────────────────────────────────────────────────


class TestRectAreaEdgeCases:
    def test_negative_width_clamped(self):
        assert _rect_area(0, 0, -10, 50) == 0

    def test_negative_height_clamped(self):
        assert _rect_area(0, 0, 50, -10) == 0

    def test_both_negative_clamped(self):
        assert _rect_area(0, 0, -10, -20) == 0


# ── _window_area ─────────────────────────────────────────────────────────────


class TestWindowArea:
    def test_normal_window(self):
        w = _el(x=0, y=0, w=1920, h=1080)
        assert _window_area(w) == 1920 * 1080


# ── _estimate_coverage edge cases ────────────────────────────────────────────


class TestEstimateCoverageEdgeCases:
    def test_coverage_capped_at_one(self):
        """Overlapping elements can exceed window area; coverage stays <= 1.0."""
        big = _el(x=0, y=0, w=2000, h=2000)
        assert _estimate_coverage([big], 100) == 1.0

    def test_zero_window_area(self):
        assert _estimate_coverage([_el()], 0) == 0.0

    def test_negative_window_area(self):
        assert _estimate_coverage([_el()], -100) == 0.0
