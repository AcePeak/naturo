"""Tests for naturo.cli.core._see — see command.

Tests cover app-id resolution, depth validation, platform checks,
cascade mode, multi-window merge, JSON/text output, snapshot storage,
display ref mapping, annotated screenshots, visible-only filtering,
selectors, cascade stats, and error paths. All mock-based, CI-safe.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from click.testing import CliRunner

from naturo.cli.core._see import see


# ── Helpers ────────────────────────────────────────────────────────────


@dataclass
class FakeElementInfo:
    """Lightweight stand-in for backends.base.ElementInfo."""
    id: str = "root"
    role: str = "Window"
    name: str = "Test Window"
    value: Optional[str] = None
    x: int = 0
    y: int = 0
    width: int = 1920
    height: int = 1080
    children: list = field(default_factory=list)
    properties: dict = field(default_factory=dict)


@dataclass
class FakeCaptureResult:
    path: str = "/tmp/test.png"
    width: int = 1920
    height: int = 1080
    format: str = "png"
    scale_factor: float = 1.0
    dpi: int = 96


@dataclass
class FakeProviderStat:
    name: str = "UIA"
    elements: int = 42
    elapsed_ms: float = 120.0
    status: str = "ok"


@dataclass
class FakeCascadeStats:
    total_elements: int = 42
    coverage_estimate: float = 0.85
    providers: list = field(default_factory=lambda: [FakeProviderStat()])

    def to_dict(self):
        return {
            "total_elements": self.total_elements,
            "coverage_estimate": self.coverage_estimate,
            "providers": [
                {"name": p.name, "elements": p.elements,
                 "elapsed_ms": p.elapsed_ms, "status": p.status}
                for p in self.providers
            ],
        }


@dataclass
class FakeCascadeResult:
    tree: FakeElementInfo = field(default_factory=FakeElementInfo)
    stats: FakeCascadeStats = field(default_factory=FakeCascadeStats)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    tree = FakeElementInfo(
        id="root",
        role="Window",
        name="Test Window",
        x=0, y=0, width=1920, height=1080,
        children=[
            FakeElementInfo(
                id="btn1",
                role="Button",
                name="OK",
                x=100, y=200, width=80, height=30,
            ),
            FakeElementInfo(
                id="edit1",
                role="Edit",
                name="Input",
                value="Hello world",
                x=100, y=100, width=200, height=30,
            ),
        ],
    )
    backend.get_element_tree.return_value = tree
    backend.capture_screen.return_value = FakeCaptureResult()
    backend.list_monitors.return_value = [
        MagicMock(scale_factor=1.0, dpi=96),
    ]
    backend.get_dpi_scale.return_value = 1.0
    return backend


def _patch_backend(mock_backend):
    return patch("naturo.cli.core._common._get_backend", return_value=mock_backend)


def _patch_platform(supports=True):
    return patch("naturo.cli.core._common._platform_supports_gui", return_value=supports)


def _patch_snapshot_manager(mgr=None):
    if mgr is None:
        mgr = MagicMock()
        mgr.create_snapshot.return_value = "snap_001"
        snap_obj = MagicMock()
        snap_obj.screenshot_path = None
        snap_obj.ui_map = {}
        snap_obj.to_dict.return_value = {}
        mgr.get_snapshot.return_value = snap_obj
        mgr._snap_dir.return_value = MagicMock(__truediv__=lambda s, x: MagicMock())
    return patch("naturo.snapshot.get_snapshot_manager", return_value=mgr), mgr


def _patch_assign_refs(ref_map=None):
    if ref_map is None:
        ref_map = {"e1234": "root"}
    ui_map = {"root": MagicMock()}

    def fake_assign(tree, cls, element_obj_to_ref=None):
        if element_obj_to_ref is not None:
            element_obj_to_ref[id(tree)] = "e1234"
            for c in tree.children:
                element_obj_to_ref[id(c)] = f"e{abs(hash(c.id)) % 9999}"
        return ui_map, ref_map

    return patch("naturo.refs.assign_stable_refs", side_effect=fake_assign)


# ── Depth validation ───────────────────────────────────────────────────


class TestDepthValidation:

    def test_depth_too_low(self, runner):
        result = runner.invoke(see, ["--depth", "0"], catch_exceptions=False)
        assert result.exit_code == 1
        assert "--depth must be between 1 and 50" in result.output

    def test_depth_too_high(self, runner):
        result = runner.invoke(see, ["--depth", "51"], catch_exceptions=False)
        assert result.exit_code == 1
        assert "--depth must be between 1 and 50" in result.output

    def test_depth_too_low_json(self, runner):
        result = runner.invoke(see, ["--depth", "0", "--json"], catch_exceptions=False)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_depth_too_high_json(self, runner):
        result = runner.invoke(see, ["--depth", "51", "--json"], catch_exceptions=False)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "INVALID_INPUT"


# ── Platform check ─────────────────────────────────────────────────────


class TestPlatformCheck:

    def test_unsupported_platform_text(self, runner):
        with _patch_platform(False):
            result = runner.invoke(see, [], catch_exceptions=False)
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_unsupported_platform_json(self, runner):
        with _patch_platform(False):
            result = runner.invoke(see, ["--json"], catch_exceptions=False)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "PLATFORM_ERROR"


# ── App ID resolution ──────────────────────────────────────────────────


class TestAppIdResolution:

    def test_app_id_not_found_text(self, runner):
        fake_map = MagicMock()
        fake_map.resolve.return_value = None
        with patch("naturo.app_ids.get_app_id_map", return_value=fake_map):
            result = runner.invoke(see, ["--app-id", "a99"], catch_exceptions=False)
        assert result.exit_code == 1
        assert 'App ID "a99" not found' in result.output

    def test_app_id_not_found_json(self, runner):
        fake_map = MagicMock()
        fake_map.resolve.return_value = None
        with patch("naturo.app_ids.get_app_id_map", return_value=fake_map):
            result = runner.invoke(see, ["--app-id", "a99", "--json"], catch_exceptions=False)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "APP_ID_NOT_FOUND"

    def test_app_id_resolved(self, runner, mock_backend):
        fake_map = MagicMock()
        entry = MagicMock(handle=12345, pid=678)
        fake_map.resolve.return_value = entry
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            patch("naturo.app_ids.get_app_id_map", return_value=fake_map),
        ):
            result = runner.invoke(see, [
                "--app-id", "a1", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        # The app-id must resolve to hwnd 12345 and every backend read must
        # target it. Cascade (the default auto backend) competes providers —
        # it reads UIA first, then also probes MSAA to see whether MSAA dwarfs
        # a thin UIA tree (the "MSAA dwarfs UIA" path opaque-UIA apps like
        # charmap rely on) — so get_element_tree may be called more than once;
        # what matters is that each read used the resolved hwnd.
        assert mock_backend.get_element_tree.called
        for call in mock_backend.get_element_tree.call_args_list:
            assert call.kwargs.get("hwnd") == 12345


# ── Basic text output ──────────────────────────────────────────────────


class TestTextOutput:

    def test_basic_tree_output(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, ["--no-snapshot"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "[Window]" in result.output
        assert '"Test Window"' in result.output
        assert "[Button]" in result.output
        assert '"OK"' in result.output
        assert "e1" in result.output

    def test_compact_output_is_lean(self, runner, mock_backend):
        # --compact: eN [role] "name" per line, refs preserved, no per-node
        # bounds/selectors — far fewer tokens for agents/scripts.
        with _patch_platform(), _patch_backend(mock_backend):
            compact = runner.invoke(see, ["--compact", "--no-snapshot"], catch_exceptions=False)
            verbose = runner.invoke(see, ["--no-snapshot"], catch_exceptions=False)
        assert compact.exit_code == 0
        assert 'e1 [Window] "Test Window"' in compact.output
        assert '[Button] "OK"' in compact.output
        assert "e" in compact.output  # refs still present for `naturo click eN`
        # bounds/position suffix "(x,y WxH)" is dropped in compact
        import re
        assert not re.search(r"\(\d+,\d+ \d+x\d+\)", compact.output)
        assert len(compact.output) < len(verbose.output)

    def test_text_preview_for_edit(self, runner, mock_backend):
        """Edit elements should show a value preview line."""
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, ["--no-snapshot"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Hello world" in result.output

    def test_no_window_found(self, runner, mock_backend):
        mock_backend.get_element_tree.return_value = None
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, ["--no-snapshot"], catch_exceptions=False)
        assert result.exit_code == 1
        assert "No window found" in result.output

    def test_no_window_found_json(self, runner, mock_backend):
        mock_backend.get_element_tree.return_value = None
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, ["--no-snapshot", "--json"], catch_exceptions=False)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "WINDOW_NOT_FOUND"

    def test_snapshot_id_shown(self, runner, mock_backend):
        """When snapshots are enabled, the snapshot ID is printed."""
        snap_patch, mgr = _patch_snapshot_manager()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            snap_patch,
            _patch_assign_refs(),
        ):
            result = runner.invoke(see, [], catch_exceptions=False)
        assert result.exit_code == 0
        assert "snap_001" in result.output
        assert "Tip:" in result.output

    def test_selectors_shown_with_flag(self, runner, mock_backend):
        """--selectors flag adds selector URIs to text output."""
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--no-snapshot", "--selectors",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        # Selector URIs contain "app://"
        assert "app://" in result.output


# ── JSON output ────────────────────────────────────────────────────────


class TestJsonOutput:

    def test_basic_json_output(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["role"] == "Window"
        assert data["name"] == "Test Window"
        assert "children" in data
        assert len(data["children"]) == 2
        assert data["dpi_context"]["scale_factor"] == 1.0

    def test_json_contains_selectors(self, runner, mock_backend):
        """JSON output always includes selectors."""
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        assert "selector" in data
        assert "selector" in data["children"][0]

    def test_json_sequential_refs(self, runner, mock_backend):
        """JSON output assigns sequential e1, e2, e3 IDs."""
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        assert data["id"] == "e1"
        assert data["children"][0]["id"] == "e2"
        assert data["children"][1]["id"] == "e3"

    def test_json_parent_ref(self, runner, mock_backend):
        """Children in JSON have parent_ref pointing to parent's display ID."""
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        child = data["children"][0]
        assert child["parent_ref"] == "e1"
        assert child["parent_id"] == "e1"

    def test_json_snapshot_id_included(self, runner, mock_backend):
        snap_patch, mgr = _patch_snapshot_manager()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            snap_patch,
            _patch_assign_refs(),
        ):
            result = runner.invoke(see, ["--json"], catch_exceptions=False)
        data = json.loads(result.output)
        assert data["snapshot_id"] == "snap_001"

    def test_json_value_preview_for_edit(self, runner, mock_backend):
        """Edit/Document elements get value_preview and value_length."""
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        edit_node = data["children"][1]  # The Edit element
        assert edit_node["value_preview"] == "Hello world"
        assert edit_node["value_length"] == 11

    def test_json_automation_id(self, runner, mock_backend):
        """Elements with real AutomationIds expose them."""
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        btn = data["children"][0]
        assert btn["automation_id"] == "btn1"

    def test_json_dpi_context_fallback(self, runner, mock_backend):
        """DPI context falls back gracefully if monitors fail."""
        mock_backend.list_monitors.side_effect = RuntimeError("no monitors")
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        assert data["dpi_context"]["scale_factor"] == 1.0
        assert data["dpi_context"]["dpi"] == 96


