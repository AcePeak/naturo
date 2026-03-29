"""Tests for naturo.detect.models — detection system data models."""

from naturo.detect.models import (
    DetectionResult,
    FrameworkInfo,
    FrameworkType,
    InteractionMethod,
    InteractionMethodType,
    METHOD_PRIORITY,
    ProbeStatus,
)


class TestEnums:
    """Enum definitions and string values."""

    def test_framework_type_values(self):
        assert FrameworkType.ELECTRON == "electron"
        assert FrameworkType.UWP == "uwp"
        assert FrameworkType.UNKNOWN == "unknown"

    def test_interaction_method_type_values(self):
        assert InteractionMethodType.CDP == "cdp"
        assert InteractionMethodType.UIA == "uia"
        assert InteractionMethodType.VISION == "vision"

    def test_probe_status_values(self):
        assert ProbeStatus.AVAILABLE == "available"
        assert ProbeStatus.UNAVAILABLE == "unavailable"
        assert ProbeStatus.ERROR == "error"

    def test_method_priority_order(self):
        assert METHOD_PRIORITY[InteractionMethodType.CDP] < METHOD_PRIORITY[InteractionMethodType.UIA]
        assert METHOD_PRIORITY[InteractionMethodType.UIA] < METHOD_PRIORITY[InteractionMethodType.VISION]


class TestInteractionMethod:
    """InteractionMethod dataclass."""

    def test_defaults(self):
        m = InteractionMethod(
            method=InteractionMethodType.UIA,
            priority=2,
            status=ProbeStatus.AVAILABLE,
        )
        assert m.capabilities == []
        assert m.metadata == {}
        assert m.confidence == 1.0

    def test_to_dict_basic(self):
        m = InteractionMethod(
            method=InteractionMethodType.CDP,
            priority=1,
            status=ProbeStatus.AVAILABLE,
            capabilities=["click", "type", "inspect"],
            confidence=0.95,
        )
        d = m.to_dict()
        assert d["method"] == "cdp"
        assert d["priority"] == 1
        assert d["status"] == "available"
        assert d["capabilities"] == ["click", "type", "inspect"]
        assert d["confidence"] == 0.95
        assert "metadata" not in d

    def test_to_dict_with_metadata(self):
        m = InteractionMethod(
            method=InteractionMethodType.CDP,
            priority=1,
            status=ProbeStatus.AVAILABLE,
            metadata={"debug_port": 9222},
        )
        d = m.to_dict()
        assert d["metadata"] == {"debug_port": 9222}


class TestFrameworkInfo:
    """FrameworkInfo dataclass."""

    def test_to_dict_minimal(self):
        f = FrameworkInfo(framework_type=FrameworkType.WPF)
        d = f.to_dict()
        assert d == {"type": "wpf"}

    def test_to_dict_full(self):
        f = FrameworkInfo(
            framework_type=FrameworkType.ELECTRON,
            version="28.0.0",
            dll_signatures=["libcef.dll", "electron.exe"],
        )
        d = f.to_dict()
        assert d["type"] == "electron"
        assert d["version"] == "28.0.0"
        assert d["dll_signatures"] == ["libcef.dll", "electron.exe"]


class TestDetectionResult:
    """DetectionResult dataclass and best_method logic."""

    def _make_method(self, method_type, priority, status=ProbeStatus.AVAILABLE):
        return InteractionMethod(method=method_type, priority=priority, status=status)

    def test_best_method_picks_lowest_priority(self):
        result = DetectionResult(
            pid=1234,
            methods=[
                self._make_method(InteractionMethodType.UIA, 2),
                self._make_method(InteractionMethodType.CDP, 1),
                self._make_method(InteractionMethodType.VISION, 6),
            ],
        )
        best = result.best_method()
        assert best is not None
        assert best.method == InteractionMethodType.CDP

    def test_best_method_skips_unavailable(self):
        result = DetectionResult(
            pid=1234,
            methods=[
                self._make_method(InteractionMethodType.CDP, 1, ProbeStatus.UNAVAILABLE),
                self._make_method(InteractionMethodType.UIA, 2, ProbeStatus.AVAILABLE),
            ],
        )
        best = result.best_method()
        assert best is not None
        assert best.method == InteractionMethodType.UIA

    def test_best_method_accepts_fallback(self):
        result = DetectionResult(
            pid=1234,
            methods=[
                self._make_method(InteractionMethodType.MSAA, 3, ProbeStatus.FALLBACK),
            ],
        )
        best = result.best_method()
        assert best is not None
        assert best.method == InteractionMethodType.MSAA

    def test_best_method_returns_none_when_all_unavailable(self):
        result = DetectionResult(
            pid=1234,
            methods=[
                self._make_method(InteractionMethodType.CDP, 1, ProbeStatus.UNAVAILABLE),
                self._make_method(InteractionMethodType.UIA, 2, ProbeStatus.ERROR),
            ],
        )
        assert result.best_method() is None

    def test_best_method_returns_none_when_empty(self):
        result = DetectionResult(pid=1234)
        assert result.best_method() is None

    def test_to_dict(self):
        result = DetectionResult(
            pid=5678,
            exe="C:\\Program Files\\App\\app.exe",
            app_name="MyApp",
            frameworks=[FrameworkInfo(framework_type=FrameworkType.WPF)],
            methods=[
                self._make_method(InteractionMethodType.UIA, 2),
            ],
            notes="Detected via DLL scan",
        )
        d = result.to_dict()
        assert d["pid"] == 5678
        assert d["exe"] == "C:\\Program Files\\App\\app.exe"
        assert d["app"] == "MyApp"
        assert d["framework"]["detected"] == [{"type": "wpf"}]
        assert len(d["interaction_methods"]) == 1
        assert d["recommended"] == "uia"
        assert d["notes"] == "Detected via DLL scan"

    def test_to_dict_no_methods(self):
        result = DetectionResult(pid=1)
        d = result.to_dict()
        assert d["recommended"] is None
        assert d["interaction_methods"] == []
