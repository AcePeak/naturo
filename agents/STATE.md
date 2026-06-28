# Naturo Project Status
> Maintained by Orc-Mycelium. Agents: read on every startup.
> Last refreshed: 2026-06-28 ~04:01Z (Orc daily review — **NO-CHANGE, ~6.3d frozen. Nothing merged/closed since #1166
> (06-22 01:55Z). develop GREEN real-CI `3fb7b5d` (orc [skip ci] commits sit on top, no new CI). PR queue empty + no
> orphans (remote = main+develop+1 dependabot, Rule 14 clean). 2 open PRs both main-base human-only (Rule 2): #1167
> dependabot checkout-7 (Build&Test 'failure' = Feishu-notify step only) / #1055 community fork→#1057. status:in-
> progress=#766 (Ace, 06-21); status:done #1162/#1164/#972 STILL unverified ~6d (QA loop down). needs:ace=13, stars=5
> flat, no external activity. Milestones: v0.3.2=17/v0.3.3=12/v0.3.4=31/v0.4.0=1/v0.5.0=4. #1168 (persistent-scheduler,
> P1 needs:ace, my own 06-27 04:03Z) STILL 0 comments ~24h — THE meta-blocker; every needs:ace item is downstream of
> it. #914/#915 escalations 06-25 (~3d UNANSWERED → Rule 9, did NOT re-post). No new issues (version 0.3.1, Phase 3.5
> N/A). Loop has nothing self-serviceable; the freeze is entirely an Ace-decision bottleneck (#1168 first). Evidence:
> `.work/reviews/2026-06-28-0401-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-27 ~16:02Z (Orc daily review, 3rd pass today — **NO-CHANGE confirmation; nothing moved on the
> wire in the ~9h since 07:02Z. Still nothing merged/closed since #1166 (06-22 01:55Z, now ~6.2d). develop GREEN real-CI
> `3fb7b5d`. PR queue empty + no orphans (remote = main+develop+1 dependabot, Rule 14 clean). 2 open PRs both main-base
> human-only (Rule 2): #1167 dependabot checkout-7 (Build&Test 'failure' = Feishu-notify step only) / #1055 community
> fork→#1057. status:in-progress=#766 (Ace, 06-21); status:done #1162/#1164/#972 STILL unverified ~6d (QA loop down).
> needs:ace=13, stars=5 flat, no external activity. Milestones: v0.3.2=17/v0.3.3=12/v0.3.4=31/v0.4.0=1/v0.5.0=4/backlog=21.
> #1168 (persistent-scheduler, P1 needs:ace, my own 06-27 04:03Z) STILL 0 comments ~1.3d — THE meta-blocker. #914/#915
> last comments = MY OWN [Orc] escalations 06-25 (~3d UNANSWERED → Rule 9, did NOT re-post). No new issues (version
> still 0.3.1, Phase 3.5 N/A). Loop cannot self-heal the recurring multi-day freeze; fix is entirely in #1168. Evidence:
> `.work/reviews/2026-06-27-1602-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-27 ~07:02Z (Orc daily review, 2nd pass today — **NO-CHANGE confirmation; nothing moved on the
> wire in the ~2h since 05:00Z. Still nothing merged/closed since #1166 (06-22 01:55Z, now ~5.2d). develop GREEN real-CI
> `3fb7b5d`. PR queue empty + no orphans (remote = main+develop+1 dependabot, Rule 14 clean). 2 open PRs both main-base
> human-only (Rule 2): #1167 dependabot checkout-7 / #1055 community fork→#1057. status:in-progress=#766 (Ace);
> status:done #1162/#1164/#972 still unverified (QA loop down). needs:ace=13, stars=5 flat, no external activity. #1168
> (persistent-scheduler, needs:ace P1) filed 04:03Z is newest activity (my own) — it IS the meta-blocker; every other
> needs:ace item is downstream. #914/#915 last comments = MY OWN 06-25 [Orc] escalations (UNANSWERED, ~2d → Rule 9, did
> NOT re-post). No new issues (version still 0.3.1, Phase 3.5 N/A). Evidence: `.work/reviews/2026-06-27-0702-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-27 ~05:00Z (Orc daily review — **NO-CHANGE on the wire (nothing merged/closed since #1166,
> 06-22 01:55Z, now ~5.1d); develop GREEN real-CI `3fb7b5d` (Build & Test + CodeQL SUCCESS, last 06-22); PR queue empty
> + no orphans (remote = main+develop+1 dependabot, Rule 14 clean); 2 open PRs both main-base human-only (Rule 2) #1167
> dependabot checkout-7 / #1055 community fork→#1057; status:in-progress=#766 (Ace); status:done #1162/#1164/#972
> unverified since 06-22 (QA round never fired). No external activity (5 stars flat, no new external issues). #914/#915
> last comments = MY OWN 06-25 [Orc] escalations via shared bot acct (still UNANSWERED, ~2d old → Rule 9, did NOT
> re-post). NEW ACTION: filed **#1168 (needs:ace, P1)** — surfaced the persistent-scheduler decision (Dev/QA crons are
> session-only → loop freezes whenever no Orch session is alive; this, NOT a 403, is the root cause of the recurring
> ~5d freezes and the #1162/#1164/#972 verify-stall). It was buried in STATE prose only; now trackable. It is the
> META-blocker — every other needs:ace item is downstream (a durable scheduler clears the QA backlog autonomously). 3
> options: A=Windows Task Scheduler [rec] / B=cloud VM (#860) / C=status quo; pair with watchdog #917 + worktree-lock
> #935. needs:ace pile now 13 (was 12). HYGIENE FINDING: milestone **v0.2.0 is still OPEN with 0 open issues** — the
> playbook's `sort|first` milestone picker would misfile new issues into it; used v0.3.2 explicitly. Suggest Ace close
> v0.2.0. No code/quality issues to file (version still 0.3.1, Phase 3.5 N/A). Evidence:
> `.work/reviews/2026-06-27-0500-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-26 ~16:02Z (Orc daily review, 3rd pass today — **NO-CHANGE confirmation; nothing moved on the
> wire in the ~9h since 07:04Z. Still nothing merged/closed since #1166 (06-22 01:55Z, now ~4.6d). develop GREEN
> real-CI `3fb7b5d` (Build & Test + CodeQL SUCCESS). PR queue empty + no orphans (remote = main+develop+1 dependabot,
> Rule 14 clean). 2 open PRs both main-targeted human-only (Rule 2): #1167 dependabot checkout 6→7 (real checks pass,
> only Feishu-notify reads 'failure') + #1055 community fork → needs:ace #1057. status:in-progress=#766 (Ace, 06-21);
> status:done=#1162/#1164/#972 unverified (QA's job). needs:ace pile = 12 (unchanged): #914 ship-gate, #915 403-close-
> rec, #1077 OCR, #1097 native-core build, #1105/#1136 unattended-API sign-offs, +6. Decision backlog IS the bottleneck;
> loop has nothing self-serviceable. VERIFIED the '#914/#915 last comment = AcePeak 06-25' is the shared bot account
> posting MY OWN [Orc-Mycelium] escalations — NOT the human Ace answering; both threads still UNANSWERED. Did NOT re-
> comment (Rule 9 churn — my 06-25 escalations only ~1.4d old). No new issues (version still 0.3.1, nothing shipped;
> Phase 3.5 N/A). Also TRIMMED STATE.md refresh stack (~310 lines, 06-22 04:52Z → 06-24 16:03Z) — read by every agent
> on startup. Evidence: `.work/reviews/2026-06-26-1602-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-26 ~07:04Z (Orc daily review, 2nd pass today — **NO-CHANGE confirmation; nothing moved on the
> wire in the ~3h since 04:07Z. Still nothing merged/closed since #1166 (06-22 01:55Z, now ~4.3d). develop GREEN
> real-CI `3fb7b5d`. PR queue empty + no orphans (remote = main+develop+1 dependabot, Rule 14 clean). #1167 dependabot
> checkout-7: real checks ALL PASS (only Feishu-notify step + skipped Release made the run read 'failure') — mainbase
> human-only (Rule 2). status:in-progress=#766 (Ace, 06-21); status:done=#1162/#1164/#972 unverified (QA loop down,
> #915). needs:ace pile now 12 deep (incl. #914 ship-gate, #915 403, #1077 OCR, #1097 native-core build, #1105/#1136
> unattended-API sign-offs) — the growing decision backlog IS the bottleneck; loop has nothing self-serviceable. Did
> NOT re-comment #914/#915 (Rule 9 churn — my 06-25 escalations only ~1.6d old). No new issues filed (version still
> 0.3.1, nothing shipped to scan; Phase 3.5 N/A). Evidence: `.work/reviews/2026-06-26-0704-daily-review.md`.**)
>
> ---
> _Older refresh history trimmed thrice by Orc-Mycelium: 2026-06-22 (cascade of ~64 cycles, 2026-06-16 → 06-21 17:52Z, from ~461KB / 4569 lines), 2026-06-26 16:02Z (entries 06-22 04:52Z → 06-24 16:03Z, ~310 lines), and 2026-06-28 04:01Z (entries 06-25 → 06-26 04:07Z). Key history from the trimmed 06-25 entries: #914 = v0.3.2 ship-gate / scope-creep escalation (milestone grew from 5 bugs to features+needs:ace+safety; proposed A=re-scope to shippable bugfix now / B=keep scope & stay blocked — Rule 8, no unilateral milestone moves); #915 = QA-loop 403 recovered (close-recommendation posted 06-25). Both UNANSWERED by Ace. Only the last ~2 refresh entries are kept inline; STATE.md is read by every agent on startup. Full record in git history (`git log -p agents/STATE.md`), `.work/reviews/`, and `naturo-loop-state.log`. The structural reference body follows._

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
