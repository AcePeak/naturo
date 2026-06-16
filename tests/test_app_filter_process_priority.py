"""Tests for --app matching priority (#465, #671).

When --app is used, process name and aliases are matched first.  If no
process name match is found, window title is tried as a fallback (#671).
This allows `--app claude` to find a Terminal window titled "claude"
while still preventing cross-process contamination when a process name
match exists (#465).
"""

import pytest
from naturo.backends.windows import WindowsBackend
from naturo.backends.base import WindowInfo
from naturo.errors import WindowNotFoundError


def _make_backend(monkeypatch, windows):
    """Create a WindowsBackend with mocked window list."""
    backend = WindowsBackend()
    monkeypatch.setattr(backend, "list_windows", lambda: windows)
    monkeypatch.setattr("naturo.backends.windows._element._app_discovery._get_console_session_id", lambda: 1)
    monkeypatch.setattr("naturo.backends.windows._element._app_discovery._get_process_session_id", lambda pid: 1)
    return backend


class TestAppFilterProcessPriority:
    """--app prefers process name matches; falls back to title (#465, #671)."""

    def test_chrome_with_notepad_in_title_matched_as_fallback(self, monkeypatch):
        """--app notepad matches Chrome window with 'notepad' in title when
        no notepad.exe is running (#671 title fallback)."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="get help with notepad in windows - Google Chrome",
                process_name="chrome.exe",
                pid=100,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
        ])
        result = backend._resolve_hwnd(app="notepad")
        assert result == 1000, "Title fallback should match when no process matches"

    def test_notepad_process_still_matched(self, monkeypatch):
        """--app notepad should match notepad.exe process name."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="get help with notepad in windows - Google Chrome",
                process_name="chrome.exe",
                pid=100,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=2000,
                title="Untitled - Notepad",
                process_name="notepad.exe",
                pid=200,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        result = backend._resolve_hwnd(app="notepad")
        assert result == 2000, "Should match notepad.exe, not chrome.exe"

    def test_title_match_ignored_when_no_process_match(self, monkeypatch):
        """When app is not running, title-only match should be rejected."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="Notepad++ - my_file.txt",
                process_name="notepad++.exe",
                pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        # "notepad" is a substring of "notepad++" process name → should match
        result = backend._resolve_hwnd(app="notepad")
        assert result == 1000, "Substring process name match should still work"

    def test_exact_title_match_used_as_fallback(self, monkeypatch):
        """Exact title match should work as fallback when no process matches (#671)."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="Calculator",
                process_name="chrome.exe",
                pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        # Chrome window with exact title "Calculator" should match via title
        # fallback when no "Calculator" process exists
        result = backend._resolve_hwnd(app="Calculator")
        assert result == 1000, "Exact title fallback should match"

    def test_process_match_wins_over_title_match(self, monkeypatch):
        """Process name match must always win over title-only match (#465)."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="help with notepad",
                process_name="chrome.exe",
                pid=100,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=2000,
                title="Untitled - Notepad",
                process_name="notepad.exe",
                pid=200,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        # When notepad.exe is running, --app notepad should match it,
        # NOT the Chrome window with "notepad" in title
        result = backend._resolve_hwnd(app="notepad")
        assert result == 2000, "Process name match must beat title match"

    def test_alias_still_matches_process(self, monkeypatch):
        """Alias matching should still work for process names."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="计算器",
                process_name="CalculatorApp.exe",
                pid=100,
                x=0, y=0, width=400, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        # "calculator" → alias "calculatorapp" → process match
        result = backend._resolve_hwnd(app="calculator")
        assert result == 1000, "Alias → process name matching should still work"

    def test_window_title_flag_still_works(self, monkeypatch):
        """--window-title should still match by title."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="get help with notepad in windows",
                process_name="chrome.exe",
                pid=100,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
        ])
        # Using window_title (not app) should match
        result = backend._resolve_hwnd(window_title="notepad")
        assert result == 1000, "--window-title should still match by title"


class TestAppTitleFallback:
    """--app falls back to window title matching when no process matches (#671)."""

    def test_app_matches_terminal_by_window_title(self, monkeypatch):
        """--app claude should find Terminal window titled 'claude' (#671)."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="claude",
                process_name="WindowsTerminal.exe",
                pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=2000,
                title="GitHub API investigation",
                process_name="WindowsTerminal.exe",
                pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=3000,
                title="Review issue #500",
                process_name="WindowsTerminal.exe",
                pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        result = backend._resolve_hwnd(app="claude")
        assert result == 1000, "--app claude should match Terminal window titled 'claude'"

    def test_app_matches_partial_title(self, monkeypatch):
        """--app GitHub should find Terminal window with 'GitHub' in title (#671)."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="claude",
                process_name="WindowsTerminal.exe",
                pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=2000,
                title="GitHub API investigation",
                process_name="WindowsTerminal.exe",
                pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        result = backend._resolve_hwnd(app="GitHub")
        assert result == 2000, "--app GitHub should match window with 'GitHub' in title"

    def test_resolve_hwnds_title_fallback(self, monkeypatch):
        """_resolve_hwnds should also fall back to title matching (#671)."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="claude - work session",
                process_name="WindowsTerminal.exe",
                pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=2000,
                title="other task",
                process_name="WindowsTerminal.exe",
                pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        result = backend._resolve_hwnds(app="claude")
        assert result == [1000], "_resolve_hwnds should find window by title fallback"

    def test_no_match_still_raises(self, monkeypatch):
        """When neither process nor title matches, should still raise."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="Untitled - Notepad",
                process_name="notepad.exe",
                pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        with pytest.raises(WindowNotFoundError):
            backend._resolve_hwnd(app="nonexistent_app_xyz")


class TestResolveHwndsProcessPriority:
    """_resolve_hwnds prefers process name matches; title is fallback."""

    def test_bulk_resolve_process_over_title(self, monkeypatch):
        """_resolve_hwnds should prefer process-name matches over title (#465)."""
        backend = _make_backend(monkeypatch, [
            WindowInfo(
                handle=1000,
                title="help with notepad",
                process_name="chrome.exe",
                pid=100,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=2000,
                title="Untitled - Notepad",
                process_name="notepad.exe",
                pid=200,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ])
        result = backend._resolve_hwnds(app="notepad")
        assert result == [2000], "Process-name matches should take priority"