# ── Visible-only filtering ─────────────────────────────────────────────


class TestVisibleOnlyFilter:

    def test_visible_only_hides_offscreen_json(self, runner, mock_backend):
        """--visible-only filters out zero-bounds elements in JSON."""
        tree = FakeElementInfo(
            id="root", role="Window", name="Win",
            x=0, y=0, width=1920, height=1080,
            children=[
                FakeElementInfo(
                    id="vis", role="Button", name="Visible",
                    x=100, y=100, width=80, height=30,
                ),
                FakeElementInfo(
                    id="offscreen", role="Button", name="Hidden",
                    x=0, y=0, width=0, height=0,
                ),
            ],
        )
        mock_backend.get_element_tree.return_value = tree
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot", "--visible-only",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        child_names = [c["name"] for c in data["children"]]
        assert "Visible" in child_names
        assert "Hidden" not in child_names

    def test_visible_only_hides_offscreen_text(self, runner, mock_backend):
        """--visible-only skips offscreen elements in text output."""
        tree = FakeElementInfo(
            id="root", role="Window", name="Win",
            x=0, y=0, width=1920, height=1080,
            children=[
                FakeElementInfo(
                    id="vis", role="Button", name="Visible",
                    x=100, y=100, width=80, height=30,
                ),
                FakeElementInfo(
                    id="offscreen", role="Button", name="Hidden",
                    x=0, y=0, width=0, height=0,
                ),
            ],
        )
        mock_backend.get_element_tree.return_value = tree
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--no-snapshot", "--visible-only",
            ], catch_exceptions=False)
        assert "Visible" in result.output
        assert "Hidden" not in result.output

    def test_offscreen_marked_in_json(self, runner, mock_backend):
        """Offscreen elements (without --visible-only) get offscreen=True."""
        tree = FakeElementInfo(
            id="root", role="Window", name="Win",
            x=0, y=0, width=1920, height=1080,
            children=[
                FakeElementInfo(
                    id="off", role="Button", name="Offscreen",
                    x=0, y=0, width=0, height=0,
                ),
            ],
        )
        mock_backend.get_element_tree.return_value = tree
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        off_child = data["children"][0]
        assert off_child["offscreen"] is True

    def test_offscreen_tagged_in_text(self, runner, mock_backend):
        """Offscreen elements show [offscreen] tag in text output."""
        tree = FakeElementInfo(
            id="root", role="Window", name="Win",
            x=0, y=0, width=1920, height=1080,
            children=[
                FakeElementInfo(
                    id="off", role="Button", name="Offscreen",
                    x=0, y=0, width=0, height=0,
                ),
            ],
        )
        mock_backend.get_element_tree.return_value = tree
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, ["--no-snapshot"], catch_exceptions=False)
        assert "[offscreen]" in result.output


