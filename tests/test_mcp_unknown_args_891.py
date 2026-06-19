"""Tests for MCP rejection of unknown tool arguments (#891).

FastMCP generates each tool's argument model from the function signature with
Pydantic's default config, which *silently discards* arguments not declared in
the schema.  A client that mistypes a parameter name (e.g. ``window_title``
instead of ``title`` for ``focus_window``) — or one targeting a schema that
drifted between naturo versions — then gets a call that runs with default
behaviour instead of a validation error.  That is a silent failure: the wrong
window is focused, the wrong text is typed, and the agent has no signal.

These tests pin the fix: unknown arguments are rejected before dispatch with a
clean ``Invalid parameters for <tool>`` message (``isError: true``), consistent
with the existing Pydantic wrong-type/missing-field path (#844).  They run
through the *real* low-level JSON-RPC dispatch path a live MCP client hits, plus
unit-level coverage of the allow-list and the message formatter.  All are
desktop-independent: the rejection happens before any backend call.
"""
from __future__ import annotations

import pytest

mcp_available = True
try:
    from naturo.mcp_server import _format_unknown_arguments_error
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


def _dispatch(tool_name: str, arguments: dict):
    """Drive a tools/call request through the registered handler.

    Returns the resulting ``CallToolResult`` (``ServerResult.root``).  Mirrors
    the dispatch helper in ``test_mcp_pydantic_leak.py`` so the test exercises
    the same path a real client triggers.
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


class TestFormatUnknownArgumentsError:
    """Unit tests for the _format_unknown_arguments_error helper."""

    def test_single_unknown_argument(self):
        msg = _format_unknown_arguments_error(
            "focus_window", ["window_title"], ["app", "hwnd", "title"],
        )
        assert msg == (
            "Invalid parameters for focus_window: unexpected argument "
            "'window_title'. Valid arguments: app, hwnd, title."
        )
        assert "pydantic" not in msg.lower()

    def test_multiple_unknown_arguments_pluralised_and_sorted(self):
        msg = _format_unknown_arguments_error(
            "click", ["zeta", "alpha"], ["x", "y"],
        )
        assert "unexpected arguments 'alpha', 'zeta'" in msg
        assert msg.startswith("Invalid parameters for click:")

    def test_no_valid_arguments_renders_none(self):
        msg = _format_unknown_arguments_error("list_monitors", ["foo"], [])
        assert "Valid arguments: (none)." in msg


class TestAllowedArgumentNames:
    """Unit tests for the per-tool allow-list lookup."""

    @staticmethod
    def _server():
        from unittest.mock import patch
        from naturo.mcp_server import create_server

        with patch("naturo.mcp_server.get_backend"):
            return create_server()

    def test_known_tool_allows_declared_params_only(self):
        allowed = self._server()._allowed_argument_names("focus_window")
        assert allowed is not None
        assert {"title", "app", "hwnd"} <= allowed
        assert "window_title" not in allowed

    def test_unknown_tool_returns_none(self):
        # None signals "no enforceable allow-list" so dispatch surfaces the
        # canonical "Unknown tool" error instead of an unknown-argument one.
        assert self._server()._allowed_argument_names("not_a_real_tool") is None


class TestDispatchRejection:
    """End-to-end rejection through the real JSON-RPC dispatch path."""

    def test_mistyped_param_name_rejected(self):
        """The #891 repro: focus_window with ``window_title`` must fail loudly.

        Previously this silently dropped ``window_title``, fell back to the
        foreground window, and leaked the ``foreground`` sentinel in a
        downstream WINDOW_NOT_FOUND message.
        """
        result = _dispatch("focus_window", {"window_title": "claude"})

        assert result.isError is True
        text = result.content[0].text
        assert "Invalid parameters for focus_window" in text
        assert "window_title" in text
        # No silent success and no Pydantic leakage.
        assert '"success": true' not in text.lower()
        assert "pydantic" not in text.lower()

    def test_extra_arg_alongside_valid_rejected(self):
        """An unknown arg next to a valid one must not pass as success (#891)."""
        result = _dispatch(
            "focus_window", {"title": "claude", "bogus_extra_param": "foo"},
        )

        assert result.isError is True
        text = result.content[0].text
        assert "bogus_extra_param" in text
        assert "Invalid parameters for focus_window" in text

    def test_unknown_tool_still_reports_unknown_tool(self):
        """A genuinely unknown tool keeps its canonical error, not ours."""
        result = _dispatch("definitely_not_a_real_tool", {"title": "x"})

        assert result.isError is True
        text = result.content[0].text
        assert "definitely_not_a_real_tool" in text
        assert "unexpected argument" not in text
