"""Tests for the macOS Peekaboo backend wrapper.

These tests mock subprocess calls to verify the backend correctly
translates naturo API calls into Peekaboo CLI invocations.
"""
from __future__ import annotations

import json
import platform
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from naturo.backends.macos import MacOSBackend, PeekabooError
from naturo.backends.base import CaptureResult, ElementInfo, MonitorInfo, WindowInfo
from naturo.errors import NaturoError, WindowNotFoundError


# Skip all tests if not testing macOS backend (can run on any platform via mocks)
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _make_result(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Create a mock subprocess.CompletedProcess."""
    return subprocess.CompletedProcess(
        args=["peekaboo"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _json_result(data: dict, returncode: int = 0):
    """Create a mock result with JSON stdout."""
    return _make_result(stdout=json.dumps(data), returncode=returncode)


class TestMacOSBackendInit:
    """Test backend initialization."""

    def test_platform_name(self):
        """Backend reports 'macos' platform."""
        backend = MacOSBackend()
        assert backend.platform_name == "macos"

    def test_capabilities_with_peekaboo(self):
        """Capabilities show peekaboo_available when installed."""
        with patch("shutil.which", return_value="/usr/local/bin/peekaboo"):
            backend = MacOSBackend()
            caps = backend.capabilities
            assert caps["peekaboo_available"] is True
            assert caps["platform"] == "macos"
            assert "ax" in caps["accessibility"]

    def test_capabilities_without_peekaboo(self):
        """Capabilities show peekaboo_available=False when not installed."""
        with patch("shutil.which", return_value=None):
            backend = MacOSBackend()
            caps = backend.capabilities
            assert caps["peekaboo_available"] is False

    def test_require_peekaboo_raises(self):
        """_require_peekaboo raises NaturoError when not installed."""
        with patch("shutil.which", return_value=None):
            backend = MacOSBackend()
            with pytest.raises(NaturoError, match="Peekaboo is not installed"):
                backend._require_peekaboo()


class TestRunCommand:
    """Test the internal _run method."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_run_success(self, mock_which):
        """Successful command returns parsed JSON."""
        backend = MacOSBackend()
        response = {"success": True, "data": {"value": 42}}

        with patch("subprocess.run", return_value=_json_result(response)):
            result = backend._run(["test", "cmd"])
            assert result == response

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_run_adds_json_flag(self, mock_which):
        """_run always appends --json to command."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend._run(["test", "cmd"])
            called_args = mock_run.call_args[0][0]
            assert "--json" in called_args
            assert called_args[0] == "/usr/local/bin/peekaboo"
            assert called_args[1] == "test"
            assert called_args[2] == "cmd"

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_run_timeout(self, mock_which):
        """Timeout raises PeekabooError."""
        backend = MacOSBackend()

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            with pytest.raises(PeekabooError, match="timed out"):
                backend._run(["test"], timeout=30)

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_run_nonzero_exit(self, mock_which):
        """Non-zero exit with non-JSON output raises PeekabooError."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_make_result(
            stderr="Error: something failed", returncode=1
        )):
            with pytest.raises(PeekabooError, match="something failed"):
                backend._run(["test"])

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_run_error_response(self, mock_which):
        """Error in JSON response raises PeekabooError."""
        backend = MacOSBackend()
        response = {
            "success": False,
            "error": {"code": "WINDOW_NOT_FOUND", "message": "Window not found"}
        }

        with patch("subprocess.run", return_value=_json_result(response, returncode=1)):
            with pytest.raises(PeekabooError, match="Window not found"):
                backend._run(["test"])

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_run_os_error(self, mock_which):
        """OSError raises PeekabooError."""
        backend = MacOSBackend()

        with patch("subprocess.run", side_effect=OSError("exec failed")):
            with pytest.raises(PeekabooError, match="Failed to run Peekaboo"):
                backend._run(["test"])


