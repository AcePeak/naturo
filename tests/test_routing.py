"""Tests for naturo.routing — auto-routing for action commands."""
import pytest
from unittest.mock import MagicMock, patch

from naturo.routing import RoutingResult, resolve_method


class TestRoutingResult:
    """Tests for RoutingResult dataclass."""

    def test_default_values(self):
        """RoutingResult has sensible defaults."""
        result = RoutingResult()
        assert result.pid is None
        assert result.app_name == ""
        assert result.method == "vision"
        assert result.source == "auto"
        assert result.framework == "unknown"
        assert result.confidence == 0.0

    def test_to_dict_complete(self):
        """to_dict includes all fields."""
        result = RoutingResult(
            pid=1234,
            app_name="Notepad",
            method="uia",
            source="auto",
            framework="win32",
            confidence=0.95,
        )
        d = result.to_dict()
        assert d == {
            "pid": 1234,
            "app": "Notepad",
            "method": "uia",
            "source": "auto",
            "framework": "win32",
            "confidence": 0.95,
        }

    def test_to_dict_defaults(self):
        """to_dict works with default values."""
        result = RoutingResult()
        d = result.to_dict()
        assert d["pid"] is None
        assert d["method"] == "vision"
        assert d["source"] == "auto"


class TestResolveMethodExplicit:
    """Tests for resolve_method with explicit --method override."""

    def test_explicit_method_skips_detection(self):
        """When method is not 'auto', detection is skipped entirely."""
        result = resolve_method(app="Notepad", explicit_method="uia")
        assert result.method == "uia"
        assert result.source == "explicit"

    def test_explicit_method_preserves_app_name(self):
        """Explicit method preserves the app name."""
        result = resolve_method(app="Chrome", explicit_method="cdp")
        assert result.app_name == "Chrome"
        assert result.method == "cdp"

    def test_explicit_method_preserves_pid(self):
        """Explicit method preserves the PID."""
        result = resolve_method(pid=9999, explicit_method="msaa")
        assert result.pid == 9999
        assert result.method == "msaa"

    @pytest.mark.parametrize("method", ["cdp", "uia", "msaa", "jab", "ia2", "vision"])
    def test_all_explicit_methods(self, method):
        """All valid methods can be set explicitly."""
        result = resolve_method(explicit_method=method)
        assert result.method == method
        assert result.source == "explicit"


class TestResolveMethodNoTarget:
    """Tests for resolve_method without app/pid."""

    def test_no_target_defaults_to_vision(self):
        """Without app or pid, defaults to vision."""
        result = resolve_method()
        assert result.method == "vision"
        assert result.source == "auto"
        assert result.pid is None

    def test_no_target_auto_method(self):
        """Auto method with no target returns vision."""
        result = resolve_method(explicit_method="auto")
        assert result.method == "vision"


class TestResolveMethodWithApp:
    """Tests for resolve_method with app name resolution."""

    @patch("naturo.routing._find_pid_by_window_title", return_value=None)
    @patch("naturo.process.find_process")
    def test_app_not_found_falls_back_to_vision(self, mock_find, mock_title):
        """When app is not found by process name or window title, falls back to vision."""
        mock_find.return_value = None
        result = resolve_method(app="NonExistentApp")
        assert result.method == "vision"
        assert result.source == "auto"
        assert result.app_name == "NonExistentApp"

    @patch("naturo.detect.chain.detect")
    @patch("naturo.process.find_process")
    def test_app_found_runs_detection(self, mock_find, mock_detect):
        """When app is found, runs detection chain."""
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_proc.name = "notepad.exe"
        mock_find.return_value = mock_proc

        mock_method = MagicMock()
        mock_method.method.value = "uia"
        mock_method.confidence = 0.9

        mock_framework = MagicMock()
        mock_framework.framework_type.value = "win32"

        mock_result = MagicMock()
        mock_result.best_method.return_value = mock_method
        mock_result.frameworks = [mock_framework]
        mock_detect.return_value = mock_result

        result = resolve_method(app="Notepad")
        assert result.method == "uia"
        assert result.source == "auto"
        assert result.pid == 1234
        assert result.framework == "win32"
        assert result.confidence == 0.9

    @patch("naturo.detect.chain.detect")
    @patch("naturo.process.find_process")
    def test_detection_no_methods_falls_back(self, mock_find, mock_detect):
        """When detection finds no methods, falls back to vision."""
        mock_proc = MagicMock()
        mock_proc.pid = 5678
        mock_proc.name = "unknown.exe"
        mock_find.return_value = mock_proc

        mock_result = MagicMock()
        mock_result.best_method.return_value = None
        mock_result.frameworks = []
        mock_detect.return_value = mock_result

        result = resolve_method(app="Unknown")
        assert result.method == "vision"
        assert result.source == "auto"

    @patch("naturo.process.find_process")
    def test_process_resolution_exception(self, mock_find):
        """When find_process raises, falls back to vision gracefully."""
        mock_find.side_effect = RuntimeError("process lookup failed")
        result = resolve_method(app="CrashApp")
        assert result.method == "vision"
        assert result.source == "auto"


