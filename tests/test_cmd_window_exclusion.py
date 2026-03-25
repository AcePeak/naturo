"""Tests for cmd/powershell window title match exclusion (Issue #315)."""
import pytest
from naturo.backends.windows import WindowsBackend
from naturo.backends.base import WindowInfo


class TestCmdWindowExclusion:
    """Verify terminal windows are excluded from title substring matching."""

    def test_cmd_window_not_matched_by_title_substring(self, monkeypatch):
        """cmd.exe windows should not match via title substring when using --app."""
        backend = WindowsBackend()

        # Mock list_windows to return a cmd window with the search term in title
        # and a real app window
        def mock_list_windows():
            return [
                WindowInfo(
                    handle=1000,
                    title="Administrator: Command Prompt - naturo see --app MyApp",
                    process_name="cmd.exe",
                    pid=100,
                    x=0, y=0, width=800, height=600,
                    is_visible=True,
                    is_minimized=False,
                ),
                WindowInfo(
                    handle=2000,
                    title="MyApp - Main Window",
                    process_name="MyApp.exe",
                    pid=200,
                    x=0, y=0, width=800, height=600,
                    is_visible=True,
                    is_minimized=False,
                ),
            ]

        def mock_console_session():
            return 1

        def mock_process_session(pid):
            return 1

        monkeypatch.setattr(backend, "list_windows", mock_list_windows)
        monkeypatch.setattr(backend, "_get_console_session_id", mock_console_session)
        monkeypatch.setattr(backend, "_get_process_session_id", mock_process_session)

        # _resolve_hwnd with --app "MyApp" should match the real MyApp, NOT cmd
        result = backend._resolve_hwnd(app="MyApp")
        assert result == 2000, "Should match MyApp.exe, not cmd.exe"

    def test_powershell_window_not_matched_by_title_substring(self, monkeypatch):
        """powershell.exe windows should not match via title substring."""
        backend = WindowsBackend()

        def mock_list_windows():
            return [
                WindowInfo(
                    handle=3000,
                    title="Windows PowerShell - naturo see --app Calculator",
                    process_name="powershell.exe",
                    pid=300,
                    x=0, y=0, width=800, height=600,
                    is_visible=True,
                    is_minimized=False,
                ),
                WindowInfo(
                    handle=4000,
                    title="Calculator",
                    process_name="Calculator.exe",
                    pid=400,
                    x=0, y=0, width=800, height=600,
                    is_visible=True,
                    is_minimized=False,
                ),
            ]

        def mock_console_session():
            return 1

        def mock_process_session(pid):
            return 1

        monkeypatch.setattr(backend, "list_windows", mock_list_windows)
        monkeypatch.setattr(backend, "_get_console_session_id", mock_console_session)
        monkeypatch.setattr(backend, "_get_process_session_id", mock_process_session)

        result = backend._resolve_hwnd(app="Calculator")
        assert result == 4000, "Should match Calculator.exe, not powershell.exe"

    def test_conhost_window_not_matched_by_title_substring(self, monkeypatch):
        """conhost.exe windows should not match via title substring."""
        backend = WindowsBackend()

        def mock_list_windows():
            return [
                WindowInfo(
                    handle=5000,
                    title="Terminal - naturo see --app Notepad",
                    process_name="conhost.exe",
                    pid=500,
                    x=0, y=0, width=800, height=600,
                    is_visible=True,
                    is_minimized=False,
                ),
                WindowInfo(
                    handle=6000,
                    title="Untitled - Notepad",
                    process_name="notepad.exe",
                    pid=600,
                    x=0, y=0, width=800, height=600,
                    is_visible=True,
                    is_minimized=False,
                ),
            ]

        def mock_console_session():
            return 1

        def mock_process_session(pid):
            return 1

        monkeypatch.setattr(backend, "list_windows", mock_list_windows)
        monkeypatch.setattr(backend, "_get_console_session_id", mock_console_session)
        monkeypatch.setattr(backend, "_get_process_session_id", mock_process_session)

        result = backend._resolve_hwnd(app="Notepad")
        assert result == 6000, "Should match notepad.exe, not conhost.exe"

    def test_cmd_can_still_be_matched_by_process_name(self, monkeypatch):
        """Explicitly targeting cmd by process name should still work."""
        backend = WindowsBackend()

        def mock_list_windows():
            return [
                WindowInfo(
                    handle=7000,
                    title="Administrator: Command Prompt",
                    process_name="cmd.exe",
                    pid=700,
                    x=0, y=0, width=800, height=600,
                    is_visible=True,
                    is_minimized=False,
                ),
            ]

        def mock_console_session():
            return 1

        def mock_process_session(pid):
            return 1

        monkeypatch.setattr(backend, "list_windows", mock_list_windows)
        monkeypatch.setattr(backend, "_get_console_session_id", mock_console_session)
        monkeypatch.setattr(backend, "_get_process_session_id", mock_process_session)

        # --app "cmd" should still match cmd.exe by process name
        result = backend._resolve_hwnd(app="cmd")
        assert result == 7000, "Should match cmd.exe when explicitly targeted"