class TestListApps:
    """Test application listing."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_list_apps(self, mock_which):
        """list_apps returns normalized app list."""
        backend = MacOSBackend()
        response = {
            "data": {
                "applications": [
                    {
                        "name": "Safari",
                        "processIdentifier": 1234,
                        "bundleIdentifier": "com.apple.Safari",
                        "bundlePath": "/Applications/Safari.app",
                        "isActive": True,
                        "isHidden": False,
                        "windowCount": 2,
                    },
                    {
                        "name": "Finder",
                        "processIdentifier": 100,
                        "bundleIdentifier": "com.apple.finder",
                        "bundlePath": "/System/Library/CoreServices/Finder.app",
                        "isActive": False,
                        "isHidden": False,
                        "windowCount": 1,
                    },
                ]
            }
        }

        with patch("subprocess.run", return_value=_json_result(response)):
            apps = backend.list_apps()
            assert len(apps) == 2
            assert apps[0]["name"] == "Safari"
            assert apps[0]["pid"] == 1234
            assert apps[0]["is_active"] is True
            assert apps[1]["name"] == "Finder"
            assert apps[1]["bundle_id"] == "com.apple.finder"


class TestLaunchApp:
    """Test application launching."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_launch_app(self, mock_which):
        """launch_app calls peekaboo app launch."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.launch_app("Safari")
            args = mock_run.call_args[0][0]
            assert "app" in args
            assert "launch" in args
            assert "Safari" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_launch_empty_name(self, mock_which):
        """launch_app with empty name raises NaturoError."""
        backend = MacOSBackend()
        with pytest.raises(NaturoError, match="Application name is required"):
            backend.launch_app("")

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_launch_not_found(self, mock_which):
        """launch_app raises NaturoError for unknown app."""
        backend = MacOSBackend()
        response = {
            "success": False,
            "error": {"code": "APP_NOT_FOUND", "message": "Application not found: xyz"}
        }

        with patch("subprocess.run", return_value=_json_result(response, returncode=1)):
            with pytest.raises(NaturoError, match="Application not found"):
                backend.launch_app("xyz")


class TestQuitApp:
    """Test application quitting."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_quit_app(self, mock_which):
        """quit_app calls peekaboo app quit."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.quit_app("Safari")
            args = mock_run.call_args[0][0]
            assert "app" in args
            assert "quit" in args
            assert "--app" in args
            assert "Safari" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_quit_app_force(self, mock_which):
        """quit_app with force passes --force flag."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.quit_app("Safari", force=True)
            args = mock_run.call_args[0][0]
            assert "--force" in args


class TestWindowManagement:
    """Test window management operations."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_focus_window_by_title(self, mock_which):
        """focus_window with title calls peekaboo window focus --app."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.focus_window(title="Safari")
            args = mock_run.call_args[0][0]
            assert "window" in args
            assert "focus" in args
            assert "--app" in args
            assert "Safari" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_focus_window_by_hwnd(self, mock_which):
        """focus_window with hwnd calls peekaboo window focus --window-id."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.focus_window(hwnd=12345)
            args = mock_run.call_args[0][0]
            assert "--window-id" in args
            assert "12345" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_focus_window_not_found(self, mock_which):
        """focus_window raises WindowNotFoundError for unknown window."""
        backend = MacOSBackend()
        response = {
            "success": False,
            "error": {"code": "WINDOW_NOT_FOUND", "message": "Window not found"}
        }

        with patch("subprocess.run", return_value=_json_result(response, returncode=1)):
            with pytest.raises(WindowNotFoundError, match="Window not found"):
                backend.focus_window(title="NonExistent")

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_close_window(self, mock_which):
        """close_window calls peekaboo window close."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.close_window(title="TextEdit")
            args = mock_run.call_args[0][0]
            assert "window" in args
            assert "close" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_minimize_window(self, mock_which):
        """minimize_window calls peekaboo window minimize."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.minimize_window(title="Finder")
            args = mock_run.call_args[0][0]
            assert "minimize" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_maximize_window(self, mock_which):
        """maximize_window calls peekaboo window maximize."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.maximize_window(title="Terminal")
            args = mock_run.call_args[0][0]
            assert "maximize" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_move_window(self, mock_which):
        """move_window passes coordinates to peekaboo."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.move_window(x=100, y=200, title="Safari")
            args = mock_run.call_args[0][0]
            assert "move" in args
            assert "--x" in args
            assert "100" in args
            assert "--y" in args
            assert "200" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_resize_window(self, mock_which):
        """resize_window passes dimensions to peekaboo."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.resize_window(width=1024, height=768, title="Chrome")
            args = mock_run.call_args[0][0]
            assert "resize" in args
            assert "--width" in args
            assert "1024" in args
            assert "--height" in args
            assert "768" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_set_bounds(self, mock_which):
        """set_bounds passes all four dimensions."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.set_bounds(x=50, y=50, width=800, height=600, title="Notes")
            args = mock_run.call_args[0][0]
            assert "set-bounds" in args
            assert "50" in args
            assert "800" in args
            assert "600" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_restore_window(self, mock_which):
        """restore_window calls app unhide."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.restore_window(title="Finder")
            args = mock_run.call_args[0][0]
            assert "app" in args
            assert "unhide" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_window_no_identifier(self, mock_which):
        """Window operations without title or hwnd raise NaturoError."""
        backend = MacOSBackend()
        with pytest.raises(NaturoError, match="must be specified"):
            backend.focus_window()


