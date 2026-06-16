"""Tests for MCP tool validation error sanitization (#844).

Verifies that Pydantic validation errors from FastMCP parameter validation
are intercepted and returned as clean, user-facing messages without
leaking Pydantic internals (model names, type annotations, validation URLs).

Covers two layers:
  - _format_tool_validation_error: pure string-formatting helper
  - The sanitizing FastMCP subclass, exercised through the *real* low-level
    JSON-RPC dispatch path (``request_handlers[CallToolRequest]``) — the same
    path a live MCP client hits.  An earlier fix (#853) only reassigned
    ``server.call_tool`` after construction, which never reached this handler,
    so the leak persisted in production while a direct-call unit test passed.
"""
from __future__ import annotations

import pytest

mcp_available = True
try:
    from naturo.mcp_server import _format_tool_validation_error
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


class _FakeValidationError(Exception):
    """Simulates a Pydantic ValidationError with .errors() method."""

    def __init__(self, errors_list: list[dict]):
        self._errors = errors_list
        super().__init__(f"{len(errors_list)} validation errors")

    def errors(self) -> list[dict]:
        return self._errors


class TestFormatValidationError:
    """Unit tests for _format_tool_validation_error helper."""

    def test_single_field_error(self):
        cause = _FakeValidationError([
            {"loc": ("wpm",), "msg": "Input should be a valid integer", "type": "int_parsing"},
        ])
        result = _format_tool_validation_error("type_text", cause)
        assert result == "Invalid parameters for type_text: wpm: Input should be a valid integer"
        assert "int_parsing" not in result
        assert "pydantic" not in result.lower()

    def test_multiple_field_errors(self):
        cause = _FakeValidationError([
            {"loc": ("x",), "msg": "Input should be a valid integer", "type": "int_parsing"},
            {"loc": ("button",), "msg": "Input should be 'left', 'right' or 'middle'", "type": "enum"},
        ])
        result = _format_tool_validation_error("click", cause)
        assert "x: Input should be a valid integer" in result
        assert "button: Input should be 'left', 'right' or 'middle'" in result
        assert result.startswith("Invalid parameters for click:")

    def test_nested_field_loc(self):
        cause = _FakeValidationError([
            {"loc": ("config", "timeout"), "msg": "value must be positive", "type": "value_error"},
        ])
        result = _format_tool_validation_error("wait_for", cause)
        assert "config.timeout: value must be positive" in result

    def test_root_error_no_field(self):
        cause = _FakeValidationError([
            {"loc": (), "msg": "Extra inputs are not permitted", "type": "extra_forbidden"},
        ])
        result = _format_tool_validation_error("click", cause)
        assert result == "Invalid parameters for click: Extra inputs are not permitted"

    def test_dunder_root_stripped(self):
        cause = _FakeValidationError([
            {"loc": ("__root__",), "msg": "invalid value", "type": "value_error"},
        ])
        result = _format_tool_validation_error("type_text", cause)
        assert "__root__" not in result
        assert "invalid value" in result

    def test_fallback_on_errors_method_failure(self):
        """If cause.errors() raises, still return a clean message."""
        class BrokenCause(Exception):
            def errors(self):
                raise RuntimeError("broken")

        result = _format_tool_validation_error("click", BrokenCause())
        assert result == "Invalid parameters for click"
        assert "pydantic" not in result.lower()

    def test_no_leak_of_type_field(self):
        """The 'type' field from Pydantic errors should not appear in output."""
        cause = _FakeValidationError([
            {"loc": ("x",), "msg": "value is not valid", "type": "value_error.number.not_gt"},
        ])
        result = _format_tool_validation_error("click", cause)
        assert "value_error.number.not_gt" not in result


class TestRealDispatchSanitization:
    """End-to-end tests through the real low-level JSON-RPC dispatch path (#844).

    FastMCP registers ``self.call_tool`` as the ``CallToolRequest`` handler
    during ``__init__``; the low-level server renders ``str(exc)`` of whatever
    that handler raises into the client-facing error text.  These tests invoke
    that registered handler directly — exactly what a live MCP client triggers —
    so they catch wiring regressions (e.g. #853, where the sanitizer was only
    bound to the unused ``server.call_tool`` attribute and never to the handler).

    Tests run the async code via ``asyncio.run()`` to avoid a pytest-asyncio
    dependency that is not present in this project's test environment.
    """

    @staticmethod
    def _dispatch(tool_name: str, arguments: dict):
        """Drive a tools/call request through the registered handler.

        Returns the resulting ``CallToolResult`` (``ServerResult.root``).
        """
        import asyncio
        from unittest.mock import patch

        from mcp.types import CallToolRequest, CallToolRequestParams
        from naturo.mcp_server import create_server

        with patch("naturo.mcp_server.get_backend"):
            server = create_server()

        handler = server._mcp_server.request_handlers[CallToolRequest]
        request = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name=tool_name, arguments=arguments),
        )
        result = asyncio.run(handler(request))
        return result.root

    def test_wrong_param_name_sanitized(self):
        """The exact scenario from #844: wrong param name → clean error text.

        Sending ``launch_app`` with ``app_name`` (instead of the required
        ``name``) must yield a user-facing message that names the missing
        field but leaks none of Pydantic's internals.
        """
        result = self._dispatch("launch_app", {"app_name": "notepad"})

        assert result.isError is True
        text = result.content[0].text

        # Clean, actionable message naming the offending tool and field.
        assert "Invalid parameters for launch_app" in text
        assert "name" in text

        # None of the Pydantic leakage from the original bug report.
        assert "validation error for" not in text
        assert "launch_appArguments" not in text
        assert "pydantic" not in text.lower()
        assert "input_value" not in text
        assert "[type=missing" not in text

    def test_genuine_tool_error_passes_through(self):
        """A non-Pydantic tool failure keeps its original message.

        Calling an unknown tool produces a ``ToolError`` with no Pydantic
        ``__cause__``; the sanitizer must leave it untouched so real failures
        stay diagnosable.
        """
        result = self._dispatch("definitely_not_a_real_tool", {})

        assert result.isError is True
        text = result.content[0].text
        assert "definitely_not_a_real_tool" in text
        # Not rewritten into the validation-error template.
        assert "Invalid parameters for" not in text
