"""Tests for issue #140 — Cascading recognition engine.

Verifies:
- run_cascade() falls back to single provider when no cascade flags
- run_cascade() with backend='auto' tries providers in order
- Source tagging on elements
- CascadeStats accumulate per-provider stats
- Coverage estimation helpers
- CDP provider is attempted when Electron debug port available
- AI vision provider is attempted when fill_gaps_ai=True
- CLI: --cascade flag passes through correctly
- CLI: --stats flag shows provider breakdown
- CLI: element output includes [source] tag in text mode
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner

from naturo.backends.base import ElementInfo
from naturo.cascade import (
    CascadeStats,
    CascadeResult,
    ProviderStat,
    _estimate_coverage,
    _flatten,
    _rect_area,
    _tag_source,
    _detect_backend_for_class,
    _find_node_by_bounds,
    build_hybrid_tree,
    run_cascade,
)
from naturo.cli import main


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_el(
    id: str = "e1",
    role: str = "Button",
    name: str = "OK",
    x: int = 0, y: int = 0, w: int = 100, h: int = 30,
    children=None,
    props=None,
) -> ElementInfo:
    return ElementInfo(
        id=id, role=role, name=name, value=None,
        x=x, y=y, width=w, height=h,
        children=children or [],
        properties=props or {},
    )


def _make_backend(tree: Optional[ElementInfo]) -> MagicMock:
    """Create a mock backend that returns *tree* from get_element_tree."""
    be = MagicMock()
    be.get_element_tree.return_value = tree
    return be


# ── Coverage helpers ──────────────────────────────────────────────────────────


class TestCoverageHelpers:
    def test_rect_area(self):
        assert _rect_area(0, 0, 100, 50) == 5000
        assert _rect_area(0, 0, 0, 50) == 0
        assert _rect_area(0, 0, -5, 50) == 0

    def test_estimate_coverage_full(self):
        # Element covers entire window
        window = _make_el(x=0, y=0, w=1000, h=600)
        flat = [_make_el(x=0, y=0, w=1000, h=600)]
        coverage = _estimate_coverage(flat, 1000 * 600)
        assert coverage == 1.0

    def test_estimate_coverage_partial(self):
        flat = [_make_el(x=0, y=0, w=500, h=600)]
        coverage = _estimate_coverage(flat, 1000 * 600)
        assert coverage == pytest.approx(0.5)

    def test_estimate_coverage_zero_window(self):
        flat = [_make_el(x=0, y=0, w=100, h=100)]
        coverage = _estimate_coverage(flat, 0)
        assert coverage == 0.0

    def test_estimate_coverage_empty_elements(self):
        coverage = _estimate_coverage([], 10000)
        assert coverage == 0.0


# ── _tag_source ───────────────────────────────────────────────────────────────


class TestTagSource:
    def test_adds_source_to_element(self):
        el = _make_el()
        tagged = _tag_source(el, "uia")
        assert tagged.properties.get("source") == "uia"

    def test_source_propagates_to_children(self):
        child = _make_el(id="child")
        parent = _make_el(id="parent", children=[child])
        tagged = _tag_source(parent, "cdp")
        assert tagged.properties["source"] == "cdp"
        assert tagged.children[0].properties["source"] == "cdp"

    def test_original_element_unchanged(self):
        el = _make_el()
        _tag_source(el, "uia")
        assert "source" not in el.properties  # original not mutated


# ── _flatten ─────────────────────────────────────────────────────────────────


class TestFlatten:
    def test_single_element(self):
        el = _make_el()
        assert _flatten(el) == [el]

    def test_nested_elements(self):
        c1 = _make_el(id="c1")
        c2 = _make_el(id="c2")
        parent = _make_el(id="root", children=[c1, c2])
        flat = _flatten(parent)
        assert len(flat) == 3
        assert flat[0].id == "root"


# ── run_cascade ───────────────────────────────────────────────────────────────


class TestRunCascade:
    def test_single_provider_uia(self):
        tree = _make_el(id="root", w=1000, h=600, children=[_make_el(id="btn")])
        be = _make_backend(tree)

        result = run_cascade(be, backend_name="uia")

        assert result.tree is not None
        assert result.tree.id == "root"
        be.get_element_tree.assert_called_once()

    def test_source_tagged_on_result(self):
        tree = _make_el(id="root")
        be = _make_backend(tree)

        result = run_cascade(be, backend_name="uia")

        assert result.tree.properties.get("source") == "uia"

    def test_stats_recorded(self):
        tree = _make_el(
            id="root", w=1000, h=600,
            children=[_make_el(id="btn")],
        )
        be = _make_backend(tree)

        result = run_cascade(be, backend_name="uia")

        assert len(result.stats.providers) >= 1
        uia_stat = next(p for p in result.stats.providers if p.name == "uia")
        assert uia_stat.status == "ok"
        assert uia_stat.elements >= 1

    def test_no_tree_returns_none(self):
        be = _make_backend(None)

        result = run_cascade(be, backend_name="uia")

        assert result.tree is None

    def test_auto_backend_tries_multiple(self):
        # First provider (uia) returns None, second (msaa) returns tree
        tree = _make_el(id="root")
        call_count = [0]

        def get_tree(*args, **kwargs):
            b = kwargs.get("backend", "uia")
            call_count[0] += 1
            if b == "msaa":
                return tree
            return None

        be = MagicMock()
        be.get_element_tree.side_effect = get_tree

        result = run_cascade(be, backend_name="auto")

        assert result.tree is not None
        assert call_count[0] >= 2  # tried at least uia and msaa

    def test_auto_skips_empty_tree_provider(self):
        """When a provider returns root-only tree (0 children), cascade should
        continue to next provider instead of stopping (#394)."""
        empty_root = _make_el(id="root", role="Pane", name="", children=[])
        rich_tree = _make_el(
            id="root", role="Window", name="Calculator",
            children=[_make_el(id="btn", role="Button", name="1")],
        )

        call_count = [0]

        def get_tree(*args, **kwargs):
            b = kwargs.get("backend", "uia")
            call_count[0] += 1
            if b == "uia":
                return empty_root
            if b == "msaa":
                return rich_tree
            return None

        be = MagicMock()
        be.get_element_tree.side_effect = get_tree

        result = run_cascade(be, backend_name="auto")

        assert result.tree is not None
        assert len(result.tree.children) == 1
        assert call_count[0] >= 2
        # Check that UIA was recorded as empty_tree
        uia_stat = next(p for p in result.stats.providers if p.name == "uia")
        assert uia_stat.status == "empty_tree"

    def test_empty_tree_kept_as_fallback_when_no_provider_works(self):
        """When all providers return empty trees, keep the first one as fallback."""
        empty_root = _make_el(id="root", role="Pane", name="", children=[])

        be = MagicMock()
        be.get_element_tree.return_value = empty_root

        result = run_cascade(be, backend_name="auto")

        # Should still return the root (as fallback), not None
        assert result.tree is not None
        assert result.tree.children == []

    def test_stats_to_dict(self):
        tree = _make_el(id="root", w=1000, h=600)
        be = _make_backend(tree)

        result = run_cascade(be, backend_name="uia")
        d = result.stats.to_dict()

        assert "providers" in d
        assert "total_elements" in d
        assert "coverage_estimate" in d

    def test_cdp_skipped_when_no_cascade(self):
        """CDP should not be tried when backend_name='uia' and cascade=False (coverage_target=0)."""
        tree = _make_el(id="root")
        be = _make_backend(tree)

        with patch("naturo.cascade._fetch_cdp_elements") as mock_cdp:
            result = run_cascade(be, backend_name="uia", coverage_target=0.0)

        # CDP fetch should not be called when coverage_target=0 and not auto
        mock_cdp.assert_not_called()

    def test_cdp_attempted_when_auto(self):
        """When backend='auto', CDP detection is always attempted."""
        tree = _make_el(id="root", w=1000, h=600)
        be = _make_backend(tree)

        with patch("naturo.cascade._fetch_cdp_elements", return_value=[]) as mock_cdp, \
             patch("naturo.cascade.get_debug_port", return_value=9222, create=True):
            # Suppress the actual electron import
            with patch.dict("sys.modules", {"naturo.electron": MagicMock(get_debug_port=lambda p: 9222)}):
                result = run_cascade(be, backend_name="auto", pid=1234)

        # CDP path was entered (no exception)
        assert result.tree is not None

    def test_ai_fill_gaps_skipped_without_screenshot(self):
        """AI vision not attempted when no screenshot_path provided."""
        tree = _make_el(id="root")
        be = _make_backend(tree)

        with patch("naturo.cascade._fetch_ai_elements") as mock_ai:
            run_cascade(be, backend_name="uia", fill_gaps_ai=True, screenshot_path=None)

        mock_ai.assert_not_called()

    def test_ai_fill_gaps_with_screenshot(self, tmp_path):
        """AI vision attempted when fill_gaps_ai=True and screenshot_path provided."""
        tree = _make_el(id="root", w=1000, h=600)
        be = _make_backend(tree)

        fake_screenshot = str(tmp_path / "screen.png")
        Path(fake_screenshot).write_bytes(b"fake")

        ai_el = _make_el(id="ai_0", role="Button", name="AI Button", x=100, y=200, w=80, h=30,
                         props={"source": "vision"})

        with patch("naturo.cascade._fetch_ai_elements", return_value=[ai_el]) as mock_ai:
            result = run_cascade(
                be, backend_name="uia",
                fill_gaps_ai=True,
                screenshot_path=fake_screenshot,
            )

        mock_ai.assert_called_once()
        vision_stat = next((p for p in result.stats.providers if p.name == "vision"), None)
        assert vision_stat is not None
        assert vision_stat.elements == 1
        assert vision_stat.status == "ok"


# ── CLI integration ───────────────────────────────────────────────────────────


class TestSeeCascadeCLI:
    """Test --cascade and --stats flags via CLI."""

    def _run_see(self, args, platform="Darwin"):
        runner = CliRunner()
        with patch("platform.system", return_value=platform), \
             patch("shutil.which", return_value="/usr/local/bin/peekaboo"):
            result = runner.invoke(main, ["see"] + args)
        return result

    def test_cascade_flag_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["see", "--help"])
        assert "--cascade" in result.output

    def test_fill_gaps_flag_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["see", "--help"])
        assert "--fill-gaps" in result.output

    def test_stats_flag_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["see", "--help"])
        assert "--stats" in result.output

    def test_coverage_flag_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["see", "--help"])
        assert "--coverage" in result.output

    def test_cascade_invokes_run_cascade(self):
        """When --cascade is passed, run_cascade() is called."""
        el = _make_el(id="root", role="Window", w=1200, h=800)
        mock_tree = el

        from naturo.cascade import CascadeResult, CascadeStats
        mock_result = CascadeResult(
            tree=mock_tree,
            stats=CascadeStats(providers=[ProviderStat(name="uia", elements=1)]),
        )

        runner = CliRunner()
        with patch("platform.system", return_value="Windows"), \
             patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend") as mock_be, \
             patch("naturo.cascade.run_cascade", return_value=mock_result) as mock_cascade:
            be = MagicMock()
            mock_be.return_value = be
            result = runner.invoke(main, ["see", "--cascade", "--no-snapshot"])

        mock_cascade.assert_called_once()

    def test_stats_shown_in_text_mode(self):
        """--stats adds a recognition stats block to text output."""
        el = _make_el(id="root", role="Window", w=1200, h=800)

        from naturo.cascade import CascadeResult, CascadeStats
        mock_result = CascadeResult(
            tree=el,
            stats=CascadeStats(
                providers=[
                    ProviderStat(name="uia", elements=5, elapsed_ms=12.3, status="ok"),
                    ProviderStat(name="cdp", elements=20, elapsed_ms=380.0, status="ok"),
                ],
                total_elements=25,
                coverage_estimate=0.82,
            ),
        )

        runner = CliRunner()
        with patch("platform.system", return_value="Windows"), \
             patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend") as mock_be, \
             patch("naturo.cascade.run_cascade", return_value=mock_result):
            be = MagicMock()
            mock_be.return_value = be
            result = runner.invoke(main, ["see", "--cascade", "--stats", "--no-snapshot"])

        assert "Recognition Stats" in result.output
        assert "uia" in result.output
        assert "cdp" in result.output


