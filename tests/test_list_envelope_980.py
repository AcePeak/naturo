"""Tests for #980: ``list windows -j`` and ``list screens -j`` envelope contract.

Sibling of #876 (``selector list`` / ``record list``) and #977 (``visual list`` /
``selector show``). These two ``list`` sub-commands emitted ``success`` plus the
collection but **omitted the top-level ``count``**, while their counterparts
(``window list`` / ``app windows``) already include it:

* ``list windows -j`` -> ``{"success": true, "windows": [...]}``   (no ``count``)
* ``list screens -j`` -> ``{"success": true, "monitors": [...]}``  (no ``count``)

These tests pin the corrected ``{success, <collection>, count}`` envelope. They
are pure CLI/JSON tests: the backend is mocked, so no DLL, desktop session, or
input simulation is required (runs identically on Linux/macOS CI).
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def _parse_json(output: str):
    """Parse the JSON object from CLI output.

    ``list windows`` prints a stderr warning on an empty result, which this
    click version merges into the captured output ahead of the JSON payload.
    The warning text contains no ``{``, so slicing from the first brace yields
    clean, platform-independent JSON.
    """
    return json.loads(output[output.index("{"):])


def _make_window(handle: int, pid: int, title: str):
    """Build a minimal window stand-in with the attributes ``list windows`` reads."""
    return SimpleNamespace(
        handle=handle,
        title=title,
        process_name="C:\\Windows\\notepad.exe",
        pid=pid,
        x=0,
        y=0,
        width=800,
        height=600,
        is_visible=True,
        is_minimized=False,
    )


def _make_monitor(index: int):
    """Build a minimal monitor stand-in with the attributes ``list screens`` reads."""
    return SimpleNamespace(
        index=index,
        name=f"Monitor{index}",
        model_name=f"Dell U{index}",
        device_path=f"\\\\.\\DISPLAY{index}",
        x=0,
        y=0,
        width=1920,
        height=1080,
        is_primary=index == 0,
        scale_factor=1.0,
        dpi=96,
        work_area=None,
    )


# ── list windows -j ───────────────────────────────────────────────────────────


class TestListWindowsEnvelope:
    def test_populated_has_success_windows_and_count(self, runner):
        """A populated window list reports success, the list, and its count."""
        # Use PIDs that cannot collide with this process / its parent (which the
        # command filters out), so the count is deterministic.
        windows = [
            _make_window(1001, 999991, "Doc 1 - Notepad"),
            _make_window(1002, 999992, "Doc 2 - Notepad"),
        ]
        backend = SimpleNamespace(list_windows=lambda: windows)
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(main, ["list", "windows", "-j"])
        assert result.exit_code == 0
        data = _parse_json(result.output)
        assert data["success"] is True
        assert isinstance(data["windows"], list)
        assert len(data["windows"]) == 2
        assert data["count"] == 2

    def test_empty_has_success_and_zero_count(self, runner):
        """An empty window list still emits the standard envelope with count 0."""
        backend = SimpleNamespace(list_windows=lambda: [])
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(main, ["list", "windows", "-j"])
        assert result.exit_code == 0
        data = _parse_json(result.output)
        assert data["success"] is True
        assert data["windows"] == []
        assert data["count"] == 0


# ── list screens -j ───────────────────────────────────────────────────────────


class TestListScreensEnvelope:
    def test_populated_has_success_monitors_and_count(self, runner):
        """A populated monitor list reports success, the list, and its count."""
        monitors = [_make_monitor(0), _make_monitor(1)]
        backend = SimpleNamespace(list_monitors=lambda: monitors)
        with patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(main, ["list", "screens", "-j"])
        assert result.exit_code == 0
        data = _parse_json(result.output)
        assert data["success"] is True
        assert isinstance(data["monitors"], list)
        assert len(data["monitors"]) == 2
        assert data["count"] == 2

    def test_empty_has_success_and_zero_count(self, runner):
        """An empty monitor list still emits the standard envelope with count 0."""
        backend = SimpleNamespace(list_monitors=lambda: [])
        with patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(main, ["list", "screens", "-j"])
        assert result.exit_code == 0
        data = _parse_json(result.output)
        assert data["success"] is True
        assert data["monitors"] == []
        assert data["count"] == 0


# ── text-mode regression guard ────────────────────────────────────────────────


class TestTextModeUnchanged:
    def test_windows_text_mode_count_line_unchanged(self, runner):
        """Human (non-JSON) output keeps its existing trailing count line."""
        windows = [_make_window(1001, 999991, "Doc 1 - Notepad")]
        backend = SimpleNamespace(list_windows=lambda: windows)
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(main, ["list", "windows"])
        assert result.exit_code == 0
        assert "1 windows found." in result.output

    def test_screens_text_mode_count_line_unchanged(self, runner):
        """Human (non-JSON) output keeps its existing trailing count line."""
        monitors = [_make_monitor(0)]
        backend = SimpleNamespace(list_monitors=lambda: monitors)
        with patch("naturo.cli.core._common._get_backend", return_value=backend):
            result = runner.invoke(main, ["list", "screens"])
        assert result.exit_code == 0
        assert "1 monitor(s) found." in result.output
