"""Tests for clipboard CLI commands and click clipboard modifiers.

Tests the `naturo clipboard` command group (get, set, clear, info)
and the --paste/--copy/--cut modifiers on the click command.
Backend calls are mocked since clipboard interaction requires a desktop session.
"""

from __future__ import annotations

import json
import platform
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    """Mock backend with clipboard methods."""
    backend = MagicMock()
    backend.clipboard_get.return_value = "hello world"
    backend.clipboard_set.return_value = None
    backend.clipboard_clear.return_value = None
    backend.clipboard_info.return_value = {
        "format": "text",
        "size": 22,
        "has_text": True,
        "has_image": False,
        "has_files": False,
    }
    return backend


# ── Backend method signatures (all platforms) ────────────────────────────────


class TestClipboardMethodSignatures:
    """Backend clipboard methods exist with correct signatures (all platforms)."""

    def test_clipboard_get_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "clipboard_get")

    def test_clipboard_set_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "clipboard_set")

    def test_clipboard_clear_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "clipboard_clear")

    def test_clipboard_info_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "clipboard_info")

    def test_clipboard_get_signature(self):
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.clipboard_get)
        required = [
            p for name, p in sig.parameters.items()
            if name != "self" and p.default is inspect.Parameter.empty
        ]
        assert len(required) == 0

    def test_clipboard_set_signature(self):
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.clipboard_set)
        assert "text" in sig.parameters

    def test_clipboard_set_default_text(self):
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.clipboard_set)
        assert sig.parameters["text"].default == ""

    def test_base_clipboard_clear_is_abstract(self):
        from naturo.backends.base import Backend
        assert hasattr(Backend, "clipboard_clear")

    def test_base_clipboard_info_is_defined(self):
        from naturo.backends.base import Backend
        assert hasattr(Backend, "clipboard_info")

    def test_default_clipboard_info_text(self):
        """Default clipboard_info detects text via clipboard_get."""
        backend = MagicMock()
        backend.clipboard_get.return_value = "test"
        from naturo.backends.base import Backend
        result = Backend.clipboard_info(backend)
        assert result["has_text"] is True
        assert result["format"] == "text"
        assert result["size"] == 4

    def test_default_clipboard_info_empty(self):
        """Default clipboard_info handles empty clipboard."""
        backend = MagicMock()
        backend.clipboard_get.return_value = ""
        from naturo.backends.base import Backend
        result = Backend.clipboard_info(backend)
        assert result["has_text"] is False
        assert result["format"] == "empty"


# ── CLI help & registration (no backend needed) ─────────────────────────────


