"""Tests for the framework detection system.

Tests models, cache, and detection chain logic.
Most probes require Windows, so probe tests are platform-gated.
"""

import platform
import time

import pytest

from naturo.detect.models import (
    DetectionResult,
    FrameworkInfo,
    FrameworkType,
    InteractionMethod,
    InteractionMethodType,
    METHOD_PRIORITY,
    ProbeStatus,
)
from naturo.detect.cache import DetectionCache
from naturo.detect.chain import detect, _run_probe_with_timeout, _PROBE_TIMEOUT_SECONDS


# ── Models ──────────────────────────────────────────────────────────


class TestFrameworkInfo:
    """Tests for FrameworkInfo data model."""

    def test_to_dict_minimal(self):
        info = FrameworkInfo(framework_type=FrameworkType.WIN32)
        result = info.to_dict()
        assert result["type"] == "win32"
        assert "version" not in result
        assert "dll_signatures" not in result

    def test_to_dict_full(self):
        info = FrameworkInfo(
            framework_type=FrameworkType.QT,
            version="Qt 6",
            dll_signatures=["qt6core.dll", "qt6widgets.dll"],
        )
        result = info.to_dict()
        assert result["type"] == "qt"
        assert result["version"] == "Qt 6"
        assert result["dll_signatures"] == ["qt6core.dll", "qt6widgets.dll"]


class TestInteractionMethod:
    """Tests for InteractionMethod data model."""

    def test_to_dict(self):
        method = InteractionMethod(
            method=InteractionMethodType.UIA,
            priority=METHOD_PRIORITY[InteractionMethodType.UIA],
            status=ProbeStatus.AVAILABLE,
            capabilities=["click", "type", "find"],
            confidence=0.9,
        )
        result = method.to_dict()
        assert result["method"] == "uia"
        assert result["priority"] == 2
        assert result["status"] == "available"
        assert "click" in result["capabilities"]
        assert result["confidence"] == 0.9

    def test_to_dict_with_metadata(self):
        method = InteractionMethod(
            method=InteractionMethodType.CDP,
            priority=1,
            status=ProbeStatus.AVAILABLE,
            metadata={"debug_port": 9222},
        )
        result = method.to_dict()
        assert result["metadata"]["debug_port"] == 9222

    def test_to_dict_without_metadata(self):
        method = InteractionMethod(
            method=InteractionMethodType.VISION,
            priority=6,
            status=ProbeStatus.FALLBACK,
        )
        result = method.to_dict()
        assert "metadata" not in result


class TestDetectionResult:
    """Tests for DetectionResult data model."""

    def test_best_method_selects_highest_priority(self):
        result = DetectionResult(
            pid=100,
            methods=[
                InteractionMethod(
                    method=InteractionMethodType.MSAA,
                    priority=3,
                    status=ProbeStatus.AVAILABLE,
                ),
                InteractionMethod(
                    method=InteractionMethodType.UIA,
                    priority=2,
                    status=ProbeStatus.AVAILABLE,
                ),
                InteractionMethod(
                    method=InteractionMethodType.VISION,
                    priority=6,
                    status=ProbeStatus.FALLBACK,
                ),
            ],
        )
        best = result.best_method()
        assert best is not None
        assert best.method == InteractionMethodType.UIA

    def test_best_method_includes_fallback(self):
        """Fallback methods are considered when no 'available' methods exist."""
        result = DetectionResult(
            pid=100,
            methods=[
                InteractionMethod(
                    method=InteractionMethodType.CDP,
                    priority=1,
                    status=ProbeStatus.UNAVAILABLE,
                ),
                InteractionMethod(
                    method=InteractionMethodType.VISION,
                    priority=6,
                    status=ProbeStatus.FALLBACK,
                ),
            ],
        )
        best = result.best_method()
        assert best is not None
        assert best.method == InteractionMethodType.VISION

    def test_best_method_none_when_empty(self):
        result = DetectionResult(pid=100, methods=[])
        assert result.best_method() is None

    def test_best_method_none_when_all_unavailable(self):
        result = DetectionResult(
            pid=100,
            methods=[
                InteractionMethod(
                    method=InteractionMethodType.CDP,
                    priority=1,
                    status=ProbeStatus.UNAVAILABLE,
                ),
                InteractionMethod(
                    method=InteractionMethodType.JAB,
                    priority=4,
                    status=ProbeStatus.ERROR,
                ),
            ],
        )
        assert result.best_method() is None

    def test_to_dict_structure(self):
        result = DetectionResult(
            pid=1234,
            exe="notepad.exe",
            app_name="Notepad",
            frameworks=[FrameworkInfo(framework_type=FrameworkType.WIN32)],
            methods=[
                InteractionMethod(
                    method=InteractionMethodType.UIA,
                    priority=2,
                    status=ProbeStatus.AVAILABLE,
                    capabilities=["click", "type"],
                ),
            ],
        )
        d = result.to_dict()
        assert d["pid"] == 1234
        assert d["exe"] == "notepad.exe"
        assert d["app"] == "Notepad"
        assert len(d["framework"]["detected"]) == 1
        assert d["framework"]["detected"][0]["type"] == "win32"
        assert len(d["interaction_methods"]) == 1
        assert d["recommended"] == "uia"


