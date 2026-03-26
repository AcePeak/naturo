"""Tests for naturo.process — launch, quit, relaunch, find, is_running."""
import platform
import pytest
from unittest.mock import patch, MagicMock
from naturo.process import (
    ProcessInfo, find_process, is_running, launch_app, quit_app,
    relaunch_app, list_apps, _list_processes,
    _get_console_session_id, _get_process_session_id,
    _resolve_launch_name, _LAUNCH_ALIASES,
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

    @patch("naturo.process._get_process_session_id")
    @patch("naturo.process._get_console_session_id")
    @patch("naturo.process._list_processes")
    def test_prefers_interactive_session_over_session_0(
        self, mock_list, mock_console, mock_proc_session
    ):
        """When multiple processes match, prefer the one in the active
        console session over the one in Session 0 (#230)."""
        mock_list.return_value = [
            ProcessInfo(pid=100, name="Notepad.exe"),  # Session 0 ghost
            ProcessInfo(pid=200, name="Notepad.exe"),  # Interactive session
        ]
        mock_console.return_value = 1
        # PID 100 → Session 0, PID 200 → Session 1 (console)
        mock_proc_session.side_effect = lambda pid: 0 if pid == 100 else 1
        result = find_process(name="notepad")
        assert result is not None
        assert result.pid == 200, "Should prefer interactive session (PID 200)"

    @patch("naturo.process._get_process_session_id")
    @patch("naturo.process._get_console_session_id")
    @patch("naturo.process._list_processes")
    def test_falls_back_to_first_match_when_no_console_session(
        self, mock_list, mock_console, mock_proc_session
    ):
        """When console session ID is unavailable, fall back to first match."""
        mock_list.return_value = [
            ProcessInfo(pid=100, name="Notepad.exe"),
            ProcessInfo(pid=200, name="Notepad.exe"),
        ]
        mock_console.return_value = -1  # Can't determine console session
        result = find_process(name="notepad")
        assert result is not None
        assert result.pid == 100, "Should fall back to first match"

    @patch("naturo.process._get_process_session_id")
    @patch("naturo.process._get_console_session_id")
    @patch("naturo.process._list_processes")
    def test_session_aware_single_match(
        self, mock_list, mock_console, mock_proc_session
    ):
        """When only one process matches, return it regardless of session."""
        mock_list.return_value = [
            ProcessInfo(pid=100, name="Notepad.exe"),
        ]
        mock_console.return_value = 1
        mock_proc_session.return_value = 0  # Only in Session 0
        result = find_process(name="notepad")
        assert result is not None
        assert result.pid == 100

    @patch("naturo.process._get_process_session_id")
    @patch("naturo.process._get_console_session_id")
    @patch("naturo.process._list_processes")
    def test_require_interactive_skips_session_0(
        self, mock_list, mock_console, mock_proc_session
    ):
        """With require_interactive=True, session 0 processes are skipped
        entirely instead of being used as a fallback (#350)."""
        mock_list.return_value = [
            ProcessInfo(pid=100, name="Notepad.exe"),  # Session 0 only
        ]
        mock_console.return_value = 1
        mock_proc_session.return_value = 0  # Only in Session 0
        result = find_process(name="notepad", require_interactive=True)
        assert result is None, "Should skip session 0 when require_interactive=True"

    @patch("naturo.process._get_process_session_id")
    @patch("naturo.process._get_console_session_id")
    @patch("naturo.process._list_processes")
    def test_require_interactive_returns_console_session_process(
        self, mock_list, mock_console, mock_proc_session
    ):
        """With require_interactive=True, still returns processes in the
        active console session."""
        mock_list.return_value = [
            ProcessInfo(pid=100, name="Notepad.exe"),  # Session 0
            ProcessInfo(pid=200, name="Notepad.exe"),  # Session 1 (console)
        ]
        mock_console.return_value = 1
        mock_proc_session.side_effect = lambda pid: 0 if pid == 100 else 1
        result = find_process(name="notepad", require_interactive=True)
        assert result is not None
        assert result.pid == 200, "Should return console session process"

    @patch("naturo.process._get_process_session_id")
    @patch("naturo.process._get_console_session_id")
    @patch("naturo.process._list_processes")
    def test_require_interactive_no_effect_when_session_unknown(
        self, mock_list, mock_console, mock_proc_session
    ):
        """When console session cannot be determined, require_interactive
        has no effect (falls back to first match)."""
        mock_list.return_value = [
            ProcessInfo(pid=100, name="Notepad.exe"),
        ]
        mock_console.return_value = -1  # Can't determine console session
        result = find_process(name="notepad", require_interactive=True)
        assert result is not None
        assert result.pid == 100


class TestSessionHelpers:
    """Tests for session ID helper functions."""

    @patch("platform.system", return_value="Darwin")
    def test_console_session_non_windows(self, _mock):
        assert _get_console_session_id() == -1

    @patch("platform.system", return_value="Darwin")
    def test_process_session_non_windows(self, _mock):
        assert _get_process_session_id(1234) == -1


class TestIsRunning:
    @patch("naturo.process.find_process")
    def test_running(self, mock_find):
        mock_find.return_value = ProcessInfo(pid=1, name="test")
        assert is_running("test") is True

    @patch("naturo.process.find_process")
    def test_not_running(self, mock_find):
        mock_find.return_value = None
        assert is_running("nonexistent") is False


class TestLaunchAppSessionGuard:
    """Tests for launch_app session 0 guard (#351)."""

    @patch("naturo.process.platform.system", return_value="Windows")
    def test_launch_rejects_non_interactive_session(self, mock_sys):
        """launch_app should raise NoDesktopSessionError in non-interactive
        sessions on Windows to prevent spawning invisible processes (#351)."""
        with patch("naturo.cli.interaction._is_current_session_interactive",
                    return_value=False):
            from naturo.errors import NoDesktopSessionError
            with pytest.raises(NoDesktopSessionError):
                launch_app(name="notepad")

    @patch("naturo.process.platform.system", return_value="Darwin")
    def test_launch_no_session_guard_on_macos(self, mock_sys):
        """Session guard should not apply on macOS."""
        with patch("naturo.process.subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.pid = 1234
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc
            with patch("naturo.process.find_process",
                        return_value=ProcessInfo(pid=1234, name="Notes")):
                # Should not raise NoDesktopSessionError
                result = launch_app(name="Notes")
                assert result is not None


class TestLaunchApp:
    """Tests for launch_app.

    On Windows, launch_app calls subprocess.run (for 'where' check) before
    subprocess.Popen.  We must mock both to prevent subprocess.run from using
    the mocked Popen internally (which causes ValueError on Python 3.14+
    because MagicMock.communicate() doesn't return a proper (stdout, stderr)).
    """

    @staticmethod
    def _make_run_result(returncode=0, stdout="", stderr=""):
        """Create a fake subprocess.CompletedProcess."""
        import subprocess as _sp
        return _sp.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)

    @patch("naturo.process.subprocess.run")
    @patch("naturo.process.subprocess.Popen")
    def test_launch_by_name(self, mock_popen, mock_run):
        mock_proc = MagicMock()
        mock_proc.pid = 5678
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc
        # 'where' succeeds on Windows; ignored on other platforms
        mock_run.return_value = self._make_run_result(returncode=0, stdout="C:\\notepad.exe")

        info = launch_app(name="notepad")
        assert info.pid == 5678
        assert info.name == "notepad"
        assert info.is_running is True

    @patch("naturo.process.subprocess.run")
    @patch("naturo.process.subprocess.Popen")
    def test_launch_by_path(self, mock_popen, mock_run):
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_proc.wait.return_value = 0
        mock_popen.return_value = mock_proc
        mock_run.return_value = self._make_run_result(returncode=0)

        if platform.system() == "Windows":
            # On Windows, path launch checks os.path.isfile first
            with patch("os.path.isfile", return_value=True):
                info = launch_app(path="/usr/bin/ls")
        else:
            info = launch_app(path="/usr/bin/ls")
        assert info.pid == 1234

    def test_launch_no_name_or_path(self):
        with pytest.raises(AppNotFoundError):
            launch_app()

    @patch("naturo.process.subprocess.run")
    @patch("naturo.process.subprocess.Popen")
    def test_launch_file_not_found(self, mock_popen, mock_run):
        mock_run.return_value = self._make_run_result(returncode=1)
        mock_popen.side_effect = FileNotFoundError("not found")
        with pytest.raises(AppNotFoundError):
            launch_app(name="nonexistent_app_xyz")

    @patch("naturo.process.subprocess.run")
    @patch("naturo.process.subprocess.Popen")
    def test_launch_nonexistent_app_returns_error(self, mock_popen, mock_run):
        """BUG-013: launch should fail for apps that don't exist (exit code != 0)."""
        mock_proc = MagicMock()
        mock_proc.pid = 31584
        mock_proc.wait.return_value = 1  # open -a returns 1 for not-found
        mock_popen.return_value = mock_proc
        # 'where' fails (app not found), then 'start /wait' also fails
        mock_run.return_value = self._make_run_result(returncode=1)

        with pytest.raises(AppNotFoundError):
            launch_app(name="nonexistent_app_xyz")

    @patch("naturo.process.subprocess.run")
    @patch("naturo.process.subprocess.Popen")
    def test_launch_timeout_expired_raises_app_not_found(self, mock_popen, mock_run):
        """BUG-013/018: subprocess.TimeoutExpired must be caught, not leaked as traceback."""
        import subprocess
        mock_popen.side_effect = subprocess.TimeoutExpired(cmd="start /wait", timeout=10)
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="where", timeout=5)

        with pytest.raises(AppNotFoundError) as exc_info:
            launch_app(name="nonexistent_app_xyz")
        assert "nonexistent_app_xyz" in exc_info.value.message

    @patch("naturo.process.subprocess.run")
    @patch("naturo.process.subprocess.Popen")
    def test_launch_wait_until_ready(self, mock_popen, mock_run):
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.poll.return_value = None  # still running
        mock_proc.wait.return_value = 0  # open -a exits successfully
        mock_popen.return_value = mock_proc
        mock_run.return_value = self._make_run_result(returncode=0, stdout="C:\\app.exe")

        info = launch_app(name="app", wait_until_ready=True, timeout=1.0)
        assert info.is_running is True

    @patch("naturo.process.subprocess.run")
    @patch("naturo.process.subprocess.Popen")
    def test_launch_wait_process_exits(self, mock_popen, mock_run):
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.poll.return_value = 1  # exited
        mock_proc.wait.return_value = 0  # open -a exits successfully (app found)
        mock_popen.return_value = mock_proc
        mock_run.return_value = self._make_run_result(returncode=0, stdout="C:\\app.exe")

        with pytest.raises(AppNotFoundError):
            launch_app(name="app", wait_until_ready=True, timeout=2.0)


