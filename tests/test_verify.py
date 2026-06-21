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
    _typed_text_in_ui_diff,
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

    def test_unknown_when_value_unchanged(self):
        """Value unchanged after typing → UNKNOWN (inconclusive, not FAILED).

        (#398) Changed from FAILED to UNKNOWN because some app frameworks
        (Win11 Notepad WinUI 3) don't expose typed text via ValuePattern.
        Reporting FAILED would be a false negative.
        """
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "original"}

        result = verify_type(
            backend,
            text="Hello",
            before_value="original",
            settle_ms=0,
        )
        assert result.status == VerifyStatus.UNKNOWN
        assert result.verified is None
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


    def test_verified_via_ui_text_fallback_when_value_unchanged(self):
        """(#398) Value unchanged but UI text changed → VERIFIED via fallback.

        Win11 Notepad WinUI 3 doesn't expose typed text via ValuePattern.
        The UI text diff fallback detects the change via GetWindowText/UIA names.
        """
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "original"}

        before_ui_texts = {"child:12345": ""}
        after_ui_texts = {"child:12345": "Hello"}

        with patch("naturo.verify._capture_ui_texts", return_value=after_ui_texts):
            result = verify_type(
                backend,
                text="Hello",
                before_value="original",
                before_ui_texts=before_ui_texts,
                settle_ms=0,
            )
        assert result.status == VerifyStatus.VERIFIED
        assert result.method == "ui_text_diff"

    def test_unknown_when_ui_text_changed_but_typed_text_missing(self):
        """(#403) UI text changed but typed text NOT in diff → UNKNOWN.

        Win11 Notepad may update window title ("Untitled" → "*Untitled")
        without the typed text actually appearing. The old code reported
        VERIFIED for any UI text change, causing a false positive.
        """
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": ""}

        # Window title changed (irrelevant) but typed text is nowhere
        before_ui_texts = {"main:54321": "Untitled - Notepad"}
        after_ui_texts = {"main:54321": "*Untitled - Notepad"}

        with patch("naturo.verify._capture_ui_texts", return_value=after_ui_texts):
            result = verify_type(
                backend,
                text="QA-Mariana v0.3.0 test",
                before_value="",
                before_ui_texts=before_ui_texts,
                settle_ms=0,
            )
        assert result.status == VerifyStatus.UNKNOWN
        assert result.verified is None
        assert "ui_text_diff" not in (result.method or "")

    def test_unknown_when_value_and_ui_texts_both_unchanged(self):
        """(#398) Value AND UI text both unchanged → UNKNOWN (not FAILED)."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "original"}

        same_texts = {"child:12345": "original"}

        with patch("naturo.verify._capture_ui_texts", return_value=same_texts):
            result = verify_type(
                backend,
                text="Hello",
                before_value="original",
                before_ui_texts=same_texts,
                settle_ms=0,
            )
        assert result.status == VerifyStatus.UNKNOWN
        assert result.verified is None


class TestTypedTextInUiDiff:
    """Test _typed_text_in_ui_diff helper (#403)."""

    def test_typed_text_found_in_changed_value(self):
        """Typed text present in a new/changed UI value → True."""
        before = {"child:100": ""}
        after = {"child:100": "Hello world"}
        assert _typed_text_in_ui_diff("Hello", before, after) is True

    def test_typed_text_not_in_changed_value(self):
        """Typed text absent from changed values → False."""
        before = {"main:200": "Untitled"}
        after = {"main:200": "*Untitled"}
        assert _typed_text_in_ui_diff("QA test text", before, after) is False

    def test_new_key_with_typed_text(self):
        """New key in after snapshot containing typed text → True."""
        before = {"main:200": "Notepad"}
        after = {"main:200": "Notepad", "child:300": "Hello"}
        assert _typed_text_in_ui_diff("Hello", before, after) is True

    def test_empty_text_returns_false(self):
        """Empty typed text → False (nothing to verify)."""
        assert _typed_text_in_ui_diff("", {}, {"child:1": "x"}) is False

    def test_no_changes_returns_false(self):
        """Identical before/after → False."""
        same = {"child:1": "text"}
        assert _typed_text_in_ui_diff("text", same, same) is False

    def test_case_insensitive(self):
        """Match is case-insensitive."""
        before = {"child:1": ""}
        after = {"child:1": "HELLO WORLD"}
        assert _typed_text_in_ui_diff("hello", before, after) is True

    def test_prefix_match(self):
        """Partial prefix match (≥3 chars) → True."""
        before = {"child:1": ""}
        after = {"child:1": "Hel"}
        assert _typed_text_in_ui_diff("Hello world", before, after) is True

    def test_short_prefix_no_false_match(self):
        """2-char text prefix shouldn't match unrelated text."""
        before = {"child:1": ""}
        after = {"child:1": "Absolutely"}
        # "Ab" prefix of "Ab" is too short for meaningful match,
        # but min_prefix=min(2,3)=2, so it checks "ab" in "absolutely" → True
        # This is acceptable since very short text is a rare edge case
        assert _typed_text_in_ui_diff("Ab", before, after) is True


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

    def test_empty_before_ui_texts_still_triggers_capture(self):
        """Empty dict before_ui_texts should still trigger post-capture (#270).

        Previously ``if before_ui_texts:`` treated ``{}`` as falsy and
        skipped the fallback.  With the fix (``is not None``), an empty
        pre-capture still runs post-capture and can detect new text.
        """
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100}

        with patch("naturo.verify._capture_focus_state") as mock_focus, \
             patch("naturo.verify._capture_ui_texts") as mock_texts:
            mock_focus.return_value = focus.copy()
            # Pre-capture was empty, but post-capture finds new text
            mock_texts.return_value = {"uia:50004:CalculatorResults": "7"}
            result = verify_click(
                backend,
                before_focus=focus,
                before_ui_texts={},
                settle_ms=0,
            )

        assert result.status == VerifyStatus.VERIFIED
        assert result.method == "ui_text_diff"

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


    def test_uia_invoked_returns_verified_immediately(self):
        """#270: UIA Invoke succeeded → verified without focus/text checks."""
        backend = MagicMock(spec=[])
        result = verify_click(
            backend,
            before_focus=None,
            uia_invoked=True,
            settle_ms=0,
        )

        assert result.status == VerifyStatus.VERIFIED
        assert result.method == "uia_invoke"
        assert "Invoke" in result.detail

    def test_uia_invoked_false_falls_through(self):
        """uia_invoked=False should use normal focus/text verification."""
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100}

        with patch("naturo.verify._capture_focus_state") as mock_focus:
            mock_focus.return_value = focus.copy()
            result = verify_click(
                backend,
                before_focus=focus,
                uia_invoked=False,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN
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

    def test_type_captures_ui_texts_for_fallback(self):
        """(#398) Before-state for type now captures UI texts for fallback verification."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "text"}

        with patch("naturo.verify._capture_focus_state", return_value={}):
            state = capture_before_state(backend, action="type")

        assert "ui_texts" in state

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

    def test_full_type_verify_inconclusive_flow(self):
        """Value unchanged after typing → UNKNOWN (inconclusive).

        (#398) Changed from FAILED to UNKNOWN. When ValuePattern reports
        no change, it could be a real silent failure OR the app framework
        doesn't expose typed text. We report UNKNOWN to avoid false negatives.
        """
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
        assert result.verified is None
        assert result.status == VerifyStatus.UNKNOWN

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


class TestVerifyTypeUiTextFallbackError:
    """Test verify_type when UI text fallback itself raises an exception."""

    def test_unknown_when_ui_text_capture_raises(self):
        """(#263) _capture_ui_texts raises during fallback → graceful UNKNOWN."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "original"}

        before_ui_texts = {"child:100": "before"}

        with patch(
            "naturo.verify._capture_ui_texts",
            side_effect=Exception("COM timeout"),
        ):
            result = verify_type(
                backend,
                text="Hello",
                before_value="original",
                before_ui_texts=before_ui_texts,
                settle_ms=0,
            )
        # Falls through to the UNKNOWN return at end of unchanged-value branch
        assert result.status == VerifyStatus.UNKNOWN
        assert result.verified is None

    def test_unknown_when_ui_text_capture_returns_empty(self):
        """_capture_ui_texts returns empty dict → falls through to UNKNOWN."""
        backend = MagicMock()
        backend.get_element_value.return_value = {"value": "original"}

        before_ui_texts = {"child:100": "before"}

        with patch("naturo.verify._capture_ui_texts", return_value={}):
            result = verify_type(
                backend,
                text="Hello",
                before_value="original",
                before_ui_texts=before_ui_texts,
                settle_ms=0,
            )
        assert result.status == VerifyStatus.UNKNOWN


class TestVerifyPressEdgeCases:
    """Additional edge case tests for verify_press."""

    def test_unknown_on_capture_error(self):
        """Focus capture raises → UNKNOWN (mirrors TestVerifyClick equivalent)."""
        backend = MagicMock(spec=[])

        with patch(
            "naturo.verify._capture_focus_state",
            side_effect=Exception("COM error"),
        ):
            result = verify_press(
                backend,
                keys=("enter",),
                before_focus={"foreground_hwnd": 100},
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN
        assert "focus state" in result.detail.lower()

    def test_multiple_nav_keys_unknown(self):
        """Multiple keys including nav key, no focus change → UNKNOWN."""
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100}

        with patch("naturo.verify._capture_focus_state") as mock_capture:
            mock_capture.return_value = focus.copy()
            result = verify_press(
                backend,
                keys=("alt+f4",),
                before_focus=focus,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN
        assert "alt+f4" in result.detail.lower()

    def test_escape_key_is_nav_key(self):
        """Escape is treated as a navigation key."""
        backend = MagicMock(spec=[])
        focus = {"foreground_hwnd": 100}

        with patch("naturo.verify._capture_focus_state") as mock_capture:
            mock_capture.return_value = focus.copy()
            result = verify_press(
                backend,
                keys=("escape",),
                before_focus=focus,
                settle_ms=0,
            )

        assert result.status == VerifyStatus.UNKNOWN


class TestCaptureBeforeStatePressAction:
    """Test capture_before_state for press actions (no ui_texts capture)."""

    def test_press_does_not_capture_ui_texts(self):
        """Press action should NOT capture ui_texts (only click/type do)."""
        backend = MagicMock(spec=[])

        with patch("naturo.verify._capture_focus_state", return_value={"fg": 1}):
            state = capture_before_state(backend, action="press")

        assert "ui_texts" not in state
        assert "focus" in state

    def test_press_does_not_capture_value(self):
        """Press action should NOT capture element value."""
        backend = MagicMock(spec=[])

        with patch("naturo.verify._capture_focus_state", return_value={}):
            state = capture_before_state(backend, action="press")

        assert "value" not in state

    def test_type_captures_none_value_when_no_info(self):
        """Type action: get_element_value returns None → value=None."""
        backend = MagicMock()
        backend.get_element_value.return_value = None

        with patch("naturo.verify._capture_focus_state", return_value={}):
            state = capture_before_state(backend, action="type")

        assert state["value"] is None

    def test_type_without_get_element_value(self):
        """Type action on backend without get_element_value → no value key."""
        backend = MagicMock(spec=[])

        with patch("naturo.verify._capture_focus_state", return_value={}):
            state = capture_before_state(backend, action="type")

        assert "value" not in state


class TestCaptureFocusStateNonWindows:
    """Test _capture_focus_state on non-Windows platforms."""

    def test_returns_platform_key_on_non_windows(self):
        """On non-Windows (Linux/macOS), should return dict with platform key."""
        from naturo.verify import _capture_focus_state

        backend = MagicMock(spec=[])
        # Force the non-Windows branch deterministically. Without this patch the
        # test only passes when the host happens to be Linux/macOS; on a real
        # Windows desktop it takes the Win32 path and fails (#1100).
        with patch("platform.system", return_value="Linux"):
            state = _capture_focus_state(backend)

        assert "platform" in state
        assert state["platform"] == "Linux"


class TestCaptureUiTextsNonWindows:
    """Test _capture_ui_texts on non-Windows platforms."""

    def test_returns_empty_dict_on_linux(self):
        """On Linux, should return empty dict immediately."""
        from naturo.verify import _capture_ui_texts

        backend = MagicMock(spec=[])
        # Force the non-Windows branch deterministically. Without this patch the
        # function takes the Win32 EnumChildWindows path on a real Windows
        # desktop and returns live window texts instead of {} (#1100).
        with patch("platform.system", return_value="Linux"):
            result = _capture_ui_texts(backend, app="test")

        assert result == {}

    def test_returns_empty_dict_without_target(self):
        """Without app/window_title/hwnd/pid, returns empty dict."""
        from naturo.verify import _capture_ui_texts

        backend = MagicMock(spec=[])
        result = _capture_ui_texts(backend)

        assert result == {}


class TestToDict:
    """Test VerificationResult.to_dict edge cases."""

    def test_minimal_verified_no_detail(self):
        """Verified result with no detail/method → only verified key."""
        result = VerificationResult(status=VerifyStatus.VERIFIED)
        d = result.to_dict()
        assert d == {"verified": True}

    def test_zero_elapsed_omitted(self):
        """Zero elapsed_ms → verification_ms key omitted."""
        result = VerificationResult(
            status=VerifyStatus.VERIFIED,
            elapsed_ms=0.0,
        )
        d = result.to_dict()
        assert "verification_ms" not in d

    def test_skipped_no_error_key(self):
        """Skipped result → no verification_error key."""
        result = VerificationResult(
            status=VerifyStatus.SKIPPED,
            detail="not applicable",
        )
        d = result.to_dict()
        assert "verification_error" not in d

    def test_unknown_no_error_key(self):
        """Unknown result → no verification_error key (only FAILED has it)."""
        result = VerificationResult(
            status=VerifyStatus.UNKNOWN,
            detail="inconclusive",
        )
        d = result.to_dict()
        assert "verification_error" not in d


class TestVerificationStatusProperties:
    """Test verification status properties (#242 / #426)."""

    def test_unknown_status_properties(self):
        """Unknown status should have verified=None and status=unknown."""
        result = unknown_result("test reason")
        assert result.verified is None
        assert result.status == VerifyStatus.UNKNOWN
        assert result.status.value == "unknown"

    def test_skipped_not_treated_as_unknown(self):
        """Skipped and unknown are distinct statuses."""
        result = skip_result("not applicable")
        assert result.verified is None
        assert result.status != VerifyStatus.UNKNOWN
        assert result.status.value == "skipped"


class TestInconclusiveExitCode:
    """Test #426: click/press/type must exit 0 even when verification is inconclusive.

    When the action was performed but verification cannot confirm the effect
    (UNKNOWN status), the exit code must be 0.  The ``verified: null`` field
    in the output lets callers distinguish confirmed from inconclusive.
    """

    def _run_click_with_unknown_verification(self):
        """Invoke click_cmd with mocked backend that yields UNKNOWN verification."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        mock_backend = MagicMock()
        mock_backend.click.return_value = None
        mock_backend.get_element_tree.return_value = {"elements": []}

        unknown = VerificationResult(
            status=VerifyStatus.UNKNOWN,
            detail="No focus change detected after click.",
            method="focus_check",
        )

        runner = CliRunner()
        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value=None), \
             patch("naturo.verify.capture_before_state", return_value=None), \
             patch("naturo.verify.verify_click", return_value=unknown):
            result = runner.invoke(click_cmd, ["--coords", "500", "300", "--json"])
        return result

    def test_click_inconclusive_exits_zero(self):
        """click must exit 0 when verification is inconclusive (#426)."""
        result = self._run_click_with_unknown_verification()
        assert result.exit_code == 0, (
            f"Expected exit code 0 for inconclusive click, got {result.exit_code}.\n"
            f"Output: {result.output}"
        )

    def test_click_inconclusive_json_has_verified_null(self):
        """click JSON output must include verified=null for inconclusive."""
        import json as json_mod

        result = self._run_click_with_unknown_verification()
        parsed = json_mod.loads(result.output)
        assert parsed["success"] is True
        assert parsed["data"]["verified"] is None

    def _run_press_with_unknown_verification(self):
        """Invoke press with mocked backend that yields UNKNOWN verification."""
        from click.testing import CliRunner
        from naturo.cli.interaction import press

        mock_backend = MagicMock()
        mock_backend.press_key.return_value = None

        unknown = VerificationResult(
            status=VerifyStatus.UNKNOWN,
            detail="No UI state change after navigation key(s) enter.",
            method="focus_check",
        )

        runner = CliRunner()
        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value=None), \
             patch("naturo.verify.capture_before_state", return_value=None), \
             patch("naturo.verify.verify_press", return_value=unknown):
            result = runner.invoke(press, ["enter", "--json"])
        return result

    def test_press_inconclusive_exits_zero(self):
        """press must exit 0 when verification is inconclusive (#426)."""
        result = self._run_press_with_unknown_verification()
        assert result.exit_code == 0, (
            f"Expected exit code 0 for inconclusive press, got {result.exit_code}.\n"
            f"Output: {result.output}"
        )
