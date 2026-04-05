"""Tests for MCP stdio transport logging suppression (#810).

Verifies that when MCP server runs in stdio mode, no debug/info/warning
output is emitted to stdout or stderr, as that would corrupt the JSON-RPC
protocol.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from naturo.mcp_server import run_server, create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


class TestStdioLoggingSuppression:
    """Logging must be fully suppressed during stdio transport."""

    def test_run_server_stdio_suppresses_stdout_handlers(self):
        """run_server(transport='stdio') should redirect/remove stdout handlers."""
        import sys
        original_handlers = logging.root.handlers.copy()
        original_level = logging.root.level

        # Add a stdout handler to verify it gets redirected
        stdout_handler = logging.StreamHandler(sys.stdout)
        logging.root.addHandler(stdout_handler)

        with patch("naturo.mcp_server.create_server") as mock_cs:
            mock_server = MagicMock()
            mock_cs.return_value = mock_server
            run_server(transport="stdio")

        # Stdout handler should have been redirected to stderr
        assert stdout_handler.stream is sys.stderr

        # Restore
        logging.root.handlers = original_handlers
        logging.root.setLevel(original_level)

    def test_run_server_sse_does_not_suppress_logging(self):
        """run_server(transport='sse') should NOT suppress logging."""
        original_level = logging.root.level
        original_handlers = logging.root.handlers.copy()

        with patch("naturo.mcp_server.create_server") as mock_cs:
            mock_server = MagicMock()
            mock_cs.return_value = mock_server
            run_server(transport="sse")

        # Root logger level should NOT have been changed
        assert logging.root.level == original_level

        # Restore
        logging.root.handlers = original_handlers

    def test_cli_stdio_sets_root_critical(self):
        """naturo mcp start (stdio) should set root logger to CRITICAL."""
        from click.testing import CliRunner
        from naturo.cli.ai import start

        original_level = logging.root.level

        with patch("naturo.mcp_server.run_server") as mock_run:
            runner = CliRunner()
            result = runner.invoke(start, ["--transport", "stdio"])

        # Root logger should be CRITICAL
        assert logging.root.level >= logging.CRITICAL

        # Restore
        logging.root.setLevel(original_level)


class TestLoggerOutputCapture:
    """Verify no actual output leaks during stdio mode."""

    def test_no_stdout_leak_from_logger(self, capsys):
        """Logger.warning() should not appear on stdout after stdio suppression."""
        import sys
        original_level = logging.root.level
        original_handlers = logging.root.handlers.copy()

        # Add a stdout handler (simulates what a library might do)
        stdout_handler = logging.StreamHandler(sys.stdout)
        logging.root.addHandler(stdout_handler)

        with patch("naturo.mcp_server.create_server") as mock_cs:
            mock_server = MagicMock()
            mock_cs.return_value = mock_server
            run_server(transport="stdio")

        # Now emit a warning — should NOT appear on stdout
        logging.getLogger("naturo").warning("This should not appear on stdout")

        captured = capsys.readouterr()
        assert "should not appear on stdout" not in captured.out

        # Restore
        logging.root.handlers = original_handlers
        logging.root.setLevel(original_level)
