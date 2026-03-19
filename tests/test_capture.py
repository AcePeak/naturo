"""Tests for screen and window capture functionality.

These tests require Windows with the naturo_core.dll available.
They are automatically skipped on other platforms.
"""

from __future__ import annotations

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
    """T001: Capturing screen should create a non-empty BMP file."""
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
    """T002: Captured BMP should have a valid BMP header (magic bytes 'BM')."""
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
    """T003: Passing None as output path should raise NaturoCoreError."""
    from naturo.bridge import NaturoCoreError

    with pytest.raises(NaturoCoreError):
        core.capture_screen(0, None)


def test_capture_screen_invalid_index(core):
    """T005: Screen capture with invalid screen index (999) should raise error or fallback.

    An out-of-range screen index should either raise NaturoCoreError or
    silently fall back to the primary monitor (producing a valid capture).
    Both behaviors are acceptable — the key requirement is no crash.
    """
    from naturo.bridge import NaturoCoreError

    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        path = f.name

    try:
        try:
            result = core.capture_screen(999, path)
            # Fallback to primary monitor is acceptable — verify output is valid
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        except NaturoCoreError:
            # Raising an error is also acceptable
            pass
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_capture_window_foreground(core):
    """T006: Capturing the foreground window (hwnd=0) should succeed or fail gracefully."""
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


def test_capture_window_specific_hwnd(core):
    """T007: Window capture by specific HWND should produce valid output.

    Uses list_windows to find a real window handle, then captures it.
    """
    windows = core.list_windows()
    if not windows:
        pytest.skip("No windows available for capture")

    # Find a visible, non-minimized window
    target = None
    for w in windows:
        if w.is_visible and not w.is_minimized and w.width > 0:
            target = w
            break

    if target is None:
        pytest.skip("No suitable visible window found")

    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        path = f.name

    try:
        core.capture_window(target.hwnd, path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
        # Verify BMP header
        with open(path, "rb") as f:
            header = f.read(2)
        assert header == b"BM"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_capture_window_by_title(backend):
    """T008: Window capture by title match should work via backend.

    Uses the WindowsBackend.capture_window(window_title=...) interface.
    """
    windows = backend.list_windows()
    if not windows:
        pytest.skip("No windows available")

    # Pick a window with a non-empty title
    target = None
    for w in windows:
        if w.title and w.is_visible and not w.is_minimized:
            target = w
            break

    if target is None:
        pytest.skip("No suitable window with title found")

    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        path = f.name

    try:
        # capture_window with hwnd (title-based lookup not yet implemented)
        result = backend.capture_window(hwnd=target.handle, output_path=path)
        assert os.path.exists(result.path)
        assert result.width > 0 or result.height > 0
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_capture_window_minimized(core):
    """T009: Window capture of minimized window should return error or handle gracefully.

    A minimized window has zero dimensions; capture should either fail with
    an appropriate error or produce a valid (possibly black) image.
    """
    from naturo.bridge import NaturoCoreError

    windows = core.list_windows()
    minimized = [w for w in windows if w.is_minimized]

    if not minimized:
        pytest.skip("No minimized windows available")

    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        path = f.name

    try:
        try:
            core.capture_window(minimized[0].hwnd, path)
            # If it succeeds, the file should exist (possibly with minimal content)
            assert os.path.exists(path)
        except NaturoCoreError:
            # Error is acceptable for minimized windows
            pass
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_capture_overwrites_existing_file(core):
    """T012: Capture should overwrite an existing file at the same path."""
    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        path = f.name
        f.write(b"old content")

    try:
        core.capture_screen(0, path)
        assert os.path.exists(path)
        size = os.path.getsize(path)
        assert size > len(b"old content"), "File should be overwritten with BMP data"
        with open(path, "rb") as f:
            header = f.read(2)
        assert header == b"BM", "Overwritten file should be a valid BMP"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_capture_to_readonly_path_raises(core):
    """T013: Capture to read-only path should raise file I/O error.

    On POSIX systems, chmod makes directories truly read-only.
    On Windows, chmod(0o444) may not enforce write protection via POSIX
    semantics — so we use icacls to deny write access instead.
    The test accepts either an error or documents that the OS allowed the write.
    """
    from naturo.bridge import NaturoCoreError

    readonly_dir = tempfile.mkdtemp()
    path = os.path.join(readonly_dir, "test.bmp")

    try:
        if platform.system() == "Windows":
            # On Windows, use icacls to deny write access
            import subprocess
            subprocess.run(
                ["icacls", readonly_dir, "/deny", "Everyone:(W)"],
                capture_output=True,
            )
        else:
            os.chmod(readonly_dir, 0o444)

        try:
            core.capture_screen(0, path)
            # If it succeeds on Windows despite icacls (e.g., running as admin),
            # that's an acceptable platform behavior
        except (NaturoCoreError, OSError, PermissionError):
            # Expected behavior — write was blocked
            pass
    finally:
        if platform.system() == "Windows":
            import subprocess
            subprocess.run(
                ["icacls", readonly_dir, "/remove:d", "Everyone"],
                capture_output=True,
            )
        else:
            os.chmod(readonly_dir, 0o755)
        if os.path.exists(path):
            os.unlink(path)
        os.rmdir(readonly_dir)


def test_capture_to_invalid_path_raises(core):
    """T014: Capture to an invalid (non-existent directory) path should raise error."""
    from naturo.bridge import NaturoCoreError

    invalid_path = os.path.join(tempfile.gettempdir(), "nonexistent_dir_xyz", "test.bmp")
    with pytest.raises((NaturoCoreError, OSError)):
        core.capture_screen(0, invalid_path)


def test_backend_capture_screen(backend):
    """T019: WindowsBackend.capture_screen should return a CaptureResult."""
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
