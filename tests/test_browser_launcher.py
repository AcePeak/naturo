"""Tests for naturo.browser._launcher — Chrome profile discovery and launch."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner

from naturo.browser._launcher import (
    ChromeProcess,
    find_chrome,
    launch_chrome,
    list_profiles,
    _default_user_data_dir,
    _resolve_profile_directory,
    _wait_for_cdp,
)
from naturo.cli.browser_cmd import browser


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fake_chrome_dir(tmp_path):
    """Create a fake Chrome user data directory with Local State and profiles."""
    data_dir = tmp_path / "Chrome" / "User Data"
    data_dir.mkdir(parents=True)

    # Create profile directories
    default_dir = data_dir / "Default"
    default_dir.mkdir()
    profile1_dir = data_dir / "Profile 1"
    profile1_dir.mkdir()
    profile2_dir = data_dir / "Profile 2"
    profile2_dir.mkdir()

    # Create Local State with profile info_cache
    local_state = {
        "profile": {
            "info_cache": {
                "Default": {"name": "Personal"},
                "Profile 1": {"name": "Work"},
                "Profile 2": {"name": "Testing"},
            }
        }
    }
    (data_dir / "Local State").write_text(json.dumps(local_state), encoding="utf-8")

    return data_dir


# ---------------------------------------------------------------------------
# find_chrome
# ---------------------------------------------------------------------------


class TestFindChrome:
    """Tests for Chrome binary discovery."""

    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value="/usr/bin/google-chrome")
    def test_finds_chrome_linux(self, mock_which, mock_system):
        result = find_chrome()
        assert result == "/usr/bin/google-chrome"

    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value=None)
    def test_returns_none_when_not_found_linux(self, mock_which, mock_system):
        result = find_chrome()
        assert result is None

    @patch("platform.system", return_value="Windows")
    @patch("os.path.isfile", return_value=False)
    def test_returns_none_when_not_found_windows(self, mock_isfile, mock_system):
        result = find_chrome()
        assert result is None

    @patch("platform.system", return_value="Darwin")
    @patch("os.path.isfile", return_value=False)
    def test_returns_none_when_not_found_macos(self, mock_isfile, mock_system):
        result = find_chrome()
        assert result is None

    @patch("platform.system", return_value="Darwin")
    @patch("os.path.isfile")
    def test_finds_chrome_macos(self, mock_isfile, mock_system):
        def isfile(path):
            return path == "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        mock_isfile.side_effect = isfile
        result = find_chrome()
        assert result == "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


# ---------------------------------------------------------------------------
# list_profiles
# ---------------------------------------------------------------------------


class TestListProfiles:
    """Tests for Chrome profile listing."""

    def test_lists_profiles_from_local_state(self, fake_chrome_dir):
        profiles = list_profiles(str(fake_chrome_dir))
        assert len(profiles) == 3

        names = {p["name"] for p in profiles}
        assert names == {"Personal", "Work", "Testing"}

        dirs = {p["directory"] for p in profiles}
        assert dirs == {"Default", "Profile 1", "Profile 2"}

    def test_returns_empty_for_nonexistent_dir(self, tmp_path):
        profiles = list_profiles(str(tmp_path / "nonexistent"))
        assert profiles == []

    def test_returns_empty_when_no_local_state(self, tmp_path):
        profiles = list_profiles(str(tmp_path))
        assert profiles == []

    def test_returns_empty_for_invalid_json(self, tmp_path):
        (tmp_path / "Local State").write_text("not json", encoding="utf-8")
        profiles = list_profiles(str(tmp_path))
        assert profiles == []

    def test_skips_missing_profile_dirs(self, tmp_path):
        """Profile listed in Local State but directory doesn't exist."""
        local_state = {
            "profile": {
                "info_cache": {
                    "Default": {"name": "Personal"},
                    "Ghost": {"name": "Missing Profile"},
                }
            }
        }
        (tmp_path / "Local State").write_text(
            json.dumps(local_state), encoding="utf-8"
        )
        (tmp_path / "Default").mkdir()
        # Don't create "Ghost" directory

        profiles = list_profiles(str(tmp_path))
        assert len(profiles) == 1
        assert profiles[0]["name"] == "Personal"

    def test_profile_path_is_absolute(self, fake_chrome_dir):
        profiles = list_profiles(str(fake_chrome_dir))
        for p in profiles:
            assert os.path.isabs(p["path"])

    def test_uses_default_dir_when_none(self):
        """When user_data_dir is None, uses OS default."""
        profiles = list_profiles(None)
        # May return empty list on CI/Linux without Chrome installed
        assert isinstance(profiles, list)


