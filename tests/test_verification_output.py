"""Tests for verification output filtering in text mode (#273).

Verification internals (verified, verification_detail, verification_method,
verification_ms) should only appear in JSON output, not in default text mode.
"""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

import click
import pytest

from naturo.cli.interaction import _json_ok, _VERIFICATION_KEYS


class TestJsonOkFiltering:
    """Verify _json_ok filters verification keys from text output."""

    def test_text_mode_excludes_verification_keys(self) -> None:
        """In text mode, verification internals must not appear."""
        data = {
            "action": "pressed",
            "key": "enter",
            "count": 1,
            "verified": None,
            "verification_detail": "No UI state change",
            "verification_method": "focus_check",
            "verification_ms": 152.0,
        }
        buf = StringIO()
        with patch.object(click, "echo", side_effect=lambda x, **kw: buf.write(x + "\n")):
            _json_ok(data, json_output=False)

        output = buf.getvalue()
        assert "action: pressed" in output
        assert "key: enter" in output
        assert "count: 1" in output
        # Verification internals must be absent
        assert "verified:" not in output
        assert "verification_detail:" not in output
        assert "verification_method:" not in output
        assert "verification_ms:" not in output

    def test_json_mode_includes_verification_keys(self) -> None:
        """In JSON mode, all fields including verification should appear."""
        data = {
            "action": "pressed",
            "key": "enter",
            "verified": None,
            "verification_detail": "No UI state change",
            "verification_method": "focus_check",
            "verification_ms": 152.0,
        }
        buf = StringIO()
        with patch.object(click, "echo", side_effect=lambda x, **kw: buf.write(x + "\n")):
            _json_ok(data, json_output=True)

        parsed = json.loads(buf.getvalue())
        assert parsed["success"] is True
        assert parsed["data"]["verified"] is None
        assert parsed["data"]["verification_detail"] == "No UI state change"
        assert parsed["data"]["verification_method"] == "focus_check"

    def test_text_mode_no_verification_data_unchanged(self) -> None:
        """When no verification data exists, output is unchanged."""
        data = {"action": "clicked", "x": 500, "y": 300}
        buf = StringIO()
        with patch.object(click, "echo", side_effect=lambda x, **kw: buf.write(x + "\n")):
            _json_ok(data, json_output=False)

        output = buf.getvalue()
        assert "action: clicked" in output
        assert "x: 500" in output
        assert "y: 300" in output


class TestVerificationKeysSet:
    """Ensure _VERIFICATION_KEYS covers all known verification fields."""

    def test_known_keys_are_covered(self) -> None:
        assert "verified" in _VERIFICATION_KEYS
        assert "verification_detail" in _VERIFICATION_KEYS
        assert "verification_method" in _VERIFICATION_KEYS
        assert "verification_ms" in _VERIFICATION_KEYS
        assert "verification_error" in _VERIFICATION_KEYS

    def test_non_verification_keys_are_not_in_set(self) -> None:
        assert "action" not in _VERIFICATION_KEYS
        assert "key" not in _VERIFICATION_KEYS
        assert "count" not in _VERIFICATION_KEYS