# ── Hybrid tree: _detect_backend_for_class ───────────────────────────────────


class TestDetectBackendForClass:
    def test_chrome_render_widget(self):
        assert _detect_backend_for_class("Chrome_RenderWidgetHostHWND") == "cdp"

    def test_chrome_widget_win(self):
        assert _detect_backend_for_class("Chrome_WidgetWin_0") == "cdp"

    def test_java_frame(self):
        assert _detect_backend_for_class("SunAwtFrame") == "jab"

    def test_java_dialog(self):
        assert _detect_backend_for_class("SunAwtDialog") == "jab"

    def test_java_prefixed(self):
        assert _detect_backend_for_class("javax.swing.JFrame") == "jab"

    def test_mozilla_window(self):
        assert _detect_backend_for_class("MozillaWindowClass") == "ia2"

    def test_regular_class_defaults_to_uia(self):
        assert _detect_backend_for_class("Edit") == "uia"
        assert _detect_backend_for_class("Button") == "uia"
        assert _detect_backend_for_class("") == "uia"

    def test_unknown_class_defaults_to_uia(self):
        assert _detect_backend_for_class("CustomVB6Control42") == "uia"


# ── Hybrid tree: _find_node_by_bounds ────────────────────────────────────────


class TestFindNodeByBounds:
    def test_finds_exact_match(self):
        child = _make_el(id="child", x=100, y=100, w=200, h=150)
        root = _make_el(id="root", x=0, y=0, w=1000, h=600, children=[child])

        found = _find_node_by_bounds(root, 100, 100, 200, 150)
        assert found is not None
        assert found.id == "child"

    def test_prefers_deeper_match(self):
        grandchild = _make_el(id="gc", x=100, y=100, w=200, h=150)
        child = _make_el(id="child", x=50, y=50, w=400, h=300, children=[grandchild])
        root = _make_el(id="root", x=0, y=0, w=1000, h=600, children=[child])

        found = _find_node_by_bounds(root, 100, 100, 200, 150)
        assert found is not None
        assert found.id == "gc"

    def test_returns_none_for_zero_area(self):
        root = _make_el(id="root", x=0, y=0, w=1000, h=600)
        assert _find_node_by_bounds(root, 0, 0, 0, 0) is None

    def test_returns_none_when_no_overlap(self):
        child = _make_el(id="child", x=0, y=0, w=100, h=100)
        root = _make_el(id="root", x=0, y=0, w=1000, h=600, children=[child])

        # Target is far away from any node
        found = _find_node_by_bounds(root, 900, 500, 50, 50)
        # Root should still match since it contains the target
        assert found is not None
        assert found.id == "root"

    def test_overlap_threshold(self):
        """Node must overlap >= 50% of target area to match."""
        child = _make_el(id="child", x=0, y=0, w=100, h=100)
        root = _make_el(id="root", x=0, y=0, w=1000, h=600, children=[child])

        # Only small overlap with child (10x100 = 1000 out of 200x100 = 20000 = 5%)
        found = _find_node_by_bounds(root, 90, 0, 200, 100)
        # Root covers it, child does not (overlap < 50%)
        assert found is not None
        assert found.id == "root"


