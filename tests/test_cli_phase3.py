"""CLI integration tests for Phase 3 commands (wait, app, diff)."""
import json
import pytest
from unittest.mock import patch
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

    def test_wait_json_timeout_single_json(self, runner):
        """BUG-016: wait --json timeout must output exactly one JSON document."""
        from naturo.wait import WaitResult
        with patch("naturo.wait.wait_for_element") as mock_wait:
            mock_wait.return_value = WaitResult(found=False, wait_time=1.0, warnings=[])
            result = runner.invoke(main, ["wait", "--element", "Button:Save", "--timeout", "1", "--json"])
        assert result.exit_code == 1
        # Must be valid single JSON — json.loads raises if there are two documents
        data = json.loads(result.output.strip())
        assert data["success"] is False
        assert data["found"] is False
        # Ensure there's only one JSON object in stdout
        assert result.output.strip().count("{") == result.output.strip().count("}")

    def test_wait_json_exception_single_json(self, runner):
        """BUG-016: wait --json exception must output exactly one JSON document."""
        from naturo.errors import NaturoError
        with patch("naturo.wait.wait_for_element") as mock_wait:
            mock_wait.side_effect = NaturoError("test error", code="TEST_ERROR")
            result = runner.invoke(main, ["wait", "--element", "Button:Save", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output.strip())
        assert data["success"] is False


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


class TestAppLaunchNonexistent:
    """BUG-013: app launch nonexistent app should fail."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_launch_nonexistent_app(self, runner):
        from unittest.mock import patch
        from naturo.errors import AppNotFoundError
        with patch("naturo.process.launch_app", side_effect=AppNotFoundError("nonexistent_xyz")):
            result = runner.invoke(main, ["app", "launch", "nonexistent_xyz"])
            assert result.exit_code == 1
            assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_launch_nonexistent_app_json(self, runner):
        from unittest.mock import patch
        from naturo.errors import AppNotFoundError
        with patch("naturo.process.launch_app", side_effect=AppNotFoundError("nonexistent_xyz")):
            result = runner.invoke(main, ["app", "launch", "nonexistent_xyz", "--json"])
            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["error"]["code"] == "APP_NOT_FOUND"


class TestAppRelaunchNonexistent:
    """BUG-018: app relaunch nonexistent app should fail."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_relaunch_nonexistent_app(self, runner):
        from unittest.mock import patch
        from naturo.errors import AppNotFoundError
        with patch("naturo.process.relaunch_app", side_effect=AppNotFoundError("nonexistent_xyz")):
            result = runner.invoke(main, ["app", "relaunch", "nonexistent_xyz"])
            assert result.exit_code == 1
            assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_relaunch_nonexistent_app_json(self, runner):
        from unittest.mock import patch
        from naturo.errors import AppNotFoundError
        with patch("naturo.process.relaunch_app", side_effect=AppNotFoundError("nonexistent_xyz")):
            result = runner.invoke(main, ["app", "relaunch", "nonexistent_xyz", "--json"])
            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["error"]["code"] == "APP_NOT_FOUND"


class TestBUG013TimeoutExpired:
    """BUG-013: subprocess.TimeoutExpired in launch_app must be caught."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_launch_timeout_expired_becomes_app_not_found(self):
        """TimeoutExpired from 'start /wait' should raise AppNotFoundError."""
        import subprocess
        from unittest.mock import patch, MagicMock
        from naturo.process import launch_app
        from naturo.errors import AppNotFoundError

        # Simulate Windows path: where fails (returncode=1), then start /wait times out
        where_result = MagicMock()
        where_result.returncode = 1

        def mock_run(cmd, **kwargs):
            if cmd[0] == "where":
                return where_result
            # 'start /wait' raises TimeoutExpired
            raise subprocess.TimeoutExpired(cmd, 10)

        with patch("naturo.process.platform.system", return_value="Windows"), \
             patch("naturo.process.subprocess.run", side_effect=mock_run), \
             patch("naturo.process.subprocess.Popen") as mock_popen:
            with pytest.raises(AppNotFoundError) as exc_info:
                launch_app(name="nonexistent_app_xyz")
            assert "nonexistent_app_xyz" in str(exc_info.value)

    def test_launch_timeout_expired_json_output(self, runner):
        """CLI should output clean JSON error, not a traceback."""
        from unittest.mock import patch
        from naturo.errors import AppNotFoundError
        with patch("naturo.process.launch_app",
                    side_effect=AppNotFoundError("nonexistent_app_xyz",
                                                 suggested_action="Application not found or failed to launch")):
            result = runner.invoke(main, ["app", "launch", "nonexistent_app_xyz", "--json"])
            assert result.exit_code == 1
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["error"]["code"] == "APP_NOT_FOUND"
            assert "Traceback" not in result.output


class TestBUG016SingleJson:
    """BUG-016: wait --json must output exactly one JSON document."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_wait_timeout_single_json(self, runner):
        """When wait times out in JSON mode, only one JSON object should be output."""
        from unittest.mock import patch
        from naturo.wait import WaitResult

        mock_result = WaitResult(found=False, wait_time=1.0, warnings=[])
        with patch("naturo.wait.wait_for_element", return_value=mock_result):
            result = runner.invoke(main, ["wait", "--element", "Button:Save", "--timeout", "1", "--json"])
            assert result.exit_code != 0
            # Must be exactly one valid JSON document
            output = result.output.strip()
            data = json.loads(output)  # Should not raise
            assert data["success"] is False
            assert data["found"] is False
            # Verify no second JSON object
            assert output.count('"success"') == 1

    def test_wait_timeout_json_no_error_key(self, runner):
        """Timeout result JSON should have found=false, not an error wrapper."""
        from unittest.mock import patch
        from naturo.wait import WaitResult

        mock_result = WaitResult(found=False, wait_time=1.0, warnings=[])
        with patch("naturo.wait.wait_for_element", return_value=mock_result):
            result = runner.invoke(main, ["wait", "--element", "Button:Save", "--timeout", "1", "--json"])
            output = result.output.strip()
            data = json.loads(output)
            # Should be the wait result format, not an error wrapper
            assert "found" in data
            assert "wait_time" in data


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


class TestWaitValidation:
    """BUG-020: --timeout negative values should be rejected."""

    def test_wait_negative_timeout(self, runner):
        result = runner.invoke(main, ["wait", "--element", "Button:Save", "--timeout", "-1"])
        assert result.exit_code == 1
        assert "must be >= 0" in result.output or "error" in result.output.lower()

    def test_wait_negative_timeout_json(self, runner):
        result = runner.invoke(main, ["wait", "--element", "Button:Save", "--timeout", "-1", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        assert "INVALID_INPUT" in data["error"]["code"]


class TestPressValidation:
    """BUG-019: --count <= 0 should be rejected."""

    def test_press_count_zero(self, runner):
        result = runner.invoke(main, ["press", "enter", "--count", "0"])
        assert result.exit_code == 1
        assert "must be >= 1" in result.output or "error" in result.output.lower()

    def test_press_count_negative(self, runner):
        result = runner.invoke(main, ["press", "enter", "--count", "-1"])
        assert result.exit_code == 1
        assert "must be >= 1" in result.output or "error" in result.output.lower()

    def test_press_count_negative_json(self, runner):
        result = runner.invoke(main, ["press", "enter", "--count", "-1", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False


class TestSnapshotCleanValidation:
    """BUG-021: --days negative values should be rejected."""

    def test_snapshot_clean_negative_days(self, runner):
        result = runner.invoke(main, ["snapshot", "clean", "--days", "-1", "-y"])
        assert result.exit_code == 1
        assert "must be >= 0" in result.output or "error" in result.output.lower()

    def test_snapshot_clean_negative_days_json(self, runner):
        result = runner.invoke(main, ["snapshot", "clean", "--days", "-1", "-y", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False


class TestGlobalJsonFlag:
    def test_json_flag_propagates(self, runner):
        result = runner.invoke(main, ["--json", "wait"])
        assert result.exit_code == 1
        # Should produce JSON error output
        data = json.loads(result.output)
        assert "success" in data
