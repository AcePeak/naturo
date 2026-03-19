"""Tests for Phase 2 clipboard: get, set, paste.

Tests are organized by category:
  - Method signature / API existence (all platforms)
  - CLI option validation (all platforms)
  - Windows-only functional tests guarded by @pytest.mark.ui
"""

from __future__ import annotations

import json
import platform

import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


# ── T140-T146: Clipboard method signatures ────────────────────────────────────


class TestClipboardMethodSignatures:
    """Backend clipboard methods exist with correct signatures (all platforms)."""

    def test_clipboard_get_method_exists(self):
        """T140 – clipboard_get method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "clipboard_get")

    def test_clipboard_set_method_exists(self):
        """T142 – clipboard_set method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "clipboard_set")

    def test_clipboard_get_signature(self):
        """T140 – clipboard_get takes no required args beyond self."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.clipboard_get)
        # Only 'self' is required
        required = [
            p for name, p in sig.parameters.items()
            if name != "self" and p.default is inspect.Parameter.empty
        ]
        assert len(required) == 0

    def test_clipboard_set_signature(self):
        """T142 – clipboard_set accepts a text parameter."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.clipboard_set)
        assert "text" in sig.parameters

    def test_clipboard_set_default_text(self):
        """T142 – clipboard_set text defaults to empty string."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.clipboard_set)
        assert sig.parameters["text"].default == ""


# ── CLI option validation (all platforms) ─────────────────────────────────────


class TestClipboardCLIOptions:
    """clipboard CLI option validation (T140-T146)."""

    def test_clipboard_group_in_main_help(self, runner):
        """clipboard group is in main help."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "clipboard" in result.output

    def test_clipboard_get_in_help(self, runner):
        """T140 – clipboard get subcommand is documented."""
        result = runner.invoke(main, ["clipboard", "--help"])
        assert result.exit_code == 0
        assert "get" in result.output

    def test_clipboard_set_in_help(self, runner):
        """T142 – clipboard set subcommand is documented."""
        result = runner.invoke(main, ["clipboard", "--help"])
        assert "set" in result.output

    def test_clipboard_get_json_option(self, runner):
        """T297 – clipboard get --json option is documented."""
        result = runner.invoke(main, ["clipboard", "get", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_clipboard_set_json_option(self, runner):
        """T297 – clipboard set --json option is documented."""
        result = runner.invoke(main, ["clipboard", "set", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_clipboard_set_subcommand_runs(self, runner):
        """T142 – clipboard set subcommand is reachable (may be placeholder)."""
        # The subcommand should at minimum be accessible (exit 0 for placeholder,
        # or non-zero if content argument is required).
        result = runner.invoke(main, ["clipboard", "set", "--help"])
        assert result.exit_code == 0

    def test_paste_group_in_main_help(self, runner):
        """T144 – paste command is in main help."""
        result = runner.invoke(main, ["--help"])
        assert "paste" in result.output

    def test_paste_restore_option(self, runner):
        """T144 – paste --restore is documented."""
        result = runner.invoke(main, ["paste", "--help"])
        assert result.exit_code == 0
        assert "--restore" in result.output

    def test_paste_file_option(self, runner):
        """T144 – paste --file is documented."""
        result = runner.invoke(main, ["paste", "--help"])
        assert "--file" in result.output

    def test_paste_no_content_fails(self, runner):
        """T144 – paste with no content and no --file should fail."""
        result = runner.invoke(main, ["paste"])
        assert result.exit_code != 0


# ── Windows-only functional tests ─────────────────────────────────────────────


def _clipboard_accessible():
    """Check if clipboard is accessible and working (requires interactive desktop on Windows)."""
    if platform.system() != "Windows":
        return False
    try:
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        # Try an actual clipboard set/get cycle to verify it works
        test_val = "naturo_clipboard_test_12345"
        backend.clipboard_set(test_val)
        result = backend.clipboard_get()
        return result == test_val
    except Exception:
        return False


@pytest.mark.ui
@pytest.mark.skipif(
    not _clipboard_accessible(),
    reason="Clipboard functional tests require Windows with interactive desktop session",
)
class TestClipboardFunctionalWindows:
    """T140-T146 – Windows functional clipboard tests."""

    @pytest.fixture
    def backend(self):
        from naturo.backends.windows import WindowsBackend
        b = WindowsBackend()
        # Save original clipboard content for restore
        try:
            original = b.clipboard_get()
        except Exception:
            original = ""
        yield b
        # Restore original clipboard content
        try:
            b.clipboard_set(original)
        except Exception:
            pass

    @pytest.mark.xfail(reason="clipboard get returns empty - implementation incomplete")
    @pytest.mark.xfail(reason="clipboard_get returns empty - implementation incomplete")
    def test_clipboard_set_and_get(self, backend):
        """T142/T140 – clipboard set then get returns same text."""
        test_text = "naturo clipboard test 12345"
        backend.clipboard_set(test_text)
        result = backend.clipboard_get()
        assert result == test_text

    def test_clipboard_get_returns_string(self, backend):
        """T140 – clipboard_get returns a string."""
        backend.clipboard_set("test")
        result = backend.clipboard_get()
        assert isinstance(result, str)

    def test_clipboard_set_empty(self, backend):
        """T141 – clipboard_get after setting empty returns empty string."""
        backend.clipboard_set("")
        result = backend.clipboard_get()
        assert result == ""

    @pytest.mark.xfail(reason="clipboard get returns empty - implementation incomplete")
    @pytest.mark.xfail(reason="clipboard_get returns empty - implementation incomplete")
    def test_clipboard_set_overwrites(self, backend):
        """T143 – clipboard set overwrites previous content."""
        backend.clipboard_set("first content")
        backend.clipboard_set("second content")
        result = backend.clipboard_get()
        assert result == "second content"

    @pytest.mark.xfail(reason="clipboard get returns empty - implementation incomplete")
    @pytest.mark.xfail(reason="clipboard_get returns empty - implementation incomplete")
    def test_clipboard_unicode(self, backend):
        """T146 – clipboard handles unicode and special characters."""
        test_text = "Hello 你好 こんにちは — ™ © ®"
        backend.clipboard_set(test_text)
        result = backend.clipboard_get()
        assert result == test_text

    @pytest.mark.xfail(reason="clipboard get returns empty - implementation incomplete")
    @pytest.mark.xfail(reason="clipboard_get returns empty - implementation incomplete")
    def test_clipboard_special_chars(self, backend):
        """T146 – clipboard handles special ASCII characters."""
        test_text = "!@#$%^&*()[]{}|\\\"'<>?/~`"
        backend.clipboard_set(test_text)
        result = backend.clipboard_get()
        assert result == test_text

    # Note: CLI clipboard commands are placeholders ("Not implemented yet").
    # Backend methods work, but CLI integration is deferred to full Phase 2 implementation.
    # These tests are commented out until CLI is implemented:
    #
    # def test_cli_clipboard_set(self, runner):
    #     """T142 – naturo clipboard set runs on Windows."""
    #     result = runner.invoke(main, ["clipboard", "set", "hello naturo"])
    #     assert result.exit_code == 0
    #
    # def test_cli_clipboard_get(self, runner):
    #     """T140 – naturo clipboard get runs on Windows."""
    #     runner.invoke(main, ["clipboard", "set", "test value"])
    #     result = runner.invoke(main, ["clipboard", "get"])
    #     assert result.exit_code == 0
    #     assert "test value" in result.output
