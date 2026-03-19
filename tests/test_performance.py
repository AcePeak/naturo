"""Performance benchmark tests for Naturo.

These tests verify that core operations complete within acceptable time
thresholds. They use generous limits suitable for CI environments.
"""

from __future__ import annotations

import os
import platform
import tempfile
import time

import pytest


pytestmark = [
    pytest.mark.performance,
    pytest.mark.ui,
    pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Performance tests require Windows with naturo_core.dll",
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


def test_capture_screen_performance(core):
    """T021/T330: Screen capture should complete in < 500ms.

    Uses a generous 2s threshold for CI stability, but the target is <500ms.
    """
    with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
        path = f.name

    try:
        start = time.perf_counter()
        core.capture_screen(0, path)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"Screen capture took {elapsed:.3f}s (target: <500ms, CI limit: <2s)"
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_list_windows_performance(core):
    """T331: Window list should complete in < 200ms.

    Uses a generous 1s threshold for CI stability, but the target is <200ms.
    """
    start = time.perf_counter()
    windows = core.list_windows()
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"list_windows took {elapsed:.3f}s (target: <200ms, CI limit: <1s)"
    assert isinstance(windows, list)


def test_element_tree_performance(core):
    """T332: Element tree (depth=3) should complete in < 2s for typical app.

    Uses a generous 5s threshold for CI stability, but the target is <2s.
    """
    start = time.perf_counter()
    tree = core.get_element_tree(hwnd=0, depth=3)
    elapsed = time.perf_counter() - start

    assert elapsed < 5.0, f"get_element_tree took {elapsed:.3f}s (target: <2s, CI limit: <5s)"
    # tree may be None in CI without foreground window, that's OK
