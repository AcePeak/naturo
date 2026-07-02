"""Guaranteed PID-scoped teardown for tests that launch real GUI apps (M4-3).

Tests that did ``proc = subprocess.Popen(["calc.exe"]) ... proc.terminate()``
leak on Windows 11: a UWP app's window-owner process (``CalculatorApp.exe``) is
not the launcher PID, so terminating the launcher leaves the app running.

``tracked_launch`` returns a Popen wrapper whose ``terminate()``/``kill()`` do a
PID-scoped teardown of the app it actually started — the *new* watched-app PIDs
that appeared since launch, plus the launcher — via ``taskkill /F /T /PID``.
``/F`` force-closes so a Save/Don't-Save dialog cannot strand the process; ``/T``
reaps the child tree. It never kills by image name, so pre-existing windows the
user already had open are untouched. Callers keep their existing
``finally: proc.terminate()`` — only the launch line changes.

The PID-diff logic takes an injectable pid-lister, so it is unit-testable and
Linux-collectable; the default lister uses ``tasklist``.
"""
from __future__ import annotations

import subprocess
import time
from typing import Callable, Iterable

# Image names to match when reaping a launched app (window-owner may differ from
# the launcher, esp. for UWP apps hosted by a broker).
NOTEPAD_IMAGES = ("Notepad.exe",)
CALCULATOR_IMAGES = ("CalculatorApp.exe", "Calculator.exe")

PidLister = Callable[[Iterable[str]], "set[int]"]


def _tasklist_app_pids(image_names: Iterable[str]) -> "set[int]":
    """PIDs of running processes whose image matches any of *image_names*."""
    pids: "set[int]" = set()
    for name in image_names:
        try:
            out = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
        except Exception:
            continue
        for line in out.stdout.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2 and parts[0].lower() == name.lower():
                try:
                    pids.add(int(parts[1]))
                except ValueError:
                    continue
    return pids


def _pid_scoped_kill(pids: Iterable[int]) -> None:
    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass


class TrackedProc:
    """Popen wrapper: ``terminate()``/``kill()`` PID-scoped-reap the launched app.

    Proxies all other attributes (``pid``, ``poll``, ``wait``, …) to the real
    Popen, so existing test code is unaffected.
    """

    def __init__(self, proc, image_names, baseline, pid_lister):
        self._proc = proc
        self._images = tuple(image_names)
        self._baseline = set(baseline)
        self._pid_lister = pid_lister
        self._reaped = False

    def __getattr__(self, name):
        return getattr(self._proc, name)

    def _reap(self) -> None:
        if self._reaped:
            return
        self._reaped = True
        launched = set(self._pid_lister(self._images)) - self._baseline
        try:
            launched.add(self._proc.pid)
        except Exception:
            pass
        _pid_scoped_kill(launched)
        try:
            self._proc.terminate()  # reap the launcher handle itself
        except Exception:
            pass

    def terminate(self) -> None:
        self._reap()

    def kill(self) -> None:
        self._reap()


def tracked_launch(cmd, image_names, settle: float = 0.0, pid_lister: PidLister = _tasklist_app_pids):
    """Launch *cmd* and return a :class:`TrackedProc` for PID-scoped teardown.

    Args:
        cmd: Popen argument (list or string).
        image_names: image names of the app's window-owner process(es).
        settle: seconds to wait after launch (0 = caller handles timing).
        pid_lister: ``(image_names) -> set[pid]`` (injectable for tests).
    """
    baseline = set(pid_lister(image_names))
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if settle:
        time.sleep(settle)
    return TrackedProc(proc, image_names, baseline, pid_lister)
