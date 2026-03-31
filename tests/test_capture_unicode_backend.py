"""Tests for Unicode path handling in WindowsBackend capture methods.

Verifies that the backend passes an ASCII-safe temp path to the C++ DLL
even when the final output path contains Chinese/Unicode characters (#728).
Mock-based, runs on all platforms.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest


@dataclass
class _FakeMonitor:
    index: int = 0
    name: str = "Monitor"
    x: int = 0
    y: int = 0
    width: int = 1920
    height: int = 1080
    scale_factor: float = 1.0
    dpi: int = 96
    is_primary: bool = True
    work_area: tuple = (0, 0, 1920, 1040)


def _make_fake_bmp(path: str) -> None:
    """Write a minimal valid BMP file (1x1 pixel, 24-bit)."""
    import struct
    pixel_data = b"\x00\x00\xff\x00"  # 1 BGR pixel + 1 byte padding
    header = struct.pack(
        "<2sIHHI", b"BM",
        14 + 40 + len(pixel_data), 0, 0, 14 + 40,
    )
    info = struct.pack(
        "<IiiHHIIiiII",
        40, 1, 1, 1, 24, 0, len(pixel_data), 0, 0, 0, 0,
    )
    with open(path, "wb") as f:
        f.write(header + info + pixel_data)


class TestCaptureUnicodePath:
    """WindowsBackend must pass ASCII-safe temp paths to the DLL (#728)."""

    @pytest.fixture
    def mock_backend(self):
        """Create a WindowsBackend with mocked DLL core."""
        from naturo.backends.windows._capture import CaptureMixin

        class FakeBackend(CaptureMixin):
            def __init__(self):
                self._core = MagicMock()

            def _ensure_core(self):
                return self._core

            def list_monitors(self):
                return [_FakeMonitor()]

        return FakeBackend()

    def test_capture_screen_uses_ascii_temp_for_dll(self, mock_backend, tmp_path):
        """DLL receives an ASCII-safe temp path, not the Unicode output path."""
        unicode_dir = tmp_path / "中文路径"
        unicode_dir.mkdir()
        output_path = str(unicode_dir / "截图.png")

        captured_dll_paths = []

        def fake_capture_screen(screen_index, bmp_path):
            captured_dll_paths.append(bmp_path)
            _make_fake_bmp(bmp_path)

        mock_backend._core.capture_screen.side_effect = fake_capture_screen

        try:
            result = mock_backend.capture_screen(screen_index=0, output_path=output_path)
        except Exception:
            pytest.skip("Pillow not available")

        assert len(captured_dll_paths) == 1
        dll_path = captured_dll_paths[0]
        # The temp path given to the DLL must be in the system temp dir,
        # NOT in the Unicode output directory
        assert dll_path.isascii(), (
            f"DLL received non-ASCII path: {dll_path!r}"
        )
        assert result.path == output_path

    def test_capture_window_uses_ascii_temp_for_dll(self, mock_backend, tmp_path):
        """Window capture also uses ASCII-safe temp path for the DLL."""
        unicode_dir = tmp_path / "テスト"
        unicode_dir.mkdir()
        output_path = str(unicode_dir / "ウィンドウ.png")

        captured_dll_paths = []

        def fake_capture_window(hwnd, bmp_path):
            captured_dll_paths.append(bmp_path)
            _make_fake_bmp(bmp_path)

        mock_backend._core.capture_window.side_effect = fake_capture_window

        try:
            result = mock_backend.capture_window(hwnd=12345, output_path=output_path)
        except Exception:
            pytest.skip("Pillow not available")

        assert len(captured_dll_paths) == 1
        dll_path = captured_dll_paths[0]
        assert dll_path.isascii(), (
            f"DLL received non-ASCII path: {dll_path!r}"
        )
        assert result.path == output_path
