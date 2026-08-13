"""Never-Lie regression tests for ``quit_app`` (#1197).

The confirmed bug: ``quit_app("notepad")`` (and even ``force=True``) returned
success while Notepad was still running — Win11 Notepad's real windows are
owned by a long-lived process, not the launcher/stub PID that ``launch_app``
returned, so quitting by the stale name/PID killed nothing that mattered and
reported success without verifying.

These tests exercise the Windows backend ``AppMixin.quit_app`` fix entirely
hermetically: a fake backend supplies the window list and records terminated
PIDs. No real app is launched or killed, and no live desktop is touched — the
kill is modelled by mutating the fake's in-memory window list.
"""

from __future__ import annotations

import pytest

from naturo.backends.base import WindowInfo
from naturo.backends.windows._shell._app import AppMixin
from naturo.errors import ErrorCode, QuitIncompleteError


@pytest.fixture(autouse=True)
def _fast_clock(monkeypatch):
    """Drive ``quit_app``'s settle/graceful waits off a virtual clock so the
    hermetic tests are instant and deterministic (no real wall-clock sleeps)."""
    import naturo.backends.windows._shell._app as mod

    clock = {"t": 0.0}

    def _monotonic() -> float:
        clock["t"] += 0.5
        return clock["t"]

    def _sleep(secs: float) -> None:
        clock["t"] += secs

    monkeypatch.setattr(mod.time, "monotonic", _monotonic)
    monkeypatch.setattr(mod.time, "sleep", _sleep)


def _win(handle: int, pid: int, process_name: str, title: str = "Untitled") -> WindowInfo:
    return WindowInfo(
        handle=handle, title=title, process_name=process_name, pid=pid,
        x=0, y=0, width=800, height=600, is_visible=True, is_minimized=False,
    )


class FakeAppBackend(AppMixin):
    """Minimal backend driving ``AppMixin.quit_app`` without any OS calls.

    ``list_windows`` is the single source of truth for "is the app still here".
    ``close_window`` (WM_CLOSE) and ``_force_kill_pid`` are overridden to mutate
    that list — modelling a real termination — and to record what they acted on.
    """

    _SYSTEM_PROCESS_NAMES: set[str] = set()
    _UWP_HOST_PROCESS: str = "applicationframehost.exe"

    def __init__(
        self,
        windows: list[WindowInfo],
        *,
        stubborn: bool = False,
        respawn_as: WindowInfo | None = None,
    ) -> None:
        self._windows = list(windows)
        self._stubborn = stubborn          # kills "succeed" but nothing dies
        self._respawn_as = respawn_as      # a new window appears after a kill
        self.closed: list[int] = []
        self.killed: list[int] = []

    # --- surfaces AppMixin.quit_app consumes -------------------------------
    def list_windows(self) -> list[WindowInfo]:
        return list(self._windows)

    def list_apps(self) -> list[dict]:  # no UWP host in these scenarios
        return []

    def close_window(self, title=None, hwnd=None, force=False) -> None:
        self.closed.append(hwnd)
        if self._stubborn:
            return
        self._windows = [w for w in self._windows if w.handle != hwnd]

    def _force_kill_pid(self, pid: int) -> None:
        self.killed.append(pid)
        if self._stubborn:
            return
        self._windows = [w for w in self._windows if w.pid != pid]
        if self._respawn_as is not None:
            # Win11 Notepad crash-recovery: a NEW process owns a window again.
            self._windows.append(self._respawn_as)
            self._respawn_as = None


# ── 1. Window-owned-by-a-different-PID-than-the-stub → resolve, kill, verify ──

def test_resolves_window_owning_pid_not_launch_stub():
    """The real window is owned by PID 4242 (the launch stub 1111 is irrelevant).

    quit must resolve 4242 from window ownership, kill it, verify gone, succeed.
    """
    be = FakeAppBackend([_win(handle=10, pid=4242, process_name=r"C:\Windows\notepad.exe")])

    be.quit_app(name="notepad", force=True)  # must not raise

    assert be.killed == [4242]            # resolved the window owner, not a stub
    assert be._windows == []              # verified actually gone


# ── 2. THE bug: terminate "succeeds" but a window survives → QUIT_INCOMPLETE ──

