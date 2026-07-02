"""M4 criterion 3 — unit tests for PID-scoped guaranteed app teardown.

Drives ``TrackedProc`` with a fake process + injected pid-lister and a mocked
``subprocess.run`` — no real processes, Linux-collectable. Proves teardown kills
only the PIDs the launch introduced (launcher + new window-owner), never
pre-existing ones, and is idempotent.
"""
from __future__ import annotations

from unittest.mock import patch

from tests._launch import CALCULATOR_IMAGES, NOTEPAD_IMAGES, TrackedProc


class _FakeProc:
    def __init__(self, pid):
        self.pid = pid
        self.terminated = False

    def terminate(self):
        self.terminated = True

    def poll(self):
        return None


def _killed_pids(mock_run):
    killed = set()
    for call in mock_run.call_args_list:
        args = call.args[0] if call.args else call.kwargs.get("args", [])
        if args and args[0] == "taskkill" and "/PID" in args:
            killed.add(int(args[args.index("/PID") + 1]))
    return killed


def test_terminate_kills_only_launched_pids_not_preexisting():
    """UWP case: launcher pid 3, pre-existing app pid 1, launched window-owner
    pid 2 → kill {2, 3}, never the pre-existing 1."""
    proc = _FakeProc(pid=3)
    tp = TrackedProc(proc, CALCULATOR_IMAGES, baseline={1}, pid_lister=lambda imgs: {1, 2})
    with patch("tests._launch.subprocess.run") as run:
        tp.terminate()
    killed = _killed_pids(run)
    assert killed == {2, 3}
    assert 1 not in killed          # pre-existing user window untouched
    assert proc.terminated          # launcher handle reaped


def test_kill_is_pid_scoped_alias():
    proc = _FakeProc(pid=9)
    tp = TrackedProc(proc, NOTEPAD_IMAGES, baseline={7}, pid_lister=lambda imgs: {7, 8})
    with patch("tests._launch.subprocess.run") as run:
        tp.kill()
    assert _killed_pids(run) == {8, 9}


def test_reap_is_idempotent():
    """A second terminate()/kill() must not issue more kills."""
    proc = _FakeProc(pid=3)
    tp = TrackedProc(proc, NOTEPAD_IMAGES, baseline=set(), pid_lister=lambda imgs: {5})
    with patch("tests._launch.subprocess.run") as run:
        tp.terminate()
        first = run.call_count
        tp.kill()
        assert run.call_count == first


def test_no_launched_pids_still_reaps_launcher():
    """If nothing new appears (classic app where launcher owns the window), the
    launcher pid is still killed."""
    proc = _FakeProc(pid=42)
    tp = TrackedProc(proc, NOTEPAD_IMAGES, baseline={42}, pid_lister=lambda imgs: {42})
    with patch("tests._launch.subprocess.run") as run:
        tp.terminate()
    assert _killed_pids(run) == {42}


def test_proxies_attributes_to_real_popen():
    proc = _FakeProc(pid=42)
    tp = TrackedProc(proc, NOTEPAD_IMAGES, baseline=set(), pid_lister=lambda imgs: set())
    assert tp.pid == 42             # proxied
    assert tp.poll() is None        # proxied
