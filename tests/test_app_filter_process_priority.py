"""Tests for --app process-name-only matching (#465).

When --app is used, matching should only consider process name and aliases,
NOT window title.  Title-only matches caused cross-process contamination:
e.g. --app notepad picking a Chrome window titled "help with notepad".
"""

import pytest
from naturo.backends.windows import WindowsBackend
from naturo.backends.base import WindowInfo
from naturo.errors import WindowNotFoundError


def _make_backend(monkeypatch, windows):
    """Create a WindowsBackend with mocked window list."""
    backend = WindowsBackend()
    monkeypatch.setattr(backend, "list_windows", lambda: windows)
    monkeypatch.setattr(backend, "_get_console_session_id", lambda: 1)
    monkeypatch.setattr(backend, "_get_process_session_id", lambda pid: 1)
    return backend


class TestAppFilterRejectsTitle:
    """--app should NOT match by window title alone."""

    def test_chrome_with_notepad_in_title_not_matched(self, monkeypatch):
        """--app notepad must NOT match a Chrome window with 'notepad' in title."""
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
        with pytest.raises(WindowNotFoundError):
            backend._resolve_hwnd(app="notepad")

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

    def test_exact_title_match_ignored_for_app(self, monkeypatch):
        """Even exact title match should not trigger for --app."""
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
        # Chrome window with exact title "Calculator" should NOT match --app calculator
        with pytest.raises(WindowNotFoundError):
            backend._resolve_hwnd(app="Calculator")

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


class TestResolveHwndsRejectsTitle:
    """_resolve_hwnds with --app should also reject title-only matches."""

    def test_bulk_resolve_no_title_matches(self, monkeypatch):
        """_resolve_hwnds should not include title-only matches for --app."""
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
        assert result == [2000], "Only process-name matches should be included"