class TestListWindows:
    """Test window listing."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_list_windows(self, mock_which):
        """list_windows aggregates windows from all apps."""
        backend = MacOSBackend()
        apps_response = {
            "data": {
                "applications": [
                    {"name": "Safari", "processIdentifier": 100, "windowCount": 1},
                    {"name": "Finder", "processIdentifier": 200, "windowCount": 0},
                ]
            }
        }
        windows_response = {
            "data": {
                "windows": [
                    {
                        "windowId": 42,
                        "title": "Google",
                        "pid": 100,
                        "frame": {"x": 0, "y": 0, "width": 1200, "height": 800},
                        "isMinimized": False,
                    }
                ]
            }
        }

        def mock_run(cmd, **kwargs):
            if "app" in cmd and "list" in cmd:
                return _json_result(apps_response)
            return _json_result(windows_response)

        with patch("subprocess.run", side_effect=mock_run):
            windows = backend.list_windows()
            assert len(windows) == 1
            assert windows[0].title == "Google"
            assert windows[0].handle == 42
            assert windows[0].process_name == "Safari"
            assert windows[0].width == 1200


class TestInput:
    """Test input operations."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_click_coords(self, mock_which):
        """click with coordinates calls peekaboo click."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.click(x=100, y=200)
            args = mock_run.call_args[0][0]
            assert "click" in args
            assert "--x" in args
            assert "100" in args
            assert "--y" in args
            assert "200" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_click_element(self, mock_which):
        """click with element_id uses peekaboo element click."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.click(element_id="btn_save")
            args = mock_run.call_args[0][0]
            assert "click" in args
            assert "btn_save" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_click_right(self, mock_which):
        """click with button='right' passes --right."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.click(x=10, y=20, button="right")
            args = mock_run.call_args[0][0]
            assert "--right" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_click_double(self, mock_which):
        """click with double=True passes --double."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.click(x=10, y=20, double=True)
            args = mock_run.call_args[0][0]
            assert "--double" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_click_no_target(self, mock_which):
        """click without coordinates or element raises NaturoError."""
        backend = MacOSBackend()
        with pytest.raises(NaturoError, match="coordinates.*element_id"):
            backend.click()

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_type_text(self, mock_which):
        """type_text calls peekaboo type."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.type_text("Hello World")
            args = mock_run.call_args[0][0]
            assert "type" in args
            assert "Hello World" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_type_empty(self, mock_which):
        """type_text with empty string is a no-op."""
        backend = MacOSBackend()

        with patch("subprocess.run") as mock_run:
            backend.type_text("")
            mock_run.assert_not_called()

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_press_key(self, mock_which):
        """press_key calls peekaboo press."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.press_key("enter")
            args = mock_run.call_args[0][0]
            assert "press" in args
            assert "enter" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_hotkey(self, mock_which):
        """hotkey joins keys with + and calls peekaboo hotkey."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.hotkey("cmd", "s")
            args = mock_run.call_args[0][0]
            assert "hotkey" in args
            assert "cmd+s" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_scroll(self, mock_which):
        """scroll calls peekaboo scroll with direction and amount."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.scroll(direction="up", amount=5)
            args = mock_run.call_args[0][0]
            assert "scroll" in args
            assert "--direction" in args
            assert "up" in args
            assert "--amount" in args
            assert "5" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_drag(self, mock_which):
        """drag calls peekaboo drag with from/to coordinates."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.drag(from_x=10, from_y=20, to_x=300, to_y=400)
            args = mock_run.call_args[0][0]
            assert "drag" in args
            assert "--from-x" in args
            assert "10" in args
            assert "--to-x" in args
            assert "300" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_move_mouse(self, mock_which):
        """move_mouse calls peekaboo move."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.move_mouse(x=500, y=300)
            args = mock_run.call_args[0][0]
            assert "move" in args
            assert "--x" in args
            assert "500" in args


