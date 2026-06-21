"""Tests for naturo.cli.core._list — list command group.

Tests cover 'list windows', 'list screens', 'list permissions' subcommands
with mocked backend. All mock-based, CI-safe.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.core._list import list_cmd


@pytest.fixture
def runner():
    return CliRunner()


def _make_window(**overrides):
    """Create a mock window info."""
    w = MagicMock()
    w.handle = overrides.get("handle", 12345)
    w.title = overrides.get("title", "Untitled - Notepad")
    w.process_name = overrides.get("process_name", "notepad.exe")
    w.pid = overrides.get("pid", 5678)
    w.x = overrides.get("x", 100)
    w.y = overrides.get("y", 100)
    w.width = overrides.get("width", 800)
    w.height = overrides.get("height", 600)
    w.is_visible = overrides.get("is_visible", True)
    w.is_minimized = overrides.get("is_minimized", False)
    return w


def _make_monitor(**overrides):
    """Create a mock monitor info."""
    m = MagicMock()
    m.index = overrides.get("index", 0)
    m.name = overrides.get("name", "\\\\.\\DISPLAY1")
    m.model_name = overrides.get("model_name", "DELL U2723QE")
    m.device_path = overrides.get("device_path", "\\\\.\\DISPLAY1")
    m.x = overrides.get("x", 0)
    m.y = overrides.get("y", 0)
    m.width = overrides.get("width", 3840)
    m.height = overrides.get("height", 2160)
    m.is_primary = overrides.get("is_primary", True)
    m.scale_factor = overrides.get("scale_factor", 1.5)
    m.dpi = overrides.get("dpi", 144)
    m.work_area = overrides.get("work_area", {"x": 0, "y": 0, "width": 3840, "height": 2112})
    return m


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.list_windows.return_value = [
        _make_window(handle=1001, title="Notepad", process_name="notepad.exe", pid=100),
        _make_window(handle=1002, title="Calculator", process_name="calc.exe", pid=200),
    ]
    backend.list_monitors.return_value = [
        _make_monitor(index=0, is_primary=True),
        _make_monitor(index=1, is_primary=False, model_name="LG 27UK850"),
    ]
    return backend


def _patch_backend(mock_backend):
    return patch("naturo.cli.core._common._get_backend", return_value=mock_backend)


def _patch_platform(supports=True):
    return patch("naturo.cli.core._common._platform_supports_gui", return_value=supports)


# ── list windows ─────────────────────────────────────────────────────


class TestListWindows:

    def test_lists_windows_json(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend), \
             patch("os.getpid", return_value=99999), patch("os.getppid", return_value=99998):
            result = runner.invoke(list_cmd, ["windows", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert len(data["windows"]) == 2
        assert data["windows"][0]["title"] == "Notepad"
        assert data["windows"][1]["title"] == "Calculator"

    def test_lists_windows_plain(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend), \
             patch("os.getpid", return_value=99999), patch("os.getppid", return_value=99998):
            result = runner.invoke(list_cmd, ["windows"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Notepad" in result.output
        assert "2 windows found" in result.output

    def test_filter_by_app(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend), \
             patch("os.getpid", return_value=99999), patch("os.getppid", return_value=99998):
            result = runner.invoke(list_cmd, ["windows", "--app", "notepad", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["windows"]) == 1
        assert data["windows"][0]["title"] == "Notepad"

    def test_filter_by_pid(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend), \
             patch("os.getpid", return_value=99999), patch("os.getppid", return_value=99998):
            result = runner.invoke(list_cmd, ["windows", "--pid", "200", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["windows"]) == 1
        assert data["windows"][0]["title"] == "Calculator"

    def test_no_windows_found(self, runner, mock_backend):
        mock_backend.list_windows.return_value = []
        with _patch_platform(), _patch_backend(mock_backend), \
             patch("os.getpid", return_value=99999), patch("os.getppid", return_value=99998):
            result = runner.invoke(list_cmd, ["windows"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No windows found" in result.output

    def test_excludes_own_process(self, runner, mock_backend):
        mock_backend.list_windows.return_value = [
            _make_window(pid=42),  # own process
            _make_window(pid=100, title="Other"),
        ]
        with _patch_platform(), _patch_backend(mock_backend), \
             patch("os.getpid", return_value=42), patch("os.getppid", return_value=99998):
            result = runner.invoke(list_cmd, ["windows", "--json"], catch_exceptions=False)
        data = json.loads(result.output)
        assert len(data["windows"]) == 1
        assert data["windows"][0]["title"] == "Other"

    def test_unsupported_platform(self, runner, mock_backend):
        with _patch_platform(supports=False):
            result = runner.invoke(list_cmd, ["windows", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "PLATFORM_ERROR" in result.output


# ── list windows: --app round-trips its own full-path output (#1084) ──


class TestListWindowsAppRoundTrip:
    """The full-path ``process_name`` emitted by ``list windows -j`` must feed
    straight back into ``--app`` and select the same window (#1084).

    Previously ``--app`` matched the query against ``basename(process_name)``
    only, while the JSON output leaked the full absolute path — so an agent
    that discovered a window and fed its reported ``process_name`` back into
    ``--app`` got zero matches (discover→act round-trip broken).
    """

    FULL_PATH = (
        r"C:\Program Files\WindowsApps"
        r"\Microsoft.WindowsTerminal_1.24.11321.0_x64__8wekyb3d8bbwe"
        r"\WindowsTerminal.exe"
    )

    @pytest.fixture
    def path_backend(self):
        backend = MagicMock()
        backend.list_windows.return_value = [
            _make_window(handle=2001, title="claude", process_name=self.FULL_PATH, pid=300),
            _make_window(handle=2002, title="Calculator", process_name="calc.exe", pid=200),
        ]
        return backend

    def _run(self, runner, backend, app_value):
        with _patch_platform(), _patch_backend(backend), \
             patch("os.getpid", return_value=99999), patch("os.getppid", return_value=99998):
            return runner.invoke(
                list_cmd, ["windows", "--app", app_value, "--json"], catch_exceptions=False
            )

    def test_full_path_process_name_round_trips(self, runner, path_backend):
        # The exact value emitted in the JSON must select the same window.
        result = self._run(runner, path_backend, self.FULL_PATH)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 1
        assert data["windows"][0]["handle"] == 2001
        # And the round-tripped value is exactly what the command emitted.
        assert data["windows"][0]["process_name"] == self.FULL_PATH

    def test_basename_still_matches(self, runner, path_backend):
        result = self._run(runner, path_backend, "WindowsTerminal.exe")
        data = json.loads(result.output)
        assert data["count"] == 1
        assert data["windows"][0]["handle"] == 2001

    def test_partial_name_still_matches(self, runner, path_backend):
        result = self._run(runner, path_backend, "terminal")
        data = json.loads(result.output)
        assert data["count"] == 1
        assert data["windows"][0]["handle"] == 2001

    def test_path_query_does_not_overmatch_siblings(self, runner, path_backend):
        # Basenaming the query must NOT broaden to full-path substring matching:
        # a shared directory component (e.g. "WindowsApps") must not pull in
        # unrelated windows the way matching the whole path would (#789).
        result = self._run(runner, path_backend, r"C:\Program Files\WindowsApps")
        data = json.loads(result.output)
        assert data["count"] == 0


# ── list screens ─────────────────────────────────────────────────────


class TestListScreens:

    def test_lists_monitors_json(self, runner, mock_backend):
        with _patch_backend(mock_backend):
            result = runner.invoke(list_cmd, ["screens", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert len(data["monitors"]) == 2
        assert data["monitors"][0]["name"] == "DELL U2723QE"
        assert data["monitors"][0]["is_primary"] is True
        assert data["monitors"][0]["dpi"] == 144

    def test_lists_monitors_plain(self, runner, mock_backend):
        with _patch_backend(mock_backend):
            result = runner.invoke(list_cmd, ["screens"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "DELL U2723QE" in result.output

    def test_not_implemented(self, runner, mock_backend):
        mock_backend.list_monitors.side_effect = NotImplementedError
        with _patch_backend(mock_backend):
            result = runner.invoke(list_cmd, ["screens", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "NOT_IMPLEMENTED" in result.output

    def test_no_monitors(self, runner, mock_backend):
        mock_backend.list_monitors.return_value = []
        with _patch_backend(mock_backend):
            result = runner.invoke(list_cmd, ["screens"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "No monitors detected" in result.output


# ── list permissions ─────────────────────────────────────────────────


class TestListPermissions:

    def test_not_implemented(self, runner, mock_backend):
        result = runner.invoke(list_cmd, ["permissions", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "NOT_IMPLEMENTED" in result.output
