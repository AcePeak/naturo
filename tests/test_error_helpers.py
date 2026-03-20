"""Tests for CLI error helper functions (Phase 4.7 — Agent-friendly Errors)."""

import json
import pytest
from unittest.mock import patch

from naturo.cli.error_helpers import (
    json_error,
    json_error_from_exception,
    emit_error,
    emit_exception_error,
    _RECOVERY_HINTS,
)
from naturo.errors import (
    NaturoError,
    WindowNotFoundError,
    AppNotFoundError,
    ElementNotFoundError,
    TimeoutError,
    InvalidInputError,
    CaptureFailedError,
    AIProviderUnavailableError,
)


class TestJsonError:
    """Test json_error() function."""

    def test_basic_error_with_known_code(self):
        """Known error codes get recovery hints automatically."""
        result = json.loads(json_error("WINDOW_NOT_FOUND", "Window not found: Notepad"))
        assert result["success"] is False
        assert result["error"]["code"] == "WINDOW_NOT_FOUND"
        assert result["error"]["message"] == "Window not found: Notepad"
        assert "suggested_action" in result["error"]
        assert result["error"]["recoverable"] is True

    def test_basic_error_with_unknown_code(self):
        """Unknown error codes get no recovery hints by default."""
        result = json.loads(json_error("CUSTOM_ERROR", "Something went wrong"))
        assert result["success"] is False
        assert result["error"]["code"] == "CUSTOM_ERROR"
        assert result["error"]["message"] == "Something went wrong"
        assert "suggested_action" not in result["error"]
        assert "recoverable" not in result["error"]

    def test_explicit_suggested_action_overrides_default(self):
        """Explicit suggested_action overrides the registry default."""
        result = json.loads(json_error(
            "WINDOW_NOT_FOUND",
            "Window not found",
            suggested_action="Try 'naturo window focus --app Chrome'",
        ))
        assert result["error"]["suggested_action"] == "Try 'naturo window focus --app Chrome'"

    def test_explicit_recoverable_overrides_default(self):
        """Explicit recoverable overrides the registry default."""
        result = json.loads(json_error(
            "WINDOW_NOT_FOUND",
            "Window not found",
            recoverable=False,
        ))
        assert "recoverable" not in result["error"]

    def test_extra_fields_included(self):
        """Extra fields are included in the error object."""
        result = json.loads(json_error(
            "INVALID_INPUT",
            "Bad value",
            extra={"parameter": "--depth", "valid_range": "1-10"},
        ))
        assert result["error"]["parameter"] == "--depth"
        assert result["error"]["valid_range"] == "1-10"

    def test_all_known_codes_have_hints(self):
        """All registered error codes produce suggested_action."""
        for code, (action, recoverable) in _RECOVERY_HINTS.items():
            result = json.loads(json_error(code, f"Test error for {code}"))
            assert "suggested_action" in result["error"], f"Missing hint for {code}"
            assert result["error"]["suggested_action"] == action

    def test_invalid_input_not_recoverable(self):
        """INVALID_INPUT errors are not marked as recoverable."""
        result = json.loads(json_error("INVALID_INPUT", "Bad value"))
        assert "recoverable" not in result["error"]


class TestJsonErrorFromException:
    """Test json_error_from_exception() function."""

    def test_naturo_error_preserves_all_fields(self):
        """NaturoError instances preserve code, message, suggested_action, recoverable."""
        exc = WindowNotFoundError("Notepad")
        result = json.loads(json_error_from_exception(exc))
        assert result["success"] is False
        assert result["error"]["code"] == "WINDOW_NOT_FOUND"
        assert "Window not found: Notepad" in result["error"]["message"]
        assert "suggested_action" in result["error"]
        assert result["error"]["recoverable"] is True

    def test_naturo_error_with_context(self):
        """NaturoError with context preserves it."""
        exc = AppNotFoundError("notepad")
        result = json.loads(json_error_from_exception(exc))
        assert result["error"]["context"]["app"] == "notepad"

    def test_element_not_found_error(self):
        """ElementNotFoundError includes step-by-step recovery hint."""
        exc = ElementNotFoundError("Button:Save")
        result = json.loads(json_error_from_exception(exc))
        assert "naturo see" in result["error"]["suggested_action"]
        assert "naturo wait" in result["error"]["suggested_action"]

    def test_timeout_error(self):
        """TimeoutError includes recovery hint."""
        exc = TimeoutError(timeout=5.0)
        result = json.loads(json_error_from_exception(exc))
        assert result["error"]["code"] == "TIMEOUT"
        assert "timeout" in result["error"]["suggested_action"].lower()

    def test_plain_exception_becomes_unknown_error(self):
        """Plain Python exceptions become UNKNOWN_ERROR."""
        exc = ValueError("something broke")
        result = json.loads(json_error_from_exception(exc))
        assert result["error"]["code"] == "UNKNOWN_ERROR"
        assert result["error"]["message"] == "something broke"

    def test_ai_provider_unavailable(self):
        """AIProviderUnavailableError includes provider context."""
        exc = AIProviderUnavailableError("anthropic")
        result = json.loads(json_error_from_exception(exc))
        assert result["error"]["code"] == "AI_PROVIDER_UNAVAILABLE"
        assert result["error"]["context"]["provider"] == "anthropic"


