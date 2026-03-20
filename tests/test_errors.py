"""Tests for naturo.errors — error framework, codes, JSON formatting."""
import pytest
from naturo.errors import (
    NaturoError, ErrorCode, ErrorCategory,
    AppNotFoundError, WindowNotFoundError, ElementNotFoundError,
    MenuNotFoundError, SnapshotNotFoundError, TimeoutError,
    CaptureFailedError, InteractionFailedError, InvalidInputError,
    InvalidCoordinatesError, PermissionDeniedError, FileIOError,
    AIProviderUnavailableError, AIAnalysisFailedError,
)


class TestErrorCode:
    def test_all_codes_are_strings(self):
        codes = [v for k, v in vars(ErrorCode).items() if not k.startswith("_")]
        assert all(isinstance(c, str) for c in codes)

    def test_peekaboo_standard_codes_present(self):
        expected = [
            "PERMISSION_DENIED", "APP_NOT_FOUND", "WINDOW_NOT_FOUND",
            "ELEMENT_NOT_FOUND", "MENU_NOT_FOUND", "SNAPSHOT_NOT_FOUND",
            "FILE_NOT_FOUND", "CAPTURE_FAILED", "INTERACTION_FAILED",
            "TIMEOUT", "CANCELLED", "INVALID_INPUT", "INVALID_COORDINATES",
            "FILE_IO_ERROR", "UNKNOWN_ERROR",
            "AI_PROVIDER_UNAVAILABLE", "AI_ANALYSIS_FAILED",
        ]
        for code in expected:
            assert hasattr(ErrorCode, code), f"Missing ErrorCode.{code}"
            assert getattr(ErrorCode, code) == code


class TestErrorCategory:
    def test_categories_are_strings(self):
        cats = [v for k, v in vars(ErrorCategory).items() if not k.startswith("_")]
        assert all(isinstance(c, str) for c in cats)

    def test_expected_categories(self):
        expected = ["permissions", "automation", "configuration", "ai", "io",
                     "network", "session", "validation", "unknown"]
        for cat in expected:
            assert cat in [v for k, v in vars(ErrorCategory).items() if not k.startswith("_")]


class TestNaturoError:
    def test_basic_creation(self):
        err = NaturoError("Something broke")
        assert str(err) == "Something broke"
        assert err.message == "Something broke"
        assert err.code == ErrorCode.UNKNOWN_ERROR
        assert err.category == ErrorCategory.UNKNOWN
        assert err.context == {}
        assert err.suggested_action is None
        assert err.is_recoverable is False

    def test_custom_creation(self):
        err = NaturoError(
            "Custom error", code="CUSTOM", category="test",
            context={"key": "val"}, suggested_action="Try again",
            is_recoverable=True,
        )
        assert err.code == "CUSTOM"
        assert err.category == "test"
        assert err.context == {"key": "val"}
        assert err.suggested_action == "Try again"
        assert err.is_recoverable is True

    def test_to_dict(self):
        err = NaturoError("test", code="TEST", category="cat", context={"a": 1})
        d = err.to_dict()
        assert d["code"] == "TEST"
        assert d["message"] == "test"
        assert d["category"] == "cat"
        assert d["context"] == {"a": 1}
        assert d["suggested_action"] is None
        assert d["recoverable"] is False

    def test_to_json_response(self):
        err = NaturoError("test")
        resp = err.to_json_response()
        assert resp["success"] is False
        assert "error" in resp
        assert resp["error"]["code"] == ErrorCode.UNKNOWN_ERROR

    def test_repr(self):
        err = NaturoError("test", code="TEST")
        assert "NaturoError" in repr(err)
        assert "TEST" in repr(err)

    def test_is_exception(self):
        err = NaturoError("test")
        assert isinstance(err, Exception)
        with pytest.raises(NaturoError):
            raise err