# ── Hybrid tree: build_hybrid_tree ───────────────────────────────────────────


class TestBuildHybridTree:
    def test_uia_only_when_no_win32_children(self):
        """When no Win32 child HWNDs exist, returns the UIA tree as-is."""
        uia_tree = _make_el(
            id="root", role="Window", name="Notepad", w=800, h=600,
            children=[_make_el(id="btn", role="Button", name="Save")],
        )
        be = MagicMock()
        be.get_element_tree.return_value = uia_tree

        with patch("naturo.cascade._get_hwnd_children_with_class", return_value=[]):
            tree, stats = build_hybrid_tree(be, hwnd=12345, depth=3)

        assert tree is not None
        assert tree.properties.get("source") == "uia"
        assert len(tree.children) == 1
        assert tree.children[0].properties.get("source") == "uia"

    def test_uia_failure_returns_none(self):
        """When UIA fails, returns None."""
        be = MagicMock()
        be.get_element_tree.side_effect = Exception("COM error")

        tree, stats = build_hybrid_tree(be, hwnd=12345, depth=3)

        assert tree is None
        assert any(p.status == "error" for p in stats.providers)

    def test_jab_enrichment_for_java_hwnd(self):
        """Java HWND detected → JAB subtree attached to matching UIA node."""
        uia_tree = _make_el(
            id="root", role="Window", name="Eclipse", x=0, y=0, w=1000, h=600,
            children=[
                _make_el(id="pane", role="Pane", name="", x=100, y=100, w=800, h=400),
            ],
        )

        jab_child1 = _make_el(id="jc1", role="PushButton", name="Run")
        jab_child2 = _make_el(id="jc2", role="PushButton", name="Debug")
        jab_tree = _make_el(
            id="jab_root", role="Panel", name="Toolbar",
            children=[jab_child1, jab_child2],
        )

        def get_tree_side_effect(**kwargs):
            backend = kwargs.get("backend", "uia")
            if backend == "uia":
                return uia_tree
            if backend == "jab":
                return jab_tree
            return None

        be = MagicMock()
        be.get_element_tree.side_effect = get_tree_side_effect

        java_children = [
            (99001, "SunAwtFrame", "Eclipse", (100, 100, 800, 400)),
        ]
        with patch("naturo.cascade._get_hwnd_children_with_class", return_value=java_children):
            tree, stats = build_hybrid_tree(be, hwnd=12345, depth=3)

        assert tree is not None
        # The pane node should now have JAB children attached
        pane = tree.children[0]
        jab_children = [c for c in pane.children if c.properties.get("source") == "jab"]
        assert len(jab_children) == 2
        assert jab_children[0].name == "Run"
        assert jab_children[1].name == "Debug"

    def test_ia2_enrichment_for_mozilla_hwnd(self):
        """Mozilla HWND detected → IA2 subtree attached."""
        uia_tree = _make_el(
            id="root", role="Window", name="Firefox", x=0, y=0, w=1200, h=800,
            children=[
                _make_el(id="moz", role="Pane", name="", x=0, y=50, w=1200, h=750),
            ],
        )

        ia2_child = _make_el(id="ia2_doc", role="Document", name="Web Page")
        ia2_tree = _make_el(
            id="ia2_root", role="Application", name="Firefox",
            children=[ia2_child],
        )

        def get_tree_side_effect(**kwargs):
            if kwargs.get("backend") == "ia2":
                return ia2_tree
            return uia_tree

        be = MagicMock()
        be.get_element_tree.side_effect = get_tree_side_effect

        moz_children = [
            (88001, "MozillaWindowClass", "Firefox", (0, 50, 1200, 750)),
        ]
        with patch("naturo.cascade._get_hwnd_children_with_class", return_value=moz_children):
            tree, stats = build_hybrid_tree(be, hwnd=12345, depth=3)

        assert tree is not None
        moz_node = tree.children[0]
        ia2_children = [c for c in moz_node.children if c.properties.get("source") == "ia2"]
        assert len(ia2_children) == 1
        assert ia2_children[0].name == "Web Page"

    def test_cdp_enrichment_for_electron_hwnd(self):
        """Chrome_RenderWidgetHostHWND → CDP elements attached."""
        uia_tree = _make_el(
            id="root", role="Window", name="Feishu", x=0, y=0, w=1200, h=800,
            children=[
                _make_el(id="chrome", role="Pane", name="", x=50, y=50, w=1100, h=700),
            ],
        )

        cdp_nav = _make_el(id="cdp_0", role="Link", name="Messages",
                           x=60, y=100, w=100, h=30, props={"source": "cdp"})

        be = MagicMock()
        be.get_element_tree.return_value = uia_tree

        electron_children = [
            (77001, "Chrome_RenderWidgetHostHWND", "", (50, 50, 1100, 700)),
        ]
        with patch("naturo.cascade._get_hwnd_children_with_class", return_value=electron_children), \
             patch("naturo.cascade._try_cdp_for_hwnd", return_value=[cdp_nav]):
            tree, stats = build_hybrid_tree(be, hwnd=12345, depth=3, pid=9999)

        assert tree is not None
        chrome_node = tree.children[0]
        cdp_children = [c for c in chrome_node.children if c.properties.get("source") == "cdp"]
        assert len(cdp_children) == 1
        assert cdp_children[0].name == "Messages"

    def test_uia_class_skipped_in_enrichment(self):
        """Regular Win32 classes (mapped to UIA) are skipped — UIA tree already covers them."""
        uia_tree = _make_el(
            id="root", role="Window", name="Notepad", x=0, y=0, w=800, h=600,
            children=[_make_el(id="edit", role="Edit", name="", x=0, y=30, w=800, h=570)],
        )

        be = MagicMock()
        be.get_element_tree.return_value = uia_tree

        # Regular Edit class → should be "uia" → skipped in enrichment
        win32_children = [
            (55001, "Edit", "", (0, 30, 800, 570)),
        ]
        with patch("naturo.cascade._get_hwnd_children_with_class", return_value=win32_children):
            tree, stats = build_hybrid_tree(be, hwnd=12345, depth=3)

        assert tree is not None
        # Only one child (the UIA Edit), nothing added
        assert len(tree.children) == 1

    def test_stats_include_all_providers(self):
        """Stats should report UIA + win32_scan + any enrichment backends."""
        uia_tree = _make_el(
            id="root", role="Window", name="Test", x=0, y=0, w=1000, h=600,
            children=[_make_el(id="pane", role="Pane", x=100, y=100, w=800, h=400)],
        )

        jab_tree = _make_el(
            id="jab_root", role="Panel", name="Java",
            children=[_make_el(id="jc1", role="PushButton", name="OK")],
        )

        def get_tree_side_effect(**kwargs):
            if kwargs.get("backend") == "jab":
                return jab_tree
            return uia_tree

        be = MagicMock()
        be.get_element_tree.side_effect = get_tree_side_effect

        java_children = [(99001, "SunAwtFrame", "Java App", (100, 100, 800, 400))]
        with patch("naturo.cascade._get_hwnd_children_with_class", return_value=java_children):
            tree, stats = build_hybrid_tree(be, hwnd=12345, depth=3)

        provider_names = [p.name for p in stats.providers]
        assert "uia" in provider_names
        assert "win32_scan" in provider_names
        assert "jab" in provider_names


