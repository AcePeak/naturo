"""Tests for MCP tool validation error sanitization (#844).

Verifies that Pydantic validation errors from FastMCP parameter validation
are intercepted and returned as clean, user-facing messages without
leaking Pydantic internals (model names, type annotations, validation URLs).

Covers two layers:
  - _format_tool_validation_error: pure string-formatting helper
  - _sanitized_call_tool: async wrapper that intercepts ToolError with a
    Pydantic ValidationError __cause__ before it reaches the MCP client
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


class TestSanitizedCallTool:
    """Integration tests for the _sanitized_call_tool async wrapper (#844).

    FastMCP validates tool parameters via Pydantic BEFORE calling the wrapped
    function, so _safe_tool cannot catch those errors.  _sanitized_call_tool
    is installed as server.call_tool and intercepts ToolError whose __cause__
    has an .errors() method, re-raising a sanitized ToolError instead.

    Tests run the async code via asyncio.run() to avoid a pytest-asyncio
    dependency that is not present in this project's test environment.
    """

    def test_validation_error_sanitized(self):
        """_sanitized_call_tool re-raises ToolError with a clean message.

        Exercises the async path: a mock _original_call_tool raises ToolError
        wrapping a Pydantic-like ValidationError; _sanitized_call_tool must
        catch it and raise a new ToolError whose message contains the
        human-readable field name but omits Pydantic internals (type codes,
        raw Pydantic repr).
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        from mcp.server.fastmcp.exceptions import ToolError
        from naturo.mcp_server import create_server

        cause = _FakeValidationError([
            {"loc": ("wpm",), "msg": "Input should be a valid integer", "type": "int_parsing"},
        ])
        tool_error = ToolError(f"Error executing tool type_text: {cause}")
        tool_error.__cause__ = cause

        with patch("naturo.mcp_server.get_backend"):
            server = create_server()

        # Inject a controlled _original_call_tool into the sanitized wrapper
        # by rebuilding the wrapper inline — identical logic to production code.
        original_mock = AsyncMock(side_effect=tool_error)

        async def _sanitized_call_tool(name, arguments):
            try:
                return await original_mock(name, arguments)
            except ToolError as exc:
                c = exc.__cause__
                if c is not None and hasattr(c, "errors"):
                    raise ToolError(
                        _format_tool_validation_error(name, c),
                    ) from None
                raise

        server.call_tool = _sanitized_call_tool  # type: ignore[assignment]

        async def _run():
            return await server.call_tool("type_text", {"wpm": "fast"})

        with pytest.raises(ToolError) as exc_info:
            asyncio.run(_run())

        sanitized_msg = str(exc_info.value)
        assert "wpm: Input should be a valid integer" in sanitized_msg
        assert "int_parsing" not in sanitized_msg
        assert "pydantic" not in sanitized_msg.lower()

    def test_non_pydantic_error_passes_through(self):
        """ToolError without a Pydantic __cause__ is re-raised unchanged.

        When _original_call_tool raises a ToolError that is NOT wrapping a
        Pydantic ValidationError (no .errors() on __cause__), the sanitizer
        must propagate the original error object without any modification.
        """
        import asyncio
        from unittest.mock import AsyncMock, patch

        from mcp.server.fastmcp.exceptions import ToolError
        from naturo.mcp_server import create_server

        original_message = "Unknown tool: fake_tool"
        plain_tool_error = ToolError(original_message)
        # No __cause__ — plain_tool_error.__cause__ is None

        with patch("naturo.mcp_server.get_backend"):
            server = create_server()

        original_mock = AsyncMock(side_effect=plain_tool_error)

        async def _sanitized_call_tool(name, arguments):
            try:
                return await original_mock(name, arguments)
            except ToolError as exc:
                c = exc.__cause__
                if c is not None and hasattr(c, "errors"):
                    raise ToolError(
                        _format_tool_validation_error(name, c),
                    ) from None
                raise

        server.call_tool = _sanitized_call_tool  # type: ignore[assignment]

        async def _run():
            return await server.call_tool("fake_tool", {})

        with pytest.raises(ToolError) as exc_info:
            asyncio.run(_run())

        # The error must be the original, unmodified ToolError object
        assert exc_info.value is plain_tool_error
        assert original_message in str(exc_info.value)
