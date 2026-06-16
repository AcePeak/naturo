"""Tests for the MCP error-envelope mapping (#881).

The MCP surface calls the same native ``naturo_core`` library as the CLI, but
historically wrapped every non-``NaturoError`` failure into
``{"code": "INTERNAL_ERROR", "message": "<ClassName>: <text>"}``.  That leaked
the internal exception class name (``NaturoCoreError``, ``TypeError``, …) and,
for keyboard/mouse failures, a ``repr()`` of the failing call's arguments
(e.g. ``key_press('F1')``), and it collapsed every native error code into the
single ``INTERNAL_ERROR`` bucket.

These tests lock the contract:

1. Bridge ``NaturoCoreError`` native codes map to the typed :class:`ErrorCode`
   catalog where a specific peer exists.
2. ``error.message`` never contains a Python/C++ exception class name.
3. ``error.message`` never contains a ``repr()`` of the failing call's
   arguments.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from naturo.bridge import NaturoCoreError
from naturo.errors import ErrorCode

# Skip the whole module when the optional ``mcp`` dependency is absent: it is
# not installed on the non-Windows CI runners, where importing ``mcp_server``
# raises ImportError at collection time.  Mirrors the other MCP test modules.
mcp_available = True
try:
    from naturo.mcp_server import _core_error_envelope, create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


def _call_tool(srv, name, args):
    """Invoke an MCP tool through the server's async dispatch and return blocks."""
    async def _run():
        return await srv.call_tool(name, args)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


class TestCoreErrorEnvelope:
    """Unit tests for the pure ``NaturoCoreError`` → envelope mapping."""

    def test_invalid_argument_maps_to_invalid_input(self):
        """Native code -1 (invalid argument) becomes the typed INVALID_INPUT."""
        env = _core_error_envelope(NaturoCoreError(-1, "capture_window"))
        assert env == {
            "success": False,
            "error": {"code": ErrorCode.INVALID_INPUT, "message": "Invalid argument"},
        }

    def test_system_com_error_maps_to_internal_error(self):
        """Native code -2 has no specific typed peer; it stays INTERNAL_ERROR."""
        env = _core_error_envelope(NaturoCoreError(-2, "capture_window"))
        assert env["error"]["code"] == "INTERNAL_ERROR"
        assert env["error"]["message"] == "System/COM error"

    def test_file_io_error_maps_to_typed_code(self):
        """Native code -3 (file I/O) becomes the typed FILE_IO_ERROR."""
        env = _core_error_envelope(NaturoCoreError(-3, "save_capture"))
        assert env["error"]["code"] == ErrorCode.FILE_IO_ERROR
        assert env["error"]["message"] == "File I/O error"

    def test_unknown_native_code_falls_back_cleanly(self):
        """An unmapped native code degrades to INTERNAL_ERROR without leaking."""
        env = _core_error_envelope(NaturoCoreError(-99, "weird_op"))
        assert env["error"]["code"] == "INTERNAL_ERROR"
        assert "NaturoCoreError" not in env["error"]["message"]
        assert "weird_op" not in env["error"]["message"]

    def test_message_never_leaks_class_name_or_arg_repr(self):
        """The context may embed a repr of arguments; the message must not."""
        env = _core_error_envelope(NaturoCoreError(-2, "key_press('F1')"))
        message = env["error"]["message"]
        assert "NaturoCoreError" not in message
        assert "key_press" not in message
        assert "F1" not in message


class TestSafeToolMapping:
    """End-to-end mapping through a real tool's ``_safe_tool`` wrapper."""

    def test_core_error_through_tool_is_typed_and_clean(self):
        """A NaturoCoreError raised inside a tool surfaces a typed, clean code."""
        mock_backend = MagicMock()
        mock_backend.capture_screen.side_effect = NaturoCoreError(-1, "capture_screen")
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = _call_tool(srv, "capture_screen", {})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == ErrorCode.INVALID_INPUT
            assert "NaturoCoreError" not in data["error"]["message"]

    def test_press_key_core_error_hides_arg_repr(self):
        """press_key failures must not echo the key argument or class name."""
        mock_backend = MagicMock()
        mock_backend.press_key.side_effect = NaturoCoreError(-2, "key_press('F1')")
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = _call_tool(srv, "press_key", {"key": "F1"})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INTERNAL_ERROR"
            message = data["error"]["message"]
            assert "NaturoCoreError" not in message
            assert "key_press" not in message
            assert "F1" not in message

    def test_generic_exception_drops_class_name_prefix(self):
        """A non-validation exception keeps its text but loses the class prefix."""
        mock_backend = MagicMock()
        mock_backend.capture_screen.side_effect = TypeError(
            "list_snapshots() got an unexpected keyword argument 'limit'"
        )
        with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
            srv = create_server()
            result = _call_tool(srv, "capture_screen", {})
            data = json.loads(result[0].text)
            assert data["success"] is False
            assert data["error"]["code"] == "INTERNAL_ERROR"
            assert "TypeError" not in data["error"]["message"]
