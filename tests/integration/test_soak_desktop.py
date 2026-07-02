"""M4 criterion 4 — real desktop soak: >=100 recognition+action cycles, >=2 apps.

Gated ``@pytest.mark.desktop`` + ``@pytest.mark.soak`` so it is opt-in and never
runs on Linux CI or by default (``pytest`` defaults to ``-m "not ... desktop"``).
Isolated QA runs it with ``-m "desktop and soak"``. It launches Notepad and
Calculator via the PID-scoped guaranteed-teardown fixtures, then alternates
recognition (``get_element_tree``) + a benign action (``focus_window``) for 100
cycles, asserting the soak verdict: zero failures, zero process leak, zero memory
leak, no timing degradation.
"""
from __future__ import annotations

import pytest


@pytest.mark.desktop
@pytest.mark.soak
def test_soak_notepad_and_calculator_100_cycles(notepad_app, calculator_app):
    from naturo.backends.windows import WindowsBackend

    from tests._soak import real_sampler, run_soak

    backend = WindowsBackend()
    pids = [notepad_app, calculator_app]  # window-owner PIDs from the fixtures
    cycles = 100
    actions_fired = {"n": 0}

    def _hwnd_for(pid: int):
        for w in backend.list_windows():
            if getattr(w, "pid", None) == pid and getattr(w, "is_visible", False):
                return w.handle
        return None

    def cycle(i: int) -> None:
        pid = pids[i % len(pids)]
        # Recognition: fuse the app's element tree (deterministic UIA path).
        tree = backend.get_element_tree(pid=pid, depth=3)
        assert tree is not None, f"cycle {i}: no element tree for pid {pid}"
        # Action: re-focus the app's window (benign, idempotent, targets the
        # launched app by hwnd — never the terminal). Count firings so a run
        # where the window can't be resolved can't masquerade as a clean soak;
        # a rare transient miss is tolerated by the 95% floor asserted below.
        hwnd = _hwnd_for(pid)
        if hwnd is not None:
            backend.focus_window(hwnd=hwnd)
            actions_fired["n"] += 1

    result = run_soak(cycle, cycles, sampler=real_sampler)
    assert result.ok, (
        result.summary() + f" | first failures: {result.failures[:5]}"
    )
    # Guard against a recognition-only pass: the action must genuinely fire for
    # (nearly) every cycle, else "0 failures" would mask "action never ran".
    assert actions_fired["n"] >= cycles * 0.95, (
        f"action fired only {actions_fired['n']}/{cycles} cycles — not a full "
        "recognition+action soak"
    )
