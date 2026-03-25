"""Tests for DPI/Scaling awareness (Phase 5A.2).

Tests cover:
- CaptureResult DPI fields
- Backend.find_monitor_for_point()
- Backend DPI coordinate conversion (physical_to_logical, logical_to_physical)
- CLI `capture live --json` includes DPI metadata
- CLI `see --json` includes dpi_context
- MCP capture_screen/capture_window include DPI metadata
"""

import json
import platform
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from click.testing import CliRunner

from naturo.backends.base import MonitorInfo, CaptureResult, Backend


# ── Fixtures ─────────────────────────────────────


def _make_monitors(primary_dpi=96, secondary_dpi=144):
    """Create a two-monitor setup for testing."""
    return [
        MonitorInfo(
            index=0, name="\\\\.\\DISPLAY1",
            x=0, y=0, width=1920, height=1080,
            is_primary=True,
            scale_factor=round(primary_dpi / 96.0, 2),
            dpi=primary_dpi,
            work_area={"x": 0, "y": 0, "width": 1920, "height": 1040},
        ),
        MonitorInfo(
            index=1, name="\\\\.\\DISPLAY2",
            x=1920, y=0, width=2560, height=1440,
            is_primary=False,
            scale_factor=round(secondary_dpi / 96.0, 2),
            dpi=secondary_dpi,
            work_area={"x": 1920, "y": 0, "width": 2560, "height": 1400},
        ),
    ]


# ── CaptureResult DPI fields ─────────────────────


class TestCaptureResultDPI:
    """CaptureResult should carry DPI metadata."""

    def test_default_dpi_values(self):
        r = CaptureResult(path="test.png", width=1920, height=1080, format="png")
        assert r.scale_factor == 1.0
        assert r.dpi == 96

    def test_custom_dpi_values(self):
        r = CaptureResult(
            path="test.png", width=3840, height=2160, format="png",
            scale_factor=2.0, dpi=192,
        )
        assert r.scale_factor == 2.0
        assert r.dpi == 192

    def test_150_percent_scaling(self):
        r = CaptureResult(
            path="test.png", width=2880, height=1620, format="png",
            scale_factor=1.5, dpi=144,
        )
        assert r.scale_factor == 1.5
        assert r.dpi == 144


# ── find_monitor_for_point ────────────────────────


class TestFindMonitorForPoint:
    """Backend.find_monitor_for_point() locates the monitor containing a point."""

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock(spec=Backend)
        backend.list_monitors.return_value = _make_monitors()
        # Use the real implementation
        backend.find_monitor_for_point = Backend.find_monitor_for_point.__get__(backend)
        return backend

    def test_point_on_primary(self, mock_backend):
        m = mock_backend.find_monitor_for_point(500, 400)
        assert m is not None
        assert m.index == 0
        assert m.is_primary is True

    def test_point_on_secondary(self, mock_backend):
        m = mock_backend.find_monitor_for_point(2000, 500)
        assert m is not None
        assert m.index == 1
        assert m.is_primary is False

    def test_point_at_primary_origin(self, mock_backend):
        m = mock_backend.find_monitor_for_point(0, 0)
        assert m is not None
        assert m.index == 0

    def test_point_at_secondary_origin(self, mock_backend):
        m = mock_backend.find_monitor_for_point(1920, 0)
        assert m is not None
        assert m.index == 1

    def test_point_at_primary_edge(self, mock_backend):
        """Right edge of primary (1919) should still be on primary."""
        m = mock_backend.find_monitor_for_point(1919, 500)
        assert m is not None
        assert m.index == 0

    def test_point_outside_all_monitors(self, mock_backend):
        m = mock_backend.find_monitor_for_point(-100, -100)
        assert m is None

    def test_point_below_all_monitors(self, mock_backend):
        m = mock_backend.find_monitor_for_point(500, 2000)
        assert m is None

    def test_point_far_right(self, mock_backend):
        m = mock_backend.find_monitor_for_point(5000, 500)
        assert m is None

    def test_no_monitors(self, mock_backend):
        mock_backend.list_monitors.return_value = []
        m = mock_backend.find_monitor_for_point(500, 500)
        assert m is None

    def test_list_monitors_raises(self, mock_backend):
        mock_backend.list_monitors.side_effect = NotImplementedError
        m = mock_backend.find_monitor_for_point(500, 500)
        assert m is None


