"""Tests for naturo.cli.core._tools — tools command (hidden, not-yet-implemented)."""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from naturo.cli.core._tools import tools


@pytest.fixture
def runner():
    return CliRunner()


class TestToolsCommand:
    """Tests for the hidden 'tools' command."""

    def test_plain_output_shows_error(self, runner):
        result = runner.invoke(tools, [], catch_exceptions=False)
        assert result.exit_code == 1
        assert "not implemented yet" in result.output.lower() or \
               "not implemented yet" in (result.stderr or "").lower() or \
               "not implemented yet" in result.output

    def test_json_output_returns_json(self, runner):
        result = runner.invoke(tools, ["--json"], catch_exceptions=False)
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data.get("error_code") == "NOT_IMPLEMENTED" or \
               "NOT_IMPLEMENTED" in result.output

    def test_short_flag_j(self, runner):
        result = runner.invoke(tools, ["-j"], catch_exceptions=False)
        assert result.exit_code == 1
        # Should produce JSON output same as --json
        assert "{" in result.output
