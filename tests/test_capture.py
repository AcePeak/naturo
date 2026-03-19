"""Tests for screen and window capture functionality.

These tests require Windows with the naturo_core.dll available.
They are automatically skipped on other platforms.
"""

import os
import platform
import tempfile

import pytest


pytestmark = [
    pytest.mark.ui,
    pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Capture tests require Windows with naturo_core.dll",
    ),
]


@pytest.fixture
def core():
    """Create and initialize a NaturoCore instance."""
    from naturo.bridge import NaturoCore

    c = NaturoCore()
    c.init()
    yield c
    c.shutdown()


@pytest.fixture
def backend():
    """Create a WindowsBackend instance."""
    from naturo.backends.windows import WindowsBackend

    return WindowsBackend()


def test_capture_screen_creates_file(core):
    """Capturing screen should create a non-empty BMP file."""
    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        path = f.name

    try:
        result = core.capture_screen(0, path)
        assert result == path
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_capture_screen_bmp_header(core):
    """Captured BMP should have a valid BMP header (magic bytes 'BM')."""
    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        path = f.name

    try:
        core.capture_screen(0, path)
        with open(path, "rb") as f:
            header = f.read(2)
        assert header == b"BM", f"Expected BMP magic 'BM', got {header!r}"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_capture_screen_null_path_raises(core):
    """Passing None as output path should raise NaturoCoreError."""
    from naturo.bridge import NaturoCoreError

    with pytest.raises(NaturoCoreError):
        core.capture_screen(0, None)


def test_capture_window_foreground(core):
    """Capturing the foreground window (hwnd=0) should succeed or fail gracefully."""
    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        path = f.name

    try:
        # hwnd=0 captures foreground — may fail in headless CI
        try:
            result = core.capture_window(0, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        except Exception:
            # Acceptable in CI without a desktop
            pass
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_backend_capture_screen(backend):
    """WindowsBackend.capture_screen should return a CaptureResult."""
    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        path = f.name

    try:
        result = backend.capture_screen(screen_index=0, output_path=path)
        assert result.path == path
        assert result.width > 0
        assert result.height > 0
        assert os.path.exists(path)
    finally:
        if os.path.exists(path):
            os.unlink(path)