# ── Multi-window merge ─────────────────────────────────────────────────


class TestMultiWindowMerge:

    def test_app_without_hwnd_merges_windows(self, runner, mock_backend):
        """When --app is used without --hwnd, multiple windows are merged."""
        mock_backend._resolve_hwnds.return_value = [111, 222]
        win1 = FakeElementInfo(
            id="w1", role="Window", name="Win 1",
            x=0, y=0, width=800, height=600,
        )
        win2 = FakeElementInfo(
            id="w2", role="Window", name="Win 2",
            x=800, y=0, width=800, height=600,
        )
        mock_backend.get_element_tree.side_effect = [win1, win2]
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--app", "TestApp", "--no-snapshot", "--backend", "uia",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Win 1" in result.output
        assert "Win 2" in result.output
        assert "[WindowGroup]" in result.output

    def test_app_no_windows_found(self, runner, mock_backend):
        mock_backend._resolve_hwnds.return_value = []
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--app", "NoSuchApp", "--no-snapshot", "--backend", "uia",
            ], catch_exceptions=False)
        assert result.exit_code == 1
        assert "No windows found" in result.output

    def test_app_all_empty_trees(self, runner, mock_backend):
        mock_backend._resolve_hwnds.return_value = [111, 222]
        mock_backend.get_element_tree.side_effect = [None, None]
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--app", "EmptyApp", "--no-snapshot", "--backend", "uia",
            ], catch_exceptions=False)
        assert result.exit_code == 1
        assert "empty UI trees" in result.output


