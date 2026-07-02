"""M4 criterion 3 — unit tests for PID-scoped guaranteed app teardown.

Drives ``TrackedProc`` with a fake process + injected pid-lister and a patched
``kill_pid`` — no real processes are ever opened or terminated, so this is safe
to run on Windows and Linux-collectable. Proves teardown targets only the PIDs
the launch introduced (launcher + new window-owner), never pre-existing ones, and
is idempotent.
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


def _killed(kill_mock):
    return {c.args[0] for c in kill_mock.call_args_list}


def test_terminate_kills_only_launched_pids_not_preexisting():
    """UWP case: launcher pid 3, pre-existing app pid 1, launched window-owner
    pid 2 → reap {2, 3}, never the pre-existing 1."""
    proc = _FakeProc(pid=3)
    tp = TrackedProc(proc, CALCULATOR_IMAGES, baseline={1}, pid_lister=lambda imgs: {1, 2})
    with patch("tests._launch.kill_pid") as kp:
        tp.terminate()
    killed = _killed(kp)
    assert killed == {2, 3}
    assert 1 not in killed          # pre-existing user window untouched
    assert proc.terminated          # launcher handle reaped


def test_kill_is_pid_scoped_alias():
    proc = _FakeProc(pid=9)
    tp = TrackedProc(proc, NOTEPAD_IMAGES, baseline={7}, pid_lister=lambda imgs: {7, 8})
    with patch("tests._launch.kill_pid") as kp:
        tp.kill()
    assert _killed(kp) == {8, 9}


def test_reap_is_idempotent():
    """A second terminate()/kill() must not issue more kills."""
    proc = _FakeProc(pid=3)
    tp = TrackedProc(proc, NOTEPAD_IMAGES, baseline=set(), pid_lister=lambda imgs: {5})
    with patch("tests._launch.kill_pid") as kp:
        tp.terminate()
        first = kp.call_count
        tp.kill()
        assert kp.call_count == first


def test_no_launched_pids_still_reaps_launcher():
    """Classic app where the launcher owns the window: the launcher pid is killed."""
    proc = _FakeProc(pid=42)
    tp = TrackedProc(proc, NOTEPAD_IMAGES, baseline={42}, pid_lister=lambda imgs: {42})
    with patch("tests._launch.kill_pid") as kp:
        tp.terminate()
    assert _killed(kp) == {42}


def test_proxies_attributes_to_real_popen():
    proc = _FakeProc(pid=42)
    tp = TrackedProc(proc, NOTEPAD_IMAGES, baseline=set(), pid_lister=lambda imgs: set())
    assert tp.pid == 42             # proxied
    assert tp.poll() is None        # proxied


def test_kill_pid_never_raises_and_attempts_taskkill_fallback():
    """kill_pid on a definitely-invalid PID must not raise and must still attempt
    the taskkill fallback (Win32 TerminateProcess can't open an invalid PID)."""
    from tests._launch import kill_pid

    with patch("tests._launch.subprocess.run") as run:
        result = kill_pid(4294967295)  # invalid PID -> OpenProcess NULL, no terminate
    args = run.call_args[0][0] if run.call_args else []
    assert "taskkill" in args and "/PID" in args and "4294967295" in args
    assert result in (True, False)  # never raises
