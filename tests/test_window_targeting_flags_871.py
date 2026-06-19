"""#871: window-targeting flag harmonization for element/menu discovery commands.

The window-targeting flag family (``--app``, ``--window``, ``--hwnd``, ``--pid``,
``--app-id``) was exposed inconsistently across subcommands, forcing scripters to
memorise a per-command matrix.  The "gold standard" commands
(``see``/``click``/``type``/...) accept the full set; the element/menu *discovery*
commands ``find``, ``highlight``, and ``menu-inspect`` had gaps.

These three commands all resolve their target window through the same DLL-backed
``_resolve_hwnd`` / ``get_element_tree`` / ``get_menu_items`` path, so the full
flag set can be threaded uniformly.  These tests assert the flags are now
accepted (no Click ``No such option`` rejection) and visible in ``--help``.

Commands that route through other resolution paths (``get``/``set`` value
patterns, ``list windows`` enumeration, ``app focus``/``quit`` lifecycle) are
tracked separately in #871 and are out of scope here.
"""
from __future__ import annotations

import pytest
from click.testing import CliRunner

from naturo.cli import main

runner = CliRunner()

# Element/menu discovery commands harmonised by this change and the full
# window-targeting flag set each must expose.
_DISCOVERY_COMMANDS = [
    ["find"],
    ["highlight"],
    ["menu-inspect"],
]
_WINDOW_TARGET_FLAGS = ["--app", "--window", "--hwnd", "--pid", "--app-id"]


@pytest.mark.parametrize("cmd_args", _DISCOVERY_COMMANDS)
@pytest.mark.parametrize("flag", _WINDOW_TARGET_FLAGS)
def test_window_target_flag_in_help(cmd_args, flag):
    """Each discovery command's --help must list the full window-targeting flag set."""
    result = runner.invoke(main, cmd_args + ["--help"])
    assert result.exit_code == 0, (
        f"naturo {' '.join(cmd_args)} --help failed:\n{result.output}"
    )
    assert flag in result.output, (
        f"naturo {' '.join(cmd_args)} --help missing {flag}:\n{result.output}"
    )


@pytest.mark.parametrize("cmd_args", _DISCOVERY_COMMANDS)
@pytest.mark.parametrize(
    "flag_with_value",
    [["--window", "Untitled"], ["--hwnd", "12345"], ["--pid", "4321"]],
)
def test_window_target_flag_accepted(cmd_args, flag_with_value):
    """The flag must be parsed (not rejected with Click 'No such option').

    The command may still fail for other reasons (no desktop session, window
    not found) — what matters is that argument parsing reaches the handler
    rather than aborting at the Click layer.
    """
    result = runner.invoke(main, cmd_args + flag_with_value)
    assert "No such option" not in result.output, (
        f"naturo {' '.join(cmd_args + flag_with_value)} rejected the flag:\n{result.output}"
    )