class TestMethodPriority:
    """Tests for METHOD_PRIORITY ordering."""

    def test_cdp_highest_priority(self):
        assert METHOD_PRIORITY[InteractionMethodType.CDP] < METHOD_PRIORITY[InteractionMethodType.UIA]

    def test_vision_lowest_priority(self):
        assert METHOD_PRIORITY[InteractionMethodType.VISION] > METHOD_PRIORITY[InteractionMethodType.IA2]

    def test_all_methods_have_priority(self):
        for method in InteractionMethodType:
            assert method in METHOD_PRIORITY, f"{method} missing from METHOD_PRIORITY"


# ── Cache ───────────────────────────────────────────────────────────


class TestDetectionCache:
    """Tests for the per-PID detection cache."""

    def test_put_and_get(self):
        cache = DetectionCache(ttl_seconds=60)
        result = DetectionResult(pid=100)
        cache.put(100, result)
        assert cache.get(100) is result

    def test_miss_returns_none(self):
        cache = DetectionCache()
        assert cache.get(999) is None

    def test_ttl_expiration(self):
        cache = DetectionCache(ttl_seconds=0.1)
        result = DetectionResult(pid=100)
        cache.put(100, result)
        assert cache.get(100) is result
        time.sleep(0.15)
        assert cache.get(100) is None

    def test_process_restart_invalidation(self):
        cache = DetectionCache()
        result = DetectionResult(pid=100)
        cache.put(100, result, process_create_time=1000.0)
        # Same process — should hit
        assert cache.get(100, process_create_time=1000.0) is result
        # Different creation time — process restarted
        assert cache.get(100, process_create_time=2000.0) is None

    def test_invalidate(self):
        cache = DetectionCache()
        cache.put(100, DetectionResult(pid=100))
        assert cache.invalidate(100) is True
        assert cache.get(100) is None
        assert cache.invalidate(100) is False

    def test_clear(self):
        cache = DetectionCache()
        for pid in range(10):
            cache.put(pid, DetectionResult(pid=pid))
        assert cache.size() == 10
        cache.clear()
        assert cache.size() == 0

    def test_cleanup_expired(self):
        cache = DetectionCache(ttl_seconds=0.1)
        for pid in range(5):
            cache.put(pid, DetectionResult(pid=pid))
        time.sleep(0.15)
        # Add a fresh one
        cache.put(99, DetectionResult(pid=99))
        removed = cache.cleanup_expired()
        assert removed == 5
        assert cache.size() == 1
        assert cache.get(99) is not None


# ── Detection Chain ────────────────────────────────────────────────