# ---------------------------------------------------------------------------
# _resolve_profile_directory
# ---------------------------------------------------------------------------


class TestResolveProfileDirectory:
    """Tests for profile name → directory resolution."""

    def test_resolves_by_name(self, fake_chrome_dir):
        result = _resolve_profile_directory("Work", str(fake_chrome_dir))
        assert result == "Profile 1"

    def test_resolves_by_directory(self, fake_chrome_dir):
        result = _resolve_profile_directory("Profile 2", str(fake_chrome_dir))
        assert result == "Profile 2"

    def test_returns_none_for_unknown(self, fake_chrome_dir):
        result = _resolve_profile_directory("Nonexistent", str(fake_chrome_dir))
        assert result is None

    def test_resolves_default(self, fake_chrome_dir):
        result = _resolve_profile_directory("Personal", str(fake_chrome_dir))
        assert result == "Default"


# ---------------------------------------------------------------------------
# _default_user_data_dir
# ---------------------------------------------------------------------------


class TestDefaultUserDataDir:
    """Tests for OS-specific default user data directory."""

    @patch("platform.system", return_value="Linux")
    def test_linux_path(self, mock_system):
        result = _default_user_data_dir()
        assert result is not None
        assert ".config/google-chrome" in str(result)

    @patch("platform.system", return_value="Darwin")
    def test_macos_path(self, mock_system):
        result = _default_user_data_dir()
        assert result is not None
        assert "Application Support/Google/Chrome" in str(result)

    @patch("platform.system", return_value="Windows")
    def test_windows_path(self, mock_system):
        result = _default_user_data_dir()
        assert result is not None
        assert "Google" in str(result) and "Chrome" in str(result)


# ---------------------------------------------------------------------------
# ChromeProcess
# ---------------------------------------------------------------------------


class TestChromeProcess:
    """Tests for the ChromeProcess handle."""

    def test_attributes(self):
        mock_proc = MagicMock(spec=subprocess.Popen, pid=12345)
        mock_proc.pid = 12345
        chrome = ChromeProcess(mock_proc, port=9222)
        assert chrome.pid == 12345
        assert chrome.port == 9222

    def test_is_running_true(self):
        mock_proc = MagicMock(spec=subprocess.Popen, pid=12345)
        mock_proc.poll.return_value = None
        chrome = ChromeProcess(mock_proc, port=9222)
        assert chrome.is_running() is True

    def test_is_running_false(self):
        mock_proc = MagicMock(spec=subprocess.Popen, pid=12345)
        mock_proc.poll.return_value = 0
        chrome = ChromeProcess(mock_proc, port=9222)
        assert chrome.is_running() is False

    def test_terminate(self):
        mock_proc = MagicMock(spec=subprocess.Popen, pid=12345)
        mock_proc.poll.return_value = None
        chrome = ChromeProcess(mock_proc, port=9222)
        chrome.terminate()
        mock_proc.terminate.assert_called_once()

    def test_terminate_already_stopped(self):
        mock_proc = MagicMock(spec=subprocess.Popen, pid=12345)
        mock_proc.poll.return_value = 0
        chrome = ChromeProcess(mock_proc, port=9222)
        chrome.terminate()
        mock_proc.terminate.assert_not_called()

    def test_kill(self):
        mock_proc = MagicMock(spec=subprocess.Popen, pid=12345)
        mock_proc.poll.return_value = None
        chrome = ChromeProcess(mock_proc, port=9222)
        chrome.kill()
        mock_proc.kill.assert_called_once()

    def test_wait(self):
        mock_proc = MagicMock(spec=subprocess.Popen, pid=12345)
        mock_proc.wait.return_value = 0
        chrome = ChromeProcess(mock_proc, port=9222)
        assert chrome.wait(timeout=5) == 0

    def test_repr_running(self):
        mock_proc = MagicMock(spec=subprocess.Popen, pid=12345)
        mock_proc.pid = 999
        mock_proc.poll.return_value = None
        chrome = ChromeProcess(mock_proc, port=9222)
        assert "running" in repr(chrome)

    def test_repr_stopped(self):
        mock_proc = MagicMock(spec=subprocess.Popen, pid=12345)
        mock_proc.pid = 999
        mock_proc.poll.return_value = 0
        chrome = ChromeProcess(mock_proc, port=9222)
        assert "stopped" in repr(chrome)


