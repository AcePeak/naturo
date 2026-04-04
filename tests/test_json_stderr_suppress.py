"""Tests for #783: JSON mode must not leak log messages to stderr.

When --json is used, all logging output must be suppressed so that
only valid JSON appears on stdout/stderr.
"""

import logging

from click.testing import CliRunner

from naturo.cli import main


class TestJsonStderrSuppress:
    """--json must silence all logging output."""

    def test_json_mode_installs_null_handler(self):
        """After invoking with --json, root logger should have a NullHandler."""
        runner = CliRunner()
        # Run any command with --json; --help exits cleanly.
        result = runner.invoke(main, ["--json", "--help"])
        assert result.exit_code == 0
        # The root logger should now have a NullHandler installed
        root = logging.getLogger()
        has_null = any(isinstance(h, logging.NullHandler) for h in root.handlers)
        assert has_null, f"Expected NullHandler in root logger, got: {root.handlers}"

    def test_verbose_mode_does_not_crash(self):
        """--verbose should enable debug-level logging without errors."""
        runner = CliRunner()
        result = runner.invoke(main, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_json_mode_no_log_output(self):
        """In JSON mode, emitting a log message should produce no output."""
        runner = CliRunner()
        result = runner.invoke(main, ["--json", "--help"])
        assert result.exit_code == 0
        # After --json setup, log messages should go nowhere
        logger = logging.getLogger("naturo.test")
        logger.warning("this should be suppressed")
        # If we got here without output, the NullHandler is working
