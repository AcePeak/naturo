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

    # (#1164) Upper-bound / non-finite duration must yield a structured
    # validation error, never a raw OverflowError/ValueError traceback — and
    # under -j a JSON envelope must still be emitted (the broken-contract bug).
    def test_huge_duration_rejected(self, runner):
        """A duration past the platform sleep limit is rejected, not crashed."""
        result = runner.invoke(wait, ["1e10"])
        assert result.exit_code != 0
        assert result.exception is None or isinstance(result.exception, SystemExit)
        assert "Error" in result.output
        assert "Traceback" not in result.output

    def test_huge_duration_rejected_json(self, runner):
        """Under -j the huge-duration error is a valid INVALID_INPUT envelope."""
        result = runner.invoke(wait, ["1e10", "--json"])
        assert result.exit_code != 0
        assert result.exception is None or isinstance(result.exception, SystemExit)
        assert "Traceback" not in result.output
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"
        assert data["error"]["category"] == "validation"

    def test_infinite_duration_rejected_json(self, runner):
        result = runner.invoke(wait, ["inf", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_nan_duration_rejected_json(self, runner):
        result = runner.invoke(wait, ["nan", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"


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
# Envelope consistency (#895)
# ---------------------------------------------------------------------------

# The single canonical success-envelope key set every ``wait`` sub-mode must
# emit so a ``-j`` consumer never has to know which flags were passed.
CANONICAL_WAIT_KEYS = {"success", "mode", "wait_time", "found", "warnings"}


class TestWaitEnvelopeConsistency:
    """All four sub-modes share one canonical ``-j`` success envelope (#895).

    Duration mode previously emitted ``{success, mode, wait_time}`` while the
    predicate modes emitted ``{success, found, wait_time, warnings}`` — no shared
    shape and no ``mode`` discriminator on the predicate path. After the fix every
    sub-mode carries ``{success, mode, wait_time, found, warnings}``, with the
    predicate-only ``found`` present-but-null in duration mode.
    """

    @patch("naturo.cli.wait_cmd.time.sleep")
    def test_duration_has_canonical_keys(self, mock_sleep, runner):
        result = runner.invoke(wait, ["0.5", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert set(data) >= CANONICAL_WAIT_KEYS
        assert data["mode"] == "duration"
        assert data["found"] is None
        assert data["warnings"] == []

    @patch("naturo.wait.wait_for_element")
    def test_element_has_mode_discriminator(self, mock_wfe, runner, mock_wait_result):
        mock_wfe.return_value = mock_wait_result
        result = runner.invoke(wait, ["--element", "Button:Save", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert set(data) >= CANONICAL_WAIT_KEYS
        assert data["mode"] == "element"
        assert data["found"] is True

    @patch("naturo.wait.wait_for_window")
    def test_window_has_mode_discriminator(self, mock_wfw, runner, mock_wait_result):
        mock_wfw.return_value = mock_wait_result
        result = runner.invoke(wait, ["--window", "Notepad", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert set(data) >= CANONICAL_WAIT_KEYS
        assert data["mode"] == "window"

    @patch("naturo.wait.wait_until_gone")
    def test_gone_has_mode_discriminator(self, mock_wug, runner, mock_wait_result):
        mock_wug.return_value = mock_wait_result
        result = runner.invoke(wait, ["--gone", "Dialog:Loading", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert set(data) >= CANONICAL_WAIT_KEYS
        assert data["mode"] == "gone"

    @patch("naturo.wait.wait_for_element")
    def test_not_found_keeps_canonical_keys(self, mock_wfe, runner):
        result_obj = MagicMock()
        result_obj.found = False
        result_obj.wait_time = 1.0
        result_obj.warnings = []
        result_obj.element = None
        mock_wfe.return_value = result_obj
        result = runner.invoke(wait, ["--element", "X", "--json", "--timeout", "1"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert set(data) >= CANONICAL_WAIT_KEYS
        assert data["mode"] == "element"
        assert data["found"] is False

    @patch("naturo.cli.wait_cmd.time.sleep")
    @patch("naturo.wait.wait_for_element")
    def test_duration_and_predicate_share_key_set(
        self, mock_wfe, mock_sleep, runner, mock_wait_result
    ):
        """The duration and predicate envelopes expose the same canonical keys."""
        duration = json.loads(runner.invoke(wait, ["0.5", "--json"]).output)
        mock_wfe.return_value = mock_wait_result
        predicate = json.loads(
            runner.invoke(wait, ["--element", "Button:Save", "--json"]).output
        )
        assert CANONICAL_WAIT_KEYS <= set(duration)
        assert CANONICAL_WAIT_KEYS <= set(predicate)
        assert CANONICAL_WAIT_KEYS <= (set(duration) & set(predicate))


# ---------------------------------------------------------------------------
# Timeout-failure error envelope (#1089)
# ---------------------------------------------------------------------------

# The six canonical keys, in order, that every ``-j`` error object must carry —
# identical to naturo.errors.NaturoError.to_dict() and json_error's object (#884).
_CANONICAL_ERROR_KEYS = [
    "code", "message", "category", "context", "suggested_action", "recoverable",
]


class TestWaitTimeoutErrorEnvelope:
    """Predicate-mode timeout (-j) carries the standard ``error`` block (#1089).

    A ``wait`` predicate timeout sets ``success:false`` and exits 1 *without
    raising*, so it never reaches the ``json_error`` path the rest of the CLI
    uses. Before #1089 the ``-j`` timeout envelope therefore omitted the ``error``
    object entirely — every other failing command, and ``wait``'s own validation
    failures, emit ``{code, message, category, recoverable, ...}``. These tests
    pin that the timeout path now attaches the canonical block while keeping the
    #895 success-shape keys intact.

    The desktop pre-flight gate is mocked out so the forced timeout path reflects
    the *code*, not the runner's desktop state (hermeticity, cf. #1068).
    """

    @staticmethod
    def _timeout_result(wait_time: float = 1.0):
        result = MagicMock()
        result.found = False
        result.wait_time = wait_time
        result.warnings = []
        result.element = None
        return result

    @patch("naturo.cli.core._common._enforce_desktop_session", lambda *a, **k: None)
    @patch("naturo.wait.wait_for_element")
    def test_element_timeout_attaches_canonical_error(self, mock_wfe, runner):
        mock_wfe.return_value = self._timeout_result(1.0)
        result = runner.invoke(
            wait, ["--element", "Button:ZZZNoExist", "--app", "Notepad",
                   "--timeout", "1", "--json"],
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        # #895 success-shape keys stay intact.
        assert set(data) >= CANONICAL_WAIT_KEYS
        assert data["success"] is False
        assert data["found"] is False
        assert data["mode"] == "element"
        # #1089 error block: canonical six keys, in order, with resolved taxonomy.
        error = data["error"]
        assert list(error.keys()) == _CANONICAL_ERROR_KEYS
        assert error["code"] == "TIMEOUT"
        assert error["category"] == "automation"
        assert error["recoverable"] is True
        assert error["suggested_action"]
        assert "Button:ZZZNoExist" in error["message"]
        assert "1.0s" in error["message"]

    @patch("naturo.cli.core._common._enforce_desktop_session", lambda *a, **k: None)
    @patch("naturo.wait.wait_for_window")
    def test_window_timeout_attaches_canonical_error(self, mock_wfw, runner):
        mock_wfw.return_value = self._timeout_result(2.0)
        result = runner.invoke(wait, ["--window", "ZZZNoWindow", "--timeout", "2", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["mode"] == "window"
        error = data["error"]
        assert list(error.keys()) == _CANONICAL_ERROR_KEYS
        assert error["code"] == "TIMEOUT"
        assert error["category"] == "automation"
        assert "ZZZNoWindow" in error["message"]

    @patch("naturo.cli.core._common._enforce_desktop_session", lambda *a, **k: None)
    @patch("naturo.wait.wait_until_gone")
    def test_gone_timeout_attaches_canonical_error(self, mock_wug, runner):
        mock_wug.return_value = self._timeout_result(1.0)
        result = runner.invoke(wait, ["--gone", "Dialog:Loading", "--timeout", "1", "--json"])
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["mode"] == "gone"
        error = data["error"]
        assert list(error.keys()) == _CANONICAL_ERROR_KEYS
        assert error["code"] == "TIMEOUT"
        assert "Dialog:Loading" in error["message"]

    @patch("naturo.cli.core._common._enforce_desktop_session", lambda *a, **k: None)
    @patch("naturo.wait.wait_for_element")
    def test_found_success_has_no_error_block(self, mock_wfe, runner, mock_wait_result):
        """The error block is attached only on failure — success stays clean."""
        mock_wfe.return_value = mock_wait_result
        result = runner.invoke(wait, ["--element", "Button:Save", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert "error" not in data

    @patch("naturo.cli.core._common._enforce_desktop_session", lambda *a, **k: None)
    @patch("naturo.wait.wait_for_element")
    def test_human_path_timeout_message_matches_error_message(self, mock_wfe, runner):
        """The -j error message mirrors the human-path ``Error: Timeout ...`` text."""
        mock_wfe.return_value = self._timeout_result(1.0)
        human = runner.invoke(wait, ["--element", "Button:ZZZNoExist", "--timeout", "1"])
        mock_wfe.return_value = self._timeout_result(1.0)
        js = runner.invoke(wait, ["--element", "Button:ZZZNoExist", "--timeout", "1", "--json"])
        # Human path: "Error: Timeout after 1.0s waiting for 'Button:ZZZNoExist'"
        assert "Timeout after 1.0s waiting for 'Button:ZZZNoExist'" in human.output
        assert json.loads(js.output)["error"]["message"] == \
            "Timeout after 1.0s waiting for 'Button:ZZZNoExist'"


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