class TestSpecificErrors:
    def test_app_not_found(self):
        err = AppNotFoundError("Notepad")
        assert err.code == ErrorCode.APP_NOT_FOUND
        assert err.category == ErrorCategory.AUTOMATION
        assert "Notepad" in err.message
        assert err.context["app"] == "Notepad"

    def test_window_not_found(self):
        err = WindowNotFoundError("My Window")
        assert err.code == ErrorCode.WINDOW_NOT_FOUND
        assert "My Window" in err.message
        assert err.context["window_title"] == "My Window"

    def test_element_not_found(self):
        err = ElementNotFoundError("Button:Save")
        assert err.code == ErrorCode.ELEMENT_NOT_FOUND
        assert "Button:Save" in err.message
        assert err.context["selector"] == "Button:Save"

    def test_menu_not_found(self):
        err = MenuNotFoundError("File > Save As")
        assert err.code == ErrorCode.MENU_NOT_FOUND
        assert err.context["menu_path"] == "File > Save As"

    def test_snapshot_not_found(self):
        err = SnapshotNotFoundError("snap-123")
        assert err.code == ErrorCode.SNAPSHOT_NOT_FOUND
        assert err.category == ErrorCategory.SESSION
        assert err.context["snapshot_id"] == "snap-123"

    def test_timeout_error(self):
        err = TimeoutError("Timed out", timeout=5.0)
        assert err.code == ErrorCode.TIMEOUT
        assert err.is_recoverable is True
        assert err.context["timeout"] == 5.0

    def test_timeout_error_default_message(self):
        err = TimeoutError()
        assert "timed out" in err.message.lower()

    def test_capture_failed(self):
        err = CaptureFailedError("Screen capture failed")
        assert err.code == ErrorCode.CAPTURE_FAILED
        assert err.is_recoverable is True

    def test_interaction_failed(self):
        err = InteractionFailedError()
        assert err.code == ErrorCode.INTERACTION_FAILED
        assert err.is_recoverable is True

    def test_invalid_input(self):
        err = InvalidInputError("Bad selector")
        assert err.code == ErrorCode.INVALID_INPUT
        assert err.category == ErrorCategory.VALIDATION

    def test_invalid_coordinates(self):
        err = InvalidCoordinatesError(x=-1, y=-1)
        assert err.code == ErrorCode.INVALID_COORDINATES
        assert err.context["x"] == -1
        assert err.context["y"] == -1

    def test_permission_denied(self):
        err = PermissionDeniedError()
        assert err.code == ErrorCode.PERMISSION_DENIED
        assert err.category == ErrorCategory.PERMISSIONS
        assert err.suggested_action is not None

    def test_file_io_error(self):
        err = FileIOError("Cannot write", path="/tmp/test")
        assert err.code == ErrorCode.FILE_IO_ERROR
        assert err.context["path"] == "/tmp/test"
        assert err.is_recoverable is True

    def test_ai_provider_unavailable(self):
        err = AIProviderUnavailableError("openai")
        assert err.code == ErrorCode.AI_PROVIDER_UNAVAILABLE
        assert err.context["provider"] == "openai"
        assert err.is_recoverable is True

    def test_ai_analysis_failed(self):
        err = AIAnalysisFailedError("Model returned garbage")
        assert err.code == ErrorCode.AI_ANALYSIS_FAILED
        assert err.category == ErrorCategory.AI
        assert err.is_recoverable is True

    def test_all_subclasses_are_naturo_error(self):
        subclasses = [
            AppNotFoundError("x"), WindowNotFoundError("x"),
            ElementNotFoundError("x"), MenuNotFoundError("x"),
            SnapshotNotFoundError("x"), TimeoutError(),
            CaptureFailedError(), InteractionFailedError(),
            InvalidInputError(), InvalidCoordinatesError(),
            PermissionDeniedError(), FileIOError(),
            AIProviderUnavailableError(), AIAnalysisFailedError(),
        ]
        for err in subclasses:
            assert isinstance(err, NaturoError)
            assert isinstance(err, Exception)
