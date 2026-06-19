"""Tests for the Windows 11 shell-enumeration warning on empty taskbar/tray reads.

Regression coverage for #916: on Windows 11 the classic Win32 taskbar/tray
toolbars (``MSTaskListWClass`` / ``TrayNotifyWnd`` under ``Shell_TrayWnd``) were
replaced by a XAML shell host that the legacy UI Automation enumeration cannot
read. ``taskbar list`` / ``tray list`` therefore returned an empty result while
reporting ``success: true`` — a silent failure that violates the project's
"never lie" contract. An empty listing on Windows 11 must now carry an explicit
warning (additive ``warning`` key in JSON, a loud stderr note in human mode)
while keeping the existing ``success``/``items``/``count`` envelope and exit
code unchanged.

All tests are mock-based (no DLL/desktop/input) so they run on Linux/macOS CI.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.system import taskbar, tray


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    return MagicMock()


class TestTaskbarWin11Warning:
    """`naturo taskbar list` must warn on an empty Windows 11 result (#916)."""

    def test_json_empty_on_win11_carries_warning(self, runner, mock_backend):
        mock_backend.taskbar_list.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend), \
                patch("naturo.cli.system._taskbar._is_windows_11_or_later", return_value=True):
            result = runner.invoke(taskbar, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # Existing envelope keys are preserved (additive change only).
        assert data["success"] is True
        assert data["items"] == []
        assert data["count"] == 0
        # The new, additive warning explains the silent-empty cause.
        assert "warning" in data
        assert "Windows 11" in data["warning"]

    def test_json_empty_off_win11_has_no_warning(self, runner, mock_backend):
        mock_backend.taskbar_list.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend), \
                patch("naturo.cli.system._taskbar._is_windows_11_or_later", return_value=False):
            result = runner.invoke(taskbar, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 0
        assert "warning" not in data

    def test_json_nonempty_on_win11_has_no_warning(self, runner, mock_backend):
        mock_backend.taskbar_list.return_value = [
            {"name": "Notepad", "is_active": True, "is_pinned": False},
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend), \
                patch("naturo.cli.system._taskbar._is_windows_11_or_later", return_value=True):
            result = runner.invoke(taskbar, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 1
        assert "warning" not in data

    def test_human_empty_on_win11_prints_warning(self, runner, mock_backend):
        mock_backend.taskbar_list.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend), \
                patch("naturo.cli.system._taskbar._is_windows_11_or_later", return_value=True):
            result = runner.invoke(taskbar, ["list"])
        assert result.exit_code == 0
        assert "Warning" in result.output
        assert "Windows 11" in result.output


class TestTrayWin11Warning:
    """`naturo tray list` must warn on an empty Windows 11 result (#916)."""

    def test_json_empty_on_win11_carries_warning(self, runner, mock_backend):
        mock_backend.tray_list.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend), \
                patch("naturo.cli.system._tray._is_windows_11_or_later", return_value=True):
            result = runner.invoke(tray, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["icons"] == []
        assert data["count"] == 0
        assert "warning" in data
        assert "Windows 11" in data["warning"]

    def test_json_empty_off_win11_has_no_warning(self, runner, mock_backend):
        mock_backend.tray_list.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend), \
                patch("naturo.cli.system._tray._is_windows_11_or_later", return_value=False):
            result = runner.invoke(tray, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 0
        assert "warning" not in data

    def test_human_empty_on_win11_prints_warning(self, runner, mock_backend):
        mock_backend.tray_list.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend), \
                patch("naturo.cli.system._tray._is_windows_11_or_later", return_value=True):
            result = runner.invoke(tray, ["list"])
        assert result.exit_code == 0
        assert "Warning" in result.output
        assert "Windows 11" in result.output
