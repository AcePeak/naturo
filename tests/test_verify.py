"""Tests for post-action verification engine (naturo/verify.py).

Issue #231 — naturo must never lie about success.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from naturo.verify import (
    VerificationResult,
    VerifyStatus,
    capture_before_state,
    skip_result,
    unknown_result,
    verify_click,
    verify_press,
    verify_type,
)


class TestVerifyStatus:
    """Test VerifyStatus enum and VerificationResult."""

    def test_verified_property_true(self):
        result = VerificationResult(status=VerifyStatus.VERIFIED)
        assert result.verified is True

    def test_verified_property_false(self):
        result = VerificationResult(status=VerifyStatus.FAILED)
        assert result.verified is False

    def test_verified_property_none_skipped(self):
        result = VerificationResult(status=VerifyStatus.SKIPPED)
        assert result.verified is None

    def test_verified_property_none_unknown(self):
        result = VerificationResult(status=VerifyStatus.UNKNOWN)
        assert result.verified is None

    def test_to_dict_verified(self):
        result = VerificationResult(
            status=VerifyStatus.VERIFIED,
            detail="Text confirmed",
            method="value_compare",
            elapsed_ms=42.5,
        )
        d = result.to_dict()
        assert d["verified"] is True
        assert d["verification_detail"] == "Text confirmed"
        assert d["verification_method"] == "value_compare"
        assert d["verification_ms"] == 42.5
        assert "verification_error" not in d

    def test_to_dict_failed(self):
        result = VerificationResult(
            status=VerifyStatus.FAILED,
            detail="Value unchanged",
            method="value_compare",
        )
        d = result.to_dict()
        assert d["verified"] is False
        assert d["verification_error"] == "Value unchanged"

    def test_to_dict_skipped(self):
        result = skip_result("test reason")
        d = result.to_dict()
        assert d["verified"] is None
        assert d["verification_detail"] == "test reason"

    def test_unknown_result(self):
        result = unknown_result("some error")
        assert result.status == VerifyStatus.UNKNOWN
        assert result.verified is None
        assert "some error" in result.detail


class TestVerifyType:
    """Test type action verification."""

    def test_verified_when_text_appears_in_value(self):
        """Value changed and contains typed text → VERIFIED."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "Hello World"}

        result = verify_type(
            backend,
            text="Hello",
            before_value="",
            settle_ms=0,
        )
        assert result.status == VerifyStatus.VERIFIED
        assert result.verified is True

    def test_failed_when_value_unchanged(self):
        """Value unchanged after typing → FAILED (silent failure)."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "original"}

        result = verify_type(
            backend,
            text="Hello",
            before_value="original",
            settle_ms=0,
        )
        assert result.status == VerifyStatus.FAILED
        assert result.verified is False
        assert "unchanged" in result.detail.lower()

    def test_verified_when_value_changed_but_text_not_found(self):
        """Value changed but doesn't contain exact text → still VERIFIED.

        The element might format/transform input (e.g., password fields).
        """
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "****"}

        result = verify_type(
            backend,
            text="password",
            before_value="",
            settle_ms=0,
        )
        assert result.status == VerifyStatus.VERIFIED

    def test_skipped_for_clipboard_only_paste(self):
        """Clipboard-only paste (no text) → SKIPPED."""
        backend = MagicMock()

        result = verify_type(
            backend,
            text=None,
            settle_ms=0,
        )
        assert result.status == VerifyStatus.SKIPPED

    def test_skipped_when_backend_lacks_get_element_value(self):
        """Non-Windows backend → SKIPPED."""
        backend = MagicMock(spec=[])  # No get_element_value

        result = verify_type(
            backend,
            text="Hello",
            settle_ms=0,
        )
        assert result.status == VerifyStatus.SKIPPED

    def test_unknown_when_element_not_found(self):
        """Element not found for value read → UNKNOWN."""
        backend = MagicMock()
        backend.get_element_value.return_value = None

        result = verify_type(
            backend,
            text="Hello",
            settle_ms=0,
        )
        assert result.status == VerifyStatus.UNKNOWN

    def test_unknown_when_get_value_raises(self):
        """Exception during value read → UNKNOWN."""
        backend = MagicMock()
        backend.get_element_value.side_effect = Exception("COM error")

        result = verify_type(
            backend,
            text="Hello",
            settle_ms=0,
        )
        assert result.status == VerifyStatus.UNKNOWN

    def test_unknown_when_no_before_value(self):
        """No before_value and text not in current value → UNKNOWN."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "something else"}

        result = verify_type(
            backend,
            text="Hello",
            before_value=None,
            settle_ms=0,
        )
        assert result.status == VerifyStatus.UNKNOWN

    def test_verified_when_no_before_but_text_found(self):
        """No before_value but typed text is in current value → VERIFIED."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "Hello World"}

        result = verify_type(
            backend,
            text="Hello",
            before_value=None,
            settle_ms=0,
        )
        assert result.status == VerifyStatus.VERIFIED

    def test_elapsed_ms_tracked(self):
        """Verification should track elapsed time."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "Hello"}

        result = verify_type(
            backend,
            text="Hello",
            before_value="",
            settle_ms=0,
        )
        assert result.elapsed_ms >= 0


