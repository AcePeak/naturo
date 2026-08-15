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
    INTERACTIVE_ROLES,
    NATURO,
    NONE,
    PASS,
    CompetitiveResult,
    build_matrix,
    count_interactive,
    format_matrix_markdown,
    is_interactive_role,
    normalize_role,
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


# --- "Meaningful interactive element" metric (issue #1233 follow-up) ----------
# These pin the honesty invariant: one symmetric role allowlist, applied
# identically to naturo and every rival, so a raw descendants() walk can no
# longer flatter a UIA-only rival on Chromium/Excel with static/decorative nodes.


def test_normalize_role_folds_spellings() -> None:
    """Spaces, hyphens and case collapse so every backend's spelling compares equal."""
    assert normalize_role("Radio Button") == "radiobutton"
    assert normalize_role("radio-button") == "radiobutton"
    assert normalize_role("RADIOBUTTON") == "radiobutton"
    assert normalize_role(None) == ""
    assert normalize_role("") == ""


def test_is_interactive_role_allowlists_actionable_and_excludes_decorative() -> None:
    """Actionable roles count; static/layout/decorative roles do not."""
    for actionable in ("Button", "Edit", "ComboBox", "CheckBox", "RadioButton",
                       "Hyperlink", "MenuItem", "ListItem", "TreeItem", "TabItem",
                       "DataItem", "Slider", "Document"):
        assert is_interactive_role(actionable) is True, actionable
    for decorative in ("Text", "Pane", "Group", "Separator", "Image", "TitleBar",
                       "StatusBar", "ToolTip", "Custom", "Window", "", None):
        assert is_interactive_role(decorative) is False, decorative


def test_count_interactive_is_the_one_shared_symmetric_filter() -> None:
    """The exact same function reduces any role list — naturo and rival alike.

    A Chromium-style dump (mostly static Text/Pane) yields few interactive nodes;
    the same allowlist applied to the same roles gives the same count no matter
    which adapter produced them. This *is* the anti-cherry-pick guarantee.
    """
    chromium_dump = (
        ["Document"] + ["Text"] * 60 + ["Pane"] * 30
        + ["Button"] * 8 + ["Hyperlink"] * 4 + ["Edit"] * 2
    )
    # 1 Document + 8 Button + 4 Hyperlink + 2 Edit = 15 interactive of 105 raw.
    assert len(chromium_dump) == 105
    assert count_interactive(chromium_dump) == 15
    # Symmetry: feeding the identical roles as if from a different adapter is equal.
    assert count_interactive(list(chromium_dump)) == 15
    # Every allowlist member is individually counted.
    assert count_interactive(sorted(INTERACTIVE_ROLES)) == len(INTERACTIVE_ROLES)


def _misleading_electron_row() -> CompetitiveResult:
    """Raw count says the UIA-only rival 'wins' Chromium; interactive says naturo does.

    Mirrors the real measured contradiction: pywinauto's raw descendants() walk
    (113) tops naturo's raw (85) by counting static text/panes, but on actionable
    elements naturo (40) leads and pywinauto (10) does not vanish.
    """
    return CompetitiveResult(
        app="Chromium fixture",
        framework="Electron/CDP",
        counts={NATURO: 85, "pywinauto": 113, "pyautogui": 0},
        interactive_counts={NATURO: 40, "pywinauto": 10, "pyautogui": 0},
    )


def _java_moat_row() -> CompetitiveResult:
    """Java/Swing: the uncontested moat — the UIA-only rival sees nothing, raw or interactive."""
    return CompetitiveResult(
        app="Java Swing fixture",
        framework="Java Access Bridge",
        counts={NATURO: 46, "pywinauto": 6, "pyautogui": 0},
        interactive_counts={NATURO: 22, "pywinauto": 0, "pyautogui": 0},
    )


def test_interactive_metric_reverses_a_misleading_raw_lead() -> None:
    """The rival leads on raw but trails on actionable elements — honestly shown both ways.

    A ``beat`` still means the rival saw *nothing* (moat). Chromium is not a moat
    (the rival sees 10 actionable nodes), so this is the spec's ``~`` parity/lead
    case, not a moat — that distinction is the whole point of the honest metric.
    """
    row = _misleading_electron_row()
    # Raw view (default) shows the rival ahead — we never hide it.
    assert row.naturo_count == 85 and row.counts["pywinauto"] == 113
    assert row.beats("pywinauto") is False          # raw: not a moat
    assert row.cell("pywinauto") == PASS            # raw: rival passed
    # Interactive view: the lead reverses (naturo 40 > rival 10) but it is a lead,
    # not a moat — the rival still recognizes actionable elements here.
    assert row.naturo_count_for("interactive") == 40
    assert row.cell("pywinauto", "interactive") == PASS        # rival still passes (10)
    assert row.beats("pywinauto", "interactive") is False      # 10 ≠ 0 → not a moat
    assert row.has_interactive() is True


def test_moat_cells_survive_the_interactive_metric() -> None:
    """The genuine Java moat stays ✗ (0); the misleading Chromium 'win' does NOT become a moat."""
    summary = build_matrix([_java_moat_row(), _misleading_electron_row()])
    # Only Java is a real moat under the honest metric — Chromium is a lead, not a moat.
    assert summary["moat_frameworks"] == ["Java Access Bridge"]
    java = next(r for r in summary["rows"] if r["framework"] == "Java Access Bridge")
    assert java["metric"] == "interactive"
    assert java["cells"]["pywinauto"]["cell"] == NONE   # ✗ (0), moat holds
    assert java["cells"]["pywinauto"]["raw"] == 6
    assert java["cells"]["pywinauto"]["interactive"] == 0
    electron = next(r for r in summary["rows"] if r["framework"] == "Electron/CDP")
    assert electron["cells"]["pywinauto"]["cell"] == PASS  # rival ran, saw 10 → not a moat


def test_markdown_dual_metric_shows_both_interactive_and_raw() -> None:
    """When interactive counts exist the table leads with them and shows raw alongside."""
    md = format_matrix_markdown([_misleading_electron_row(), _java_moat_row()])
    assert "✓ (40 · raw 85)" in md      # naturo Chromium: interactive · raw
    assert "✗ (0 · raw 6)" in md        # rival Java: ran, no interactive element
    assert "meaningful interactive" in md
    assert "Moat (from real runs)" in md


def test_legacy_rows_without_interactive_render_unchanged() -> None:
    """A row with no interactive_counts keeps the exact legacy raw-only rendering."""
    row = CompetitiveResult(
        app="Electron fixture", framework="Electron/CDP",
        counts={NATURO: 84, "pywinauto": 0, "pyautogui": 0},
    )
    md = format_matrix_markdown([row])
    assert "✓ (84)" in md               # legacy single-number cell
    assert "· raw" not in md            # dual rendering must stay off
    assert row.has_interactive() is False