class TestClipboard:
    """Test clipboard operations."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_clipboard_get(self, mock_which):
        """clipboard_get returns text from peekaboo."""
        backend = MacOSBackend()
        response = {"data": {"text": "Hello clipboard"}}

        with patch("subprocess.run", return_value=_json_result(response)):
            assert backend.clipboard_get() == "Hello clipboard"

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_clipboard_set(self, mock_which):
        """clipboard_set calls peekaboo clipboard set."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.clipboard_set("Test text")
            args = mock_run.call_args[0][0]
            assert "clipboard" in args
            assert "set" in args
            assert "--text" in args
            assert "Test text" in args


class TestCapture:
    """Test screen/window capture."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_capture_screen(self, mock_which):
        """capture_screen returns CaptureResult."""
        backend = MacOSBackend()
        response = {"data": {"path": "/tmp/cap.png", "width": 1920, "height": 1080, "format": "png"}}

        with patch("subprocess.run", return_value=_json_result(response)):
            result = backend.capture_screen(output_path="/tmp/cap.png")
            assert isinstance(result, CaptureResult)
            assert result.width == 1920
            assert result.path == "/tmp/cap.png"

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_capture_window_by_title(self, mock_which):
        """capture_window with title uses --app."""
        backend = MacOSBackend()
        response = {"data": {"path": "/tmp/win.png", "width": 800, "height": 600, "format": "png"}}

        with patch("subprocess.run", return_value=_json_result(response)) as mock_run:
            result = backend.capture_window(window_title="Safari", output_path="/tmp/win.png")
            args = mock_run.call_args[0][0]
            assert "--app" in args
            assert "Safari" in args
            assert result.width == 800

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_capture_window_not_found(self, mock_which):
        """capture_window raises WindowNotFoundError for missing window."""
        backend = MacOSBackend()
        response = {
            "success": False,
            "error": {"code": "WINDOW_NOT_FOUND", "message": "Window not found: xyz"}
        }

        with patch("subprocess.run", return_value=_json_result(response, returncode=1)):
            with pytest.raises(WindowNotFoundError, match="Window not found"):
                backend.capture_window(window_title="xyz")


class TestElementInspection:
    """Test UI element inspection."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_find_element(self, mock_which):
        """find_element searches peekaboo see output."""
        backend = MacOSBackend()
        response = {
            "data": {
                "elements": [
                    {
                        "id": "btn1",
                        "role": "Button",
                        "name": "Save",
                        "frame": {"x": 100, "y": 200, "width": 80, "height": 30},
                        "children": [],
                    },
                    {
                        "id": "txt1",
                        "role": "TextField",
                        "name": "Search",
                        "frame": {"x": 10, "y": 10, "width": 200, "height": 25},
                        "children": [],
                    },
                ]
            }
        }

        with patch("subprocess.run", return_value=_json_result(response)):
            elem = backend.find_element("Save", window_title="Safari")
            assert elem is not None
            assert elem.name == "Save"
            assert elem.role == "Button"
            assert elem.x == 100

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_find_element_not_found(self, mock_which):
        """find_element returns None when element not found."""
        backend = MacOSBackend()
        response = {"data": {"elements": []}}

        with patch("subprocess.run", return_value=_json_result(response)):
            assert backend.find_element("NonExistent") is None

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_find_element_nested(self, mock_which):
        """find_element searches nested children."""
        backend = MacOSBackend()
        response = {
            "data": {
                "elements": [
                    {
                        "id": "toolbar",
                        "role": "Toolbar",
                        "name": "",
                        "frame": {"x": 0, "y": 0, "width": 800, "height": 40},
                        "children": [
                            {
                                "id": "btn_ok",
                                "role": "Button",
                                "name": "OK",
                                "frame": {"x": 700, "y": 5, "width": 60, "height": 30},
                                "children": [],
                            }
                        ],
                    }
                ]
            }
        }

        with patch("subprocess.run", return_value=_json_result(response)):
            elem = backend.find_element("OK")
            assert elem is not None
            assert elem.name == "OK"
            assert elem.id == "btn_ok"

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_get_element_tree(self, mock_which):
        """get_element_tree parses peekaboo see output."""
        backend = MacOSBackend()
        response = {
            "data": {
                "elements": [
                    {
                        "id": "win",
                        "role": "Window",
                        "name": "Main",
                        "frame": {"x": 0, "y": 0, "width": 800, "height": 600},
                        "children": [
                            {
                                "id": "btn",
                                "role": "Button",
                                "name": "Close",
                                "frame": {"x": 10, "y": 10, "width": 60, "height": 30},
                                "children": [],
                            }
                        ],
                    }
                ]
            }
        }

        with patch("subprocess.run", return_value=_json_result(response)):
            tree = backend.get_element_tree(window_title="Safari", depth=3)
            assert tree is not None
            assert tree.role == "Window"
            assert len(tree.children) == 1
            assert tree.children[0].name == "Close"


