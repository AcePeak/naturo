"""Self-maintaining contract for ``-j`` stdout purity (issue #987, layer 2).

Background
----------
:mod:`tests.test_json_envelope_contract` (issue #979) is **layer 1**: it walks the
Click tree and asserts every *collection read* emits exactly ``{success,
<collection>, count}`` under ``-j``. That structurally kills the ``list``/``show``
shape-drift class (#876 -> #977 -> #980).

It does **not** catch the other recurring ``-j`` sub-class: **stray non-JSON bytes
on stdout** (or, equivalently, the JSON envelope going missing). Three of these
landed one at a time, none of which a collection-read walk would have caught:

* **#874** — the eager ``--version`` / ``--help`` handlers ran before naturo's
  command code and emitted plain text, so ``naturo -j --version`` / ``-j --help``
  broke any caller piping stdout into a JSON parser.
* **#869** — the optional-dependency install prompt leaked human-readable text
  onto stdout under ``-j``.
* **#872** — an unknown subcommand (and every other parse-time ``UsageError``)
  emitted Click's plain usage banner on stderr with exit code 2 instead of the
  ``{success: false, ...}`` envelope, so the envelope a JSON caller expected on
  stdout was simply absent.

The reactive cadence does not stop on its own: we keep fixing instance *N* while
the contract that makes instance *N + 1* unmergeable sits unbuilt. This module is
that contract — layer 2 to #979's layer 1. Layer 1 checks the *shape* of
collection reads; layer 2 checks that *nothing else leaks onto the channel*.

What it asserts
---------------
For every command and subcommand in the live Click tree, and for the root eager
options (``--version`` / ``--help``), it runs the surface under ``-j`` and asserts
stdout is **exactly one** JSON document — it parses cleanly, the top level is an
object carrying a boolean ``success``, and there are **zero** extra bytes before
or after it (no banner, prompt, or usage text). Both the success path (root
``--version`` / ``--help``) and the failure path (unknown option on every node,
unknown command on every group, unknown top-level command) are covered.

Why drive the console-script wrapper
------------------------------------
The leaks all happen at *parse time*, in :func:`naturo.cli.run` — the
console-script entry point that wraps the Click group to honour ``-j`` on Click's
eager/usage-error paths. ``click.testing.CliRunner`` invokes the group directly
and **bypasses that wrapper**, so it cannot see this class of bug. These tests
therefore exercise ``run`` through a synthetic ``sys.argv``, exactly as the
#874/#872 regression tests do.

Why this is safe to run on every CI lane
----------------------------------------
Every probe is an *unknown option* or *unknown command*, which Click rejects
during argument parsing — before any command body runs. No command code, no DLL,
no desktop session, and (critically) no input injection is ever reached. The
suite is pure-Python and runs on every lane.
"""

from __future__ import annotations

import json
from typing import Iterator

import click
import pytest

from naturo.cli import main, run
from naturo.version import __version__

# A flag/subcommand name that is not registered anywhere in the tree, so every
# probe is rejected at parse time (NoSuchOption / "No such command") before any
# command body can run. Kept deliberately implausible to avoid any collision.
_UNKNOWN_OPTION = "--naturo-stdout-purity-probe-xyz"
_UNKNOWN_SUBCOMMAND = "naturo-stdout-purity-probe-xyz"

# Anchor set: top-level surfaces we ship today. If a tree-import regression
# collapses the walk, the discovery assertions below fail loudly instead of the
# contract silently shrinking to zero parametrised cases.
_CORE_NODES: frozenset[tuple[str, ...]] = frozenset(
    {
        ("see",),
        ("click",),
        ("type",),
        ("press",),
        ("find",),
        ("get",),
        ("set",),
        ("wait",),
        ("app",),
        ("list",),
        ("mcp",),
        ("browser",),
    }
)


# ── Tree discovery ───────────────────────────────────────────────────────────

def _walk(group: click.Group, prefix: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], click.Command]]:
    """Yield ``(path, command)`` for every node under ``group``.

    Unlike the layer-1 walk, this yields *both* groups and leaf commands: a group
    is itself a stdout-channel surface (an unknown option or unknown subcommand
    on ``naturo app`` must still produce a clean envelope), so the contract must
    probe it too.
    """
    for name, command in group.commands.items():
        path = prefix + (name,)
        yield path, command
        if isinstance(command, click.Group):
            yield from _walk(command, path)


_ALL_NODES: list[tuple[tuple[str, ...], click.Command]] = sorted(
    _walk(main), key=lambda item: item[0]
)
_ALL_PATHS: list[tuple[str, ...]] = [path for path, _ in _ALL_NODES]
_GROUP_PATHS: list[tuple[str, ...]] = [
    path for path, command in _ALL_NODES if isinstance(command, click.Group)
]


# ── Harness + purity assertion ───────────────────────────────────────────────

