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

_SESSION_PATCH_BASE = "naturo.backends.windows._element"


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
        backend._get_foreground_hwnd = MagicMock(return_value=0)
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id",
                   side_effect=lambda pid: 0 if pid == 100 else 1):
            result = backend._resolve_hwnd(app="notepad")
        # Should pick handle 2002 (PID 200, Session 1) not 1001 (PID 100, Session 0)
        assert result == 2002

    def test_falls_back_when_session_unknown(self):
        """When console session is unknown, prefer larger window area (#440)."""
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
                x=100, y=100, width=1200, height=800,
                is_visible=True, is_minimized=False,
            ),
        ]
        backend.list_windows = MagicMock(return_value=windows)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        backend._get_foreground_hwnd = MagicMock(return_value=0)
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=-1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=-1):
            result = backend._resolve_hwnd(app="notepad")
        # Both match equally on process name; PID 200 has larger area
        assert result == 2002

    def test_popup_menu_not_selected_over_main_window(self):
        """(#440) Popup menu (tiny window) should not beat main window."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)

        windows = [
            WindowInfo(
                handle=3001, title="Untitled - Notepad",
                process_name="Notepad.exe", pid=300,
                x=100, y=100, width=1536, height=534,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=3002, title="X",
                process_name="Notepad.exe", pid=300,
                x=500, y=200, width=38, height=46,
                is_visible=True, is_minimized=False,
            ),
        ]
        backend.list_windows = MagicMock(return_value=windows)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        backend._get_foreground_hwnd = MagicMock(return_value=0)
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnd(app="notepad")
        # Main window (3001) has much larger area than popup (3002)
        assert result == 3001

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
        backend._get_foreground_hwnd = MagicMock(return_value=0)
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id",
                   side_effect=lambda pid: 1 if pid == 100 else 0):
            result = backend._resolve_hwnd(app="notepad")
        # PID 200 has exact process name match (score 4),
        # PID 100 only has title substring (score 1).
        # Higher score wins regardless of session.
        assert result == 2002


class TestResolveHwndForegroundPreference:
    """Verify _resolve_hwnd prefers the foreground window when scores are equal (#449)."""

    def test_foreground_window_preferred_among_equal_matches(self):
        """When multiple windows match identically, prefer the foreground one."""
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
                handle=2002, title="Document - Notepad",
                process_name="Notepad.exe", pid=200,
                x=100, y=100, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ]
        backend.list_windows = MagicMock(return_value=windows)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        # Window 2002 is the foreground window
        backend._get_foreground_hwnd = MagicMock(return_value=2002)
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnd(app="notepad")
        # Both match on process name (score 4), same session, same area.
        # Foreground window (2002) should win.
        assert result == 2002

    def test_foreground_window_preferred_even_when_listed_first(self):
        """Foreground preference works regardless of iteration order."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)

        windows = [
            WindowInfo(
                handle=2002, title="Document - Notepad",
                process_name="Notepad.exe", pid=200,
                x=100, y=100, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=1001, title="Untitled - Notepad",
                process_name="Notepad.exe", pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ]
        backend.list_windows = MagicMock(return_value=windows)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        # Window 1001 is the foreground window (listed second)
        backend._get_foreground_hwnd = MagicMock(return_value=1001)
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnd(app="notepad")
        # Foreground window 1001 should win even though it's listed second
        assert result == 1001

    def test_larger_area_still_wins_when_no_foreground(self):
        """When no foreground match, area tie-breaker still works."""
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
                handle=2002, title="Document - Notepad",
                process_name="Notepad.exe", pid=200,
                x=100, y=100, width=1200, height=800,
                is_visible=True, is_minimized=False,
            ),
        ]
        backend.list_windows = MagicMock(return_value=windows)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        # Foreground is some unrelated window
        backend._get_foreground_hwnd = MagicMock(return_value=9999)
        backend._APP_ALIASES = BackendClass._APP_ALIASES

        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnd(app="notepad")
        # Neither is foreground, so larger area (2002) wins
        assert result == 2002


class TestResolveHwndPid:
    """Verify _resolve_hwnd correctly handles --pid targeting (#471)."""

    def _make_multi_app_windows(self):
        """Three apps: Notepad (PID 100), Calculator (PID 200), Paint (PID 300)."""
        return [
            WindowInfo(
                handle=1001, title="Untitled - Notepad",
                process_name="Notepad.exe", pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=2002, title="Calculator",
                process_name="CalculatorApp.exe", pid=200,
                x=100, y=100, width=400, height=500,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=3003, title="Untitled - Paint",
                process_name="mspaint.exe", pid=300,
                x=200, y=200, width=1200, height=800,
                is_visible=True, is_minimized=False,
            ),
        ]

    def _setup_backend(self, windows, fg_hwnd=0):
        """Create a mock backend with the given windows."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.list_windows = MagicMock(return_value=windows)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        backend._get_foreground_hwnd = MagicMock(return_value=fg_hwnd)
        backend._APP_ALIASES = BackendClass._APP_ALIASES
        return backend

    def test_pid_alone_targets_correct_window(self):
        """--pid alone should target the specified process, not foreground."""
        backend = self._setup_backend(
            self._make_multi_app_windows(), fg_hwnd=3003,
        )
        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            # Paint (3003) is foreground, but --pid 200 should target Calculator
            result = backend._resolve_hwnd(pid=200)
        assert result == 2002

    def test_pid_alone_targets_notepad_not_foreground(self):
        """--pid for Notepad should work even when Paint is foreground."""
        backend = self._setup_backend(
            self._make_multi_app_windows(), fg_hwnd=3003,
        )
        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnd(pid=100)
        assert result == 1001

    def test_pid_with_app_filters_both(self):
        """--pid combined with --app should filter by both."""
        backend = self._setup_backend(self._make_multi_app_windows())
        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            # PID 200 is Calculator, --app calculator should also match
            result = backend._resolve_hwnd(app="calculator", pid=200)
        assert result == 2002

    def test_pid_selects_largest_window_among_process(self):
        """When a PID has multiple windows, prefer the largest."""
        windows = [
            WindowInfo(
                handle=1001, title="Untitled - Notepad",
                process_name="Notepad.exe", pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=1002, title="Find and Replace",
                process_name="Notepad.exe", pid=100,
                x=200, y=200, width=300, height=200,
                is_visible=True, is_minimized=False,
            ),
        ]
        backend = self._setup_backend(windows)
        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnd(pid=100)
        # Main window (1001) is larger → should be selected
        assert result == 1001

    def test_pid_not_found_raises_error(self):
        """--pid with no matching windows should raise WindowNotFoundError."""
        backend = self._setup_backend(self._make_multi_app_windows())
        from naturo.errors import WindowNotFoundError
        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            with pytest.raises(WindowNotFoundError, match="PID 999"):
                backend._resolve_hwnd(pid=999)

    def test_pid_none_without_search_returns_foreground(self):
        """When pid=None and no search term, return 0 (foreground)."""
        backend = self._setup_backend(self._make_multi_app_windows())
        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnd()
        assert result == 0

    def test_pid_with_hwnd_prefers_hwnd(self):
        """Direct hwnd takes priority over pid."""
        backend = self._setup_backend(self._make_multi_app_windows())
        # _is_hwnd_alive is mocked True so the #788 liveness guard does not
        # reject the synthetic handle on Windows, where IsWindow(9999) → 0
        # (#870).  This test isolates hwnd-over-pid priority, not liveness.
        with patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=True), \
             patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnd(hwnd=9999, pid=200)
        assert result == 9999

    def test_pid_prefers_foreground_among_same_process(self):
        """Among multiple windows of same PID, prefer the foreground one."""
        windows = [
            WindowInfo(
                handle=1001, title="Document1 - Notepad",
                process_name="Notepad.exe", pid=100,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=1002, title="Document2 - Notepad",
                process_name="Notepad.exe", pid=100,
                x=100, y=100, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ]
        # Window 1002 is foreground
        backend = self._setup_backend(windows, fg_hwnd=1002)
        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            result = backend._resolve_hwnd(pid=100)
        assert result == 1002


class TestResolveHwndStaleValidation:
    """#788: _resolve_hwnd rejects stale HWND parameters."""

    def test_stale_hwnd_raises_window_not_found(self):
        """When _is_hwnd_alive returns False, raise WindowNotFoundError."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)

        from naturo.errors import WindowNotFoundError
        with patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=False), \
             pytest.raises(WindowNotFoundError) as exc_info:
            backend._resolve_hwnd(hwnd=0xDEAD)
        assert "no longer valid" in exc_info.value.suggested_action.lower()

    def test_valid_hwnd_returned_directly(self):
        """When _is_hwnd_alive returns True, return HWND without error."""
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)

        with patch("naturo.cli.interaction._common._is_hwnd_alive", return_value=True):
            result = backend._resolve_hwnd(hwnd=0x1234)
        assert result == 0x1234

    @patch("sys.platform", "linux")
    def test_non_windows_skips_validation(self):
        """On non-Windows, _is_hwnd_alive returns True so HWND passes.

        ``sys.platform`` is forced to ``"linux"`` so the real ``_is_hwnd_alive``
        takes its non-Windows branch on any host — on Windows the genuine
        ``IsWindow(0x5678)`` would return 0 and wrongly raise (#870).
        """
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)

        result = backend._resolve_hwnd(hwnd=0x5678)
        assert result == 0x5678
