"""Non-ASCII (CJK / emoji) must round-trip *literally* through CLI ``-j`` output (#894).

Python's ``json.dumps`` defaults to ``ensure_ascii=True``, which rewrites every
non-ASCII code point as a ``\\uXXXX`` escape. For naturo's ``-j`` output that means
Chinese window titles, user-supplied paths, selector names and error messages come
back mangled (``记事本`` → ``\\u8bb0\\u4e8b\\u672c``) — unreadable for CJK users and
inconsistent with the non-JSON path, which already prints literal Unicode. The CLI
already reconfigures stdout/stderr to UTF-8 (``naturo/cli/__init__.py``), so emitting
literal Unicode is safe on every platform.

These tests pin the contract: the shared :func:`naturo.cli._jsonio.json_dumps` helper
defaults to ``ensure_ascii=False``, the canonical error envelope preserves literal
Unicode, and an end-to-end command echoes CJK input without escaping.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# A sampling of non-ASCII the field cares about: CJK app names and an emoji.
_CJK = "记事本"  # "Notepad"
_EMOJI = "🚀"


@pytest.fixture
def runner():
    return CliRunner()


class TestJsonDumpsHelper:
    """The shared helper defaults to literal (non-escaped) Unicode."""

    def test_defaults_to_literal_unicode(self):
        from naturo.cli._jsonio import json_dumps

        out = json_dumps({"title": _CJK, "icon": _EMOJI})
        assert _CJK in out
        assert _EMOJI in out
        assert "\\u" not in out
        # Still valid JSON that round-trips to the original values.
        assert json.loads(out) == {"title": _CJK, "icon": _EMOJI}

    def test_ascii_output_is_unchanged(self):
        from naturo.cli._jsonio import json_dumps

        payload = {"success": True, "count": 3, "name": "Save"}
        assert json_dumps(payload) == json.dumps(payload)

    def test_explicit_ensure_ascii_true_is_honored(self):
        from naturo.cli._jsonio import json_dumps

        out = json_dumps({"title": _CJK}, ensure_ascii=True)
        assert _CJK not in out
        assert "\\u" in out

    def test_passes_through_other_kwargs(self):
        from naturo.cli._jsonio import json_dumps

        out = json_dumps({"b": 1, "a": 2}, indent=2, sort_keys=True)
        assert out == json.dumps({"b": 1, "a": 2}, indent=2,
                                 sort_keys=True, ensure_ascii=False)


class TestErrorEnvelopePreservesUnicode:
    """The canonical error envelope (every command's ``-j`` error path) stays literal."""

    def test_json_error_message_is_literal(self):
        from naturo.cli.error_helpers import json_error

        out = json_error("INVALID_INPUT", f"bad path: {_CJK}")
        assert _CJK in out
        assert "\\u" not in out
        assert json.loads(out)["error"]["message"] == f"bad path: {_CJK}"

    def test_json_error_context_is_literal(self):
        from naturo.cli.error_helpers import json_error

        out = json_error("WINDOW_NOT_FOUND", "not found",
                         context={"app": _CJK})
        assert _CJK in out
        assert json.loads(out)["error"]["context"]["app"] == _CJK


def _make_mock_backend():
    """Minimal element tree whose only Button is named 'Save' (ASCII)."""
    backend = MagicMock()
    button = MagicMock()
    button.id, button.role, button.name, button.value = "btn", "Button", "Save", ""
    button.x, button.y, button.width, button.height = 100, 200, 80, 30
    button.children, button.properties = [], {"className": "Button"}
    root = MagicMock()
    root.id, root.role, root.name, root.value = "root", "Window", "Untitled", ""
    root.x, root.y, root.width, root.height = 0, 0, 800, 600
    root.children, root.properties = [button], {"className": "Notepad"}
    backend.get_element_tree.return_value = root
    return backend


class TestCliEndToEnd:
    """A real command's ``-j`` error path echoes CJK input without escaping."""

    def test_selector_not_found_error_keeps_cjk_literal(self, runner):
        mock_be = _make_mock_backend()
        patches = [
            patch("naturo.cli.interaction._common._get_backend",
                  return_value=mock_be),
            patch("naturo.cli.interaction._common._check_desktop_session"),
            patch("naturo.cli.interaction._common._auto_route", return_value={}),
        ]
        for p in patches:
            p.start()
        try:
            from naturo.cli.interaction import click_cmd
            result = runner.invoke(click_cmd, [
                "--selector", f'app://*/Button[@name="{_CJK}"]',
                "--json",
            ])
            assert result.exit_code != 0
            assert "SELECTOR_NOT_FOUND" in result.output
            # The echoed selector must contain literal CJK, not \uXXXX escapes.
            assert _CJK in result.output
            assert "\\u" not in result.output
        finally:
            for p in patches:
                p.stop()
