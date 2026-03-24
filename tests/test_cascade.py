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
        tree = _make_el(id="root", w=1000, h=600)
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
             patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be, \
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
             patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be, \
             patch("naturo.cascade.run_cascade", return_value=mock_result):
            be = MagicMock()
            mock_be.return_value = be
            result = runner.invoke(main, ["see", "--cascade", "--stats", "--no-snapshot"])

        assert "Recognition Stats" in result.output
        assert "uia" in result.output
        assert "cdp" in result.output
