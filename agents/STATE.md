# Naturo Project Status
> Maintained by Orc-Mycelium. Agents: read on every startup.
> Last refreshed: 2026-06-22 05:22Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; #1156
> (electron-decode/hermeticity, via PR #1158) now QA-verified+closed; NO open team PR; one Dev cycle in-flight
> (#1100 test_verify hermeticity); NO new human-only item; Step 3.6 honest no-change; queue unchanged at 12.**)
> **`develop` GREEN** — merge commit `959411d` (#1158, *fixes #1156*) **CodeQL + Build & Test both SUCCESS**
> @20:53Z; HEAD `7138f8d` = prior orc `[skip ci]` (no run) → no STOP → new work permitted. **Step 1 PR sweep:**
> NO open team-Dev PR — #1158 (`fix/issue-1156-electron-decode-hermeticity`→`develop`, *fixes #1156*)
> **auto-merged itself** (`959411d`); branch auto-deleted (Rule 14 clean — remote = `develop`+`main` only).
> Only open PR = community **#1055** (@muhamedfazalps, base `main`, fork, MERGEABLE/UNSTABLE) → already queued
> needs:ace **#1057**, human-only → untouched. Nothing merged/closed BY Orc (Rule 1). **Step 2 health:** **no
> handoff owed** — #1156 already flipped `status:done` by Dev on merge, then **QA verified+closed it @05:08Z**
> (verified label + evidence comment citing `959411d` per Rule 1; live `_bulk_get_process_info` ran 669
> processes with no crash + forced-`stdout=None` mock; 6 repro + 11 decode tests deterministic). `status:done`
> open = **#972** only (P0 input-safety, human-only sign-off, already needs:ace) → untouched. `status:in-progress`
> = **#1100** (P2 from:dev, test_verify.py NonWindows hermeticity — same #1100/#1133 family; Dev active @05:07Z,
> updated ~12 min pre-cycle → not abandoned) + **#766** (Ace migration-guide umbrella, assignee AcePeak/`from:ace`)
> → both legitimate, nothing for Orc to close (Rule 1). **Step 3 (moat, Standing #1):** native-core moat
> (#920/#932/JAB #1096) build-blocked (MSVC/cmake absent) → needs:ace #1097; OCR (#1060) blocked on #1077; #931
> benchmark CLOSED+verified, README leads with the moat headline. Backlog sharp & self-feeding (Dev on #1100
> hermeticity family; #1152/#1146/#1142/#1121/#897 feed Dev) → no new gap (Rule 9, no churn). **Step 3.5
> competitiveness: NOT due** (last row 06-16, today 06-22 = 6d < 7) → skipped (due 06-23). **Step 3.6 (evolve the
> team): no change — no new evidence.** The one completed cycle since 04:52Z — **QA @05:08Z verified+closed #1156**
> — was exemplary (runtime check the offline runner can't do; cited merged commit; zero intrusive input; left #972
> queued; traced a one-off pytest tmp-dir PermissionError to a harness artifact and filed nothing false, applying
> the 20:22Z QA-harness rule). The current Dev cycle (#1100, @05:07Z) is still in-flight → not yet assessable.
> Freshest rule (dev-cycle.md HEAD-check) landed <1d ago, only clean exercises → over-fit forbidden. Honest
> no-change row appended to EVOLUTION.md. **Step 4 (needs:ace): no new item;** queue unchanged at 12
> #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897; NEEDS-ACE.md refreshed. Evidence in
> `.work/reviews/2026-06-22-0522-auto-review.md`. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call,
> #914). Detail below is prior cycles' record, kept as history.)
>
> Last refreshed (prior): 2026-06-22 04:52Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; one NEW team-Dev
> PR #1158 (fixes #1156 electron-decode/hermeticity) MERGEABLE + auto-merge ON, landing itself; NO new
> human-only item; Step 3.6 honest no-change; queue unchanged at 12.**) **`develop` GREEN** — last real-CI
> `5226d9f` (#1157, *fixes #1150*) Build & Test + CodeQL both SUCCESS @19:53Z; HEAD `7e36ce8` = prior orc
> `[skip ci]` (no run) → no STOP → new work permitted. **Step 1 PR sweep:** one NEW team-Dev PR **#1158**
> (`fix/issue-1156-electron-decode-hermeticity`→`develop`, *fixes #1156* — harden `_bulk_get_process_info`
> electron decode vs non-UTF-8 stdout + make `test_app_ids`/`test_electron` hermetic) is **MERGEABLE +
> auto-merge SQUASH ON** (enabled by AcePeak 20:49Z); `BLOCKED` only because macOS 3.9/3.13 + Analyze c-cpp
> still running — every completed check SUCCESS (Ubuntu/macOS 3.9–3.13, Windows+DLL, Lint, Build C++, Version,
> Author) → **left to land on its own** (never merge outside its own auto-merge, Rule 1). Community **#1055**
> (base `main`, fork, MERGEABLE/UNSTABLE) → already queued needs:ace **#1057**, human-only → untouched.
> Nothing merged/closed BY Orc (Rule 1). **Step 2 health:** **no handoff owed** — no team PR MERGED this
> cycle (#1158 still in CI; its `status:done` flip is Dev's on-merge job). `status:done` open = **#972** only
> (P0 input-safety, human-only sign-off, already needs:ace) → untouched. `status:in-progress` = **#1156**
> (active — PR #1158 in CI) + **#766** (Ace migration-guide umbrella, `from:ace`/assignee AcePeak) → both
> legitimate, nothing abandoned, nothing for Orc to close (Rule 1). **Step 3 (moat, Standing #1):** native-core
> moat (#920/#932/JAB #1096) build-blocked (MSVC/cmake absent) → needs:ace #1097; OCR (#1060) blocked on #1077;
> #931 benchmark CLOSED+verified, README leads with the moat headline; #1150 (P1 mojibake) fixed+QA-closed last
> cycle. Backlog sharp & self-feeding (#1156 in PR, #1152/#1146/#1142/#1121/#897 feed Dev) → no new gap (Rule 9,
> no churn). **Step 3.5 competitiveness: NOT due** (last row 06-16, today 06-22 = 6d < 7) → skipped (due 06-23).
> **Step 3.6 (evolve the team): no change — no new evidence.** Both completed cycles since 04:22Z were
> exemplary: **Dev @04:37Z** shipped PR #1158 (hardest-first, real #1156 fix at the right layer) and **QA
> @04:40Z** ran a clean read-only exploratory sweep with **zero intrusive input** (capture ground-truth +
> arg-validation matrix; filed nothing false; left #972 queued). Freshest rule (dev-cycle.md HEAD-check) landed
> <1d ago, only clean exercises → over-fit forbidden. Honest no-change row appended to EVOLUTION.md. **Step 4
> (needs:ace): no new item;** queue unchanged at 12 #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/
> #914/#897; NEEDS-ACE.md refreshed. Evidence in `.work/reviews/2026-06-22-0452-auto-review.md`. v0.3.2
> ship-gate unchanged (FULLY MET — release is Ace's call, #914). Detail below is prior cycles' record, kept as
> history.)
>
> Last refreshed (prior): 2026-06-22 04:22Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; #1150 (CJK mojibake)
> fix MERGED via PR #1157 (`5226d9f`) AND QA-verified+closed; NO open team PR; NO new human-only item; Step 3.6
> honest no-change; queue unchanged at 12.**) **`develop` GREEN** — last real-CI `5226d9f` (#1157, *fixes #1150*)
> **Build & Test + CodeQL both SUCCESS** @19:53Z; HEAD `dffe62a` = prior orc `[skip ci]` (no run) → no STOP → new
> work permitted. **Step 1 PR sweep:** NO open team-Dev PR — #1157 (`fix/issue-1150-ansi-codepage-mojibake`→
> `develop`) **MERGED via its own auto-merge** (squash, `5226d9f`); branch auto-deleted (Rule 14 clean). Only open
> PR = community **#1055** (base `main`, fork, MERGEABLE/UNSTABLE) → already queued needs:ace **#1057**, human-only
> → untouched. Nothing merged/closed BY Orc (Rule 1). **Step 2 health:** **no handoff owed** — #1157 merged AND
> #1150 already flipped `status:done` by Dev on merge, then **QA verified+closed #1150** this window (independent
> Win32 `GetWindowTextW` ground truth, 41/41 non-ASCII titles match, 0 U+FFFD; cited `5226d9f` per Rule 1).
> `status:done` open = **#972** only (P0 input-safety, human-only sign-off, already needs:ace) → untouched.
> `status:in-progress` = **#766** only (Ace migration-guide umbrella, `from:ace`/assignee AcePeak) → Ace-owned, not
> abandoned, left as-is. Nothing for Orc to close (Rule 1). **Step 3 (moat, Standing #1):** P1 **#1150** mojibake
> now **fixed at the right Python read-path layer + QA-closed**; native-core moat (#920/#932/JAB #1096) remains
> build-blocked (MSVC/cmake absent) → needs:ace #1097; OCR (#1060) blocked on #1077; #931 benchmark CLOSED+verified,
> README leads with the moat headline. Backlog sharp & self-feeding (#1156/#1152/#1146/#1142/#1121/#897 feed Dev) →
> no new gap (Rule 9, no churn). **Step 3.5 competitiveness: NOT due** (last row 06-16, today 06-22 = 6d < 7) →
> skipped (due 06-23). **Step 3.6 (evolve the team): no change — no new evidence.** The one cycle completed since
> 03:52Z — **QA verified+closed #1150** — was exemplary (independent `GetWindowTextW` ground truth, no duplicate,
> cited merged commit, #972 left queued, zero intrusive input); the Dev #1157 ship was already assessed (03:52Z);
> a Dev cycle @04:07 errored on a `naturo-loop-state.log` file-lock = harness-infra transient already tracked by
> #935/#1156, NOT a Dev weakness. Freshest rule (dev-cycle.md HEAD-check) landed <1d ago, only clean exercises →
> over-fit forbidden. Honest no-change row appended to EVOLUTION.md. **Step 4 (needs:ace): no new item;** queue
> unchanged at 12 #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897; NEEDS-ACE.md refreshed.
> Evidence in `.work/reviews/2026-06-22-0422-auto-review.md`. v0.3.2 ship-gate unchanged (FULLY MET — release is
> Ace's call, #914). Detail below is prior cycles' record, kept as history.)
>
> ---
> _Older refresh history (cascade of ~64 cycles, 2026-06-16 → 2026-06-21 17:52Z) trimmed 2026-06-22 by Orc-Mycelium to cut STATE.md back from ~461KB / 4569 lines (it is read by every agent on startup). The full record is retained in git history (`git log -p agents/STATE.md`), `.work/reviews/`, and `naturo-loop-state.log`. The structural reference body follows._

## Current Version
v0.3.1 (PyPI + GitHub Release). `develop` CI green.

## Operating Mode — LOCAL multi-agent loop (NEW, 2026-06-15)
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
