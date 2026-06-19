"""Tests for Electron/CEF app detection and automation (naturo.electron).

Phase 5C.4 — Electron/CEF App Support.
"""

from __future__ import annotations

import os
import platform
import subprocess
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from naturo.errors import NaturoError

# Skip entire module on non-Windows for import-level tests
pytestmark = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Electron module requires Windows",
)


# ── detect_electron_app ─────────────────────────


class TestDetectElectronApp:
    """Test detect_electron_app()."""

    @pytest.fixture(autouse=True)
    def _patch_platform(self):
        with patch("naturo.electron.platform.system", return_value="Windows"):
            yield

    @patch("naturo.electron._find_processes_by_name")
    def test_no_processes_found(self, mock_find):
        """Returns is_electron=False when no matching processes found."""
        from naturo.electron import detect_electron_app

        mock_find.return_value = []
        result = detect_electron_app("NonexistentApp")
        assert result["is_electron"] is False
        assert result["processes"] == []
        assert result["debug_port"] is None

    @patch("naturo.electron._find_debug_port_from_cmdline")
    @patch("naturo.electron._is_electron_process")
    @patch("naturo.electron._find_processes_by_name")
    def test_electron_detected(self, mock_find, mock_is_electron, mock_port):
        """Correctly identifies an Electron process."""
        from naturo.electron import detect_electron_app

        mock_find.return_value = [{"pid": 1234, "name": "Code.exe"}]
        mock_is_electron.return_value = True
        mock_port.return_value = 9229
        result = detect_electron_app("vscode")
        assert result["is_electron"] is True
        assert result["app_name"] == "Visual Studio Code"
        assert result["debug_port"] == 9229
        assert result["main_pid"] == 1234

    @patch("naturo.electron._is_electron_process")
    @patch("naturo.electron._find_processes_by_name")
    def test_not_electron(self, mock_find, mock_is_electron):
        """Non-Electron process correctly identified."""
        from naturo.electron import detect_electron_app

        mock_find.return_value = [{"pid": 5678, "name": "notepad.exe"}]
        mock_is_electron.return_value = False
        result = detect_electron_app("notepad")
        assert result["is_electron"] is False

    @patch("naturo.electron._find_debug_port_from_cmdline")
    @patch("naturo.electron._is_electron_process")
    @patch("naturo.electron._find_processes_by_name")
    def test_electron_no_debug_port(self, mock_find, mock_is_electron, mock_port):
        """Electron app running without debug port."""
        from naturo.electron import detect_electron_app

        mock_find.return_value = [{"pid": 1111, "name": "Slack.exe"}]
        mock_is_electron.return_value = True
        mock_port.return_value = None
        result = detect_electron_app("slack")
        assert result["is_electron"] is True
        assert result["debug_port"] is None
        assert result["app_name"] == "Slack"

    @patch("naturo.electron._get_process_exe_path")
    @patch("naturo.electron._get_process_command_line")
    @patch("naturo.electron._bulk_get_process_info")
    @patch("naturo.electron._find_processes_by_name")
    def test_uses_single_bulk_query_for_many_pids(
        self, mock_find, mock_bulk, mock_cmdline, mock_exe,
    ):
        """detect_electron_app batches process info into one bulk query.

        Regression for #1023: with many matching PIDs the old code issued
        two ``wmic`` subprocesses per PID (~0.86 s each), causing a ~23 s
        stall on the ``see``/``find`` cascade for multi-process apps (e.g.
        Calculator spawns ~27 processes). The fix mirrors
        ``list_electron_apps``: fetch ``_bulk_get_process_info`` once and pass
        it through to the per-PID helpers, which must therefore never fall
        back to their per-PID ``wmic`` calls.
        """
        from naturo.electron import detect_electron_app

        pids = list(range(1000, 1027))  # 27 processes, like a UWP/Electron app
        mock_find.return_value = [
            {"pid": pid, "name": "App.exe"} for pid in pids
        ]
        mock_bulk.return_value = {
            pid: {
                "command_line": '"C:\\App.exe" --type=renderer',
                "exe_path": "",
            }
            for pid in pids
        }

        result = detect_electron_app("App")

        # Exactly one bulk query, and zero per-PID wmic fallbacks.
        assert mock_bulk.call_count == 1
        mock_cmdline.assert_not_called()
        mock_exe.assert_not_called()
        # Functional result is unchanged: the renderer marker confirms Electron.
        assert result["is_electron"] is True


# ── list_electron_apps ──────────────────────────


