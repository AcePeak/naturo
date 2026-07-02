"""Tests for MCP stdio transport logging suppression (#810).

Verifies that when MCP server runs in stdio mode, no debug/info/warning
output is emitted to stdout or stderr, as that would corrupt the JSON-RPC
protocol.

Gap addressed in this revision: the logging-only fix did not protect against
``print()`` calls or libraries that write directly to ``sys.stdout``.  The
``_StdoutGuard`` class redirects all text-layer stdout writes to stderr while
keeping ``sys.stdout.buffer`` pointing at the real stdout so that the MCP
``stdio_server()`` transport can still perform its JSON-RPC binary I/O on the
correct file descriptor.
"""
from __future__ import annotations

import io
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from naturo.mcp_server import run_server, create_server, _StdoutGuard
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


class TestStdoutGuard:
    """Unit tests for the _StdoutGuard stdout proxy."""

    def test_guard_write_goes_to_stderr(self):
        """Text written to _StdoutGuard should land on stderr, not stdout."""
        real_stdout = sys.stdout
        stderr_capture = io.StringIO()

        guard = _StdoutGuard(real_stdout)
        # Redirect stderr to a capture buffer so we can inspect it.
        original_stderr = sys.stderr
        sys.stderr = stderr_capture
        try:
            guard.write("hello from guard\n")
        finally:
            sys.stderr = original_stderr

        assert "hello from guard" in stderr_capture.getvalue()

    def test_guard_exposes_real_buffer(self):
        """_StdoutGuard.buffer must be the original sys.stdout.buffer."""
        guard = _StdoutGuard(sys.stdout)
        assert guard.buffer is sys.stdout.buffer

    def test_guard_restores_stdout_after_run_server(self):
        """sys.stdout must be restored to the real object after run_server returns."""
        original_stdout = sys.stdout

        with patch("naturo.mcp_server.create_server") as mock_cs:
            mock_server = MagicMock()
            mock_cs.return_value = mock_server
            run_server(transport="stdio")

        assert sys.stdout is original_stdout

    def test_guard_restores_stdout_on_exception(self):
        """sys.stdout must be restored even if server.run() raises."""
        original_stdout = sys.stdout

        with patch("naturo.mcp_server.create_server") as mock_cs:
            mock_server = MagicMock()
            mock_server.run.side_effect = RuntimeError("boom")
            mock_cs.return_value = mock_server
            with pytest.raises(RuntimeError, match="boom"):
                run_server(transport="stdio")

        assert sys.stdout is original_stdout

    def test_print_during_stdio_does_not_appear_on_real_stdout(self, capsys):
        """print() inside run_server(stdio) must not corrupt the JSON-RPC channel.

        This is the end-to-end regression test for the gap identified in #810:
        the logging-only fix left direct print() calls unblocked.  With
        _StdoutGuard in place, any print() that fires while the server is
        running is silently diverted to stderr.
        """
        def _leaky_server_run(transport, **_kwargs):
            # Simulate a library or user code that calls print() directly.
            print("DEBUG: this would corrupt JSON-RPC without the guard")

        with patch("naturo.mcp_server.create_server") as mock_cs:
            mock_server = MagicMock()
            mock_server.run.side_effect = _leaky_server_run
            mock_cs.return_value = mock_server
            run_server(transport="stdio")

        captured = capsys.readouterr()
        # The print() must NOT have reached real stdout.
        assert "DEBUG: this would corrupt JSON-RPC" not in captured.out
        # It should have been diverted to stderr instead.
        assert "DEBUG: this would corrupt JSON-RPC" in captured.err

    def test_non_stdio_transport_does_not_install_guard(self):
        """_StdoutGuard must NOT be installed for non-stdio transports."""
        original_stdout = sys.stdout

        with patch("naturo.mcp_server.create_server") as mock_cs:
            mock_server = MagicMock()
            mock_cs.return_value = mock_server
            run_server(transport="sse")

        # sys.stdout should never have been replaced.
        assert sys.stdout is original_stdout
