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

    @app.command(hidden=True)
    def internal():
        click.echo("internal")

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

    def test_hidden_command_not_suggested(self, cli):
        """A typo close to a hidden command must NOT suggest it (#867).

        Hidden commands are omitted from ``--help``; suggesting them on a typo
        contradicts that and points first-time users at internal/debug surfaces.
        """
        result = CliRunner().invoke(cli, ["interna"])
        assert result.exit_code != 0
        assert "Did you mean" not in result.output

    def test_visible_suggestion_unaffected_by_hidden(self, cli):
        """Filtering hidden commands must not suppress visible close matches."""
        result = CliRunner().invoke(cli, ["captur"])
        assert result.exit_code != 0
        assert "Did you mean 'capture'?" in result.output


class TestRealCliHiddenSuggestions:
    """Regression tests against the real naturo CLI (#867).

    Several top-level commands are registered ``hidden=True`` (e.g. ``snapshot``,
    ``window``, ``hotkey``, ``excel``). None of them should ever surface as a
    typo suggestion, since they are deliberately omitted from ``naturo --help``.
    """

    @pytest.mark.parametrize(
        "typo,hidden_name",
        [
            ("screenshot", "snapshot"),
            ("snapshots", "snapshot"),
            ("windo", "window"),
            ("hotke", "hotkey"),
        ],
    )
    def test_hidden_top_level_command_not_suggested(self, typo, hidden_name):
        from naturo.cli import main

        result = CliRunner().invoke(main, [typo])
        assert result.exit_code != 0
        assert f"Did you mean '{hidden_name}'" not in result.output

    def test_visible_top_level_command_still_suggested(self):
        """A typo of a visible command still gets a suggestion."""
        from naturo.cli import main

        result = CliRunner().invoke(main, ["captur"])
        assert result.exit_code != 0
        assert "Did you mean 'capture'?" in result.output
