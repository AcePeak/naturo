"""Self-maintaining coverage contract for the desktop-session guard (#912).

``#885`` wired the desktop-session pre-flight check onto the CLI commands and
MCP tools that obtain the Windows UI backend, so they fail loudly instead of
returning fabricated success (empty arrays, all-black PNGs, stale window lists)
in a ``NO_DESKTOP_SESSION`` environment.  ``tests/test_no_desktop_guard_885.py``
locks that down with a *behavioral* matrix that proves a representative set of
those surfaces fails loudly.

That matrix is a hand-maintained static list, however, and nothing forces a
*future* CLI subcommand or MCP tool to either carry the guard or be a
deliberate, reviewed exemption.  The moment someone adds a new backend-touching
surface without the guard, the ``#885`` silent-failure class can silently recur
there while every existing test stays green -- because the new surface simply
isn't in any list.

This module closes that hole.  It derives the surface inventory **at runtime**
and asserts every surface is classified into exactly one of two explicit,
reviewed sets:

* ``_CLI_DESKTOP_SESSION_REQUIRED`` / ``_MCP_DESKTOP_SESSION_REQUIRED`` --
  surfaces that acquire the desktop UI backend and therefore *must* fail loudly
  without an interactive desktop session (the ``require_desktop_session`` /
  guarded ``_get_backend`` class).
* ``_CLI_SESSION_INDEPENDENT`` / ``_MCP_SESSION_INDEPENDENT`` -- surfaces that
  do **not** touch the desktop UI backend and work headless: pure config,
  clipboard text, on-disk selector / visual-baseline / recording / snapshot
  stores, snapshot diffing of stored data, Chromium/CDP browser automation,
  Excel COM automation, MCP/daemon management, and pure ``--help``.

A brand-new surface that is in neither set fails
:func:`test_every_cli_leaf_is_classified` /
:func:`test_every_mcp_tool_is_classified`, forcing its author to make a
conscious decision: route it through the guard and add it to the
desktop-required set (and the behavioral matrix), or justify it as
session-independent.  This converts the ``#885`` static snapshot into a
self-maintaining contract -- guard coverage can no longer silently rot as the
CLI/MCP surface grows.

The classification was grounded in the source, not guessed: a surface is
desktop-required iff its handler reaches ``naturo.backends.base.get_backend``
(directly or through the guarded ``_get_backend``).  Two deliberate notes:

* ``clipboard`` is split by surface because the two entry points differ today:
  the MCP ``clipboard_*`` tools route through the guarded ``_get_backend`` (so
  they fail loudly and are desktop-required), while the ``clipboard`` *CLI*
  commands use a local backend accessor that does not run the desktop-session
  pre-flight -- consistent with ``#885`` listing "pure-clipboard" as a
  session-independent allow-list example.  The sets record actual behavior, not
  aspiration.
* ``diff`` and the ``desktop`` (virtual-desktop) commands acquire the backend
  via a raw ``get_backend()`` rather than the guarded helper; they are
  classified desktop-required because they genuinely need a session.  Hardening
  their acquisition to the guarded path is tracked separately and is out of
  scope for this coverage test.

Relates to #912.  Regression-proofs #885 / #868 / #875 / #878 / #883 / #893.
"""
from __future__ import annotations

import click
import pytest

from naturo.cli import main

# The ``mcp`` package requires Python >= 3.10, so it is absent on the 3.9 CI
# lane.  Detect it once at import time and skip the MCP-enumeration test there,
# mirroring ``test_no_desktop_guard_885.py``.  The CLI coverage and the
# data-only behavioral cross-check do not need ``mcp`` and always run.
try:
    from naturo.mcp_server import create_server as _create_server

    _MCP_AVAILABLE = True
except ImportError:  # pragma: no cover - mcp optional, absent on Python 3.9
    _MCP_AVAILABLE = False


# ── Runtime surface enumeration ──────────────────────────────────────────────


def _all_cli_leaves() -> set[str]:
    """Return every leaf command in the ``naturo`` CLI as a space-joined path.

    Walks the Click command tree from the root group, descending into every
    sub-group, and yields the full invocation path of each non-group (leaf)
    command -- e.g. ``"app windows"``, ``"taskbar list"``, ``"see"``.  Hidden
    commands are included: a hidden surface that skips the guard is just as much
    a silent-failure risk as a visible one.

    Returns:
        The set of space-joined leaf command paths registered on the CLI.
    """
    leaves: set[str] = set()

    def walk(command: click.Command, path: list[str]) -> None:
        if isinstance(command, click.Group):
            for name, sub in command.commands.items():
                walk(sub, [*path, name])
        else:
            leaves.add(" ".join(path))

    walk(main, [])
    return leaves


