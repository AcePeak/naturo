"""FuzzyGroup — Click Group with typo-correcting command suggestions."""

from __future__ import annotations

import difflib

import click

# Minimum ``difflib`` similarity ratio for a typo to earn a "Did you mean"
# hint. Click's default of 0.6 is too lax for short verbs: a 2–3 char query
# crosses it on incidental character overlap alone (``ai``→``wait``,
# ``tap``→``app`` both score 0.667), aiming an authoritative-sounding hint at a
# semantically unrelated command (#889). Genuine one-character typos of real
# commands score noticeably higher (``apps``→``app`` 0.857, ``mvoe``→``move``
# 0.750), so 0.7 sits in the empirical gap — it drops the spurious short-query
# matches while preserving every real near-miss.
_SUGGESTION_CUTOFF = 0.7


class FuzzyGroup(click.Group):
    """Click Group subclass that suggests the closest command on typos.

    When a user types an unrecognized subcommand, this group uses
    ``difflib.get_close_matches`` to find and suggest the most similar
    command name, improving the error message from a bare "No such command"
    to "No such command 'X'. Did you mean 'Y'?".

    Commands registered with ``hidden=True`` are excluded from suggestions:
    they are deliberately omitted from ``--help``, so pointing a user at them
    on a typo would contradict that (see #867).

    The not-found branch is handled entirely here rather than delegated to the
    base class. Click 8.4 added its own "Did you mean" suggester
    (:class:`click.exceptions.NoSuchCommand`) which matches against *all*
    commands, including ``hidden=True`` ones — so delegating would re-introduce
    the leak this class exists to prevent.

    An optional ``aliases`` map handles intuitive verbs that edit-distance
    matching cannot discover — either because the real command lives inside a
    subgroup (``launch`` → ``app launch``) or because it is named differently
    (``screenshot`` → ``capture``). These curated intents are checked before
    the fuzzy match and may point at a multi-word command path (see #880).
    """

    def __init__(
        self, *args: object, aliases: dict[str, str] | None = None, **kwargs: object
    ) -> None:
        """Initialize the group, capturing the optional intent-alias map.

        Args:
            *args: Positional arguments forwarded to :class:`click.Group`.
            aliases: Optional mapping of an unrecognized command name to the
                canonical command path to suggest (e.g. ``{"launch": "app
                launch"}``). The path may contain spaces to reference a
                subgroup command.
            **kwargs: Keyword arguments forwarded to :class:`click.Group`.
        """
        super().__init__(*args, **kwargs)
        self.aliases: dict[str, str] = aliases or {}

    def _suggestable_commands(self, ctx: click.Context) -> list[str]:
        """Return command names eligible to appear as typo suggestions.

        Excludes commands that fail to resolve and those registered with
        ``hidden=True``, keeping suggestions consistent with ``--help``.

        Args:
            ctx: Click context.

        Returns:
            The visible (non-hidden) subcommand names of this group.
        """
        visible: list[str] = []
        for name in self.list_commands(ctx):
            cmd = self.get_command(ctx, name)
            if cmd is not None and not getattr(cmd, "hidden", False):
                visible.append(name)
        return visible

    def resolve_command(self, ctx: click.Context, args: list[str]):
        """Resolve a subcommand, injecting typo-correction suggestions.

        When the requested command is unknown, fail here with a suggestion
        drawn only from visible commands (:meth:`_suggestable_commands`),
        rather than delegating to the base class — see the class docstring for
        why delegation would leak hidden commands on Click 8.4+.

        Args:
            ctx: Click context.
            args: Remaining CLI arguments (args[0] is the subcommand name).

        Returns:
            Tuple of (command_name, command, remaining_args) from the parent
            implementation when the command resolves.

        Raises:
            click.UsageError: When the command is not found, with a
                "Did you mean 'X'?" hint if a visible command is a close match.
        """
        cmd_name = click.utils.make_str(args[0])
        cmd = self.get_command(ctx, cmd_name)

        # Mirror Click's own normalization fallback before giving up.
        if cmd is None and ctx.token_normalize_func is not None:
            cmd_name = ctx.token_normalize_func(cmd_name)
            cmd = self.get_command(ctx, cmd_name)

        # An option-like first token (e.g. ``-x``) is not a typo'd command;
        # let the base class re-parse it so option errors / ``--help`` work.
        # ``resilient_parsing`` is set during shell completion, where failing
        # would break completion — defer to the base class there too.
        if cmd is None and not ctx.resilient_parsing and not cmd_name.startswith("-"):
            # Curated intents win over fuzzy guesses: they target the command a
            # first-time user actually means, which edit distance cannot reach
            # (subgroup commands or differently-named ones).
            alias_target = self.aliases.get(cmd_name)
            if alias_target:
                ctx.fail(
                    f"No such command '{cmd_name}'. Did you mean '{alias_target}'?"
                )
            matches = difflib.get_close_matches(
                cmd_name,
                self._suggestable_commands(ctx),
                n=1,
                cutoff=_SUGGESTION_CUTOFF,
            )
            if matches:
                ctx.fail(
                    f"No such command '{cmd_name}'. Did you mean '{matches[0]}'?"
                )
            ctx.fail(f"No such command '{cmd_name}'.")

        return super().resolve_command(ctx, args)