# ---------------------------------------------------------------------------
# launch_chrome
# ---------------------------------------------------------------------------


class TestLaunchChrome:
    """Tests for Chrome launch with profiles."""

    @patch("naturo.browser._launcher._wait_for_cdp")
    @patch("subprocess.Popen")
    @patch("naturo.browser._launcher.find_chrome", return_value="/usr/bin/google-chrome")
    def test_basic_launch(self, mock_find, mock_popen, mock_wait):
        mock_proc = MagicMock()
        mock_proc.pid = 100
        mock_popen.return_value = mock_proc

        result = launch_chrome(port=9222)
        assert result.port == 9222
        assert result.pid == 100

        args = mock_popen.call_args[0][0]
        assert "/usr/bin/google-chrome" in args
        assert "--remote-debugging-port=9222" in args
        assert "about:blank" in args

    @patch("naturo.browser._launcher._wait_for_cdp")
    @patch("subprocess.Popen")
    @patch("naturo.browser._launcher.find_chrome", return_value="/usr/bin/google-chrome")
    def test_launch_headless(self, mock_find, mock_popen, mock_wait):
        mock_popen.return_value = MagicMock(pid=100)
        launch_chrome(headless=True)
        args = mock_popen.call_args[0][0]
        assert "--headless=new" in args

    @patch("naturo.browser._launcher._wait_for_cdp")
    @patch("subprocess.Popen")
    @patch("naturo.browser._launcher.find_chrome", return_value="/usr/bin/chrome")
    def test_launch_with_user_data_dir(self, mock_find, mock_popen, mock_wait):
        mock_popen.return_value = MagicMock(pid=100)
        launch_chrome(user_data_dir="/tmp/my-profile")
        args = mock_popen.call_args[0][0]
        assert "--user-data-dir=/tmp/my-profile" in args

    @patch("naturo.browser._launcher._wait_for_cdp")
    @patch("subprocess.Popen")
    @patch("naturo.browser._launcher.find_chrome", return_value="/usr/bin/chrome")
    def test_launch_with_user_data_dir_and_profile(self, mock_find, mock_popen, mock_wait):
        mock_popen.return_value = MagicMock(pid=100)
        launch_chrome(user_data_dir="/tmp/data", profile="Profile 1")
        args = mock_popen.call_args[0][0]
        assert "--user-data-dir=/tmp/data" in args
        assert "--profile-directory=Profile 1" in args

    @patch("naturo.browser._launcher._wait_for_cdp")
    @patch("subprocess.Popen")
    @patch("naturo.browser._launcher.find_chrome", return_value="/usr/bin/chrome")
    @patch("naturo.browser._launcher._resolve_profile_directory", return_value="Profile 1")
    def test_launch_with_named_profile(self, mock_resolve, mock_find, mock_popen, mock_wait):
        mock_popen.return_value = MagicMock(pid=100)
        launch_chrome(profile="Work")
        args = mock_popen.call_args[0][0]
        assert "--profile-directory=Profile 1" in args
        mock_resolve.assert_called_once_with("Work")

    @patch("naturo.browser._launcher._wait_for_cdp")
    @patch("subprocess.Popen")
    @patch("naturo.browser._launcher.find_chrome", return_value="/usr/bin/chrome")
    @patch("naturo.browser._launcher._resolve_profile_directory", return_value=None)
    def test_launch_with_unresolved_profile_uses_literal(self, mock_resolve, mock_find, mock_popen, mock_wait):
        mock_popen.return_value = MagicMock(pid=100)
        launch_chrome(profile="CustomDir")
        args = mock_popen.call_args[0][0]
        assert "--profile-directory=CustomDir" in args

    @patch("naturo.browser._launcher._wait_for_cdp")
    @patch("subprocess.Popen")
    @patch("naturo.browser._launcher.find_chrome", return_value="/usr/bin/chrome")
    def test_launch_with_extra_args(self, mock_find, mock_popen, mock_wait):
        mock_popen.return_value = MagicMock(pid=100)
        launch_chrome(extra_args=["--disable-gpu", "--no-sandbox"])
        args = mock_popen.call_args[0][0]
        assert "--disable-gpu" in args
        assert "--no-sandbox" in args

    @patch("naturo.browser._launcher._wait_for_cdp")
    @patch("subprocess.Popen")
    @patch("naturo.browser._launcher.find_chrome", return_value="/usr/bin/chrome")
    def test_launch_with_url(self, mock_find, mock_popen, mock_wait):
        mock_popen.return_value = MagicMock(pid=100)
        launch_chrome(url="https://example.com")
        args = mock_popen.call_args[0][0]
        assert "https://example.com" in args
        assert "about:blank" not in args

    def test_launch_chrome_not_found(self):
        with patch("naturo.browser._launcher.find_chrome", return_value=None):
            with pytest.raises(FileNotFoundError, match="Chrome.*not found"):
                launch_chrome()

    @patch("subprocess.Popen", side_effect=OSError("Permission denied"))
    @patch("naturo.browser._launcher.find_chrome", return_value="/usr/bin/chrome")
    def test_launch_os_error(self, mock_find, mock_popen):
        with pytest.raises(FileNotFoundError, match="Failed to launch"):
            launch_chrome(wait_ready=False)

    @patch("naturo.browser._launcher._wait_for_cdp")
    @patch("subprocess.Popen")
    def test_launch_with_explicit_chrome_path(self, mock_popen, mock_wait):
        mock_popen.return_value = MagicMock(pid=100)
        launch_chrome(chrome_path="/custom/chrome")
        args = mock_popen.call_args[0][0]
        assert args[0] == "/custom/chrome"

    @patch("subprocess.Popen")
    @patch("naturo.browser._launcher.find_chrome", return_value="/usr/bin/chrome")
    def test_launch_no_wait(self, mock_find, mock_popen):
        mock_popen.return_value = MagicMock(pid=100)
        result = launch_chrome(wait_ready=False)
        assert result.pid == 100


