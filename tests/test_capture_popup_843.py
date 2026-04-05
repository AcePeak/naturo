"""Tests for capture --app including popup menu windows (#843).

Verifies that when an app has popup menus open (separate top-level windows
owned by the same process), ``capture_app_windows`` composites them into
a single image alongside the main window.
"""
from __future__ import annotations

import ctypes
import os
import platform
import sys
import tempfile
from dataclasses import dataclass
from unittest.mock import MagicMock, patch, call

import pytest

try:
    from PIL import Image as _PIL_Image  # noqa: F401
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

from naturo.backends.base import CaptureResult, WindowInfo

# Build a minimal ctypes.wintypes stub for Linux.  The real module is only
# available on Windows, but the code under test imports it.  We store the
# stub but only install it into sys.modules inside a context manager so it
# does not pollute other tests.
_NEED_WINTYPES_STUB = "ctypes.wintypes" not in sys.modules
_NEED_WINDLL_STUB = not hasattr(ctypes, "windll")


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                 ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


if _NEED_WINTYPES_STUB:
    _wt_stub = type(sys)("ctypes.wintypes")
    _wt_stub.RECT = _RECT  # type: ignore[attr-defined]
    _wt_stub.DWORD = ctypes.c_ulong  # type: ignore[attr-defined]
    _wt_stub.LONG = ctypes.c_long  # type: ignore[attr-defined]
else:
    _wt_stub = sys.modules["ctypes.wintypes"]


@pytest.fixture(autouse=True)
def _install_ctypes_stubs():
    """Temporarily install ctypes.windll and ctypes.wintypes stubs on Linux."""
    old_windll = getattr(ctypes, "windll", None)
    old_wt_mod = sys.modules.get("ctypes.wintypes")
    old_wt_attr = getattr(ctypes, "wintypes", None)

    if _NEED_WINDLL_STUB:
        ctypes.windll = MagicMock()  # type: ignore[attr-defined]
    if _NEED_WINTYPES_STUB:
        sys.modules["ctypes.wintypes"] = _wt_stub
        ctypes.wintypes = _wt_stub  # type: ignore[attr-defined]

    yield

    # Restore original state
    if _NEED_WINDLL_STUB:
        if old_windll is None:
            if hasattr(ctypes, "windll"):
                del ctypes.windll  # type: ignore[attr-defined]
        else:
            ctypes.windll = old_windll  # type: ignore[attr-defined]
    if _NEED_WINTYPES_STUB:
        if old_wt_mod is None:
            sys.modules.pop("ctypes.wintypes", None)
        else:
            sys.modules["ctypes.wintypes"] = old_wt_mod
        if old_wt_attr is None:
            if hasattr(ctypes, "wintypes"):
                del ctypes.wintypes  # type: ignore[attr-defined]
        else:
            ctypes.wintypes = old_wt_attr  # type: ignore[attr-defined]


def _make_window(handle: int, pid: int, title: str,
                 x: int, y: int, w: int, h: int) -> WindowInfo:
    return WindowInfo(
        handle=handle, title=title, process_name="notepad.exe",
        pid=pid, x=x, y=y, width=w, height=h,
        is_visible=True, is_minimized=False,
    )


