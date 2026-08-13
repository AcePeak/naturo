"""Session-scoped PID registry + safety-net sweeper for test-launched apps (#1202).

The launch fixtures (``naturo_browser``, ``launched_app``, ``tracked_launch``)
each **append the PID(s) they started** to a shared, session-lived ledger via
:func:`register`. Two guarantees ride on that ledger:

1. **Safety-net sweeper** (:func:`sweep`): at session end a session-scoped
   fixture kills any *still-alive* registered PID. So even a fixture that
   crashes *before* its own ``finally`` teardown runs — leaving its app orphaned
   — is reaped. The sweeper only ever touches PIDs a fixture itself recorded, so
   it can never kill a window the human already had open (the #1197 non-negotiable).

2. **Leak gate**: any registered PID still alive at session end is, by
   definition, a process a test launched and failed to clean up. :func:`sweep`
   returns that leaked set (after killing it) so the session fixture can assert
   it was empty — a leaking test fails the run instead of silently polluting the
   next one. This also catches a #226-class *silent* teardown failure where an
   ``app quit`` reported success but left the process alive.

The ledger is an append-only record of everything launched: a PID is **not**
removed when a fixture tears it down. A well-behaved teardown leaves the PID
*dead*, so the sweeper simply finds it already gone. This is deliberate — it
means both "crashed before teardown" and "teardown silently failed" surface as
the same signal (still-alive registered PID), with no way for a fixture to hide
a leak by unregistering.

The kill / liveness primitives are injectable, so the sweep logic is fully
unit-testable headlessly (no real process is launched or killed) and collectable
on Linux; the defaults use Win32 ``OpenProcess`` + :func:`tests._launch.kill_pid`.
"""
from __future__ import annotations

import threading
from typing import Callable, Iterable

# Session-lived, append-only ledger of PIDs the launch fixtures started.
_lock = threading.Lock()
_registry: "set[int]" = set()

AliveFn = Callable[[int], bool]
KillFn = Callable[[int], object]


def register(pid: "int | None") -> None:
    """Append *pid* to the session ledger (idempotent; ``None`` is ignored)."""
    if pid is None:
        return
    with _lock:
        _registry.add(int(pid))


def registered_pids() -> "set[int]":
    """Snapshot of every PID registered this session (defensive copy)."""
    with _lock:
        return set(_registry)


def clear() -> None:
    """Reset the ledger. For test isolation of the registry itself."""
    with _lock:
        _registry.clear()


def pid_alive(pid: int) -> bool:
    """Return True if *pid* is a live process. False off-Windows / on any error.

    Uses ``OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)`` +
    ``GetExitCodeProcess``: a process is alive iff the handle opens and its exit
    code is ``STILL_ACTIVE`` (259). This never shells out, so it is robust on a
    host whose ``tasklist``/``taskkill`` CLI is broken.
    """
    try:
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid),
        )
        if not handle:
            return False
        try:
            code = ctypes.c_ulong(0)
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return False


def _default_kill(pid: int) -> None:
    # Imported lazily so this module stays import-safe on Linux CI (tests._launch
    # is pure Python, but keep the dependency edge lazy and one-directional).
    from tests._launch import kill_pid

    kill_pid(pid)


def sweep(
    pids: "Iterable[int] | None" = None,
    alive_fn: AliveFn = pid_alive,
    kill_fn: KillFn = _default_kill,
) -> "set[int]":
    """Kill every still-alive registered PID; return the set that had leaked.

    Args:
        pids: PIDs to sweep. Defaults to the whole session ledger.
        alive_fn: ``(pid) -> bool`` liveness probe (injectable for tests).
        kill_fn: ``(pid) -> None`` PID-scoped killer (injectable for tests).

    Returns:
        The set of registered PIDs that were **still alive** — i.e. leaked past
        their fixture's own teardown — each of which has now been killed. An
        empty set means no test leaked.
    """
    candidates = registered_pids() if pids is None else {int(p) for p in pids}
    leaked = {pid for pid in candidates if alive_fn(pid)}
    for pid in leaked:
        kill_fn(pid)
    return leaked
