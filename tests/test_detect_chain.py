"""Tests for naturo.detect.chain — detection chain orchestrator.

Tests cover:
- _run_probe_with_timeout: success, error propagation, timeout handling
- detect(): cache hit/miss, probe ordering, quick mode, error resilience
- detect_for_hwnd(): Windows-only guard
"""
from __future__ import annotations

import threading
import time
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from naturo.detect.models import (
    DetectionResult,
    FrameworkInfo,
    FrameworkType,
    InteractionMethod,
    InteractionMethodType,
    ProbeStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_method(
    method: InteractionMethodType = InteractionMethodType.UIA,
    priority: int = 2,
    status: ProbeStatus = ProbeStatus.AVAILABLE,
) -> InteractionMethod:
    """Create an InteractionMethod for testing."""
    return InteractionMethod(method=method, priority=priority, status=status)


def _probe_factory(
    result: Optional[InteractionMethod] = None,
    error: Optional[Exception] = None,
    hang_seconds: float = 0,
):
    """Return a probe function that returns *result*, raises *error*, or hangs."""
    def probe(pid: int, exe: str, hwnd: Optional[int]) -> Optional[InteractionMethod]:
        if hang_seconds:
            time.sleep(hang_seconds)
        if error:
            raise error
        return result
    probe.__name__ = f"probe_factory({result})"
    return probe


# ---------------------------------------------------------------------------
# _run_probe_with_timeout
# ---------------------------------------------------------------------------

class TestRunProbeWithTimeout:
    """Tests for the per-probe timeout wrapper."""

    def test_successful_probe_returns_result(self):
        from naturo.detect.chain import _run_probe_with_timeout

        method = _make_method()
        probe = _probe_factory(result=method)
        got = _run_probe_with_timeout(probe, pid=123, exe="test.exe", hwnd=None)
        assert got is method

    def test_probe_returning_none(self):
        from naturo.detect.chain import _run_probe_with_timeout

        probe = _probe_factory(result=None)
        got = _run_probe_with_timeout(probe, pid=123, exe="test.exe", hwnd=None)
        assert got is None

    def test_probe_error_propagates(self):
        from naturo.detect.chain import _run_probe_with_timeout

        probe = _probe_factory(error=ValueError("bad probe"))
        with pytest.raises(ValueError, match="bad probe"):
            _run_probe_with_timeout(probe, pid=123, exe="test.exe", hwnd=None)

    def test_probe_timeout_returns_none(self):
        from naturo.detect import chain as chain_mod
        from naturo.detect.chain import _run_probe_with_timeout

        # Temporarily set a very short timeout
        original = chain_mod._PROBE_TIMEOUT_SECONDS
        chain_mod._PROBE_TIMEOUT_SECONDS = 0.1
        try:
            probe = _probe_factory(hang_seconds=5)
            got = _run_probe_with_timeout(probe, pid=123, exe="test.exe", hwnd=None)
            assert got is None
        finally:
            chain_mod._PROBE_TIMEOUT_SECONDS = original


# ---------------------------------------------------------------------------
# detect()
# ---------------------------------------------------------------------------

class TestDetect:
    """Tests for the main detect() function."""

    @patch("naturo.detect.chain.detect_frameworks_from_dlls", return_value=[])
    @patch("naturo.detect.chain.get_cache")
    @patch("naturo.detect.chain._DEFAULT_PROBES", [])
    @patch("naturo.detect.chain.platform")
    def test_cache_hit_returns_cached_result(self, mock_platform, mock_get_cache, mock_dlls):
        from naturo.detect.chain import detect

        mock_platform.system.return_value = "Linux"
        cached_result = DetectionResult(pid=42, exe="notepad.exe")
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_result
        mock_get_cache.return_value = mock_cache

        result = detect(pid=42, exe="notepad.exe")
        assert result is cached_result
        mock_cache.get.assert_called_once_with(42)
        # Probes should not have been called
        mock_dlls.assert_not_called()

    @patch("naturo.detect.chain.detect_frameworks_from_dlls", return_value=[])
    @patch("naturo.detect.chain.get_cache")
    @patch("naturo.detect.chain._run_probe_with_timeout")
    @patch("naturo.detect.chain._DEFAULT_PROBES")
    @patch("naturo.detect.chain.platform")
    def test_cache_miss_runs_probes(self, mock_platform, mock_probes, mock_run, mock_get_cache, mock_dlls):
        from naturo.detect.chain import detect

        mock_platform.system.return_value = "Linux"
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        uia_method = _make_method(InteractionMethodType.UIA, priority=2)
        vision_method = _make_method(InteractionMethodType.VISION, priority=6, status=ProbeStatus.FALLBACK)
        probe_uia = MagicMock(name="probe_uia")
        probe_vision = MagicMock(name="probe_vision")
        mock_probes.__iter__ = MagicMock(return_value=iter([probe_uia, probe_vision]))
        mock_run.side_effect = [uia_method, vision_method]

        result = detect(pid=100, exe="app.exe")

        assert result.pid == 100
        assert len(result.methods) == 2
        assert result.recommended == InteractionMethodType.UIA
        mock_cache.put.assert_called_once()

    @patch("naturo.detect.chain.detect_frameworks_from_dlls", return_value=[])
    @patch("naturo.detect.chain.get_cache")
    @patch("naturo.detect.chain._DEFAULT_PROBES", [])
    @patch("naturo.detect.chain.platform")
    def test_no_cache_mode(self, mock_platform, mock_get_cache, mock_dlls):
        from naturo.detect.chain import detect

        mock_platform.system.return_value = "Linux"
        mock_cache = MagicMock()
        mock_get_cache.return_value = mock_cache

        result = detect(pid=1, use_cache=False)
        mock_cache.get.assert_not_called()
        mock_cache.put.assert_not_called()
        assert result.pid == 1

    @patch("naturo.detect.chain.detect_frameworks_from_dlls")
    @patch("naturo.detect.chain.get_cache")
    @patch("naturo.detect.chain._run_probe_with_timeout")
    @patch("naturo.detect.chain._DEFAULT_PROBES")
    @patch("naturo.detect.chain.platform")
    def test_frameworks_included_in_result(self, mock_platform, mock_probes, mock_run, mock_get_cache, mock_dlls):
        from naturo.detect.chain import detect

        mock_platform.system.return_value = "Linux"
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        fw = FrameworkInfo(framework_type=FrameworkType.ELECTRON, dll_signatures=["libcef.dll"])
        mock_dlls.return_value = [fw]
        mock_probes.__iter__ = MagicMock(return_value=iter([]))

        result = detect(pid=200, exe="electron.exe")
        assert len(result.frameworks) == 1
        assert result.frameworks[0].framework_type == FrameworkType.ELECTRON

    @patch("naturo.detect.chain.detect_frameworks_from_dlls", return_value=[])
    @patch("naturo.detect.chain.get_cache")
    @patch("naturo.detect.chain._run_probe_with_timeout")
    @patch("naturo.detect.chain._DEFAULT_PROBES")
    @patch("naturo.detect.chain.platform")
    def test_probe_exception_does_not_crash_chain(self, mock_platform, mock_probes, mock_run, mock_get_cache, mock_dlls):
        from naturo.detect.chain import detect

        mock_platform.system.return_value = "Linux"
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        vision_method = _make_method(InteractionMethodType.VISION, priority=6, status=ProbeStatus.FALLBACK)
        probe_bad = MagicMock(name="probe_bad", __name__="probe_bad")
        probe_good = MagicMock(name="probe_good", __name__="probe_good")
        mock_probes.__iter__ = MagicMock(return_value=iter([probe_bad, probe_good]))
        mock_run.side_effect = [RuntimeError("probe crashed"), vision_method]

        result = detect(pid=300)
        assert len(result.methods) == 1
        assert result.methods[0].method == InteractionMethodType.VISION

    @patch("naturo.detect.chain.detect_frameworks_from_dlls", return_value=[])
    @patch("naturo.detect.chain.get_cache")
    @patch("naturo.detect.chain._run_probe_with_timeout")
    @patch("naturo.detect.chain._DEFAULT_PROBES")
    @patch("naturo.detect.chain.probe_vision")
    @patch("naturo.detect.chain.platform")
    def test_quick_mode_stops_after_first_available(
        self, mock_platform, mock_probe_vision, mock_probes, mock_run, mock_get_cache, mock_dlls,
    ):
        from naturo.detect.chain import detect

        mock_platform.system.return_value = "Linux"
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        uia_method = _make_method(InteractionMethodType.UIA, priority=2)
        vision_method = _make_method(InteractionMethodType.VISION, priority=6, status=ProbeStatus.FALLBACK)

        probe_uia = MagicMock(name="probe_uia")
        probe_msaa = MagicMock(name="probe_msaa")
        mock_probes.__iter__ = MagicMock(return_value=iter([probe_uia, probe_msaa]))
        # Only UIA returns a result; MSAA should not be reached in quick mode
        mock_run.return_value = uia_method
        mock_probe_vision.return_value = vision_method

        result = detect(pid=400, quick=True)

        # _run_probe_with_timeout should only be called once (for UIA)
        assert mock_run.call_count == 1
        # Vision fallback should be added
        assert len(result.methods) == 2
        assert result.recommended == InteractionMethodType.UIA

    @patch("naturo.detect.chain.detect_frameworks_from_dlls", return_value=[])
    @patch("naturo.detect.chain.get_cache")
    @patch("naturo.detect.chain._DEFAULT_PROBES", [])
    @patch("naturo.detect.chain.platform")
    def test_no_methods_gives_no_recommended(self, mock_platform, mock_get_cache, mock_dlls):
        from naturo.detect.chain import detect

        mock_platform.system.return_value = "Linux"
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        result = detect(pid=500)
        assert result.recommended is None
        assert result.methods == []

    @patch("naturo.detect.chain.detect_frameworks_from_dlls", return_value=[])
    @patch("naturo.detect.chain.get_cache")
    @patch("naturo.detect.chain._run_probe_with_timeout")
    @patch("naturo.detect.chain._DEFAULT_PROBES")
    @patch("naturo.detect.chain.platform")
    def test_methods_sorted_by_priority(self, mock_platform, mock_probes, mock_run, mock_get_cache, mock_dlls):
        from naturo.detect.chain import detect

        mock_platform.system.return_value = "Linux"
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        vision = _make_method(InteractionMethodType.VISION, priority=6, status=ProbeStatus.FALLBACK)
        uia = _make_method(InteractionMethodType.UIA, priority=2)
        msaa = _make_method(InteractionMethodType.MSAA, priority=3)

        probe1 = MagicMock(name="p1")
        probe2 = MagicMock(name="p2")
        probe3 = MagicMock(name="p3")
        mock_probes.__iter__ = MagicMock(return_value=iter([probe1, probe2, probe3]))
        # Return in reverse priority order
        mock_run.side_effect = [vision, uia, msaa]

        result = detect(pid=600)
        assert len(result.methods) == 3
        # Should be sorted: UIA(2), MSAA(3), VISION(6)
        assert result.methods[0].method == InteractionMethodType.UIA
        assert result.methods[1].method == InteractionMethodType.MSAA
        assert result.methods[2].method == InteractionMethodType.VISION

    @patch("naturo.detect.chain.detect_frameworks_from_dlls", return_value=[])
    @patch("naturo.detect.chain.get_cache")
    @patch("naturo.detect.chain._DEFAULT_PROBES", [])
    @patch("naturo.detect.chain.platform")
    def test_app_name_passed_through(self, mock_platform, mock_get_cache, mock_dlls):
        from naturo.detect.chain import detect

        mock_platform.system.return_value = "Linux"
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        result = detect(pid=700, app_name="Notepad")
        assert result.app_name == "Notepad"


# ---------------------------------------------------------------------------
# detect_for_hwnd()
# ---------------------------------------------------------------------------

class TestDetectForHwnd:
    """Tests for detect_for_hwnd()."""

    @patch("naturo.detect.chain.platform")
    def test_raises_on_non_windows(self, mock_platform):
        from naturo.detect.chain import detect_for_hwnd

        mock_platform.system.return_value = "Linux"
        with pytest.raises(RuntimeError, match="requires Windows"):
            detect_for_hwnd(hwnd=12345)
