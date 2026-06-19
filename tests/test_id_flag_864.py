"""#864: ``--id eN`` flag harmonization for single-element targeting commands.

``naturo see`` emits elements with display refs (``e1``, ``e2``, ...).  The
natural scripter workflow pipes those refs into follow-up commands, but the
``--id eN`` convention established by ``click`` (#23) — and shared by ``scroll``
and ``move`` — was never propagated to the other commands that act on a single
element.  Scripters had to memorise a per-command flag matrix
(``get -r eN``, ``type --on eN``, ``highlight eN`` ...) and hit a Click
``No such option: --id`` wall mid-pipeline.

This change adds ``--id`` as an accepted alias on every command that targets a
*single* element by ref: ``type``, ``press``, ``get``, ``set``, and
``highlight``.  ``--id`` maps to each command's existing eN-capable input, so
the other targeting methods (``--on``, ``-r``, positional) keep working as
aliases.

Out of scope (documented in #864): ``find`` *produces* refs rather than
consuming one; ``wait`` polls the live UI by selector string (``--element``),
not a snapshot ref; ``drag`` targets two endpoints (``--from``/``--to``, which
already accept eN refs), so a single ``--id`` is ambiguous for it.  ``click``,
``scroll``, and ``move`` already expose ``--id``.
"""
from __future__ import annotations

import pytest
from click.testing import CliRunner

from naturo.cli import main

runner = CliRunner()

# Commands that target a single element by ref and must now accept ``--id``.
_ID_REF_COMMANDS = [
    ["type"],
    ["press"],
    ["get"],
    ["set"],
    ["highlight"],
]

# Commands that established the convention earlier (#23) — regression guard so a
# refactor can't quietly drop ``--id`` from them either.
_ALREADY_SUPPORTED = [
    ["click"],
    ["scroll"],
    ["move"],
]


@pytest.mark.parametrize("cmd_args", _ID_REF_COMMANDS + _ALREADY_SUPPORTED)
def test_id_flag_in_help(cmd_args):
    """Each single-element command's --help must list the ``--id`` flag."""
    result = runner.invoke(main, cmd_args + ["--help"])
    assert result.exit_code == 0, (
        f"naturo {' '.join(cmd_args)} --help failed:\n{result.output}"
    )
    assert "--id" in result.output, (
        f"naturo {' '.join(cmd_args)} --help missing --id:\n{result.output}"
    )


@pytest.mark.parametrize("cmd_args", _ID_REF_COMMANDS + _ALREADY_SUPPORTED)
def test_id_flag_accepted(cmd_args):
    """``--id eN`` must be parsed (not rejected with Click 'No such option').

    The command may still fail downstream (no desktop session, stale ref) — what
    matters is that parsing reaches the handler instead of aborting at the Click
    layer with a usage error.
    """
    result = runner.invoke(main, cmd_args + ["--id", "e1"])
    assert "No such option" not in result.output, (
        f"naturo {' '.join(cmd_args)} --id e1 rejected the flag:\n{result.output}"
    )


@pytest.mark.parametrize(
    "cmd_args,dest",
    [
        (["type"], "on_element"),
        (["press"], "on_element"),
        (["get"], "ref"),
        (["set"], "ref"),
        (["highlight"], "on_ref"),
    ],
)
def test_id_flag_aliases_existing_ref_input(cmd_args, dest):
    """``--id`` must alias the command's existing eN-ref parameter, not invent a new one.

    Aliasing the existing destination guarantees ``--id eN`` flows through the
    exact same snapshot-ref resolution as ``--on``/``-r``/positional, so there is
    no second, divergent code path to keep in sync.
    """
    command = main.commands[cmd_args[0]]
    id_param = next(
        (p for p in command.params if "--id" in getattr(p, "opts", [])),
        None,
    )
    assert id_param is not None, f"{cmd_args[0]} has no --id option"
    assert id_param.name == dest, (
        f"{cmd_args[0]} --id maps to {id_param.name!r}, expected {dest!r}"
    )
