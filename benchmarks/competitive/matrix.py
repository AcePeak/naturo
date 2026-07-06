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
from typing import Dict, Iterable, List, Optional

#: The tool key reserved for naturo itself in every ``counts`` mapping.
NATURO = "naturo"

#: Roles/control-types an automation agent can **target for an action or a value
#: read** — the "meaningful interactive element" allowlist (see
#: ``docs/design/MEANINGFUL_INTERACTIVE_ELEMENT_METRIC.md``). Normalised form:
#: lower-cased with spaces/hyphens/underscores stripped, so ``"Radio Button"``,
#: ``"radio-button"`` and ``"RadioButton"`` all match. Synonyms across the UIA /
#: JAB / CDP / COM role vocabularies are folded together (e.g. ``hyperlink`` and
#: ``link``; ``edit``/``textbox``; ``cell``/``gridcell``/``dataitem``).
#:
#: This is an **allowlist**: anything not listed (static text, panes, groups,
#: separators, images, title/scroll/status bars, tooltips, custom-no-pattern) is
#: excluded. The same allowlist is applied **symmetrically to every adapter** —
#: that symmetry is the honesty invariant D1 crit #3 requires; an adapter-specific
#: allowlist would be cherry-picking. Bare static ``Text`` is deliberately absent
#: (editable fields surface as ``Edit``/``TextBox``/``Document``).
INTERACTIVE_ROLES: frozenset = frozenset({
    "button", "splitbutton", "togglebutton", "dropdownbutton", "menubutton",
    "edit", "textbox", "document", "passwordedit",
    "combobox", "dropdown",
    "checkbox", "radiobutton", "radio", "menuitemcheck", "menuitemradio",
    "hyperlink", "link",
    "menuitem", "menubaritem",
    "listitem", "treeitem",
    "tab", "tabitem",
    "cell", "gridcell", "dataitem", "tablecell",
    "slider",
    "spinner", "spinbutton",
    "calendar", "datepicker", "date",
    "hotkeyfield",
})


def normalize_role(role: Optional[str]) -> str:
    """Fold a raw role/control-type string to the allowlist's normalised form.

    Lower-cases and strips spaces, hyphens and underscores so the many spellings
    of the same role across backends (``"Radio Button"``, ``"radio-button"``,
    ``"RadioButton"``) all compare equal. ``None``/empty -> ``""``.
    """
    if not role:
        return ""
    return "".join(ch for ch in role.lower() if ch not in " -_")


def is_interactive_role(role: Optional[str]) -> bool:
    """Return ``True`` iff ``role`` is a meaningful interactive element.

    Pure, backend-agnostic, and applied identically to naturo and every rival —
    this single function *is* the symmetric filter (the honesty invariant).
    """
    return normalize_role(role) in INTERACTIVE_ROLES


