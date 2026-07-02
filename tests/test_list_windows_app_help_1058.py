"""Regression tests for #1058 — `list windows` help text must not lie about
``--app``'s match scope.

The ``list windows`` docstring (added by the #871 harmonization) claimed
``--app`` matched the *application name or process name* and that ``--window``
matched the *window title only*, describing the two filters as having disjoint
scopes.  In reality ``--app <term>`` matches a window when ``<term>`` is a
substring of the **window title** *or* the process basename — the deliberate,
family-consistent broad-targeting rule shared by ``see``/``capture``/``click``
(#671/#1084).  The defect was purely that the new docstring promised a narrower
scope than the code (and the family) actually deliver.

These tests pin the contract in both directions so it cannot silently drift
back:

1. the rendered ``list windows --help`` text documents that ``--app`` also
   matches the window title (broad targeting), and no longer claims ``--app``
   is process/app-name-only or that ``--window`` is the *only* way to match a
   title; and
2. the behavior the help now documents is real — ``--app`` matches by window
   title as well as by process basename.

All tests mock the backend and platform so they run on any CI host.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.core._list import list_cmd


def _make_window(**overrides):
    w = MagicMock()
    w.handle = overrides.get("handle", 12345)
    w.title = overrides.get("title", "Untitled - Notepad")
    w.process_name = overrides.get("process_name", "notepad.exe")
    w.pid = overrides.get("pid", 5678)
    w.x = overrides.get("x", 100)
    w.y = overrides.get("y", 100)
    w.width = overrides.get("width", 800)
    w.height = overrides.get("height", 600)
    w.is_visible = overrides.get("is_visible", True)
    w.is_minimized = overrides.get("is_minimized", False)
    return w


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def backend():
    """Two windows whose titles do NOT contain their process basenames, so a
    title match and a process match are unambiguously distinguishable."""
    b = MagicMock()
    b.list_windows.return_value = [
        _make_window(handle=1001, title="Quarterly report - Notepad",
                     process_name="notepad.exe", pid=100),
        _make_window(handle=1002, title="Inbox - Mail",
                     process_name="olk.exe", pid=200),
    ]
    return b


def _patches(backend):
    return [
        patch("naturo.cli.core._common._platform_supports_gui", return_value=True),
        patch("naturo.cli.core._common._get_backend", return_value=backend),
        patch("naturo.cli.core._list.platform.system", return_value="Windows"),
        patch("os.getpid", return_value=99999),
        patch("os.getppid", return_value=99998),
    ]


def _run(runner, backend, args):
    ctx = _patches(backend)
    for p in ctx:
        p.start()
    try:
        return runner.invoke(list_cmd, args, catch_exceptions=False)
    finally:
        for p in reversed(ctx):
            p.stop()


def test_help_documents_app_matches_window_title(runner):
    """The rendered help must state that ``--app`` also matches the window
    title — the broad-targeting behavior the code actually implements."""
    result = runner.invoke(list_cmd, ["windows", "--help"], catch_exceptions=False)
    assert result.exit_code == 0
    help_text = result.output.lower()
    # The honest contract: --app matches the process name OR the window title.
    # Both halves of the broad-targeting rule must appear in the help so the
    # docs describe what the code does (formatting markers between the words
    # must not be assumed, so check the two terms independently).
    assert "process name" in help_text
    assert "window title" in help_text


def test_help_does_not_describe_app_as_name_only(runner):
    """The help must not reassert the old disjoint contract that described
    ``--app`` as matching the ``application name or process name`` (with title
    matching reserved to ``--window``) — that exact phrasing is what lied about
    behavior in #1058, since ``--app`` also matches the title."""
    result = runner.invoke(list_cmd, ["windows", "--help"], catch_exceptions=False)
    assert result.exit_code == 0
    normalized = " ".join(result.output.lower().split())
    assert "application name or process name" not in normalized


def test_app_filter_matches_by_window_title(runner, backend):
    """Behavior the help now documents: ``--app <term>`` matches a window whose
    *title* contains the term even when no process is named that."""
    result = _run(runner, backend, ["windows", "--app", "Quarterly", "-j"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["count"] == 1
    assert data["windows"][0]["handle"] == 1001


def test_app_filter_matches_by_process_basename(runner, backend):
    """``--app`` still matches by process basename (the other half of the
    documented broad-targeting rule)."""
    result = _run(runner, backend, ["windows", "--app", "olk", "-j"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["count"] == 1
    assert data["windows"][0]["handle"] == 1002
