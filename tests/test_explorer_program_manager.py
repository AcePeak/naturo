"""Tests for explorer.exe desktop shell deprioritization (#524).

explorer.exe hosts both the desktop (Program Manager, class "Progman") and
File Explorer windows.  When --app explorer is used, _resolve_hwnd should
prefer actual File Explorer windows over the desktop.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from naturo.backends.base import WindowInfo


def _make_backend():
    """Create a WindowsBackend class for testing _resolve_hwnd."""
    try:
        from naturo.backends.windows import WindowsBackend
        return WindowsBackend
    except Exception:
        pytest.skip("WindowsBackend not available on this platform")


_SESSION_PATCH_BASE = "naturo.backends.windows._element._app_discovery"


class TestExplorerProgramManager:
    """Verify --app explorer prefers File Explorer over Program Manager (#524)."""

    @pytest.fixture(autouse=True)
    def _patch_session(self):
        with patch(f"{_SESSION_PATCH_BASE}._get_console_session_id", return_value=-1), \
             patch(f"{_SESSION_PATCH_BASE}._get_process_session_id", return_value=1):
            yield

    def _make_explorer_windows(self):
        """Program Manager (desktop) + File Explorer window."""
        return [
            WindowInfo(
                handle=0x10010,
                title="Program Manager",
                process_name="explorer.exe",
                pid=1000,
                x=0, y=0, width=1920, height=1080,  # full screen
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=0x20020,
                title="Windows (C:) - File Explorer",
                process_name="explorer.exe",
                pid=1000,
                x=100, y=100, width=900, height=600,  # smaller
                is_visible=True, is_minimized=False,
            ),
        ]

    def _setup_backend(self, windows, class_map=None):
        """Create a mock backend with the given windows and class names.

        Args:
            windows: List of WindowInfo to return from list_windows.
            class_map: Dict mapping hwnd -> class name string.
        """
        BackendClass = _make_backend()
        backend = MagicMock(spec=BackendClass)
        backend.list_windows = MagicMock(return_value=windows)
        backend._resolve_hwnd = BackendClass._resolve_hwnd.__get__(backend)
        backend._get_foreground_hwnd = MagicMock(return_value=0)
        backend._APP_ALIASES = BackendClass._APP_ALIASES
        backend._DESKTOP_SHELL_CLASSES = BackendClass._DESKTOP_SHELL_CLASSES

        if class_map is None:
            class_map = {}
        backend._get_window_class_name = MagicMock(
            side_effect=lambda h: class_map.get(h, "")
        )
        return backend

    def test_prefers_file_explorer_over_program_manager(self):
        """--app explorer should pick File Explorer, not Program Manager."""
        windows = self._make_explorer_windows()
        class_map = {
            0x10010: "Progman",        # desktop
            0x20020: "CabinetWClass",  # File Explorer
        }
        backend = self._setup_backend(windows, class_map)

        result = backend._resolve_hwnd(app="explorer")
        assert result == 0x20020, (
            "Expected File Explorer (0x20020), got Program Manager (0x10010)"
        )

    def test_workerw_also_deprioritized(self):
        """WorkerW (desktop wallpaper layer) should also be deprioritized."""
        windows = [
            WindowInfo(
                handle=0x10010,
                title="",
                process_name="explorer.exe",
                pid=1000,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=0x20020,
                title="Downloads - File Explorer",
                process_name="explorer.exe",
                pid=1000,
                x=100, y=100, width=900, height=600,
                is_visible=True, is_minimized=False,
            ),
        ]
        class_map = {
            0x10010: "WorkerW",
            0x20020: "CabinetWClass",
        }
        backend = self._setup_backend(windows, class_map)

        result = backend._resolve_hwnd(app="explorer")
        assert result == 0x20020

    def test_program_manager_still_matches_when_only_option(self):
        """When no File Explorer windows exist, Program Manager should still match."""
        windows = [
            WindowInfo(
                handle=0x10010,
                title="Program Manager",
                process_name="explorer.exe",
                pid=1000,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
        ]
        class_map = {0x10010: "Progman"}
        backend = self._setup_backend(windows, class_map)

        result = backend._resolve_hwnd(app="explorer")
        assert result == 0x10010, (
            "Program Manager should still match when it's the only explorer window"
        )

    def test_chinese_locale_explorer_preferred(self):
        """Chinese locale: File Explorer with Chinese title preferred over desktop."""
        windows = [
            WindowInfo(
                handle=0x10010,
                title="Program Manager",
                process_name="explorer.exe",
                pid=1000,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=0x20020,
                title="Windows (C:) - 文件资源管理器",
                process_name="explorer.exe",
                pid=1000,
                x=100, y=100, width=900, height=600,
                is_visible=True, is_minimized=False,
            ),
        ]
        class_map = {
            0x10010: "Progman",
            0x20020: "CabinetWClass",
        }
        backend = self._setup_backend(windows, class_map)

        result = backend._resolve_hwnd(app="explorer")
        assert result == 0x20020

    def test_multiple_explorer_windows_picks_largest(self):
        """Among multiple File Explorer windows, largest area wins."""
        windows = [
            WindowInfo(
                handle=0x10010,
                title="Program Manager",
                process_name="explorer.exe",
                pid=1000,
                x=0, y=0, width=1920, height=1080,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=0x20020,
                title="Downloads - File Explorer",
                process_name="explorer.exe",
                pid=1000,
                x=100, y=100, width=400, height=300,
                is_visible=True, is_minimized=False,
            ),
            WindowInfo(
                handle=0x30030,
                title="Documents - File Explorer",
                process_name="explorer.exe",
                pid=1000,
                x=200, y=200, width=1000, height=700,
                is_visible=True, is_minimized=False,
            ),
        ]
        class_map = {
            0x10010: "Progman",
            0x20020: "CabinetWClass",
            0x30030: "CabinetWClass",
        }
        backend = self._setup_backend(windows, class_map)

        result = backend._resolve_hwnd(app="explorer")
        assert result == 0x30030, "Should pick the largest File Explorer window"

    def test_non_explorer_apps_unaffected(self):
        """Desktop shell deprioritization only applies to process name matches."""
        windows = [
            WindowInfo(
                handle=0xAAAA,
                title="Untitled - Notepad",
                process_name="notepad.exe",
                pid=2000,
                x=0, y=0, width=800, height=600,
                is_visible=True, is_minimized=False,
            ),
        ]
        class_map = {0xAAAA: "Notepad"}
        backend = self._setup_backend(windows, class_map)

        result = backend._resolve_hwnd(app="notepad")
        assert result == 0xAAAA
