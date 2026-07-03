"""Tests for the competitive coverage matrix (D1, issue #1233).

These pin the **matrix-generation logic** — cell classification, the moat
detection ("naturo passes where every rival returns nothing"), and the Markdown
rendering published to ``docs/COMPETITIVE.md``. They import only
``benchmarks.competitive.matrix``, which pulls in neither naturo nor any rival
library, so they collect and pass on Linux/macOS CI (D1 criterion 4).

The live head-to-head runs against real windows (``harness.py`` +
``run_competitive.py``) are Windows-desktop QA, not exercised here.
"""
from __future__ import annotations

from benchmarks.competitive import matrix
from benchmarks.competitive.matrix import (
    BLOCKED,
    NATURO,
    NONE,
    PASS,
    CompetitiveResult,
    build_matrix,
    format_matrix_markdown,
    rivals_in,
)


def _electron_row() -> CompetitiveResult:
    """A framework where naturo passes and both rivals return nothing (the moat)."""
    return CompetitiveResult(
        app="Electron fixture",
        framework="Electron/CDP",
        counts={NATURO: 84, "pywinauto": 0, "pyautogui": 0},
    )


def _uia_row() -> CompetitiveResult:
    """A UIA-native app where pywinauto also passes (honest, not a moat cell)."""
    return CompetitiveResult(
        app="Notepad",
        framework="UIA",
        counts={NATURO: 30, "pywinauto": 28, "pyautogui": 0},
    )


def test_cell_classifies_pass_none_and_blocked() -> None:
    """A count>0 is pass, ==0 is none, and None is blocked: needs env."""
    row = CompetitiveResult(
        app="x", framework="UIA",
        counts={NATURO: 5, "pywinauto": 0, "pyautogui": None},
    )
    assert row.cell(NATURO) == PASS
    assert row.cell("pywinauto") == NONE
    assert row.cell("pyautogui") == BLOCKED


def test_beats_only_when_rival_ran_and_saw_nothing() -> None:
    """naturo 'beats' a rival only when the rival ran (count 0), not when blocked."""
    moat = _electron_row()
    assert moat.beats("pywinauto") is True
    assert moat.beats("pyautogui") is True

    tie = _uia_row()
    assert tie.beats("pywinauto") is False  # rival also passed

    blocked = CompetitiveResult(
        app="x", framework="UIA", counts={NATURO: 5, "pywinauto": None},
    )
    assert blocked.beats("pywinauto") is False  # blocked ≠ beaten

    naturo_blank = CompetitiveResult(
        app="x", framework="SAP", counts={NATURO: 0, "pywinauto": 0},
    )
    assert naturo_blank.beats("pywinauto") is False  # naturo saw nothing too


def test_naturo_count_defaults_to_zero() -> None:
    """A missing/None naturo entry counts as zero, never crashes."""
    assert CompetitiveResult(app="x", framework="UIA", counts={}).naturo_count == 0
    assert CompetitiveResult(
        app="x", framework="UIA", counts={NATURO: None}
    ).naturo_count == 0


def test_rivals_in_is_stable_and_excludes_naturo() -> None:
    """Rival columns follow DEFAULT_RIVALS order regardless of measurement order."""
    rows = [
        CompetitiveResult(app="a", framework="UIA",
                          counts={"pyautogui": 0, NATURO: 3, "pywinauto": 2}),
    ]
    assert rivals_in(rows) == ["pywinauto", "pyautogui"]


def test_build_matrix_detects_moat_frameworks() -> None:
    """moat_frameworks lists only frameworks where naturo beats every rival that ran."""
    summary = build_matrix([_electron_row(), _uia_row()])
    assert summary["rivals"] == ["pywinauto", "pyautogui"]
    assert summary["moat_frameworks"] == ["Electron/CDP"]  # UIA excluded (tie)
    electron = next(r for r in summary["rows"] if r["framework"] == "Electron/CDP")
    assert electron["beats"] == ["pywinauto", "pyautogui"]


def test_build_matrix_no_moat_when_only_blocked_rivals() -> None:
    """A framework where the only rivals are blocked is not a proven moat."""
    row = CompetitiveResult(
        app="x", framework="SAP GUI",
        counts={NATURO: 40, "pywinauto": None, "pyautogui": None},
    )
    assert build_matrix([row])["moat_frameworks"] == []


def test_markdown_has_header_cells_legend_and_moat() -> None:
    """The rendered matrix carries the table, honest cell glyphs, legend and moat."""
    md = format_matrix_markdown([_electron_row(), _uia_row()])
    assert "| App | Framework | naturo | pywinauto | PyAutoGUI |" in md
    assert "✓ (84)" in md          # naturo pass with count
    assert "✗ (0)" in md           # rival ran, saw nothing
    assert "Moat (from real runs)" in md
    assert "Electron/CDP" in md
    assert "Legend:" in md


def test_markdown_renders_blocked_cells_and_notes() -> None:
    """Blocked rivals render `blocked: needs env` in-cell and in the notes list."""
    row = CompetitiveResult(
        app="x", framework="UIA",
        counts={NATURO: 5, "pywinauto": None, "pyautogui": None},
    )
    md = format_matrix_markdown(
        row and [row],
        blocked_rivals={"pywinauto": "Windows-only, not installed here."},
        generated_note="Generated from a real run on WIN-RUNNER, 2026-07-03.",
    )
    assert "`blocked: needs env`" in md
    assert "Windows-only, not installed here." in md
    assert "Generated from a real run" in md


def test_matrix_module_imports_without_naturo_or_rivals() -> None:
    """Guardrail: the matrix core must stay import-light (Linux-collectable)."""
    import sys

    # Importing matrix must not have pulled in naturo or the rival libraries.
    assert "benchmarks.competitive.matrix" in sys.modules
    assert matrix.NATURO == "naturo"