class TestEmitError:
    """Test emit_error() function."""

    def test_json_mode_outputs_json(self, capsys):
        """JSON mode outputs structured error with recovery hints."""
        with pytest.raises(SystemExit) as exc_info:
            emit_error("WINDOW_NOT_FOUND", "Window not found", json_output=True)
        assert exc_info.value.code == 1
        output = capsys.readouterr().out
        result = json.loads(output)
        assert result["success"] is False
        assert result["error"]["code"] == "WINDOW_NOT_FOUND"
        assert "suggested_action" in result["error"]

    def test_text_mode_outputs_stderr(self, capsys):
        """Text mode outputs to stderr."""
        with pytest.raises(SystemExit):
            emit_error("WINDOW_NOT_FOUND", "Window not found", json_output=False)
        output = capsys.readouterr().err
        assert "Error: Window not found" in output

    def test_custom_exit_code(self, capsys):
        """Custom exit code is respected."""
        with pytest.raises(SystemExit) as exc_info:
            emit_error("INVALID_INPUT", "Bad input", json_output=True, exit_code=2)
        assert exc_info.value.code == 2


class TestEmitExceptionError:
    """Test emit_exception_error() function."""

    def test_naturo_error_json_mode(self, capsys):
        """NaturoError in JSON mode outputs full structured response."""
        exc = WindowNotFoundError("Chrome")
        with pytest.raises(SystemExit):
            emit_exception_error(exc, json_output=True)
        output = capsys.readouterr().out
        result = json.loads(output)
        assert result["error"]["code"] == "WINDOW_NOT_FOUND"
        assert "suggested_action" in result["error"]
        assert result["error"]["recoverable"] is True

    def test_naturo_error_text_mode(self, capsys):
        """NaturoError in text mode outputs message to stderr."""
        exc = AppNotFoundError("notepad")
        with pytest.raises(SystemExit):
            emit_exception_error(exc, json_output=False)
        output = capsys.readouterr().err
        assert "Application not found: notepad" in output

    def test_plain_exception_json_mode(self, capsys):
        """Plain exception in JSON mode uses fallback code."""
        exc = RuntimeError("disk full")
        with pytest.raises(SystemExit):
            emit_exception_error(exc, json_output=True, fallback_code="IO_ERROR")
        output = capsys.readouterr().out
        result = json.loads(output)
        assert result["error"]["code"] == "IO_ERROR"
        assert result["error"]["message"] == "disk full"

    def test_plain_exception_text_mode(self, capsys):
        """Plain exception in text mode outputs to stderr."""
        exc = RuntimeError("disk full")
        with pytest.raises(SystemExit):
            emit_exception_error(exc, json_output=False)
        output = capsys.readouterr().err
        assert "Error: disk full" in output


class TestRecoveryHintCoverage:
    """Verify recovery hint quality and coverage."""

    def test_all_hints_are_actionable(self):
        """All recovery hints contain actionable commands or instructions."""
        for code, (action, _) in _RECOVERY_HINTS.items():
            assert len(action) > 20, f"Hint for {code} too short to be useful"
            # Should reference a naturo command or a clear action
            has_command = "naturo" in action.lower() or "try" in action.lower() or "check" in action.lower() or "run" in action.lower() or "set" in action.lower()
            assert has_command, f"Hint for {code} lacks actionable guidance: {action}"

    def test_recoverable_errors_are_sensible(self):
        """Only truly recoverable errors are marked as such."""
        # These should NOT be recoverable (user must change input)
        non_recoverable = {"INVALID_INPUT", "INVALID_COORDINATES", "FILE_NOT_FOUND",
                           "PLATFORM_ERROR", "NOT_IMPLEMENTED", "MISSING_DEPENDENCY",
                           "PERMISSION_DENIED", "SNAPSHOT_NOT_FOUND", "AI_PROVIDER_UNAVAILABLE"}
        for code in non_recoverable:
            if code in _RECOVERY_HINTS:
                _, recoverable = _RECOVERY_HINTS[code]
                assert not recoverable, f"{code} should not be recoverable"

        # These SHOULD be recoverable (transient or retryable)
        recoverable_codes = {"APP_NOT_FOUND", "WINDOW_NOT_FOUND", "ELEMENT_NOT_FOUND",
                             "TIMEOUT", "CAPTURE_ERROR", "CAPTURE_FAILED",
                             "WINDOW_OPERATION_FAILED", "PROCESS_NOT_FOUND"}
        for code in recoverable_codes:
            if code in _RECOVERY_HINTS:
                _, recoverable = _RECOVERY_HINTS[code]
                assert recoverable, f"{code} should be recoverable"
