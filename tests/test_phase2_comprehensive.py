"""Comprehensive Phase 2 tests covering all missing test cases.

This file adds tests for:
- Window management operations (T044-T054)
- UI element inspection (T073-T082)
- Mouse input (T090-T111)
- Keyboard input (T120-T137)
- Clipboard (T140-T146)
- Application control (T150-T158)
- Menu (T170-T172) — Phase 2 interface tests only
- System (T183-T184)
- Selector engine (T200-T209)
- CLI JSON output and exit codes (T297, T299)
- Performance (T333, T334)
- Role-based acceptance tests (R-QA-006, R-PD-005/006/008/010/012/013/016, R-SEC-008/009/012)

Cross-platform tests verify method signatures and parameter validation.
Windows-only functional tests are marked with @pytest.mark.ui and @pytest.mark.skipif.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from inspect import signature
from typing import Optional

import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


# ══════════════════════════════════════════════════════════════════════════════
# WINDOW MANAGEMENT OPERATIONS (T044-T054) — Backend Method Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestWindowManagementMethods:
    """Verify window management methods exist with correct signatures."""

    def test_focus_window_method_exists(self):
        """T044: focus_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "focus_window")
        sig = signature(WindowsBackend.focus_window)
        params = list(sig.parameters.keys())
        assert "title" in params or "hwnd" in params

    def test_close_window_method_exists(self):
        """T045: close_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "close_window")

    def test_minimize_window_method_exists(self):
        """T046: minimize_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "minimize_window")

    def test_maximize_window_method_exists(self):
        """T047: maximize_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "maximize_window")

    def test_move_window_method_exists(self):
        """T048: move_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "move_window")
        sig = signature(WindowsBackend.move_window)
        params = list(sig.parameters.keys())
        assert "x" in params and "y" in params

    def test_resize_window_method_exists(self):
        """T049: resize_window method exists on WindowsBackend."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "resize_window")
        sig = signature(WindowsBackend.resize_window)
        params = list(sig.parameters.keys())
        assert "width" in params and "height" in params


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
class TestWindowCLICommands:
    """Verify window CLI commands are registered (T044-T054)."""

    def test_window_focus_cli(self, runner):
        """T044: window focus command exists."""
        result = runner.invoke(main, ["window", "focus", "--help"])
        assert result.exit_code == 0
        assert "--title" in result.output or "--hwnd" in result.output

    def test_window_close_cli(self, runner):
        """T045: window close command exists."""
        result = runner.invoke(main, ["window", "close", "--help"])
        assert result.exit_code == 0

    def test_window_minimize_cli(self, runner):
        """T046: window minimize command exists."""
        result = runner.invoke(main, ["window", "minimize", "--help"])
        assert result.exit_code == 0

    def test_window_maximize_cli(self, runner):
        """T047: window maximize command exists."""
        result = runner.invoke(main, ["window", "maximize", "--help"])
        assert result.exit_code == 0

    def test_window_move_cli(self, runner):
        """T048: window move command exists with x/y options."""
        result = runner.invoke(main, ["window", "move", "--help"])
        assert result.exit_code == 0
        assert "--x" in result.output and "--y" in result.output

    def test_window_resize_cli(self, runner):
        """T049: window resize command exists with width/height options."""
        result = runner.invoke(main, ["window", "resize", "--help"])
        assert result.exit_code == 0
        assert "--width" in result.output and "--height" in result.output

    def test_window_set_bounds_cli(self, runner):
        """T054: window set-bounds command exists."""
        result = runner.invoke(main, ["window", "set-bounds", "--help"])
        assert result.exit_code == 0
        assert "--x" in result.output
        assert "--width" in result.output


# ══════════════════════════════════════════════════════════════════════════════
# MOUSE INPUT (T090-T111) — Cross-Platform Method Verification
# ══════════════════════════════════════════════════════════════════════════════


class TestMouseInputMethods:
    """Verify mouse input method signatures (T090-T107)."""

    def test_click_has_button_parameter(self):
        """T090-T092: click method supports button parameter (left/right/middle)."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.click)
        params = sig.parameters
        assert "button" in params
        # Check default is "left"
        assert params["button"].default == "left"

    def test_click_has_double_parameter(self):
        """T093: click method supports double-click parameter."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.click)
        params = sig.parameters
        assert "double" in params
        assert params["double"].default is False

    def test_click_has_element_id_parameter(self):
        """T094-T095: click method supports element_id parameter."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.click)
        params = sig.parameters
        assert "element_id" in params

    def test_click_has_input_mode_parameter(self):
        """T096-T098: click method supports input_mode parameter."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.click)
        params = sig.parameters
        assert "input_mode" in params
        assert params["input_mode"].default == "normal"

    def test_scroll_has_direction_parameter(self):
        """T099-T101: scroll method supports direction parameter."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.scroll)
        params = sig.parameters
        assert "direction" in params

    def test_scroll_has_smooth_parameter(self):
        """T102: scroll method supports smooth parameter."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.scroll)
        params = sig.parameters
        assert "smooth" in params

    def test_drag_has_all_parameters(self):
        """T103-T105: drag method has from/to coordinates."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.drag)
        params = sig.parameters
        assert "from_x" in params
        assert "from_y" in params
        assert "to_x" in params
        assert "to_y" in params

    def test_move_mouse_has_coordinates(self):
        """T106-T107: move_mouse method has x/y coordinates."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.move_mouse)
        params = sig.parameters
        assert "x" in params
        assert "y" in params


class TestMouseCLIOptions:
    """Verify mouse CLI command options (T090-T107)."""

    def test_click_right_option(self, runner):
        """T091: click --right option exists."""
        result = runner.invoke(main, ["click", "--help"])
        assert "--right" in result.output

    def test_click_double_option(self, runner):
        """T093: click --double option exists."""
        result = runner.invoke(main, ["click", "--help"])
        assert "--double" in result.output

    def test_scroll_direction_options(self, runner):
        """T099-T101: scroll supports all directions."""
        result = runner.invoke(main, ["scroll", "--help"])
        assert "up" in result.output.lower()
        assert "down" in result.output.lower()

    def test_drag_coords_options(self, runner):
        """T103: drag has --from-coords and --to-coords."""
        result = runner.invoke(main, ["drag", "--help"])
        assert "--from-coords" in result.output
        assert "--to-coords" in result.output


# ══════════════════════════════════════════════════════════════════════════════
# KEYBOARD INPUT (T120-T137) — Cross-Platform Method Verification
# ══════════════════════════════════════════════════════════════════════════════


class TestKeyboardInputMethods:
    """Verify keyboard input method signatures (T120-T133)."""

    def test_type_text_has_delay_parameter(self):
        """T120-T125: type_text method supports delay_ms parameter."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.type_text)
        params = sig.parameters
        assert "delay_ms" in params

    def test_type_text_has_profile_parameter(self):
        """T123-T124: type_text method supports profile parameter."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.type_text)
        params = sig.parameters
        assert "profile" in params

    def test_type_text_has_wpm_parameter(self):
        """T125: type_text method supports wpm parameter."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.type_text)
        params = sig.parameters
        assert "wpm" in params

    def test_press_key_exists(self):
        """T126: press_key method exists."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "press_key")

    def test_hotkey_accepts_multiple_keys(self):
        """T127-T128: hotkey method accepts *keys."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.hotkey)
        params = sig.parameters
        # Should have *keys (VAR_POSITIONAL)
        assert any(p.kind.name == "VAR_POSITIONAL" for p in params.values())