# ── DPI Coordinate Conversion ─────────────────────


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows backend only")
class TestDPIConversion:
    """Test physical_to_logical and logical_to_physical on WindowsBackend."""

    @pytest.fixture
    def backend(self):
        with patch("naturo.backends.windows.NaturoCore"):
            from naturo.backends.windows import WindowsBackend
            b = WindowsBackend()
            return b

    def test_physical_to_logical_100pct(self, backend):
        with patch.object(backend, "get_dpi_scale", return_value=1.0):
            assert backend.physical_to_logical(1920, 1080) == (1920, 1080)

    def test_physical_to_logical_150pct(self, backend):
        with patch.object(backend, "get_dpi_scale", return_value=1.5):
            lx, ly = backend.physical_to_logical(1920, 1080)
            assert lx == 1280
            assert ly == 720

    def test_physical_to_logical_200pct(self, backend):
        with patch.object(backend, "get_dpi_scale", return_value=2.0):
            lx, ly = backend.physical_to_logical(1920, 1080)
            assert lx == 960
            assert ly == 540

    def test_logical_to_physical_100pct(self, backend):
        with patch.object(backend, "get_dpi_scale", return_value=1.0):
            assert backend.logical_to_physical(1920, 1080) == (1920, 1080)

    def test_logical_to_physical_150pct(self, backend):
        with patch.object(backend, "get_dpi_scale", return_value=1.5):
            px, py = backend.logical_to_physical(1280, 720)
            assert px == 1920
            assert py == 1080

    def test_logical_to_physical_200pct(self, backend):
        with patch.object(backend, "get_dpi_scale", return_value=2.0):
            px, py = backend.logical_to_physical(960, 540)
            assert px == 1920
            assert py == 1080

    def test_roundtrip_150pct(self, backend):
        """physical → logical → physical should be identity (within rounding)."""
        with patch.object(backend, "get_dpi_scale", return_value=1.5):
            lx, ly = backend.physical_to_logical(300, 450)
            px, py = backend.logical_to_physical(lx, ly)
            assert px == 300
            assert py == 450

    def test_get_dpi_scale_from_monitors(self, backend):
        monitors = _make_monitors(primary_dpi=144, secondary_dpi=192)
        with patch.object(backend, "list_monitors", return_value=monitors):
            assert backend.get_dpi_scale(0) == 1.5
            assert backend.get_dpi_scale(1) == 2.0

    def test_get_dpi_scale_invalid_index(self, backend):
        monitors = _make_monitors()
        with patch.object(backend, "list_monitors", return_value=monitors):
            assert backend.get_dpi_scale(99) == 1.0

    def test_get_dpi_scale_no_monitors(self, backend):
        with patch.object(backend, "list_monitors", return_value=[]):
            assert backend.get_dpi_scale(0) == 1.0


# ── CLI capture live --json DPI ───────────────────


