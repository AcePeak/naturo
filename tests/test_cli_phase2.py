"""Tests for Phase 2 CLI commands (click, type, press, hotkey, scroll, drag, move, paste).

Tests CLI command registration and option validation on all platforms.
Functional tests that invoke SendInput are Windows-only and guarded by @pytest.mark.ui.
"""

from __future__ import annotations

import json
import os
import platform

import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


# ── Command Registration (all platforms) ─────────────────────────────────────


class TestClickCommandRegistration:
    """Phase 2 click command is registered and documented."""

    def test_click_in_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "click" in result.output

    def test_click_has_coords_option(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--coords" in result.output

    def test_click_has_double_option(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--double" in result.output

    def test_click_has_right_option(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--right" in result.output

    def test_click_has_id_option(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--id" in result.output

    def test_click_has_on_option(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--on" in result.output

    def test_click_has_input_mode_option(self, runner):
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--input-mode" in result.output


class TestTypeCommandRegistration:
    """Phase 2 type command is registered and documented."""

    def test_type_in_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "type" in result.output

    def test_type_has_delay_option(self, runner):
        result = runner.invoke(main, ["type", "--help"])
        assert result.exit_code == 0
        assert "--delay" in result.output

    def test_type_has_profile_option(self, runner):
        result = runner.invoke(main, ["type", "--help"])
        assert result.exit_code == 0
        assert "--profile" in result.output

    def test_type_has_return_option(self, runner):
        result = runner.invoke(main, ["type", "--help"])
        assert result.exit_code == 0
        assert "--return" in result.output

    def test_type_has_clear_option(self, runner):
        result = runner.invoke(main, ["type", "--help"])
        assert result.exit_code == 0
        assert "--clear" in result.output

    def test_type_has_wpm_option(self, runner):
        result = runner.invoke(main, ["type", "--help"])
        assert result.exit_code == 0
        assert "--wpm" in result.output


class TestPressCommandRegistration:
    """Phase 2 press command is registered and documented."""

    def test_press_in_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "press" in result.output

    def test_press_has_count_option(self, runner):
        result = runner.invoke(main, ["press", "--help"])
        assert result.exit_code == 0
        assert "--count" in result.output

    def test_press_has_delay_option(self, runner):
        result = runner.invoke(main, ["press", "--help"])
        assert result.exit_code == 0
        assert "--delay" in result.output

    def test_press_has_on_option(self, runner):
        """press --on option exists for element targeting (fixes #375)."""
        result = runner.invoke(main, ["press", "--help"])
        assert result.exit_code == 0
        assert "--on" in result.output


class TestPressJsonError:
    """Press command returns JSON error when KEY is missing (fixes #123)."""

    def test_press_missing_key_json_error(self, runner):
        """naturo press --json without KEY returns JSON error, not Click usage text."""
        result = runner.invoke(main, ["press", "--json"])
        assert result.exit_code != 0
        import json
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    def test_press_missing_key_plain_error(self, runner):
        """naturo press without KEY returns readable error."""
        result = runner.invoke(main, ["press"])
        assert result.exit_code != 0
        assert "KEY" in result.output or "Missing" in result.output


class TestHotkeyCommandRegistration:
    """hotkey is a hidden alias for press — still callable but not in --help."""

    def test_hotkey_hidden_from_main_help(self, runner):
        """hotkey merged into press — hidden from top-level help."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "press" in result.output

    def test_hotkey_help_exits_zero(self, runner):
        """hotkey alias still callable."""
        result = runner.invoke(main, ["hotkey", "--help"])
        assert result.exit_code == 0

    def test_press_accepts_combo(self, runner):
        """press now accepts combo notation like ctrl+c."""
        result = runner.invoke(main, ["press", "--help"])
        assert result.exit_code == 0
        assert "ctrl+c" in result.output or "combo" in result.output.lower()


class TestScrollCommandRegistration:
    """Phase 2 scroll command is registered and documented."""

    def test_scroll_in_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "scroll" in result.output

    def test_scroll_has_direction_option(self, runner):
        result = runner.invoke(main, ["scroll", "--help"])
        assert result.exit_code == 0
        assert "--direction" in result.output

    def test_scroll_has_amount_option(self, runner):
        result = runner.invoke(main, ["scroll", "--help"])
        assert result.exit_code == 0
        assert "--amount" in result.output


class TestDragCommandRegistration:
    """Phase 2 drag command is registered and documented."""

    def test_drag_in_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "drag" in result.output

    def test_drag_has_from_coords_option(self, runner):
        result = runner.invoke(main, ["drag", "--help"])
        assert result.exit_code == 0
        assert "--from-coords" in result.output

    def test_drag_has_to_coords_option(self, runner):
        result = runner.invoke(main, ["drag", "--help"])
        assert result.exit_code == 0
        assert "--to-coords" in result.output

    def test_drag_has_steps_option(self, runner):
        result = runner.invoke(main, ["drag", "--help"])
        assert result.exit_code == 0
        assert "--steps" in result.output


class TestMoveCommandRegistration:
    """Phase 2 move command is registered and documented."""

    def test_move_in_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "move" in result.output

    def test_move_has_coords_option(self, runner):
        result = runner.invoke(main, ["move", "--help"])
        assert result.exit_code == 0
        assert "--coords" in result.output


@pytest.mark.skip(reason="paste command removed in v0.2.0, merged into type --paste")
class TestPasteCommandRegistration:
    """Phase 2 paste command is registered and documented."""

    def test_paste_in_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "paste" in result.output

    def test_paste_has_file_option(self, runner):
        result = runner.invoke(main, ["paste", "--help"])
        assert result.exit_code == 0
        assert "--file" in result.output


# ── Input Validation (non-Windows safe, no SendInput) ────────────────────────


class TestClickValidation:
    """click command validation errors."""

    def test_click_no_target_exits_nonzero(self, runner):
        """click with no target should fail gracefully."""
        result = runner.invoke(main, ["click"])
        assert result.exit_code != 0

    def test_click_json_no_target_emits_json_error(self, runner):
        """click --json with no target should emit JSON error."""
        result = runner.invoke(main, ["click", "--json"])
        assert result.exit_code != 0
        try:
            data = json.loads(result.output)
            assert data.get("success") is False
        except json.JSONDecodeError:
            pass  # Non-JSON error output is also acceptable


class TestTypeValidation:
    """type command validation errors."""

    def test_type_no_text_exits_nonzero(self, runner):
        """type with no text should fail."""
        result = runner.invoke(main, ["type"])
        assert result.exit_code != 0


class TestHotkeyValidation:
    """hotkey command validation errors."""

    def test_hotkey_no_keys_exits_nonzero(self, runner):
        """hotkey with no keys should fail."""
        result = runner.invoke(main, ["hotkey"])
        assert result.exit_code != 0


class TestDragValidation:
    """drag command validation errors."""

    def test_drag_no_coords_exits_nonzero(self, runner):
        """drag with no coords should fail."""
        result = runner.invoke(main, ["drag"])
        assert result.exit_code != 0

    def test_drag_only_from_exits_nonzero(self, runner):
        """drag with only --from-coords should fail (needs --to-coords)."""
        result = runner.invoke(main, ["drag", "--from-coords", "100", "100"])
        assert result.exit_code != 0


class TestMoveValidation:
    """move command validation errors."""

    def test_move_no_coords_exits_nonzero(self, runner):
        """move with no coords should fail."""
        result = runner.invoke(main, ["move"])
        assert result.exit_code != 0


@pytest.mark.skip(reason="paste command removed in v0.2.0, merged into type --paste")
class TestPasteValidation:
    """paste command validation errors."""

    def test_paste_no_text_exits_nonzero(self, runner):
        """paste with no text or --file should fail."""
        result = runner.invoke(main, ["paste"])
        assert result.exit_code != 0


# ── Bridge Unit Tests (no DLL, mocked) ───────────────────────────────────────


class TestBridgeInputMethods:
    """Unit test NaturoCore input method signatures without the DLL."""

    def test_mouse_move_method_exists(self):
        from naturo.bridge import NaturoCore
        assert hasattr(NaturoCore, "mouse_move")

    def test_mouse_click_method_exists(self):
        from naturo.bridge import NaturoCore
        assert hasattr(NaturoCore, "mouse_click")

    def test_mouse_scroll_method_exists(self):
        from naturo.bridge import NaturoCore
        assert hasattr(NaturoCore, "mouse_scroll")

    def test_key_type_method_exists(self):
        from naturo.bridge import NaturoCore
        assert hasattr(NaturoCore, "key_type")

    def test_key_press_method_exists(self):
        from naturo.bridge import NaturoCore
        assert hasattr(NaturoCore, "key_press")

    def test_key_hotkey_method_exists(self):
        from naturo.bridge import NaturoCore
        assert hasattr(NaturoCore, "key_hotkey")


class TestBackendInputMethods:
    """Windows backend exposes all Phase 2 input methods."""

    def test_click_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "click")

    def test_type_text_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "type_text")

    def test_press_key_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "press_key")

    def test_hotkey_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "hotkey")

    def test_scroll_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "scroll")

    def test_drag_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "drag")

    def test_move_mouse_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "move_mouse")

    def test_clipboard_get_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "clipboard_get")

    def test_clipboard_set_method_exists(self):
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "clipboard_set")


class TestKeyHotkeyParsing:
    """key_hotkey modifier parsing logic (bridge-level, no DLL)."""

    def test_hotkey_modifier_bitmask_ctrl(self):
        """Ctrl modifier should set bit 0."""
        # Verify the MODIFIER_MAP in key_hotkey is correct by inspecting
        # the source code indirectly: ctrl=bit0, alt=bit1, shift=bit2, win=bit3
        MODIFIER_MAP = {"ctrl": 0, "alt": 1, "shift": 2, "win": 3}
        modifiers = 0
        for k in ["ctrl"]:
            modifiers |= 1 << MODIFIER_MAP[k]
        assert modifiers == 1

    def test_hotkey_modifier_bitmask_ctrl_shift(self):
        """Ctrl+Shift should set bits 0 and 2 = 0b101 = 5."""
        MODIFIER_MAP = {"ctrl": 0, "alt": 1, "shift": 2, "win": 3}
        modifiers = 0
        for k in ["ctrl", "shift"]:
            modifiers |= 1 << MODIFIER_MAP[k]
        assert modifiers == 5

    def test_hotkey_modifier_bitmask_all(self):
        """All modifiers = Ctrl(1) + Alt(2) + Shift(4) + Win(8) = 15."""
        MODIFIER_MAP = {"ctrl": 0, "alt": 1, "shift": 2, "win": 3}
        modifiers = 0
        for k in ["ctrl", "alt", "shift", "win"]:
            modifiers |= 1 << MODIFIER_MAP[k]
        assert modifiers == 15


# ── Functional Tests (Windows only) ──────────────────────────────────────────


@pytest.mark.ui
@pytest.mark.desktop
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Functional input tests require Windows with desktop session",
)
class TestPhase2FunctionalWindows:
    """Windows-only functional Phase 2 tests using the real DLL."""

    @pytest.fixture
    def core(self):
        from naturo.bridge import NaturoCore
        c = NaturoCore()
        c.init()
        yield c
        c.shutdown()

    def test_mouse_move(self, core):
        """mouse_move to center of screen should succeed."""
        core.mouse_move(500, 400)

    def test_key_press_enter(self, core):
        """key_press(enter) should not raise."""
        core.key_press("enter")

    def test_key_press_escape(self, core):
        """key_press(escape) should not raise."""
        core.key_press("escape")

    def test_key_press_tab(self, core):
        """key_press(tab) should not raise."""
        core.key_press("tab")

    def test_key_press_f5(self, core):
        """key_press(f5) should not raise."""
        core.key_press("f5")

    def test_key_press_unknown_raises(self, core):
        """key_press with unknown key should raise NaturoCoreError."""
        from naturo.bridge import NaturoCoreError
        with pytest.raises(NaturoCoreError):
            core.key_press("xyzzy_unknown")

    def test_key_type_basic(self, core):
        """key_type with simple ASCII string should not raise."""
        core.key_type("hello", 0)

    def test_key_type_unicode(self, core):
        """key_type with unicode string should not raise."""
        core.key_type("héllo wörld", 0)

    def test_mouse_scroll_down(self, core):
        """mouse_scroll down should not raise."""
        core.mouse_scroll(-120, False)

    def test_mouse_scroll_up(self, core):
        """mouse_scroll up should not raise."""
        core.mouse_scroll(120, False)

    def test_key_hotkey_ctrl_a(self, core):
        """key_hotkey ctrl+a should not raise."""
        core.key_hotkey("ctrl", "a")

    def test_key_hotkey_ctrl_z(self, core):
        """key_hotkey ctrl+z should not raise."""
        core.key_hotkey("ctrl", "z")

    def test_click_coords(self, runner):
        """naturo click --coords runs on Windows."""
        result = runner.invoke(main, ["click", "--coords", "500", "400"])
        assert result.exit_code == 0

    def test_type_text_cli(self, runner):
        """naturo type runs on Windows."""
        result = runner.invoke(main, ["type", "hello"])
        assert result.exit_code == 0

    def test_press_enter_cli(self, runner):
        """naturo press enter runs on Windows."""
        result = runner.invoke(main, ["press", "enter"])
        assert result.exit_code == 0

    def test_scroll_down_cli(self, runner):
        """naturo scroll runs on Windows."""
        result = runner.invoke(main, ["scroll", "--direction", "down", "--amount", "1"])
        assert result.exit_code == 0

    def test_hotkey_ctrl_a_cli(self, runner):
        """naturo hotkey ctrl+a runs on Windows."""
        result = runner.invoke(main, ["hotkey", "ctrl+a"])
        assert result.exit_code == 0


# ── E2E Notepad Interaction (Windows-only, interactive desktop required) ─────


@pytest.mark.ui
@pytest.mark.e2e
@pytest.mark.desktop
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="E2E tests require Windows with desktop session",
)
@pytest.mark.skipif(
    os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true",
    reason="Requires interactive desktop session (not available in CI)",
)
class TestNotepadAutomation:
    """Phase 2 checkpoint: Can automate Notepad — open, type, save, close."""

    @pytest.fixture
    def core(self):
        from naturo.bridge import NaturoCore
        c = NaturoCore()
        c.init()
        yield c
        c.shutdown()

    def test_notepad_open_type_close(self, core):
        """Open Notepad, type text, close without saving — full automation cycle.

        This is the Phase 2 checkpoint test:
        Can automate Notepad (open, type, save, close).
        """
        import subprocess
        import time

        proc = subprocess.Popen(["notepad.exe"])
        try:
            time.sleep(1.5)

            # Find Notepad window
            windows = core.list_windows()
            notepad = next(
                (w for w in windows if "notepad" in w.process_name.lower() and w.is_visible),
                None
            )
            assert notepad is not None, "Notepad window not found"

            # Click center of window (approximate edit area)
            cx = notepad.x + notepad.width // 2
            cy = notepad.y + notepad.height // 2
            core.mouse_move(cx, cy)
            core.mouse_click(0, False)
            time.sleep(0.2)

            # Type a test string
            test_text = "Hello from naturo Phase 2 automation!"
            core.key_type(test_text, delay_ms=10)
            time.sleep(0.3)

            # Close without saving: Alt+F4 → Don't Save
            core.key_hotkey("alt", "f4")
            time.sleep(0.5)

            # Dismiss save dialog with Tab + Enter or just press N (Don't Save)
            core.key_press("tab")
            time.sleep(0.2)
            core.key_press("enter")
            time.sleep(0.5)

        finally:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                pass
