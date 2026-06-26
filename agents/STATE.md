# Naturo Project Status
> Maintained by Orc-Mycelium. Agents: read on every startup.
> Last refreshed: 2026-06-26 ~07:04Z (Orc daily review, 2nd pass today — **NO-CHANGE confirmation; nothing moved on the
> wire in the ~3h since 04:07Z. Still nothing merged/closed since #1166 (06-22 01:55Z, now ~4.3d). develop GREEN
> real-CI `3fb7b5d`. PR queue empty + no orphans (remote = main+develop+1 dependabot, Rule 14 clean). #1167 dependabot
> checkout-7: real checks ALL PASS (only Feishu-notify step + skipped Release made the run read 'failure') — mainbase
> human-only (Rule 2). status:in-progress=#766 (Ace, 06-21); status:done=#1162/#1164/#972 unverified (QA loop down,
> #915). needs:ace pile now 12 deep (incl. #914 ship-gate, #915 403, #1077 OCR, #1097 native-core build, #1105/#1136
> unattended-API sign-offs) — the growing decision backlog IS the bottleneck; loop has nothing self-serviceable. Did
> NOT re-comment #914/#915 (Rule 9 churn — my 06-25 escalations only ~1.6d old). No new issues filed (version still
> 0.3.1, nothing shipped to scan; Phase 3.5 N/A). Evidence: `.work/reviews/2026-06-26-0704-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-26 ~04:07Z (Orc daily review — **quiet, healthy; NO-CHANGE on the wire (nothing merged/closed
> since #1166, 06-22 01:55Z, now ~4.1d); develop GREEN real-CI `3fb7b5d` (Build & Test + CodeQL SUCCESS); Dev-Sirius PR
> queue empty + no orphan branches (remote = main+develop+1 dependabot, Rule 14 clean); session-log/pr-requests are
> STALE artifacts (cleared 05-13). 2 open PRs both main-targeted human-only (Rule 2): #1167 (dependabot checkout 6→7,
> main-base) + #1055 (community fork → needs:ace #1057) — unchanged. status:done = #1162/#1164/#972 (QA's job);
> status:in-progress = #766 only (Ace umbrella, upd 06-21); v0.3.2=16/v0.3.3=12/v0.3.4=31/backlog=21 all unchanged.
> BOTH strategic threads remain UNANSWERED by Ace: #914 scope-escalation (A/B re-scope call) + #915 close-recommendation
> (06-16 403 long recovered, ~10d clean) — last comments on both are prior Orc cycles (06-25); did NOT re-post either
> (Rule 9 churn). NO new code/quality issues to file (nothing shipped to scan; Phase 3.5 N/A — version still 0.3.1, no
> PyPI release since). STRATEGIC SIGNAL persists: loop produced NO merges/verifications since 06-22 (~4.1d) —
> #1162/#1164/#972 still unverified — consistent with session-only-cron limit (Dev :07/QA :37 fire only while Orch
> session alive; persistent scheduling = open Ace decision), NOT a 403. The two open Ace decisions (#914 scope, #915
> close, + persistent-cron) are now the ONLY levers; agent loop has nothing actionable until one moves.
> Evidence in `.work/reviews/2026-06-26-0407-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-25 ~04:30Z (Orc daily review — quiet, healthy; NO-CHANGE since #1166 06-22 (~3.4d);
> develop GREEN `3fb7b5d`; queue+branches clean (Rule 14); status:done #1162/#1164/#972; v0.3.2=16/v0.3.3=12/v0.3.4=31.
> #914 scope escalation UNANSWERED, did not re-post (Rule 9). ACTION: posted close-recommendation on #915 (403 recovered
> ~9d; QA chain 06-21 #1135/#1139/#1141/#1144/#1149/#1150/#1156/#1146 + #1100 06-22). Loop stalled ~3.4d = session-only-
> cron limit, NOT a 403; flagged on #915.)
>
> Last refreshed (prior): 2026-06-25 (Orc daily review — **NO-CHANGE on the wire (nothing merged/closed since #1166, 06-22
> 01:55Z, ~3.4d; develop GREEN `3fb7b5d`; remote = main+develop+1 dependabot, Rule 14 clean; needs:ace queue at 12;
> version.py 0.3.1; v0.3.2=16/v0.3.3=12/v0.3.4=31, all unchanged) — BUT this cycle corrected the freeze narrative
> and ACTED. CORRECTION: prior cycles framed #915 as 'QA down since 06-16, ~8.5d, freezing all verify'. FALSE —
> QA-Mariana was active through 06-20 (last verify #1054), so #915 (QA-loop 403) RECOVERED and is a likely
> close/relabel (still OPEN+needs:ace, last comment 06-16 said 'close after one clean day'). NEW STRATEGIC FINDING:
> the v0.3.2 ship-gate #914 was QA-signed-off 06-16 for the ORIGINAL 5 bugs, but the milestone has since grown to 16
> issues incl. P0 FEATURES (#809/#920/#932/#1060/#1096) + needs:ace (#1097 build path, #1077 OCR) + safety #972 +
> QA tasks #581/#773/#863 → a 'v0.3.2' patch CANNOT cut at this scope. Root blocker is SCOPE CREEP, not just
> sign-off. ACTION TAKEN: posted consolidated escalation on #914 (untouched 9d, not churn) proposing Ace pick
> A=re-scope v0.3.2 to shippable bugfix/safety now (move features→v0.3.3/v0.4.0) [recommended] vs B=keep scope &
> stay blocked weeks. Rule 8 → did NOT move milestones unilaterally; awaiting Ace's A/B call to execute relabeling.
> Next cycle: if Ace answered #914, execute the split; #1162/#1164 still status:done awaiting QA (landed 06-22,
> post-signoff). Evidence in `.work/reviews/2026-06-25-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-24 16:03Z (Orc autonomous cycle — **quiet, healthy; NO-CHANGE cycle — nothing merged/closed/
> changed since #1166 (06-22 01:55Z, ~2.6d); develop GREEN real-CI `3fb7b5d`; NO team-Dev PR; Dev-Sirius PR queue
> empty + no orphan branches (remote = main+develop+1 dependabot, Rule 14 clean); session-log's "12 awaiting PR"
> list is a STALE artifact — those merged as PRs #845–855 on 05-13, confirmed against live remote. 2 open PRs both
> main-targeted human-only (Rule 2): #1167 dependabot checkout 6→7 (only failed job = Feishu webhook, code gates
> PASS → safe); #1055 community fork → needs:ace #1057. status:done = #1162/#1164/#972 (untouched, QA's job);
> status:in-progress = #766 only (Ace-owned umbrella, upd 06-21); needs:ace queue unchanged at 12; Step 3.5 weekly
> cadence (last 06-23 04:04Z) → NOT due (~06-30); no PyPI release since (version.py still 0.3.1) → post-release sweep
> not triggered; pending-issues.md (06-23) still accurate (v0.3.2 set unchanged at 16) — left as-is, no churn.
> STRATEGIC SIGNAL: project is FULLY Ace-blocked & frozen ~2.6d — entire critical path runs through needs:ace.
> #915 (QA loop 403, since 06-16, now ~8.5d, untouched) is root blocker → freezes all QA verify (#581/#773/#863/
> #972/#1162/#1164) → freezes ship-gate #914 (also untouched 8.5d). #1097 blocks moat #920/#932/#1096; #1077 blocks
> OCR #1060/#809. THREE Ace decisions (#915 infra, #1097 build path, #1077 OCR) would unblock ~everything. No
> agent-side fix exists; all tracked needs:ace; re-commenting = churn (Rule 9), held. v0.3.3 (12) + v0.3.4 (31)
> progressing normally. Evidence in `.work/reviews/2026-06-24-1603-auto-review.md`.**)
>
> Last refreshed (prior): 2026-06-24 07:03Z (Orc daily review — **quiet, healthy; NO-CHANGE cycle — nothing merged/closed/
> changed since #1166 (06-22 01:55Z, ~2.2d); develop GREEN real-CI `3fb7b5d` (HEAD `076f39e` = orc review, skip-ci);
> NO team-Dev PR; Dev-Sirius PR queue empty + no orphan branches (remote = main+develop+1 dependabot, Rule 14 clean);
> 2 open PRs both main-targeted human-only (Rule 2): #1167 dependabot checkout 6→7 — only failed job is Feishu
> webhook, CodeQL+Build&Test PASS → safe; #1055 community fork → needs:ace #1057. status:done = #1162/#1164/#972
> (untouched, QA's job); status:in-progress = #766 only (Ace-owned umbrella); needs:ace queue unchanged at 12; Step
> 3.5 weekly cadence (last 06-23 04:04Z) → NOT due (~06-30); pending-issues.md current (v0.3.2 still 16). v0.3.2
> ship-gate MET 06-17 → #914 is Ace's release call. STRATEGIC SIGNAL: QA loop down ~8 days (#915 since 06-16, 403
> errors) is the single biggest blocker — #1162/#1164/#972 unverified, ship-gate verification stuck; already tracked
> needs:ace, no agent-side fix (Rule 9 no churn). Milestone shape: v0.3.3 (12 open, distribution/recognition) +
> v0.3.4 (31 open, JSON-envelope family; watch umbrella #1142 vs per-subcommand drip) progressing normally. Evidence
> in `.work/reviews/2026-06-24-0703-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-24 04:10Z (Orc autonomous cycle — **quiet, healthy; NO-CHANGE cycle — nothing merged/closed/
> changed since 16:03Z (~12h); develop GREEN `3fb7b5d`; NO team-Dev PR; Dev-Sirius PR queue empty + no orphan branches
> (remote = main+develop+1 dependabot); status:done = #1162/#1164/#972 (untouched, QA's job); status:in-progress =
> #766 only (Ace-owned); needs:ace queue unchanged at 12; Step 3.5 weekly cadence (last 06-23 04:04Z) → not due;
> pending-issues.md current (v0.3.2 still 16). v0.3.2 ship-gate MET 06-17 → #914 is Ace's release call. STRATEGIC
> SIGNAL: QA loop down ~8 days (#915 since 06-16, 403 errors) is the single biggest blocker — #1162/#1164 unverified,
> ship-gate verification stuck; already tracked needs:ace, no agent-side fix (Rule 9 no churn). Evidence in
> `.work/reviews/2026-06-24-0410-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-23 16:03Z (Orc autonomous cycle — **quiet, healthy; NO-CHANGE cycle — nothing merged/closed/
> changed since 07:02Z (~9h); develop GREEN; NO team-Dev PR; Dev-Sirius PR queue empty + no orphan branches; needs:ace
> queue unchanged at 12; Step 3.5 weekly cadence run 04:04Z → not due. v0.3.2 ship-gate MET 06-17 → #914 is Ace's
> release call.**)
> **`develop` GREEN** — HEAD real-CI `3fb7b5d` (#1166, *fixes #1162*) **Build & Test + CodeQL both SUCCESS**; no STOP
> → new work permitted. **Step 1 PR sweep:** NO open team-Dev PR (remote = `main`+`develop`+one dependabot branch,
> Rule 14 clean). Both open PRs are `main`-targeted, **human-only (Rule 2)**: **#1167** (dependabot `actions/checkout`
> 6→7 — workflow shows *failure* but the ONLY failed job is **Feishu Notification** webhook, NOT a code gate; all
> build/test/lint/CodeQL gates PASS → `checkout@7` safe, no develop-CI regression risk) and **#1055** (community fork
> @muhamedfazalps → queued needs:ace **#1057**). Nothing merged/closed BY Orc (Rule 1). **Step 2 health:**
> `status:done` open = **#1162, #1164** (post-ship-gate hardening, awaiting QA — QA's job; sat ~62h, NOT a ship-gate
> blocker, tracked by #915) + **#972** (P0
> input-safety, human-only) → untouched. `status:in-progress` = **#766** only (Ace migration-guide umbrella,
> AcePeak-owned, updated 06-21 — not abandoned Dev work). Nothing for Orc to close (Rule 1). **Step 3 (moat):**
> native-core moat (#920/#932/JAB #1096) build-blocked locally (no MSVC/cmake) → needs:ace #1097; OCR (#1060) blocked
> on #1077. Backlog self-feeding → no new gap (Rule 9). **Step 3.5 competitiveness:** already run today (04:04Z) —
> star flatline, gap −1,535; weekly cadence satisfied for 06-23 → not re-run (Rule 9). **Step 4 (needs:ace): no new
> item;** queue unchanged at 12 #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897. **Maintenance:**
> pending-issues.md current (regenerated 06-23, v0.3.2 = 16 matches). Evidence in
> `.work/reviews/2026-06-23-0702-auto-review.md`. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call,
> #914). Detail below is prior cycles' record, kept as history.)
>
> Last refreshed (prior): 2026-06-23 04:04Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; NO team-Dev PR;
> needs:ace queue unchanged at 12; Step 3.5 competitiveness ran (due today) — star flatline, no new landscape signal
> → no redundant #919 comment (Rule 9); refreshed stale pending-issues.md (was 06-01, ref'd merged #892).**)
> **`develop` GREEN** — HEAD real-CI `3fb7b5d` (#1166, *fixes #1162*) **Build & Test + CodeQL both SUCCESS**; no STOP
> → new work permitted. **Step 1 PR sweep:** NO open team-Dev PR (remote = `main`+`develop`+one dependabot branch,
> Rule 14 clean). Open PRs are both `main`-targeted, **human-only (Rule 2)**: **#1167** (dependabot
> `actions/checkout` 6→7 — all build gates PASS, only *Feishu Notification* webhook fails, not a code gate) and
> **#1055** (community envelope fix, fork → queued needs:ace **#1057**). Nothing merged/closed BY Orc (Rule 1).
> **Step 2 health:** `status:done` open = **#1164, #1162** (fresh, from #1165/#1166 — QA's job) + **#972** (P0
> input-safety, human-only) → untouched. `status:in-progress` = **#766** only (Ace migration-guide umbrella,
> AcePeak-owned, updated 06-21 — not abandoned Dev work → label left). Nothing for Orc to close (Rule 1). **Step 3
> (moat):** native-core moat (#920/#932/JAB #1096) build-blocked locally (no MSVC/cmake) → needs:ace #1097; OCR
> (#1060) blocked on #1077. Backlog self-feeding → no new gap (Rule 9). **Step 3.5 competitiveness (DUE 06-23):**
> naturo ⭐5 (Δ0), Terminator 1,540 (Δ0), Windows-MCP 6,201 (+7), UFO² 9,092 (+8); gap → Terminator −1,535 (flat,
> naturo flat). No new major landscape signal since yesterday's "Windows Agent Runtime" intel on epic #919 → no
> redundant comment (Rule 9). **Step 4 (needs:ace): no new item;** queue unchanged at 12
> #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897. **Maintenance:** refreshed stale
> `pending-issues.md` → current v0.3.2 snapshot. **Process note:** milestone v0.2.0 still open with 0 issues → the
> routine's `CURRENT_MS=(open|sort|first)` would mis-resolve to v0.2.0 not v0.3.2 (harmless this cycle; closing
> stale milestones is Ace's call). Evidence in `.work/reviews/2026-06-23-0404-auto-review.md`. v0.3.2 ship-gate
> unchanged (FULLY MET — release is Ace's call, #914). Detail below is prior cycles' record, kept as history.)
>
> Last refreshed (prior): 2026-06-22 16:04Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; two real-CI fixes
> merged since 07:52Z (#1165 *fixes #1164*, #1166 *fixes #1162*) both now `status:done` awaiting QA; NO open team
> PR; needs:ace queue unchanged at 12; Step 3.5 NOT due (6d<7, due 06-23) — advance star+landscape intel gathered;
> NEW landscape signal: Microsoft Build 2026 "Windows Agent Runtime" first-party entrant.**)
> **`develop` GREEN** — HEAD `3fb7b5d` (#1166, *fixes #1162*) **Build & Test + CodeQL both SUCCESS**; prior real-CI
> `4721b67` (#1165, *fixes #1164*) both SUCCESS → no STOP → new work permitted. **Step 1 PR sweep:** NO open team-Dev
> PR — #1165/#1166 auto-merged themselves green, branches auto-deleted (Rule 14 clean; remote = `main`+`develop`+one
> dependabot branch). Open PRs = **#1167** (dependabot `actions/checkout` 6→7, base `main`, human-only per Rule 2 →
> left). Nothing merged/closed BY Orc (Rule 1). **Step 2 health:** no handoff owed (#1162/#1164 flipped `status:done`
> by Dev on merge → QA's verification job). `status:done` open = **#1164, #1162** (fresh, awaiting QA) + **#972** (P0
> input-safety, human-only) → untouched. `status:in-progress` = **#766** only (Ace migration-guide umbrella,
> author/assignee AcePeak, updated 06-21 — Ace-owned, not abandoned Dev work → label left). Nothing for Orc to close
> (Rule 1). **Step 3 (moat, Standing #1):** native-core moat (#920/#932/JAB #1096) build-blocked (no MSVC/cmake) →
> needs:ace #1097; OCR (#1060) blocked on #1077. Backlog sharp & self-feeding → no new gap (Rule 9, no churn).
> **Step 3.5 competitiveness: NOT due** (last row 06-16, today 06-22 16:04Z = 6d < 7; due 06-23). Advance intel:
> naturo ⭐5 (Δ0), Terminator 1,540 (+10), Windows-MCP 6,194 (+136), UFO² 9,084 (+70); gap → Terminator −1,535
> (widening, naturo flat). **NEW landscape signal — Microsoft "Windows Agent Runtime"** (Build 2026, Jun 2–3):
> first-party agentic OS substrate → commoditization risk for generic UIA automation, *sharpens* naturo's
> multi-framework recognition moat. **Rival distribution lead** (Windows-MCP 2M+ installs / MCP Registry / `uvx`) is
> the real widening gap → reinforces existing #922/#928/#997/#923 (no new issue, Rule 9). Posted as strategic intel
> on competitiveness epic **#919**. **Step 4 (needs:ace): no new item;** queue unchanged at 12
> #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897; NEEDS-ACE.md refreshed. Evidence in
> `.work/reviews/2026-06-22-1604-auto-review.md`. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call,
> #914). Detail below is prior cycles' record, kept as history.)
>
> Last refreshed (prior): 2026-06-22 07:52Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; #1146 (find --help
> saved-selector examples) now QA-verified+closed (handoff fully complete); NO open team PR; one Dev cycle in-flight;
> NO new human-only item; Step 3.6 honest no-change; queue unchanged at 12.**)
> **`develop` GREEN** — last real-CI `aa0f983` (#1163, *fixes #1146*) **Build & Test + CodeQL both SUCCESS**; HEAD
> `e54bc9e` = prior orc `[skip ci]` (no run) → no STOP → new work permitted. **Step 1 PR sweep:** NO open team-Dev
> PR (remote = `develop`+`main` only, Rule 14 clean). Only open PR = community **#1055** (@muhamedfazalps, base
> `main`, fork, MERGEABLE/UNSTABLE) → already queued needs:ace **#1057**, human-only → untouched. Nothing
> merged/closed BY Orc (Rule 1). **Step 2 health:** handoff complete — **#1146 QA-verified+closed @07:39Z**
> (clean-path verify: no pipe, JSON→file, strict UTF-8; `find --help` uniformly `@app/name`; cited merged `aa0f983`
> per Rule 1). `status:done` open now = **#972** only (P0 input-safety, human-only) → untouched. `status:in-progress`
> = **#766** only (Ace migration-guide umbrella, author+assignee AcePeak/`from:ace` — Ace-owned, not abandoned Dev
> work → label left). Nothing for Orc to close (Rule 1). **Step 3 (moat, Standing #1):** native-core moat
> (#920/#932/JAB #1096) build-blocked (MSVC/cmake/nmake/msbuild absent — Dev re-proved @07:20Z) → needs:ace #1097;
> OCR (#1060) blocked on #1077; #931 benchmark CLOSED+verified, README leads with the moat headline. Backlog sharp
> & self-feeding (#1162/#1160/#1159/#1154/#897 feed Dev) → no new gap to file (Rule 9, no churn). **Step 3.5
> competitiveness: NOT due** (last row 06-16, today 06-22 = 6d < 7) → skipped (due 06-23). **Step 3.6 (evolve the
> team): no change — no new evidence.** The one cycle that completed since 07:22Z — **QA @07:39Z verified+closed
> #1146** — was exemplary (clean-path verify, cited merged commit, lateral-grepped residual `@name` mentions and
> ruled them non-user-facing rather than re-opening, zero intrusive input, left #972 queued). The Dev cycle (started
> 07:37) is still in-flight (no `cycle END`; only #766 Ace-umbrella in-progress; no new team-Dev PR) → not yet
> assessable. Freshest rule (dev-cycle.md HEAD-check, 06-21 18:52Z <1d) only clean exercises → over-fit forbidden.
> Honest no-change row appended to EVOLUTION.md. **Step 4 (needs:ace): no new item;** queue unchanged at 12
> #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897; NEEDS-ACE.md refreshed. Evidence in
> `.work/reviews/2026-06-22-0752-auto-review.md`. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call,
> #914). Detail below is prior cycles' record, kept as history.)
>
> Last refreshed (prior): 2026-06-22 07:22Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; one open team-Dev PR
> #1163 (*fixes #1146* find --help saved-selector examples) MERGEABLE + auto-merge SQUASH ON, landing itself; QA filed
> one fresh P2 (#1162 — UNKNOWN_OPTION/UNKNOWN_COMMAND `-j` category miss) feeding Dev; NO new human-only item; Step
> 3.6 honest no-change; queue unchanged at 12.**)
> **`develop` GREEN** — last real-CI `d79647f` (#1161, *fixes #1100*) **Build & Test + CodeQL both SUCCESS**; HEAD
> `c4a8207` = prior orc `[skip ci]` (no run) → no STOP → new work permitted. **Step 1 PR sweep:** ONE open team-Dev
> PR **#1163** (`fix/issue-1146-find-help-saved-selector` → `develop`, *fixes #1146*) is **MERGEABLE + auto-merge
> SQUASH ON** (enabled 23:20Z); `BLOCKED` only because the Python test matrix + Analyze c-cpp are still running —
> every completed check SUCCESS (Build C++, Lint & Type, Version, Commit Author, Analyze python) → **left to land on
> its own** (never merge outside its own auto-merge, Rule 1/2). Pure docs/help-text (no public-API) → auto-merge
> eligible. Community **#1055** (@muhamedfazalps, base `main`, fork, MERGEABLE/UNSTABLE) → already queued needs:ace
> **#1057**, human-only → untouched. Nothing merged/closed BY Orc (Rule 1). **Step 2 health:** no handoff owed (no
> team PR MERGED this cycle — #1163 still in CI; its `status:done` flip is Dev's on-merge job). `status:done` open =
> **#972** only (P0 input-safety, human-only) → untouched. `status:in-progress` = **#1146** (active — PR #1163 in CI)
> + **#766** (Ace migration-guide umbrella, `from:ace`/AcePeak — Ace-owned, not abandoned Dev work → label left).
> Nothing for Orc to close (Rule 1). **Step 3 (moat, Standing #1):** native-core moat (#920/#932/JAB #1096)
> build-blocked (MSVC/cmake/nmake/msbuild absent — Dev re-proved @07:20Z) → needs:ace #1097; OCR (#1060) blocked on
> #1077; #931 benchmark CLOSED+verified, README leads with the moat headline. Backlog sharp & self-feeding
> (#1162/#1160/#1159/#1154/#897 feed Dev) → no new gap to file (Rule 9, no churn). **Step 3.5 competitiveness: NOT
> due** (last row 06-16, today 06-22 = 6d < 7) → skipped (due 06-23). **Step 3.6 (evolve the team): no change — no
> new evidence.** Both completed cycles since 06:52Z exemplary — **QA @07:12Z** filed P2 **#1162**
> (UNKNOWN_OPTION/UNKNOWN_COMMAND under `-j` emit `category:"unknown"` not `"validation"`; usage-path siblings #1101
> missed; ruled out the 39-Calculator `list apps` anomaly as machine clutter via OS ground truth and filed nothing
> false; zero intrusive input) and **Dev @07:20Z** shipped PR #1163 (re-proved native block first, fell to highest
> *actionable* in-progress item, **adopted a near-complete prior-cycle uncommitted fix** the safe #935 adopt-verify
> way rather than leave it half-done, fixed EVERY saved-selector example + a regression test walking docstring AND
> every option-help string, applied the 18:52Z HEAD-check rule). Freshest rule (dev-cycle.md HEAD-check, 06-21
> 18:52Z <1d) only clean exercises → over-fit forbidden. Honest no-change row appended to EVOLUTION.md. **Step 4
> (needs:ace): no new item;** queue unchanged at 12
> #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897; NEEDS-ACE.md refreshed. Evidence in
> `.work/reviews/2026-06-22-0722-auto-review.md`. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call,
> #914). Detail below is prior cycles' record, kept as history.)
>
> Last refreshed (prior): 2026-06-22 06:52Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; #1100 (test_verify
> NonWindows hermeticity) now QA-verified+closed (handoff fully complete); NO open team PR; one Dev cycle in-flight;
> NO new human-only item; Step 3.6 honest no-change; queue unchanged at 12.**)
> **`develop` GREEN** — last real-CI `d79647f` (#1161, *fixes #1100*) **Build & Test + CodeQL both SUCCESS**; HEAD
> `e029b2d` = prior orc `[skip ci]` (no run) → no STOP → new work permitted. **Step 1 PR sweep:** NO open team-Dev
> PR (remote = `develop`+`main` only, Rule 14 clean). Only open PR = community **#1055** (@muhamedfazalps, base
> `main`, fork, MERGEABLE/UNSTABLE) → already queued needs:ace **#1057**, human-only → untouched. Nothing
> merged/closed BY Orc (Rule 1). **Step 2 health:** handoff complete — **#1100 QA-verified+closed @06:38Z** (both
> prev-Windows-red tests PASS on real `win32`/py3.12.10 desktop, full `test_verify.py` 81 passed, cited merged
> `d79647f` per Rule 1). `status:done` open now = **#972** only (P0 input-safety, human-only) → untouched.
> `status:in-progress` = **#766** only (Ace migration-guide umbrella, `from:ace`/AcePeak — Ace-owned, not abandoned
> Dev work → label left). Nothing for Orc to close (Rule 1). **Step 3 (moat, Standing #1):** native-core moat
> (#920/#932/JAB #1096) build-blocked (MSVC/cmake/nmake/msbuild absent — Dev re-proved @06:20Z) → needs:ace #1097;
> OCR (#1060) blocked on #1077; #931 benchmark CLOSED+verified, README leads with the moat headline. Backlog sharp
> & self-feeding (#1160/#1159/#1154/#1152/#1146/#897 feed Dev) → no new gap to file (Rule 9, no churn). **Step 3.5
> competitiveness: NOT due** (last row 06-16, today 06-22 = 6d < 7) → skipped (due 06-23). **Step 3.6 (evolve the
> team): no change — no new evidence.** The one cycle that completed since 06:22Z — **QA @06:38Z verified+closed
> #1100** — was exemplary (real-desktop runtime check the offline runner can't do; both prev-red tests PASS; cited
> merged commit; zero intrusive input; left #972 queued). The Dev cycle (started 06:37) is still in-flight (no
> `cycle END`; no new team-Dev PR; no new remote branch) → not yet assessable. Freshest rule (dev-cycle.md
> HEAD-check, 06-21 18:52Z <1d) only clean exercises → over-fit forbidden. Honest no-change row appended to
> EVOLUTION.md. **Step 4 (needs:ace): no new item;** queue unchanged at 12
> #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897; NEEDS-ACE.md refreshed. Evidence in
> `.work/reviews/2026-06-22-0652-auto-review.md`. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call,
> #914). Detail below is prior cycles' record, kept as history.)
>
> Last refreshed (prior): 2026-06-22 06:22Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; team-Dev PR #1161
> (*fixes #1100* test_verify NonWindows hermeticity) auto-merged itself green this cycle; #1100 already
> `status:done` (handoff complete); NO open team PR; QA filed one fresh P2 (#1160 — bare `type --paste` bypasses
> the input-content guard); NO new human-only item; Step 3.6 honest no-change; queue unchanged at 12.**)
> **`develop` GREEN** — HEAD `d79647f` (#1161, *fixes #1100*) **Build & Test + CodeQL both SUCCESS** → no STOP →
> new work permitted. **Step 1 PR sweep:** NO open team-Dev PR — #1161 (`fix/issue-1100-verify-nonwindows-hermetic`
> → `develop`) **auto-merged itself** (`d79647f`, full CI matrix green); **branch auto-deleted** (Rule 14 clean —
> remote = `develop`+`main` only). Only open PR = community **#1055** (@muhamedfazalps, base `main`, fork,
> MERGEABLE/UNSTABLE) → already queued needs:ace **#1057**, human-only → untouched. Nothing merged/closed BY Orc
> (Rule 1). **Step 2 health:** handoff already complete — #1100 is **`status:done`** (Dev flipped on merge; PR base
> `develop` ≠ default branch so GitHub did not auto-close → Rule 1 preserved). `status:done` open = **#1100**
> (awaiting QA) + **#972** (P0 input-safety, human-only) → #972 untouched. `status:in-progress` = **#766** only
> (Ace migration-guide umbrella, `from:ace`/AcePeak — Ace-owned, not abandoned Dev work → label left). Nothing for
> Orc to close (Rule 1). **Step 3 (moat, Standing #1):** native-core moat (#920/#932/JAB #1096) build-blocked
> (MSVC/cmake/nmake/msbuild absent — Dev re-proved this cycle) → needs:ace #1097; OCR (#1060) blocked on #1077;
> #931 benchmark CLOSED+verified, README leads with the moat headline. QA filed **#1160** (P2 from:qa — bare
> `naturo type --paste` clipboard-only path issues raw Ctrl+V WITHOUT the input-content guard; guard gated on
> `if text is not None` at `_type.py:143`, bare-paste branch 330-332 bypasses it; mocked-backend demo, zero live
> keystrokes; fix = validate `clipboard_get()` via `unsafe_input_reason` before paste) — genuine Dev-actionable
> backlog bug, lateral to #960/#972, NOT human-only → no new gap to file (Rule 9, no churn). **Step 3.5
> competitiveness: NOT due** (last row 06-16, today 06-22 = 6d < 7) → skipped (due 06-23). **Step 3.6 (evolve the
> team): no change — no new evidence.** Both completed cycles since 05:52Z exemplary — **QA @06:12Z** filed P2
> #1160 (true new code path, mocked-backend, zero intrusive input) and **Dev @06:20Z** shipped #1100 (re-proved
> the native block first, surgical test-only fix, auditable stash-rerun gate, branch auto-deleted). Freshest rule
> (dev-cycle.md HEAD-check, 06-21 18:52Z <1d) only clean exercises → over-fit forbidden. Honest no-change row
> appended to EVOLUTION.md. **Step 4 (needs:ace): no new item;** queue unchanged at 12
> #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897; NEEDS-ACE.md refreshed. Evidence in
> `.work/reviews/2026-06-22-0622-auto-review.md`. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call,
> #914). Detail below is prior cycles' record, kept as history.)
>
> Last refreshed (prior): 2026-06-22 05:52Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; NO open team PR;
> QA filed one fresh P2 (#1159 — native A-API title data-loss, lateral to #1150) feeding Dev; Dev cycle
> in-flight (#1100 test_verify hermeticity); NO new human-only item; Step 3.6 honest no-change; queue
> unchanged at 12.**)
> **`develop` GREEN** — last real-CI `959411d` (#1158, *fixes #1156*) **CodeQL + Build & Test both SUCCESS**
> @20:53Z; HEAD `46fccf5` = prior orc `[skip ci]` (no run) → no STOP → new work permitted. **Step 1 PR sweep:**
> NO open team-Dev PR (remote = `develop`+`main` only, Rule 14 clean). Only open PR = community **#1055**
> (@muhamedfazalps, base `main`, fork, MERGEABLE/UNSTABLE) → already queued needs:ace **#1057**, human-only →
> untouched. Nothing merged/closed BY Orc (Rule 1). **Step 2 health:** no handoff owed (no team PR merged this
> cycle). `status:done` open = **#972** only (P0 input-safety, human-only) → untouched. `status:in-progress` =
> **#1100** (P2 from:dev, test_verify NonWindows hermeticity, #1133 family; Dev active @05:37Z → not abandoned)
> + **#766** (Ace migration-guide umbrella, from:ace) → both legitimate, nothing for Orc to close (Rule 1).
> **Step 3 (moat, Standing #1):** native-core moat (#920/#932/JAB #1096) build-blocked (MSVC/cmake absent) →
> needs:ace #1097; OCR (#1060) blocked on #1077; #931 benchmark CLOSED+verified, README leads with the moat
> headline. **New:** QA filed **#1159** (P2 from:qa — emoji/cross-script window titles corrupted to `?`/0x3F via
> native `GetWindowTextA` lossy `WideCharToMultiByte`; the #1150/#1157 Python codepage-decode fix can't recover;
> true fix = native `GetWindowTextW`+`CP_UTF8`, gated on native-build #1097) — genuine Dev-actionable backlog
> bug, NOT a duplicate of #1150, NOT human-only → no new gap to file (Rule 9, no churn). **Step 3.5
> competitiveness: NOT due** (last row 06-16, today 06-22 = 6d < 7) → skipped (due 06-23). **Step 3.6 (evolve the
> team): no change — no new evidence.** The one completed cycle since 05:22Z — **QA @05:40Z** (filed #1159) — was
> exemplary (independent `GetWindowTextW` ground truth + raw-byte 0x3F evidence; correctly distinguished from
> #1150 as a new native-A-API loss class; zero false needs:ace; zero intrusive input; left #972 queued). The Dev
> cycle (@05:37Z, #1100) is still in-flight (no `cycle END` since 04:54; HEAD still `46fccf5`) → not yet
> assessable. Freshest rule (dev-cycle.md HEAD-check) landed <1d ago, only clean exercises → over-fit forbidden.
> Honest no-change row appended to EVOLUTION.md. **Step 4 (needs:ace): no new item;** queue unchanged at 12
> #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897; NEEDS-ACE.md refreshed. Evidence in
> `.work/reviews/2026-06-22-0552-auto-review.md`. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call,
> #914). Detail below is prior cycles' record, kept as history.)
>
> Last refreshed (prior): 2026-06-22 05:22Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; #1156
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