class TestDetectChain:
    """Tests for the detect() orchestrator function."""

    def test_detect_nonexistent_pid(self):
        """Detection of a bogus PID should not crash, returns result with vision fallback."""
        result = detect(pid=99999999, exe="fake.exe", use_cache=False)
        assert result.pid == 99999999
        # Should at least have vision fallback on any platform
        method_types = [m.method for m in result.methods]
        assert InteractionMethodType.VISION in method_types

    def test_detect_returns_detection_result(self):
        result = detect(pid=1, exe="test.exe", use_cache=False)
        assert isinstance(result, DetectionResult)
        assert result.pid == 1

    def test_detect_caching(self):
        """Second call should return cached result."""
        cache = DetectionCache(ttl_seconds=60)
        # Manually populate cache
        cached_result = DetectionResult(
            pid=42,
            exe="cached.exe",
            app_name="Cached App",
        )
        cache.put(42, cached_result)

        from naturo.detect import cache as cache_module
        original_cache = cache_module._global_cache
        try:
            cache_module._global_cache = cache
            from naturo.detect.chain import get_cache as chain_get_cache
            # Patch get_cache to return our cache
            import naturo.detect.chain as chain_mod
            old_get_cache = chain_mod.get_cache
            chain_mod.get_cache = lambda: cache

            result = detect(pid=42, use_cache=True)
            assert result is cached_result
        finally:
            chain_mod.get_cache = old_get_cache
            cache_module._global_cache = original_cache

    def test_detect_skip_cache(self):
        result = detect(pid=1, exe="test.exe", use_cache=False)
        assert isinstance(result, DetectionResult)

    def test_detect_quick_mode(self):
        """Quick mode should still return a valid result."""
        result = detect(pid=99999999, exe="fake.exe", use_cache=False, quick=True)
        assert isinstance(result, DetectionResult)

    def test_detect_result_serializable(self):
        """Result should be JSON-serializable via to_dict()."""
        import json
        result = detect(pid=1, exe="test.exe", use_cache=False)
        d = result.to_dict()
        # Should not raise
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

    @pytest.mark.skipif(
        platform.system() != "Windows",
        reason="Probe integration tests require Windows",
    )
    def test_detect_real_process_windows(self):
        """On Windows, detect the current Python process."""
        import os
        import sys
        result = detect(pid=os.getpid(), exe=sys.executable, use_cache=False)
        assert result.pid == os.getpid()
        assert len(result.methods) > 0
        assert result.recommended is not None


# ── Probes (cross-platform safe) ───────────────────────────────────


class TestProbeVision:
    """Vision probe tests — works on all platforms."""

    def test_vision_always_returns(self):
        from naturo.detect.probes import probe_vision
        result = probe_vision(pid=1, exe="anything.exe")
        assert result is not None
        assert result.method == InteractionMethodType.VISION
        assert result.status == ProbeStatus.FALLBACK


class TestProbesCrossPlatform:
    """Probes that return None on non-Windows should not crash."""

    def test_probe_cdp_non_windows(self):
        if platform.system() == "Windows":
            pytest.skip("Only tests non-Windows behavior")
        from naturo.detect.probes import probe_cdp
        assert probe_cdp(pid=1, exe="test.exe") is None

    def test_probe_uia_non_windows(self):
        if platform.system() == "Windows":
            pytest.skip("Only tests non-Windows behavior")
        from naturo.detect.probes import probe_uia
        assert probe_uia(pid=1, exe="test.exe") is None

    def test_probe_msaa_non_windows(self):
        if platform.system() == "Windows":
            pytest.skip("Only tests non-Windows behavior")
        from naturo.detect.probes import probe_msaa
        assert probe_msaa(pid=1, exe="test.exe") is None

    def test_probe_jab_non_windows(self):
        if platform.system() == "Windows":
            pytest.skip("Only tests non-Windows behavior")
        from naturo.detect.probes import probe_jab
        assert probe_jab(pid=1, exe="test.exe") is None

    def test_probe_ia2_non_windows(self):
        if platform.system() == "Windows":
            pytest.skip("Only tests non-Windows behavior")
        from naturo.detect.probes import probe_ia2
        assert probe_ia2(pid=1, exe="test.exe") is None


