"""Tests for naturo.mcp._capture — MCP capture tools.

Tests cover capture_screen, capture_window, list_monitors
with mocked backend. All tests run on Linux CI (no Windows dependencies).
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


def _call_tool(server, tool_name: str, arguments: dict):
    """Helper to call an MCP tool function by name."""
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    return backend


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


class TestCaptureScreen:

    def test_returns_screenshot_info(self, server, mock_backend, tmp_path):
        png_file = tmp_path / "capture.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\nfake")

        capture_result = MagicMock()
        capture_result.path = str(png_file)
        capture_result.width = 1920
        capture_result.height = 1080
        capture_result.format = "png"
        capture_result.scale_factor = 1.0
        capture_result.dpi = 96
        mock_backend.capture_screen.return_value = capture_result

        result = _call_tool(server, "capture_screen", {"output_path": str(png_file)})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["width"] == 1920
        assert data["height"] == 1080
        assert data["format"] == "png"
        assert data["scale_factor"] == 1.0
        assert data["dpi"] == 96
        assert "data_base64" in data

    def test_default_arguments(self, server, mock_backend):
        capture_result = MagicMock()
        capture_result.path = "/nonexistent/capture.png"
        capture_result.width = 1920
        capture_result.height = 1080
        capture_result.format = "png"
        capture_result.scale_factor = 1.0
        capture_result.dpi = 96
        mock_backend.capture_screen.return_value = capture_result

        result = _call_tool(server, "capture_screen", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.capture_screen.assert_called_once_with(
            screen_index=0, output_path="capture.png"
        )

    def test_custom_screen_index(self, server, mock_backend):
        capture_result = MagicMock()
        capture_result.path = "/tmp/test.png"
        capture_result.width = 2560
        capture_result.height = 1440
        capture_result.format = "png"
        capture_result.scale_factor = 1.5
        capture_result.dpi = 144
        mock_backend.capture_screen.return_value = capture_result

        result = _call_tool(server, "capture_screen", {"screen_index": 1})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["scale_factor"] == 1.5
        assert data["dpi"] == 144
        mock_backend.capture_screen.assert_called_once_with(
            screen_index=1, output_path="capture.png"
        )

    def test_no_base64_when_file_missing(self, server, mock_backend):
        capture_result = MagicMock()
        capture_result.path = "/nonexistent/file.png"
        capture_result.width = 1920
        capture_result.height = 1080
        capture_result.format = "png"
        capture_result.scale_factor = 1.0
        capture_result.dpi = 96
        mock_backend.capture_screen.return_value = capture_result

        result = _call_tool(server, "capture_screen", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert "data_base64" not in data


class TestCaptureWindow:

    def test_captures_specific_window(self, server, mock_backend, tmp_path):
        png_file = tmp_path / "win.png"
        png_file.write_bytes(b"\x89PNGdata")

        capture_result = MagicMock()
        capture_result.path = str(png_file)
        capture_result.width = 800
        capture_result.height = 600
        capture_result.format = "png"
        capture_result.scale_factor = 1.0
        capture_result.dpi = 96
        mock_backend._resolve_hwnd.return_value = 999
        mock_backend.capture_window.return_value = capture_result

        result = _call_tool(server, "capture_window", {"window_title": "Notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["width"] == 800
        assert data["height"] == 600
        assert "data_base64" in data
        # window_title is resolved to an hwnd before capture (#954).
        mock_backend.capture_window.assert_called_once_with(
            hwnd=999, output_path="capture.png"
        )

    def test_unmatched_window_title_returns_window_not_found(self, server, mock_backend):
        """An unmatched window_title must fail loudly, not silently capture the
        foreground window (#954 — silent failure / CLI↔MCP contract drift)."""
        from naturo.errors import WindowNotFoundError

        mock_backend._resolve_hwnd.side_effect = WindowNotFoundError("zzz_nonexistent_qa")

        result = _call_tool(server, "capture_window", {"window_title": "zzz_nonexistent_qa"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "WINDOW_NOT_FOUND"
        assert "zzz_nonexistent_qa" in data["error"]["message"]
        # The backend must never be asked to capture when resolution fails.
        mock_backend.capture_window.assert_not_called()

    def test_matched_window_title_captures_resolved_hwnd(self, server, mock_backend, tmp_path):
        """A matched window_title must capture the resolved window by hwnd, not
        pass the raw title (which the Windows backend ignores -> foreground)."""
        png_file = tmp_path / "win.png"
        png_file.write_bytes(b"\x89PNGdata")

        capture_result = MagicMock()
        capture_result.path = str(png_file)
        capture_result.width = 800
        capture_result.height = 600
        capture_result.format = "png"
        capture_result.scale_factor = 1.0
        capture_result.dpi = 96
        mock_backend._resolve_hwnd.return_value = 4242
        mock_backend.capture_window.return_value = capture_result

        result = _call_tool(server, "capture_window", {"window_title": "Notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend._resolve_hwnd.assert_called_once_with(window_title="Notepad")
        mock_backend.capture_window.assert_called_once_with(
            hwnd=4242, output_path="capture.png"
        )

    def test_captures_foreground_window(self, server, mock_backend):
        capture_result = MagicMock()
        capture_result.path = "/nonexistent/capture.png"
        capture_result.width = 1024
        capture_result.height = 768
        capture_result.format = "png"
        capture_result.scale_factor = 2.0
        capture_result.dpi = 192
        mock_backend.capture_window.return_value = capture_result

        result = _call_tool(server, "capture_window", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.capture_window.assert_called_once_with(
            window_title=None, output_path="capture.png"
        )


class TestListMonitors:

    def test_returns_monitor_list(self, server, mock_backend):
        monitor = MagicMock()
        monitor.index = 0
        monitor.name = "\\\\.\\DISPLAY1"
        monitor.x = 0
        monitor.y = 0
        monitor.width = 1920
        monitor.height = 1080
        monitor.is_primary = True
        monitor.scale_factor = 1.0
        monitor.dpi = 96
        monitor.work_area = {"x": 0, "y": 0, "width": 1920, "height": 1040}
        mock_backend.list_monitors.return_value = [monitor]

        result = _call_tool(server, "list_monitors", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert len(data["monitors"]) == 1
        m = data["monitors"][0]
        assert m["index"] == 0
        assert m["is_primary"] is True
        assert m["width"] == 1920
        assert m["dpi"] == 96

    def test_multiple_monitors(self, server, mock_backend):
        monitors = []
        for i in range(3):
            m = MagicMock()
            m.index = i
            m.name = f"\\\\.\\DISPLAY{i + 1}"
            m.x = i * 1920
            m.y = 0
            m.width = 1920
            m.height = 1080
            m.is_primary = (i == 0)
            m.scale_factor = 1.0
            m.dpi = 96
            m.work_area = {"x": i * 1920, "y": 0, "width": 1920, "height": 1040}
            monitors.append(m)
        mock_backend.list_monitors.return_value = monitors

        result = _call_tool(server, "list_monitors", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert len(data["monitors"]) == 3

    def test_empty_monitor_list(self, server, mock_backend):
        mock_backend.list_monitors.return_value = []
        result = _call_tool(server, "list_monitors", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["monitors"] == []