def _run(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> int:
    """Invoke the console-script wrapper with a synthetic argv.

    Args:
        monkeypatch: pytest fixture used to swap ``sys.argv``.
        argv: CLI arguments excluding the program name.

    Returns:
        The process exit code (``0`` when the wrapper exits with ``None``).
    """
    monkeypatch.setattr("sys.argv", ["naturo", *argv])
    with pytest.raises(SystemExit) as excinfo:
        run()
    code = excinfo.value.code
    return 0 if code is None else code


def _assert_single_json_envelope(stdout: str) -> dict:
    """Assert ``stdout`` is exactly one JSON envelope and return it.

    The check is deliberately strict about the *channel*, not just parseability:
    a single ``json.loads`` would accept e.g. ``"{...}"`` but silently ignore a
    trailing banner, so this parses one value and then asserts the remainder is
    whitespace. Any leading banner makes the initial decode fail.

    Args:
        stdout: The full text captured from the command's stdout.

    Returns:
        The decoded top-level JSON object.

    Raises:
        AssertionError: If stdout is empty, is not a single JSON object, carries
            stray bytes around the document, or omits a boolean ``success`` key.
    """
    assert stdout, "expected a JSON envelope on stdout, got nothing"
    body = stdout.lstrip()
    try:
        payload, end = json.JSONDecoder().raw_decode(body)
    except json.JSONDecodeError as exc:  # leading banner / non-JSON bytes
        raise AssertionError(
            f"stdout is not a JSON document (stray bytes on the channel?): {stdout!r}"
        ) from exc
    remainder = body[end:]
    assert remainder.strip() == "", f"stray bytes after the JSON envelope: {remainder!r}"
    assert isinstance(payload, dict), f"top-level JSON must be an object: {payload!r}"
    assert isinstance(payload.get("success"), bool), (
        f"envelope is missing a boolean 'success' key: {payload!r}"
    )
    return payload


# ── 1. Discovery anchors ─────────────────────────────────────────────────────

def test_tree_walk_discovers_the_core_surface() -> None:
    """The walk must rediscover every core command; a collapse fails loudly."""
    discovered = set(_ALL_PATHS)
    missing = _CORE_NODES - discovered
    assert not missing, (
        f"tree walk lost core commands {sorted(missing)} — a CLI import regression "
        f"would otherwise shrink this contract to near-zero cases silently."
    )
    # Sanity floor: the real tree is ~150 nodes; anything tiny means breakage.
    assert len(_ALL_PATHS) >= 100, f"only {len(_ALL_PATHS)} nodes discovered"


# ── 2. Root eager options (success path, #874) ───────────────────────────────

@pytest.mark.parametrize("json_flag", ["-j", "--json"])
def test_root_version_is_pure_json(monkeypatch, capsys, json_flag) -> None:
    """``naturo -j --version`` emits exactly the version envelope, exit 0."""
    code = _run(monkeypatch, [json_flag, "--version"])
    payload = _assert_single_json_envelope(capsys.readouterr().out)
    assert code == 0
    assert payload == {"success": True, "version": __version__}


@pytest.mark.parametrize("json_flag", ["-j", "--json"])
def test_root_help_is_pure_json(monkeypatch, capsys, json_flag) -> None:
    """``naturo -j --help`` emits exactly the help envelope, exit 0."""
    code = _run(monkeypatch, [json_flag, "--help"])
    payload = _assert_single_json_envelope(capsys.readouterr().out)
    assert code == 0
    assert payload["success"] is True
    assert "help" in payload


def test_root_unknown_command_is_pure_json(monkeypatch, capsys) -> None:
    """``naturo -j <unknown>`` emits exactly the error envelope, exit 1 (#874)."""
    code = _run(monkeypatch, ["-j", _UNKNOWN_SUBCOMMAND])
    payload = _assert_single_json_envelope(capsys.readouterr().out)
    assert code == 1
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNKNOWN_COMMAND"


def test_root_unknown_option_is_pure_json(monkeypatch, capsys) -> None:
    """``naturo <unknown-option> -j`` emits exactly the error envelope, exit 1."""
    code = _run(monkeypatch, [_UNKNOWN_OPTION, "-j"])
    payload = _assert_single_json_envelope(capsys.readouterr().out)
    assert code == 1
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNKNOWN_OPTION"


# ── 3. Self-maintaining walk: failure path on every node (#872) ──────────────

@pytest.mark.parametrize(
    "path",
    _ALL_PATHS,
    ids=lambda value: " ".join(value) if isinstance(value, tuple) else str(value),
)
def test_unknown_option_emits_pure_json_envelope(monkeypatch, capsys, path) -> None:
    """Every command/subcommand rejects an unknown option as a clean envelope.

    An unknown option is rejected during parsing on the *failing* node, before
    any body runs, so this both covers the #872 leak class for every surface and
    is safe to run on every CI lane (no DLL, no desktop, no input injection).
    """
    code = _run(monkeypatch, [*path, _UNKNOWN_OPTION, "-j"])
    payload = _assert_single_json_envelope(capsys.readouterr().out)
    assert code == 1, f"{' '.join(path)} -j should exit 1 on an unknown option"
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNKNOWN_OPTION"


@pytest.mark.parametrize(
    "path",
    _GROUP_PATHS,
    ids=lambda value: " ".join(value) if isinstance(value, tuple) else str(value),
)
def test_unknown_subcommand_emits_pure_json_envelope(monkeypatch, capsys, path) -> None:
    """Every group rejects an unknown subcommand as a clean envelope (#872)."""
    code = _run(monkeypatch, [*path, _UNKNOWN_SUBCOMMAND, "-j"])
    payload = _assert_single_json_envelope(capsys.readouterr().out)
    assert code == 1, f"{' '.join(path)} -j should exit 1 on an unknown subcommand"
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNKNOWN_COMMAND"
