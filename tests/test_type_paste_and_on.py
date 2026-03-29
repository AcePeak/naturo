"""Tests for type --paste without TEXT, --on element targeting (#165),
and IME paste fallback (#425).

These tests verify:
1. ``type --paste`` without TEXT pastes current clipboard (Ctrl+V only)
2. ``type --paste`` with TEXT sets clipboard then Ctrl+V (existing behavior)
3. ``type "text" --on eN`` clicks element then types
4. ``type --on eN --paste`` clicks element then pastes clipboard
5. ``type`` without TEXT or --paste gives an error
6. (#425) When SendInput type fails verification, auto-retry with paste mode
"""
from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

_win_only = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Interaction commands require Windows",
)


@pytest.fixture
def runner():
    return CliRunner()


class TestTypePasteWithoutText:
    """type --paste without TEXT should paste current clipboard."""

    def test_type_no_text_no_paste_errors(self, runner):
        """type without TEXT and without --paste should give INVALID_INPUT."""
        from naturo.cli.interaction import type_cmd

        with patch("naturo.cli.interaction._common._get_backend"):
            result = runner.invoke(type_cmd, ["--json"])
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    @_win_only
    def test_type_paste_without_text_calls_ctrl_v(self, runner):
        """type --paste without TEXT should just press Ctrl+V."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}):
            result = runner.invoke(type_cmd, ["--paste", "--json"])

        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["action"] == "pasted"
        assert data["data"]["text"] == "(clipboard)"
        # Should NOT call clipboard_set — just Ctrl+V
        mock_backend.clipboard_set.assert_not_called()
        mock_backend.hotkey.assert_called_once_with("ctrl", "v")

    @_win_only
    def test_type_paste_with_text_sets_clipboard(self, runner):
        """type "hello" --paste should set clipboard then Ctrl+V."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()
        mock_backend.clipboard_get.return_value = ""

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}):
            result = runner.invoke(type_cmd, ["hello", "--paste", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["action"] == "pasted"
        assert data["data"]["text"] == "hello"
        mock_backend.clipboard_set.assert_called()
        mock_backend.hotkey.assert_called_with("ctrl", "v")


class TestTypeOnElement:
    """type --on should click target element before typing."""

    def test_type_has_on_param(self):
        """type command should accept --on option."""
        from naturo.cli.interaction import type_cmd

        param_names = [p.name for p in type_cmd.params]
        assert "on_element" in param_names

    @_win_only
    def test_type_on_eref_clicks_then_types(self, runner):
        """type "hello" --on e5 should resolve ref, click, then type."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}), \
             patch("naturo.snapshot.SnapshotManager") as MockMgr:
            mock_mgr = MockMgr.return_value
            mock_mgr.resolve_ref.return_value = (100, 200)

            result = runner.invoke(type_cmd, ["hello", "--on", "e5", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["target"] == "e5"
        # Should click the element coordinates first
        mock_backend.click.assert_called_once_with(100, 200, button="left", input_mode="normal")
        # Then type
        mock_backend.type_text.assert_called_once()

    @_win_only
    def test_type_on_eref_not_found(self, runner):
        """type --on e99 with missing ref should error."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}), \
             patch("naturo.snapshot.SnapshotManager") as MockMgr:
            mock_mgr = MockMgr.return_value
            mock_mgr.resolve_ref.return_value = None

            result = runner.invoke(type_cmd, ["hello", "--on", "e99", "--json"])

        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "REF_NOT_FOUND"

    @_win_only
    def test_type_on_with_paste_clicks_then_pastes(self, runner):
        """type --paste --on e5 should click then paste clipboard."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}), \
             patch("naturo.snapshot.SnapshotManager") as MockMgr:
            mock_mgr = MockMgr.return_value
            mock_mgr.resolve_ref.return_value = (100, 200)

            result = runner.invoke(type_cmd, ["--paste", "--on", "e5", "--json"])

        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["action"] == "pasted"
        assert data["data"]["target"] == "e5"
        # Should click, then Ctrl+V (no clipboard_set since no text)
        mock_backend.click.assert_called_once()
        mock_backend.hotkey.assert_called_once_with("ctrl", "v")
        mock_backend.clipboard_set.assert_not_called()


class TestTypePasteFallbackOnIME:
    """(#425) When SendInput type verification fails, retry via paste mode."""

    @_win_only
    def test_paste_fallback_triggered_on_verification_failure(self, runner):
        """When verify_type returns FAILED after SendInput, fallback to paste."""
        from naturo.cli.interaction import type_cmd
        from naturo.verify import VerificationResult, VerifyStatus

        mock_backend = MagicMock()
        mock_backend.clipboard_get.return_value = ""

        failed_result = VerificationResult(
            status=VerifyStatus.FAILED,
            detail="No text change detected",
            method="value_compare",
        )
        success_result = VerificationResult(
            status=VerifyStatus.VERIFIED,
            detail="Text matches",
            method="value_compare",
        )

        call_count = [0]

        def mock_verify_type(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return failed_result  # First call: SendInput failed
            return success_result  # Second call: paste succeeded

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}), \
             patch("naturo.verify.verify_type", side_effect=mock_verify_type), \
             patch("naturo.verify.capture_before_state", return_value=None):
            result = runner.invoke(type_cmd, ["Hello World", "--json", "--verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["action"] == "pasted"
        assert data["data"]["fallback"] == "paste_after_type_failure"
        # Should have called clipboard_set and hotkey for paste
        mock_backend.clipboard_set.assert_called_with("Hello World")
        mock_backend.hotkey.assert_called_with("ctrl", "v")

    @_win_only
    def test_no_fallback_when_already_paste_mode(self, runner):
        """When --paste is already used, no fallback attempt on failure."""
        from naturo.cli.interaction import type_cmd
        from naturo.verify import VerificationResult, VerifyStatus

        mock_backend = MagicMock()
        mock_backend.clipboard_get.return_value = ""

        failed_result = VerificationResult(
            status=VerifyStatus.FAILED,
            detail="No text change detected",
            method="value_compare",
        )

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}), \
             patch("naturo.verify.verify_type", return_value=failed_result), \
             patch("naturo.verify.capture_before_state", return_value=None):
            result = runner.invoke(type_cmd, ["Hello", "--paste", "--json", "--verify"])

        # Should exit with code 1 (verification failure) — no second attempt
        assert result.exit_code == 1

    @_win_only
    def test_fallback_not_triggered_on_success(self, runner):
        """When SendInput type succeeds verification, no paste fallback."""
        from naturo.cli.interaction import type_cmd
        from naturo.verify import VerificationResult, VerifyStatus

        mock_backend = MagicMock()

        success_result = VerificationResult(
            status=VerifyStatus.VERIFIED,
            detail="Text matches",
            method="value_compare",
        )

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}), \
             patch("naturo.verify.verify_type", return_value=success_result), \
             patch("naturo.verify.capture_before_state", return_value=None):
            result = runner.invoke(type_cmd, ["Hello", "--json", "--verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["action"] == "typed"
        assert "fallback" not in data["data"]
        # Should NOT have used clipboard
        mock_backend.clipboard_set.assert_not_called()


class TestTypeEscapeSequences:
    """type should interpret C-style escape sequences (\\t, \\n, \\r, \\\\)."""

    @_win_only
    def test_type_tab_escape(self, runner):
        """type 'A\\tB' should send text with real tab character."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}):
            result = runner.invoke(type_cmd, [r"A\tB", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        mock_backend.type_text.assert_called_once()
        typed_text = mock_backend.type_text.call_args[0][0]
        assert typed_text == "A\tB"

    @_win_only
    def test_type_newline_escape(self, runner):
        """type 'Line1\\nLine2' should send text with real newline."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}):
            result = runner.invoke(type_cmd, [r"Line1\nLine2", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        typed_text = mock_backend.type_text.call_args[0][0]
        assert typed_text == "Line1\nLine2"

    @_win_only
    def test_type_carriage_return_escape(self, runner):
        """type 'A\\rB' should send text with real carriage return."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}):
            result = runner.invoke(type_cmd, [r"A\rB", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        typed_text = mock_backend.type_text.call_args[0][0]
        assert typed_text == "A\rB"

    @_win_only
    def test_type_literal_backslash(self, runner):
        """type 'path\\\\file' should produce single backslash."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}):
            result = runner.invoke(type_cmd, ["path\\\\file", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        typed_text = mock_backend.type_text.call_args[0][0]
        assert typed_text == "path\\file"

    @_win_only
    def test_type_mixed_escapes(self, runner):
        """type 'Col1\\tCol2\\nRow2' should handle mixed escapes."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}):
            result = runner.invoke(type_cmd, [r"Col1\tCol2\nRow2", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        typed_text = mock_backend.type_text.call_args[0][0]
        assert typed_text == "Col1\tCol2\nRow2"

    @_win_only
    def test_type_paste_mode_also_gets_escapes(self, runner):
        """Escape sequences should also work in --paste mode."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()
        mock_backend.clipboard_get.return_value = ""

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}):
            result = runner.invoke(type_cmd, [r"A\tB", "--paste", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        # Clipboard should receive the processed text with real tab
        mock_backend.clipboard_set.assert_called_once_with("A\tB")

    @_win_only
    def test_type_raw_disables_escape_interpretation(self, runner):
        """#619: --raw flag types text literally without escape processing."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}):
            result = runner.invoke(type_cmd, [
                r"C:\Users\test\report.txt", "--raw", "--json", "--no-verify",
            ])

        data = json.loads(result.output)
        assert data["success"] is True
        typed_text = mock_backend.type_text.call_args[0][0]
        # With --raw, backslash sequences should NOT be interpreted
        assert typed_text == r"C:\Users\test\report.txt"
        assert "\t" not in typed_text
        assert "\r" not in typed_text

    @_win_only
    def test_type_without_raw_still_interprets_escapes(self, runner):
        """Without --raw, escape sequences are still interpreted as before."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value={}):
            result = runner.invoke(type_cmd, [r"A\tB", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        typed_text = mock_backend.type_text.call_args[0][0]
        assert typed_text == "A\tB"  # \t still becomes real tab


class TestTypeNewlineBypassesUIA:
    """When text contains \\n or \\r, type must bypass UIA SetValue (#563).

    UIA ValuePattern.SetValue() silently strips newline/CR characters,
    causing a silent failure. The type command should detect this and
    fall through to SendInput which handles them as Enter keypresses.
    """

    @_win_only
    def test_newline_text_skips_uia_uses_sendinput(self, runner):
        """type 'Line1\\nLine2' with UIA route should bypass SetValue."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()
        mock_backend.set_element_value.return_value = True  # Would succeed if called

        # Route says UIA is available
        route_info = {"method": "uia"}
        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value=route_info):
            result = runner.invoke(type_cmd, [r"Line1\nLine2", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        # SetValue should NOT have been called — newlines would be stripped
        mock_backend.set_element_value.assert_not_called()
        # SendInput (type_text) should have been used instead
        mock_backend.type_text.assert_called_once()
        typed_text = mock_backend.type_text.call_args[0][0]
        assert typed_text == "Line1\nLine2"

    @_win_only
    def test_cr_text_skips_uia_uses_sendinput(self, runner):
        """type 'A\\rB' with UIA route should bypass SetValue."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()
        mock_backend.set_element_value.return_value = True

        route_info = {"method": "uia"}
        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value=route_info):
            result = runner.invoke(type_cmd, [r"A\rB", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        mock_backend.set_element_value.assert_not_called()
        mock_backend.type_text.assert_called_once()
        typed_text = mock_backend.type_text.call_args[0][0]
        assert typed_text == "A\rB"

    @_win_only
    def test_tab_text_still_uses_uia(self, runner):
        """type 'A\\tB' with UIA route should still use SetValue (tabs are safe)."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()
        mock_backend.set_element_value.return_value = True

        route_info = {"method": "uia"}
        with patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._common._auto_route", return_value=route_info):
            result = runner.invoke(type_cmd, [r"A\tB", "--json", "--no-verify"])

        data = json.loads(result.output)
        assert data["success"] is True
        # SetValue SHOULD be called — tabs survive SetValue
        mock_backend.set_element_value.assert_called_once()
        # type_text should NOT be called
        mock_backend.type_text.assert_not_called()
