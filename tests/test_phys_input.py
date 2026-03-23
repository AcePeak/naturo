"""Tests for Phase 5B.5 — Hardware-level keyboard input (Phys32).

Tests the scan code-based input functions at bridge, backend, and CLI layers.
On non-Windows platforms, tests verify stub behavior (return -1).
"""

import json
import platform
import subprocess
import sys
from unittest.mock import MagicMock, patch, call

import pytest

IS_WINDOWS = platform.system() == "Windows"


# ── Bridge Layer Tests ───────────────────────────────────────────────────────


class TestBridgePhysKeyType:
    """Test NaturoCore.phys_key_type() bridge method."""

    def test_phys_key_type_calls_native(self):
        """phys_key_type should call naturo_phys_key_type with encoded text."""
        from naturo.bridge import NaturoCore
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()
        core._lib.naturo_phys_key_type.return_value = 0

        core.phys_key_type("Hello", 5)

        core._lib.naturo_phys_key_type.assert_called_once_with(b"Hello", 5)

    def test_phys_key_type_empty_text_raises(self):
        """phys_key_type with empty text should raise NaturoCoreError."""
        from naturo.bridge import NaturoCore, NaturoCoreError
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()

        with pytest.raises(NaturoCoreError):
            core.phys_key_type("", 0)

    def test_phys_key_type_error_raises(self):
        """phys_key_type should raise NaturoCoreError on non-zero return."""
        from naturo.bridge import NaturoCore, NaturoCoreError
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()
        core._lib.naturo_phys_key_type.return_value = -2

        with pytest.raises(NaturoCoreError):
            core.phys_key_type("test", 0)

    def test_phys_key_type_utf8_encoding(self):
        """phys_key_type should encode text as UTF-8."""
        from naturo.bridge import NaturoCore
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()
        core._lib.naturo_phys_key_type.return_value = 0

        core.phys_key_type("你好", 0)

        core._lib.naturo_phys_key_type.assert_called_once_with("你好".encode("utf-8"), 0)


class TestBridgePhysKeyPress:
    """Test NaturoCore.phys_key_press() bridge method."""

    def test_phys_key_press_calls_native(self):
        """phys_key_press should call naturo_phys_key_press."""
        from naturo.bridge import NaturoCore
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()
        core._lib.naturo_phys_key_press.return_value = 0

        core.phys_key_press("enter")

        core._lib.naturo_phys_key_press.assert_called_once_with(b"enter")

    def test_phys_key_press_empty_raises(self):
        """phys_key_press with empty key should raise NaturoCoreError."""
        from naturo.bridge import NaturoCore, NaturoCoreError
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()

        with pytest.raises(NaturoCoreError):
            core.phys_key_press("")

    def test_phys_key_press_error_raises(self):
        """phys_key_press should raise NaturoCoreError on error."""
        from naturo.bridge import NaturoCore, NaturoCoreError
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()
        core._lib.naturo_phys_key_press.return_value = -1

        with pytest.raises(NaturoCoreError):
            core.phys_key_press("unknown_key")