class TestResolveMethodWindowTitleFallback:
    """(#430) Tests for window title fallback when process name doesn't match."""

    @patch("naturo.detect.chain.detect")
    @patch("naturo.routing._find_pid_by_window_title", return_value=5678)
    @patch("naturo.process.find_process", return_value=None)
    def test_window_title_fallback_resolves_pid(
        self, mock_find, mock_title, mock_detect
    ):
        """When process name fails but window title matches, resolve PID."""
        mock_method = MagicMock()
        mock_method.method.value = "uia"
        mock_method.confidence = 0.9

        mock_framework = MagicMock()
        mock_framework.framework_type.value = "win32"

        mock_result = MagicMock()
        mock_result.best_method.return_value = mock_method
        mock_result.frameworks = [mock_framework]
        mock_detect.return_value = mock_result

        result = resolve_method(app="计算器")
        assert result.pid == 5678
        assert result.method == "uia"
        assert result.source == "auto"
        mock_title.assert_called_once_with("计算器")

    @patch("naturo.routing._find_pid_by_window_title", return_value=None)
    @patch("naturo.process.find_process", return_value=None)
    def test_window_title_also_fails_falls_back_to_vision(
        self, mock_find, mock_title
    ):
        """When both process name and window title fail, fall back to vision."""
        result = resolve_method(app="不存在的应用")
        assert result.method == "vision"
        assert result.source == "auto"

    @patch("naturo.routing._find_pid_by_window_title")
    @patch("naturo.process.find_process")
    def test_process_found_skips_window_title(self, mock_find, mock_title):
        """When process name matches, window title lookup is not attempted."""
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_proc.name = "notepad.exe"
        mock_find.return_value = mock_proc

        # Mock detect to return something
        with patch("naturo.detect.chain.detect") as mock_detect:
            mock_result = MagicMock()
            mock_result.best_method.return_value = None
            mock_result.frameworks = []
            mock_detect.return_value = mock_result

            resolve_method(app="notepad")

        mock_title.assert_not_called()


class TestResolveMethodWithPid:
    """Tests for resolve_method with explicit PID."""

    @patch("naturo.detect.chain.detect")
    def test_pid_runs_detection_directly(self, mock_detect):
        """PID skips process resolution, runs detection directly."""
        mock_method = MagicMock()
        mock_method.method.value = "cdp"
        mock_method.confidence = 0.85

        mock_framework = MagicMock()
        mock_framework.framework_type.value = "electron"

        mock_result = MagicMock()
        mock_result.best_method.return_value = mock_method
        mock_result.frameworks = [mock_framework]
        mock_detect.return_value = mock_result

        result = resolve_method(pid=4321)
        assert result.method == "cdp"
        assert result.pid == 4321
        assert result.framework == "electron"

    @patch("naturo.detect.chain.detect")
    def test_detection_exception_falls_back(self, mock_detect):
        """When detection chain raises, falls back to vision."""
        mock_detect.side_effect = RuntimeError("COM error")
        result = resolve_method(pid=9999)
        assert result.method == "vision"
        assert result.source == "auto"
        assert result.pid == 9999


class TestResolveMethodEdgeCases:
    """Edge cases and integration scenarios."""

    def test_explicit_auto_with_no_target(self):
        """Explicitly passing 'auto' with no target returns vision."""
        result = resolve_method(explicit_method="auto")
        assert result.method == "vision"

    @patch("naturo.detect.chain.detect")
    @patch("naturo.process.find_process")
    def test_app_and_pid_prefers_pid(self, mock_find, mock_detect):
        """When both app and pid are given, pid takes precedence."""
        mock_method = MagicMock()
        mock_method.method.value = "uia"
        mock_method.confidence = 1.0

        mock_result = MagicMock()
        mock_result.best_method.return_value = mock_method
        mock_result.frameworks = []
        mock_detect.return_value = mock_result

        result = resolve_method(app="Notepad", pid=1111)
        # pid is set, so find_process is not called
        mock_find.assert_not_called()
        assert result.pid == 1111

    @patch("naturo.detect.chain.detect")
    @patch("naturo.process.find_process")
    def test_detection_no_frameworks_unknown(self, mock_find, mock_detect):
        """When detection returns no frameworks, framework is 'unknown'."""
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_proc.name = "app.exe"
        mock_find.return_value = mock_proc

        mock_method = MagicMock()
        mock_method.method.value = "uia"
        mock_method.confidence = 0.5

        mock_result = MagicMock()
        mock_result.best_method.return_value = mock_method
        mock_result.frameworks = []
        mock_detect.return_value = mock_result

        result = resolve_method(app="App")
        assert result.framework == "unknown"
        assert result.method == "uia"