def count_interactive(roles: Iterable[Optional[str]]) -> int:
    """Count how many of ``roles`` are meaningful interactive elements.

    Both the naturo adapter (walking cascade-node roles) and the pywinauto
    adapter (walking ``element_info.control_type`` over ``descendants()``) reduce
    their element list to a role sequence and call this one function, so the
    filter is provably identical on both sides.
    """
    return sum(1 for r in roles if is_interactive_role(r))

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
    #: Per-tool **meaningful-interactive** element count (the same symmetric
    #: allowlist applied to every adapter). Empty when a run predates the metric
    #: — then every accessor transparently falls back to the raw ``counts`` and
    #: behaviour is identical to before (backward compatible).
    interactive_counts: Dict[str, Optional[int]] = field(default_factory=dict)

    def _counts_for(self, metric: str) -> Dict[str, Optional[int]]:
        """Return the count map for ``metric`` (``"raw"`` | ``"interactive"``).

        Falls back to raw when interactive numbers were not measured, so callers
        never crash on an older result.
        """
        if metric == "interactive" and self.interactive_counts:
            return self.interactive_counts
        return self.counts

    def has_interactive(self) -> bool:
        """Whether this row carries measured interactive counts."""
        return bool(self.interactive_counts)

    @property
    def naturo_count(self) -> int:
        """naturo's raw recognized-element count (0 if it recognized nothing)."""
        return self.counts.get(NATURO) or 0

    def naturo_count_for(self, metric: str = "raw") -> int:
        """naturo's count under ``metric`` (0 if it recognized nothing)."""
        return self._counts_for(metric).get(NATURO) or 0

    def cell(self, tool: str, metric: str = "raw") -> str:
        """Classify one tool's result into a cell class (``pass``/``none``/``blocked``).

        ``metric`` selects raw vs interactive; it defaults to ``"raw"`` so every
        existing caller is unchanged.
        """
        count = self._counts_for(metric).get(tool)
        if count is None:
            return BLOCKED
        return PASS if count > 0 else NONE

    def beats(self, rival: str, metric: str = "raw") -> bool:
        """True when naturo recognizes elements the rival returns nothing on.

        The moat claim, measured per row: naturo ``pass`` while ``rival`` ran and
        recognized nothing (``count == 0``). A ``blocked`` rival does not count
        as beaten — we only claim superiority where the rival actually ran.
        ``metric`` defaults to raw; pass ``"interactive"`` for the actionable-
        element view that the published matrix now leads with.
        """
        cmap = self._counts_for(metric)
        return (cmap.get(NATURO) or 0) > 0 and cmap.get(rival) == 0


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
        # Classify on the interactive metric when it was measured (the honest,
        # actionable view), else on raw — so pre-metric rows behave exactly as
        # before. Both counts are carried so a reader can see what changed.
        metric = "interactive" if r.has_interactive() else "raw"
        cells = {
            t: {
                "cell": r.cell(t, metric),
                "count": r._counts_for(metric).get(t),
                "raw": r.counts.get(t),
                "interactive": r.interactive_counts.get(t) if r.has_interactive() else None,
            }
            for t in tools
        }
        beaten = [rv for rv in rivals if r.beats(rv, metric)]
        rows.append(
            {
                "app": r.app,
                "framework": r.framework,
                "metric": metric,
                "cells": cells,
                "beats": beaten,
            }
        )
        ran_rivals = [rv for rv in rivals if r.cell(rv, metric) != BLOCKED]
        naturo_saw = r.naturo_count_for(metric) > 0
        if naturo_saw and ran_rivals and all(r.beats(rv, metric) for rv in ran_rivals):
            if r.framework not in moat_frameworks:
                moat_frameworks.append(r.framework)
    return {"rivals": rivals, "rows": rows, "moat_frameworks": moat_frameworks}


def _cell_md(cell: str, count: Optional[int]) -> str:
    """Render one matrix cell to Markdown (single metric — legacy raw view)."""
    if cell == PASS:
        return f"✓ ({count})"
    if cell == NONE:
        return "✗ (0)"
    return "`blocked: needs env`"


def _cell_md_dual(cell: str, interactive: Optional[int], raw: Optional[int]) -> str:
    """Render a cell showing the interactive count (leading, drives ✓/✗) with the
    raw count alongside — honesty: the actionable number, plus what it came from.
    """
    if cell == BLOCKED:
        return "`blocked: needs env`"
    glyph = "✓" if cell == PASS else "✗"
    raw_str = "–" if raw is None else str(raw)
    return f"{glyph} ({interactive if interactive is not None else 0} · raw {raw_str})"


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
    # Dual-metric rendering kicks in only when interactive counts were measured;
    # otherwise the output is byte-identical to the legacy raw-only table.
    dual = any(r.has_interactive() for r in results)
    header = "| App | Framework | " + " | ".join(DISPLAY_NAMES.get(t, t) for t in tools) + " |"
    sep = "| --- | --- | " + " | ".join([":--:"] * len(tools)) + " |"
    lines = [header, sep]
    for r in results:
        metric = "interactive" if r.has_interactive() else "raw"
        if dual:
            cells = " | ".join(
                _cell_md_dual(
                    r.cell(t, metric),
                    r.interactive_counts.get(t) if r.has_interactive() else r.counts.get(t),
                    r.counts.get(t),
                )
                for t in tools
            )
        else:
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

    if dual:
        out += (
            "\n\n_Legend: ✓ (n · raw m) = recognized **n meaningful interactive** "
            "elements (targetable for an action/value-read) out of **m raw** nodes "
            "walked · ✗ (0) = ran but recognized no interactive element · "
            "`blocked: needs env` = tool not runnable on this host. The interactive "
            "count applies one symmetric role allowlist to every tool — a raw "
            "`descendants()` walk inflates on Chromium/Excel (static text, panes) "
            "without adding anything an agent can act on._"
        )
    else:
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
