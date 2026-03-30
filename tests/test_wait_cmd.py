"""Tests for naturo.cli.wait_cmd — wait duration, element, window, gone."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.wait_cmd import wait


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_wait_result():
    """Build a mock WaitResult."""
    result = MagicMock()
    result.found = True
    result.wait_time = 1.5
    result.warnings = []
    result.element = None
    return result


# ---------------------------------------------------------------------------
# Duration mode
# ---------------------------------------------------------------------------

class TestWaitDuration:
    """Tests for 'naturo wait <seconds>' duration mode."""

    @patch("naturo.cli.wait_cmd.time.sleep")
    def test_duration(self, mock_sleep, runner):
        result = runner.invoke(wait, ["0.01"])
        assert result.exit_code == 0
        assert "Waited" in result.output
        mock_sleep.assert_called_once_with(0.01)

    @patch("naturo.cli.wait_cmd.time.sleep")
    def test_duration_json(self, mock_sleep, runner):
        result = runner.invoke(wait, ["0.5", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["mode"] == "duration"
        assert data["wait_time"] == 0.5

    def test_negative_duration(self, runner):
        result = runner.invoke(wait, ["--", "-1"])
        assert result.exit_code != 0
        assert "must be >= 0" in result.output or "Error" in result.output

    def test_negative_duration_json(self, runner):
        result = runner.invoke(wait, ["--json", "--", "-1"])
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output

    def test_duration_with_condition(self, runner):
        """Duration + --element is an error."""
        result = runner.invoke(wait, ["3", "--element", "Button:OK"])
        assert result.exit_code != 0
        assert "Cannot combine" in result.output or "Error" in result.output

    def test_duration_with_condition_json(self, runner):
        result = runner.invoke(wait, ["3", "--element", "Button:OK", "--json"])
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output


# ---------------------------------------------------------------------------
# No arguments
# ---------------------------------------------------------------------------

class TestWaitNoArgs:
    def test_no_args(self, runner):
        result = runner.invoke(wait, [])
        assert result.exit_code != 0
        assert "Specify" in result.output or "Error" in result.output

    def test_no_args_json(self, runner):
        result = runner.invoke(wait, ["--json"])
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestWaitValidation:
    def test_negative_timeout(self, runner):
        result = runner.invoke(wait, ["--element", "Button:OK", "--timeout", "-1"])
        assert result.exit_code != 0
        assert "timeout" in result.output.lower() or "Error" in result.output

    def test_zero_interval(self, runner):
        result = runner.invoke(wait, ["--element", "Button:OK", "--interval", "0"])
        assert result.exit_code != 0
        assert "interval" in result.output.lower() or "Error" in result.output

    def test_negative_interval(self, runner):
        result = runner.invoke(wait, ["--element", "Button:OK", "--interval", "-0.5"])
        assert result.exit_code != 0

    def test_negative_timeout_json(self, runner):
        result = runner.invoke(wait, ["--element", "B:OK", "--timeout", "-1", "--json"])
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output

    def test_zero_interval_json(self, runner):
        result = runner.invoke(wait, ["--element", "B:OK", "--interval", "0", "--json"])
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output


# ---------------------------------------------------------------------------
# Wait for element
# ---------------------------------------------------------------------------

class TestWaitForElement:
    @patch("naturo.wait.wait_for_element")
    def test_element_found(self, mock_wfe, runner, mock_wait_result):
        mock_wfe.return_value = mock_wait_result
        result = runner.invoke(wait, ["--element", "Button:Save", "--timeout", "1"])
        assert result.exit_code == 0
        assert "Found element" in result.output
        mock_wfe.assert_called_once_with(
            selector="Button:Save", timeout=1.0, poll_interval=0.1,
            window_title=None, hwnd=None,
        )

    @patch("naturo.wait.wait_for_element")
    def test_element_not_found(self, mock_wfe, runner):
        result_obj = MagicMock()
        result_obj.found = False
        result_obj.wait_time = 10.0
        result_obj.warnings = []
        result_obj.element = None
        mock_wfe.return_value = result_obj
        result = runner.invoke(wait, ["--element", "Button:Missing", "--timeout", "1"])
        assert result.exit_code != 0
        assert "Timeout" in result.output

    @patch("naturo.wait.wait_for_element")
    def test_element_json_found(self, mock_wfe, runner, mock_wait_result):
        elem = MagicMock()
        elem.id = "e1"
        elem.role = "Button"
        elem.name = "Save"
        elem.value = ""
        elem.x = 100
        elem.y = 200
        elem.width = 80
        elem.height = 30
        mock_wait_result.element = elem
        mock_wfe.return_value = mock_wait_result
        result = runner.invoke(wait, ["--element", "Button:Save", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["element"]["role"] == "Button"

    @patch("naturo.wait.wait_for_element")
    def test_element_json_not_found(self, mock_wfe, runner):
        result_obj = MagicMock()
        result_obj.found = False
        result_obj.wait_time = 10.0
        result_obj.warnings = []
        result_obj.element = None
        mock_wfe.return_value = result_obj
        result = runner.invoke(wait, ["--element", "X", "--json", "--timeout", "1"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["found"] is False

    @patch("naturo.wait.wait_for_element")
    def test_element_with_app_becomes_window_title(self, mock_wfe, runner, mock_wait_result):
        """--app without --window should set window_title from app."""
        mock_wfe.return_value = mock_wait_result
        result = runner.invoke(wait, ["--element", "Button:OK", "--app", "notepad"])
        assert result.exit_code == 0
        mock_wfe.assert_called_once_with(
            selector="Button:OK", timeout=10.0, poll_interval=0.1,
            window_title="notepad", hwnd=None,
        )

    @patch("naturo.wait.wait_for_element")
    def test_element_naturo_error(self, mock_wfe, runner):
        from naturo.errors import NaturoError
        mock_wfe.side_effect = NaturoError("TIMEOUT", "Element not found within timeout")
        result = runner.invoke(wait, ["--element", "B:X", "--timeout", "1"])
        assert result.exit_code != 0
        assert "Error" in result.output

    @patch("naturo.wait.wait_for_element")
    def test_element_generic_error(self, mock_wfe, runner):
        mock_wfe.side_effect = RuntimeError("unexpected")
        result = runner.invoke(wait, ["--element", "B:X"])
        assert result.exit_code != 0

    @patch("naturo.wait.wait_for_element")
    def test_element_with_warnings(self, mock_wfe, runner):
        result_obj = MagicMock()
        result_obj.found = True
        result_obj.wait_time = 2.0
        result_obj.warnings = ["Slow response detected"]
        result_obj.element = None
        mock_wfe.return_value = result_obj
        result = runner.invoke(wait, ["--element", "B:OK"])
        assert result.exit_code == 0
        assert "Warning" in result.output


# ---------------------------------------------------------------------------
# Wait for window
# ---------------------------------------------------------------------------

class TestWaitForWindow:
    @patch("naturo.wait.wait_for_window")
    def test_window_found(self, mock_wfw, runner, mock_wait_result):
        mock_wfw.return_value = mock_wait_result
        result = runner.invoke(wait, ["--window", "Notepad"])
        assert result.exit_code == 0
        assert "appeared" in result.output
        mock_wfw.assert_called_once_with(title="Notepad", timeout=10.0, poll_interval=0.1)

    @patch("naturo.wait.wait_for_window")
    def test_window_json(self, mock_wfw, runner, mock_wait_result):
        mock_wfw.return_value = mock_wait_result
        result = runner.invoke(wait, ["--window", "Notepad", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True


# ---------------------------------------------------------------------------
# Wait gone
# ---------------------------------------------------------------------------

class TestWaitGone:
    @patch("naturo.wait.wait_until_gone")
    def test_gone(self, mock_wug, runner, mock_wait_result):
        mock_wug.return_value = mock_wait_result
        result = runner.invoke(wait, ["--gone", "Dialog:Loading"])
        assert result.exit_code == 0
        assert "disappeared" in result.output
        mock_wug.assert_called_once_with(
            selector="Dialog:Loading", timeout=10.0, poll_interval=0.1,
            window_title=None, hwnd=None,
        )

    @patch("naturo.wait.wait_until_gone")
    def test_gone_json(self, mock_wug, runner, mock_wait_result):
        mock_wug.return_value = mock_wait_result
        result = runner.invoke(wait, ["--gone", "Dialog:Loading", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

class TestWaitHelp:
    def test_help(self, runner):
        result = runner.invoke(wait, ["--help"])
        assert result.exit_code == 0
        assert "--element" in result.output
        assert "--window" in result.output
        assert "--gone" in result.output
        assert "--timeout" in result.output
