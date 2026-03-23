"""FuzzyGroup — Click Group with typo-correcting command suggestions."""

import difflib

import click


class FuzzyGroup(click.Group):
    """Click Group subclass that suggests the closest command on typos.

    When a user types an unrecognized subcommand, this group uses
    ``difflib.get_close_matches`` to find and suggest the most similar
    command name, improving the error message from a bare "No such command"
    to "No such command 'X'. Did you mean 'Y'?".
    """

    def resolve_command(self, ctx: click.Context, args: list[str]):
        """Override to inject typo-correction suggestions.

        Args:
            ctx: Click context.
            args: Remaining CLI arguments (args[0] is the subcommand name).

        Returns:
            Tuple of (command_name, command, remaining_args) from the parent
            implementation.

        Raises:
            click.UsageError: When the command is not found and a close match
                exists, includes "Did you mean 'X'?" in the error.
        """
        cmd_name = click.utils.make_str(args[0])
        cmd = self.get_command(ctx, cmd_name)
        if cmd is None:
            matches = difflib.get_close_matches(
                cmd_name, self.list_commands(ctx), n=1, cutoff=0.6
            )
            if matches:
                ctx.fail(
                    f"No such command '{cmd_name}'. Did you mean '{matches[0]}'?"
                )
        return super().resolve_command(ctx, args)
