"""Tests for naturo/cascade/_build.py and _run.py.

Tests pure-logic functions directly and mocks backend/platform calls
for orchestration functions.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from naturo.backends.base import ElementInfo
from naturo.cascade._build import (
    _CLASS_BACKEND_MAP,
    _detect_backend_for_class,
    _find_node_by_bounds,
    _get_hwnd_children_with_class,
    build_hybrid_tree,
)
from naturo.cascade._run import (
    _run_cdp_only,
    run_cascade,
)
from naturo.cascade._types import CascadeResult


# ── Helper to build ElementInfo trees ────────────────────────────────────────

def _el(
    name: str = "el",
    role: str = "Button",
    x: int = 0,
    y: int = 0,
    w: int = 100,
    h: int = 50,
    children: list | None = None,
) -> ElementInfo:
    return ElementInfo(
        id=name,
        role=role,
        name=name,
        value=None,
        x=x, y=y, width=w, height=h,
        children=children or [],
        properties={},
    )


# ── _detect_backend_for_class ────────────────────────────────────────────────

class TestDetectBackendForClass:

    def test_chrome_render_widget(self):
        assert _detect_backend_for_class("Chrome_RenderWidgetHostHWND") == "cdp"

    def test_chrome_widget_win_0(self):
        assert _detect_backend_for_class("Chrome_WidgetWin_0") == "cdp"

    def test_chrome_widget_win_1(self):
        assert _detect_backend_for_class("Chrome_WidgetWin_1") == "cdp"

    def test_sun_awt_frame(self):
        assert _detect_backend_for_class("SunAwtFrame") == "jab"

    def test_sun_awt_dialog(self):
        assert _detect_backend_for_class("SunAwtDialog") == "jab"

    def test_sun_awt_canvas(self):
        assert _detect_backend_for_class("SunAwtCanvas") == "jab"

    def test_sun_awt_panel(self):
        assert _detect_backend_for_class("SunAwtPanel") == "jab"

    def test_sun_awt_versioned(self):
        """Versioned SunAwt classes use prefix matching."""
        assert _detect_backend_for_class("SunAwtFrame_v2") == "jab"

    def test_javax_swing(self):
        assert _detect_backend_for_class("javax.swing.JFrame") == "jab"

    def test_mozilla_window(self):
        assert _detect_backend_for_class("MozillaWindowClass") == "ia2"

    def test_mozilla_compositor(self):
        assert _detect_backend_for_class("MozillaCompositorWindowClass") == "ia2"

    def test_unknown_class_defaults_uia(self):
        assert _detect_backend_for_class("NOTEPAD") == "uia"

    def test_empty_class(self):
        assert _detect_backend_for_class("") == "uia"

    def test_class_map_covers_all_entries(self):
        """All entries in _CLASS_BACKEND_MAP are handled."""
        for cls_name, expected in _CLASS_BACKEND_MAP.items():
            assert _detect_backend_for_class(cls_name) == expected


# ── _find_node_by_bounds ─────────────────────────────────────────────────────

class TestFindNodeByBounds:

    def test_exact_match(self):
        root = _el("root", x=0, y=0, w=800, h=600, children=[
            _el("child", x=100, y=100, w=200, h=150),
        ])
        result = _find_node_by_bounds(root, 100, 100, 200, 150)
        assert result is not None
        assert result.name == "child"

    def test_prefers_deeper_match(self):
        grandchild = _el("grandchild", x=150, y=150, w=100, h=80)
        child = _el("child", x=100, y=100, w=300, h=200, children=[grandchild])
        root = _el("root", x=0, y=0, w=800, h=600, children=[child])
        result = _find_node_by_bounds(root, 150, 150, 100, 80)
        assert result is not None
        assert result.name == "grandchild"

    def test_zero_width_returns_none(self):
        root = _el("root", x=0, y=0, w=800, h=600)
        assert _find_node_by_bounds(root, 100, 100, 0, 50) is None

    def test_zero_height_returns_none(self):
        root = _el("root", x=0, y=0, w=800, h=600)
        assert _find_node_by_bounds(root, 100, 100, 50, 0) is None

    def test_no_overlap_returns_none(self):
        root = _el("root", x=0, y=0, w=100, h=100)
        assert _find_node_by_bounds(root, 500, 500, 50, 50) is None

    def test_partial_overlap_50_percent(self):
        """Node overlapping >= 50% of target area matches."""
        root = _el("root", x=0, y=0, w=200, h=200)
        # Target 100x100 at (150, 0) — overlaps root by 50x200 area? No,
        # overlap_x = min(200,250) - max(0,150) = 50, overlap_y = min(200,100) - max(0,0) = 100
        # overlap_area = 5000, target_area = 10000, ratio = 0.5 — exactly at threshold
        result = _find_node_by_bounds(root, 150, 0, 100, 100)
        assert result is not None

    def test_root_matches_when_no_children(self):
        root = _el("root", x=0, y=0, w=800, h=600)
        result = _find_node_by_bounds(root, 50, 50, 100, 100)
        assert result is not None
        assert result.name == "root"


# ── _get_hwnd_children_with_class non-Windows ────────────────────────────────

class TestGetHwndChildrenNonWindows:

    def test_returns_empty_on_non_windows(self):
        result = _get_hwnd_children_with_class(12345)
        assert result == []


# ── build_hybrid_tree ────────────────────────────────────────────────────────

class TestBuildHybridTree:

    def _mock_backend(self, tree: ElementInfo | None = None):
        backend = MagicMock()
        backend.get_element_tree.return_value = tree
        return backend

    def test_uia_tree_none_returns_error_stats(self):
        """When UIA tree fails, stats record error."""
        backend = self._mock_backend(tree=None)
        tree, stats = build_hybrid_tree(backend, hwnd=1234)
        assert tree is None
        assert any(p.name == "uia" and p.status == "error" for p in stats.providers)

    def test_uia_tree_only_no_win32_children(self):
        """When no Win32 children, returns UIA tree as-is."""
        uia_tree = _el("root", role="Window", x=0, y=0, w=800, h=600, children=[
            _el("btn", x=10, y=10, w=80, h=30),
        ])
        backend = self._mock_backend(tree=uia_tree)
        with patch("naturo.cascade._build._get_cascade_pkg") as mock_pkg:
            mock_pkg.return_value._get_hwnd_children_with_class.return_value = []
            tree, stats = build_hybrid_tree(backend, hwnd=1234)
        assert tree is not None
        assert tree.name == "root"
        assert any(p.name == "uia" and p.status == "ok" for p in stats.providers)

    def test_win32_children_with_cdp(self):
        """Chrome child HWNDs trigger CDP enrichment."""
        uia_tree = _el("root", role="Window", x=0, y=0, w=800, h=600, children=[
            _el("pane", role="Pane", x=0, y=0, w=800, h=600),
        ])
        cdp_el = _el("div", role="div", x=10, y=10, w=100, h=50)

        backend = self._mock_backend(tree=uia_tree)
        with patch("naturo.cascade._build._get_cascade_pkg") as mock_pkg:
            pkg = mock_pkg.return_value
            pkg._get_hwnd_children_with_class.return_value = [
                (5678, "Chrome_RenderWidgetHostHWND", "", (0, 0, 800, 600)),
            ]
            pkg._try_cdp_for_hwnd.return_value = [cdp_el]
            tree, stats = build_hybrid_tree(backend, hwnd=1234)

        assert tree is not None
        assert stats.total_elements >= 2  # root + at least the CDP element


# ── run_cascade ──────────────────────────────────────────────────────────────

class TestRunCascade:

    def _mock_backend(self, tree: ElementInfo | None = None):
        backend = MagicMock()
        backend.get_element_tree.return_value = tree
        return backend

    def test_returns_cascade_result(self):
        """run_cascade always returns a CascadeResult."""
        uia_tree = _el("root", role="Window", x=0, y=0, w=800, h=600, children=[
            _el("btn", x=10, y=10, w=80, h=30),
        ])
        backend = self._mock_backend(tree=uia_tree)
        with patch("naturo.cascade._run._get_cascade_pkg") as mock_pkg:
            mock_pkg.return_value.find_cdp_port.return_value = None
            result = run_cascade(backend, backend_name="uia")
        assert isinstance(result, CascadeResult)
        assert result.tree is not None

    def test_auto_mode_tries_uia_first(self):
        """auto mode starts with UIA provider."""
        uia_tree = _el("root", role="Window", x=0, y=0, w=800, h=600, children=[
            _el("btn", x=10, y=10, w=80, h=30),
        ])
        backend = self._mock_backend(tree=uia_tree)
        with patch("naturo.cascade._run._get_cascade_pkg") as mock_pkg:
            mock_pkg.return_value.find_cdp_port.return_value = None
            result = run_cascade(backend, backend_name="auto")
        assert result.primary_provider == "uia"
        assert any(p.name == "uia" for p in result.stats.providers)

    def test_null_tree_records_stats(self):
        """When backend returns None, stats record the skip."""
        backend = self._mock_backend(tree=None)
        with patch("naturo.cascade._run._get_cascade_pkg") as mock_pkg:
            mock_pkg.return_value.find_cdp_port.return_value = None
            result = run_cascade(backend, backend_name="uia")
        assert result.tree is None
        assert any(p.status == "skipped" for p in result.stats.providers)

    def test_backend_exception_recorded(self):
        """Backend exceptions are caught and recorded."""
        backend = MagicMock()
        backend.get_element_tree.side_effect = RuntimeError("UIA failed")
        with patch("naturo.cascade._run._get_cascade_pkg") as mock_pkg:
            mock_pkg.return_value.find_cdp_port.return_value = None
            result = run_cascade(backend, backend_name="uia")
        assert result.tree is None
        assert any(p.status == "error" for p in result.stats.providers)

    def test_hybrid_mode_delegates(self):
        """hybrid mode calls build_hybrid_tree."""
        uia_tree = _el("root", role="Window", x=0, y=0, w=800, h=600, children=[
            _el("btn", x=10, y=10, w=80, h=30),
        ])
        backend = MagicMock()
        backend._resolve_hwnd.return_value = 1234
        with patch("naturo.cascade._run._get_cascade_pkg") as mock_pkg:
            from naturo.cascade._types import CascadeStats
            mock_pkg.return_value.build_hybrid_tree.return_value = (uia_tree, CascadeStats())
            result = run_cascade(backend, backend_name="hybrid")
        assert result.primary_provider == "hybrid"

    def test_cdp_mode_delegates(self):
        """cdp mode calls _run_cdp_only."""
        backend = MagicMock()
        with patch("naturo.cascade._run._get_cascade_pkg") as mock_pkg:
            mock_pkg.return_value.find_cdp_port.return_value = None
            result = run_cascade(backend, backend_name="cdp")
        assert result.primary_provider == "cdp"

    def test_empty_tree_continues_to_next_provider(self):
        """A root-only tree (0 children) triggers next provider attempt."""
        root_only = _el("root", role="Window", x=0, y=0, w=800, h=600)
        full_tree = _el("root2", role="Window", x=0, y=0, w=800, h=600, children=[
            _el("btn", x=10, y=10, w=80, h=30),
        ])
        backend = MagicMock()
        backend.get_element_tree.side_effect = [root_only, full_tree, None, None]
        with patch("naturo.cascade._run._get_cascade_pkg") as mock_pkg:
            mock_pkg.return_value.find_cdp_port.return_value = None
            result = run_cascade(backend, backend_name="auto")
        assert result.tree is not None
        # First provider should be recorded as empty_tree
        assert any(p.status == "empty_tree" for p in result.stats.providers)


# ── _run_cdp_only ────────────────────────────────────────────────────────────

class TestRunCDPOnly:

    def test_no_debug_port_returns_error(self):
        """When no CDP port found, returns error stats."""
        backend = MagicMock()
        with patch("naturo.cascade._run._get_cascade_pkg") as mock_pkg:
            mock_pkg.return_value.find_cdp_port.return_value = None
            result = _run_cdp_only(backend, hwnd=1234)
        assert result.primary_provider == "cdp"
        assert any(p.name == "cdp" and p.status == "error" for p in result.stats.providers)

    def test_with_cdp_elements(self):
        """When CDP returns elements, they're included in the result."""
        uia_tree = _el("root", role="Window", x=0, y=0, w=800, h=600)
        cdp_el = _el("div", role="div", x=10, y=10, w=100, h=50)

        backend = MagicMock()
        backend.get_element_tree.return_value = uia_tree

        with patch("naturo.cascade._run._get_cascade_pkg") as mock_pkg:
            pkg = mock_pkg.return_value
            pkg.find_cdp_port.return_value = 9222
            pkg._fetch_cdp_elements.return_value = [cdp_el]
            result = _run_cdp_only(backend, hwnd=1234, pid=5678)

        assert result.tree is not None
        assert len(result.tree.children) >= 1
        assert any(p.name == "cdp" and p.status == "ok" for p in result.stats.providers)

    def test_cdp_without_uia_creates_synthetic_root(self):
        """When no UIA tree, CDP creates a synthetic root."""
        cdp_el = _el("div", role="div", x=10, y=10, w=100, h=50)

        backend = MagicMock()
        backend.get_element_tree.return_value = None

        with patch("naturo.cascade._run._get_cascade_pkg") as mock_pkg:
            pkg = mock_pkg.return_value
            pkg.find_cdp_port.return_value = 9222
            pkg._fetch_cdp_elements.return_value = [cdp_el]
            result = _run_cdp_only(backend, app="chrome", hwnd=1234)

        assert result.tree is not None
        assert result.tree.role == "Window"
        assert len(result.tree.children) >= 1
