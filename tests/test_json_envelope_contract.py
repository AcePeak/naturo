"""Self-maintaining contract for the ``-j`` success envelope of collection reads.

Background (issue #979)
-----------------------
Every ``list``-style command that emits a collection under ``-j`` hand-builds the
same envelope at its callsite::

    json.dumps({"success": True, "<collection>": items, "count": len(items)})

Because each callsite wrote this literally, the envelope drifted silently every
time a new read command was added — QA discovered the omissions one at a time
(#876 ``selector list`` / ``record list``; #977 ``visual list`` / ``selector
show``). Nothing structurally prevented the *next* read command from drifting.

This module is that structural guard. It does two things:

1. Unit-tests the single source of truth, :func:`success_envelope`, so the canonical
   shape is pinned in one place.
2. Walks the live Click command tree, finds every command tagged as a collection
   read via :func:`collection_read`, runs it with ``-j`` against an **empty** store,
   and asserts the emitted JSON is *exactly* ``{"success": bool, "<collection>":
   list, "count": int}`` with ``count == len(collection)``. A new collection-read
   command that forgets the envelope — or a marked command without an isolation
   fixture — fails CI on day one instead of weeks later in QA.

The test is pure-Python and touches only on-disk JSON stores (no DLL, no desktop),
so it runs on every CI lane.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Iterator

import click
import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.cli.error_helpers import success_envelope

# ── Where each collection-read command keeps its on-disk store ────────────────
# Maps a collection key to the ``(module, attribute)`` holding its storage root,
# so the contract test can point it at an empty temp directory. Every command
# discovered with that collection key MUST have an entry here — the walk below
# asserts it, which is what forces a new collection read to wire in isolation
# (and therefore prove its empty-store shape) before it can land.
_STORE_ROOTS: dict[str, tuple[str, str]] = {
    "selectors": ("naturo.cli.selector_cmd", "SELECTORS_DIR"),
    "baselines": ("naturo.visual", "BASELINES_DIR"),
    "recordings": ("naturo.recording", "RECORDINGS_DIR"),
}

# The collection reads we know exist today. The walk must rediscover at least
# these; if one loses its marker (and so drops out of the contract), this set
# makes the regression loud instead of silent.
_KNOWN_COLLECTION_READS: dict[tuple[str, ...], str] = {
    ("selector", "list"): "selectors",
    ("visual", "list"): "baselines",
    ("record", "list"): "recordings",
}


def _walk(group: click.Group, prefix: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], click.Command]]:
    """Yield ``(path, command)`` for every leaf command under ``group``."""
    for name, command in group.commands.items():
        path = prefix + (name,)
        if isinstance(command, click.Group):
            yield from _walk(command, path)
        else:
            yield path, command


def _discover_collection_reads() -> dict[tuple[str, ...], str]:
    """Find every command tagged via :func:`collection_read` in the live tree."""
    found: dict[tuple[str, ...], str] = {}
    for path, command in _walk(main):
        key = getattr(command, "_naturo_collection_key", None)
        if key is not None:
            found[path] = key
    return found


# ── 1. Single source of truth ────────────────────────────────────────────────

def test_success_envelope_canonical_shape() -> None:
    """The helper emits exactly the three canonical keys, in order."""
    items = [{"a": 1}, {"b": 2}]
    envelope = success_envelope("widgets", items)

    assert list(envelope.keys()) == ["success", "widgets", "count"]
    assert envelope["success"] is True
    assert envelope["widgets"] == items
    assert envelope["count"] == 2


def test_success_envelope_empty_collection() -> None:
    """An empty collection yields ``count == 0`` and an empty list."""
    envelope = success_envelope("widgets", [])

    assert envelope == {"success": True, "widgets": [], "count": 0}


def test_success_envelope_copies_items() -> None:
    """The envelope must not alias the caller's list (mutation isolation)."""
    items = [1, 2]
    envelope = success_envelope("widgets", items)
    items.append(3)

    assert envelope["widgets"] == [1, 2]
    assert envelope["count"] == 2


def test_success_envelope_count_matches_any_iterable() -> None:
    """``count`` reflects the materialised collection even for a generator."""
    envelope = success_envelope("widgets", (n for n in range(3)))

    assert envelope["widgets"] == [0, 1, 2]
    assert envelope["count"] == 3


# ── 2. Self-maintaining tree contract ────────────────────────────────────────

def test_known_collection_reads_are_discovered() -> None:
    """The marker survives on every collection read we ship today."""
    discovered = _discover_collection_reads()
    for path, key in _KNOWN_COLLECTION_READS.items():
        assert discovered.get(path) == key, (
            f"{' '.join(path)} lost its collection_read marker — its -j envelope "
            f"is no longer guarded by the contract test."
        )


def test_every_collection_read_has_a_store_fixture() -> None:
    """A marked command without an isolation fixture fails loudly here.

    This is the self-maintaining hinge: adding a new ``collection_read`` command
    forces the author to register its storage root, which in turn makes the
    empty-store shape assertion below run against it.
    """
    for path, key in _discover_collection_reads().items():
        assert key in _STORE_ROOTS, (
            f"{' '.join(path)} is tagged collection_read('{key}') but '{key}' has "
            f"no entry in _STORE_ROOTS — add one so the contract can isolate and "
            f"verify its empty-store envelope."
        )


@pytest.fixture()
def empty_store_dir() -> Iterator[Path]:
    """Yield a fresh, empty, writable directory for a command's store.

    Uses :func:`tempfile.mkdtemp` rather than the ``tmp_path`` fixture: the shared
    pytest temp base on the agent host is contended by concurrent loop cycles and
    its numbered-dir scan intermittently raises ``WinError 5``. ``mkdtemp`` creates
    an isolated directory without scanning that base, so the contract stays
    deterministic on both the agent host and CI.
    """
    path = Path(tempfile.mkdtemp(prefix="naturo-envelope-contract-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.mark.parametrize(
    "path,key",
    sorted(_discover_collection_reads().items()),
    ids=lambda value: " ".join(value) if isinstance(value, tuple) else str(value),
)
def test_collection_read_emits_canonical_envelope(
    path: tuple[str, ...],
    key: str,
    empty_store_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every tagged read emits exactly the canonical envelope on an empty store."""
    module_name, attribute = _STORE_ROOTS[key]
    module = __import__(module_name, fromlist=[attribute])
    monkeypatch.setattr(module, attribute, empty_store_dir / "store")

    result = CliRunner().invoke(main, [*path, "-j"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)

    assert set(payload) == {"success", key, "count"}, (
        f"{' '.join(path)} -j drifted from the canonical envelope: {sorted(payload)}"
    )
    assert payload["success"] is True
    assert isinstance(payload[key], list)
    assert payload["count"] == len(payload[key]) == 0
