"""Tests for coverage estimation — fix for #609.

Verifies that _estimate_coverage ignores container elements (Pane, Group, etc.)
that have children, preventing false 100% coverage on Electron/CEF apps.
"""
from __future__ import annotations

import pytest

from naturo.backends.base import ElementInfo
from naturo.cascade import _estimate_coverage, _is_actionable_leaf


def _el(role: str, x: int, y: int, w: int, h: int,
        children: list | None = None) -> ElementInfo:
    """Helper to create an ElementInfo with minimal fields."""
    return ElementInfo(
        id="test",
        role=role,
        name="",
        value=None,
        x=x, y=y, width=w, height=h,
        children=children or [],
        properties={},
    )


class TestIsActionableLeaf:
    """Test _is_actionable_leaf classification."""

    def test_leaf_button(self) -> None:
        assert _is_actionable_leaf(_el("Button", 0, 0, 80, 30)) is True

    def test_leaf_pane(self) -> None:
        """A Pane with no children IS counted (it's a leaf — no deeper info)."""
        assert _is_actionable_leaf(_el("Pane", 0, 0, 1000, 800)) is True

    def test_pane_with_children(self) -> None:
        """A Pane with children is NOT counted — children provide real coverage."""
        child = _el("Button", 10, 10, 80, 30)
        pane = _el("Pane", 0, 0, 1000, 800, children=[child])
        assert _is_actionable_leaf(pane) is False

    def test_group_with_children(self) -> None:
        child = _el("Text", 10, 10, 100, 20)
        group = _el("Group", 0, 0, 500, 400, children=[child])
        assert _is_actionable_leaf(group) is False

    def test_window_with_children(self) -> None:
        child = _el("Pane", 0, 0, 1920, 1080)
        window = _el("Window", 0, 0, 1920, 1080, children=[child])
        assert _is_actionable_leaf(window) is False

    def test_document_with_children(self) -> None:
        child = _el("Text", 0, 0, 200, 20)
        doc = _el("Document", 0, 0, 1000, 800, children=[child])
        assert _is_actionable_leaf(doc) is False

    def test_tabitem_with_children_counts(self) -> None:
        """TabItem is not a container role — it counts even with children."""
        child = _el("Text", 0, 0, 100, 20)
        tab = _el("TabItem", 10, 10, 120, 30, children=[child])
        assert _is_actionable_leaf(tab) is True

    def test_custom_with_children(self) -> None:
        """Custom role with children — treated as container, skip."""
        child = _el("Button", 10, 10, 80, 30)
        custom = _el("Custom", 0, 0, 500, 400, children=[child])
        assert _is_actionable_leaf(custom) is False


class TestEstimateCoverage:
    """Test _estimate_coverage with the improved leaf-only counting."""

    def test_empty_elements(self) -> None:
        assert _estimate_coverage([], 100000) == 0.0

    def test_zero_window_area(self) -> None:
        assert _estimate_coverage([_el("Button", 0, 0, 80, 30)], 0) == 0.0

    def test_leaf_buttons_count(self) -> None:
        """Leaf buttons contribute their full area to coverage."""
        # Window is 1000x1000 = 1,000,000
        # Two buttons: 100x50 each = 5,000 each = 10,000 total
        elements = [
            _el("Button", 10, 10, 100, 50),
            _el("Button", 200, 10, 100, 50),
        ]
        coverage = _estimate_coverage(elements, 1_000_000)
        assert abs(coverage - 0.01) < 0.001  # 10000/1000000 = 1%

    def test_container_with_children_excluded(self) -> None:
        """A full-window Pane with children should NOT inflate coverage."""
        button = _el("Button", 10, 10, 100, 50)
        pane = _el("Pane", 0, 0, 1000, 1000, children=[button])
        # Only the button (100*50=5000) should count, not the pane (1000*1000)
        elements = [pane, button]
        coverage = _estimate_coverage(elements, 1_000_000)
        assert coverage < 0.01  # 5000/1000000 = 0.5%, not 100%

    def test_electron_app_scenario(self) -> None:
        """Simulate the Feishu/Electron scenario from #609.

        UIA returns a few containers that span the full window area,
        but no actionable leaf elements inside the sidebar region.
        Coverage should NOT be 100%.
        """
        # Simulated UIA tree for an Electron app:
        # Window (1920x1080) → Pane (1920x1080) → Document (1920x1080)
        # Only the top bar has actual leaf buttons
        top_bar_btn = _el("Button", 10, 10, 80, 30)  # 2400 area
        menu_btn = _el("Button", 100, 10, 80, 30)     # 2400 area
        doc = _el("Document", 0, 0, 1920, 1080, children=[top_bar_btn, menu_btn])
        pane = _el("Pane", 0, 0, 1920, 1080, children=[doc])

        window_area = 1920 * 1080  # 2,073,600
        elements = [pane, doc, top_bar_btn, menu_btn]
        coverage = _estimate_coverage(elements, window_area)
        # Should be ~0.2% (4800/2073600), NOT 100%
        assert coverage < 0.01

    def test_leaf_pane_counts_when_no_children(self) -> None:
        """A Pane with no children is a leaf — it should count."""
        pane = _el("Pane", 100, 100, 200, 200)
        coverage = _estimate_coverage([pane], 1_000_000)
        assert coverage > 0  # 40000/1000000 = 4%

    def test_mixed_elements(self) -> None:
        """Mix of containers with children and leaf elements."""
        leaf_btn = _el("Button", 10, 10, 100, 50)       # 5000 — counts
        leaf_input = _el("Edit", 10, 70, 200, 30)       # 6000 — counts
        child = _el("Text", 500, 500, 100, 20)           # 2000 — counts
        container = _el("Group", 0, 0, 800, 600, children=[child])  # 480000 — SKIP

        elements = [leaf_btn, leaf_input, container, child]
        coverage = _estimate_coverage(elements, 1_000_000)
        # 5000 + 6000 + 2000 = 13000 / 1000000 = 1.3%
        assert abs(coverage - 0.013) < 0.002