class TestFrameworkDetection:
    """Tests for DLL-based framework detection."""

    def test_detect_frameworks_unknown_exe(self):
        from naturo.detect.probes import detect_frameworks_from_dlls
        # Non-Windows or PID 0 — should not crash
        frameworks = detect_frameworks_from_dlls(pid=0, exe="unknown.exe")
        # On non-Windows, returns empty or inferred
        assert isinstance(frameworks, list)

    def test_detect_electron_from_exe_name(self):
        from naturo.detect.probes import detect_frameworks_from_dlls
        if platform.system() == "Windows":
            pytest.skip("This test checks non-Windows exe name heuristic")
        frameworks = detect_frameworks_from_dlls(pid=0, exe="/usr/bin/electron")
        types = [f.framework_type for f in frameworks]
        assert FrameworkType.ELECTRON in types

    def test_detect_java_from_exe_name(self):
        from naturo.detect.probes import detect_frameworks_from_dlls
        if platform.system() == "Windows":
            pytest.skip("This test checks non-Windows exe name heuristic")
        frameworks = detect_frameworks_from_dlls(pid=0, exe="/usr/bin/java")
        types = [f.framework_type for f in frameworks]
        assert FrameworkType.JAVA_SWING in types


class TestNativeCoreInit:
    """Tests for _get_native_core — ensures probes call init() (#208)."""

    def test_get_native_core_calls_init(self):
        """_get_native_core must call .init() on the NaturoCore instance."""
        from unittest.mock import patch, MagicMock
        import naturo.detect.probes as probes_mod

        # Reset cached instance
        probes_mod._native_core = None

        mock_core = MagicMock()
        with patch("naturo.bridge.NaturoCore", return_value=mock_core) as mock_cls:
            result = probes_mod._get_native_core()
            mock_cls.assert_called_once()
            mock_core.init.assert_called_once()
            assert result is mock_core

        # Cleanup
        probes_mod._native_core = None

    def test_get_native_core_caches_instance(self):
        """_get_native_core returns the same instance on subsequent calls."""
        from unittest.mock import patch, MagicMock
        import naturo.detect.probes as probes_mod

        # Reset cached instance
        probes_mod._native_core = None

        mock_core = MagicMock()
        with patch("naturo.bridge.NaturoCore", return_value=mock_core):
            first = probes_mod._get_native_core()
            second = probes_mod._get_native_core()
            assert first is second

        # Cleanup
        probes_mod._native_core = None

    def test_probe_uia_uses_initialized_core(self):
        """probe_uia should use _get_native_core (with init) not raw NaturoCore."""
        from unittest.mock import patch, MagicMock
        import naturo.detect.probes as probes_mod

        if platform.system() != "Windows":
            pytest.skip("probe_uia returns None on non-Windows")

        # Reset cached instance
        probes_mod._native_core = None

        mock_core = MagicMock()
        mock_element = MagicMock()
        mock_core.get_element_tree.return_value = mock_element

        with patch("naturo.detect.probes._get_native_core", return_value=mock_core) as mock_get:
            with patch("naturo.detect.probes._find_main_window", return_value=12345):
                result = probes_mod.probe_uia(pid=1234, exe="notepad.exe")
                mock_get.assert_called_once()
                mock_core.get_element_tree.assert_called_once_with(hwnd=12345, depth=1)
                assert result is not None
                assert result.method == InteractionMethodType.UIA
                assert result.status == ProbeStatus.AVAILABLE

        # Cleanup
        probes_mod._native_core = None