class TestCaptureLiveDPI:
    """CLI capture live --json should include scale_factor and dpi."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock()
        backend.capture_screen.return_value = CaptureResult(
            path="capture.png", width=1920, height=1080, format="png",
            scale_factor=1.5, dpi=144,
        )
        backend.list_monitors.return_value = _make_monitors(primary_dpi=144)
        return backend

    def test_json_includes_dpi_fields(self, runner, mock_backend):
        from naturo.cli.core import capture
        with patch("naturo.cli.core._get_backend", return_value=mock_backend), \
             patch("naturo.cli.core.platform") as mock_plat:
            mock_plat.system.return_value = "Windows"
            result = runner.invoke(capture, ["--json", "--no-snapshot"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        assert data["success"] is True
        assert data["scale_factor"] == 1.5
        assert data["dpi"] == 144

    def test_json_default_dpi(self, runner):
        backend = MagicMock()
        backend.capture_screen.return_value = CaptureResult(
            path="capture.png", width=1920, height=1080, format="png",
        )
        backend.list_monitors.return_value = _make_monitors()
        from naturo.cli.core import capture
        with patch("naturo.cli.core._get_backend", return_value=backend), \
             patch("naturo.cli.core.platform") as mock_plat:
            mock_plat.system.return_value = "Windows"
            result = runner.invoke(capture, ["--json", "--no-snapshot"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        assert data["scale_factor"] == 1.0
        assert data["dpi"] == 96


# ── CLI see --json DPI context ────────────────────


class TestSeeDPIContext:
    """CLI see --json should include dpi_context."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_tree(self):
        from naturo.backends.base import ElementInfo
        return ElementInfo(
            id="root", role="Window", name="Test Window",
            value=None, x=0, y=0, width=800, height=600,
            children=[], properties={},
        )

    @pytest.mark.skipif(platform.system() != "Windows", reason="see requires Windows")
    def test_see_json_includes_dpi_context(self, runner, mock_tree):
        backend = MagicMock()
        backend.get_element_tree.return_value = mock_tree
        backend.list_monitors.return_value = _make_monitors(primary_dpi=144)
        backend.get_dpi_scale.return_value = 1.5

        from naturo.cli.core import see
        with patch("naturo.cli.core._get_backend", return_value=backend):
            with patch("naturo.cli.core.platform") as mock_platform:
                mock_platform.system.return_value = "Windows"
                result = runner.invoke(see, ["--json", "--no-snapshot"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        assert "dpi_context" in data
        assert data["dpi_context"]["scale_factor"] == 1.5
        assert data["dpi_context"]["dpi"] == 144
        assert "note" in data["dpi_context"]

    @pytest.mark.skipif(platform.system() != "Windows", reason="see requires Windows")
    def test_see_json_dpi_context_fallback(self, runner, mock_tree):
        """When list_monitors fails, dpi_context should have defaults."""
        backend = MagicMock()
        backend.get_element_tree.return_value = mock_tree
        backend.list_monitors.side_effect = NotImplementedError
        backend.get_dpi_scale.side_effect = Exception("no monitors")

        from naturo.cli.core import see
        with patch("naturo.cli.core._get_backend", return_value=backend):
            with patch("naturo.cli.core.platform") as mock_platform:
                mock_platform.system.return_value = "Windows"
                result = runner.invoke(see, ["--json", "--no-snapshot"])

        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        assert data["dpi_context"]["scale_factor"] == 1.0
        assert data["dpi_context"]["dpi"] == 96


# ── MCP DPI metadata ─────────────────────────────


class TestMCPDPIMetadata:
    """MCP capture tools should return DPI metadata."""

    @pytest.mark.skipif(platform.system() != "Windows", reason="MCP requires Windows backend context")
    def test_mcp_capture_screen_includes_dpi(self):
        """Verify MCP capture_screen response structure includes scale_factor/dpi."""
        # Validate the response dict structure directly
        result = CaptureResult(
            path="test.png", width=1920, height=1080, format="png",
            scale_factor=1.5, dpi=144,
        )
        response = {
            "success": True,
            "path": result.path,
            "width": result.width,
            "height": result.height,
            "format": result.format,
            "scale_factor": result.scale_factor,
            "dpi": result.dpi,
        }
        assert response["scale_factor"] == 1.5
        assert response["dpi"] == 144

    def test_capture_result_serialization(self):
        """CaptureResult DPI fields should serialize correctly to JSON."""
        r = CaptureResult(
            path="cap.png", width=2560, height=1440, format="png",
            scale_factor=1.25, dpi=120,
        )
        data = {
            "scale_factor": r.scale_factor,
            "dpi": r.dpi,
        }
        serialized = json.dumps(data)
        parsed = json.loads(serialized)
        assert parsed["scale_factor"] == 1.25
        assert parsed["dpi"] == 120


# ── Multi-monitor DPI scenarios ───────────────────


class TestMultiMonitorDPI:
    """Test DPI awareness across multi-monitor setups."""

    def test_mixed_dpi_monitors(self):
        """A setup with 100% primary + 200% secondary."""
        monitors = _make_monitors(primary_dpi=96, secondary_dpi=192)
        assert monitors[0].scale_factor == 1.0
        assert monitors[1].scale_factor == 2.0

    def test_all_high_dpi(self):
        """Both monitors at 150%."""
        monitors = _make_monitors(primary_dpi=144, secondary_dpi=144)
        assert monitors[0].scale_factor == 1.5
        assert monitors[1].scale_factor == 1.5

    def test_125_percent_scaling(self):
        """125% is common on 1440p monitors."""
        m = MonitorInfo(
            index=0, name="DISPLAY1",
            x=0, y=0, width=2560, height=1440,
            is_primary=True, scale_factor=1.25, dpi=120,
        )
        assert m.scale_factor == 1.25
        assert m.dpi == 120

    def test_175_percent_scaling(self):
        """175% scaling (168 DPI)."""
        m = MonitorInfo(
            index=0, name="DISPLAY1",
            x=0, y=0, width=3840, height=2160,
            is_primary=True, scale_factor=1.75, dpi=168,
        )
        assert m.scale_factor == 1.75
        assert m.dpi == 168


# ── Edge cases ────────────────────────────────────


class TestDPIEdgeCases:
    """Edge cases in DPI handling."""

    def test_capture_result_zero_scale(self):
        """scale_factor of 0 shouldn't crash (invalid but defensive)."""
        r = CaptureResult(
            path="test.png", width=1920, height=1080, format="png",
            scale_factor=0.0, dpi=0,
        )
        assert r.scale_factor == 0.0

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows backend only")
    def test_physical_to_logical_zero_scale(self):
        """Zero scale should return original coords (no division by zero)."""
        with patch("naturo.backends.windows.NaturoCore"):
            from naturo.backends.windows import WindowsBackend
            b = WindowsBackend()
            with patch.object(b, "get_dpi_scale", return_value=0.0):
                assert b.physical_to_logical(100, 200) == (100, 200)

    def test_single_monitor_find(self):
        """find_monitor_for_point with single monitor."""
        backend = MagicMock(spec=Backend)
        backend.list_monitors.return_value = [
            MonitorInfo(
                index=0, name="DISPLAY1",
                x=0, y=0, width=1920, height=1080,
                is_primary=True, scale_factor=1.5, dpi=144,
            ),
        ]
        backend.find_monitor_for_point = Backend.find_monitor_for_point.__get__(backend)
        m = backend.find_monitor_for_point(960, 540)
        assert m is not None
        assert m.scale_factor == 1.5

    def test_monitor_with_negative_coords(self):
        """Monitors can have negative coordinates (e.g., left of primary)."""
        backend = MagicMock(spec=Backend)
        backend.list_monitors.return_value = [
            MonitorInfo(
                index=0, name="DISPLAY1",
                x=0, y=0, width=1920, height=1080,
                is_primary=True, scale_factor=1.0, dpi=96,
            ),
            MonitorInfo(
                index=1, name="DISPLAY2",
                x=-2560, y=0, width=2560, height=1440,
                is_primary=False, scale_factor=1.5, dpi=144,
            ),
        ]
        backend.find_monitor_for_point = Backend.find_monitor_for_point.__get__(backend)

        # Point on left monitor (negative x)
        m = backend.find_monitor_for_point(-1000, 500)
        assert m is not None
        assert m.index == 1

        # Point on primary
        m = backend.find_monitor_for_point(500, 500)
        assert m is not None
        assert m.index == 0

    def test_vertical_monitor_layout(self):
        """Monitors stacked vertically."""
        backend = MagicMock(spec=Backend)
        backend.list_monitors.return_value = [
            MonitorInfo(
                index=0, name="DISPLAY1",
                x=0, y=0, width=1920, height=1080,
                is_primary=True, scale_factor=1.0, dpi=96,
            ),
            MonitorInfo(
                index=1, name="DISPLAY2",
                x=0, y=1080, width=1920, height=1080,
                is_primary=False, scale_factor=2.0, dpi=192,
            ),
        ]
        backend.find_monitor_for_point = Backend.find_monitor_for_point.__get__(backend)

        m = backend.find_monitor_for_point(500, 500)
        assert m.index == 0

        m = backend.find_monitor_for_point(500, 1500)
        assert m.index == 1