# ---------------------------------------------------------------------------
# _wait_for_cdp
# ---------------------------------------------------------------------------


class TestWaitForCdp:
    """Tests for CDP readiness polling."""

    @patch("urllib.request.urlopen")
    def test_returns_when_ready(self, mock_urlopen):
        mock_urlopen.return_value.__enter__ = MagicMock()
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        _wait_for_cdp(9222, timeout=5.0)

    def test_raises_when_process_exits(self):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 1
        mock_proc.returncode = 1
        with pytest.raises(RuntimeError, match="Chrome exited"):
            _wait_for_cdp(9222, timeout=1.0, process=mock_proc)

    @patch("urllib.request.urlopen", side_effect=OSError("refused"))
    def test_raises_on_timeout(self, mock_urlopen):
        with pytest.raises(RuntimeError, match="not ready"):
            _wait_for_cdp(9222, timeout=0.5)


# ---------------------------------------------------------------------------
# CLI: browser launch
# ---------------------------------------------------------------------------


class TestLaunchCli:
    """Tests for 'naturo browser launch' command."""

    @patch("naturo.browser._launcher.launch_chrome")
    def test_launch_basic(self, mock_launch, runner):
        mock_proc = MagicMock()
        mock_proc.pid = 999
        mock_proc.port = 9222
        mock_launch.return_value = mock_proc

        result = runner.invoke(browser, ["launch"])
        assert result.exit_code == 0
        assert "999" in result.output
        assert "9222" in result.output

    @patch("naturo.browser._launcher.launch_chrome")
    def test_launch_json_output(self, mock_launch, runner):
        mock_proc = MagicMock()
        mock_proc.pid = 999
        mock_proc.port = 9222
        mock_launch.return_value = mock_proc

        result = runner.invoke(browser, ["launch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # Standard success envelope (#879): success boolean, not status string.
        assert data["success"] is True
        assert "status" not in data
        assert data["action"] == "browser_launch"
        assert data["pid"] == 999
        assert data["port"] == 9222
        assert data["profile"] is None

    @patch("naturo.browser._launcher.launch_chrome")
    def test_launch_json_includes_profile(self, mock_launch, runner):
        mock_proc = MagicMock()
        mock_proc.pid = 999
        mock_proc.port = 9222
        mock_launch.return_value = mock_proc

        result = runner.invoke(browser, ["launch", "--json", "--profile", "Work"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["profile"] == "Work"

    @patch("naturo.browser._launcher.launch_chrome",
           side_effect=RuntimeError("Chrome exited with code 0 before CDP became available"))
    def test_launch_json_error_exits_nonzero(self, mock_launch, runner):
        """A failed launch must emit the error envelope AND exit non-zero (#879).

        Scripted callers rely on ``if naturo browser launch -j; then`` — a
        zero exit code on failure makes the shell treat a broken launch as
        success.
        """
        result = runner.invoke(browser, ["launch", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert "error" in data

    @patch("naturo.browser._launcher.launch_chrome", side_effect=FileNotFoundError("Chrome not found"))
    def test_launch_chrome_not_found_cli(self, mock_launch, runner):
        result = runner.invoke(browser, ["launch"])
        assert result.exit_code != 0

    @patch("naturo.browser._launcher.launch_chrome")
    def test_launch_with_profile_text(self, mock_launch, runner):
        mock_proc = MagicMock()
        mock_proc.pid = 999
        mock_proc.port = 9222
        mock_launch.return_value = mock_proc

        result = runner.invoke(browser, ["launch", "--profile", "Work"])
        assert result.exit_code == 0
        assert "Work" in result.output

    def test_launch_help(self, runner):
        result = runner.invoke(browser, ["launch", "--help"])
        assert result.exit_code == 0
        assert "--profile" in result.output
        assert "--user-data-dir" in result.output
        assert "--headless" in result.output
        assert "--stealth" in result.output

    def test_launch_has_chrome_path_option(self, runner):
        result = runner.invoke(browser, ["launch", "--help"])
        assert "--chrome-path" in result.output


# ---------------------------------------------------------------------------
# CLI: browser profiles
# ---------------------------------------------------------------------------


class TestProfilesCli:
    """Tests for 'naturo browser profiles' command."""

    def test_profiles_help(self, runner):
        result = runner.invoke(browser, ["profiles", "--help"])
        assert result.exit_code == 0
        assert "--user-data-dir" in result.output

    @patch("naturo.browser._launcher.list_profiles")
    def test_profiles_empty(self, mock_list, runner):
        mock_list.return_value = []
        result = runner.invoke(browser, ["profiles"])
        assert result.exit_code == 0
        assert "No Chrome profiles found" in result.output

    @patch("naturo.browser._launcher.list_profiles")
    def test_profiles_json(self, mock_list, runner):
        mock_list.return_value = [
            {"directory": "Default", "name": "Personal", "path": "/tmp/Default"},
            {"directory": "Profile 1", "name": "Work", "path": "/tmp/Profile 1"},
        ]
        result = runner.invoke(browser, ["profiles", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["count"] == 2
        assert len(data["profiles"]) == 2

    @patch("naturo.browser._launcher.list_profiles")
    def test_profiles_text_output(self, mock_list, runner):
        mock_list.return_value = [
            {"directory": "Default", "name": "Personal", "path": "/tmp/Default"},
        ]
        result = runner.invoke(browser, ["profiles"])
        assert result.exit_code == 0
        assert "Personal" in result.output
        assert "Default" in result.output