class TestFindMainWindowUwp:
    """Tests for _find_main_window UWP/ApplicationFrameHost support (#249)."""

    def test_returns_none_non_windows(self):
        """Should return None on non-Windows platforms."""
        if platform.system() == "Windows":
            pytest.skip("Only tests non-Windows behavior")
        from naturo.detect.probes import _find_main_window
        assert _find_main_window(pid=12345) is None

    def test_frame_hosts_pid_helper(self):
        """_frame_hosts_pid should detect child windows with matching PID."""
        if platform.system() != "Windows":
            pytest.skip("Windows-only test")

        from naturo.detect.probes import _frame_hosts_pid
        import ctypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        # We can't easily mock EnumChildWindows, but we can test it
        # against the desktop window (should not crash, may return False)
        desktop_hwnd = user32.GetDesktopWindow()
        result = _frame_hosts_pid(user32, desktop_hwnd, 0)
        assert isinstance(result, bool)


class TestAppInspectPidValidation:
    """Tests for app inspect --pid input validation (fixes #256).

    Verifies that invalid PIDs (0, negative, non-existent) are rejected
    with clear error messages instead of showing misleading 'Unknown' results.
    """

    def test_zero_pid_rejected(self):
        """PID 0 should be rejected with INVALID_INPUT error."""
        from click.testing import CliRunner
        from naturo.cli.app_cmd import app_inspect

        runner = CliRunner()
        result = runner.invoke(app_inspect, ["--pid", "0", "--json"])
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output or "Invalid PID" in result.output

    def test_negative_pid_rejected(self):
        """Negative PID should be rejected with INVALID_INPUT error."""
        from click.testing import CliRunner
        from naturo.cli.app_cmd import app_inspect

        runner = CliRunner()
        result = runner.invoke(app_inspect, ["--pid", "-1", "--json"])
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output or "Invalid PID" in result.output

    def test_nonexistent_pid_rejected(self):
        """Non-existent PID should be rejected with PROCESS_NOT_FOUND error."""
        from click.testing import CliRunner
        from naturo.cli.app_cmd import app_inspect
        from unittest.mock import patch

        # Use a PID that almost certainly doesn't exist
        runner = CliRunner()
        with patch("naturo.process.find_process", return_value=None):
            result = runner.invoke(app_inspect, ["--pid", "999999", "--json"])
        assert result.exit_code != 0
        assert "PROCESS_NOT_FOUND" in result.output or "No process found" in result.output


class TestUwpFrameworkDetection:
    """Tests for UWP app framework detection fallback (fixes #257).

    When DLL scanning is unavailable (common for protected UWP processes),
    framework detection should still identify UWP apps via exe name or path.
    """

    def test_calculator_detected_as_uwp_by_exe_name(self):
        """CalculatorApp.exe should be detected as UWP even without DLL scan."""
        from naturo.detect.probes import detect_frameworks_from_dlls
        from naturo.detect.models import FrameworkType
        from unittest.mock import patch

        # Simulate DLL scan failure (returns empty set)
        with patch("naturo.detect.probes._get_process_dlls", return_value=set()):
            frameworks = detect_frameworks_from_dlls(
                pid=12345, exe="C:\\Program Files\\WindowsApps\\Microsoft.WindowsCalculator\\CalculatorApp.exe"
            )

        assert len(frameworks) >= 1
        assert frameworks[0].framework_type == FrameworkType.UWP

    def test_windowsapps_path_detected_as_uwp(self):
        """Any exe in WindowsApps directory should be detected as UWP."""
        from naturo.detect.probes import detect_frameworks_from_dlls
        from naturo.detect.models import FrameworkType
        from unittest.mock import patch

        with patch("naturo.detect.probes._get_process_dlls", return_value=set()):
            frameworks = detect_frameworks_from_dlls(
                pid=12345, exe="C:\\Program Files\\WindowsApps\\SomeApp\\unknown.exe"
            )

        assert len(frameworks) >= 1
        assert frameworks[0].framework_type == FrameworkType.UWP

    def test_known_uwp_apps_detected(self):
        """All known UWP app exe names should be detected as UWP."""
        from naturo.detect.probes import detect_frameworks_from_dlls, _UWP_KNOWN_APPS
        from naturo.detect.models import FrameworkType
        from unittest.mock import patch

        for app_exe in ["calculatorapp.exe", "windowsterminal.exe", "windowscamera.exe"]:
            with patch("naturo.detect.probes._get_process_dlls", return_value=set()):
                frameworks = detect_frameworks_from_dlls(pid=12345, exe=app_exe)
            assert frameworks[0].framework_type == FrameworkType.UWP, f"{app_exe} not detected as UWP"

    def test_non_uwp_app_not_detected_as_uwp(self):
        """Non-UWP apps should not be detected as UWP."""
        from naturo.detect.probes import detect_frameworks_from_dlls
        from naturo.detect.models import FrameworkType
        from unittest.mock import patch

        with patch("naturo.detect.probes._get_process_dlls", return_value=set()):
            frameworks = detect_frameworks_from_dlls(pid=12345, exe="C:\\Windows\\system32\\cmd.exe")

        # Should fallback to WIN32 on Windows or UNKNOWN on other platforms
        assert frameworks[0].framework_type != FrameworkType.UWP

    def test_uwp_detected_from_bare_proc_name(self):
        """When proc.path is empty, proc.name (bare exe) should still detect UWP.

        Regression test for #257: UWP protected processes return empty path
        from find_process(). The fallback passes proc.name (e.g. 'CalculatorApp.exe')
        as the exe argument, and framework detection must still match it.
        """
        from naturo.detect.probes import detect_frameworks_from_dlls
        from naturo.detect.models import FrameworkType
        from unittest.mock import patch

        # Simulate what happens when proc.path="" and we fall back to proc.name
        with patch("naturo.detect.probes._get_process_dlls", return_value=set()):
            frameworks = detect_frameworks_from_dlls(pid=12345, exe="CalculatorApp.exe")

        assert len(frameworks) >= 1
        assert frameworks[0].framework_type == FrameworkType.UWP