# ── Hybrid tree: run_cascade with backend="hybrid" ──────────────────────────


class TestRunCascadeHybrid:
    def test_hybrid_backend_routes_to_build_hybrid_tree(self):
        """backend_name='hybrid' should call build_hybrid_tree."""
        uia_tree = _make_el(
            id="root", role="Window", name="Test", w=800, h=600,
            children=[_make_el(id="btn", role="Button", name="OK")],
        )

        be = MagicMock()
        be.get_element_tree.return_value = uia_tree
        be._resolve_hwnd.return_value = 12345

        with patch("naturo.cascade._get_hwnd_children_with_class", return_value=[]):
            result = run_cascade(be, backend_name="hybrid")

        assert result.tree is not None
        assert result.primary_provider == "hybrid"
        assert result.tree.properties.get("source") == "uia"

    def test_hybrid_uses_provided_hwnd(self):
        """When hwnd is provided, hybrid mode uses it directly."""
        uia_tree = _make_el(id="root", role="Window", w=800, h=600)
        be = MagicMock()
        be.get_element_tree.return_value = uia_tree

        with patch("naturo.cascade._get_hwnd_children_with_class", return_value=[]):
            result = run_cascade(be, backend_name="hybrid", hwnd=99999)

        assert result.tree is not None
        # Should NOT have called _resolve_hwnd since hwnd was provided
        be._resolve_hwnd.assert_not_called()

    def test_hybrid_returns_error_on_hwnd_resolution_failure(self):
        """When HWND resolution fails, returns error stats."""
        be = MagicMock()
        be._resolve_hwnd.side_effect = Exception("No window found")

        result = run_cascade(be, backend_name="hybrid", app="nonexistent")

        assert result.tree is None
        assert result.primary_provider == "hybrid"
        assert any(p.status == "error" for p in result.stats.providers)