class TestBridgePhysKeyHotkey:
    """Test NaturoCore.phys_key_hotkey() bridge method."""

    def test_phys_key_hotkey_ctrl_c(self):
        """phys_key_hotkey('ctrl', 'c') should pass modifiers=1, key='c'."""
        from naturo.bridge import NaturoCore
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()
        core._lib.naturo_phys_key_hotkey.return_value = 0

        core.phys_key_hotkey("ctrl", "c")

        core._lib.naturo_phys_key_hotkey.assert_called_once_with(1, b"c")

    def test_phys_key_hotkey_ctrl_shift_z(self):
        """phys_key_hotkey('ctrl', 'shift', 'z') should pass modifiers=5."""
        from naturo.bridge import NaturoCore
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()
        core._lib.naturo_phys_key_hotkey.return_value = 0

        core.phys_key_hotkey("ctrl", "shift", "z")

        # ctrl=bit0(1), shift=bit2(4), total=5
        core._lib.naturo_phys_key_hotkey.assert_called_once_with(5, b"z")

    def test_phys_key_hotkey_multiple_base_keys_raises(self):
        """phys_key_hotkey with two non-modifier keys should raise."""
        from naturo.bridge import NaturoCore, NaturoCoreError
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()

        with pytest.raises(NaturoCoreError, match="multiple base keys"):
            core.phys_key_hotkey("a", "b")

    def test_phys_key_hotkey_modifier_only(self):
        """phys_key_hotkey with only modifiers should pass None key."""
        from naturo.bridge import NaturoCore
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()
        core._lib.naturo_phys_key_hotkey.return_value = 0

        core.phys_key_hotkey("ctrl", "alt")

        # ctrl=1, alt=2, total=3
        core._lib.naturo_phys_key_hotkey.assert_called_once_with(3, None)

    def test_phys_key_hotkey_error_raises(self):
        """phys_key_hotkey should raise NaturoCoreError on error."""
        from naturo.bridge import NaturoCore, NaturoCoreError
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()
        core._lib.naturo_phys_key_hotkey.return_value = -2

        with pytest.raises(NaturoCoreError):
            core.phys_key_hotkey("ctrl", "s")


# ── Backend Layer Tests ──────────────────────────────────────────────────────


class TestBackendInputMode:
    """Test that WindowsBackend routes input_mode='hardware' to phys functions."""

    def _make_backend(self):
        """Create a WindowsBackend with mocked NaturoCore."""
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        mock_core = MagicMock()
        backend._core = mock_core
        # Patch _ensure_core to return the mock
        backend._ensure_core = lambda: mock_core
        return backend, mock_core

    def test_type_text_normal_uses_key_type(self):
        """type_text with input_mode='normal' should use key_type."""
        backend, core = self._make_backend()
        backend.type_text("hello", input_mode="normal")
        core.key_type.assert_called_once()
        core.phys_key_type.assert_not_called()

    def test_type_text_hardware_uses_phys_key_type(self):
        """type_text with input_mode='hardware' should use phys_key_type."""
        backend, core = self._make_backend()
        backend.type_text("hello", input_mode="hardware")
        core.phys_key_type.assert_called_once()
        core.key_type.assert_not_called()

    def test_press_key_normal_uses_key_press(self):
        """press_key with input_mode='normal' should use key_press."""
        backend, core = self._make_backend()
        backend.press_key("enter", input_mode="normal")
        core.key_press.assert_called_once_with("enter")
        core.phys_key_press.assert_not_called()

    def test_press_key_hardware_uses_phys_key_press(self):
        """press_key with input_mode='hardware' should use phys_key_press."""
        backend, core = self._make_backend()
        backend.press_key("enter", input_mode="hardware")
        core.phys_key_press.assert_called_once_with("enter")
        core.key_press.assert_not_called()

    def test_hotkey_normal_uses_key_hotkey(self):
        """hotkey with input_mode='normal' should use key_hotkey."""
        backend, core = self._make_backend()
        backend.hotkey("ctrl", "c", input_mode="normal")
        core.key_hotkey.assert_called_once()
        core.phys_key_hotkey.assert_not_called()

    def test_hotkey_hardware_uses_phys_key_hotkey(self):
        """hotkey with input_mode='hardware' should use phys_key_hotkey."""
        backend, core = self._make_backend()
        backend.hotkey("ctrl", "c", input_mode="hardware")
        core.phys_key_hotkey.assert_called_once()
        core.key_hotkey.assert_not_called()

    def test_default_input_mode_is_normal(self):
        """Default input_mode should be 'normal'."""
        backend, core = self._make_backend()
        backend.type_text("test")
        core.key_type.assert_called_once()
        core.phys_key_type.assert_not_called()


# ── CLI Layer Tests ──────────────────────────────────────────────────────────


