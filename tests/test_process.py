"""Tests for naturo.process — launch, quit, relaunch, find, is_running."""
import platform
import pytest
from unittest.mock import patch, MagicMock
from naturo.process import (
    ProcessInfo, find_process, is_running, launch_app, quit_app,
    relaunch_app, list_apps, _list_processes,
)
from naturo.errors import AppNotFoundError, TimeoutError


class TestProcessInfo:
    def test_creation(self):
        p = ProcessInfo(pid=1234, name="notepad.exe", path="C:\\notepad.exe")
        assert p.pid == 1234
        assert p.name == "notepad.exe"
        assert p.is_running is True
        assert p.window_count == 0

    def test_defaults(self):
        p = ProcessInfo(pid=1, name="test")
        assert p.path == ""
        assert p.is_running is True
        assert p.window_count == 0


class TestFindProcess:
    @patch("naturo.process._list_processes")
    def test_find_by_name(self, mock_list):
        mock_list.return_value = [
            ProcessInfo(pid=1, name="python"),
            ProcessInfo(pid=2, name="notepad"),
        ]
        result = find_process(name="notepad")
        assert result is not None
        assert result.pid == 2

    @patch("naturo.process._list_processes")
    def test_find_by_pid(self, mock_list):
        mock_list.return_value = [
            ProcessInfo(pid=1, name="python"),
            ProcessInfo(pid=2, name="notepad"),
        ]
        result = find_process(pid=2)
        assert result is not None
        assert result.name == "notepad"

    @patch("naturo.process._list_processes")
    def test_not_found(self, mock_list):
        mock_list.return_value = [ProcessInfo(pid=1, name="python")]
        assert find_process(name="nonexistent") is None

    def test_no_criteria(self):
        assert find_process() is None

    @patch("naturo.process._list_processes")
    def test_case_insensitive(self, mock_list):
        mock_list.return_value = [ProcessInfo(pid=1, name="Notepad.exe")]
        result = find_process(name="notepad")
        assert result is not None


class TestIsRunning:
    @patch("naturo.process.find_process")
    def test_running(self, mock_find):
        mock_find.return_value = ProcessInfo(pid=1, name="test")
        assert is_running("test") is True

    @patch("naturo.process.find_process")
    def test_not_running(self, mock_find):
        mock_find.return_value = None
        assert is_running("nonexistent") is False


class TestLaunchApp:
    @patch("subprocess.Popen")
    def test_launch_by_name(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 5678
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc

        info = launch_app(name="notepad")
        assert info.pid == 5678
        assert info.name == "notepad"
        assert info.is_running is True

    @patch("subprocess.Popen")
    def test_launch_by_path(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_popen.return_value = mock_proc

        info = launch_app(path="/usr/bin/ls")
        assert info.pid == 1234

    def test_launch_no_name_or_path(self):
        with pytest.raises(AppNotFoundError):
            launch_app()

    @patch("subprocess.Popen")
    def test_launch_file_not_found(self, mock_popen):
        mock_popen.side_effect = FileNotFoundError("not found")
        with pytest.raises(AppNotFoundError):
            launch_app(name="nonexistent_app_xyz")

    @patch("subprocess.Popen")
    def test_launch_nonexistent_app_returns_error(self, mock_popen):
        """BUG-013: launch should fail for apps that don't exist (exit code != 0)."""
        mock_proc = MagicMock()
        mock_proc.pid = 31584
        mock_proc.wait.return_value = 1  # open -a returns 1 for not-found
        mock_popen.return_value = mock_proc

        with pytest.raises(AppNotFoundError):
            launch_app(name="nonexistent_app_xyz")

    @patch("subprocess.Popen")
    def test_launch_wait_until_ready(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.poll.return_value = None  # still running
        mock_proc.wait.return_value = 0  # open -a exits successfully
        mock_popen.return_value = mock_proc

        info = launch_app(name="app", wait_until_ready=True, timeout=1.0)
        assert info.is_running is True

    @patch("subprocess.Popen")
    def test_launch_wait_process_exits(self, mock_popen):
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.poll.return_value = 1  # exited
        mock_proc.wait.return_value = 0  # open -a exits successfully (app found)
        mock_popen.return_value = mock_proc

        with pytest.raises(AppNotFoundError):
            launch_app(name="app", wait_until_ready=True, timeout=2.0)


class TestQuitApp:
    @patch("naturo.process.find_process")
    def test_quit_not_found(self, mock_find):
        mock_find.return_value = None
        with pytest.raises(AppNotFoundError):
            quit_app(name="nonexistent")

    @patch("naturo.process._force_kill")
    @patch("naturo.process.find_process")
    def test_quit_force(self, mock_find, mock_kill):
        mock_find.return_value = ProcessInfo(pid=123, name="app")
        quit_app(name="app", force=True)
        mock_kill.assert_called_once()


class TestRelaunchApp:
    @patch("naturo.process.launch_app")
    @patch("naturo.process.quit_app")
    def test_relaunch(self, mock_quit, mock_launch):
        mock_launch.return_value = ProcessInfo(pid=999, name="app")
        info = relaunch_app("app", wait_until_ready=False, timeout=5.0)
        assert info.pid == 999
        mock_quit.assert_called_once()

    @patch("naturo.process.launch_app")
    @patch("naturo.process.quit_app")
    def test_relaunch_not_running(self, mock_quit, mock_launch):
        mock_quit.side_effect = AppNotFoundError("app")
        mock_launch.return_value = ProcessInfo(pid=888, name="app")
        info = relaunch_app("app", wait_until_ready=False)
        assert info.pid == 888

    @patch("naturo.process.launch_app")
    @patch("naturo.process.quit_app")
    def test_relaunch_nonexistent_app_fails(self, mock_quit, mock_launch):
        """BUG-018: relaunch should fail for apps that don't exist."""
        mock_quit.side_effect = AppNotFoundError("nonexistent_xyz")
        mock_launch.side_effect = AppNotFoundError("nonexistent_xyz")
        with pytest.raises(AppNotFoundError):
            relaunch_app("nonexistent_xyz", wait_until_ready=False)


class TestListApps:
    @patch("naturo.process._list_processes")
    def test_deduplicates(self, mock_list):
        mock_list.return_value = [
            ProcessInfo(pid=1, name="python"),
            ProcessInfo(pid=2, name="python"),
            ProcessInfo(pid=3, name="notepad"),
        ]
        apps = list_apps()
        names = [a.name for a in apps]
        assert names.count("python") == 1
        assert "notepad" in names

    @patch("naturo.process._list_processes")
    def test_empty(self, mock_list):
        mock_list.return_value = []
        assert list_apps() == []
