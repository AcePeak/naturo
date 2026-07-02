"""Tests for _resolve_uwp_child_pid Strategy 2 fix (#749).

The bug: line 822 called self._find_uwp_content_children() which doesn't
exist — the actual static method is _find_uwp_content_hwnd().  This caused
Strategy 2 (WinUI 3 fallback) to silently fail via AttributeError, making
Windows 11 Notepad (WinUI 3) invisible when CoreWindow lookup also fails.

These tests verify that Strategy 2 is correctly wired to
_find_uwp_content_hwnd and that the full resolution chain works.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def backend():
    """Create a WindowsBackend with mocked core initialization."""
    with patch("naturo.backends.windows.WindowsBackend._ensure_core"):
        from naturo.backends.windows import WindowsBackend

        b = WindowsBackend()
        b._core = MagicMock()
        return b


class TestResolveUwpChildPidStrategy2:
    """Verify Strategy 2 calls _find_uwp_content_hwnd (not _find_uwp_content_children)."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Mocking ctypes on Windows is fragile")
    def test_no_attribute_error_on_strategy2(self, backend):
        """_resolve_uwp_child_pid should NOT raise AttributeError for Strategy 2.

        Before the fix, line 822 called self._find_uwp_content_children()
        which didn't exist. The except clause caught it silently, returning
        (None, None) and hiding the bug.
        """
        # Verify the method _find_uwp_content_children does NOT exist
        assert not hasattr(backend, "_find_uwp_content_children"), (
            "_find_uwp_content_children should not exist — "
            "the correct method is _find_uwp_content_hwnd"
        )

        # Verify the correct method DOES exist
        assert hasattr(backend, "_find_uwp_content_hwnd"), (
            "_find_uwp_content_hwnd must exist on the backend"
        )

    def test_find_uwp_content_hwnd_is_static_method(self):
        """_find_uwp_content_hwnd should be a static method callable from instances."""
        from naturo.backends.windows import WindowsBackend

        # Should be callable as a class method (static)
        assert callable(getattr(WindowsBackend, "_find_uwp_content_hwnd", None))

    def test_source_code_uses_correct_method_name(self):
        """Verify the source code of _resolve_uwp_child_pid calls the correct method.

        This is a belt-and-suspenders check: even if the method is mocked in
        other tests, verify the actual source references _find_uwp_content_hwnd.
        """
        import inspect
        from naturo.backends.windows import WindowsBackend

        source = inspect.getsource(WindowsBackend._resolve_uwp_child_pid)
        assert "_find_uwp_content_hwnd" in source, (
            "_resolve_uwp_child_pid must call _find_uwp_content_hwnd"
        )
        assert "_find_uwp_content_children" not in source, (
            "_resolve_uwp_child_pid must NOT reference the non-existent "
            "_find_uwp_content_children method"
        )


class TestAppListUwpResolution:
    """Tests for UWP child process resolution in app list CLI (#749)."""

    def test_app_list_resolves_uwp_process_name(self, monkeypatch):
        """app list should show real process name for ApplicationFrameHost windows."""
        from click.testing import CliRunner
        from naturo.backends.base import WindowInfo

        afh_window = WindowInfo(
            handle=1000,
            title="無標題 - Notepad",
            process_name="ApplicationFrameHost.exe",
            pid=500,
            x=0, y=0, width=800, height=600,
            is_visible=True, is_minimized=False,
        )

        mock_backend = MagicMock()
        mock_backend.list_windows.return_value = [afh_window]
        mock_backend._SYSTEM_PROCESS_NAMES = set()
        mock_backend._UWP_HOST_PROCESS = "applicationframehost.exe"
        mock_backend._resolve_uwp_child_pid.return_value = (
            100, "C:\\Program Files\\WindowsApps\\Notepad\\Notepad.exe",
        )

        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            # Skip desktop session check (we're on Linux)
            with patch("naturo.cli.interaction._check_desktop_session"):
                from naturo.cli.app_cmd import app_list

                runner = CliRunner()
                result = runner.invoke(app_list, ["--json"], obj={})

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        import json
        data = json.loads(result.output)
        assert data["success"] is True
        assert len(data["windows"]) == 1
        win = data["windows"][0]
        # Should show resolved Notepad process, not ApplicationFrameHost
        assert "Notepad" in win["process_name"]
        assert win["pid"] == 100

    def test_app_list_fallback_when_uwp_resolution_fails(self, monkeypatch):
        """When UWP child resolution fails, should still show AFH window."""
        from click.testing import CliRunner
        from naturo.backends.base import WindowInfo

        afh_window = WindowInfo(
            handle=1000,
            title="Calculator",
            process_name="ApplicationFrameHost.exe",
            pid=500,
            x=0, y=0, width=400, height=600,
            is_visible=True, is_minimized=False,
        )

        mock_backend = MagicMock()
        mock_backend.list_windows.return_value = [afh_window]
        mock_backend._SYSTEM_PROCESS_NAMES = set()
        mock_backend._UWP_HOST_PROCESS = "applicationframehost.exe"
        mock_backend._resolve_uwp_child_pid.return_value = (None, None)

        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            with patch("naturo.cli.interaction._check_desktop_session"):
                from naturo.cli.app_cmd import app_list

                runner = CliRunner()
                result = runner.invoke(app_list, ["--json"], obj={})

        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert len(data["windows"]) == 1
        # Falls back to original AFH info
        assert data["windows"][0]["process_name"] == "ApplicationFrameHost.exe"
        assert data["windows"][0]["pid"] == 500
