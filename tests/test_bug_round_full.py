"""Regression tests for Round Full bugs (BUG-022 through BUG-028)."""
import json
import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestBUG022SnapshotCleanExitCode:
    """BUG-022: snapshot clean without args should exit non-zero."""

    def test_clean_no_args_exit_code(self, runner):
        result = runner.invoke(main, ["snapshot", "clean"])
        assert result.exit_code != 0, f"Expected non-zero exit code, got {result.exit_code}"

    def test_clean_no_args_json(self, runner):
        result = runner.invoke(main, ["snapshot", "clean", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


class TestBUG023LearnUnknownTopic:
    """BUG-023: learn nonexistent topic should error."""

    def test_learn_unknown_topic(self, runner):
        result = runner.invoke(main, ["learn", "nonexistent_topic"])
        assert result.exit_code != 0
        assert "Unknown topic" in result.output or "nonexistent_topic" in result.output

    def test_learn_valid_topic(self, runner):
        result = runner.invoke(main, ["learn", "capture"])
        assert result.exit_code == 0

    def test_learn_no_topic(self, runner):
        result = runner.invoke(main, ["learn"])
        assert result.exit_code == 0
        assert "Available topics" in result.output


class TestBUG024JsonFormatConsistency:
    """BUG-024: All JSON output should use {success, error: {code, message}} format."""

    def test_click_json_error_format(self, runner):
        """click --json error should use structured error format."""
        result = runner.invoke(main, ["click", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert isinstance(data["error"], dict)
        assert "code" in data["error"]
        assert "message" in data["error"]

    def test_type_json_error_format(self, runner):
        result = runner.invoke(main, ["type", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert isinstance(data["error"], dict)
        assert "code" in data["error"]

    def test_press_json_error_format(self, runner):
        result = runner.invoke(main, ["press", "enter", "--count", "0", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert isinstance(data["error"], dict)

    def test_hotkey_json_error_format(self, runner):
        result = runner.invoke(main, ["hotkey", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert isinstance(data["error"], dict)

    def test_move_json_error_format(self, runner):
        result = runner.invoke(main, ["move", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert isinstance(data["error"], dict)

    def test_drag_json_error_format(self, runner):
        result = runner.invoke(main, ["drag", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert isinstance(data["error"], dict)

    def test_paste_json_error_format(self, runner):
        result = runner.invoke(main, ["paste", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert isinstance(data["error"], dict)

    def test_no_ok_key_in_json(self, runner):
        """Ensure 'ok' key is not used anywhere — only 'success'."""
        result = runner.invoke(main, ["click", "--json"])
        data = json.loads(result.output)
        assert "ok" not in data, "'ok' key found — should be 'success'"


class TestBUG025ScrollAmountValidation:
    """BUG-025: scroll -a 0 and -a -1 should be rejected."""

    def test_scroll_amount_zero(self, runner):
        result = runner.invoke(main, ["scroll", "-a", "0"])
        assert result.exit_code != 0
        assert "must be >= 1" in result.output or "error" in result.output.lower()

    def test_scroll_amount_negative(self, runner):
        result = runner.invoke(main, ["scroll", "-a", "-1"])
        assert result.exit_code != 0
        assert "must be >= 1" in result.output or "error" in result.output.lower()

    def test_scroll_amount_negative_json(self, runner):
        result = runner.invoke(main, ["scroll", "-a", "-1", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


class TestBUG026MenuInspectAppNotFound:
    """BUG-026: menu-inspect --app nonexistent should report APP_NOT_FOUND."""

    def test_menu_inspect_nonexistent_app(self, runner):
        from unittest.mock import patch, MagicMock
        with patch("naturo.cli.core.platform.system", return_value="Windows"), \
             patch("naturo.cli.core._get_backend", return_value=MagicMock()), \
             patch("naturo.process.find_process", return_value=None):
            result = runner.invoke(main, ["menu-inspect", "--app", "nonexistent"])
            assert result.exit_code != 0
            assert "not found" in result.output.lower() or "Application not found" in result.output

    def test_menu_inspect_nonexistent_app_json(self, runner):
        from unittest.mock import patch, MagicMock
        with patch("naturo.cli.core.platform.system", return_value="Windows"), \
             patch("naturo.cli.core._get_backend", return_value=MagicMock()), \
             patch("naturo.process.find_process", return_value=None):
            result = runner.invoke(main, ["menu-inspect", "--app", "nonexistent", "--json"])
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["success"] is False
            assert data["error"]["code"] == "APP_NOT_FOUND"


class TestBUG027MenuInspectExitCode:
    """BUG-027: menu-inspect success=false should have non-zero exit code."""

    def test_menu_inspect_no_items_exit_code(self, runner):
        from unittest.mock import patch, MagicMock
        mock_backend = MagicMock()
        mock_backend.get_menu_items.return_value = []
        with patch("naturo.cli.core.platform.system", return_value="Windows"), \
             patch("naturo.cli.core._get_backend", return_value=mock_backend), \
             patch("naturo.process.find_process", return_value=MagicMock()):
            result = runner.invoke(main, ["menu-inspect", "--app", "someapp", "--json"])
            assert result.exit_code != 0
            data = json.loads(result.output)
            assert data["success"] is False


class TestBUG028DepthValidation:
    """BUG-028: see/find --depth should validate range 1-10."""

    def test_see_depth_zero(self, runner):
        result = runner.invoke(main, ["see", "--depth", "0"])
        assert result.exit_code != 0
        assert "must be between 1 and 10" in result.output or "error" in result.output.lower()

    def test_see_depth_negative(self, runner):
        result = runner.invoke(main, ["see", "--depth", "-1"])
        assert result.exit_code != 0

    def test_see_depth_zero_json(self, runner):
        result = runner.invoke(main, ["see", "--depth", "0", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_find_depth_zero(self, runner):
        result = runner.invoke(main, ["find", "Save", "--depth", "0"])
        assert result.exit_code != 0
        assert "must be between 1 and 10" in result.output or "error" in result.output.lower()

    def test_find_depth_negative_json(self, runner):
        result = runner.invoke(main, ["find", "Save", "--depth", "-1", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_see_depth_11(self, runner):
        result = runner.invoke(main, ["see", "--depth", "11"])
        assert result.exit_code != 0


class TestBUG032TypeWpmValidation:
    """BUG-032: type --wpm should validate >= 1."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_type_wpm_zero(self, runner):
        result = runner.invoke(main, ["type", "--wpm", "0", "hello"])
        assert result.exit_code != 0
        assert "--wpm must be >= 1" in result.output or "error" in result.output.lower()

    def test_type_wpm_negative(self, runner):
        result = runner.invoke(main, ["type", "--wpm", "-1", "hello"])
        assert result.exit_code != 0

    def test_type_wpm_zero_json(self, runner):
        result = runner.invoke(main, ["type", "--wpm", "0", "hello", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_type_wpm_negative_json(self, runner):
        result = runner.invoke(main, ["type", "--wpm", "-1", "hello", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


class TestBUG033DragBoundaryValidation:
    """BUG-033: drag --steps and --duration should validate boundaries."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_drag_steps_zero(self, runner):
        result = runner.invoke(main, ["drag", "--from-coords", "100", "100", "--to-coords", "200", "200", "--steps", "0"])
        assert result.exit_code != 0
        assert "--steps must be >= 1" in result.output or "error" in result.output.lower()

    def test_drag_steps_negative(self, runner):
        result = runner.invoke(main, ["drag", "--from-coords", "100", "100", "--to-coords", "200", "200", "--steps", "-1"])
        assert result.exit_code != 0

    def test_drag_steps_zero_json(self, runner):
        result = runner.invoke(main, ["drag", "--from-coords", "100", "100", "--to-coords", "200", "200", "--steps", "0", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_drag_duration_negative(self, runner):
        result = runner.invoke(main, ["drag", "--from-coords", "100", "100", "--to-coords", "200", "200", "--duration", "-1"])
        assert result.exit_code != 0
        assert "--duration must be >= 0" in result.output or "error" in result.output.lower()

    def test_drag_duration_negative_json(self, runner):
        result = runner.invoke(main, ["drag", "--from-coords", "100", "100", "--to-coords", "200", "200", "--duration", "-1", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


class TestBUG034WaitIntervalValidation:
    """BUG-034: wait --interval should validate > 0."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_wait_interval_negative(self, runner):
        result = runner.invoke(main, ["wait", "--element", "test", "--interval", "-1"])
        assert result.exit_code != 0
        assert "--interval must be > 0" in result.output or "error" in result.output.lower()

    def test_wait_interval_zero(self, runner):
        result = runner.invoke(main, ["wait", "--element", "test", "--interval", "0"])
        assert result.exit_code != 0

    def test_wait_interval_negative_json(self, runner):
        result = runner.invoke(main, ["wait", "--element", "test", "--interval", "-1", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "--interval must be > 0" in data["error"]["message"]

    def test_wait_interval_zero_json(self, runner):
        result = runner.invoke(main, ["wait", "--element", "test", "--interval", "0", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


class TestBug035ClickWaitForHidden:
    """BUG-035: click --wait-for is declared but not implemented; should be hidden."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_wait_for_not_in_help(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert "--wait-for" not in result.output

    def test_wait_for_still_accepted(self, runner):
        """Hidden options should still be accepted (not break existing scripts)."""
        result = runner.invoke(main, ["click", "--wait-for", "5", "--coords", "100", "100"])
        # Should not fail due to unknown option
        assert "No such option" not in (result.output or "")


class TestBug036MoveDurationHidden:
    """BUG-036: move --duration is declared but not passed to backend; should be hidden."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_duration_not_in_help(self, runner):
        result = runner.invoke(main, ["move", "--help"])
        assert "--duration" not in result.output

    def test_duration_still_accepted(self, runner):
        """Hidden options should still be accepted."""
        result = runner.invoke(main, ["move", "--duration", "2", "--coords", "100", "100"])
        assert "No such option" not in (result.output or "")


class TestBug037HotkeyHoldDurationValidation:
    """BUG-037: hotkey --hold-duration should reject negative values."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_hold_duration_negative(self, runner):
        result = runner.invoke(main, ["hotkey", "--hold-duration", "-1", "ctrl+c"])
        assert result.exit_code != 0
        assert "--hold-duration must be >= 0" in result.output

    def test_hold_duration_negative_json(self, runner):
        result = runner.invoke(main, ["hotkey", "--hold-duration", "-1", "ctrl+c", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "--hold-duration must be >= 0" in data["error"]["message"]

    def test_hold_duration_zero_allowed(self, runner):
        """Zero hold duration should be valid (instant press/release)."""
        result = runner.invoke(main, ["hotkey", "--hold-duration", "0", "ctrl+c"])
        # Should not fail validation (may fail on backend since no Windows, but not INVALID_INPUT)
        if result.exit_code != 0:
            assert "--hold-duration must be >= 0" not in (result.output or "")


class TestBug045DiffIntervalValidation:
    """BUG-045: diff --interval should validate > 0."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_diff_interval_negative(self, runner):
        result = runner.invoke(main, ["diff", "--window", "Notepad", "--interval", "-1"])
        assert result.exit_code != 0
        assert "--interval must be > 0" in result.output or "error" in result.output.lower()

    def test_diff_interval_zero(self, runner):
        result = runner.invoke(main, ["diff", "--window", "Notepad", "--interval", "0"])
        assert result.exit_code != 0
        assert "--interval must be > 0" in result.output or "error" in result.output.lower()

    def test_diff_interval_negative_json(self, runner):
        result = runner.invoke(main, ["diff", "--window", "Notepad", "--interval", "-1", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        assert "--interval must be > 0" in data["error"]["message"]

    def test_diff_interval_zero_json(self, runner):
        result = runner.invoke(main, ["diff", "--window", "Notepad", "--interval", "0", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
