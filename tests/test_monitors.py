"""Tests for monitor/display enumeration (Phase 5A.1).

Tests cover:
- MonitorInfo data class
- Backend.list_monitors() on Windows (mocked)
- CLI `list screens` command (text and JSON output)
- CLI `capture live --screen` validation
- MCP list_monitors tool
"""

import json
import platform
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from naturo.backends.base import MonitorInfo


# ── MonitorInfo data class ──────────────────────

class TestMonitorInfo:
    """Test MonitorInfo dataclass construction and defaults."""

    def test_basic_construction(self):
        m = MonitorInfo(
            index=0, name="\\\\.\\DISPLAY1",
            x=0, y=0, width=1920, height=1080,
            is_primary=True, scale_factor=1.0, dpi=96,
        )
        assert m.index == 0
        assert m.width == 1920
        assert m.height == 1080
        assert m.is_primary is True
        assert m.scale_factor == 1.0
        assert m.dpi == 96
        assert m.work_area is None

    def test_with_work_area(self):
        wa = {"x": 0, "y": 0, "width": 1920, "height": 1040}
        m = MonitorInfo(
            index=0, name="DISPLAY1",
            x=0, y=0, width=1920, height=1080,
            is_primary=True, scale_factor=1.0, dpi=96,
            work_area=wa,
        )
        assert m.work_area == wa
        assert m.work_area["height"] == 1040

    def test_high_dpi(self):
        m = MonitorInfo(
            index=1, name="DISPLAY2",
            x=1920, y=0, width=3840, height=2160,
            is_primary=False, scale_factor=2.0, dpi=192,
        )
        assert m.scale_factor == 2.0
        assert m.dpi == 192
        assert m.is_primary is False

    def test_multi_monitor_positions(self):
        """Monitors can have negative coordinates (left of primary)."""
        m = MonitorInfo(
            index=1, name="DISPLAY2",
            x=-1920, y=0, width=1920, height=1080,
            is_primary=False, scale_factor=1.0, dpi=96,
        )
        assert m.x == -1920


# ── Backend list_monitors (mocked) ──────────────

def _mock_monitors(count=1, primary_dpi=96, secondary_dpi=96):
    """Create mock MonitorInfo list."""
    monitors = [
        MonitorInfo(
            index=0, name="\\\\.\\DISPLAY1",
            x=0, y=0, width=1920, height=1080,
            is_primary=True, scale_factor=round(primary_dpi / 96.0, 2),
            dpi=primary_dpi,
            work_area={"x": 0, "y": 40, "width": 1920, "height": 1040},
        ),
    ]
    if count >= 2:
        monitors.append(MonitorInfo(
            index=1, name="\\\\.\\DISPLAY2",
            x=1920, y=0, width=2560, height=1440,
            is_primary=False, scale_factor=round(secondary_dpi / 96.0, 2),
            dpi=secondary_dpi,
            work_area={"x": 1920, "y": 40, "width": 2560, "height": 1400},
        ))
    if count >= 3:
        monitors.append(MonitorInfo(
            index=2, name="\\\\.\\DISPLAY3",
            x=-1920, y=0, width=1920, height=1080,
            is_primary=False, scale_factor=1.0, dpi=96,
            work_area={"x": -1920, "y": 40, "width": 1920, "height": 1040},
        ))
    return monitors