# ── Cascade mode ───────────────────────────────────────────────────────


class TestCascadeMode:

    def test_cascade_flag_calls_run_cascade(self, runner, mock_backend):
        fake_result = FakeCascadeResult()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            patch("naturo.cascade.run_cascade", return_value=fake_result) as mock_cascade,
        ):
            result = runner.invoke(see, [
                "--cascade", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        mock_cascade.assert_called_once()

    def test_cascade_stats_shown(self, runner, mock_backend):
        fake_result = FakeCascadeResult()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            patch("naturo.cascade.run_cascade", return_value=fake_result),
        ):
            result = runner.invoke(see, [
                "--cascade", "--stats", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Recognition Stats:" in result.output
        assert "42" in result.output
        assert "85.0%" in result.output
        assert "UIA" in result.output

    def test_cascade_json_includes_stats(self, runner, mock_backend):
        fake_result = FakeCascadeResult()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            patch("naturo.cascade.run_cascade", return_value=fake_result),
        ):
            result = runner.invoke(see, [
                "--cascade", "--json", "--no-snapshot",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        assert "cascade_stats" in data
        assert data["cascade_stats"]["total_elements"] == 42

    def test_auto_backend_triggers_cascade(self, runner, mock_backend):
        """--backend auto should trigger cascade path."""
        fake_result = FakeCascadeResult()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            patch("naturo.cascade.run_cascade", return_value=fake_result) as mock_cascade,
        ):
            result = runner.invoke(see, [
                "--backend", "auto", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        mock_cascade.assert_called_once()

    def test_hybrid_backend_triggers_cascade(self, runner, mock_backend):
        """--backend hybrid should trigger cascade path."""
        fake_result = FakeCascadeResult()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            patch("naturo.cascade.run_cascade", return_value=fake_result) as mock_cascade,
        ):
            result = runner.invoke(see, [
                "--backend", "hybrid", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        mock_cascade.assert_called_once()

    def test_cascade_captures_target_window_not_screen(self, runner, mock_backend):
        """#694: cascade screenshot should use capture_window with hwnd, not capture_screen."""
        fake_result = FakeCascadeResult()
        mock_backend.capture_window.return_value = FakeCaptureResult()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            patch("naturo.cascade.run_cascade", return_value=fake_result),
        ):
            result = runner.invoke(see, [
                "--cascade", "--hwnd", "12345", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        # Must use capture_window with the target hwnd, not capture_screen
        mock_backend.capture_window.assert_called_once()
        call_kwargs = mock_backend.capture_window.call_args
        assert call_kwargs.kwargs.get("hwnd") == 12345 or call_kwargs[1].get("hwnd") == 12345

    def test_cascade_resolves_hwnd_from_app(self, runner, mock_backend):
        """#694: when --app is given without --hwnd, resolve hwnd before capturing."""
        fake_result = FakeCascadeResult()
        mock_backend._resolve_hwnd.return_value = 99999
        mock_backend.capture_window.return_value = FakeCaptureResult()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            patch("naturo.cascade.run_cascade", return_value=fake_result),
        ):
            result = runner.invoke(see, [
                "--cascade", "--app", "feishu", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend._resolve_hwnd.assert_called_once()
        mock_backend.capture_window.assert_called_once()
        call_kwargs = mock_backend.capture_window.call_args
        assert call_kwargs.kwargs.get("hwnd") == 99999 or call_kwargs[1].get("hwnd") == 99999

    def test_cascade_capture_fallback_on_resolve_failure(self, runner, mock_backend):
        """#694: if hwnd resolution fails, fall back to capture_screen."""
        fake_result = FakeCascadeResult()
        mock_backend._resolve_hwnd.side_effect = RuntimeError("no window")
        mock_backend.capture_screen.return_value = FakeCaptureResult()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            patch("naturo.cascade.run_cascade", return_value=fake_result),
        ):
            result = runner.invoke(see, [
                "--cascade", "--app", "feishu", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        # Falls back to capture_screen when resolve fails
        mock_backend.capture_screen.assert_called_once()


# ── Error handling ─────────────────────────────────────────────────────


class TestErrorHandling:

    def test_window_not_found_error_text(self, runner, mock_backend):
        from naturo.errors import WindowNotFoundError
        mock_backend.get_element_tree.side_effect = WindowNotFoundError("No such window")
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--no-snapshot", "--backend", "uia",
            ], catch_exceptions=False)
        assert result.exit_code == 1
        assert "No such window" in result.output

    def test_window_not_found_error_json(self, runner, mock_backend):
        from naturo.errors import WindowNotFoundError
        mock_backend.get_element_tree.side_effect = WindowNotFoundError("No such window")
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--no-snapshot", "--json", "--backend", "uia",
            ], catch_exceptions=False)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "WINDOW_NOT_FOUND"

    def test_generic_exception_text(self, runner, mock_backend):
        mock_backend.get_element_tree.side_effect = RuntimeError("boom")
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--no-snapshot", "--backend", "uia",
            ], catch_exceptions=False)
        assert result.exit_code == 1
        assert "boom" in result.output

    def test_generic_exception_json(self, runner, mock_backend):
        mock_backend.get_element_tree.side_effect = RuntimeError("boom")
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--no-snapshot", "--json", "--backend", "uia",
            ], catch_exceptions=False)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["error"]["code"] == "UNKNOWN_ERROR"
        assert "boom" in data["error"]["message"]


# ── Snapshot storage ───────────────────────────────────────────────────


class TestSnapshotStorage:

    def test_snapshot_stores_ref_map(self, runner, mock_backend):
        snap_patch, mgr = _patch_snapshot_manager()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            snap_patch,
            _patch_assign_refs(),
        ):
            result = runner.invoke(see, [], catch_exceptions=False)
        assert result.exit_code == 0
        mgr.store_detection_result.assert_called_once()
        mgr.store_ref_map.assert_called_once()

    def test_snapshot_stores_display_ref_map(self, runner, mock_backend):
        snap_patch, mgr = _patch_snapshot_manager()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            snap_patch,
            _patch_assign_refs(),
        ):
            result = runner.invoke(see, [], catch_exceptions=False)
        assert result.exit_code == 0
        mgr.store_display_ref_map.assert_called_once()

    def test_snapshot_with_path_stores_screenshot(self, runner, mock_backend):
        snap_patch, mgr = _patch_snapshot_manager()
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            snap_patch,
            _patch_assign_refs(),
        ):
            result = runner.invoke(see, [
                "--path", "/tmp/screen.png",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.capture_screen.assert_called_once_with(output_path="/tmp/screen.png")
        mgr.store_screenshot.assert_called_once()

    def test_no_snapshot_skips_storage(self, runner, mock_backend):
        """--no-snapshot should not create a snapshot."""
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, ["--no-snapshot"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Snapshot:" not in result.output


# ── Annotate ───────────────────────────────────────────────────────────


class TestAnnotate:

    def test_annotate_needs_screenshot(self, runner, mock_backend):
        """--annotate without a screenshot warns the user."""
        snap_patch, mgr = _patch_snapshot_manager()
        snap_obj = mgr.get_snapshot.return_value
        snap_obj.screenshot_path = None
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            snap_patch,
            _patch_assign_refs(),
        ):
            result = runner.invoke(see, ["--annotate"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "--annotate requires a screenshot" in result.output

    def test_annotate_with_screenshot(self, runner, mock_backend):
        snap_patch, mgr = _patch_snapshot_manager()
        snap_obj = mgr.get_snapshot.return_value
        snap_obj.screenshot_path = "/tmp/screen.png"
        snap_obj.ui_map = {"e1": MagicMock()}
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            snap_patch,
            _patch_assign_refs(),
            patch("naturo.annotate.annotate_screenshot", return_value="/tmp/annotated.png") as mock_ann,
        ):
            result = runner.invoke(see, ["--annotate"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_ann.assert_called_once()
        assert "Annotated:" in result.output

    def test_annotate_import_error(self, runner, mock_backend):
        """Missing Pillow shows install hint."""
        snap_patch, mgr = _patch_snapshot_manager()
        snap_obj = mgr.get_snapshot.return_value
        snap_obj.screenshot_path = "/tmp/screen.png"
        snap_obj.ui_map = {"e1": MagicMock()}
        with (
            _patch_platform(),
            _patch_backend(mock_backend),
            snap_patch,
            _patch_assign_refs(),
            patch("naturo.annotate.annotate_screenshot", side_effect=ImportError("No Pillow")),
        ):
            result = runner.invoke(see, ["--annotate"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Pillow required" in result.output


# ── Screenshot without snapshot ────────────────────────────────────────


class TestScreenshotWithoutSnapshot:

    def test_path_without_snapshot_captures(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--path", "/tmp/shot.png", "--no-snapshot",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend.capture_screen.assert_called_once()
        assert "Screenshot saved" in result.output


# ── Keyboard shortcut in output ────────────────────────────────────────


class TestKeyboardShortcutOutput:

    def test_json_includes_keyboard_shortcut(self, runner, mock_backend):
        tree = FakeElementInfo(
            id="root", role="Window", name="Win",
            x=0, y=0, width=1920, height=1080,
            children=[
                FakeElementInfo(
                    id="btn", role="Button", name="Save",
                    x=10, y=10, width=80, height=30,
                    properties={"keyboard_shortcut": "Ctrl+S"},
                ),
            ],
        )
        mock_backend.get_element_tree.return_value = tree
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        btn = data["children"][0]
        assert btn["keyboard_shortcut"] == "Ctrl+S"

    def test_json_includes_source(self, runner, mock_backend):
        tree = FakeElementInfo(
            id="root", role="Window", name="Win",
            x=0, y=0, width=1920, height=1080,
            children=[
                FakeElementInfo(
                    id="btn", role="Button", name="Save",
                    x=10, y=10, width=80, height=30,
                    properties={"source": "cdp"},
                ),
            ],
        )
        mock_backend.get_element_tree.return_value = tree
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(see, [
                "--json", "--no-snapshot", "--backend", "uia",
            ], catch_exceptions=False)
        data = json.loads(result.output)
        btn = data["children"][0]
        assert btn["source"] == "cdp"
