"""Test that every exposed CLI command works (no "Not implemented" stubs visible)."""
import re
from click.testing import CliRunner
from naturo.cli import main


runner = CliRunner()

NOT_IMPLEMENTED_RE = re.compile(r"Not implemented yet", re.IGNORECASE)


def _visible_subcommands(group, parent_args=None):
    """Yield (full_args_list, command) for every non-hidden leaf/group."""
    parent_args = parent_args or []
    for name, cmd in sorted(group.commands.items()):
        if getattr(cmd, "hidden", False):
            continue
        full = parent_args + [name]
        yield full, cmd
        # Recurse into subgroups
        if hasattr(cmd, "commands"):
            yield from _visible_subcommands(cmd, full)


def test_no_stub_in_help():
    """Top-level --help must not mention 'Not implemented'."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0, result.output
    assert not NOT_IMPLEMENTED_RE.search(result.output), (
        f"Top-level --help contains stub text:\n{result.output}"
    )


def test_all_visible_commands_respond():
    """Every visible command must produce --help output without 'Not implemented'."""
    for args, cmd in _visible_subcommands(main):
        help_args = args + ["--help"]
        result = runner.invoke(main, help_args)
        assert result.exit_code == 0, (
            f"naturo {' '.join(help_args)} failed (exit {result.exit_code}):\n{result.output}"
        )
        assert not NOT_IMPLEMENTED_RE.search(result.output), (
            f"naturo {' '.join(help_args)} contains stub text:\n{result.output}"
        )


def test_no_visible_command_prints_not_implemented():
    """Invoking any visible leaf command (with no args) must not print 'Not implemented'."""
    for args, cmd in _visible_subcommands(main):
        # Skip groups — they just show help when invoked bare
        if hasattr(cmd, "commands"):
            continue
        result = runner.invoke(main, args)
        # Some commands legitimately fail due to missing args or Windows-only —
        # that's fine. They just must NOT say "Not implemented".
        assert not NOT_IMPLEMENTED_RE.search(result.output), (
            f"naturo {' '.join(args)} returned stub text:\n{result.output}"
        )


def test_hidden_commands_not_in_help():
    """Hidden commands must not appear in any --help output."""
    # Check top level
    result = runner.invoke(main, ["--help"])
    # Known hidden top-level groups that were removed entirely
    for name in ["window", "menu", "clipboard", "dialog", "open", "taskbar",
                 "tray", "desktop", "agent", "mcp", "excel", "java", "sap",
                 "registry", "service", "tools"]:
        # These should not appear as commands in help
        # (they may appear in description text, so check the Commands section)
        lines = result.output.split("\n")
        in_commands = False
        for line in lines:
            if line.strip().startswith("Commands:"):
                in_commands = True
                continue
            if in_commands:
                # Each command line starts with spaces then the command name
                stripped = line.strip()
                cmd_name = stripped.split()[0] if stripped else ""
                assert cmd_name != name, (
                    f"Hidden group '{name}' is visible in top-level --help"
                )