def _leaf_path_of_argv(argv: list[str]) -> str:
    """Resolve a CLI ``argv`` to the space-joined path of the leaf command it runs.

    Consumes leading tokens as long as they name a sub-command of the current
    group, stopping at the first non-group command -- so ``["app", "windows"]``
    maps to ``"app windows"`` and ``["wait", "--gone", "X", "--timeout", "1"]``
    maps to ``"wait"`` (the trailing tokens are that command's options/args).

    Args:
        argv: The argument vector passed to the CLI, as used by the behavioral
            matrix in ``test_no_desktop_guard_885.py``.

    Returns:
        The space-joined leaf-command path the argv invokes.
    """
    command: click.Command = main
    path: list[str] = []
    for token in argv:
        if not isinstance(command, click.Group) or token not in command.commands:
            break
        command = command.commands[token]
        path.append(token)
    return " ".join(path)


def _all_mcp_tools() -> set[str]:
    """Return the name of every tool registered on the MCP server.

    Builds the server via :func:`naturo.mcp_server.create_server` and reads back
    the registered tool list, mirroring how an MCP client discovers the surface.

    Returns:
        The set of registered MCP tool names.
    """
    import asyncio

    server = _create_server()
    loop = asyncio.new_event_loop()
    try:
        tools = loop.run_until_complete(server.list_tools())
    finally:
        loop.close()
    return {tool.name for tool in tools}


# ── CLI classification ───────────────────────────────────────────────────────

# Leaf commands that acquire the desktop UI backend and MUST fail loudly without
# an interactive desktop session.  Adding a new such command requires routing it
# through ``require_desktop_session`` / the guarded ``_get_backend`` and adding
# it here (and ideally to the behavioral matrix in
# ``test_no_desktop_guard_885.py``).
_CLI_DESKTOP_SESSION_REQUIRED = frozenset(
    {
        # app lifecycle / inspection / window control
        "app close", "app find", "app focus", "app hide", "app inspect",
        "app launch", "app list", "app maximize", "app minimize", "app move",
        "app quit", "app relaunch", "app restore", "app switch", "app unhide",
        "app windows",
        # screen capture + UI-tree read + element targeting
        "capture", "see", "find", "get", "set", "highlight", "menu-inspect",
        # input injection
        "click", "type", "press", "hotkey", "scroll", "drag", "move",
        # waits, snapshot diff (captures live state), virtual desktops
        "wait", "diff",
        "desktop close", "desktop create", "desktop list", "desktop move-window",
        "desktop switch",
        # dialogs / taskbar / tray / window enumeration + control
        "dialog accept", "dialog click-button", "dialog detect",
        "dialog dismiss", "dialog type",
        "list apps", "list screens", "list windows",
        "taskbar click", "taskbar list", "tray click", "tray list",
        "window close", "window focus", "window list", "window maximize",
        "window minimize", "window move", "window resize", "window restore",
        "window set-bounds",
    }
)

# Leaf commands that do NOT touch the desktop UI backend and work headless.
# Each group is exempt for a concrete, reviewed reason (see module docstring).
_CLI_SESSION_INDEPENDENT = frozenset(
    {
        # Chromium / CDP browser automation -- its own backend, not desktop UIA.
        "browser attr", "browser captcha-detect", "browser captcha-solve",
        "browser click", "browser close", "browser download", "browser eval",
        "browser find", "browser frame-eval", "browser frame-find",
        "browser frames", "browser hover", "browser html", "browser intercept",
        "browser launch", "browser navigate", "browser profiles",
        "browser requests", "browser screenshot", "browser scroll",
        "browser select", "browser stealth", "browser stealth-check",
        "browser stealth-flags", "browser tab", "browser tabs", "browser text",
        "browser title", "browser type", "browser url", "browser wait",
        "browser wait-function", "browser wait-navigation",
        "browser wait-network-idle", "browser wait-url",
        # Clipboard text (CLI path is session-independent per #885 allow-list).
        "clipboard clear", "clipboard get", "clipboard info", "clipboard set",
        # Pure on-disk config.
        "config clear", "config setup anthropic", "config show",
        # Excel COM automation -- its own backend, not desktop UIA.
        "excel info", "excel list-sheets", "excel open", "excel read",
        "excel run-macro", "excel write",
        # Pure help; permissions listing is an unimplemented stub (no backend).
        "help", "list permissions",
        # MCP / daemon management.
        "mcp install", "mcp start", "mcp tools",
        # On-disk recording store management + replay setup.
        "record delete", "record export", "record list", "record play",
        "record show", "record start", "record stop",
        # On-disk selector store.
        "selector clear", "selector delete", "selector export",
        "selector import", "selector list", "selector load", "selector save",
        "selector show", "selector test",
        # On-disk snapshot store management.
        "snapshot clean", "snapshot list", "snapshot sessions",
        # On-disk visual-baseline store + image diffing.
        "visual baseline", "visual compare", "visual delete", "visual diff",
        "visual list", "visual report", "visual suite", "visual update",
        "visual update-all",
    }
)


