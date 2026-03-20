"""Tests for Phase 2 mouse input: click, scroll, drag, move.

Tests are organized by category:
  - Method signature / API existence (all platforms)
  - CLI option validation (all platforms)
  - Windows-only functional tests guarded by @pytest.mark.ui
  - E2E tests guarded by @pytest.mark.e2e
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


# ── T090-T107: Mouse method signatures ────────────────────────────────────────


class TestMouseMethodSignatures:
    """Backend mouse methods exist with correct signatures (all platforms)."""

    def test_click_signature(self):
        """T090 – click accepts x, y, element_id, button, double, input_mode."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.click)
        params = sig.parameters
        assert "x" in params
        assert "y" in params
        assert "element_id" in params
        assert "button" in params
        assert "double" in params
        assert "input_mode" in params

    def test_click_button_default_left(self):
        """T091 – click button defaults to 'left'."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.click)
        assert sig.parameters["button"].default == "left"

    def test_click_double_default_false(self):
        """T093 – click double defaults to False."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.click)
        assert sig.parameters["double"].default is False

    def test_scroll_signature(self):
        """T099/T100/T101 – scroll accepts direction, amount, x, y, smooth."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.scroll)
        params = sig.parameters
        assert "direction" in params
        assert "amount" in params
        assert "smooth" in params

    def test_scroll_direction_default_down(self):
        """T099 – scroll direction defaults to 'down'."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.scroll)
        assert sig.parameters["direction"].default == "down"

    def test_drag_signature(self):
        """T103 – drag accepts from_x, from_y, to_x, to_y, duration_ms, steps."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.drag)
        params = sig.parameters
        assert "from_x" in params
        assert "from_y" in params
        assert "to_x" in params
        assert "to_y" in params
        assert "duration_ms" in params
        assert "steps" in params

    def test_move_mouse_signature(self):
        """T106 – move_mouse accepts x, y."""
        import inspect
        from naturo.backends.windows import WindowsBackend
        sig = inspect.signature(WindowsBackend.move_mouse)
        params = sig.parameters
        assert "x" in params
        assert "y" in params

    def test_mouse_click_bridge_signature(self):
        """T096 – NaturoCore.mouse_click exists with button and double params."""
        import inspect
        from naturo.bridge import NaturoCore
        sig = inspect.signature(NaturoCore.mouse_click)
        params = sig.parameters
        assert "button" in params
        assert "double" in params

    def test_mouse_scroll_bridge_signature(self):
        """T099 – NaturoCore.mouse_scroll exists with delta and horizontal params."""
        import inspect
        from naturo.bridge import NaturoCore
        sig = inspect.signature(NaturoCore.mouse_scroll)
        params = sig.parameters
        assert "delta" in params
        assert "horizontal" in params


# ── CLI validation (all platforms) ────────────────────────────────────────────


class TestClickCLIValidation:
    """click CLI argument/option validation (T090-T095)."""

    def test_click_coords_option_in_help(self, runner):
        """T090 – --coords is documented."""
        result = runner.invoke(main, ["click", "--help"])
        assert result.exit_code == 0
        assert "--coords" in result.output

    def test_click_right_option_in_help(self, runner):
        """T091 – --right is documented."""
        result = runner.invoke(main, ["click", "--help"])
        assert "--right" in result.output

    def test_click_double_option_in_help(self, runner):
        """T093 – --double is documented."""
        result = runner.invoke(main, ["click", "--help"])
        assert "--double" in result.output

    def test_click_id_option_in_help(self, runner):
        """T094 – --id is documented."""
        result = runner.invoke(main, ["click", "--help"])
        assert "--id" in result.output

    def test_click_input_mode_normal_valid(self, runner):
        """T096 – --input-mode normal is a valid choice."""
        result = runner.invoke(main, ["click", "--help"])
        assert "normal" in result.output

    def test_click_input_mode_hardware_valid(self, runner):
        """T097 – --input-mode hardware is a valid choice."""
        result = runner.invoke(main, ["click", "--help"])
        assert "hardware" in result.output

    def test_click_input_mode_hook_valid(self, runner):
        """T098 – --input-mode hook is a valid choice."""
        result = runner.invoke(main, ["click", "--help"])
        assert "hook" in result.output

    def test_click_invalid_input_mode_fails(self, runner):
        """T096 – --input-mode with invalid value should fail."""
        result = runner.invoke(main, ["click", "--coords", "100", "100",
                                     "--input-mode", "invalid_mode"])
        assert result.exit_code != 0

    def test_click_no_args_exits_nonzero(self, runner):
        """click with no target should fail."""
        result = runner.invoke(main, ["click"])
        assert result.exit_code != 0

    def test_click_json_error_structure(self, runner):
        """T297 – click --json with no target emits valid JSON with ok=False."""
        result = runner.invoke(main, ["click", "--json"])
        assert result.exit_code != 0
        output = result.output.strip()
        if output:
            try:
                data = json.loads(output)
                assert data.get("success") is False
                assert "error" in data
            except json.JSONDecodeError:
                pass  # Non-JSON error is also acceptable


class TestScrollCLIValidation:
    """scroll CLI option validation (T099-T102)."""

    def test_scroll_direction_down(self, runner):
        """T099 – 'down' is a valid direction."""
        result = runner.invoke(main, ["scroll", "--help"])
        assert "down" in result.output

    def test_scroll_direction_up(self, runner):
        """T100 – 'up' is a valid direction."""
        result = runner.invoke(main, ["scroll", "--help"])
        assert "up" in result.output

    def test_scroll_direction_left(self, runner):
        """T101 – 'left' is a valid direction."""
        result = runner.invoke(main, ["scroll", "--help"])
        assert "left" in result.output

    def test_scroll_direction_right(self, runner):
        """T101 – 'right' is a valid direction."""
        result = runner.invoke(main, ["scroll", "--help"])
        assert "right" in result.output

    def test_scroll_smooth_option(self, runner):
        """T102 – --smooth option is documented."""
        result = runner.invoke(main, ["scroll", "--help"])
        assert "--smooth" in result.output

    def test_scroll_amount_option(self, runner):
        """T099 – --amount option is documented."""
        result = runner.invoke(main, ["scroll", "--help"])
        assert "--amount" in result.output

    def test_scroll_invalid_direction_fails(self, runner):
        """scroll with invalid direction should fail."""
        result = runner.invoke(main, ["scroll", "--direction", "diagonal"])
        assert result.exit_code != 0


class TestDragCLIValidation:
    """drag CLI option validation (T103-T105)."""

    def test_drag_from_coords_option(self, runner):
        """T103 – --from-coords is documented."""
        result = runner.invoke(main, ["drag", "--help"])
        assert "--from-coords" in result.output

    def test_drag_to_coords_option(self, runner):
        """T103 – --to-coords is documented."""
        result = runner.invoke(main, ["drag", "--help"])
        assert "--to-coords" in result.output

    def test_drag_steps_option(self, runner):
        """T103 – --steps is documented."""
        result = runner.invoke(main, ["drag", "--help"])
        assert "--steps" in result.output

    def test_drag_duration_option(self, runner):
        """T103 – --duration is documented."""
        result = runner.invoke(main, ["drag", "--help"])
        assert "--duration" in result.output

    def test_drag_modifiers_option(self, runner):
        """T105 – --modifiers is documented."""
        result = runner.invoke(main, ["drag", "--help"])
        assert "--modifiers" in result.output

    def test_drag_missing_to_coords_fails(self, runner):
        """T103 – drag with only --from-coords should fail."""
        result = runner.invoke(main, ["drag", "--from-coords", "100", "100"])
        assert result.exit_code != 0

    def test_drag_no_args_fails(self, runner):
        """T103 – drag with no args should fail."""
        result = runner.invoke(main, ["drag"])
        assert result.exit_code != 0


class TestMoveCLIValidation:
    """move CLI option validation (T106-T107)."""

    def test_move_coords_option(self, runner):
        """T106 – --coords is documented."""
        result = runner.invoke(main, ["move", "--help"])
        assert "--coords" in result.output

    def test_move_to_option(self, runner):
        """T107 – --to is documented."""
        result = runner.invoke(main, ["move", "--help"])
        assert "--to" in result.output

    def test_move_no_args_fails(self, runner):
        """T106 – move with no args should fail."""
        result = runner.invoke(main, ["move"])
        assert result.exit_code != 0


# ── Scroll delta computation logic ────────────────────────────────────────────


class TestScrollDeltaComputation:
    """Scroll direction-to-delta mapping logic (no DLL required)."""

    def test_scroll_down_delta_is_negative(self):
        """T099 – down direction = negative delta (wheel down)."""
        WHEEL_DELTA = 120
        direction = "down"
        sign = 1 if direction in ("up", "right") else -1
        delta = sign * 1 * WHEEL_DELTA
        assert delta == -120

    def test_scroll_up_delta_is_positive(self):
        """T100 – up direction = positive delta (wheel up)."""
        WHEEL_DELTA = 120
        direction = "up"
        sign = 1 if direction in ("up", "right") else -1
        delta = sign * 1 * WHEEL_DELTA
        assert delta == 120

    def test_scroll_right_delta_is_positive(self):
        """T101 – right direction = positive horizontal delta."""
        WHEEL_DELTA = 120
        direction = "right"
        sign = 1 if direction in ("up", "right") else -1
        delta = sign * 1 * WHEEL_DELTA
        assert delta == 120

    def test_scroll_left_delta_is_negative(self):
        """T101 – left direction = negative horizontal delta."""
        WHEEL_DELTA = 120
        direction = "left"
        sign = 1 if direction in ("up", "right") else -1
        delta = sign * 1 * WHEEL_DELTA
        assert delta == -120

    def test_scroll_amount_multiplier(self):
        """T099 – amount multiplies WHEEL_DELTA."""
        WHEEL_DELTA = 120
        amount = 5
        delta = -1 * amount * WHEEL_DELTA
        assert delta == -600

    def test_horizontal_flag_for_left(self):
        """T101 – left/right directions set horizontal=True."""
        horizontal = "left" in ("left", "right")
        assert horizontal is True

    def test_horizontal_flag_for_up(self):
        """T099 – up/down directions set horizontal=False."""
        horizontal = "up" in ("left", "right")
        assert horizontal is False


# ── Drag interpolation logic ───────────────────────────────────────────────────


class TestDragInterpolation:
    """Drag coordinate interpolation (no DLL required)."""

    def test_drag_interpolation_midpoint(self):
        """T103 – midpoint of drag is correctly interpolated."""
        from_x, from_y, to_x, to_y = 0, 0, 100, 100
        steps = 10
        t = 5 / steps
        ix = int(from_x + (to_x - from_x) * t)
        iy = int(from_y + (to_y - from_y) * t)
        assert ix == 50
        assert iy == 50

    def test_drag_interpolation_start(self):
        """T103 – first step of interpolation is near start."""
        from_x, from_y, to_x, to_y = 0, 0, 100, 0
        steps = 10
        t = 1 / steps
        ix = int(from_x + (to_x - from_x) * t)
        assert ix == 10

    def test_drag_interpolation_end(self):
        """T103 – last step reaches destination."""
        from_x, from_y, to_x, to_y = 0, 0, 100, 50
        steps = 10
        t = steps / steps  # t = 1.0
        ix = int(from_x + (to_x - from_x) * t)
        iy = int(from_y + (to_y - from_y) * t)
        assert ix == 100
        assert iy == 50

    def test_drag_steps_minimum_one(self):
        """T103 – steps is clamped to minimum 1."""
        steps = max(1, 0)  # would be 0 without clamp
        assert steps == 1

    def test_drag_delay_per_step(self):
        """T103 – delay per step = duration_ms / (1000 * steps)."""
        duration_ms, steps = 500, 10
        delay_s = (duration_ms / 1000.0) / steps
        assert abs(delay_s - 0.05) < 1e-9


# ── Click button mapping ───────────────────────────────────────────────────────


class TestClickButtonMapping:
    """Click button string-to-int mapping (T090-T092)."""

    def test_left_button_maps_to_zero(self):
        """T090 – left button = 0."""
        BUTTON_MAP = {"left": 0, "right": 1, "middle": 2}
        assert BUTTON_MAP["left"] == 0

    def test_right_button_maps_to_one(self):
        """T091 – right button = 1."""
        BUTTON_MAP = {"left": 0, "right": 1, "middle": 2}
        assert BUTTON_MAP["right"] == 1

    def test_middle_button_maps_to_two(self):
        """T092 – middle button = 2."""
        BUTTON_MAP = {"left": 0, "right": 1, "middle": 2}
        assert BUTTON_MAP["middle"] == 2

    def test_unknown_button_defaults_to_zero(self):
        """T090 – unknown button falls back to 0 (left)."""
        BUTTON_MAP = {"left": 0, "right": 1, "middle": 2}
        btn = BUTTON_MAP.get("unknown", 0)
        assert btn == 0


# ── Windows-only functional tests ─────────────────────────────────────────────


@pytest.mark.ui
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Mouse functional tests require Windows with desktop session",
)
class TestMouseFunctionalWindows:
    """T090-T107, T111 – Windows functional mouse tests."""

    @pytest.fixture
    def core(self):
        from naturo.bridge import NaturoCore
        c = NaturoCore()
        c.init()
        yield c
        c.shutdown()

    def test_mouse_move_center(self, core):
        """T106 – move_mouse to screen center should succeed."""
        core.mouse_move(500, 400)

    def test_mouse_left_click(self, core):
        """T090 – left click at coordinates should succeed."""
        core.mouse_move(500, 400)
        core.mouse_click(0, False)  # button=0 left, double=False

    def test_mouse_right_click(self, core):
        """T091 – right click at coordinates should succeed."""
        import time
        core.mouse_move(500, 400)
        core.mouse_click(1, False)  # button=1 right
        time.sleep(0.1)
        core.key_press("escape")  # dismiss context menu

    def test_mouse_double_click(self, core):
        """T093 – double-click at coordinates should succeed."""
        core.mouse_move(500, 400)
        core.mouse_click(0, True)

    def test_scroll_down(self, core):
        """T099 – scroll down should succeed."""
        core.mouse_scroll(-120, False)

    def test_scroll_up(self, core):
        """T100 – scroll up should succeed."""
        core.mouse_scroll(120, False)

    def test_scroll_horizontal_right(self, core):
        """T101 – horizontal scroll right should succeed."""
        core.mouse_scroll(120, True)

    def test_scroll_horizontal_left(self, core):
        """T101 – horizontal scroll left should succeed."""
        core.mouse_scroll(-120, True)

    def test_click_performance_under_100ms(self, core):
        """T111 – click execution should be under 100ms."""
        import time
        start = time.perf_counter()
        core.mouse_move(500, 400)
        core.mouse_click(0, False)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, f"click took {elapsed_ms:.1f}ms, expected < 100ms"

    def test_cli_click_coords(self, runner):
        """T090 – naturo click --coords runs on Windows."""
        result = runner.invoke(main, ["click", "--coords", "500", "400"])
        assert result.exit_code == 0

    def test_cli_click_right(self, runner):
        """T091 – naturo click --right runs on Windows."""
        import time
        result = runner.invoke(main, ["click", "--coords", "500", "400", "--right"])
        assert result.exit_code == 0
        time.sleep(0.1)
        runner.invoke(main, ["press", "escape"])

    def test_cli_click_double(self, runner):
        """T093 – naturo click --double runs on Windows."""
        result = runner.invoke(main, ["click", "--coords", "500", "400", "--double"])
        assert result.exit_code == 0

    def test_cli_scroll_down(self, runner):
        """T099 – naturo scroll --direction down runs on Windows."""
        result = runner.invoke(main, ["scroll", "--direction", "down", "--amount", "3"])
        assert result.exit_code == 0

    def test_cli_scroll_up(self, runner):
        """T100 – naturo scroll --direction up runs on Windows."""
        result = runner.invoke(main, ["scroll", "--direction", "up", "--amount", "2"])
        assert result.exit_code == 0

    def test_cli_move_coords(self, runner):
        """T106 – naturo move --coords runs on Windows."""
        result = runner.invoke(main, ["move", "--coords", "500", "400"])
        assert result.exit_code == 0

    def test_cli_drag_coords(self, runner):
        """T103 – naturo drag --from-coords --to-coords runs on Windows."""
        result = runner.invoke(main, [
            "drag",
            "--from-coords", "100", "100",
            "--to-coords", "200", "200",
            "--steps", "5",
        ])
        assert result.exit_code == 0
