"""Tests for click --on text fallback search (#442).

When the C++ exact UIA Name match fails, the fallback searches the
element tree for matching elements.  This handles localized apps
where the UIA Name differs from the visible text (e.g., Calculator
on Chinese Windows has UIA Name "清除" but displays "C").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock

import pytest

from naturo.backends.base import ElementInfo
from naturo.cli.interaction import _find_element_by_text_fallback


def _make_element(
    name: str,
    role: str = "Text",
    x: int = 100,
    y: int = 100,
    width: int = 40,
    height: int = 40,
    children: Optional[list] = None,
    value: Optional[str] = None,
) -> ElementInfo:
    """Create an ElementInfo for testing."""
    return ElementInfo(
        id="",
        role=role,
        name=name,
        value=value,
        x=x,
        y=y,
        width=width,
        height=height,
        children=children or [],
        properties={},
    )


def _make_calculator_tree() -> ElementInfo:
    """Build a simplified Calculator element tree matching Chinese locale.

    Structure:
        Window "计算器"
          ├── Button "清除" (Clear button, UIA Name is Chinese)
          │   └── Text "C"  (visible label is "C")
          ├── Button "清除条目" (Clear Entry button)
          │   └── Text "CE"
          ├── Button "退格" (Backspace button)
          │   └── Text "⌫"
          ├── Button "七"  (Seven button, Chinese character)
          │   └── Text "7"
          └── Button "Cancel"  (hypothetical, for testing substring)
    """
    clear_btn = _make_element(
        "清除", role="Button", x=50, y=200, width=60, height=40,
        children=[_make_element("C", role="Text", x=60, y=210, width=30, height=20)],
    )
    ce_btn = _make_element(
        "清除条目", role="Button", x=120, y=200, width=60, height=40,
        children=[_make_element("CE", role="Text", x=130, y=210, width=30, height=20)],
    )
    backspace_btn = _make_element(
        "退格", role="Button", x=190, y=200, width=60, height=40,
        children=[_make_element("⌫", role="Text", x=200, y=210, width=30, height=20)],
    )
    seven_btn = _make_element(
        "七", role="Button", x=50, y=260, width=60, height=40,
        children=[_make_element("7", role="Text", x=60, y=270, width=30, height=20)],
    )
    cancel_btn = _make_element(
        "Cancel", role="Button", x=260, y=200, width=80, height=40,
    )
    root = _make_element(
        "计算器", role="Window", x=0, y=0, width=400, height=500,
        children=[clear_btn, ce_btn, backspace_btn, seven_btn, cancel_btn],
    )
    return root


def _make_backend(tree: Optional[ElementInfo] = None) -> MagicMock:
    """Create a mock backend that returns the given element tree."""
    backend = MagicMock()
    backend.get_element_tree.return_value = tree
    return backend


class TestFindElementByTextFallback:
    """Tests for _find_element_by_text_fallback."""

    def test_exact_match_on_child_text_element(self):
        """'C' matches the TextBlock child inside the '清除' button."""
        tree = _make_calculator_tree()
        backend = _make_backend(tree)
        result = _find_element_by_text_fallback(backend, "C", app="calculator")
        assert result is not None
        x, y = result
        # Should match the Text "C" element (center of 60,210 30x20)
        assert x == 75
        assert y == 220

    def test_exact_match_ce(self):
        """'CE' matches the TextBlock child inside the '清除条目' button."""
        tree = _make_calculator_tree()
        backend = _make_backend(tree)
        result = _find_element_by_text_fallback(backend, "CE", app="calculator")
        assert result is not None
        x, y = result
        assert x == 145
        assert y == 220

    def test_exact_match_chinese_name(self):
        """'七' matches the Button element directly (exact actionable match)."""
        tree = _make_calculator_tree()
        backend = _make_backend(tree)
        result = _find_element_by_text_fallback(backend, "七", app="calculator")
        assert result is not None
        x, y = result
        # Should match the Button "七" (actionable, exact match)
        # center of 50,260 60x40
        assert x == 80
        assert y == 280

    def test_exact_actionable_preferred_over_text(self):
        """When both a Button and a Text child match exactly, prefer the Button."""
        btn = _make_element(
            "OK", role="Button", x=10, y=10, width=80, height=40,
            children=[_make_element("OK", role="Text", x=20, y=15, width=50, height=20)],
        )
        root = _make_element(
            "Dialog", role="Window", x=0, y=0, width=300, height=200,
            children=[btn],
        )
        backend = _make_backend(root)
        result = _find_element_by_text_fallback(backend, "OK", app="dialog")
        assert result is not None
        x, y = result
        # Should prefer the Button (actionable), center of 10,10 80x40
        assert x == 50
        assert y == 30

    def test_substring_match_on_actionable(self):
        """When no exact match, falls back to substring match on actionable."""
        tree = _make_calculator_tree()
        backend = _make_backend(tree)
        result = _find_element_by_text_fallback(backend, "Canc", app="calculator")
        assert result is not None
        x, y = result
        # Should match "Cancel" button via substring, center of 260,200 80x40
        assert x == 300
        assert y == 220

    def test_no_match_returns_none(self):
        """Returns None when nothing matches."""
        tree = _make_calculator_tree()
        backend = _make_backend(tree)
        result = _find_element_by_text_fallback(backend, "ZZZ_NONEXISTENT")
        assert result is None

    def test_no_tree_returns_none(self):
        """Returns None when element tree is unavailable."""
        backend = _make_backend(None)
        result = _find_element_by_text_fallback(backend, "C", app="calculator")
        assert result is None

    def test_backend_without_get_element_tree(self):
        """Returns None for backends that don't support element trees."""
        backend = MagicMock(spec=[])  # No get_element_tree attribute
        result = _find_element_by_text_fallback(backend, "C")
        assert result is None

    def test_case_insensitive_match(self):
        """Matching is case-insensitive."""
        tree = _make_calculator_tree()
        backend = _make_backend(tree)
        result = _find_element_by_text_fallback(backend, "cancel", app="calculator")
        assert result is not None

    def test_skips_zero_bounds_elements(self):
        """Zero-bounds (offscreen) elements are skipped."""
        hidden = _make_element(
            "C", role="Button", x=0, y=0, width=0, height=0,
        )
        visible = _make_element(
            "C", role="Text", x=100, y=100, width=30, height=20,
        )
        root = _make_element(
            "Window", role="Window", x=0, y=0, width=500, height=500,
            children=[hidden, visible],
        )
        backend = _make_backend(root)
        result = _find_element_by_text_fallback(backend, "C")
        assert result is not None
        x, y = result
        # Should skip zero-bounds, use the visible one
        assert x == 115
        assert y == 110