# ── Probe Timeout ──────────────────────────────────────────────────


class TestProbeTimeout:
    """Tests for the per-probe timeout guard (#288)."""

    def test_fast_probe_returns_result(self):
        """A probe that completes quickly should return its result."""
        def fast_probe(pid, exe, hwnd):
            return InteractionMethod(
                method=InteractionMethodType.UIA,
                priority=METHOD_PRIORITY[InteractionMethodType.UIA],
                status=ProbeStatus.AVAILABLE,
                capabilities=["click"],
                confidence=0.9,
            )

        result = _run_probe_with_timeout(fast_probe, pid=123, exe="", hwnd=None)
        assert result is not None
        assert result.method == InteractionMethodType.UIA

    def test_hanging_probe_returns_none(self):
        """A probe that exceeds the timeout should return None, not hang."""
        import time
        import naturo.detect.chain as chain_mod
        orig = chain_mod._PROBE_TIMEOUT_SECONDS

        def hanging_probe(pid, exe, hwnd):
            time.sleep(60)  # Simulate indefinite hang
            return InteractionMethod(
                method=InteractionMethodType.CDP,
                priority=METHOD_PRIORITY[InteractionMethodType.CDP],
                status=ProbeStatus.AVAILABLE,
                capabilities=["dom"],
                confidence=0.9,
            )

        # Use a short timeout for the test
        try:
            chain_mod._PROBE_TIMEOUT_SECONDS = 0.5
            start = time.monotonic()
            result = _run_probe_with_timeout(hanging_probe, pid=123, exe="", hwnd=None)
            elapsed = time.monotonic() - start
        finally:
            chain_mod._PROBE_TIMEOUT_SECONDS = orig

        assert result is None, "Hanging probe should return None after timeout"
        assert elapsed < 5, f"Timeout took too long: {elapsed:.1f}s"

    def test_probe_exception_propagates(self):
        """A probe that raises an exception should propagate the error."""
        def broken_probe(pid, exe, hwnd):
            raise RuntimeError("probe internal error")

        with pytest.raises(RuntimeError, match="probe internal error"):
            _run_probe_with_timeout(broken_probe, pid=123, exe="", hwnd=None)