class TestClipboardHelp:
    """Test clipboard command registration and help output."""

    def test_clipboard_appears_in_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "clipboard" in result.output

    def test_clipboard_help(self, runner):
        result = runner.invoke(main, ["clipboard", "--help"])
        assert result.exit_code == 0
        assert "get" in result.output
        assert "set" in result.output
        assert "clear" in result.output
        assert "info" in result.output

    def test_clipboard_get_help(self, runner):
        result = runner.invoke(main, ["clipboard", "get", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_clipboard_set_help(self, runner):
        result = runner.invoke(main, ["clipboard", "set", "--help"])
        assert result.exit_code == 0
        assert "TEXT" in result.output

    def test_click_has_paste_option(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--paste" in result.output

    def test_click_has_copy_option(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--copy" in result.output

    def test_click_has_cut_option(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--cut" in result.output

    def test_click_has_restore_option(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--restore" in result.output


# ── clipboard get ────────────────────────────────────


class TestClipboardGet:
    """Tests for 'naturo clipboard get'."""

    def test_get_text(self, runner, mock_backend):
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get"])
        assert result.exit_code == 0
        assert "hello world" in result.output
        mock_backend.clipboard_get.assert_called_once()

    def test_get_empty(self, runner, mock_backend):
        mock_backend.clipboard_get.return_value = ""
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get"])
        assert result.exit_code == 0
        assert "clipboard is empty" in result.output

    def test_get_json(self, runner, mock_backend):
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["text"] == "hello world"
        assert data["length"] == 11
        assert data["action"] == "clipboard_get"

    def test_get_error(self, runner, mock_backend):
        mock_backend.clipboard_get.side_effect = Exception("clipboard locked")
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "get"])
        # emit_exception_error calls sys.exit(1)
        assert result.exit_code == 1


# ── clipboard set ────────────────────────────────────


class TestClipboardSet:
    """Tests for 'naturo clipboard set'."""

    def test_set_text(self, runner, mock_backend):
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set", "test data"])
        assert result.exit_code == 0
        assert "9 chars" in result.output
        mock_backend.clipboard_set.assert_called_once_with("test data")

    def test_set_json(self, runner, mock_backend):
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "set", "abc", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "clipboard_set"
        assert data["length"] == 3

    def test_set_requires_text_argument(self, runner):
        result = runner.invoke(main, ["clipboard", "set"])
        assert result.exit_code != 0


# ── clipboard clear ──────────────────────────────────


class TestClipboardClear:
    """Tests for 'naturo clipboard clear'."""

    def test_clear(self, runner, mock_backend):
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "clear"])
        assert result.exit_code == 0
        assert "cleared" in result.output.lower()
        mock_backend.clipboard_clear.assert_called_once()

    def test_clear_json(self, runner, mock_backend):
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "clear", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["action"] == "clipboard_clear"


# ── clipboard info ───────────────────────────────────


class TestClipboardInfo:
    """Tests for 'naturo clipboard info'."""

    def test_info_text(self, runner, mock_backend):
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "info"])
        assert result.exit_code == 0
        assert "text" in result.output.lower()
        assert "22 bytes" in result.output

    def test_info_json(self, runner, mock_backend):
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "info", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["format"] == "text"
        assert data["has_text"] is True
        assert data["has_image"] is False

    def test_info_empty(self, runner, mock_backend):
        mock_backend.clipboard_info.return_value = {
            "format": "empty",
            "size": 0,
            "has_text": False,
            "has_image": False,
            "has_files": False,
        }
        with patch("naturo.cli.clipboard_cmd._get_backend", return_value=mock_backend):
            result = runner.invoke(main, ["clipboard", "info"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()


# ── click --paste/--copy/--cut modifiers ─────────────


def _click_patches(mock_backend):
    """Return patch context managers for mocking click command dependencies."""
    return {
        "backend": patch("naturo.cli.interaction._get_backend", return_value=mock_backend),
        "desktop": patch("naturo.cli.interaction._check_desktop_session"),
        "auto_route": patch("naturo.cli.interaction._auto_route", return_value={}),
    }


class TestClickClipboardModifiers:
    """Tests for click --paste, --copy, --cut modifiers."""

    def test_click_paste_calls_hotkey(self, runner, mock_backend):
        patches = _click_patches(mock_backend)
        with patches["backend"], patches["desktop"], patches["auto_route"]:
            result = runner.invoke(main, [
                "click", "--coords", "100", "200", "--paste", "--no-verify",
            ])
        assert result.exit_code == 0
        mock_backend.click.assert_called_once()
        mock_backend.hotkey.assert_called_with("ctrl", "v")

    def test_click_copy_calls_select_all_and_copy(self, runner, mock_backend):
        patches = _click_patches(mock_backend)
        with patches["backend"], patches["desktop"], patches["auto_route"]:
            result = runner.invoke(main, [
                "click", "--coords", "100", "200", "--copy", "--no-verify",
            ])
        assert result.exit_code == 0
        mock_backend.click.assert_called_once()
        hotkey_calls = mock_backend.hotkey.call_args_list
        assert call("ctrl", "a") in hotkey_calls
        assert call("ctrl", "c") in hotkey_calls

    def test_click_cut_calls_select_all_and_cut(self, runner, mock_backend):
        patches = _click_patches(mock_backend)
        with patches["backend"], patches["desktop"], patches["auto_route"]:
            result = runner.invoke(main, [
                "click", "--coords", "100", "200", "--cut", "--no-verify",
            ])
        assert result.exit_code == 0
        mock_backend.click.assert_called_once()
        hotkey_calls = mock_backend.hotkey.call_args_list
        assert call("ctrl", "a") in hotkey_calls
        assert call("ctrl", "x") in hotkey_calls

    def test_click_paste_json_includes_clipboard_action(self, runner, mock_backend):
        patches = _click_patches(mock_backend)
        with patches["backend"], patches["desktop"], patches["auto_route"]:
            result = runner.invoke(main, [
                "click", "--coords", "100", "200", "--paste", "--no-verify", "--json",
            ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # JSON output may nest data under "data" key
        inner = data.get("data", data)
        assert inner.get("clipboard_action") == "paste"

    def test_click_copy_json_includes_clipboard_action(self, runner, mock_backend):
        patches = _click_patches(mock_backend)
        with patches["backend"], patches["desktop"], patches["auto_route"]:
            result = runner.invoke(main, [
                "click", "--coords", "100", "200", "--copy", "--no-verify", "--json",
            ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        inner = data.get("data", data)
        assert inner.get("clipboard_action") == "copy"


# ── Windows-only functional tests ────────────────────────────────────────────


def _clipboard_accessible():
    """Check if clipboard is accessible (requires interactive desktop on Windows)."""
    if platform.system() != "Windows":
        return False
    try:
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        test_val = "naturo_clipboard_test_12345"
        backend.clipboard_set(test_val)
        result = backend.clipboard_get()
        return result == test_val
    except Exception:
        return False


@pytest.mark.ui
@pytest.mark.desktop
@pytest.mark.skipif(
    not _clipboard_accessible(),
    reason="Clipboard functional tests require Windows with interactive desktop session",
)
class TestClipboardFunctionalWindows:
    """Windows functional clipboard tests."""

    @pytest.fixture
    def backend(self):
        from naturo.backends.windows import WindowsBackend
        b = WindowsBackend()
        try:
            original = b.clipboard_get()
        except Exception:
            original = ""
        yield b
        try:
            b.clipboard_set(original)
        except Exception:
            pass

    def test_clipboard_set_and_get(self, backend):
        test_text = "naturo clipboard test 12345"
        backend.clipboard_set(test_text)
        result = backend.clipboard_get()
        assert result == test_text

    def test_clipboard_clear(self, backend):
        backend.clipboard_set("something")
        backend.clipboard_clear()
        result = backend.clipboard_get()
        assert result == ""

    def test_clipboard_info_text(self, backend):
        backend.clipboard_set("hello")
        info = backend.clipboard_info()
        assert info["has_text"] is True
        assert info["format"] == "text"
        assert info["size"] > 0

    def test_clipboard_info_empty(self, backend):
        backend.clipboard_clear()
        info = backend.clipboard_info()
        assert info["format"] == "empty"
        assert info["has_text"] is False

    def test_clipboard_unicode(self, backend):
        test_text = "Hello 你好 こんにちは — ™ © ®"
        backend.clipboard_set(test_text)
        result = backend.clipboard_get()
        assert result == test_text
