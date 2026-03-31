"""Tests for naturo.mcp._clipboard — MCP clipboard tools.

Tests cover clipboard_get, clipboard_set, clipboard_clear, clipboard_info
with mocked backend. All tests run on Linux CI (no Windows dependencies).
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
    backend = MagicMock()
    backend.clipboard_get.return_value = "hello world"
    backend.clipboard_info.return_value = {
        "format": "text",
        "size": 11,
        "has_text": True,
        "has_image": False,
        "has_files": False,
    }
    return backend


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


class TestClipboardGet:

    def test_returns_text_and_length(self, server, mock_backend):
        result = _call_tool(server, "clipboard_get", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["text"] == "hello world"
        assert data["length"] == 11
        mock_backend.clipboard_get.assert_called_once()

    def test_empty_clipboard(self, server, mock_backend):
        mock_backend.clipboard_get.return_value = ""
        result = _call_tool(server, "clipboard_get", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["text"] == ""
        assert data["length"] == 0


class TestClipboardSet:

    def test_sets_text_and_returns_length(self, server, mock_backend):
        result = _call_tool(server, "clipboard_set", {"text": "new content"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["length"] == 11
        mock_backend.clipboard_set.assert_called_once_with("new content")

    def test_sets_empty_string(self, server, mock_backend):
        result = _call_tool(server, "clipboard_set", {"text": ""})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["length"] == 0
        mock_backend.clipboard_set.assert_called_once_with("")

    def test_sets_unicode_text(self, server, mock_backend):
        text = "日本語テスト 🎉"
        result = _call_tool(server, "clipboard_set", {"text": text})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["length"] == len(text)
        mock_backend.clipboard_set.assert_called_once_with(text)


class TestClipboardClear:

    def test_clears_clipboard(self, server, mock_backend):
        result = _call_tool(server, "clipboard_clear", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_backend.clipboard_clear.assert_called_once()


class TestClipboardInfo:

    def test_returns_info(self, server, mock_backend):
        result = _call_tool(server, "clipboard_info", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["format"] == "text"
        assert data["size"] == 11
        assert data["has_text"] is True
        assert data["has_image"] is False
        assert data["has_files"] is False

    def test_empty_clipboard_info(self, server, mock_backend):
        mock_backend.clipboard_info.return_value = {
            "format": "empty",
            "size": 0,
            "has_text": False,
            "has_image": False,
            "has_files": False,
        }
        result = _call_tool(server, "clipboard_info", {})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["format"] == "empty"
        assert data["has_text"] is False
