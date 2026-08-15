# Design Spec — "Meaningful Interactive Element" benchmark metric

**Status:** logic+test LANDED (2026-07-07) — real-desktop data regen (crit #4/#5) PENDING a Windows run
**Owner:** Orc-Mycelium · **Milestone:** D1 (competitive matrix) · **Date:** 2026-07-05

> **Progress (2026-07-07, Orc):** Acceptance criteria **#1–#3 are implemented, verified and merged**
> (`matrix.py` symmetric `is_interactive_role`/`count_interactive` filter + `interactive_counts` on
> `CompetitiveResult` + both adapters wired + dual-metric matrix rendering + pinning tests, all
> ruff/pytest green and independently verified for anti-cherry-pick symmetry — the filter is one shared
> function both adapters pass their role list through). The machinery is Linux-collectable and ready.
> **Still pending (needs the NATUROBOT Windows desktop, cannot be produced off-Windows honestly):**
> crit **#4** — run `run_competitive --markdown` to regenerate `docs/COMPETITIVE.md`'s measured table with
> the Interactive column and resolve/annotate the ⚠️ reconcile note from the *measured* interactive
> numbers; crit **#5** — fresh-context desktop QA re-runs the harness to confirm the numbers are generated,
> not hand-authored. `docs/COMPETITIVE.md` is intentionally **untouched** until that real run exists.

This is a **decision-ready** slice: the design below is settled so a `/goal` round can go
straight to TDD build → independent verify → land, with no re-deliberation. It is **non-Ace-gated**
(it changes benchmark measurement + `docs/COMPETITIVE.md` *data*, not the README public claim).

## Problem — the published matrix contradicts its own measured run
`docs/COMPETITIVE.md` marks **Electron/CDP** and **Excel COM** as rival-`✗` in the capability table,
but the *measured* run shows a UIA-only rival (pywinauto) recognizing **more** raw nodes than naturo:

| App | Framework | naturo (raw) | pywinauto (raw) | pyautogui |
|-----|-----------|-------------|-----------------|-----------|
| Chromium | Electron/CDP | 85 | **113** | 0 |
| ExcelCom | Excel COM | 1177 | **1307** | 0 |

The cause is a **non-comparable metric**, not a real rival win:
- `NaturoAdapter.count_elements` → `result.stats.total_elements` (cascade-*recognized* elements).
- `PywinautoAdapter.count_elements` → `len(window.descendants())` — **every** UIA descendant,
  including static text, panes, separators, images, group headers.

Chrome and Excel dump their entire accessibility subtree into UIA, so a raw `descendants()` walk
inflates. The count says nothing about how many elements a tool can **act on**. The genuine,
uncontested moat is **Java (JAB) / SAP / deep-Electron**, where a UIA-only walk returns ~nothing —
that must survive any metric change.

## Definition — "meaningful interactive element"
A node counts iff its role/control-type is one an automation agent can **target for an action or a
value read**. Everything else (static/decorative/layout) is excluded. The filter is applied
**symmetrically to every adapter** — this is the honesty invariant; an asymmetric filter is
cherry-picking and fails D1 crit #3.

**Interactive role allowlist (UIA ControlType, map equivalents for JAB/CDP/COM):**
`Button, Edit, ComboBox, CheckBox, RadioButton, Hyperlink, MenuItem, ListItem, TreeItem,
TabItem, DataItem/Cell, Slider, Spinner, SplitButton, Text-that-is-editable, Document(editable),
ToggleButton, Calendar/date, Table cell`.

**Excluded:** `Text (static), Pane, Group, Separator, Image, TitleBar, ScrollBar thumb-only,
Custom-with-no-pattern, ToolTip, StatusBar (unless it exposes an invoke/value pattern)`.

Refinement (optional, stronger): keep only nodes exposing an actionable **UIA pattern**
(`Invoke, Toggle, Value(editable), SelectionItem, ExpandCollapse, RangeValue`). Pattern-presence is
a more robust "actionable" test than role name and is available on `pywinauto`'s wrapper and on
naturo's cascade node metadata. Prefer pattern-presence where both backends expose it; fall back to
the role allowlist otherwise.

## Where to change (grounded in the existing harness)
- `benchmarks/competitive/harness.py`
  - Add `count_interactive_elements(...)` to `Adapter` (or a `mode="interactive"` param on
    `count_elements`). Keep the **raw** count too — report **both** columns; do not delete the raw
    number (honesty: show what changed).
  - `NaturoAdapter`: filter cascade nodes by their recognized role/pattern metadata.
  - `PywinautoAdapter`: replace bare `len(window.descendants())` with a filtered walk —
    `descendants()` then keep wrappers whose `element_info.control_type` ∈ allowlist (or whose
    pattern set is actionable). This is the crux fix.
  - `PyAutoGUIAdapter`: stays honest **0** (no element model).
- `benchmarks/competitive/matrix.py`: render an **Interactive** column alongside **Raw**; the moat
  cell logic (`✗ (0)` = ran-but-saw-nothing) is unchanged — Java/SAP/deep-Electron still read `✗`
  for rivals because their *interactive* count there is genuinely 0.
- `benchmarks/competitive/run_competitive.py`: emit both metrics.

## Expected outcome (hypothesis, to be confirmed by the real run — NOT pre-written)
- **Java (JAB) / SAP / deep-Electron:** unchanged — rivals stay `✗ (0)`; the moat holds.
- **Chromium/Excel:** the interactive gap should narrow or invert the *misleading* raw lead. The run
  may show naturo ≈ rival on interactive count → then the honest matrix cell becomes `~` (parity),
  which **resolves the COMPETITIVE.md contradiction on the merits** and removes it from Ace's
  positioning decision. If the real run instead shows the rival still ahead on interactive count,
  **report that honestly** — do not massage the metric to win. D1 crit #3 forbids cherry-picking.

## Acceptance criteria
1. Symmetric interactive-element filter implemented for all adapters; raw count retained alongside.
2. `matrix.py` renders both Raw and Interactive; moat cells (`✗ (0)`) unchanged for Java/SAP/deep-CEF.
3. `tests/test_competitive_benchmark.py` extended: pins the filter (a fixture node set → expected
   interactive count), asserts the allowlist is applied identically across adapters, and asserts the
   moat-cell logic still fires. `pytest` exits 0; Linux-collectable (matrix.py imports no rival/naturo).
4. Real Windows run regenerates the `docs/COMPETITIVE.md` measured table from harness output (both
   columns). The reconcile ⚠️ note is either **removed** (if interactive parity resolves it) or
   **updated with the measured interactive numbers** — never left contradicting itself.
5. Independent fresh-context QA re-runs the harness and confirms the numbers are generated, not
   hand-authored (D1's standing verify rule).

## Verify plan (per GOAL.md step 3)
Fresh-context sub-agent that did not write the code: re-runs `run_competitive --markdown` on the
real fixtures, diffs its output against `docs/COMPETITIVE.md`, tries the asymmetric-filter attack
(does one adapter get a laxer allowlist?), and confirms the Java/SAP/deep-Electron `✗` cells are
untouched. FAIL → fix ≤2× → else revert. Never land on a failed verification.

## Why this is the right next non-gated slice
It is the one D1 action that (a) needs **no Ace decision**, (b) directly discharges D1 crit #3
(honest, not cherry-picked) by fixing a real measurement flaw, and (c) may **shrink the Ace gate**
itself — if interactive parity is real, the Electron/Excel `✗→~` reframe becomes a measured fact
rather than a positioning judgment call.
