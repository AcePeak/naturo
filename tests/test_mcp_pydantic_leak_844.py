"""Tests for MCP tool validation error formatting (#844).

Verifies that Pydantic ValidationError internals (field paths, validator
names, raw repr) are not leaked to MCP clients.  Instead, errors should
use code=INVALID_INPUT with a clean, user-friendly message.
"""
from __future__ import annotations

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
    """Synchronously call an MCP tool and return the result."""
    import asyncio

    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


class TestPydanticLeakPrevention:
    """Pydantic ValidationError should produce INVALID_INPUT, not INTERNAL_ERROR."""

    def test_safe_tool_catches_validation_error(self):
        """_safe_tool wraps Pydantic ValidationError with user-friendly message."""
        from naturo.mcp_server import create_server as _cs

        # Create a fake Pydantic-like ValidationError
        class FakeValidationError(Exception):
            def errors(self):
                return [
                    {"loc": ("wpm",), "msg": "Input should be a valid integer", "type": "int_parsing"},
                ]

        FakeValidationError.__name__ = "ValidationError"

        mock_backend = MagicMock()

        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = _cs()

        # Get _safe_tool from the server's closure — access via a registered tool
        # Instead, test end-to-end: register a tool that raises the fake error
        # and verify it returns INVALID_INPUT
        from naturo.mcp_server import create_server

        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()

            # Patch an existing tool to raise a ValidationError
            # Use type_text since it's commonly used
            mock_backend.type_text = MagicMock(side_effect=FakeValidationError("1 validation error"))

            # Use a valid input that would pass parameter checks but fail inside
            # We need the tool to call backend.type_text, so use valid params
            result = _call_tool(srv, "type_text", {"text": "hello"})

        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "wpm" in data["error"]["message"]
        assert "Input should be a valid integer" in data["error"]["message"]
        # Must NOT contain Pydantic internal details
        assert "int_parsing" not in data["error"]["message"]
        assert "type=" not in data["error"]["message"]

    def test_safe_tool_handles_broken_validation_error(self):
        """If errors() method fails, still returns clean message."""

        class BrokenValidationError(Exception):
            def errors(self):
                raise RuntimeError("broken")

        BrokenValidationError.__name__ = "ValidationError"

        mock_backend = MagicMock()

        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            from naturo.mcp_server import create_server
            srv = create_server()

            mock_backend.type_text = MagicMock(
                side_effect=BrokenValidationError("broken error"),
            )

            result = _call_tool(srv, "type_text", {"text": "hello"})

        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "failed validation" in data["error"]["message"]
        # Must NOT contain raw traceback or Pydantic internals
        assert "Traceback" not in data["error"]["message"]

    def test_non_validation_error_still_internal(self):
        """Non-validation exceptions still get INTERNAL_ERROR code."""
        mock_backend = MagicMock()

        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            from naturo.mcp_server import create_server
            srv = create_server()

            mock_backend.type_text = MagicMock(
                side_effect=RuntimeError("something broke"),
            )

            result = _call_tool(srv, "type_text", {"text": "hello"})

        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "INTERNAL_ERROR"


class TestExistingValidationErrorsClean:
    """Existing parameter validation errors should use INVALID_INPUT code."""

    @pytest.mark.parametrize("tool_name,args", [
        ("type_text", {"text": "x", "wpm": 0}),
        ("press_key", {"key": "a", "count": 0}),
        ("scroll", {"amount": 0}),
    ])
    def test_validation_errors_are_not_internal(self, tool_name, args):
        """App-level validation errors use specific error codes, not INTERNAL_ERROR."""
        mock_backend = MagicMock()

        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = _call_tool(srv, tool_name, args)

        data = json.loads(result[0].text)
        assert data["success"] is False
        assert "error" in data
        # These use NaturoError with specific codes — they should NOT be INTERNAL_ERROR
        assert data["error"]["code"] != "INTERNAL_ERROR"
