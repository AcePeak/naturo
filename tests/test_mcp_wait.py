"""Tests for naturo.mcp._wait — MCP wait tools.

Tests cover wait_for_element, wait_for_window, wait_until_gone
with mocked wait module. All tests run on Linux CI (no Windows dependencies).
"""
from __future__ import annotations

import asyncio
import json
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
    return MagicMock()


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


def _make_element(id="e1", role="Button", name="Save", x=100, y=200, width=80, height=30):
    el = MagicMock()
    el.id = id
    el.role = role
    el.name = name
    el.x = x
    el.y = y
    el.width = width
    el.height = height
    return el


def _make_wait_result(found=True, element=None, wait_time=0.5):
    result = MagicMock()
    result.found = found
    result.element = element
    result.wait_time = wait_time
    return result


class TestWaitForElement:

    def test_element_found(self, server, mock_backend):
        el = _make_element()
        wait_result = _make_wait_result(found=True, element=el, wait_time=0.234)

        with patch("naturo.wait.wait_for_element", return_value=wait_result):
            result = _call_tool(server, "wait_for_element", {"selector": "Button:Save"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["found"] is True
        assert data["wait_time"] == 0.234
        assert data["element"]["id"] == "e1"
        assert data["element"]["role"] == "Button"
        assert data["element"]["name"] == "Save"
        assert data["element"]["bounds"]["x"] == 100

    def test_element_not_found_timeout(self, server, mock_backend):
        wait_result = _make_wait_result(found=False, element=None, wait_time=10.0)

        with patch("naturo.wait.wait_for_element", return_value=wait_result):
            result = _call_tool(server, "wait_for_element", {
                "selector": "Button:Missing", "timeout": 10.0,
            })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["found"] is False
        assert data["error"]["code"] == "TIMEOUT"

    def test_negative_timeout_rejected(self, server, mock_backend):
        result = _call_tool(server, "wait_for_element", {
            "selector": "Button:X", "timeout": -1,
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_zero_interval_rejected(self, server, mock_backend):
        result = _call_tool(server, "wait_for_element", {
            "selector": "Button:X", "interval": 0,
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_custom_window_title(self, server, mock_backend):
        el = _make_element(id="e5", role="Edit", name="Search")
        wait_result = _make_wait_result(found=True, element=el, wait_time=1.0)

        with patch("naturo.wait.wait_for_element", return_value=wait_result) as mock_wait:
            result = _call_tool(server, "wait_for_element", {
                "selector": "Edit:Search",
                "window_title": "Notepad",
                "timeout": 5.0,
                "interval": 0.2,
            })
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_wait.assert_called_once_with(
            selector="Edit:Search",
            timeout=5.0,
            poll_interval=0.2,
            window_title="Notepad",
            backend=mock_backend,
        )

    def test_wait_time_rounded(self, server, mock_backend):
        el = _make_element()
        wait_result = _make_wait_result(found=True, element=el, wait_time=1.23456789)

        with patch("naturo.wait.wait_for_element", return_value=wait_result):
            result = _call_tool(server, "wait_for_element", {"selector": "Button:X"})
        data = json.loads(result[0].text)
        assert data["wait_time"] == 1.235


class TestWaitForWindow:

    def test_window_found(self, server, mock_backend):
        wait_result = _make_wait_result(found=True, wait_time=0.5)

        with patch("naturo.wait.wait_for_window", return_value=wait_result):
            result = _call_tool(server, "wait_for_window", {"title": "Notepad"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["found"] is True
        assert data["wait_time"] == 0.5

    def test_window_not_found_timeout(self, server, mock_backend):
        wait_result = _make_wait_result(found=False, wait_time=10.0)

        with patch("naturo.wait.wait_for_window", return_value=wait_result):
            result = _call_tool(server, "wait_for_window", {
                "title": "Missing App", "timeout": 10.0,
            })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["found"] is False
        assert data["error"]["code"] == "TIMEOUT"
        assert "Missing App" in data["error"]["message"]

    def test_negative_timeout_rejected(self, server, mock_backend):
        result = _call_tool(server, "wait_for_window", {
            "title": "X", "timeout": -5,
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_zero_interval_rejected(self, server, mock_backend):
        result = _call_tool(server, "wait_for_window", {
            "title": "X", "interval": 0,
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_negative_interval_rejected(self, server, mock_backend):
        result = _call_tool(server, "wait_for_window", {
            "title": "X", "interval": -0.1,
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


class TestWaitUntilGone:

    def test_element_disappeared(self, server, mock_backend):
        wait_result = _make_wait_result(found=True, wait_time=2.0)

        with patch("naturo.wait.wait_until_gone", return_value=wait_result):
            result = _call_tool(server, "wait_until_gone", {"selector": "Dialog:*"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["gone"] is True
        assert data["wait_time"] == 2.0

    def test_element_still_present(self, server, mock_backend):
        wait_result = _make_wait_result(found=False, wait_time=10.0)

        with patch("naturo.wait.wait_until_gone", return_value=wait_result):
            result = _call_tool(server, "wait_until_gone", {
                "selector": "ProgressBar:*", "timeout": 10.0,
            })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["gone"] is False
        assert data["error"]["code"] == "TIMEOUT"

    def test_negative_timeout_rejected(self, server, mock_backend):
        result = _call_tool(server, "wait_until_gone", {
            "selector": "X:Y", "timeout": -1,
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_zero_interval_rejected(self, server, mock_backend):
        result = _call_tool(server, "wait_until_gone", {
            "selector": "X:Y", "interval": 0,
        })
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_with_window_title(self, server, mock_backend):
        wait_result = _make_wait_result(found=True, wait_time=0.8)

        with patch("naturo.wait.wait_until_gone", return_value=wait_result) as mock_wait:
            result = _call_tool(server, "wait_until_gone", {
                "selector": "Dialog:Save",
                "window_title": "MyApp",
                "timeout": 5.0,
                "interval": 0.3,
            })
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_wait.assert_called_once_with(
            selector="Dialog:Save",
            timeout=5.0,
            poll_interval=0.3,
            window_title="MyApp",
            backend=mock_backend,
        )