class TestListElectronApps:
    """Test list_electron_apps()."""

    @pytest.fixture(autouse=True)
    def _patch_platform(self):
        with patch("naturo.electron.platform.system", return_value="Windows"):
            yield

    @patch("naturo.electron._bulk_get_process_info", return_value={})
    @patch("naturo.electron._find_debug_port_from_cmdline")
    @patch("naturo.electron._is_electron_process")
    @patch("naturo.electron.subprocess.run")
    def test_lists_running_electron_apps(
        self, mock_run, mock_is_electron, mock_port, mock_bulk,
    ):
        """Lists detected Electron apps by scanning all processes."""
        from naturo.electron import list_electron_apps

        # Simulate tasklist CSV output with an Electron app and a system process
        mock_run.return_value = MagicMock(
            stdout=(
                '"Code.exe","100","Console","1","200,000 K"\n'
                '"Code.exe","101","Console","1","50,000 K"\n'
                '"svchost.exe","4","Services","0","10,000 K"\n'
                '"notepad.exe","200","Console","1","5,000 K"\n'
            ),
        )
        # Only Code.exe is Electron
        mock_is_electron.side_effect = lambda pid, **kw: pid in (100, 101)
        mock_port.return_value = None

        result = list_electron_apps()
        assert result["count"] >= 1
        app_names = [a["app_name"] for a in result["apps"]]
        assert "Visual Studio Code" in app_names
        # svchost is skipped, notepad is not Electron
        assert "notepad" not in [a["exe_name"] for a in result["apps"]]

    @patch("naturo.electron._bulk_get_process_info", return_value={})
    @patch("naturo.electron.subprocess.run")
    def test_no_electron_apps(self, mock_run, mock_bulk):
        """Returns empty list when no Electron apps running."""
        from naturo.electron import list_electron_apps

        mock_run.return_value = MagicMock(stdout="")
        result = list_electron_apps()
        assert result["count"] == 0
        assert result["apps"] == []

    @patch("naturo.electron._bulk_get_process_info", return_value={})
    @patch("naturo.electron._find_debug_port_from_cmdline")
    @patch("naturo.electron._is_electron_process")
    @patch("naturo.electron.subprocess.run")
    def test_scans_all_pids_per_exe(
        self, mock_run, mock_is_electron, mock_port, mock_bulk,
    ):
        """Checks multiple PIDs per exe to catch apps like Feishu where
        only child processes have Electron indicators."""
        from naturo.electron import list_electron_apps

        mock_run.return_value = MagicMock(
            stdout=(
                '"Feishu.exe","1000","Console","1","300,000 K"\n'
                '"Feishu.exe","1001","Console","1","50,000 K"\n'
                '"Feishu.exe","1002","Console","1","200,000 K"\n'
            ),
        )
        # Main process (1000) is NOT detected as Electron,
        # but child process (1001) IS — simulates Feishu behavior
        mock_is_electron.side_effect = lambda pid, **kw: pid == 1001
        mock_port.return_value = None

        result = list_electron_apps()
        assert result["count"] == 1
        assert result["apps"][0]["app_name"] == "Feishu"
        assert result["apps"][0]["process_count"] == 3


# ── get_debug_port ──────────────────────────────


class TestGetDebugPort:
    """Test get_debug_port()."""

    @pytest.fixture(autouse=True)
    def _patch_platform(self):
        with patch("naturo.electron.platform.system", return_value="Windows"):
            yield

    @patch("naturo.electron.detect_electron_app")
    def test_returns_port(self, mock_detect):
        """Returns debug port when available."""
        from naturo.electron import get_debug_port

        mock_detect.return_value = {"debug_port": 9229}
        assert get_debug_port("Code") == 9229

    @patch("naturo.electron.detect_electron_app")
    def test_returns_none(self, mock_detect):
        """Returns None when no debug port."""
        from naturo.electron import get_debug_port

        mock_detect.return_value = {"debug_port": None}
        assert get_debug_port("Slack") is None


# ── launch_with_debug ───────────────────────────


