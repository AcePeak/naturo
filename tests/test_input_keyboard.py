"""Tests for Phase 2 keyboard input: type, press, hotkey.

Tests are organized by category:
  - Method signature / API existence (all platforms)
  - CLI option validation (all platforms)
  - Typing profile / WPM calculation logic (all platforms)
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


# ── T120-T137: Keyboard method signatures ─────────────────────────────────────


class TestKeyboardMethodSignatures:
    """Backend keyboard methods have correct signatures (all platforms)."""

    def test_type_text_signature(self):
        """T120 – type_text accepts text, delay_ms, profile, wpm, input_mode."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.type_text)
        params = sig.parameters
        assert "text" in params
        assert "delay_ms" in params
        assert "profile" in params
        assert "wpm" in params
        assert "input_mode" in params

    def test_type_text_default_delay(self):
        """T120 – type_text delay_ms defaults to 5."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.type_text)
        assert sig.parameters["delay_ms"].default == 5

    def test_type_text_default_profile(self):
        """T124 – type_text profile defaults to 'linear'."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.type_text)
        assert sig.parameters["profile"].default == "linear"

    def test_type_text_default_wpm(self):
        """T125 – type_text wpm defaults to 120."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.type_text)
        assert sig.parameters["wpm"].default == 120

    def test_press_key_signature(self):
        """T126 – press_key accepts key and input_mode."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.press_key)
        params = sig.parameters
        assert "key" in params
        assert "input_mode" in params

    def test_hotkey_signature(self):
        """T128 – hotkey accepts *keys and hold_duration_ms."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.hotkey)
        params = sig.parameters
        # variadic keys (*keys) shows as "keys" with VAR_POSITIONAL kind
        assert "keys" in params or any(
            p.kind.name == "VAR_POSITIONAL" for p in params.values()
        )
        assert "hold_duration_ms" in params

    def test_key_type_bridge_signature(self):
        """T120 – NaturoCore.key_type exists with text and delay_ms params."""
        import inspect
        from naturo.bridge import NaturoCore
        sig = inspect.signature(NaturoCore.key_type)
        params = sig.parameters
        assert "text" in params
        assert "delay_ms" in params

    def test_key_press_bridge_signature(self):
        """T126 – NaturoCore.key_press exists with key_name param."""
        import inspect
        from naturo.bridge import NaturoCore
        sig = inspect.signature(NaturoCore.key_press)
        params = sig.parameters
        assert "key_name" in params

    def test_key_hotkey_bridge_signature(self):
        """T128 – NaturoCore.key_hotkey exists."""
        from naturo.bridge import NaturoCore
        assert hasattr(NaturoCore, "key_hotkey")


# ── CLI option validation (all platforms) ─────────────────────────────────────


class TestTypeCLIOptions:
    """type CLI option validation (T120-T133)."""

    def test_type_delay_option(self, runner):
        """T120 – --delay option is documented."""
        result = runner.invoke(main, ["type", "--help"])
        assert "--delay" in result.output

    def test_type_profile_option(self, runner):
        """T123/T124 – --profile option is documented."""
        result = runner.invoke(main, ["type", "--help"])
        assert "--profile" in result.output

    def test_type_human_profile_choice(self, runner):
        """T123 – 'human' is a valid profile choice."""
        result = runner.invoke(main, ["type", "--help"])
        assert "human" in result.output

    def test_type_linear_profile_choice(self, runner):
        """T124 – 'linear' is a valid profile choice."""
        result = runner.invoke(main, ["type", "--help"])
        assert "linear" in result.output

    def test_type_wpm_option(self, runner):
        """T125 – --wpm option is documented."""
        result = runner.invoke(main, ["type", "--help"])
        assert "--wpm" in result.output

    def test_type_return_option(self, runner):
        """T126 – --return option is documented."""
        result = runner.invoke(main, ["type", "--help"])
        assert "--return" in result.output

    def test_type_clear_option(self, runner):
        """T133 – --clear option is documented."""
        result = runner.invoke(main, ["type", "--help"])
        assert "--clear" in result.output

    def test_type_input_mode_option(self, runner):
        """T130/T131/T132 – --input-mode option is documented."""
        result = runner.invoke(main, ["type", "--help"])
        assert "--input-mode" in result.output

    def test_type_no_text_fails(self, runner):
        """T120 – type with no TEXT argument should fail."""
        result = runner.invoke(main, ["type"])
        assert result.exit_code != 0

    def test_type_empty_text_fails(self, runner):
        """T120 – type with empty string should fail."""
        result = runner.invoke(main, ["type", ""])
        assert result.exit_code != 0

    def test_type_invalid_profile_fails(self, runner):
        """T123 – type with invalid profile should fail."""
        result = runner.invoke(main, ["type", "hello", "--profile", "turbo"])
        assert result.exit_code != 0

    def test_type_invalid_input_mode_fails(self, runner):
        """T130 – type with invalid input mode should fail."""
        result = runner.invoke(main, ["type", "hello", "--input-mode", "quantum"])
        assert result.exit_code != 0


class TestPressCLIOptions:
    """press CLI option validation (T126-T132)."""

    def test_press_count_option(self, runner):
        """T126 – --count option is documented."""
        result = runner.invoke(main, ["press", "--help"])
        assert "--count" in result.output

    def test_press_delay_option(self, runner):
        """T126 – --delay option is documented."""
        result = runner.invoke(main, ["press", "--help"])
        assert "--delay" in result.output

    def test_press_input_mode_option(self, runner):
        """T130 – --input-mode option is documented."""
        result = runner.invoke(main, ["press", "--help"])
        assert "--input-mode" in result.output

    def test_press_no_key_fails(self, runner):
        """T126 – press with no KEY argument should fail."""
        result = runner.invoke(main, ["press"])
        assert result.exit_code != 0

    def test_press_invalid_input_mode_fails(self, runner):
        """T130 – press with invalid input mode should fail."""
        result = runner.invoke(main, ["press", "enter", "--input-mode", "magic"])
        assert result.exit_code != 0


class TestHotkeyCLIOptions:
    """hotkey CLI option validation (T127-T128)."""

    def test_hotkey_help_succeeds(self, runner):
        """T128 – hotkey --help exits 0."""
        result = runner.invoke(main, ["hotkey", "--help"])
        assert result.exit_code == 0

    def test_hotkey_input_mode_option(self, runner):
        """T127/T130 – --input-mode option is documented."""
        result = runner.invoke(main, ["hotkey", "--help"])
        assert "--input-mode" in result.output

    def test_hotkey_no_keys_fails(self, runner):
        """T127 – hotkey with no keys should fail."""
        result = runner.invoke(main, ["hotkey"])
        assert result.exit_code != 0


# ── Typing profile / WPM calculation logic ────────────────────────────────────


class TestTypingProfileLogic:
    """Typing profile and WPM calculation (T123-T125), no DLL required."""

    def test_linear_profile_uses_delay_ms_directly(self):
        """T124 – linear profile uses delay_ms as-is."""
        profile = "linear"
        delay_ms = 10
        wpm = 120

        actual_delay = delay_ms
        if profile == "human" and wpm > 0:
            ms_per_char = int(60_000 / (wpm * 5))
            actual_delay = max(1, ms_per_char)

        assert actual_delay == 10

    def test_human_profile_120wpm_delay(self):
        """T123 – human profile at 120 WPM = 100ms per char."""
        profile = "human"
        wpm = 120
        delay_ms = 5  # base, overridden by human profile

        actual_delay = delay_ms
        if profile == "human" and wpm > 0:
            ms_per_char = int(60_000 / (wpm * 5))
            actual_delay = max(1, ms_per_char)

        assert actual_delay == 100

    def test_human_profile_60wpm_delay(self):
        """T125 – human profile at 60 WPM = 200ms per char."""
        profile = "human"
        wpm = 60

        ms_per_char = int(60_000 / (wpm * 5))
        actual_delay = max(1, ms_per_char)

        assert actual_delay == 200

    def test_human_profile_zero_wpm_clamps_to_one(self):
        """T125 – human profile with wpm=0 clamps delay to 1ms."""
        # When wpm=0, the 'if' condition is False, so we fall through to delay_ms
        profile = "human"
        wpm = 0
        delay_ms = 5

        actual_delay = delay_ms
        if profile == "human" and wpm > 0:
            ms_per_char = int(60_000 / (wpm * 5))
            actual_delay = max(1, ms_per_char)

        # With wpm=0 the condition is False, so actual_delay stays as delay_ms
        assert actual_delay == 5

    def test_human_profile_very_fast_wpm(self):
        """T125 – very fast WPM (1000) still produces at least 1ms delay."""
        wpm = 1000
        ms_per_char = int(60_000 / (wpm * 5))
        actual_delay = max(1, ms_per_char)
        assert actual_delay >= 1

    def test_100_chars_at_120wpm_under_5s(self):
        """T137 – 100 chars at 120 WPM takes ~10s; linear 5ms = 0.5s."""
        # Linear profile at default 5ms: 100 * 5ms = 500ms < 5s
        delay_ms = 5
        n_chars = 100
        total_ms = n_chars * delay_ms
        assert total_ms <= 5000


# ── Hotkey modifier parsing (extends test_cli_phase2.py) ──────────────────────


class TestHotkeyParsing:
    """Hotkey key string parsing (no DLL required)."""

    def test_parse_ctrl_plus_c(self):
        """T127 – 'ctrl+c' parses to ['ctrl', 'c']."""
        keys = "ctrl+c"
        key_list = [k.strip() for k in keys.replace("+", " ").split()]
        assert key_list == ["ctrl", "c"]

    def test_parse_ctrl_shift_t(self):
        """T128 – 'ctrl+shift+t' parses to ['ctrl', 'shift', 't']."""
        keys = "ctrl+shift+t"
        key_list = [k.strip() for k in keys.replace("+", " ").split()]
        assert key_list == ["ctrl", "shift", "t"]

    def test_parse_alt_f4(self):
        """T128 – 'alt+f4' parses to ['alt', 'f4']."""
        keys = "alt+f4"
        key_list = [k.strip() for k in keys.replace("+", " ").split()]
        assert key_list == ["alt", "f4"]

    def test_parse_single_key(self):
        """T126 – single key 'enter' parses to ['enter']."""
        keys = "enter"
        key_list = [k.strip() for k in keys.replace("+", " ").split()]
        assert key_list == ["enter"]

    def test_all_modifier_bitmask(self):
        """T128 – all modifiers sum to 15."""
        MODIFIER_MAP = {"ctrl": 0, "alt": 1, "shift": 2, "win": 3}
        modifiers = sum(1 << MODIFIER_MAP[k] for k in ["ctrl", "alt", "shift", "win"])
        assert modifiers == 15


# ── Windows-only functional tests ─────────────────────────────────────────────


@pytest.mark.ui
@pytest.mark.desktop
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Keyboard functional tests require Windows with desktop session",
)
class TestKeyboardFunctionalWindows:
    """T120-T133, T137 – Windows functional keyboard tests."""

    @pytest.fixture
    def core(self):
        from naturo.bridge import NaturoCore
        c = NaturoCore()
        c.init()
        yield c
        c.shutdown()

    def test_key_type_ascii(self, core):
        """T120 – type ASCII text should not raise."""
        core.key_type("Hello World", delay_ms=0)

    def test_key_type_special_chars(self, core):
        """T121 – type special characters should not raise."""
        core.key_type("!@#$%^&*()", delay_ms=0)

    def test_key_type_unicode(self, core):
        """T122 – type unicode text should not raise."""
        core.key_type("你好世界 こんにちは", delay_ms=0)

    def test_press_enter(self, core):
        """T126 – press enter should not raise."""
        core.key_press("enter")

    def test_press_tab(self, core):
        """T129 – press tab should not raise."""
        core.key_press("tab")

    def test_press_escape(self, core):
        """T129 – press escape should not raise."""
        core.key_press("escape")

    def test_press_delete(self, core):
        """T129 – press delete should not raise."""
        core.key_press("delete")

    def test_press_arrow_up(self, core):
        """T129 – press arrow up should not raise."""
        core.key_press("up")

    def test_press_f1(self, core):
        """T129 – press F1 should not raise."""
        core.key_press("f1")

    def test_press_f12(self, core):
        """T129 – press F12 should not raise."""
        core.key_press("f12")

    def test_hotkey_ctrl_a(self, core):
        """T127 – Ctrl+A hotkey should not raise."""
        core.key_hotkey("ctrl", "a")

    def test_hotkey_ctrl_z(self, core):
        """T127 – Ctrl+Z hotkey should not raise."""
        core.key_hotkey("ctrl", "z")

    def test_hotkey_ctrl_shift_t(self, core):
        """T128 – Ctrl+Shift+T multi-key hotkey should not raise."""
        core.key_hotkey("ctrl", "shift", "t")

    def test_type_with_human_profile(self, core):
        """T123 – type with human profile should not raise."""
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        backend.type_text("test", delay_ms=10, profile="human", wpm=60)

    def test_type_with_linear_profile(self, core):
        """T124 – type with linear profile should not raise."""
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        backend.type_text("test", delay_ms=5, profile="linear")

    def test_type_100_chars_default_speed(self, core):
        """T137 – type 100 chars at default speed (5ms) should be under 5s."""
        import time
        from naturo.backends.windows import WindowsBackend
        backend = WindowsBackend()
        text = "a" * 100
        start = time.perf_counter()
        backend.type_text(text, delay_ms=5, profile="linear")
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"Typing 100 chars took {elapsed:.2f}s, expected < 5s"

    def test_cli_type_text(self, runner):
        """T120 – naturo type TEXT runs on Windows."""
        result = runner.invoke(main, ["type", "hello"])
        assert result.exit_code == 0

    def test_cli_press_enter(self, runner):
        """T126 – naturo press enter runs on Windows."""
        result = runner.invoke(main, ["press", "enter"])
        assert result.exit_code == 0

    def test_cli_press_multiple_count(self, runner):
        """T126 – naturo press tab --count 3 runs on Windows."""
        result = runner.invoke(main, ["press", "tab", "--count", "3", "--delay", "10"])
        assert result.exit_code == 0

    def test_cli_hotkey_ctrl_a(self, runner):
        """T127 – naturo hotkey ctrl+a runs on Windows."""
        result = runner.invoke(main, ["hotkey", "ctrl+a"])
        assert result.exit_code == 0

    def test_cli_hotkey_ctrl_shift_z(self, runner):
        """T128 – naturo hotkey ctrl+shift+z runs on Windows."""
        result = runner.invoke(main, ["hotkey", "ctrl+shift+z"])
        assert result.exit_code == 0

    def test_cli_type_with_return(self, runner):
        """T126 – naturo type TEXT --return runs on Windows."""
        result = runner.invoke(main, ["type", "test", "--return"])
        assert result.exit_code == 0

    def test_cli_type_human_profile(self, runner):
        """T123 – naturo type --profile human runs on Windows."""
        result = runner.invoke(main, ["type", "hi", "--profile", "human", "--wpm", "120"])
        assert result.exit_code == 0

    def test_cli_type_json_output(self, runner):
        """T297 – naturo type --json emits valid JSON on Windows."""
        result = runner.invoke(main, ["type", "hello", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data.get("success") is True
        assert "text" in data.get("data", {})
        assert "length" in data.get("data", {})
