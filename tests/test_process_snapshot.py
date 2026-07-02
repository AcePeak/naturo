"""M4 criterion 3 — unit tests for the process-snapshot orphan harness.

Pure snapshot/diff logic driven by a fake process lister — no real processes,
Linux-collectable. Proves the harness detects leaked test-launched apps, ignores
pre-existing ones, and NEVER flags shells/terminals/the runner (enforcing
"cmd/terminals never touched").
"""
from __future__ import annotations

from tests._process_snapshot import (
    NEVER_WATCH,
    WATCHED_APP_NAMES,
    find_orphans,
    snapshot,
)


def _lister(pairs):
    return lambda: list(pairs)


def test_detects_leaked_app():
    before = snapshot(_lister([]))
    after = snapshot(_lister([("Notepad.exe", 100)]))
    assert find_orphans(before, after) == {"notepad.exe": {100}}


def test_ignores_preexisting_process():
    """A process present both before and after was not launched by the suite."""
    before = snapshot(_lister([("notepad.exe", 100)]))
    after = snapshot(_lister([("notepad.exe", 100)]))
    assert find_orphans(before, after) == {}


def test_partial_leak_same_app_new_pid():
    before = snapshot(_lister([("notepad.exe", 100)]))
    after = snapshot(_lister([("notepad.exe", 100), ("notepad.exe", 200)]))
    assert find_orphans(before, after) == {"notepad.exe": {200}}


def test_cmd_and_terminals_are_never_flagged():
    """The core safety property: shells/terminals/the runner are NEVER watched,
    even when they appear only in the 'after' snapshot."""
    before = snapshot(_lister([]))
    after = snapshot(_lister([
        ("cmd.exe", 11), ("conhost.exe", 12), ("powershell.exe", 13),
        ("pwsh.exe", 14), ("windowsterminal.exe", 15), ("python.exe", 16),
        ("pytest.exe", 17), ("bash.exe", 18), ("ssh.exe", 19), ("explorer.exe", 20),
    ]))
    assert after == {}
    assert find_orphans(before, after) == {}


def test_only_watched_app_names_tracked():
    """A random unwatched process is neither snapshotted nor flagged."""
    after = snapshot(_lister([("some_random_service.exe", 500)]))
    assert after == {}


def test_case_insensitive_image_names():
    after = snapshot(_lister([("CHROME.EXE", 700), ("MsEdge.exe", 701)]))
    assert after == {"chrome.exe": {700}, "msedge.exe": {701}}


def test_multiple_apps_mixed_leak_and_preexisting():
    before = snapshot(_lister([("chrome.exe", 1), ("excel.exe", 2)]))
    after = snapshot(_lister([
        ("chrome.exe", 1),           # pre-existing
        ("chrome.exe", 3),           # leaked
        ("excel.exe", 2),            # pre-existing
        ("notepad.exe", 4),          # leaked (new app)
        ("cmd.exe", 99),             # never watched
    ]))
    assert find_orphans(before, after) == {"chrome.exe": {3}, "notepad.exe": {4}}


def test_watch_and_never_watch_are_disjoint():
    """No image name may be both watched and never-watched (would be ambiguous)."""
    assert WATCHED_APP_NAMES.isdisjoint(NEVER_WATCH)
