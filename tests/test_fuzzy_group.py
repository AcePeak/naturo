"""Tests for naturo.cli.fuzzy_group — FuzzyGroup typo-correcting Click group."""

import click
import pytest
from click.testing import CliRunner

from naturo.cli.fuzzy_group import FuzzyGroup


@pytest.fixture
def cli():
    """Create a CLI app using FuzzyGroup with a few subcommands."""
    @click.group(cls=FuzzyGroup)
    def app():
        pass

    @app.command()
    def capture():
        click.echo("captured")

    @app.command()
    def click_cmd():
        click.echo("clicked")

    @app.command()
    def scroll():
        click.echo("scrolled")

    @app.command()
    def snapshot():
        click.echo("snapshot taken")

    return app


class TestFuzzyGroup:
    """Tests for FuzzyGroup typo correction."""

    def test_exact_command_works(self, cli):
        result = CliRunner().invoke(cli, ["capture"])
        assert result.exit_code == 0
        assert "captured" in result.output

    def test_typo_suggests_close_match(self, cli):
        result = CliRunner().invoke(cli, ["captur"])
        assert result.exit_code != 0
        assert "Did you mean 'capture'?" in result.output

    def test_no_match_no_suggestion(self, cli):
        """Completely unrelated command should not suggest anything."""
        result = CliRunner().invoke(cli, ["zzzzzzz"])
        assert result.exit_code != 0
        assert "Did you mean" not in result.output

    def test_close_typo_scroll(self, cli):
        result = CliRunner().invoke(cli, ["scrol"])
        assert result.exit_code != 0
        assert "Did you mean 'scroll'?" in result.output

    def test_close_typo_snapshot(self, cli):
        result = CliRunner().invoke(cli, ["snapsho"])
        assert result.exit_code != 0
        assert "Did you mean 'snapshot'?" in result.output

    def test_empty_group_no_crash(self):
        """FuzzyGroup with no commands should handle typo gracefully."""
        @click.group(cls=FuzzyGroup)
        def empty():
            pass

        result = CliRunner().invoke(empty, ["anything"])
        assert result.exit_code != 0

    def test_help_still_works(self, cli):
        result = CliRunner().invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "capture" in result.output
