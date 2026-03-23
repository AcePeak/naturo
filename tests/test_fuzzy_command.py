"""Tests for fuzzy command matching — typo correction suggestions."""

import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestFuzzyTopLevel:
    """Fuzzy matching on top-level naturo commands."""

    @pytest.mark.parametrize("typo,expected", [
        ("captur", "capture"),
        ("clck", "click"),
        ("tpye", "type"),
        ("widnow", "window"),
        ("snapshto", "snapshot"),
        ("appp", "app"),
    ])
    def test_suggests_close_match(self, runner, typo, expected):
        result = runner.invoke(main, [typo])
        assert result.exit_code != 0
        assert f"Did you mean '{expected}'?" in result.output

    def test_no_suggestion_for_gibberish(self, runner):
        result = runner.invoke(main, ["xyzzyplugh"])
        assert result.exit_code != 0
        assert "Did you mean" not in result.output


class TestFuzzySubgroup:
    """Fuzzy matching on subgroup commands (e.g. app inspect)."""

    def test_app_subcommand_typo(self, runner):
        result = runner.invoke(main, ["app", "inspact"])
        assert result.exit_code != 0
        assert "Did you mean 'inspect'?" in result.output

    def test_app_subcommand_typo_lanch(self, runner):
        result = runner.invoke(main, ["app", "lanch"])
        assert result.exit_code != 0
        assert "Did you mean 'launch'?" in result.output
