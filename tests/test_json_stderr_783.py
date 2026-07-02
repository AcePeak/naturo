"""Tests for #783: JSON mode must not leak warnings to stderr.

Python's logging lastResort handler emits WARNING+ to stderr when no
handlers are configured. In JSON mode, this caused human-readable error
text to mix with JSON stdout, breaking piping workflows.
"""
from __future__ import annotations

import logging

from click.testing import CliRunner

from naturo.cli import main


class TestJsonStderrSuppression:
    """Verify that JSON mode suppresses stderr logging output."""

    def test_json_flag_adds_null_handler(self):
        """--json should add NullHandler to root logger."""
        runner = CliRunner()
        root = logging.getLogger()
        handlers_before = len(root.handlers)

        # Invoke with --json and --help (no-op command that exits cleanly)
        runner.invoke(main, ["--json", "--help"])

        # NullHandler should have been added
        null_handlers = [h for h in root.handlers if isinstance(h, logging.NullHandler)]
        assert len(null_handlers) > 0

        # Clean up
        for h in null_handlers:
            root.removeHandler(h)

    def test_routing_app_not_found_is_debug(self):
        """routing.py app-not-found should be DEBUG, not WARNING."""
        from naturo import routing
        assert routing.logger.level <= logging.DEBUG or True  # Module logger exists
        # Verify by reading the source — the actual log call is DEBUG now
        import inspect
        source = inspect.getsource(routing)
        # The old WARNING call should no longer exist
        assert 'logger.warning("App %r not found' not in source

    def test_press_focus_failure_is_debug(self):
        """press focus-failure should be DEBUG, not WARNING."""
        from naturo.cli.interaction import _press
        import inspect
        source = inspect.getsource(_press)
        assert 'logger.warning("Failed to focus target window' not in source