class TestResolveLaunchName:
    """Tests for _resolve_launch_name alias resolution (#246)."""

    def test_aliases_table_has_expected_entries(self):
        """Smoke test: key aliases exist in the table."""
        assert "calculator" in _LAUNCH_ALIASES
        assert "paint" in _LAUNCH_ALIASES
        assert "settings" in _LAUNCH_ALIASES

    def test_calculator_aliases(self):
        """calculator maps to calc and calculatorapp."""
        aliases = _LAUNCH_ALIASES["calculator"]
        assert "calc" in aliases
        assert "calculatorapp" in aliases

    def test_paint_aliases(self):
        """paint maps to mspaint."""
        assert "mspaint" in _LAUNCH_ALIASES["paint"]

    @patch("naturo.process.platform.system", return_value="Darwin")
    def test_non_windows_returns_original(self, _mock_sys):
        """On non-Windows platforms, alias resolution is a no-op."""
        assert _resolve_launch_name("calculator") == "calculator"

    @patch("naturo.process.platform.system", return_value="Windows")
    @patch("naturo.process.subprocess.run")
    def test_direct_name_found(self, mock_run, _mock_sys):
        """If the name itself is resolvable via 'where', return it unchanged."""
        mock_run.return_value = MagicMock(returncode=0)
        assert _resolve_launch_name("notepad") == "notepad"

    @patch("naturo.process.platform.system", return_value="Windows")
    @patch("naturo.process.subprocess.run")
    def test_alias_resolution(self, mock_run, _mock_sys):
        """'calculator' should resolve to 'calc' when 'where calculator' fails."""
        def where_side_effect(args, **kwargs):
            name = args[1] if len(args) > 1 else ""
            if name == "calc":
                return MagicMock(returncode=0)
            return MagicMock(returncode=1)
        mock_run.side_effect = where_side_effect
        assert _resolve_launch_name("calculator") == "calc"

    @patch("naturo.process.platform.system", return_value="Windows")
    @patch("naturo.process.subprocess.run")
    def test_paint_alias_resolution(self, mock_run, _mock_sys):
        """'paint' should resolve to 'mspaint'."""
        def where_side_effect(args, **kwargs):
            name = args[1] if len(args) > 1 else ""
            if name == "mspaint":
                return MagicMock(returncode=0)
            return MagicMock(returncode=1)
        mock_run.side_effect = where_side_effect
        assert _resolve_launch_name("paint") == "mspaint"

    @patch("naturo.process.platform.system", return_value="Windows")
    @patch("naturo.process.subprocess.run")
    def test_unknown_name_returns_original(self, mock_run, _mock_sys):
        """Unknown names with no aliases return the original name."""
        mock_run.return_value = MagicMock(returncode=1)
        assert _resolve_launch_name("some_random_app") == "some_random_app"

    @patch("naturo.process.platform.system", return_value="Windows")
    @patch("naturo.process.subprocess.run")
    def test_case_insensitive_lookup(self, mock_run, _mock_sys):
        """Alias lookup is case-insensitive."""
        def where_side_effect(args, **kwargs):
            name = args[1] if len(args) > 1 else ""
            if name == "calc":
                return MagicMock(returncode=0)
            return MagicMock(returncode=1)
        mock_run.side_effect = where_side_effect
        assert _resolve_launch_name("Calculator") == "calc"

    @patch("naturo.process.platform.system", return_value="Windows")
    @patch("naturo.process.subprocess.run")
    def test_cjk_alias_resolution(self, mock_run, _mock_sys):
        """Chinese alias '计算器' should resolve to 'calc'."""
        def where_side_effect(args, **kwargs):
            name = args[1] if len(args) > 1 else ""
            if name == "calc":
                return MagicMock(returncode=0)
            return MagicMock(returncode=1)
        mock_run.side_effect = where_side_effect
        assert _resolve_launch_name("计算器") == "calc"


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