class TestLaunchWithDebug:
    """Test launch_with_debug()."""

    @pytest.fixture(autouse=True)
    def _patch_platform(self):
        with patch("naturo.electron.platform.system", return_value="Windows"):
            yield

    @patch("naturo.electron.subprocess.Popen")
    @patch("naturo.electron.os.path.isfile", return_value=True)
    def test_launch_success(self, mock_isfile, mock_popen):
        """Successfully launches app with debug port."""
        from naturo.electron import launch_with_debug

        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_popen.return_value = mock_proc

        result = launch_with_debug("C:\\Apps\\Code.exe", port=9229)
        assert result["pid"] == 9999
        assert result["port"] == 9229
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "--remote-debugging-port=9229" in args

    def test_launch_file_not_found(self):
        """Raises NaturoError for nonexistent executable."""
        from naturo.electron import launch_with_debug

        with pytest.raises(NaturoError) as exc_info:
            launch_with_debug("C:\\nonexistent\\app.exe")
        assert exc_info.value.code == "FILE_NOT_FOUND"

    @patch("naturo.electron.subprocess.Popen", side_effect=OSError("denied"))
    @patch("naturo.electron.os.path.isfile", return_value=True)
    def test_launch_os_error(self, mock_isfile, mock_popen):
        """Raises NaturoError on OS errors."""
        from naturo.electron import launch_with_debug

        with pytest.raises(NaturoError) as exc_info:
            launch_with_debug("C:\\Apps\\Code.exe")
        assert exc_info.value.code == "LAUNCH_FAILED"

    @patch("naturo.electron.subprocess.Popen")
    @patch("naturo.electron.os.path.isfile", return_value=True)
    def test_launch_with_extra_args(self, mock_isfile, mock_popen):
        """Extra args passed to subprocess."""
        from naturo.electron import launch_with_debug

        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_popen.return_value = mock_proc

        launch_with_debug("C:\\Apps\\Code.exe", extra_args=["--no-sandbox"])
        args = mock_popen.call_args[0][0]
        assert "--no-sandbox" in args


# ── connect_to_electron ─────────────────────────


class TestConnectToElectron:
    """Test connect_to_electron()."""

    @pytest.fixture(autouse=True)
    def _patch_platform(self):
        with patch("naturo.electron.platform.system", return_value="Windows"):
            yield

    @patch("naturo.electron.detect_electron_app")
    def test_not_electron_error(self, mock_detect):
        """Raises error when app is not Electron."""
        from naturo.electron import connect_to_electron

        mock_detect.return_value = {"is_electron": False}
        with pytest.raises(NaturoError) as exc_info:
            connect_to_electron("notepad")
        assert exc_info.value.code == "NOT_ELECTRON"

    @patch("naturo.electron.detect_electron_app")
    def test_no_debug_port_error(self, mock_detect):
        """Raises error when no debug port."""
        from naturo.electron import connect_to_electron

        mock_detect.return_value = {"is_electron": True, "debug_port": None}
        with pytest.raises(NaturoError) as exc_info:
            connect_to_electron("slack")
        assert exc_info.value.code == "NO_DEBUG_PORT"

    @patch("naturo.cdp.CDPClient")
    @patch("naturo.electron.detect_electron_app")
    def test_connect_success(self, mock_detect, mock_cdp_cls):
        """Connects and returns tab info."""
        from naturo.electron import connect_to_electron

        mock_detect.return_value = {"is_electron": True, "debug_port": 9229}
        mock_client = MagicMock()
        mock_client.list_tabs.return_value = [
            {"title": "Settings", "url": "chrome://settings"}
        ]
        mock_cdp_cls.return_value = mock_client

        result = connect_to_electron("Code")
        assert result["port"] == 9229
        assert result["count"] == 1

    @patch("naturo.electron.detect_electron_app")
    def test_connect_with_explicit_port(self, mock_detect):
        """Uses explicit port, skips detection."""
        from naturo.electron import connect_to_electron
        from naturo.cdp import CDPConnectionError

        # Should not call detect at all with explicit port
        with patch("naturo.cdp.CDPClient") as mock_cdp_cls:
            mock_client = MagicMock()
            mock_client.list_tabs.return_value = []
            mock_cdp_cls.return_value = mock_client
            result = connect_to_electron("any", port=9999)
            assert result["port"] == 9999
            mock_detect.assert_not_called()


# ── Platform guard ──────────────────────────────


