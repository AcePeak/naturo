"""Tests for #789: --app must match process basename, not full path.

process_name from the backend may contain a full path
(e.g. C:\\Windows\\System32\\notepad.exe). Substring matching against the
full path caused --app system to incorrectly match any process in System32.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from naturo.backends.base import WindowInfo

_ELEMENT_MOD = "naturo.backends.windows._element"


def _make_backend():
    try:
        from naturo.backends.windows import WindowsBackend
        return WindowsBackend
    except Exception:
        pytest.skip("WindowsBackend not available on this platform")


def _windows_with_full_paths():
    """Windows whose process_name fields contain full executable paths."""
    return [
        WindowInfo(
            handle=1001, title="Untitled - Notepad",
            process_name=r"C:\Windows\System32\notepad.exe", pid=100,
            x=0, y=0, width=800, height=600,
            is_visible=True, is_minimized=False,
        ),
        WindowInfo(
            handle=2002, title="Google Chrome",
            process_name=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            pid=200,
            x=0, y=0, width=1200, height=800,
            is_visible=True, is_minimized=False,
        ),
    ]


class TestResolveHwndBasename:
    """_resolve_hwnd must extract basename before matching."""

    def test_app_notepad_matches_full_path(self):
        """--app notepad should match even when process_name is a full path."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.list_windows = MagicMock(return_value=_windows_with_full_paths())
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        backend._APP_ALIASES = BackendClass._APP_ALIASES
        backend._DESKTOP_SHELL_CLASSES = BackendClass._DESKTOP_SHELL_CLASSES
        backend._get_window_class_name = MagicMock(return_value="Notepad")
        backend._get_foreground_hwnd = MagicMock(return_value=0)

        with patch(f"{_ELEMENT_MOD}._get_console_session_id", return_value=-1), \
             patch(f"{_ELEMENT_MOD}._get_process_session_id", return_value=1):
            hwnd = backend._resolve_hwnd(app="notepad")
        assert hwnd == 1001

    def test_app_system_does_not_match_system32_path(self):
        """--app system must NOT match processes just because they're in System32."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.list_windows = MagicMock(return_value=_windows_with_full_paths())
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        backend._APP_ALIASES = BackendClass._APP_ALIASES
        backend._DESKTOP_SHELL_CLASSES = BackendClass._DESKTOP_SHELL_CLASSES
        backend._get_window_class_name = MagicMock(return_value="")
        backend._get_foreground_hwnd = MagicMock(return_value=0)
        # UWP fallback should not match either
        backend._uwp_afh_fallback = MagicMock(return_value=None)

        from naturo.errors import WindowNotFoundError
        with patch(f"{_ELEMENT_MOD}._get_console_session_id", return_value=-1), \
             patch(f"{_ELEMENT_MOD}._get_process_session_id", return_value=1):
            with pytest.raises(WindowNotFoundError):
                backend._resolve_hwnd(app="system")

    def test_app_program_does_not_match_program_files_path(self):
        """--app program must NOT match processes in Program Files."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.list_windows = MagicMock(return_value=_windows_with_full_paths())
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        backend._APP_ALIASES = BackendClass._APP_ALIASES
        backend._DESKTOP_SHELL_CLASSES = BackendClass._DESKTOP_SHELL_CLASSES
        backend._get_window_class_name = MagicMock(return_value="")
        backend._get_foreground_hwnd = MagicMock(return_value=0)
        backend._uwp_afh_fallback = MagicMock(return_value=None)

        from naturo.errors import WindowNotFoundError
        with patch(f"{_ELEMENT_MOD}._get_console_session_id", return_value=-1), \
             patch(f"{_ELEMENT_MOD}._get_process_session_id", return_value=1):
            with pytest.raises(WindowNotFoundError):
                backend._resolve_hwnd(app="program")


class TestResolveHwndsBasename:
    """_resolve_hwnds must also extract basename before matching."""

    def test_resolve_hwnds_uses_basename(self):
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.list_windows = MagicMock(return_value=_windows_with_full_paths())
        backend._resolve_hwnds = BackendClass._resolve_hwnds.__get__(backend)
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        with patch(f"{_ELEMENT_MOD}._get_console_session_id", return_value=-1), \
             patch(f"{_ELEMENT_MOD}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnds(app="notepad")
        assert 1001 in result

    def test_resolve_hwnds_no_path_component_match(self):
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.list_windows = MagicMock(return_value=_windows_with_full_paths())
        backend._resolve_hwnds = BackendClass._resolve_hwnds.__get__(backend)
        backend._APP_ALIASES = BackendClass._APP_ALIASES
        backend._uwp_afh_fallback = MagicMock(return_value=None)

        with patch(f"{_ELEMENT_MOD}._get_console_session_id", return_value=-1), \
             patch(f"{_ELEMENT_MOD}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnds(app="windows")
        assert result == []