class TestOpenURI:
    """Test open URI functionality."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_open_url(self, mock_which):
        """open_uri calls peekaboo open."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.open_uri("https://example.com")
            args = mock_run.call_args[0][0]
            assert "open" in args
            # Exact-match membership (args is the argv list), not a URL substring
            # check — avoids a py/incomplete-url-substring-sanitization false positive.
            assert any(a == "https://example.com" for a in args)

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_open_empty(self, mock_which):
        """open_uri with empty string raises NaturoError."""
        backend = MacOSBackend()
        with pytest.raises(NaturoError, match="URI is required"):
            backend.open_uri("")


class TestDialog:
    """Test dialog operations."""

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_detect_dialogs(self, mock_which):
        """detect_dialogs returns list from peekaboo."""
        backend = MacOSBackend()
        response = {"data": {"dialogs": [{"title": "Save?", "buttons": ["Save", "Cancel"]}]}}

        with patch("subprocess.run", return_value=_json_result(response)):
            dialogs = backend.detect_dialogs()
            assert len(dialogs) == 1
            assert dialogs[0]["title"] == "Save?"

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_dialog_click_accept(self, mock_which):
        """dialog_click_button with 'OK' calls dialog accept."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.dialog_click_button("OK")
            args = mock_run.call_args[0][0]
            assert "dialog" in args
            assert "accept" in args

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    def test_dialog_click_dismiss(self, mock_which):
        """dialog_click_button with 'Cancel' calls dialog dismiss."""
        backend = MacOSBackend()

        with patch("subprocess.run", return_value=_json_result({"success": True})) as mock_run:
            backend.dialog_click_button("Cancel")
            args = mock_run.call_args[0][0]
            assert "dialog" in args
            assert "dismiss" in args