class TestPlatformGuard:
    """Test that functions reject non-Windows platforms."""

    @patch("naturo.electron.platform.system", return_value="Darwin")
    def test_detect_rejects_non_windows(self, _mock):
        from naturo.electron import detect_electron_app

        with pytest.raises(NaturoError) as exc_info:
            detect_electron_app("Code")
        assert exc_info.value.code == "PLATFORM_ERROR"

    @patch("naturo.electron.platform.system", return_value="Linux")
    def test_list_rejects_non_windows(self, _mock):
        from naturo.electron import list_electron_apps

        with pytest.raises(NaturoError) as exc_info:
            list_electron_apps()
        assert exc_info.value.code == "PLATFORM_ERROR"

    @patch("naturo.electron.platform.system", return_value="Darwin")
    def test_launch_rejects_non_windows(self, _mock):
        from naturo.electron import launch_with_debug

        with pytest.raises(NaturoError) as exc_info:
            launch_with_debug("/usr/bin/code")
        assert exc_info.value.code == "PLATFORM_ERROR"


# ── Internal helpers ────────────────────────────


class TestInternalHelpers:
    """Test internal helper functions."""

    @pytest.fixture(autouse=True)
    def _patch_platform(self):
        with patch("naturo.electron.platform.system", return_value="Windows"):
            yield

    @patch("naturo.electron.subprocess.run")
    def test_get_process_command_line(self, mock_run):
        """Extracts command line from WMIC output."""
        from naturo.electron import _get_process_command_line

        mock_run.return_value = MagicMock(
            stdout='CommandLine="C:\\Code.exe" --type=renderer\n',
        )
        result = _get_process_command_line(1234)
        assert result is not None
        assert "Code.exe" in result

    @patch("naturo.electron.subprocess.run")
    def test_get_process_command_line_timeout(self, mock_run):
        """Returns None on timeout."""
        from naturo.electron import _get_process_command_line

        mock_run.side_effect = subprocess.TimeoutExpired("wmic", 5)
        assert _get_process_command_line(1234) is None

    @patch("naturo.electron.subprocess.run")
    def test_find_processes_by_name(self, mock_run):
        """Parses tasklist CSV output."""
        from naturo.electron import _find_processes_by_name

        mock_run.return_value = MagicMock(
            stdout='"Code.exe","1234","Console","1","100,000 K"\n'
                   '"Code.exe","1235","Console","1","50,000 K"\n',
        )
        result = _find_processes_by_name("Code")
        assert len(result) == 2
        assert result[0]["pid"] == 1234
        assert result[0]["name"] == "Code.exe"

    @patch("naturo.electron._get_process_command_line")
    def test_is_electron_process_by_cmdline(self, mock_cmdline):
        """Detects Electron from command line args."""
        from naturo.electron import _is_electron_process

        mock_cmdline.return_value = '"C:\\Code.exe" --type=renderer --lang=en'
        with patch("naturo.electron._get_process_exe_path", return_value=None):
            assert _is_electron_process(1234) is True

    @patch("naturo.electron._get_process_command_line")
    def test_is_not_electron_process(self, mock_cmdline):
        """Non-Electron process correctly identified."""
        from naturo.electron import _is_electron_process

        mock_cmdline.return_value = '"C:\\Windows\\notepad.exe"'
        with patch("naturo.electron._get_process_exe_path", return_value=None):
            assert _is_electron_process(5678) is False

    def test_is_electron_process_with_proc_info(self):
        """Uses pre-fetched proc_info instead of wmic calls."""
        from naturo.electron import _is_electron_process

        proc_info = {
            100: {
                "command_line": '"C:\\Code.exe" --type=renderer',
                "exe_path": "C:\\Code\\Code.exe",
            },
            200: {
                "command_line": '"C:\\notepad.exe"',
                "exe_path": "C:\\Windows\\notepad.exe",
            },
        }
        assert _is_electron_process(100, proc_info=proc_info) is True
        assert _is_electron_process(200, proc_info=proc_info) is False

    def test_find_debug_port_with_proc_info(self):
        """Extracts debug port from pre-fetched proc_info."""
        from naturo.electron import _find_debug_port_from_cmdline

        proc_info = {
            100: {
                "command_line": '"C:\\Code.exe" --remote-debugging-port=9229',
                "exe_path": "",
            },
            200: {
                "command_line": '"C:\\notepad.exe"',
                "exe_path": "",
            },
        }
        assert _find_debug_port_from_cmdline(100, proc_info=proc_info) == 9229
        assert _find_debug_port_from_cmdline(200, proc_info=proc_info) is None

    @patch("naturo.electron.subprocess.run")
    def test_bulk_get_process_info(self, mock_run):
        """Parses bulk wmic CSV output."""
        from naturo.electron import _bulk_get_process_info

        mock_run.return_value = MagicMock(
            stdout=(
                "Node,CommandLine,ExecutablePath,ProcessId\n"
                'WIN11,C:\\Code.exe --type=renderer,C:\\Code\\Code.exe,100\n'
                'WIN11,C:\\notepad.exe,C:\\Windows\\notepad.exe,200\n'
            ),
        )
        info = _bulk_get_process_info()
        assert 100 in info
        assert "renderer" in info[100]["command_line"]
        assert 200 in info
        assert "notepad" in info[200]["exe_path"]

    @patch("naturo.electron.subprocess.run")
    def test_bulk_get_process_info_timeout(self, mock_run):
        """Returns empty dict on timeout."""
        from naturo.electron import _bulk_get_process_info

        mock_run.side_effect = subprocess.TimeoutExpired("wmic", 15)
        assert _bulk_get_process_info() == {}

    @patch("naturo.electron._get_process_command_line")
    def test_find_debug_port_from_cmdline(self, mock_cmdline):
        """Extracts debug port from command line."""
        from naturo.electron import _find_debug_port_from_cmdline

        mock_cmdline.return_value = (
            '"C:\\Code.exe" --remote-debugging-port=9229 --no-sandbox'
        )
        assert _find_debug_port_from_cmdline(1234) == 9229

    @patch("naturo.electron._get_process_command_line")
    def test_find_debug_port_none(self, mock_cmdline):
        """Returns None when no debug port in command line."""
        from naturo.electron import _find_debug_port_from_cmdline

        mock_cmdline.return_value = '"C:\\Code.exe" --no-sandbox'
        assert _find_debug_port_from_cmdline(1234) is None