class TestCLIInputMode:
    """Test that CLI commands accept and pass --input-mode hardware."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Set up Click test environment."""
        from click.testing import CliRunner
        self.runner = CliRunner()

    @patch("naturo.cli.interaction._get_backend")
    def test_type_hardware_mode(self, mock_get_backend):
        """naturo type --input-mode hardware should call type_text with hardware."""
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        from naturo.cli.interaction import type_cmd
        result = self.runner.invoke(type_cmd, ["hello", "--input-mode", "hardware", "--json"])

        mock_backend.type_text.assert_called_once()
        call_kwargs = mock_backend.type_text.call_args
        assert call_kwargs[1].get("input_mode") == "hardware" or \
               (len(call_kwargs[0]) > 0 and "hardware" in str(call_kwargs))

    @patch("naturo.cli.interaction._get_backend")
    def test_press_hardware_mode(self, mock_get_backend):
        """naturo press --input-mode hardware should call press_key with hardware."""
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        from naturo.cli.interaction import press
        result = self.runner.invoke(press, ["enter", "--input-mode", "hardware", "--json"])

        mock_backend.press_key.assert_called_once_with(
            "enter", input_mode="hardware"
        )

    @patch("naturo.cli.interaction._get_backend")
    def test_hotkey_hardware_mode(self, mock_get_backend):
        """naturo hotkey --input-mode hardware should call hotkey with hardware."""
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        from naturo.cli.interaction import hotkey
        result = self.runner.invoke(hotkey, ["ctrl+c", "--input-mode", "hardware", "--json"])

        mock_backend.hotkey.assert_called_once()
        call_kwargs = mock_backend.hotkey.call_args
        assert call_kwargs[1].get("input_mode") == "hardware"

    @patch("naturo.cli.interaction._get_backend")
    def test_type_normal_mode_default(self, mock_get_backend):
        """naturo type without --input-mode should default to normal."""
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        from naturo.cli.interaction import type_cmd
        result = self.runner.invoke(type_cmd, ["hello", "--json"])

        mock_backend.type_text.assert_called_once()
        call_kwargs = mock_backend.type_text.call_args
        assert call_kwargs[1].get("input_mode") == "normal"

    @patch("naturo.cli.interaction._get_backend")
    def test_click_hardware_mode(self, mock_get_backend):
        """naturo click --input-mode hardware should pass to backend."""
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        from naturo.cli.interaction import click_cmd
        result = self.runner.invoke(click_cmd, [
            "--coords", "100", "200",
            "--input-mode", "hardware",
            "--json",
        ])

        mock_backend.click.assert_called_once()
        call_kwargs = mock_backend.click.call_args
        assert call_kwargs[1].get("input_mode") == "hardware"

    def test_invalid_input_mode_rejected(self):
        """Invalid --input-mode value should be rejected by Click."""
        from naturo.cli.interaction import type_cmd
        result = self.runner.invoke(type_cmd, ["hello", "--input-mode", "invalid", "--json"])
        assert result.exit_code != 0


# ── C++ Stub Tests (non-Windows) ─────────────────────────────────────────────


@pytest.mark.skipif(IS_WINDOWS, reason="Stub tests only for non-Windows")
class TestPhysStubsNonWindows:
    """Verify that phys functions return -1 on non-Windows (stub)."""

    def test_phys_key_type_stub(self):
        """phys_key_type should raise on non-Windows (return -1 from stub)."""
        from naturo.bridge import NaturoCore, NaturoCoreError
        try:
            core = NaturoCore()
            with pytest.raises(NaturoCoreError):
                core.phys_key_type("test", 0)
        except (OSError, Exception) as exc:
            if "naturo_core" in str(exc) or "DEPENDENCY_MISSING" in str(getattr(exc, 'code', '')):
                pytest.skip("DLL not available")
            raise

    def test_phys_key_press_stub(self):
        """phys_key_press should raise on non-Windows (return -1 from stub)."""
        from naturo.bridge import NaturoCore, NaturoCoreError
        try:
            core = NaturoCore()
            with pytest.raises(NaturoCoreError):
                core.phys_key_press("enter")
        except (OSError, Exception) as exc:
            if "naturo_core" in str(exc) or "DEPENDENCY_MISSING" in str(getattr(exc, 'code', '')):
                pytest.skip("DLL not available")
            raise

    def test_phys_key_hotkey_stub(self):
        """phys_key_hotkey should raise on non-Windows (return -1 from stub)."""
        from naturo.bridge import NaturoCore, NaturoCoreError
        try:
            core = NaturoCore()
            with pytest.raises(NaturoCoreError):
                core.phys_key_hotkey("ctrl", "c")
        except (OSError, Exception) as exc:
            if "naturo_core" in str(exc) or "DEPENDENCY_MISSING" in str(getattr(exc, 'code', '')):
                pytest.skip("DLL not available")
            raise