def _make_bmp(path: str, width: int, height: int,
              color: tuple[int, int, int] = (128, 128, 128)) -> None:
    """Create a minimal BMP file at *path* with the given dimensions."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color)
    img.save(path, "BMP")


class _FakeUser32:
    """Simulates user32 for GetWindowThreadProcessId and GetWindowRect."""

    def __init__(self, pid_map: dict[int, int], rect_map: dict[int, tuple[int, int, int, int]]):
        self._pid_map = pid_map      # hwnd → pid
        self._rect_map = rect_map    # hwnd → (left, top, right, bottom)

    def GetWindowThreadProcessId(self, hwnd, pid_ptr):
        pid = self._pid_map.get(hwnd, 0)
        # pid_ptr is ctypes.byref(c_ulong) — write via memmove
        src = ctypes.c_ulong(pid)
        ctypes.memmove(pid_ptr, ctypes.byref(src), ctypes.sizeof(ctypes.c_ulong))
        return 1

    def GetWindowRect(self, hwnd, rect_ptr):
        r = self._rect_map.get(hwnd)
        if r is None:
            return 0
        # rect_ptr is ctypes.byref(RECT) — build a source RECT and memmove
        wt = sys.modules["ctypes.wintypes"]
        src = wt.RECT()
        src.left = r[0]
        src.top = r[1]
        src.right = r[2]
        src.bottom = r[3]
        ctypes.memmove(rect_ptr, ctypes.byref(src), ctypes.sizeof(wt.RECT))
        return 1

    def GetForegroundWindow(self):
        return 0


class _FakeWindll:
    def __init__(self, user32):
        self.user32 = user32


def _make_backend(windows, pid_map, rect_map, core_capture_fn=None):
    """Create a FakeBackend with configured mocks."""
    from naturo.backends.windows._capture import CaptureMixin

    fake_user32 = _FakeUser32(pid_map, rect_map)
    fake_windll = _FakeWindll(fake_user32)

    mock_core = MagicMock()
    if core_capture_fn:
        mock_core.capture_window.side_effect = core_capture_fn

    class FakeBackend(CaptureMixin):
        def _ensure_core(self):
            return mock_core

        def list_windows(self):
            return windows

        def find_monitor_for_point(self, x, y):
            return None

        def capture_window(self, window_title=None, hwnd=None,
                           output_path="capture.png"):
            return CaptureResult(
                path=output_path, width=100, height=100,
                format="png", scale_factor=1.0, dpi=96,
            )

    backend = FakeBackend()
    return backend, mock_core, fake_windll


class TestCaptureAppWindows:
    """Unit tests for CaptureMixin.capture_app_windows (#843)."""

    def test_no_siblings_falls_back_to_single_capture(self):
        """When no popup windows exist, delegates to capture_window."""
        main_hwnd = 1001
        pid = 42

        backend, mock_core, fake_windll = _make_backend(
            windows=[_make_window(1001, pid, "Notepad", 100, 100, 800, 600)],
            pid_map={1001: pid},
            rect_map={},
        )

        with patch("ctypes.windll", fake_windll), \
             patch.object(backend, "capture_window") as mock_cw:
            mock_cw.return_value = CaptureResult(
                path="out.png", width=800, height=600,
                format="png", scale_factor=1.0, dpi=96,
            )
            result = backend.capture_app_windows(main_hwnd, "out.png")

        mock_cw.assert_called_once_with(hwnd=main_hwnd, output_path="out.png")
        assert result.width == 800

    @pytest.mark.skipif(not _HAS_PIL, reason="Pillow not installed")
    def test_popup_menu_composited_into_capture(self):
        """When a popup menu window exists, both are captured and composited."""
        main_hwnd = 2001
        popup_hwnd = 2002
        pid = 55

        rect_map = {
            main_hwnd: (100, 100, 900, 700),   # 800x600
            popup_hwnd: (150, 300, 350, 500),   # 200x200
        }

        def fake_core_capture(hwnd, bmp_path):
            r = rect_map[hwnd]
            _make_bmp(bmp_path, r[2] - r[0], r[3] - r[1])

        backend, mock_core, fake_windll = _make_backend(
            windows=[
                _make_window(main_hwnd, pid, "Notepad", 100, 100, 800, 600),
                _make_window(popup_hwnd, pid, "", 150, 300, 200, 200),
            ],
            pid_map={main_hwnd: pid, popup_hwnd: pid},
            rect_map=rect_map,
            core_capture_fn=fake_core_capture,
        )

        with patch("ctypes.windll", fake_windll), \
             tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "composite.png")
            result = backend.capture_app_windows(main_hwnd, out_path)

            # Bounding box: (100,100) to (900,700) = 800x600
            assert result.width == 800
            assert result.height == 600
            assert os.path.exists(out_path)
            assert mock_core.capture_window.call_count == 2

    @pytest.mark.skipif(not _HAS_PIL, reason="Pillow not installed")
    def test_popup_extends_beyond_main_window(self):
        """A popup that extends beyond the main window expands the canvas."""
        main_hwnd = 3001
        popup_hwnd = 3002
        pid = 77

        rect_map = {
            main_hwnd: (100, 100, 600, 500),   # 500x400
            popup_hwnd: (500, 400, 700, 550),   # 200x150, extends right/below
        }

        def fake_core_capture(hwnd, bmp_path):
            r = rect_map[hwnd]
            _make_bmp(bmp_path, r[2] - r[0], r[3] - r[1])

        backend, mock_core, fake_windll = _make_backend(
            windows=[
                _make_window(main_hwnd, pid, "Notepad", 100, 100, 500, 400),
                _make_window(popup_hwnd, pid, "", 500, 400, 200, 150),
            ],
            pid_map={main_hwnd: pid, popup_hwnd: pid},
            rect_map=rect_map,
            core_capture_fn=fake_core_capture,
        )

        with patch("ctypes.windll", fake_windll), \
             tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "extended.png")
            result = backend.capture_app_windows(main_hwnd, out_path)

            # Bounding box: (100,100) to (700,550) = 600x450
            assert result.width == 600
            assert result.height == 450
            assert os.path.exists(out_path)

    def test_pid_zero_falls_back(self):
        """When PID cannot be determined, falls back to single capture."""
        backend, mock_core, fake_windll = _make_backend(
            windows=[],
            pid_map={9999: 0},  # PID = 0
            rect_map={},
        )

        with patch("ctypes.windll", fake_windll), \
             patch.object(backend, "capture_window") as mock_cw:
            mock_cw.return_value = CaptureResult(
                path="out.png", width=100, height=100,
                format="png", scale_factor=1.0, dpi=96,
            )
            result = backend.capture_app_windows(9999, "out.png")

        mock_cw.assert_called_once()

    def test_minimized_sibling_excluded(self):
        """Minimized windows from the same process should be excluded."""
        main_hwnd = 4001
        minimized_hwnd = 4002
        pid = 88

        backend, mock_core, fake_windll = _make_backend(
            windows=[
                _make_window(main_hwnd, pid, "Notepad", 100, 100, 800, 600),
                WindowInfo(handle=minimized_hwnd, title="Notepad - doc2",
                           process_name="notepad.exe", pid=pid,
                           x=0, y=0, width=0, height=0,
                           is_visible=True, is_minimized=True),
            ],
            pid_map={main_hwnd: pid},
            rect_map={},
        )

        with patch("ctypes.windll", fake_windll), \
             patch.object(backend, "capture_window") as mock_cw:
            mock_cw.return_value = CaptureResult(
                path="out.png", width=800, height=600,
                format="png", scale_factor=1.0, dpi=96,
            )
            result = backend.capture_app_windows(main_hwnd, "out.png")

        # Should fall back to single capture (minimized sibling excluded)
        mock_cw.assert_called_once()