# ── CLI Commands ────────────────────────────────


import pytest

@pytest.mark.skip(reason="electron CLI command removed — Eyes+Hands focus")
class TestElectronCLI:
    """Test electron CLI commands via Click test runner."""

    @pytest.fixture(autouse=True)
    def _patch_platform(self):
        with patch("naturo.electron.platform.system", return_value="Windows"):
            yield

    def _invoke(self, args):
        from click.testing import CliRunner
        from naturo.cli import main
        runner = CliRunner()
        return runner.invoke(main, ["electron"] + args)

    @patch("naturo.electron.detect_electron_app")
    def test_detect_json(self, mock_detect):
        """detect --json returns structured output."""
        import json

        mock_detect.return_value = {
            "is_electron": True,
            "app_name": "VS Code",
            "processes": [{"pid": 1234, "name": "Code.exe"}],
            "debug_port": 9229,
            "main_pid": 1234,
        }
        result = self._invoke(["detect", "vscode", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["is_electron"] is True

    @patch("naturo.electron.list_electron_apps")
    def test_list_json(self, mock_list):
        """list --json returns structured output."""
        import json

        mock_list.return_value = {
            "apps": [
                {
                    "app_name": "VS Code",
                    "exe_name": "Code.exe",
                    "pid": 100,
                    "debug_port": None,
                    "debuggable": False,
                }
            ],
            "count": 1,
        }
        result = self._invoke(["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 1

    @patch("naturo.electron.list_electron_apps")
    def test_list_empty(self, mock_list):
        """list shows message when no apps found."""
        mock_list.return_value = {"apps": [], "count": 0}
        result = self._invoke(["list"])
        assert result.exit_code == 0
        assert "No Electron" in result.output

    @patch("naturo.electron.detect_electron_app")
    def test_detect_not_electron(self, mock_detect):
        """detect shows appropriate message for non-Electron apps."""
        mock_detect.return_value = {
            "is_electron": False,
            "app_name": "notepad",
            "processes": [],
            "debug_port": None,
            "main_pid": None,
        }
        result = self._invoke(["detect", "notepad"])
        assert result.exit_code == 0
        assert "not detected" in result.output


# ── Known apps registry ─────────────────────────


class TestKnownApps:
    """Test the known Electron apps registry."""

    def test_known_apps_have_required_keys(self):
        """All known apps have exe and display keys."""
        from naturo.electron import _KNOWN_ELECTRON_APPS

        for key, info in _KNOWN_ELECTRON_APPS.items():
            assert "exe" in info, f"Missing exe for {key}"
            assert "display" in info, f"Missing display for {key}"
            assert info["exe"].endswith(".exe"), f"Invalid exe for {key}"

    def test_known_apps_lowercase_keys(self):
        """All keys are lowercase."""
        from naturo.electron import _KNOWN_ELECTRON_APPS

        for key in _KNOWN_ELECTRON_APPS:
            assert key == key.lower(), f"Key {key} should be lowercase"
