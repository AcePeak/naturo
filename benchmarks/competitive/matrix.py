"""Competitive coverage matrix — pure aggregation + Markdown rendering (D1).

This module holds the *pure* part of the competitive benchmark: it turns a list
of :class:`CompetitiveResult` measurements (naturo vs each real, installed OSS
rival on the **same** window) into the published coverage matrix.

It deliberately imports **neither naturo nor any rival library**, so it stays
importable and testable on Linux/macOS CI — the matrix-generation logic is the
part D1 pins with a test (``pytest`` exits 0, Linux-collectable). The runtime
part that actually drives naturo + the rivals against real windows lives in
``harness.py`` (Windows-only, guarded imports).

Cell semantics (honest, not cherry-picked)
------------------------------------------
Each ``(app, framework, rival)`` measurement is a recognized-element **count**,
or ``None`` when the rival could not run on the host at all:

* ``pass``    -- the tool recognized ≥1 interactive element (``count > 0``).
* ``none``    -- the tool ran but recognized **nothing** (``count == 0``): the
  framework's content is invisible to it. This is the moat cell when naturo
  passes and a rival returns ``none``.
* ``blocked`` -- the tool is not installable/runnable here (``count is None``);
  rendered ``blocked: needs env``, never guessed.

naturo's own gaps are rendered the same way (a naturo ``none``/``blocked`` cell
shows honestly), so the matrix cannot cherry-pick.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

#: The tool key reserved for naturo itself in every ``counts`` mapping.
NATURO = "naturo"

#: Reproducibly pip-installable OSS rivals, in display order. Others
#: (UFO²/Windows-MCP/Terminator) are recorded as ``blocked: needs env`` rows by
#: the runner when they do not install cleanly on the host.
DEFAULT_RIVALS: List[str] = ["pywinauto", "pyautogui"]

#: Human-facing display labels for tool keys.
DISPLAY_NAMES: Dict[str, str] = {
    NATURO: "naturo",
    "pywinauto": "pywinauto",
    "pyautogui": "PyAutoGUI",
}

# Cell classes.
PASS = "pass"
NONE = "none"
BLOCKED = "blocked"


@dataclass
class CompetitiveResult:
    """One head-to-head measurement of naturo vs rivals on a single window.

    Attributes:
        app: Human-readable application label (e.g. ``"Owned Electron fixture"``).
        framework: The UI framework exercised (``"Electron/CDP"``, ``"Java
            Access Bridge"``, ``"UIA"`` ...).
        counts: Tool key -> recognized element count. ``None`` for a tool that
            could not run on this host. MUST contain a ``naturo`` entry.
        notes: Free-form provenance/caveat note carried into the report.
    """

    app: str
    framework: str
    counts: Dict[str, Optional[int]] = field(default_factory=dict)
    notes: str = ""

    @property
    def naturo_count(self) -> int:
        """naturo's recognized-element count (0 if it recognized nothing)."""
        return self.counts.get(NATURO) or 0

    def cell(self, tool: str) -> str:
        """Classify one tool's result into a cell class (``pass``/``none``/``blocked``)."""
        count = self.counts.get(tool)
        if count is None:
            return BLOCKED
        return PASS if count > 0 else NONE

    def beats(self, rival: str) -> bool:
        """True when naturo recognizes elements the rival returns nothing on.

        The moat claim, measured per row: naturo ``pass`` while ``rival`` ran and
        recognized nothing (``count == 0``). A ``blocked`` rival does not count
        as beaten — we only claim superiority where the rival actually ran.
        """
        return self.naturo_count > 0 and self.counts.get(rival) == 0


def rivals_in(results: List[CompetitiveResult]) -> List[str]:
    """Return the rival tool keys present across ``results`` (naturo excluded).

    Order follows :data:`DEFAULT_RIVALS` first, then any extra keys seen, so the
    published column order is stable regardless of measurement order.
    """
    seen = {tool for r in results for tool in r.counts if tool != NATURO}
    ordered = [t for t in DEFAULT_RIVALS if t in seen]
    ordered += sorted(t for t in seen if t not in DEFAULT_RIVALS)
    return ordered


def build_matrix(results: List[CompetitiveResult]) -> dict:
    """Aggregate measurements into a JSON-serialisable matrix summary.

    Returns a dict with:

    * ``rivals`` -- ordered rival tool keys (columns after naturo).
    * ``rows``   -- one entry per result: app, framework, per-tool ``{cell,
      count}``, and ``beats`` (rivals this row proves naturo superior on).
    * ``moat_frameworks`` -- frameworks where naturo passes and **every** rival
      that ran returned nothing (the headline: "them 0 / naturo pass").
    """
    rivals = rivals_in(results)
    rows = []
    moat_frameworks = []
    for r in results:
        tools = [NATURO, *rivals]
        cells = {t: {"cell": r.cell(t), "count": r.counts.get(t)} for t in tools}
        beaten = [rv for rv in rivals if r.beats(rv)]
        rows.append(
            {
                "app": r.app,
                "framework": r.framework,
                "cells": cells,
                "beats": beaten,
            }
        )
        ran_rivals = [rv for rv in rivals if r.cell(rv) != BLOCKED]
        if r.naturo_count > 0 and ran_rivals and all(r.beats(rv) for rv in ran_rivals):
            if r.framework not in moat_frameworks:
                moat_frameworks.append(r.framework)
    return {"rivals": rivals, "rows": rows, "moat_frameworks": moat_frameworks}


def _cell_md(cell: str, count: Optional[int]) -> str:
    """Render one matrix cell to Markdown."""
    if cell == PASS:
        return f"✓ ({count})"
    if cell == NONE:
        return "✗ (0)"
    return "`blocked: needs env`"


def format_matrix_markdown(
    results: List[CompetitiveResult],
    *,
    blocked_rivals: Optional[Dict[str, str]] = None,
    generated_note: str = "",
) -> str:
    """Render the coverage matrix as Markdown for ``docs/COMPETITIVE.md``.

    Args:
        results: Head-to-head measurements (from real runs).
        blocked_rivals: Optional map of rival name -> reason for rivals that
            could not be installed/run here at all (e.g. Windows-only tools on a
            Linux host), listed below the table as ``blocked: needs env``.
        generated_note: Optional provenance line (e.g. host + date) so readers
            know the numbers came from a real run, not authorship.

    Returns:
        A Markdown string: a table (naturo + rival columns), a legend, a
        headline moat line, and any ``blocked: needs env`` notes.
    """
    rivals = rivals_in(results)
    tools = [NATURO, *rivals]
    header = "| App | Framework | " + " | ".join(DISPLAY_NAMES.get(t, t) for t in tools) + " |"
    sep = "| --- | --- | " + " | ".join([":--:"] * len(tools)) + " |"
    lines = [header, sep]
    for r in results:
        cells = " | ".join(_cell_md(r.cell(t), r.counts.get(t)) for t in tools)
        lines.append(f"| {r.app} | {r.framework} | {cells} |")

    out = "\n".join(lines)

    summary = build_matrix(results)
    if summary["moat_frameworks"]:
        fw = ", ".join(summary["moat_frameworks"])
        out += (
            "\n\n**Moat (from real runs):** naturo recognizes interactive "
            f"elements on **{fw}** where every rival that ran returned nothing."
        )

    out += (
        "\n\n_Legend: ✓ (n) = recognized n interactive elements · ✗ (0) = ran "
        "but recognized nothing · `blocked: needs env` = tool not runnable on "
        "this host._"
    )

    if blocked_rivals:
        out += "\n\n**Rivals not runnable here (`blocked: needs env`):**\n"
        out += "\n".join(
            f"- {DISPLAY_NAMES.get(name, name)}: {reason}"
            for name, reason in sorted(blocked_rivals.items())
        )

    if generated_note:
        out += f"\n\n_{generated_note}_"

    return out