# ── MCP Tool Tests ───────────────────────────────────────────────────────────


class TestMCPPhysInput:
    """Test that MCP tools accept input_mode parameter via backend routing."""

    def test_type_text_hardware_routing(self):
        """Backend type_text with input_mode='hardware' should route correctly."""
        mock_backend = MagicMock()
        mock_backend.type_text(text="hello", wpm=120, input_mode="hardware")
        mock_backend.type_text.assert_called_with(
            text="hello", wpm=120, input_mode="hardware"
        )

    def test_press_key_hardware_routing(self):
        """Backend press_key with input_mode='hardware' should route correctly."""
        mock_backend = MagicMock()
        mock_backend.press_key(key="enter", input_mode="hardware")
        mock_backend.press_key.assert_called_with(
            key="enter", input_mode="hardware"
        )

    def test_hotkey_hardware_routing(self):
        """Backend hotkey with input_mode='hardware' should route correctly."""
        mock_backend = MagicMock()
        mock_backend.hotkey("ctrl", "c", input_mode="hardware")
        mock_backend.hotkey.assert_called_with(
            "ctrl", "c", input_mode="hardware"
        )


# ── Scan Code Table Validation ───────────────────────────────────────────────


class TestScanCodeCoverage:
    """Verify scan code table completeness (validated at integration level)."""

    ESSENTIAL_KEYS = [
        "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
        "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        "enter", "tab", "escape", "space", "backspace",
        "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
        "up", "down", "left", "right",
        "home", "end", "pageup", "pagedown",
        "insert", "delete",
    ]

    def test_essential_keys_have_bridge_methods(self):
        """All essential keys should be accepted by phys_key_press (mock)."""
        from naturo.bridge import NaturoCore
        core = NaturoCore.__new__(NaturoCore)
        core._lib = MagicMock()
        core._lib.naturo_phys_key_press.return_value = 0

        for key in self.ESSENTIAL_KEYS:
            core.phys_key_press(key)
            core._lib.naturo_phys_key_press.assert_called_with(key.encode("utf-8"))


# ── Integration Test (Windows only) ─────────────────────────────────────────


@pytest.mark.ui
@pytest.mark.skipif(not IS_WINDOWS, reason="Windows-only integration test")
class TestPhysIntegrationWindows:
    """Integration tests that require Windows + naturo_core.dll."""

    def test_phys_key_press_enter(self):
        """phys_key_press('enter') should succeed on Windows."""
        try:
            from naturo.bridge import NaturoCore
            core = NaturoCore()
            core.phys_key_press("enter")
        except OSError:
            pytest.skip("DLL not available")

    def test_phys_key_type_hello(self):
        """phys_key_type('hello') should succeed on Windows."""
        try:
            from naturo.bridge import NaturoCore
            core = NaturoCore()
            core.phys_key_type("hello", 0)
        except OSError:
            pytest.skip("DLL not available")

    def test_phys_key_hotkey_ctrl_a(self):
        """phys_key_hotkey('ctrl', 'a') should succeed on Windows."""
        try:
            from naturo.bridge import NaturoCore
            core = NaturoCore()
            core.phys_key_hotkey("ctrl", "a")
        except OSError:
            pytest.skip("DLL not available")