class TestVerifyClick:
    """Test click action verification."""

    def test_verified_when_focus_changed(self):
        """Focus state changed after click → VERIFIED."""
        backend = MagicMock(spec=[])
        before_focus = {"foreground_hwnd": 100, "foreground_title": "Window A"}

        with patch("naturo.verify._capture_focus_state") as mock_capture:
            mock_capture.return_value = {
                "foreground_hwnd": 200,
                "foreground_title": "Window B",
            }
            result = verify_click(
                backend,
                before_focus=before_focus,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.VERIFIED

    def test_unknown_when_focus_unchanged(self):
        """Focus unchanged after click → UNKNOWN (not FAILED, to avoid false positives)."""
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100, "foreground_title": "Window A"}

        with patch("naturo.verify._capture_focus_state") as mock_capture:
            mock_capture.return_value = focus.copy()
            result = verify_click(
                backend,
                before_focus=focus,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN

    def test_unknown_when_no_before_focus(self):
        """No before_focus captured → UNKNOWN."""
        backend = MagicMock(spec=[])

        with patch("naturo.verify._capture_focus_state"):
            result = verify_click(
                backend,
                before_focus=None,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN

    def test_unknown_on_capture_error(self):
        """Focus capture raises → UNKNOWN."""
        backend = MagicMock(spec=[])

        with patch(
            "naturo.verify._capture_focus_state",
            side_effect=Exception("COM error"),
        ):
            result = verify_click(
                backend,
                before_focus={"foreground_hwnd": 100},
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN


class TestVerifyClickUiTextFallback:
    """Test #263: click verification falls back to UI text diff when focus unchanged."""

    def test_verified_when_ui_texts_changed(self):
        """Focus unchanged but UI element text changed → VERIFIED."""
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100, "foreground_title": "Calculator"}
        before_texts = {"uia:50033:CalculatorResults": "Display is 0"}
        after_texts = {"uia:50033:CalculatorResults": "Display is 7"}

        with patch("naturo.verify._capture_focus_state") as mock_focus, \
             patch("naturo.verify._capture_ui_texts") as mock_texts:
            mock_focus.return_value = focus.copy()
            mock_texts.return_value = after_texts
            result = verify_click(
                backend,
                before_focus=focus,
                before_ui_texts=before_texts,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.VERIFIED
        assert result.method == "ui_text_diff"
        assert "display updated" in result.detail.lower()

    def test_unknown_when_ui_texts_unchanged(self):
        """Focus unchanged and UI texts unchanged → UNKNOWN."""
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100, "foreground_title": "Calculator"}
        texts = {"uia:50033:CalculatorResults": "Display is 0"}

        with patch("naturo.verify._capture_focus_state") as mock_focus, \
             patch("naturo.verify._capture_ui_texts") as mock_texts:
            mock_focus.return_value = focus.copy()
            mock_texts.return_value = texts.copy()
            result = verify_click(
                backend,
                before_focus=focus,
                before_ui_texts=texts,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN

    def test_unknown_when_no_before_ui_texts(self):
        """No before_ui_texts provided → falls through to UNKNOWN."""
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100}

        with patch("naturo.verify._capture_focus_state") as mock_focus:
            mock_focus.return_value = focus.copy()
            result = verify_click(
                backend,
                before_focus=focus,
                before_ui_texts=None,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN

    def test_ui_text_capture_error_handled_gracefully(self):
        """UI text capture fails → falls through to UNKNOWN, no crash."""
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100}
        before_texts = {"some:element": "value"}

        with patch("naturo.verify._capture_focus_state") as mock_focus, \
             patch("naturo.verify._capture_ui_texts", side_effect=Exception("COM error")):
            mock_focus.return_value = focus.copy()
            result = verify_click(
                backend,
                before_focus=focus,
                before_ui_texts=before_texts,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN

    def test_focus_change_takes_priority_over_ui_texts(self):
        """Focus changed → VERIFIED via focus_check, ui_texts not consulted."""
        backend = MagicMock(spec=[])
        before_focus = {"foreground_hwnd": 100}
        before_texts = {"some:element": "value"}

        with patch("naturo.verify._capture_focus_state") as mock_focus:
            mock_focus.return_value = {"foreground_hwnd": 200}
            result = verify_click(
                backend,
                before_focus=before_focus,
                before_ui_texts=before_texts,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.VERIFIED
        assert result.method == "focus_check"


class TestCaptureBeforeStateUiTexts:
    """Test #263: capture_before_state includes UI texts for click actions."""

    def test_click_captures_ui_texts(self):
        """Before-state for click should capture UI element texts."""
        backend = MagicMock(spec=[])
        focus_data = {"foreground_hwnd": 123}
        ui_texts = {"uia:50004:CalculatorResults": "0"}

        with patch("naturo.verify._capture_focus_state", return_value=focus_data), \
             patch("naturo.verify._capture_ui_texts", return_value=ui_texts):
            state = capture_before_state(backend, action="click")

        assert state["focus"] == focus_data
        assert state["ui_texts"] == ui_texts

    def test_type_does_not_capture_ui_texts(self):
        """Before-state for type should NOT capture UI texts."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "text"}

        with patch("naturo.verify._capture_focus_state", return_value={}):
            state = capture_before_state(backend, action="type")

        assert "ui_texts" not in state

    def test_click_handles_ui_texts_error(self):
        """UI text capture failure → ui_texts=None, still works."""
        backend = MagicMock(spec=[])

        with patch("naturo.verify._capture_focus_state", return_value={}), \
             patch("naturo.verify._capture_ui_texts", side_effect=Exception("error")):
            state = capture_before_state(backend, action="click")

        assert state["ui_texts"] is None


class TestVerifyPress:
    """Test press action verification."""

    def test_verified_when_focus_changed(self):
        """Focus changed after press → VERIFIED."""
        backend = MagicMock(spec=[])
        before_focus = {"foreground_hwnd": 100}

        with patch("naturo.verify._capture_focus_state") as mock_capture:
            mock_capture.return_value = {"foreground_hwnd": 200}
            result = verify_press(
                backend,
                keys=("tab",),
                before_focus=before_focus,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.VERIFIED

    def test_unknown_for_nav_key_no_change(self):
        """Navigation key with no focus change → UNKNOWN."""
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100}

        with patch("naturo.verify._capture_focus_state") as mock_capture:
            mock_capture.return_value = focus.copy()
            result = verify_press(
                backend,
                keys=("tab",),
                before_focus=focus,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN

    def test_skipped_for_non_nav_key_no_change(self):
        """Non-navigation key with no focus change → SKIPPED (normal)."""
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100}

        with patch("naturo.verify._capture_focus_state") as mock_capture:
            mock_capture.return_value = focus.copy()
            result = verify_press(
                backend,
                keys=("a",),
                before_focus=focus,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.SKIPPED

    def test_unknown_when_no_before_focus(self):
        """No before_focus captured → UNKNOWN."""
        backend = MagicMock(spec=[])

        with patch("naturo.verify._capture_focus_state"):
            result = verify_press(
                backend,
                keys=("enter",),
                before_focus=None,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN


class TestCaptureBeforeState:
    """Test pre-action state capture."""

    def test_type_captures_value(self):
        """Before-state for type should capture element value."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "existing text"}

        with patch("naturo.verify._capture_focus_state", return_value={}):
            state = capture_before_state(backend, action="type")

        assert state["value"] == "existing text"
        assert "focus" in state

    def test_click_captures_focus(self):
        """Before-state for click should capture focus state."""
        backend = MagicMock(spec=[])
        focus_data = {"foreground_hwnd": 123}

        with patch("naturo.verify._capture_focus_state", return_value=focus_data), \
             patch("naturo.verify._capture_ui_texts", return_value={}):
            state = capture_before_state(backend, action="click")

        assert state["focus"] == focus_data
        assert "value" not in state

    def test_type_handles_value_error(self):
        """Value read failure → value=None, still captures focus."""
        backend = MagicMock()
        backend.get_element_value.side_effect = Exception("error")

        with patch("naturo.verify._capture_focus_state", return_value={}):
            state = capture_before_state(backend, action="type")

        assert state["value"] is None
        assert "focus" in state

    def test_focus_capture_failure_handled(self):
        """Focus capture failure → focus=None."""
        backend = MagicMock(spec=[])

        with patch(
            "naturo.verify._capture_focus_state",
            side_effect=Exception("error"),
        ), patch("naturo.verify._capture_ui_texts", return_value={}):
            state = capture_before_state(backend, action="click")

        assert state["focus"] is None


class TestVerificationIntegration:
    """Integration-style tests for the verification flow."""

    def test_full_type_verify_success_flow(self):
        """Simulate full type → verify flow: before="", after="Hello" → VERIFIED."""
        backend = MagicMock()
        # First call (before): return empty
        # Second call (after): return typed text
        backend.get_element_value.side_effect = [
            {"value": ""},
            {"value": "Hello World"},
        ]

        with patch("naturo.verify._capture_focus_state", return_value={}):
            before = capture_before_state(backend, action="type")

        result = verify_type(
            backend,
            text="Hello",
            before_value=before.get("value"),
            settle_ms=0,
        )
        assert result.verified is True

    def test_full_type_verify_failure_flow(self):
        """Simulate silent failure: value stays the same → FAILED."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "unchanged"}

        with patch("naturo.verify._capture_focus_state", return_value={}):
            before = capture_before_state(backend, action="type")

        result = verify_type(
            backend,
            text="Hello",
            before_value=before.get("value"),
            settle_ms=0,
        )
        assert result.verified is False

    def test_to_dict_includes_all_fields_for_json_output(self):
        """Verified result should serialize cleanly for JSON output."""
        result = VerificationResult(
            status=VerifyStatus.VERIFIED,
            detail="Text 'Hello' confirmed in element value",
            method="value_compare",
            before="",
            after="Hello",
            elapsed_ms=123.4,
        )
        d = result.to_dict()
        assert d == {
            "verified": True,
            "verification_detail": "Text 'Hello' confirmed in element value",
            "verification_method": "value_compare",
            "verification_ms": 123.4,
        }

    def test_failed_to_dict_includes_error(self):
        """Failed result should include verification_error."""
        result = VerificationResult(
            status=VerifyStatus.FAILED,
            detail="Element value unchanged after type operation",
            method="value_compare",
        )
        d = result.to_dict()
        assert d["verified"] is False
        assert "verification_error" in d
        assert d["verification_error"] == "Element value unchanged after type operation"


class TestGetElementValueProbing:
    """Test #242: get_element_value auto-probing editable elements."""

    @pytest.fixture
    def mock_core(self):
        """Create a mock core with get_element_value."""
        core = MagicMock()
        return core

    def test_probe_finds_edit_element(self, mock_core):
        """When no identifiers but HWND is available, probe Edit role."""
        from naturo.backends.windows import WindowsBackend
        from unittest.mock import PropertyMock

        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = mock_core

        # First call (Edit role) returns a result
        mock_core.get_element_value.return_value = {
            "value": "Hello",
            "pattern": "ValuePattern",
            "role": "Edit",
            "name": "",
            "automation_id": "15",
        }

        with patch.object(backend, "_ensure_core", return_value=mock_core):
            result = backend.get_element_value(hwnd=12345)

        assert result is not None
        assert result["value"] == "Hello"
        assert result["probe_role"] == "Edit"
        mock_core.get_element_value.assert_called_once_with(
            hwnd=12345,
            automation_id=None,
            role="Edit",
            name=None,
        )

    def test_probe_falls_through_to_document(self, mock_core):
        """If Edit not found, try Document role."""
        from naturo.backends.windows import WindowsBackend

        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = mock_core

        # Edit returns None, Document returns result
        mock_core.get_element_value.side_effect = [
            None,  # Edit probe fails
            {"value": "Document text", "role": "Document"},  # Document probe succeeds
        ]

        with patch.object(backend, "_ensure_core", return_value=mock_core):
            result = backend.get_element_value(hwnd=12345)

        assert result is not None
        assert result["probe_role"] == "Document"
        assert mock_core.get_element_value.call_count == 2

    def test_probe_raises_when_all_fail(self, mock_core):
        """If all probes fail, raise NaturoError."""
        from naturo.backends.windows import WindowsBackend
        from naturo.errors import NaturoError

        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = mock_core

        mock_core.get_element_value.return_value = None  # All probes fail

        with patch.object(backend, "_ensure_core", return_value=mock_core):
            with pytest.raises(NaturoError, match="No editable element found"):
                backend.get_element_value(hwnd=12345)

    def test_probe_not_triggered_without_hwnd(self, mock_core):
        """Without HWND, original error is raised (no probing)."""
        from naturo.backends.windows import WindowsBackend
        from naturo.errors import NaturoError

        backend = WindowsBackend.__new__(WindowsBackend)
        backend._core = mock_core

        with patch.object(backend, "_ensure_core", return_value=mock_core):
            with pytest.raises(NaturoError, match="Must specify ref"):
                backend.get_element_value()


class TestExitCodeWarning:
    """Test #242: exit code 2 for inconclusive verification."""

    def test_unknown_status_properties(self):
        """Unknown status should have verified=None and status=unknown."""
        result = unknown_result("test reason")
        assert result.verified is None
        assert result.status == VerifyStatus.UNKNOWN
        assert result.status.value == "unknown"

    def test_skipped_not_treated_as_unknown(self):
        """Skipped results should not trigger exit code 2."""
        result = skip_result("not applicable")
        assert result.verified is None
        assert result.status != VerifyStatus.UNKNOWN
        assert result.status.value == "skipped"