class TestCaptureCLIAppWindowsIntegration:
    """Verify the CLI calls capture_app_windows when --app is used."""

    def test_capture_app_uses_composite_method(self):
        """capture --app should call capture_app_windows, not capture_window."""
        from click.testing import CliRunner
        from naturo.cli import main

        mock_backend = MagicMock()
        mock_backend._resolve_hwnd.return_value = 5001
        mock_backend.capture_app_windows.return_value = CaptureResult(
            path="/tmp/test.png", width=800, height=600,
            format="png", scale_factor=1.0, dpi=96,
        )

        with patch("naturo.cli.core._capture._common._get_backend",
                    return_value=mock_backend), \
             patch("naturo.cli.core._capture._common._platform_supports_gui",
                    return_value=True):
            runner = CliRunner()
            result = runner.invoke(main, [
                "capture", "--app", "notepad", "-p", "/tmp/test.png",
            ])

        mock_backend.capture_app_windows.assert_called_once_with(
            main_hwnd=5001, output_path="/tmp/test.png",
        )
        mock_backend.capture_window.assert_not_called()

    def test_capture_hwnd_uses_single_window(self):
        """capture --hwnd should call capture_window, not capture_app_windows."""
        from click.testing import CliRunner
        from naturo.cli import main

        mock_backend = MagicMock()
        mock_backend.capture_window.return_value = CaptureResult(
            path="/tmp/test.png", width=800, height=600,
            format="png", scale_factor=1.0, dpi=96,
        )

        with patch("naturo.cli.core._capture._common._get_backend",
                    return_value=mock_backend), \
             patch("naturo.cli.core._capture._common._platform_supports_gui",
                    return_value=True):
            runner = CliRunner()
            result = runner.invoke(main, [
                "capture", "--hwnd", "5001", "-p", "/tmp/test.png",
            ])

        mock_backend.capture_window.assert_called_once()
        mock_backend.capture_app_windows.assert_not_called()
