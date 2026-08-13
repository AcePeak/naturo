"""Hermetic unit tests for the #1202 PID-registry safety-net sweeper.

These drive the registry + :func:`sweep` with a **stub process launcher** — a
plain in-memory set of "alive" PIDs and a recording kill function. No real
process is ever launched or killed, so this runs in the default (headless) CI
gate and is Linux-collectable. It proves the two guarantees #1202 requires:

  * the sweeper kills a tracked, still-alive PID (crash-before-teardown safety
    net), and reports it as leaked (the leak gate), and
  * it NEVER kills a PID it does not have in the ledger, and never touches a
    registered-but-already-dead PID (the "PID-scoped, only what we launched"
    non-negotiable — a bug here could kill the developer's real Chrome).
"""
from __future__ import annotations

import pytest

from tests import _teardown_registry as reg


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Each test gets a clean ledger and leaves one behind."""
    reg.clear()
    yield
    reg.clear()


class _StubProcessWorld:
    """A fake process table: which PIDs are alive, and which got killed."""

    def __init__(self, alive: "set[int]") -> None:
        self.alive = set(alive)
        self.killed: "list[int]" = []

    def alive_fn(self, pid: int) -> bool:
        return pid in self.alive

    def kill_fn(self, pid: int) -> None:
        self.killed.append(pid)
        self.alive.discard(pid)


def test_register_and_snapshot_is_defensive_copy():
    reg.register(100)
    reg.register(200)
    reg.register(None)  # ignored
    snap = reg.registered_pids()
    assert snap == {100, 200}
    snap.add(999)  # mutating the snapshot must not affect the ledger
    assert reg.registered_pids() == {100, 200}


def test_sweep_kills_tracked_alive_pid_and_reports_it_leaked():
    """The core safety-net: a fixture registered a PID that is still alive at
    session end (its teardown never ran) -> sweep kills it AND flags the leak."""
    reg.register(4242)
    world = _StubProcessWorld(alive={4242})

    leaked = reg.sweep(alive_fn=world.alive_fn, kill_fn=world.kill_fn)

    assert leaked == {4242}
    assert world.killed == [4242]
    assert 4242 not in world.alive


def test_sweep_skips_registered_but_already_dead_pid():
    """A well-behaved test tore its app down: the PID is registered but dead, so
    sweep neither kills it nor reports a leak (no false positive)."""
    reg.register(500)
    world = _StubProcessWorld(alive=set())  # already dead

    leaked = reg.sweep(alive_fn=world.alive_fn, kill_fn=world.kill_fn)

    assert leaked == set()
    assert world.killed == []


def test_sweep_never_touches_unregistered_pid():
    """SAFETY: a live process that was never registered (the human's real Chrome)
    is invisible to the sweep — never probed as leaked, never killed."""
    reg.register(10)  # the only thing we launched; already dead
    world = _StubProcessWorld(alive={10, 99999})  # 99999 = user's real app

    world.alive.discard(10)  # our launch was cleanly torn down
    leaked = reg.sweep(alive_fn=world.alive_fn, kill_fn=world.kill_fn)

    assert leaked == set()
    assert 99999 not in world.killed
    assert world.killed == []


def test_sweep_mixed_ledger_kills_only_the_leakers():
    for pid in (1, 2, 3, 4):
        reg.register(pid)
    # 2 and 4 leaked (still alive); 1 and 3 were torn down cleanly.
    world = _StubProcessWorld(alive={2, 4, 555})  # 555 never registered

    leaked = reg.sweep(alive_fn=world.alive_fn, kill_fn=world.kill_fn)

    assert leaked == {2, 4}
    assert set(world.killed) == {2, 4}
    assert 555 not in world.killed  # untracked bystander untouched


def test_sweep_explicit_pids_argument_overrides_ledger():
    reg.register(1)
    world = _StubProcessWorld(alive={7})
    leaked = reg.sweep(pids=[7], alive_fn=world.alive_fn, kill_fn=world.kill_fn)
    assert leaked == {7}
    assert world.killed == [7]


def test_clear_empties_the_ledger():
    reg.register(1)
    reg.register(2)
    reg.clear()
    assert reg.registered_pids() == set()


def test_pid_alive_is_false_for_impossible_pid():
    """Real liveness probe: an impossible PID is never 'alive' and never raises
    (returns False off-Windows, and on Windows OpenProcess fails)."""
    assert reg.pid_alive(4294967295) is False
