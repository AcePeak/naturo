"""Process-snapshot harness — detect test-launched processes that leaked (M4-3).

A before/after snapshot of GUI *app* processes lets the desktop/browser suite
assert it left **zero orphaned** processes. The snapshot/diff logic is pure and
takes an injectable process lister, so it is unit-testable and Linux-collectable;
the real lister uses ``tasklist``. The opt-in session fixture that runs it over
the real suite lives in ``tests/integration/conftest.py``.

Only GUI app processes the suite launches are watched (notepad, calculator,
chrome, msedge, excel, …). Shells, terminals, the Python test runner, and system
processes are **never** watched — the "cmd/terminals never touched" non-negotiable
means the harness must not so much as flag them, even if one appears mid-run.
"""
from __future__ import annotations

from typing import Callable, Iterable

# App image names the desktop/browser suite launches and must clean up.
WATCHED_APP_NAMES = frozenset({
    "notepad.exe",
    "calculatorapp.exe", "calculator.exe",
    "chrome.exe", "msedge.exe", "chromium.exe",
    "excel.exe", "winword.exe",
    "mspaint.exe", "wordpad.exe",
})

# Never watched / never touched: shells, terminals, the test runner, the shell.
# A process whose image is here is ignored unconditionally — the harness will
# never report it as an orphan and nothing may ever kill it.
NEVER_WATCH = frozenset({
    "cmd.exe", "conhost.exe", "powershell.exe", "pwsh.exe",
    "windowsterminal.exe", "openconsole.exe", "bash.exe", "sh.exe",
    "python.exe", "pythonw.exe", "pytest.exe", "py.exe",
    "explorer.exe", "ssh.exe", "sshd.exe", "code.exe",
})

# A process lister returns ``(image_name, pid)`` pairs; image name case-insensitive.
ProcList = Callable[[], Iterable["tuple[str, int]"]]


def snapshot(lister: ProcList, watch: "frozenset[str]" = WATCHED_APP_NAMES) -> "dict[str, set[int]]":
    """Return ``{app_name: {pids}}`` for watched apps only.

    Anything in :data:`NEVER_WATCH` is skipped unconditionally; anything not in
    *watch* is ignored (we only track apps the suite is responsible for).
    """
    result: "dict[str, set[int]]" = {}
    for name, pid in lister():
        n = name.lower()
        if n in NEVER_WATCH:
            continue
        if n in watch:
            result.setdefault(n, set()).add(pid)
    return result


def find_orphans(
    before: "dict[str, set[int]]", after: "dict[str, set[int]]",
) -> "dict[str, set[int]]":
    """Return watched PIDs present in *after* but not *before* — leaked processes."""
    orphans: "dict[str, set[int]]" = {}
    for name, pids in after.items():
        leaked = pids - before.get(name, set())
        if leaked:
            orphans[name] = leaked
    return orphans


def tasklist_lister() -> "list[tuple[str, int]]":
    """Real process lister via ``tasklist`` CSV. Windows-only; empty elsewhere."""
    import subprocess

    try:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return []
    procs: "list[tuple[str, int]]" = []
    for line in out.stdout.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2:
            try:
                procs.append((parts[0].lower(), int(parts[1])))
            except ValueError:
                continue
    return procs
