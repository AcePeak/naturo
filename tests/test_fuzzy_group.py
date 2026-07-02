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


class TestFuzzyGroupAliases:
    """Tests for the curated intent-alias suggestions (#880).

    Some intuitive verbs do not match any top-level command by edit distance —
    either because the real command lives inside a subgroup (``launch`` →
    ``app launch``) or because it is named differently (``screenshot`` →
    ``capture``). A curated ``aliases`` map lets a group point such intents at
    the right command, which ``difflib`` alone cannot discover.
    """

    @pytest.fixture
    def cli(self):
        """Create a FuzzyGroup CLI with a subgroup and an intent-alias map."""
        @click.group(
            cls=FuzzyGroup,
            aliases={"launch": "app launch", "screenshot": "capture"},
        )
        def app():
            pass

        @app.command()
        def capture():
            click.echo("captured")

        @click.group()
        def app_group():
            pass

        @app_group.command("launch")
        def app_launch():
            click.echo("launched")

        app.add_command(app_group, "app")
        return app

    def test_subgroup_intent_suggests_full_path(self, cli):
        result = CliRunner().invoke(cli, ["launch"])
        assert result.exit_code != 0
        assert "Did you mean 'app launch'?" in result.output

    def test_renamed_intent_suggests_real_name(self, cli):
        result = CliRunner().invoke(cli, ["screenshot"])
        assert result.exit_code != 0
        assert "Did you mean 'capture'?" in result.output

    def test_alias_does_not_break_exact_command(self, cli):
        result = CliRunner().invoke(cli, ["capture"])
        assert result.exit_code == 0
        assert "captured" in result.output

    def test_no_alias_falls_back_to_no_suggestion(self, cli):
        result = CliRunner().invoke(cli, ["zzzzzzz"])
        assert result.exit_code != 0
        assert "Did you mean" not in result.output


class TestRealCliIntentAliases:
    """The first-run verbs from #880 should suggest the correct command.

    A first-time user typing an intuitive English verb must be pointed at the
    real command instead of hitting a dead ``No such command`` wall.
    """

    @pytest.mark.parametrize(
        "verb,target",
        [
            ("launch", "app launch"),
            ("open", "app launch"),
            ("run", "app launch"),
            ("start", "app launch"),
            ("screenshot", "capture"),
        ],
    )
    def test_intent_verb_suggests_command(self, verb, target):
        from naturo.cli import main

        result = CliRunner().invoke(main, [verb])
        assert result.exit_code != 0
        assert f"Did you mean '{target}'?" in result.output

    def test_alias_targets_resolve_to_real_commands(self):
        """Every alias target must be a real command path (drift guard)."""
        from naturo.cli import _COMMAND_INTENT_ALIASES, main

        ctx = click.Context(main, info_name="naturo")
        for target in set(_COMMAND_INTENT_ALIASES.values()):
            group = main
            *groups, leaf = target.split()
            for name in groups:
                group = group.get_command(ctx, name)
                assert isinstance(group, click.Group), (
                    f"alias target '{target}': '{name}' is not a group"
                )
            assert group.get_command(ctx, leaf) is not None, (
                f"alias target '{target}' does not resolve to a command"
            )


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


class TestFuzzyGroupShortQueryPrecision:
    """A short query that is only an edit-distance neighbor — sharing no real
    intent — must not produce an authoritative "Did you mean" hint (#889).

    Click's default ``cutoff=0.6`` lets random character overlaps in 2–3 char
    queries cross the bar (``ai``→``wait``, ``tap``→``app``, both ratio 0.667).
    Genuine one-character typos of real commands score markedly higher
    (≥ 0.75), so a tighter cutoff cleanly separates the two.
    """

    @pytest.fixture
    def cli(self):
        @click.group(cls=FuzzyGroup)
        def app_group():
            pass

        @app_group.command(name="app")
        def app_cmd():
            click.echo("app")

        @app_group.command(name="wait")
        def wait_cmd():
            click.echo("wait")

        @app_group.command(name="list")
        def list_cmd():
            click.echo("list")

        return app_group

    def test_spurious_short_neighbor_not_suggested(self, cli):
        """``ai`` is a 0.667-ratio neighbor of ``wait`` but shares no intent."""
        result = CliRunner().invoke(cli, ["ai"])
        assert result.exit_code != 0
        assert "Did you mean" not in result.output

    def test_spurious_short_neighbor_not_aimed_at_app(self, cli):
        """``tap`` is a 0.667-ratio neighbor of ``app`` but means ``click``."""
        result = CliRunner().invoke(cli, ["tap"])
        assert result.exit_code != 0
        assert "Did you mean" not in result.output

    def test_genuine_short_typo_still_suggested(self, cli):
        """``lis`` is a genuine one-char-short typo of ``list`` (ratio 0.857)."""
        result = CliRunner().invoke(cli, ["lis"])
        assert result.exit_code != 0
        assert "Did you mean 'list'?" in result.output


class TestRealCliSpuriousSuggestions:
    """#889 — short verbs must not be nudged toward unrelated commands.

    The hint reads as authoritative ("Did you mean ...?"), so aiming it at the
    wrong command is worse than emitting nothing: a user who types ``naturo ai``
    and is pointed at ``wait`` concludes naturo has no AI surface.
    """

    @pytest.mark.parametrize(
        "verb,wrong_target",
        [
            ("ai", "wait"),
            ("tap", "app"),
        ],
    )
    def test_short_spurious_verb_gives_no_wrong_suggestion(self, verb, wrong_target):
        from naturo.cli import main

        result = CliRunner().invoke(main, [verb])
        assert result.exit_code != 0
        assert f"Did you mean '{wrong_target}'?" not in result.output

    @pytest.mark.parametrize(
        "typo,target",
        [
            ("apps", "app"),
            ("clik", "click"),
            ("lis", "list"),
            ("typ", "type"),
            ("mov", "move"),
            ("fnd", "find"),
            ("dif", "diff"),
            ("scrol", "scroll"),
        ],
    )
    def test_genuine_near_miss_still_suggested(self, typo, target):
        """A real one-character typo still surfaces its command (ratio ≥ 0.75)."""
        from naturo.cli import main

        result = CliRunner().invoke(main, [typo])
        assert result.exit_code != 0
        assert f"Did you mean '{target}'?" in result.output