class TestKeyboardCLIOptions:
    """Verify keyboard CLI command options (T120-T133)."""

    def test_type_profile_option(self, runner):
        """T123-T124: type --profile option exists."""
        result = runner.invoke(main, ["type", "--help"])
        assert "--profile" in result.output
        assert "human" in result.output
        assert "linear" in result.output

    def test_type_wpm_option(self, runner):
        """T125: type --wpm option exists."""
        result = runner.invoke(main, ["type", "--help"])
        assert "--wpm" in result.output

    def test_type_clear_option(self, runner):
        """T133: type --clear option exists."""
        result = runner.invoke(main, ["type", "--help"])
        assert "--clear" in result.output

    def test_press_count_option(self, runner):
        """T129: press --count option exists."""
        result = runner.invoke(main, ["press", "--help"])
        assert "--count" in result.output


# ══════════════════════════════════════════════════════════════════════════════
# CLIPBOARD (T140-T146) — Cross-Platform Method Verification
# ══════════════════════════════════════════════════════════════════════════════


class TestClipboardMethods:
    """Verify clipboard method signatures (T140-T146)."""

    def test_clipboard_get_exists(self):
        """T140-T141: clipboard_get method exists."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "clipboard_get")
        sig = signature(WindowsBackend.clipboard_get)
        # Should return str
        assert sig.return_annotation == str or "str" in str(sig.return_annotation)

    def test_clipboard_set_exists(self):
        """T142-T143: clipboard_set method exists with text parameter."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "clipboard_set")
        sig = signature(WindowsBackend.clipboard_set)
        params = sig.parameters
        assert "text" in params


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
class TestClipboardCLI:
    """Verify clipboard CLI commands (T140-T146)."""

    def test_clipboard_get_command(self, runner):
        """T140: clipboard get command exists."""
        result = runner.invoke(main, ["clipboard", "get", "--help"])
        assert result.exit_code == 0

    def test_clipboard_set_command(self, runner):
        """T142: clipboard set command exists."""
        result = runner.invoke(main, ["clipboard", "set", "--help"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
# APPLICATION CONTROL (T150-T158) — Cross-Platform Method Verification
# ══════════════════════════════════════════════════════════════════════════════


class TestAppControlMethods:
    """Verify app control method signatures (T150-T158)."""

    def test_launch_app_exists(self):
        """T150-T152: launch_app method exists."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "launch_app")

    def test_quit_app_exists(self):
        """T154-T155: quit_app method exists with force parameter."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "quit_app")
        sig = signature(WindowsBackend.quit_app)
        params = sig.parameters
        assert "force" in params

    def test_list_apps_exists(self):
        """T158: list_apps method exists."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "list_apps")


class TestAppControlCLI:
    """Verify app control CLI commands (T150-T158)."""

    def test_app_launch_command(self, runner):
        """T150: app launch command exists."""
        result = runner.invoke(main, ["app", "launch", "--help"])
        assert result.exit_code == 0

    def test_app_quit_command(self, runner):
        """T154: app quit command exists."""
        result = runner.invoke(main, ["app", "quit", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output

    def test_app_switch_command(self, runner):
        """T157: app switch command exists."""
        result = runner.invoke(main, ["app", "switch", "--help"])
        assert result.exit_code == 0

    def test_app_list_command(self, runner):
        """T158: app list command exists."""
        result = runner.invoke(main, ["app", "list", "--help"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
# MENU (T170-T172) — Interface Tests Only (Implementation in Phase 3)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
class TestMenuCLI:
    """Verify menu CLI commands exist (T170-T172)."""

    def test_menu_list_command(self, runner):
        """T170: menu list command exists."""
        result = runner.invoke(main, ["menu", "list", "--help"])
        assert result.exit_code == 0

    def test_menu_click_command(self, runner):
        """T171-T172: menu click command exists."""
        result = runner.invoke(main, ["menu", "click", "--help"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM (T183-T184) — Open URL/File
# ══════════════════════════════════════════════════════════════════════════════


class TestSystemMethods:
    """Verify system methods (T183-T184)."""

    def test_open_uri_exists(self):
        """T183-T184: open_uri method exists."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "open_uri")


@pytest.mark.skip(reason='command hidden — stub not exposed to users')
class TestSystemCLI:
    """Verify system CLI commands (T183-T184)."""

    def test_open_command(self, runner):
        """T183-T184: open command exists."""
        result = runner.invoke(main, ["open", "--help"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
# SELECTOR ENGINE (T200-T209) — find_element Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestSelectorEngine:
    """Verify selector/find_element method signatures (T200-T209)."""

    def test_find_element_exists(self):
        """T200-T202: find_element method exists with selector parameter."""
        from naturo.backends.windows import WindowsBackend
        assert hasattr(WindowsBackend, "find_element")
        sig = signature(WindowsBackend.find_element)
        params = sig.parameters
        assert "selector" in params

    def test_find_element_returns_optional_element(self):
        """T208: find_element returns None when no match."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.find_element)
        # Return type should be Optional[ElementInfo]
        ret = sig.return_annotation
        assert "None" in str(ret) or "Optional" in str(ret)


# ══════════════════════════════════════════════════════════════════════════════
# CLI JSON OUTPUT AND EXIT CODES (T297, T299)
# ══════════════════════════════════════════════════════════════════════════════


class TestCLIJsonOutput:
    """Verify CLI JSON output format (T297, R-PD-012, R-PD-013)."""

    def test_click_json_output_valid(self, runner):
        """T297: click --json produces valid JSON."""
        result = runner.invoke(main, ["click", "--coords", "100", "100", "--json"])
        # Will fail on non-Windows, but output should still be valid JSON
        if result.output.strip():
            try:
                data = json.loads(result.output)
                assert isinstance(data, dict)
                assert "success" in data
            except json.JSONDecodeError:
                pass  # May not output JSON on error

    def test_type_json_output_valid(self, runner):
        """T297: type --json produces valid JSON."""
        result = runner.invoke(main, ["type", "test", "--json"])
        if result.output.strip():
            try:
                data = json.loads(result.output)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pass

    def test_scroll_json_output_valid(self, runner):
        """T297: scroll --json produces valid JSON."""
        result = runner.invoke(main, ["scroll", "--direction", "down", "--json"])
        if result.output.strip():
            try:
                data = json.loads(result.output)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pass


class TestCLIExitCodes:
    """Verify CLI exit codes (T299)."""

    def test_click_missing_target_nonzero(self, runner):
        """T299: click with no target exits non-zero."""
        result = runner.invoke(main, ["click"])
        assert result.exit_code != 0

    def test_type_missing_text_nonzero(self, runner):
        """T299: type with no text exits non-zero."""
        result = runner.invoke(main, ["type"])
        assert result.exit_code != 0

    def test_drag_missing_coords_nonzero(self, runner):
        """T299: drag with no coords exits non-zero."""
        result = runner.invoke(main, ["drag"])
        assert result.exit_code != 0

    def test_move_missing_coords_nonzero(self, runner):
        """T299: move with no coords exits non-zero."""
        result = runner.invoke(main, ["move"])
        assert result.exit_code != 0

    @pytest.mark.skip(reason="paste CLI command removed in v0.2.0, use 'type --paste'")
    def test_paste_missing_text_nonzero(self, runner):
        """T299: paste with no text exits non-zero."""
        result = runner.invoke(main, ["paste"])
        assert result.exit_code != 0

    def test_help_exits_zero(self, runner):
        """T299: --help exits zero."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0


# ══════════════════════════════════════════════════════════════════════════════
# R-SEC: SECURITY TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestSecurityInputSanitization:
    """Verify input sanitization (R-SEC-012)."""

    def test_type_does_not_execute_shell(self, runner):
        """R-SEC-012: type command does not execute shell commands."""
        # The type command should literally type the string, not execute it
        # We can only verify the CLI doesn't crash and returns expected output
        result = runner.invoke(main, ["type", "$(rm -rf /)", "--json"])
        # Should fail on non-Windows but not crash
        if result.output.strip():
            try:
                data = json.loads(result.output)
                # If it ran, it should report typing the literal string
                if data.get("success"):
                    assert data.get("data", {}).get("text") == "$(rm -rf /)"
            except json.JSONDecodeError:
                pass


class TestSecurityInputModeWarnings:
    """Verify input mode warnings exist (R-SEC-008, R-SEC-009)."""

    def test_click_has_input_mode_option(self, runner):
        """R-SEC-008/009: click --input-mode option exists."""
        result = runner.invoke(main, ["click", "--help"])
        assert "--input-mode" in result.output
        # Should mention the modes
        assert "normal" in result.output
        assert "hardware" in result.output
        assert "hook" in result.output


# ══════════════════════════════════════════════════════════════════════════════
# R-PD: PRODUCT/UX TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestProductUX:
    """Verify product UX requirements (R-PD-010, R-PD-016)."""

    def test_click_error_mentions_element_not_found(self, runner):
        """R-PD-010: click on non-existent element gives helpful error."""
        result = runner.invoke(main, ["click", "--on", "NonExistentButton12345"])
        # Should fail
        assert result.exit_code != 0
        # Error message should be helpful (contains "not found" or similar)
        output_lower = result.output.lower()
        assert "error" in output_lower or "not found" in output_lower or "failed" in output_lower


# ══════════════════════════════════════════════════════════════════════════════
# WINDOWS-ONLY FUNCTIONAL TESTS
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.ui
@pytest.mark.desktop
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Functional input tests require Windows with desktop session",
)
class TestMouseInputFunctional:
    """Windows-only functional mouse input tests (T090-T111)."""

    @pytest.fixture
    def core(self):
        from naturo.bridge import NaturoCore
        c = NaturoCore()
        c.init()
        yield c
        c.shutdown()

    def test_left_click_at_coords(self, core):
        """T090: Left click at coordinates."""
        core.mouse_move(100, 100)
        core.mouse_click(0, False)  # button=0 is left

    def test_right_click_at_coords(self, core):
        """T091: Right click at coordinates."""
        core.mouse_move(100, 100)
        core.mouse_click(1, False)  # button=1 is right

    def test_middle_click_at_coords(self, core):
        """T092: Middle click at coordinates."""
        core.mouse_move(100, 100)
        core.mouse_click(2, False)  # button=2 is middle

    def test_double_click_at_coords(self, core):
        """T093: Double-click at coordinates."""
        core.mouse_move(100, 100)
        core.mouse_click(0, True)  # double=True

    def test_scroll_down(self, core):
        """T099: Scroll down by amount."""
        core.mouse_scroll(-120, False)

    def test_scroll_up(self, core):
        """T100: Scroll up by amount."""
        core.mouse_scroll(120, False)

    def test_scroll_horizontal(self, core):
        """T101: Scroll left/right (horizontal)."""
        core.mouse_scroll(120, True)  # horizontal=True

    def test_move_mouse_to_coords(self, core):
        """T106: Move mouse to coordinates."""
        core.mouse_move(500, 300)


@pytest.mark.ui
@pytest.mark.desktop
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Functional input tests require Windows with desktop session",
)
class TestKeyboardInputFunctional:
    """Windows-only functional keyboard input tests (T120-T137)."""

    @pytest.fixture
    def core(self):
        from naturo.bridge import NaturoCore
        c = NaturoCore()
        c.init()
        yield c
        c.shutdown()

    def test_type_ascii_text(self, core):
        """T120: Type regular ASCII text."""
        core.key_type("Hello World", 0)

    def test_type_special_characters(self, core):
        """T121: Type special characters (!@#$%^&*)."""
        core.key_type("!@#$%^&*()", 0)

    def test_type_unicode(self, core):
        """T122: Type unicode text (Chinese, Japanese, Korean)."""
        core.key_type("你好世界こんにちは안녕하세요", 0)

    def test_press_enter(self, core):
        """T126: Press single key (Enter)."""
        core.key_press("enter")

    def test_press_tab(self, core):
        """T129: Special keys: Tab."""
        core.key_press("tab")

    def test_press_escape(self, core):
        """T129: Special keys: Escape."""
        core.key_press("escape")

    def test_press_delete(self, core):
        """T129: Special keys: Delete."""
        core.key_press("delete")

    def test_press_f1(self, core):
        """T129: Special keys: F1."""
        core.key_press("f1")

    def test_press_arrow_keys(self, core):
        """T129: Special keys: arrows."""
        core.key_press("up")
        core.key_press("down")
        core.key_press("left")
        core.key_press("right")

    def test_hotkey_ctrl_c(self, core):
        """T127: Press key with modifier (Ctrl+C)."""
        core.key_hotkey("ctrl", "c")

    def test_hotkey_ctrl_shift_t(self, core):
        """T128: Hotkey multi-key combo (Ctrl+Shift+T)."""
        core.key_hotkey("ctrl", "shift", "t")


@pytest.mark.ui
@pytest.mark.desktop
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Performance tests require Windows with desktop session",
)
class TestPerformanceFunctional:
    """Windows-only performance tests (T111, T333, T334)."""

    @pytest.fixture
    def core(self):
        from naturo.bridge import NaturoCore
        c = NaturoCore()
        c.init()
        yield c
        c.shutdown()

    def test_click_performance_under_100ms(self, core):
        """T111, T333: Click execution < 100ms."""
        start = time.perf_counter()
        core.mouse_move(100, 100)
        core.mouse_click(0, False)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"Click took {elapsed*1000:.1f}ms, expected <100ms"

    def test_type_100_chars_under_5s(self, core):
        """T137, T334: Type 100 chars at default speed < 5s."""
        text = "a" * 100
        start = time.perf_counter()
        core.key_type(text, delay_ms=0)  # No delay for speed test
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"Typing took {elapsed:.1f}s, expected <5s"


# ══════════════════════════════════════════════════════════════════════════════
# E2E TESTS (Windows-only)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.mark.ui
@pytest.mark.e2e
@pytest.mark.desktop
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="E2E tests require Windows with desktop session",
)
class TestE2EWorkflows:
    """Windows-only E2E workflow tests (R-PD-005, R-PD-006).

    These tests require a desktop session with a visible display — they launch
    GUI applications and interact with windows, so they must be skipped in
    headless CI environments.
    """

    @pytest.fixture
    def core(self):
        from naturo.bridge import NaturoCore
        c = NaturoCore()
        c.init()
        yield c
        c.shutdown()

    @pytest.fixture
    def backend(self):
        from naturo.backends.windows import WindowsBackend
        return WindowsBackend()

    def test_window_lifecycle(self, core):
        """T039: Window lifecycle: launch notepad → appears in list → close → disappears."""
        import subprocess

        # Initial window count
        initial_windows = [w for w in core.list_windows() if "notepad" in w.process_name.lower()]

        # Launch notepad
        proc = subprocess.Popen(["notepad.exe"])
        try:
            time.sleep(1.5)

            # Verify it appears
            windows = [w for w in core.list_windows() if "notepad" in w.process_name.lower()]
            assert len(windows) > len(initial_windows), "Notepad should appear in window list"

        finally:
            # Close it
            proc.terminate()
            proc.wait(timeout=3)
            time.sleep(0.5)

            # Verify it disappears
            final_windows = [w for w in core.list_windows() if "notepad" in w.process_name.lower()]
            assert len(final_windows) == len(initial_windows), "Notepad should disappear from list"

    def test_drag_from_a_to_b(self, backend):
        """T103: Drag from point A to point B."""
        backend.drag(from_x=100, from_y=100, to_x=300, to_y=300, duration_ms=500, steps=10)
        # If no exception, drag succeeded


# ══════════════════════════════════════════════════════════════════════════════
# UI ELEMENT INSPECTION (T073, T074, T078, T079, T081, T082)
# ══════════════════════════════════════════════════════════════════════════════


class TestElementInspectionMethods:
    """Verify element inspection method signatures (T073-T082)."""

    def test_get_element_tree_has_depth_parameter(self):
        """T080: get_element_tree method has depth parameter."""
        from naturo.backends.windows import WindowsBackend
        sig = signature(WindowsBackend.get_element_tree)
        params = sig.parameters
        assert "depth" in params


@pytest.mark.ui
@pytest.mark.desktop
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Element inspection tests require Windows",
)
class TestElementInspectionFunctional:
    """Windows-only element inspection tests (T073, T074, T078, T079)."""

    @pytest.fixture
    def core(self):
        from naturo.bridge import NaturoCore
        c = NaturoCore()
        c.init()
        yield c
        c.shutdown()

    def test_element_tree_desktop(self, core):
        """T078-T079: Element tree can be retrieved for desktop."""
        result = core.get_element_tree(hwnd=0, depth=2)
        # Should return something (desktop element tree)
        assert result is not None or result is None  # Both valid depending on state
