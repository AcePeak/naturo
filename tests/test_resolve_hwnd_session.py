"""Tests for session-aware window resolution in _resolve_hwnd (#230).

These tests mock the Windows backend to verify that _resolve_hwnd prefers
windows in the active console session over windows in Session 0 (the
non-interactive services session).  This prevents schtasks/remote contexts
from targeting ghost processes.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from naturo.backends.base import WindowInfo


def _make_backend():
    """Create a WindowsBackend-like object for testing _resolve_hwnd.

    Since we can't import WindowsBackend on non-Windows (it needs
    naturo_core.dll), we test the logic via the actual class with mocked
    internals.
    """
    try:
        from naturo.backends.windows import WindowsBackend
        return WindowsBackend
    except Exception:
        pytest.skip("WindowsBackend not available on this platform")


class TestResolveHwndSessionAwareness:
    """Verify _resolve_hwnd prefers interactive session windows."""

    def _make_windows(self):
        """Two Notepad windows: one in Session 0, one in Session 1."""
        return [
            WindowInfo(
                handle=1001, title="Untitled - Notepad",
                process_name="Notepad.exe", pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=2002, title="Untitled - Notepad",
                process_name="Notepad.exe", pid=200,
                x=100, y=100, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ]

    def test_prefers_console_session_window(self):
        """When two windows match equally, prefer the one in console session."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.list_windows = MagicMock(return_value=self._make_windows())

        # Bind the real method to our mock
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        backend._get_console_session_id = MagicMock(return_value=1)
        backend._get_process_session_id = MagicMock(
            side_effect=lambda pid: 0 if pid == 100 else 1
        )
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        result = backend._resolve_hwnd(app="notepad")
        # Should pick handle 2002 (PID 200, Session 1) not 1001 (PID 100, Session 0)
        assert result == 2002

    def test_falls_back_when_session_unknown(self):
        """When console session is unknown, use title-length heuristic."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)

        windows = [
            WindowInfo(
                handle=1001, title="Untitled - Notepad",
                process_name="Notepad.exe", pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=2002, title="Notepad",
                process_name="Notepad.exe", pid=200,
                x=100, y=100, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ]
        backend.list_windows = MagicMock(return_value=windows)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        backend._get_console_session_id = MagicMock(return_value=-1)
        backend._get_process_session_id = MagicMock(return_value=-1)
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        result = backend._resolve_hwnd(app="notepad")
        # Both match equally on process name; PID 200 has shorter title
        assert result == 2002

    def test_higher_score_wins_over_session(self):
        """A higher match score should win even if in Session 0."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)

        windows = [
            WindowInfo(
                handle=1001, title="Some Notepad Thing",
                process_name="other.exe", pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=2002, title="Untitled",
                process_name="Notepad.exe", pid=200,
                x=100, y=100, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ]
        backend.list_windows = MagicMock(return_value=windows)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        backend._get_console_session_id = MagicMock(return_value=1)
        # PID 100 in console, PID 200 in Session 0
        backend._get_process_session_id = MagicMock(
            side_effect=lambda pid: 1 if pid == 100 else 0
        )
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        result = backend._resolve_hwnd(app="notepad")
        # PID 200 has exact process name match (score 4),
        # PID 100 only has title substring (score 1).
        # Higher score wins regardless of session.
        assert result == 2002