# ── MCP classification ───────────────────────────────────────────────────────

# MCP tools that do NOT touch the desktop UI backend (verified: their handlers
# never call the guarded ``_get_backend``).  ``get_snapshot`` / ``list_snapshots``
# read the on-disk snapshot store; ``excel_*`` drive Excel via COM.
_MCP_SESSION_INDEPENDENT = frozenset(
    {
        "get_snapshot", "list_snapshots",
        "excel_open", "excel_read", "excel_write", "excel_list_sheets",
        "excel_run_macro", "excel_info",
    }
)


# ── Tests: every surface is classified (the forcing function) ─────────────────


def test_every_cli_leaf_is_classified() -> None:
    """Every CLI leaf command is in exactly one classification set.

    A new leaf command in neither set fails here, forcing its author to decide
    whether it needs the desktop-session guard.  A stale entry (a removed
    command still listed) also fails, keeping the sets honest.
    """
    runtime = _all_cli_leaves()
    classified = _CLI_DESKTOP_SESSION_REQUIRED | _CLI_SESSION_INDEPENDENT

    unclassified = runtime - classified
    assert not unclassified, (
        "New CLI surface(s) are not classified for the desktop-session guard: "
        f"{sorted(unclassified)}. If a command acquires the desktop backend, "
        "route it through require_desktop_session / the guarded _get_backend and "
        "add it to _CLI_DESKTOP_SESSION_REQUIRED (and the behavioral matrix in "
        "test_no_desktop_guard_885.py); otherwise add it to "
        "_CLI_SESSION_INDEPENDENT with its reason."
    )

    stale = classified - runtime
    assert not stale, (
        f"Classification lists name CLI surfaces that no longer exist: "
        f"{sorted(stale)}. Remove them from the sets in this file."
    )


def test_cli_classification_sets_are_disjoint() -> None:
    """No CLI command is both desktop-required and session-independent."""
    overlap = _CLI_DESKTOP_SESSION_REQUIRED & _CLI_SESSION_INDEPENDENT
    assert not overlap, f"CLI commands classified both ways: {sorted(overlap)}"


@pytest.mark.skipif(not _MCP_AVAILABLE, reason="mcp package not installed")
def test_every_mcp_tool_is_classified() -> None:
    """Every MCP tool is classified; desktop-required = all minus the allow-list.

    The desktop-required MCP set is derived by exclusion so that adding a new
    tool defaults it to *desktop-required* (the safe, guarded assumption): a new
    headless tool must be consciously added to ``_MCP_SESSION_INDEPENDENT`` to
    opt out, while a new backend-touching tool is covered automatically.
    """
    runtime = _all_mcp_tools()

    missing_allowlist = _MCP_SESSION_INDEPENDENT - runtime
    assert not missing_allowlist, (
        "The MCP session-independent allow-list names tools that no longer "
        f"exist: {sorted(missing_allowlist)}. Remove them from "
        "_MCP_SESSION_INDEPENDENT."
    )

    desktop_required = runtime - _MCP_SESSION_INDEPENDENT
    # Every tool is now in exactly one bucket by construction; assert the
    # partition is non-degenerate so a future refactor that empties the server
    # (e.g. a registration regression) is caught rather than passing vacuously.
    assert desktop_required, "No desktop-required MCP tools found -- did tool registration break?"
    assert desktop_required.isdisjoint(_MCP_SESSION_INDEPENDENT)


# ── Teeth: tie this contract to the behavioral matrix so they can't drift ─────


def test_behavioral_matrix_surfaces_are_desktop_required() -> None:
    """Every surface proven to fail loudly in #885 is classified desktop-required.

    ``test_no_desktop_guard_885.py`` behaviorally proves a representative set of
    CLI commands and MCP tools fail loudly without a desktop session.  This ties
    that proof to the coverage contract: if a behaviorally-guarded surface were
    ever misclassified here as session-independent, this fails -- the two files
    cannot silently disagree about what the guard covers.
    """
    from tests.test_no_desktop_guard_885 import _CLI_GUARDED, _MCP_GUARDED

    cli_proven = {_leaf_path_of_argv(param.values[0]) for param in _CLI_GUARDED}
    assert cli_proven <= _CLI_DESKTOP_SESSION_REQUIRED, (
        "Behaviorally-guarded CLI surfaces missing from "
        f"_CLI_DESKTOP_SESSION_REQUIRED: {sorted(cli_proven - _CLI_DESKTOP_SESSION_REQUIRED)}"
    )

    mcp_proven = {param.values[0] for param in _MCP_GUARDED}
    assert mcp_proven.isdisjoint(_MCP_SESSION_INDEPENDENT), (
        "Behaviorally-guarded MCP tools wrongly listed as session-independent: "
        f"{sorted(mcp_proven & _MCP_SESSION_INDEPENDENT)}"
    )
