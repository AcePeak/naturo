# Naturo Project Status
> Maintained by Orc-Mycelium. Agents: read on every startup.
>
> Last refreshed: 2026-07-13 (Orc, daily review #2 — **the Windows suite was lying; I got the truth out of it**).
>
> **THE FINDING: a P0 Never-Lie violation was hiding behind a green check for a week.** #1273's fix (merged 07-11) removed `pytest -x`, so the Windows suite ran end-to-end for the first time: **`63 failed, 6636 passed`** — where CI had been reporting *green* off **632 of 7030** tests (91% never executed). I landed **#1290** (`648aa99`), which fixed the single largest cause and took Windows **63 → 24**; I then attributed **all 24** remaining. **What the mask was hiding matters more than the count:**
> - **#1291 (P0, NEW)** — **`type_text`/`press_key` return `success:true` on an unresolvable `window_title` and the keystrokes land in whatever window is focused.** A wrong-window *write* — destructive, not merely incorrect, on the two most-used input tools. The self-maintaining guard built by #957 to make this bug class unshippable (`test_mcp_window_selector_contract_957`) **was already red and doing its job — CI was discarding its verdict.** Detection was never the problem; the reporting channel was.
> - **#1292 (P1, NEW)** — **the MCP surface has silently diverged from the CLI**: `app_hide`/`app_unhide`/`hotkey`/`list_snapshots`/`get_snapshot` exist in the codebase but are **not registered as MCP tools**. This is **Pillar B (agent fit)**, not tech debt — a capability naturo has on the CLI but not over MCP is one an agent *cannot use*. Guard #912 was saying so into a muted channel.
> - **#1293 (P1, NEW)** — MCP **error-contract** regression (validation failures surface as `INTERNAL_ERROR`, not `INVALID_INPUT` — an agent cannot self-correct from `INTERNAL_ERROR`) + `see_ui_tree` drops the `tree` key, breaking the `see`→`eN`→`click` round-trip, **the primary agent loop**.
>
> **#1290 detail (fix + method):** `tests/conftest.py`'s CI-Windows guard replaces two constructors — `_SkippingWindowsBackend` **subclasses** the real backend, but `_SkippingNaturoCore` was a **bare class**. `NaturoCore` has 34 class-level methods, so every test introspecting the class (signature checks, `mock.patch.object`, `MagicMock(spec=NaturoCore)`) hit a stub with none of them and raised `AttributeError` instead of skipping → **39 tests**. Subclassing the real core (mirroring the sibling that was already correct) cleared all 39; `__init__` still short-circuits before `self._load(...)`, so no DLL loads. **Verified on the real Windows job (63→24, zero stub errors), not locally — and deliberately NOT auto-merged, because the Windows job is still non-blocking and would have merged it green either way.**
>
> **#1274 is now unblocked and fully mapped (re-prioritized P1 → P0):** `#1291 (2) + #1292 (11) + #1293 (11) + #1175 (1 known flake) = 24`. Close those four → flip `continue-on-error` + add `build-python` to `ci-gate.needs` → this class of silent failure **cannot recur**. **RULE FOR DEV: do not delete a failing test to get green.** #1292/#1293 contain tests that are inconvenient *and correct*; discarding their signal is exactly how `develop` merged red for a week. Until #1274 lands, **every Windows "success" on `develop` still means nothing.**
>
> **The loop is STILL FROZEN, and the bottleneck is STILL not engineering.** `CronList` returns **"No scheduled jobs"** for the second consecutive cycle; before this session `develop` had **0 merges for ~68h** (last merge #1289 @ `2026-07-11T16:01:54Z`). It advanced today *only because a session was alive*. I again did **not** create a session-only cron — that reproduces the failure and gives false coverage. **Critical path runs entirely through Ace:** `needs:ace` is **8 items**, oldest 3–4 weeks — keystones **#1168** (persistent scheduler) and **#914** (v0.3.2 ship-gate, **19 days** stale). Evidence: `.work/reviews/2026-07-13-0415-daily-review.md`.
>
> _Carried from the 07-13 #1 entry (still true): **D1 is Ace-gated, not engineering-blocked.** The measured matrix was published from a real run 07-04 via PR #1264 (`e22e606`) and is honest — naturo **loses** on Electron (85 vs 113) and Excel COM (1177 vs 1307) while winning the real moat cell, Java/Swing **46 vs pywinauto 6**. D1 criteria #1/#2/#3/#4/#6 are **MET**; only #5 (README "beats X" positioning) is outstanding and is Ace-gated by design. Phase 2 is DISTRIBUTION and D2–D4 + D1#5 are **all** Ace-gated — so the loop fills its time with the only work it *can* do unsupervised (the U-series). Rational, but it does not move the stated milestone. Community flat (5★/6 forks, 0 external PRs). `agents/GOAL.md` remains top-level source of truth (M1–M4 done; **Phase 2 / D1 current**)._
>
> **The old finding (kept — it is the second-order lesson):** there is no scheduler at all. `CronList` this session returns **"No scheduled jobs"** — zero registered jobs. Consequently `develop` has had **0 merges / 0 open PRs / 0 feature branches for ~44h** (last merge PR #1289 @ `2026-07-11T16:01:54Z`; head `03ce4db`; CI green). This is **#1168 manifesting a second time**, now with direct evidence rather than inference: work advances *only* while an interactive Orch session is alive (it advanced 07-11 = 13 PRs, and it advances today — because a session is alive). **Liveness is the bottleneck; engineering is not.** I did **not** create another session-only cron — that reproduces the failure and gives false coverage. Escalated on #1168 with the evidence.
>
> **Correction to the 07-12 entry (it was wrong).** Last cycle I recorded D1 crit #2/#3 as *"unmet — `docs/COMPETITIVE.md` untouched, needs a NATUROBOT run"*. That contradicted its own carried facts and the repo: **the measured matrix was published from a real run on 2026-07-04 via PR #1264** (`e22e606`) and is honest — it shows naturo **losing** on Electron (85 vs 113) and Excel COM (1177 vs 1307) while winning the real moat cell, Java/Swing **46 vs pywinauto 6**. **D1's literal done-criteria #1/#2/#3/#4/#6 are therefore MET; only #5 (README "beats X" positioning) is outstanding, and it is Ace-gated by design.** D1 is *not* engineering-blocked — it is **awaiting an Ace decision**. Optional refinement (not a criterion): regenerate the matrix using the meaningful-interactive-element metric that landed in **#1271** — `docs/COMPETITIVE.md` still carries the pre-metric raw counts + an "until it exists" caveat; that refresh needs a real Windows desktop.
>
> **Strategic read — the loop substitutes autonomous engineering for the milestone it cannot advance.** The U-series (`agents/GOAL_UITREE_CONSISTENCY.md`, U1–U5) is genuinely good moat work and lands cleanly, but **Phase 2 is DISTRIBUTION (proof/visibility/adoption), and D2–D4 plus D1#5 are all Ace-gated** — so the loop fills its time with the only work it *can* do unsupervised. Rational, but it does not move the stated milestone. **The critical path now runs entirely through Ace:** the `needs:ace` pile is **8 items**, oldest 3–4 weeks — keystone **#1168** (scheduler), **#914** (v0.3.2 ship-gate, **18 days** stale), #1136/#1105/#1057 (unattended-API sign-offs + a community PR), #969/#935/#897. Community flat (5★/6 forks, 0 external PRs). `agents/GOAL.md` remains top-level source of truth (M1–M4 done; **Phase 2 / D1 current**). Phase-2 human gate unchanged (README/PyPI/"we beat X" auto-merge OFF; engineering PRs auto-merge on green). Hygiene this cycle: **#1273** (P0 CI silent-failure) → `status:done`, its fix **#1275** merged green `5bee2ba8` 07-11; posted a **positive-control** QA bar (a green Windows job is the *symptom*, not the cure — QA must prove the job can go red). Evidence: `.work/reviews/2026-07-13-daily-review.md`.
>
> _Prior entries (07-08→07-12: three HOLDING cycles, the #1272 false-"landed" correction, and the 07-11→12 13-PR U-series wave #1276–#1289) collapsed 2026-07-13 — full record in `git log -p agents/STATE.md` + `.work/reviews/`. Carried facts: the 07-11→12 wave delivered usable window handles + full-doc `get` + embedded-browser content, `office_dismiss_startup` + multi-window `see_ui_tree` parity, in-tree text content, per-call Excel COM caps, deep-JAB InternalFrame + `AccessibleText`, Terminal-buffer role+name disambiguation, Slider/Spinner `set` via RangeValuePattern, per-node readable/actionable/editable caps, window-matched snapshot/eN resolve, the Scintilla/Notepad++ moat provider, and caller-driven tree depth (#1289). #1272 (D3 framework tool-spec export) genuinely merged `1e4cc9d` after a CI-gating fix. #1269 wired the Java moat into `see_ui_tree`'s auto-JAB fallback; metric design in `docs/design/MEANINGFUL_INTERACTIVE_ELEMENT_METRIC.md`, implementation in #1271. **Recurring ops pattern: green engineering PRs sit unmerged for want of auto-merge arming (#1275, #1289) — arm `gh pr merge --auto` at PR creation.** Legacy `status:*` labels from the superseded issue-loop are residue; not mass-relabeling, to avoid noise._
>
> _Refresh history trimmed 2026-07-02 by Orc-Mycelium (collapsed the stacked 06-28’07-01 pause-era entries; prior trims 06-22/06-26/06-28). Only the current entry is kept inline — STATE.md is read by every agent on startup and had grown to 754 lines. Full record in git history (`git log -p agents/STATE.md`), `.work/reviews/`, and `naturo-loop-state.log`. NOTE: the structural body below predates the `/goal` pivot and is retained for reference only — `agents/GOAL.md` is the live source of truth._

> ⚠️ **SUPERSEDED BODY (retained for reference only).** Everything below predates the `/goal`-session
> pivot. The live process, milestones (M1–M4), and done-criteria are in **`agents/GOAL.md`** — read that
> first. The version-milestone/issue-loop described here is no longer the driver (see the Strategic Gap
> in the refresh entry above).

## Current Version
v0.3.1 (PyPI + GitHub Release). `develop` CI green. _(Note: dev now happens on `develop` via `/goal` PRs
#1214–#1220; no new PyPI release cut since — versioning of the M-series work is a pending Ace decision.)_

## Operating Mode — LOCAL multi-agent loop (2026-06-15) — ⚠️ SUPERSEDED by the `/goal` process
The project now runs as a machine-local 3-role loop on NATUROBOT (real Windows desktop),
defined in `agents/local/` (PR #908). This supersedes the old cloud-cron design for daily work.

| Role | Who | Worktree | Cadence |
|------|-----|----------|---------|
| **Orch** | live interactive session (Orc-Mycelium) | main checkout on `develop` | interactive |
| **Dev** | hourly background agent (Dev-Sirius) | `../naturo-dev` (dev-work) | cron :07 |
| **QA**  | hourly background agent (QA-Mariana) | `../naturo-qa` (qa-work) | cron :37 |

- Orch also runs a **PR-triage sweep at :22** (allow/merge team dev→develop PRs, bottom out
  stuck ones, review external PRs). Machine-local state log lives **outside the repo** at
  `C:\Users\Naturobot\naturo-loop-state.log`.
- Crons are **session-only** — they fire only while the Orch Claude session is alive, and
  auto-expire after 7 days. Persistent (survives-session-close) scheduling is an open Ace decision.
- Dev/QA here have a real desktop + working DLL + `gh` CLI → they run `@pytest.mark.desktop`
  tests and manage their own PRs/labels (no `pr-requests.md` handoff).

## Active Work — query live, do not trust hardcoded numbers
```bash
gh issue list --state open --limit 100 --json milestone,number,title,labels \
  --jq 'group_by(.milestone.title // "backlog") | sort_by(.[0].milestone.title // "z") |
  .[] | "\n### \(.[0].milestone.title // "Backlog")\n\(.[] | "- #\(.number) [\(.labels | map(.name) | join(","))] \(.title)")"'
```

## Milestone Summary (2026-06-16)
- **v0.3.2**: ~30 open / 98 closed. **Ship-gate requirement (1) now MET:**
  - (1) Epic **#885** (P0 silent-failure cluster) — **CLOSED + verified 2026-06-16** along with its
    members #868/#875/#878/#883/#893. Fix landed via PR #911 (`require_desktop_session` on all 11
    CLI+MCP surfaces + 23-case matrix `tests/test_no_desktop_guard_885.py`, building on community
    PR #892, contributor co-credited).
  - (2) Verify the 5 remaining `status:done` bugs from a real desktop: **#786, #788, #807, #840, #843**
    — **ALL VERIFIED+CLOSED 2026-06-17** (#786/#788/#807/#840 @01:15Z, #843 @02:42Z). **Requirement (2)
    MET.** Input-family closure was unblocked by QA's probe-first gate (input works on the no-RDP console;
    capability landed `19a72cd`), disproving #863's premise. **Both ship-gate requirements now satisfied —
    cutting/tagging v0.3.2 (#914) is Ace's call (Rule 2, human-only); QA does not sign off.**
- **QA LOOP RECOVERED (Orc 2026-06-16 18:24) — supersedes the "QA dead ~5 days" finding:** after the
  runner gained local-proxy auto-detection (commit `2ccbcf0`), QA `claude -p` rounds authenticate again
  and did real work today — **9 issues verified+closed 2026-06-16** (#885 cluster above + #902 + #870 +
  #906), with full verification cycles logged in `naturo-loop-state.log` at 16:43 and 17:42. **Still
  intermittent** (the 16:00 scheduled round 403'd — `agents/qa/logs/qa-20260616-1600.log:584`), so
  durability is unproven. **#915 reframed** from "TOP blocker / down 5 days" to *recovering — monitor*
  (commented; Ace to confirm durability, then close). The 403 no longer outranks everything.
- **Remaining verification blocker is now #863 (P0, `from:qa`), NOT #915:** QA **deferred #788** at
  17:42 because input commands (`type`/`click`/`press`) drive Win32 `SendInput`, which is blocked in
  the unattended agent session (#863) — a live type-after-restart test would be confounded. #788's unit
  tests pass (76/76); only true end-to-end runtime closure is gated. #807/#840 (input-family) are likely
  similarly gated; #786 (UWP menu click) is also input-gated. **#843 (capture popup): QA verified the
  composite path non-intrusively (18:50 — `capture --pid` on 2 same-PID windows produced one composited
  image; `test_capture_popup_843.py` 7/7), left `status:done` — final acceptance (a live #32768 menu
  opened via input) is deferred on #863, same pattern as #788.** Net: of the 5 remaining bugs, only
  capture-class is partially verifiable headless; all input-class closure is blocked by #863.
- **Detection gap #917 (Orc 2026-06-16, P1 `silent-failure`):** `runner.ps1` has no failure-streak
  watchdog — the earlier ~5-day 403 outage went undetected. Still open for Dev (code-only). Now also
  relevant for the *recovery* side: a watchdog would equally confirm QA is healthy again.
- **NEW ops item #935 (`needs:ace`, Orc/Dev 2026-06-16):** two Dev cycles ran **concurrently in the
  shared `naturo-dev` worktree** at ~18:07; the second cycle's Step 0 `reset --hard` wiped the first's
  in-flight uncommitted branch (#910 work) — a **Rule 4 violation at the orchestration layer**. Needs a
  per-worktree lock / serialized dev scheduling (runner.ps1/cron policy) — human-only ops decision.
- **v0.3.3**: 6 open / 1 closed. Enterprise features. Blocked on v0.3.2.
- **v0.3.4**: ~46 open / 8+ closed. Effectively a "contract stability" milestone (MCP/CLI envelope,
  param-name, exit-code drift from QA R135–R153). #890 (MCP list_snapshots) closed via PR #909.
  - **#912 (NEW, Orc 2026-06-16):** auto-enumerate CLI/MCP surfaces so a future command/tool can't
    silently bypass the desktop-session guard — converts #885's hand-maintained regression matrix
    (`tests/test_no_desktop_guard_885.py`) into a self-maintaining coverage contract. Test-only, P2.
  - **#979 (Orc, P1) — LANDED 2026-06-18 (`a8402af`, PR #986), now `status:done` awaiting QA.** Layer 1 of
    the self-maintaining `-j` envelope contract: `@collection_read` decorator + `success_envelope()` helper +
    a Click-tree-walking test that fails CI if any collection read drops `{success,<collection>,count}`. Kills
    the list/show drift class (#876→#977→#980) structurally.
  - **#987 (NEW, Orc 2026-06-18, P1):** **layer 2 — global `-j` stdout-purity contract.** #979 covers
    collection reads only; #987 asserts every command + eager option (`--version`/`--help`) under `-j` emits
    exactly one JSON doc with zero extra stdout bytes — catches the stray-text/eager-option sub-class
    (#874/#869/#872) that the collection-read walk misses. Test-only, Dev-actionable, pickable.
  Blocked on v0.3.2.
- **Backlog**: ~10 open (Linux platform + migrated community/docs tasks). **#777 (Unicode capture)
  fixed via PR #941** (Python bridge-level ASCII staging — ships independent of the stale DLL #842);
  **VERIFIED+CLOSED by QA 2026-06-16 21:40** (screenshot-backed: Unicode-path Calculator capture is
  content-identical to the ASCII control; full-screen DXGI returns black over disconnected RDP —
  environmental, affects both paths equally, doesn't change the verdict).

## Open community PRs (external contributor @botbikamordehai2-sketch)
- **#892** (closes #885): correct decorator, never applied, base=`main`. Team carrying forward.
- **#904** (closes #844): right direction, breaks `errors.py` (mis-spliced helper), no wiring,
  unrelated workflow churn, base=develop. Team carrying forward.
- Both: warm "we'll complete + co-credit you" notes posted 2026-06-15; close when the team PR lands.
- **RESOLVED 2026-06-16:** disposition issue **#913 closed** — both community PRs now **CLOSED**
  (#892 superseded by merged PR #911 with co-credit; #904 superseded for #844 carry-forward). No longer
  in the needs:ace queue.

## Coordination
- Bug tracking: GitHub Issues only. State flow: `status:in-progress` → `status:done` → `verified` → close.
- One issue = one commit = one PR. English-only on GitHub. CI red → stop all new dev work.
- Never push directly to `main`/`develop` (only release tags → `main`); Orch may push
  operational files (STATE.md, queue) to develop with `[skip ci]`.
- **Human-decision items (Ace only):** **#935 serialize dev cycles / per-worktree lock (NEW)**;
  **#915 confirm QA auth durable then close** (recovering, no longer TOP); self-hosted runner #842
  (offline) / cloud-VM #860; persistent cron scheduling; ship-gate timing (#914 — req (1) #885 now
  met); public-API changes.
  _(Community-PR disposition #913 resolved/closed 2026-06-16 — both #892/#904 closed.)_
- **STANDING #1 PRODUCT PRIORITY — recognition supremacy (proofs QA-verified 2026-06-16 20:25):**
  - **#931 VERIFIED+CLOSED** (11:40Z) — coverage benchmark (PR #936). Reproducible cascade-vs-UIA-only
    harness + `docs/RECOGNITION.md` with measured numbers; README "Why naturo?" headline leads with the
    multi-framework pitch and links the proof. **QA-confirmed**, no longer awaiting QA.
  - **#933 VERIFIED+CLOSED** (11:41Z) — owned real-Electron fixture + CDP recognition proof (PR #938).
    **Measured (Win11): UIA-only 83 vs cascade 113 (+30, all via CDP)** — the literal Electron case, not
    a Chrome proxy. **QA-confirmed.** (Chrome row also published: 52→89, +37.)
  - **Net:** the headline recognition claim now has **two QA-verified framework proofs** backing it.
  - **Still open, at queue top:** epic **#920** (P0 moat); **#932** (Java Swing/SWT JAB fixture+proof,
    P1) — JAB is *implemented* (`core/src/jab.cpp`, `naturo/cascade/`) and marked ✅ in the matrix but
    **not yet benchmark-measured** (no Java app on the desktop); **#934** (SAP GUI, P2, honestly marked
    🚧 planned in the matrix); **#937** (QA validate the benchmark on mature external apps, P1).
  - **Next move:** #932 (Java) is the last major framework lacking an owned-fixture proof — pull it
    forward. Distribution (#922 MCP registries/.mcpb, #927 one-line install snippets) feeds the proof
    outward once the matrix is complete. RECOGNITION.md is honest (gaps documented "no fabrication").

## Code Health
- Large files still open for split: `_element.py` (#720), `browser_cmd.py` (#856),
  `macos.py` (#862), `_input.py` (#861).
- Version consistent at 0.3.1 across pyproject/version.py/PyPI.

## Completed Releases
- v0.1.0 core · v0.1.1 (67 fixes) · v0.2.0 (Unified App Model + DPI) · v0.2.1 (auto-routing + get)
- v0.3.0 (QA-tested) · v0.3.1 (hotfix: CMakeLists + version.cpp sync)
