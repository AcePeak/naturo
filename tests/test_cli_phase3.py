"""CLI integration tests for Phase 3 commands (wait, app, diff)."""
import json
import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestWaitCommand:
    def test_wait_help(self, runner):
        result = runner.invoke(main, ["wait", "--help"])
        assert result.exit_code == 0
        assert "--element" in result.output
        assert "--window" in result.output
        assert "--gone" in result.output
        assert "--timeout" in result.output
        assert "--interval" in result.output

    def test_wait_no_args(self, runner):
        result = runner.invoke(main, ["wait"])
        assert result.exit_code == 1
        assert "Specify" in result.output or "error" in result.output.lower()

    def test_wait_json_no_args(self, runner):
        result = runner.invoke(main, ["wait", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "INVALID_INPUT" in data["error"]["code"]


class TestAppCommands:
    def test_app_help(self, runner):
        result = runner.invoke(main, ["app", "--help"])
        assert result.exit_code == 0
        assert "launch" in result.output
        assert "quit" in result.output
        assert "relaunch" in result.output
        assert "list" in result.output
        assert "find" in result.output

    def test_app_launch_help(self, runner):
        result = runner.invoke(main, ["app", "launch", "--help"])
        assert result.exit_code == 0
        assert "--wait-until-ready" in result.output
        assert "--no-focus" in result.output
        assert "--timeout" in result.output

    def test_app_quit_help(self, runner):
        result = runner.invoke(main, ["app", "quit", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--pid" in result.output
        assert "--force" in result.output

    def test_app_quit_no_args(self, runner):
        result = runner.invoke(main, ["app", "quit"])
        assert result.exit_code == 1

    def test_app_quit_json_no_args(self, runner):
        result = runner.invoke(main, ["app", "quit", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False

    def test_app_relaunch_help(self, runner):
        result = runner.invoke(main, ["app", "relaunch", "--help"])
        assert result.exit_code == 0
        assert "--wait-until-ready" in result.output
        assert "--timeout" in result.output

    def test_app_list_help(self, runner):
        result = runner.invoke(main, ["app", "list", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_app_find_help(self, runner):
        result = runner.invoke(main, ["app", "find", "--help"])
        assert result.exit_code == 0
        assert "--pid" in result.output


class TestDiffCommand:
    def test_diff_help(self, runner):
        result = runner.invoke(main, ["diff", "--help"])
        assert result.exit_code == 0
        assert "--snapshot" in result.output
        assert "--window" in result.output
        assert "--interval" in result.output

    def test_diff_no_args(self, runner):
        result = runner.invoke(main, ["diff"])
        assert result.exit_code == 1

    def test_diff_json_no_args(self, runner):
        result = runner.invoke(main, ["diff", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "INVALID_INPUT" in data["error"]["code"]

    def test_diff_single_snapshot(self, runner):
        result = runner.invoke(main, ["diff", "--snapshot", "snap1"])
        assert result.exit_code == 1
        # Need exactly 2 snapshots


class TestGlobalJsonFlag:
    def test_json_flag_propagates(self, runner):
        result = runner.invoke(main, ["--json", "wait"])
        assert result.exit_code == 1
        # Should produce JSON error output
        data = json.loads(result.output)
        assert "success" in data
