# Naturo Project Status
> Maintained by Orc-Mycelium. Agents: read on every startup.
>
> Last refreshed: 2026-07-07 (Orc, 15:11 anti-stall cycle) — **D1 stayed fully human/infra-gated (unchanged), so Orc broke the stall by pulling the D3 slice forward: BUILT + independently-verified + landed PR #1272** — `naturo.agent_tools` re-emits naturo's **full MCP tool surface (62 tools)** as OpenAI *and* Anthropic function-calling specs (`to_openai_tools()` / `to_anthropic_tools()`), derived from the live MCP registry so they never drift, **no Windows desktop needed** (schemas are static → Linux/CI-collectable). Ships `tests/test_agent_tools.py` (8 green), `examples/agent_frameworks.py` (copy-paste OpenAI/Anthropic/LangChain wiring + CLI dispatcher), and an "any framework" section in `docs/AGENT_INTEGRATION.md`. This advances **pillar B (AI-agent fit)** — "3 lines to give your agent Windows control" now works for *any* framework, not only MCP clients — with **zero Ace/NATUROBOT dependency**. A **fresh-context sub-agent** verified registry parity (62==62, no drift), JSON-safe specs, no desktop side effects, and that the LangChain closure binds per-tool (no late-binding bug); ruff+pytest green. PR #1272 → develop, **auto-merge armed** (engineering, not a public claim), BLOCKED-on-CI = normal. **D1 is UNCHANGED — still down to TWO gates, BOTH outside Orc/macOS reach — no engineering left to do without fabricating:** *(metric slice #1271 landed 07-06 16:17Z, code side complete+verified; pillow dependabot #1270 merged 07-07 04:02Z.)* **(a) crit #2/#3** — regenerate `docs/COMPETITIVE.md`'s measured table from a **real NATUROBOT Windows run** (now with the Interactive column) + desktop QA re-run. The GH self-hosted `desktop-tests.yml` runner has been **idle/cancelled since 2026-04-12**; the 07-04 measured matrix came from the *local NATUROBOT agent loop*, which has been **quiet since 07-04 (#1269)**. Orc **cannot trigger** it and **will not fabricate** numbers on macOS — `docs/COMPETITIVE.md` intentionally **untouched**. **(b) crit #5** — README positioning (narrow public claim to Java/SAP/deep-CEF; Electron/Excel `✗`→`~`), **Ace-gated, already escalated, NOT re-escalating.** The metric may resolve Electron/Excel *on the merits* once (a) runs and confirms interactive parity — potentially shrinking the (b) gate. **Anti-stall watch:** D3 is now the active non-gated lane while D1 waits — slice 1 (framework tool-spec export, #1272) is done; **next D3 increments** (still CI-gatable, no Ace/NATUROBOT): a runnable end-to-end example proving an agent completes a task via the exported specs (mocked LLM, Linux-green), a LangGraph/OpenAI-Agents-SDK adapter example, and a `naturo mcp tools --format openai|anthropic` CLI so the specs are shippable without importing the package. develop CI **GREEN**; community flat **5★/6 forks**, no external PRs. **`agents/GOAL.md` is the single source of truth** (M1–M4 done; D1 current). **Phase-2 human gate:** README/PyPI/"we beat X" claims open auto-merge OFF for Ace; engineering PRs still auto-merge on green. **Legacy trackers dormant** (GitHub issue/milestone + Dev-Sirius github-queue, idle since 04-05 — NOT driving work). Evidence: `.work/reviews/2026-07-07-1?-daily-review.md`. — _Prior entries (07-04/07-05) collapsed 07-07; full record in `git log -p agents/STATE.md` + `.work/reviews/`. Key carried facts: real 07-04 matrix (PR #1264) showed Java/Swing **46 vs pywinauto 6** = the demonstrable raw-count moat (UIA is Swing-blind), while Electron/Chromium (85 vs 113) + Excel COM (1177 vs 1307) are **NOT** raw-count wins — which is exactly why the interactive metric (#1271) matters; #1269 wired the Java moat into the default agent path (`see_ui_tree` auto-JAB fallback); the metric design is settled in `docs/design/MEANINGFUL_INTERACTIVE_ELEMENT_METRIC.md`._
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
