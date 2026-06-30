"""Tests for click landing-window honesty (#1207).

A coordinate click must never be reported as a success when it actually landed
on a different window — e.g. the target was occluded or never came to the
foreground, so the synthetic click reached whatever window was on top instead.

When a target window is known (--app/--hwnd/--pid or a cached snapshot) and the
window under the click point belongs to a *different process*, the command must
fail loudly (CLICK_WRONG_WINDOW). For bare --coords with no known target, it
discloses which window received the click via ``hit_window``.

These tests patch the window-hit-test helpers, so they are desktop-independent
and send no real input.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from naturo.cli._jsonio import json_dumps  # noqa: F401 — ensures module import
from naturo.cli.interaction import click_cmd


def _invoke(args, *, hit, target_pid):
    """Invoke click_cmd with the window hit-test helpers patched.

    Args:
        args: CLI args (without -j; added here).
        hit: tuple returned by _window_root_at_point, or None.
        target_pid: value returned by _window_pid for the target hwnd.
    """
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 349525
    # Avoid the UWP/WinUI UIA-click branch so the normal backend.click() runs.
    backend._is_afh_window.return_value = False
    backend._is_winui_window.return_value = False
    with patch("naturo.cli.interaction._common._get_backend",
               return_value=backend), \
         patch("naturo.cli.interaction._common._auto_route", return_value={}), \
         patch("naturo.cli.interaction._click._window_root_at_point",
               return_value=hit), \
         patch("naturo.cli.interaction._click._window_pid",
               return_value=target_pid):
        runner = CliRunner()
        return runner.invoke(click_cmd, args + ["--no-verify", "-j"]), backend


def test_targeted_click_on_other_process_window_fails_loudly():
    """--hwnd target occluded by another process → CLICK_WRONG_WINDOW, exit!=0."""
    result, backend = _invoke(
        ["--coords", "500", "300", "--hwnd", "349525"],
        hit=(777, "WindowsTerminal", 999),  # different pid
        target_pid=111,
    )
    assert result.exit_code != 0
    assert "CLICK_WRONG_WINDOW" in result.output


def test_targeted_click_same_process_succeeds():
    """Click landing on the target's own process is reported as success."""
    result, backend = _invoke(
        ["--coords", "500", "300", "--hwnd", "349525"],
        hit=(349525, "Target App", 111),  # same pid as target
        target_pid=111,
    )
    assert result.exit_code == 0
    assert "hit_window" in result.output
    backend.click.assert_called_once()


def test_bare_coords_discloses_hit_window():
    """Bare --coords (no target) cannot fail, but discloses the hit window."""
    result, backend = _invoke(
        ["--coords", "500", "300"],
        hit=(777, "WindowsTerminal", 999),
        target_pid=None,
    )
    assert result.exit_code == 0
    assert "hit_window" in result.output
    assert "999" in result.output  # the pid actually clicked


def test_no_hit_info_behaves_as_before():
    """When the hit window is undeterminable, output omits hit_window."""
    result, backend = _invoke(
        ["--coords", "500", "300"],
        hit=None,
        target_pid=None,
    )
    assert result.exit_code == 0
    assert "hit_window" not in result.output
    backend.click.assert_called_once()