def test_survivor_window_reports_quit_incomplete_not_success():
    """Kill returns, but the app still owns a window — must NOT report success.

    This is the exact #1197 regression: never report success while the app
    survives. A stubborn backend keeps the window on every re-enumeration.
    """
    be = FakeAppBackend(
        [_win(handle=10, pid=4242, process_name=r"C:\Windows\notepad.exe")],
        stubborn=True,
    )

    with pytest.raises(QuitIncompleteError) as ei:
        be.quit_app(name="notepad", force=True)

    assert be.killed == [4242]                      # it did try to kill
    assert ei.value.code == ErrorCode.QUIT_INCOMPLETE
    assert 4242 in ei.value.context["surviving_pids"]
    assert ei.value.context["respawned"] is False   # same PID survived


# ── 3. Respawn: after kill a NEW app window appears → not-fully-quit ──────────

def test_crash_recovery_respawn_reported_as_not_quit():
    """After the kill, a fresh PID owns a Notepad window (crash recovery).

    Verification must detect the surviving window and report the truth, noting
    it is a respawn (a different PID than the one we terminated).
    """
    respawn = _win(handle=99, pid=99999, process_name=r"C:\Windows\notepad.exe", title="Notepad")
    be = FakeAppBackend(
        [_win(handle=10, pid=4242, process_name=r"C:\Windows\notepad.exe")],
        respawn_as=respawn,
    )

    with pytest.raises(QuitIncompleteError) as ei:
        be.quit_app(name="notepad", force=True)

    assert be.killed == [4242]                        # original owner killed
    assert ei.value.context["respawned"] is True      # new PID → respawn
    assert 99999 in ei.value.context["surviving_pids"]


# ── 4. force=False (graceful WM_CLOSE) vs force=True (immediate kill) ─────────

def test_graceful_path_uses_wm_close():
    """force=False sends WM_CLOSE to owned windows; no hard kill when it works."""
    be = FakeAppBackend([_win(handle=10, pid=4242, process_name=r"C:\Windows\notepad.exe")])

    be.quit_app(name="notepad", force=False)  # must not raise

    assert be.closed == [10]      # WM_CLOSE sent to the owned window
    assert be.killed == []        # graceful close sufficed — no taskkill /F
    assert be._windows == []


def test_force_path_hard_kills_without_wm_close():
    """force=True hard-kills the resolved PID set immediately, no WM_CLOSE."""
    be = FakeAppBackend([_win(handle=10, pid=4242, process_name=r"C:\Windows\notepad.exe")])

    be.quit_app(name="notepad", force=True)

    assert be.closed == []        # no graceful step
    assert be.killed == [4242]


def test_graceful_falls_back_to_kill_when_close_ignored():
    """A window that ignores WM_CLOSE is still hard-killed on the graceful path."""
    be = FakeAppBackend(
        [_win(handle=10, pid=4242, process_name=r"C:\Windows\notepad.exe")],
        stubborn=True,
    )

    with pytest.raises(QuitIncompleteError):
        be.quit_app(name="notepad", force=False)

    assert be.closed == [10]      # tried graceful first
    assert 4242 in be.killed      # then escalated to a hard kill


# ── 5. Safety: only PIDs that own a window of the NAMED app are killed ────────

def test_never_kills_pid_that_does_not_own_a_named_window():
    """A co-running app (calc, PID 7777) must never be terminated by quitting
    notepad — termination is scoped to the resolved window-owning PID set."""
    be = FakeAppBackend([
        _win(handle=10, pid=4242, process_name=r"C:\Windows\notepad.exe", title="Untitled - Notepad"),
        _win(handle=20, pid=7777, process_name=r"C:\Windows\System32\calc.exe", title="Calculator"),
    ])

    be.quit_app(name="notepad", force=True)  # must not raise

    assert be.killed == [4242]        # only notepad's owner
    assert 7777 not in be.killed      # the bystander is untouched
    # calc's window remains, but it is not the named app, so quit still succeeds
    assert [w.pid for w in be._windows] == [7777]


def test_no_window_owner_falls_back_to_name_taskkill(monkeypatch):
    """When the app owns no window, fall back to a name-based taskkill and,
    with nothing surviving, report success (no false failure either)."""
    calls: list = []

    class _Result:
        returncode = 0

    def _fake_run(cmd, *a, **k):
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr("naturo.backends.windows._shell._app.subprocess.run", _fake_run)

    be = FakeAppBackend([])  # no windows at all
    be.quit_app(name="ghost", force=False)  # must not raise

    assert calls and "ghost" in calls[0]  # fallback taskkill /IM used