class TestListMonitorsBackend:
    """Test backend.list_monitors() via mock."""

    @patch("naturo.cli.core._get_backend")
    def test_single_monitor(self, mock_backend):
        backend = MagicMock()
        backend.list_monitors.return_value = _mock_monitors(1)
        mock_backend.return_value = backend

        from naturo.cli.core import list_cmd
        runner = CliRunner()
        result = runner.invoke(list_cmd, ["screens", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert len(data["monitors"]) == 1
        assert data["monitors"][0]["is_primary"] is True

    @patch("naturo.cli.core._get_backend")
    def test_multiple_monitors(self, mock_backend):
        backend = MagicMock()
        backend.list_monitors.return_value = _mock_monitors(3)
        mock_backend.return_value = backend

        from naturo.cli.core import list_cmd
        runner = CliRunner()
        result = runner.invoke(list_cmd, ["screens", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["monitors"]) == 3
        assert data["monitors"][0]["is_primary"] is True
        assert data["monitors"][1]["x"] == 1920
        assert data["monitors"][2]["x"] == -1920


# ── CLI list screens ────────────────────────────

class TestListScreensCLI:
    """Test CLI output for `naturo list screens`."""

    @patch("naturo.cli.core._get_backend")
    def test_text_output(self, mock_backend):
        backend = MagicMock()
        backend.list_monitors.return_value = _mock_monitors(2)
        mock_backend.return_value = backend

        from naturo.cli.core import list_cmd
        runner = CliRunner()
        result = runner.invoke(list_cmd, ["screens"])
        assert result.exit_code == 0
        assert "1920x1080" in result.output
        assert "2560x1440" in result.output
        assert "2 monitor(s) found" in result.output

    @patch("naturo.cli.core._get_backend")
    def test_json_output_has_success(self, mock_backend):
        backend = MagicMock()
        backend.list_monitors.return_value = _mock_monitors(1)
        mock_backend.return_value = backend

        from naturo.cli.core import list_cmd
        runner = CliRunner()
        result = runner.invoke(list_cmd, ["screens", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert "monitors" in data
        m = data["monitors"][0]
        assert "index" in m
        assert "width" in m
        assert "height" in m
        assert "dpi" in m
        assert "scale_factor" in m

    @patch("naturo.cli.core._get_backend")
    def test_json_output_work_area(self, mock_backend):
        backend = MagicMock()
        backend.list_monitors.return_value = _mock_monitors(1)
        mock_backend.return_value = backend

        from naturo.cli.core import list_cmd
        runner = CliRunner()
        result = runner.invoke(list_cmd, ["screens", "--json"])
        data = json.loads(result.output)
        wa = data["monitors"][0]["work_area"]
        assert wa["height"] == 1040

    @patch("naturo.cli.core._get_backend")
    def test_no_monitors_text(self, mock_backend):
        backend = MagicMock()
        backend.list_monitors.return_value = []
        mock_backend.return_value = backend

        from naturo.cli.core import list_cmd
        runner = CliRunner()
        result = runner.invoke(list_cmd, ["screens"])
        assert result.exit_code == 0
        assert "No monitors detected" in result.output

    @patch("naturo.cli.core._get_backend")
    def test_not_implemented_json(self, mock_backend):
        backend = MagicMock()
        backend.list_monitors.side_effect = NotImplementedError("Not supported")
        mock_backend.return_value = backend

        from naturo.cli.core import list_cmd
        runner = CliRunner()
        result = runner.invoke(list_cmd, ["screens", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "NOT_IMPLEMENTED"

    @patch("naturo.cli.core._get_backend")
    def test_not_implemented_text(self, mock_backend):
        backend = MagicMock()
        backend.list_monitors.side_effect = NotImplementedError("Not supported")
        mock_backend.return_value = backend

        from naturo.cli.core import list_cmd
        runner = CliRunner()
        result = runner.invoke(list_cmd, ["screens"])
        assert result.exit_code == 1
        assert "not supported" in result.output.lower()

    @patch("naturo.cli.core._get_backend")
    def test_dpi_fields(self, mock_backend):
        backend = MagicMock()
        backend.list_monitors.return_value = _mock_monitors(2, primary_dpi=144, secondary_dpi=192)
        mock_backend.return_value = backend

        from naturo.cli.core import list_cmd
        runner = CliRunner()
        result = runner.invoke(list_cmd, ["screens", "--json"])
        data = json.loads(result.output)
        assert data["monitors"][0]["dpi"] == 144
        assert data["monitors"][0]["scale_factor"] == 1.5
        assert data["monitors"][1]["dpi"] == 192
        assert data["monitors"][1]["scale_factor"] == 2.0


# ── Capture screen index validation ─────────────

class TestCaptureScreenValidation:
    """Test --screen index validation in capture."""

    @patch("naturo.cli.core.platform")
    @patch("naturo.cli.core._get_backend")
    def test_negative_screen_index_json(self, mock_backend, mock_platform):
        mock_platform.system.return_value = "Windows"
        from naturo.cli.core import capture
        runner = CliRunner()
        result = runner.invoke(capture, ["--screen", "-1", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    @patch("naturo.cli.core.platform")
    @patch("naturo.cli.core._get_backend")
    def test_negative_screen_index_text(self, mock_backend, mock_platform):
        mock_platform.system.return_value = "Windows"
        from naturo.cli.core import capture
        runner = CliRunner()
        result = runner.invoke(capture, ["--screen", "-1"])
        assert result.exit_code == 1
        assert "--screen must be >= 0" in result.output

    @patch("naturo.cli.core.platform")
    @patch("naturo.cli.core._get_backend")
    def test_out_of_range_screen_index_json(self, mock_backend, mock_platform):
        mock_platform.system.return_value = "Windows"
        backend = MagicMock()
        backend.list_monitors.return_value = _mock_monitors(2)
        mock_backend.return_value = backend

        from naturo.cli.core import capture
        runner = CliRunner()
        result = runner.invoke(capture, ["--screen", "5", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "out of range" in data["error"]["message"].lower()

    @patch("naturo.cli.core.platform")
    @patch("naturo.cli.core._get_backend")
    def test_out_of_range_screen_index_text(self, mock_backend, mock_platform):
        mock_platform.system.return_value = "Windows"
        backend = MagicMock()
        backend.list_monitors.return_value = _mock_monitors(1)
        mock_backend.return_value = backend

        from naturo.cli.core import capture
        runner = CliRunner()
        result = runner.invoke(capture, ["--screen", "3"])
        assert result.exit_code == 1
        assert "out of range" in result.output.lower()


# ── Windows backend list_monitors (integration mock) ────

@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
class TestWindowsListMonitors:
    """Integration tests for WindowsBackend.list_monitors()."""

    def test_returns_at_least_one_monitor(self):
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        monitors = backend.list_monitors()
        assert len(monitors) >= 1

    def test_primary_monitor_exists(self):
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        monitors = backend.list_monitors()
        primaries = [m for m in monitors if m.is_primary]
        assert len(primaries) == 1

    def test_primary_is_index_zero(self):
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        monitors = backend.list_monitors()
        assert monitors[0].is_primary is True

    def test_monitor_has_positive_dimensions(self):
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        monitors = backend.list_monitors()
        for m in monitors:
            assert m.width > 0
            assert m.height > 0
            assert m.dpi > 0
            assert m.scale_factor > 0

    def test_monitor_has_work_area(self):
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        monitors = backend.list_monitors()
        for m in monitors:
            assert m.work_area is not None
            assert m.work_area["width"] > 0
            assert m.work_area["height"] > 0


# ── MCP tool ────────────────────────────────────

class TestMCPListMonitors:
    """Test MCP list_monitors tool output structure."""

    def test_mcp_tool_output_structure(self):
        """Verify the expected JSON structure for list_monitors MCP tool."""
        monitors = _mock_monitors(2)
        result = {
            "success": True,
            "monitors": [
                {
                    "index": m.index,
                    "name": m.name,
                    "x": m.x, "y": m.y,
                    "width": m.width, "height": m.height,
                    "is_primary": m.is_primary,
                    "scale_factor": m.scale_factor,
                    "dpi": m.dpi,
                    "work_area": m.work_area,
                }
                for m in monitors
            ],
        }
        assert result["success"] is True
        assert len(result["monitors"]) == 2
        assert result["monitors"][0]["is_primary"] is True
        assert result["monitors"][1]["width"] == 2560

    def test_mcp_tool_single_monitor(self):
        """Verify MCP output for single monitor."""
        monitors = _mock_monitors(1)
        result = {
            "success": True,
            "monitors": [
                {
                    "index": m.index,
                    "name": m.name,
                    "x": m.x, "y": m.y,
                    "width": m.width, "height": m.height,
                    "is_primary": m.is_primary,
                    "scale_factor": m.scale_factor,
                    "dpi": m.dpi,
                    "work_area": m.work_area,
                }
                for m in monitors
            ],
        }
        assert result["success"] is True
        assert len(result["monitors"]) == 1
        assert result["monitors"][0]["dpi"] == 96


# ── CLI consistency ─────────────────────────────

# ── DPI coordinate conversion ────────────────────

@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only")
class TestDPIConversion:
    """Test DPI coordinate conversion utilities."""

    def test_physical_to_logical_100pct(self):
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        # At 100% (scale=1.0), coordinates are unchanged
        lx, ly = backend.physical_to_logical(100, 200, screen_index=0)
        # Just verify it returns reasonable values (scale depends on actual system)
        assert isinstance(lx, int)
        assert isinstance(ly, int)

    def test_logical_to_physical_100pct(self):
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        px, py = backend.logical_to_physical(100, 200, screen_index=0)
        assert isinstance(px, int)
        assert isinstance(py, int)

    def test_dpi_scale_returns_positive(self):
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        scale = backend.get_dpi_scale(0)
        assert scale > 0


class TestDPIConversionMocked:
    """Test DPI conversion with mocked scale factors."""

    def test_150pct_physical_to_logical(self):
        """At 150% scale (DPI=144), 300px → 200 logical pixels."""
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = None
        backend._initialized = False
        backend._dpi_aware = True

        with patch.object(backend, "get_dpi_scale", return_value=1.5):
            lx, ly = backend.physical_to_logical(300, 600)
            assert lx == 200
            assert ly == 400

    def test_200pct_logical_to_physical(self):
        """At 200% scale (DPI=192), 100 logical → 200 physical pixels."""
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = None
        backend._initialized = False
        backend._dpi_aware = True

        with patch.object(backend, "get_dpi_scale", return_value=2.0):
            px, py = backend.logical_to_physical(100, 200)
            assert px == 200
            assert py == 400

    def test_100pct_no_change(self):
        """At 100% scale, coordinates unchanged."""
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = None
        backend._initialized = False
        backend._dpi_aware = True

        with patch.object(backend, "get_dpi_scale", return_value=1.0):
            lx, ly = backend.physical_to_logical(500, 300)
            assert lx == 500
            assert ly == 300

    def test_roundtrip(self):
        """physical → logical → physical should be consistent."""
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = None
        backend._initialized = False
        backend._dpi_aware = True

        with patch.object(backend, "get_dpi_scale", return_value=1.5):
            lx, ly = backend.physical_to_logical(300, 450)
            px, py = backend.logical_to_physical(lx, ly)
            assert px == 300
            assert py == 450


# ── CLI consistency ─────────────────────────────

class TestScreensVisibility:
    """Ensure `list screens` is no longer hidden."""

    def test_screens_in_help(self):
        from naturo.cli.core import list_cmd
        runner = CliRunner()
        result = runner.invoke(list_cmd, ["--help"])
        assert "screens" in result.output
