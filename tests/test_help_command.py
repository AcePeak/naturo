"""Test that `naturo help` works as an alias for `naturo --help` (#457)."""
from click.testing import CliRunner

from naturo.cli import main


class TestHelpCommand:
    """Verify `naturo help` shows usage information."""

    def test_help_subcommand_succeeds(self):
        """'naturo help' exits 0 and shows usage text."""
        runner = CliRunner()
        result = runner.invoke(main, ["help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "naturo" in result.output.lower()

    def test_help_shows_commands(self):
        """'naturo help' lists available commands like --help does."""
        runner = CliRunner()
        help_result = runner.invoke(main, ["help"])
        flag_result = runner.invoke(main, ["--help"])
        # Both should show the same core content
        assert "see" in help_result.output
        assert "click" in help_result.output
        assert help_result.output == flag_result.output

    def test_help_is_hidden(self):
        """'help' command should not appear in the commands list."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        # 'help' should not be listed as a command
        lines = result.output.split("\n")
        command_lines = [l.strip() for l in lines if l.strip().startswith("help ")]
        assert len(command_lines) == 0
