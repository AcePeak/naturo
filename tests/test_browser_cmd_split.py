"""Structural guards for the ``browser_cmd.py`` module split (#856).

These tests lock the public command surface of ``naturo browser`` so the split
into focused ``naturo/cli/_browser/`` submodules cannot silently drop, rename,
or fail to register a subcommand, and so backward-compatible imports keep working.
"""

from __future__ import annotations

import importlib

import pytest

from naturo.cli.browser_cmd import browser

# Every subcommand that ``naturo browser`` must expose, regardless of which
# focused module now defines it.
EXPECTED_COMMANDS = {
    "navigate", "url", "title", "eval", "scroll", "close", "tabs", "tab",
    "find", "click", "type", "select", "text", "attr", "html", "hover",
    "frames", "frame-eval", "frame-find",
    "wait", "wait-navigation", "wait-url", "wait-function", "wait-network-idle",
    "requests", "intercept",
    "screenshot",
    "stealth", "stealth-flags", "stealth-check",
    "launch", "profiles", "download",
    "captcha-detect", "captcha-solve",
}

# Command callables re-exported from ``browser_cmd`` for backward compatibility.
EXPECTED_REEXPORTS = [
    "navigate", "url_cmd", "title_cmd", "eval_cmd", "scroll_cmd", "close_cmd",
    "tabs_cmd", "tab_cmd", "find_cmd", "click_cmd", "type_cmd", "select_cmd",
    "text_cmd", "attr_cmd", "html_cmd", "hover_cmd", "frames_cmd",
    "frame_eval_cmd", "frame_find_cmd", "wait_cmd", "wait_navigation_cmd",
    "wait_url_cmd", "wait_function_cmd", "wait_network_idle_cmd", "requests_cmd",
    "intercept_cmd", "screenshot_cmd", "stealth_cmd", "stealth_flags_cmd",
    "stealth_check_cmd", "launch_cmd", "profiles_cmd", "download_cmd",
    "captcha_detect", "captcha_solve",
]

_SUBMODULES = [
    "navigation", "elements", "frames", "waits", "network",
    "visual", "stealth", "lifecycle", "captcha",
]


def test_all_subcommands_registered() -> None:
    """The full command surface survives the split — no command dropped or renamed."""
    assert set(browser.commands) == EXPECTED_COMMANDS


def test_backward_compatible_reexports() -> None:
    """Command callables remain importable from ``naturo.cli.browser_cmd``."""
    module = importlib.import_module("naturo.cli.browser_cmd")
    for name in EXPECTED_REEXPORTS:
        assert hasattr(module, name), f"browser_cmd no longer re-exports {name!r}"


def test_get_page_helper_is_canonical() -> None:
    """``_get_page`` stays defined on ``browser_cmd`` so existing patch targets hold."""
    module = importlib.import_module("naturo.cli.browser_cmd")
    assert callable(module._get_page)


@pytest.mark.parametrize("name", _SUBMODULES)
def test_focused_submodule_importable(name: str) -> None:
    """Each focused submodule imports cleanly and shares the canonical group."""
    submodule = importlib.import_module(f"naturo.cli._browser.{name}")
    assert submodule.browser is browser
