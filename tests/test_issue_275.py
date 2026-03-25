"""Tests for issue #275: --cascade should auto-trigger AI vision fallback
when UIA tree is too shallow.

All tests use mocks — no real Windows environment needed.
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

from naturo.backends.base import ElementInfo
from naturo.cascade import (
    SHALLOW_TREE_INVALID_BOUNDS_RATIO,
    SHALLOW_TREE_MAX_ELEMENTS,
    CascadeResult,
    _has_invalid_bounds,
    _is_shallow_tree,
    run_cascade,
)


# ── Helper factories ────────────────────────────────────────────────────────


def _make_element(
    id: str = "e0",
    role: str = "Window",
    name: str = "Test",
    x: int = 0,
    y: int = 0,
    width: int = 100,
    height: int = 100,
    children: list | None = None,
) -> ElementInfo:
    return ElementInfo(
        id=id,
        role=role,
        name=name,
        value=None,
        x=x,
        y=y,
        width=width,
        height=height,
        children=children or [],
        properties={},
    )


def _make_shallow_tree() -> ElementInfo:
    """Create a shallow tree: 4 elements, 3 with invalid bounds."""
    return _make_element(
        id="root",
        role="Window",
        name="App",
        x=0,
        y=0,
        width=800,
        height=600,
        children=[
            _make_element(id="e1", x=0, y=0, width=0, height=0),  # invalid
            _make_element(id="e2", x=-1, y=-1, width=50, height=50),  # invalid
            _make_element(id="e3", x=0, y=0, width=0, height=0),  # invalid
        ],
    )


def _make_normal_tree() -> ElementInfo:
    """Create a normal tree with 10+ valid elements."""
    children = [
        _make_element(id=f"e{i}", x=10 * i, y=10 * i, width=80, height=30)
        for i in range(1, 11)
    ]
    return _make_element(
        id="root",
        role="Window",
        name="App",
        x=0,
        y=0,
        width=800,
        height=600,
        children=children,
    )


def _make_mock_backend(tree: ElementInfo | None = None):
    """Create a mock backend that returns the given tree."""
    backend = MagicMock()
    backend.get_element_tree.return_value = tree
    return backend


# ── Tests: _has_invalid_bounds ──────────────────────────────────────────────


class TestHasInvalidBounds:
    def test_zero_width(self):
        el = _make_element(x=10, y=10, width=0, height=50)
        assert _has_invalid_bounds(el) is True

    def test_zero_height(self):
        el = _make_element(x=10, y=10, width=50, height=0)
        assert _has_invalid_bounds(el) is True

    def test_negative_x(self):
        el = _make_element(x=-1, y=10, width=50, height=50)
        assert _has_invalid_bounds(el) is True

    def test_negative_y(self):
        el = _make_element(x=10, y=-5, width=50, height=50)
        assert _has_invalid_bounds(el) is True

    def test_valid_bounds(self):
        el = _make_element(x=10, y=10, width=50, height=50)
        assert _has_invalid_bounds(el) is False

    def test_zero_origin_valid_size(self):
        el = _make_element(x=0, y=0, width=50, height=50)
        assert _has_invalid_bounds(el) is False


# ── Tests: _is_shallow_tree ────────────────────────────────────────────────


class TestIsShallowTree:
    def test_empty_list(self):
        is_shallow, total, invalid = _is_shallow_tree([])
        assert is_shallow is True
        assert total == 0

    def test_few_elements_mostly_invalid(self):
        elements = [
            _make_element(x=0, y=0, width=0, height=0),
            _make_element(x=0, y=0, width=0, height=0),
            _make_element(x=10, y=10, width=50, height=50),
        ]
        is_shallow, total, invalid = _is_shallow_tree(elements)
        assert is_shallow is True
        assert total == 3
        assert invalid == 2

    def test_few_elements_mostly_valid(self):
        """5 elements, only 1 invalid → ratio 0.2 < 0.5 → not shallow."""
        elements = [
            _make_element(x=10, y=10, width=50, height=50),
            _make_element(x=20, y=20, width=50, height=50),
            _make_element(x=30, y=30, width=50, height=50),
            _make_element(x=40, y=40, width=50, height=50),
            _make_element(x=0, y=0, width=0, height=0),  # invalid
        ]
        is_shallow, total, invalid = _is_shallow_tree(elements)
        assert is_shallow is False
        assert total == 5
        assert invalid == 1

    def test_many_elements_not_shallow(self):
        """More than SHALLOW_TREE_MAX_ELEMENTS → never shallow."""
        elements = [
            _make_element(x=0, y=0, width=0, height=0)
            for _ in range(SHALLOW_TREE_MAX_ELEMENTS + 1)
        ]
        is_shallow, total, invalid = _is_shallow_tree(elements)
        assert is_shallow is False
        assert total == SHALLOW_TREE_MAX_ELEMENTS + 1

    def test_exactly_threshold_elements_all_invalid(self):
        elements = [
            _make_element(x=0, y=0, width=0, height=0)
            for _ in range(SHALLOW_TREE_MAX_ELEMENTS)
        ]
        is_shallow, total, invalid = _is_shallow_tree(elements)
        assert is_shallow is True
        assert total == SHALLOW_TREE_MAX_ELEMENTS
        assert invalid == SHALLOW_TREE_MAX_ELEMENTS


# ── Tests: run_cascade shallow fallback ─────────────────────────────────────


class TestCascadeShallowFallback:
    """Test that run_cascade auto-triggers AI vision for shallow trees."""

    @patch("naturo.cascade._fetch_ai_elements")
    def test_shallow_tree_triggers_ai_vision(self, mock_ai):
        """When UIA tree is shallow and screenshot exists, AI vision runs."""
        mock_ai.return_value = [
            _make_element(id="ai_0", role="Button", name="OK", x=100, y=200, width=80, height=30),
            _make_element(id="ai_1", role="Edit", name="Search", x=200, y=100, width=200, height=30),
        ]

        backend = _make_mock_backend(_make_shallow_tree())
        result = run_cascade(
            backend,
            fill_gaps_ai=False,  # NOT explicitly enabled
            screenshot_path="/tmp/test_screenshot.png",
        )

        # AI vision should have been called
        mock_ai.assert_called_once()
        # Stats should include vision provider
        provider_names = [p.name for p in result.stats.providers]
        assert "vision" in provider_names
        vision_stat = next(p for p in result.stats.providers if p.name == "vision")
        assert vision_stat.elements == 2
        assert vision_stat.status == "ok"

    @patch("naturo.cascade._fetch_ai_elements")
    def test_shallow_tree_no_screenshot_no_fallback(self, mock_ai):
        """Without screenshot_path, AI vision should not trigger."""
        backend = _make_mock_backend(_make_shallow_tree())
        result = run_cascade(
            backend,
            fill_gaps_ai=False,
            screenshot_path=None,
        )

        mock_ai.assert_not_called()
        provider_names = [p.name for p in result.stats.providers]
        assert "vision" not in provider_names

    @patch("naturo.cascade._fetch_ai_elements")
    def test_normal_tree_no_auto_fallback(self, mock_ai):
        """A normal tree should NOT trigger auto fallback."""
        backend = _make_mock_backend(_make_normal_tree())
        result = run_cascade(
            backend,
            fill_gaps_ai=False,
            screenshot_path="/tmp/test_screenshot.png",
        )

        mock_ai.assert_not_called()
        provider_names = [p.name for p in result.stats.providers]
        assert "vision" not in provider_names

    @patch("naturo.cascade._fetch_ai_elements")
    def test_fill_gaps_still_works(self, mock_ai):
        """Explicit --fill-gaps should still trigger AI vision on normal trees."""
        mock_ai.return_value = [
            _make_element(id="ai_0", role="Button", name="Submit"),
        ]

        backend = _make_mock_backend(_make_normal_tree())
        result = run_cascade(
            backend,
            fill_gaps_ai=True,  # Explicitly enabled
            screenshot_path="/tmp/test_screenshot.png",
        )

        mock_ai.assert_called_once()
        provider_names = [p.name for p in result.stats.providers]
        assert "vision" in provider_names

    @patch("naturo.cascade._fetch_ai_elements")
    def test_shallow_tree_ai_returns_empty(self, mock_ai):
        """Shallow tree triggers AI but AI returns nothing → vision skipped."""
        mock_ai.return_value = []

        backend = _make_mock_backend(_make_shallow_tree())
        result = run_cascade(
            backend,
            fill_gaps_ai=False,
            screenshot_path="/tmp/test_screenshot.png",
        )

        mock_ai.assert_called_once()
        provider_names = [p.name for p in result.stats.providers]
        assert "vision" in provider_names
        vision_stat = next(p for p in result.stats.providers if p.name == "vision")
        assert vision_stat.status == "skipped"


# ── Tests: constants are sane ───────────────────────────────────────────────


class TestConstants:
    def test_max_elements_positive(self):
        assert SHALLOW_TREE_MAX_ELEMENTS > 0

    def test_ratio_between_0_and_1(self):
        assert 0.0 < SHALLOW_TREE_INVALID_BOUNDS_RATIO <= 1.0
