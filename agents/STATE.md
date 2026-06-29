# Naturo Project Status
> Maintained by Orc-Mycelium. Agents: read on every startup.
> Last refreshed: 2026-06-29 ~1601Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; clean convergence heartbeat ~1h50m after 1410Z — NOTHING merged/closed/verified since PR #1199 (06:40Z, ~9.4h ago); develop real-CI HEAD unchanged at `4e371fb` (Build&Test+CodeQL SUCCESS). No completed Dev/QA cycle since 1410Z; no Orc mutations to the wire (nothing crossed a threshold in <2h → commenting/re-labeling = churn). All guardrails held.** **Step 1:** PRs unchanged — #1194 (`fixes #1190`, P1) CLEAN/MERGEABLE, auto-merge OFF by design (public-surface sign-off, #1134 class; #1190 carries needs:ace) → untouched, still TOP of needs:ace, one click from merge. #1170 (`--ocr`) CONFLICTING, Ace-owned public-API gate → untouched (won't land while dirty; re-comment = churn). #1167(dependabot)/#1055(community, base=`main`) human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+`fix/issue-1060-find-ocr` [#1170]+`fix/issue-1190-wildcard-host-roundtrip` [#1194]; no orphans). **Step 2:** status:done open = **0** → no handoff owed. status:in-progress = #1195(schema-divergence P2)+#1190(PR #1194 gated)+#1175(test-debt, 00:41Z ≈15.3h <24h — aging-watch, still no PR, escalation armed)+#1169(facet-2)+#1060(#1170 held)+#932(multi-part, advanced by #1199)+#763(Ace umbrella)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog self-servicing (#1200/#1198/#1201 already filed by Dev) → **no new gap (Rule 9)**. **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6:** no change — no completed Dev/QA work since 1410Z to audit; #1175 aging held as WATCH (if >24h next cycle with no PR → nudge Dev). **Step 3.7:** done-criteria 1–4 NOT all met (#2 #1170 CONFLICTING + #1194/#1190 gated + #1169 facet-2; #3 #763/#766 in-progress; #4 #1190/#1195 open) → **no auto-advance**. needs:ace UNCHANGED at **9** (#897/#914/#935/#969/#1057/#1105/#1136/#1168/#1190). develop GREEN HEAD real-CI `4e371fb`. Evidence: `.work/reviews/2026-06-29-1601-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~1410Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; queue UNCHANGED at 9. One completed Dev cycle since 1354Z, all rules SUCCEEDING: Dev merged PR #1199 (click-via-JAB action-assertion slice of #932) and self-filed the multi-part follow-ups (#1200 JAB value/states gap, #1201 find `-q` conflict). No Orc mutations to the wire beyond one [Orc] consolidation note on #1201; all guardrails held.** **Step 1:** **PR #1199 already MERGED** (`4e371fb`, *part of #932*, team branch auto-deleted) — full CI GREEN (Build&Test + CodeQL SUCCESS); Dev held #932 honestly `status:in-progress` (multi-part: type-via-JAB + checkbox/toggle-via-JAB slices remain, blocked by the #1200 JAB-provider value/states gap) → **NO handoff flip owed** (partial-by-design, `part of` not `fixes`). #1194 (`fixes #1190`, P1) re-confirmed auto-merge OFF by design (public-surface sign-off, #1134 class; #1190 carries needs:ace) → untouched (guardrail), still TOP of NEEDS-ACE.md one click from merge. #1170 (`--ocr`) UNKNOWN/CONFLICTING, Ace-owned public-API gate → untouched. #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+`fix/issue-1060-find-ocr` [#1170]+`fix/issue-1190-wildcard-host-roundtrip` [#1194]; #932 branch auto-deleted, no orphans). **Step 2:** status:done open = **0** → no handoff owed. status:in-progress = #1195(schema-divergence P2)+#1190(PR #1194 gated)+#1175(test-debt, 00:41Z ≈9.5h <24h — aging-watch, still no PR)+#1169(facet-2)+#1060(#1170 held)+**#932**(just advanced by #1199, multi-part)+#766(Ace umbrella, parked) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET (#1199 *advances* #932's Java moat — recognition+action both now proven via JAB); backlog self-servicing — the JAB value/states gap (#1200) and find-query footguns (#1198/#1201) are already filed by Dev → **no new gap to file (Rule 9)**. **Orc Step-3 action:** posted ONE [Orc] consolidation note on **#1201** tying the `find` query-source conflict-guard family (#1193 FIXED + #1198 + #1201), recommending Dev fix #1198+#1201 in one branch with a single unified conflict-guard (reuse #1193's `INVALID_INPUT` plumbing, validate before the platform gate) instead of chasing siblings one at a time — mirrors the prior #1192⊂#1175 cross-link discipline; did NOT close/relabel (Dev/Ace's call). **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence; signals are the rules SUCCEEDING** — #1199's new desktop test is exemplary (independent adversarial-verifier PASS, tautology ruled out via no-click/wrong-coords both leaving `Pending`, discriminating Submit-vs-Cancel control, per-test relaunch, CI-safe), and Dev's honest partial-issue handling + self-filed follow-ups are good hygiene. The find-query footgun cluster (#1193/#1198/#1201) is a **same-day same-surface product-bug burst** → encoding a broad input-source-conflict principle now = over-fit (forbidden); held as a WATCH-ITEM with an escalation trigger (if Dev fixes #1198/#1201 narrowly one-at-a-time → encode next cycle). Checklist dev 7 + qa 6, both < ~8 → no distillation. EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING + #1194/#1190 gated + #1169 facet-2; #3 #766 in-progress; #4 #1190/#1195/#1198/#1201 open + #1170 half-finished) → **no auto-advance**. needs:ace UNCHANGED at **9**. develop GREEN HEAD real-CI `4e371fb` (#1199 Build&Test+CodeQL SUCCESS; orc `[skip ci]` on top). Evidence: `.work/reviews/2026-06-29-1410-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~1354Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; queue UNCHANGED at 9. Clean convergence heartbeat (~30 min after 1322Z) — NOTHING merged/closed/verified since; develop real-CI HEAD unchanged at `d3a90b8` (#1196 Build & Test + CodeQL SUCCESS). Two signals, neither a Dev/QA operating artifact: (1) a Dev cycle in flight (started 13:37 local, no branch/PR pushed yet — remote still only #1170/#1194 heads); (2) a QA cycle that ERRORED before running — its runner crashed on a transient lock of the shared `naturo-loop-state.log` (held by the concurrently-starting dev runner), so that QA heartbeat was skipped. No Orc mutations to the wire; all guardrails held.** **Step 1:** #1194 (`fixes #1190`, P1, team) re-confirmed CLEAN/MERGEABLE, auto-merge OFF by design (public-surface sign-off, #1134 class; #1190 carries needs:ace) → untouched (guardrail), still TOP of NEEDS-ACE.md one click from merge. #1170 (`--ocr`) re-confirmed CONFLICTING/DIRTY, auto-merge ON, Ace-owned public-API gate → untouched (won't land while dirty; re-comment = churn). #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+`fix/issue-1060-find-ocr` [#1170]+`fix/issue-1190-wildcard-host-roundtrip` [#1194]; no orphans). **Step 2:** status:done open = **#1193** (empty-query fix, merged `d3a90b8` ~05:32Z, awaiting QA — fresh ~20min, handoff already done last cycle → no handoff owed, not aging). status:in-progress = #1195(schema-divergence P2)+#1190(PR #1194 gated)+#1175(test-debt, 00:41Z ≈5h <24h — aging-watch, still no PR)+#1169(facet-2)+#1060(#1170 held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog self-servicing (#1190 fix gated, #1193 awaiting QA, #1195/#1189/#1197 filed) → **no new gap (Rule 9)**. **Watch (1st instance):** QA runner died on a transient `naturo-loop-state.log` lock — a loop-durability/robustness signal in the #1168/#935 harness family (NOT product code, NOT a Dev/QA operating weakness); one instance → note, don't escalate; if a 2nd QA cycle dies the same way, surface a harness fix (log-lock retry / per-runner log) to Ace under #1168. **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (Dev in flight, no completed work/tests to audit; QA crashed before running; the QA log-lock crash is harness/infra, not an encodable operating/test-quality weakness, and is a 1st instance → over-fit forbidden; checklist dev 7 + qa 6, both < ~8 → no distillation; EVOLUTION row appended). **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING + #1194/#1190 gated + #1169 facet-2; #3 #766 in-progress; #4 #1190/#1195/#1189 open + #1170 half-finished) → **no auto-advance**. needs:ace UNCHANGED at **9**. develop GREEN HEAD real-CI `d3a90b8` (#1196 Build&Test+CodeQL SUCCESS; orc `[skip ci]` on top). Evidence: `.work/reviews/2026-06-29-1354-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~1322Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; queue UNCHANGED at 9. Two completed cycles since 1252Z, both the loop working: (1) Dev opened PR #1196 (`fixes #1193`, empty-query footgun → `INVALID_INPUT`) — green-in-flight, auto-merge ON, self-landing; (2) a read-only QA cycle (0 bugs, 1 false positive correctly suppressed) flagged an env-hygiene leak → Orc filed actionable #1197. No Orc mutations to the wire beyond filing #1197; all guardrails held.** Since 1252Z: **(1) Dev @~13:23 local opened PR #1196** (team branch `fix/issue-1193-empty-query`→develop, *fixes #1193*) — empty/whitespace-only positional query & `-q ""` now normalize to `None` → registered **`INVALID_INPUT`** (category validation) **before** the platform/backend gate, instead of falling through to the `*` wildcard match-all-as-success footgun; `--all`/`--role`/`--actionable` still opt into match-all. **CI green-in-flight** (Lint/Version/Author/Win C++ build/**Windows DLL tests**/Ubuntu 3.9-3.13 all SUCCESS; macOS + c-cpp CodeQL pending — not red); **auto-merge ON (squash) by Dev — CORRECT**: bug-fix behavior correction reusing the pre-existing `INVALID_INPUT` code (no new flag/code/param), the #1172/#1179/#1180 error-contract-fix class where the public-API guardrail correctly does NOT fire (vs the #1190/#1194 new-resolution-semantics class where it DID) → self-lands when green; **Orc did NOT merge** (auto-merge is Dev's; guardrail). **(2) QA cycle @~13:17 local** (read-only): develop GREEN reconfirmed, **0 verifications** (status:done queue empty), **0 new bugs** — correctly **suppressed 1 false positive** (identically-titled orphaned windows made a title lookup ambiguous → diagnosed as polluted-desktop, NOT a naturo defect), zero intrusive input; **flagged an env-hygiene leak for Ace** (80+ orphaned Calculator/Notepad windows accumulating across cycles, degrading title-based recognition QA). **Step 1:** #1196 = team Dev PR auto-merge ON → self-lands, untouched (Orc doesn't merge). #1194 (`fixes #1190`, P1) CLEAN/MERGEABLE, auto-merge OFF by design (public-surface sign-off, #1134 class; #1190 carries `needs:ace`) → untouched (guardrail); still TOP of NEEDS-ACE.md, one click from merge. #1170 (`--ocr`) re-confirmed CONFLICTING/DIRTY, auto-merge ON, Ace-owned public-API gate → untouched (won't land while dirty; no churn). #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+`fix/issue-1060-find-ocr` [#1170]+`fix/issue-1190-wildcard-host-roundtrip` [#1194]+`fix/issue-1193-empty-query` [#1196]; no orphans). **Step 2:** status:done open = **0** → no handoff owed (nothing merged since `2cb623c`). status:in-progress = #1193(PR #1196 in flight)+#1190(PR #1194 gated)+#1175(test-debt, 00:41Z ~12.5h <24h — aging watch, still no PR)+#1169(facet-2)+#1060(#1170 held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog self-servicing (#1193 fix in flight; #1190 fix gated; #1195 filed) → but QA's env-hygiene flag is a **concrete, untracked, recurring loop-hygiene/silent-failure gap** (80+ orphaned windows degrade the recognition surface; possible #226-class `app quit` silent failure) → **filed sharp #1197** (tech-debt/P3/silent-failure: audit dev/QA teardown + the `app quit`-silently-succeeds hypothesis [Dev-actionable] + an Ace-only one-time live-machine cleanup note). NOT needs:ace (the audit/fix is loop-ownable). **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence; the one completed Dev signal is the rules SUCCEEDING.** Test-quality audit of `test_find_empty_query_1193.py` = **EXEMPLARY** (hermetic; BEHAVIOR-not-shape — asserts `INVALID_INPUT` AND `elements` absent AND backend never reached; discriminating negative controls — `--all`/`--role`/`--actionable` pass the gate and DO reach the backend, proving a specific not blanket reject; parametrized positional×`-q`×empty/whitespace×json/plain); Dev's auto-merge-ON judgment shows the public-API guardrail discriminating correctly on the bug-fix side (mirror of #1194's correct OFF). Encoding a rule atop rules succeeding = over-fit (forbidden). Checklist dev 7 + qa 6, both < ~8 → no distillation. EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING + #1190/PR#1194 gated + #1169 facet-2; #3 #766 in-progress; #4 #1190/#1193/#1195 open + #1170 half-finished) → **no auto-advance**. needs:ace UNCHANGED at **9** (#1197 is backlog, not a human gate). develop GREEN HEAD real-CI `2cb623c` (#1191 Build&Test+CodeQL SUCCESS; orc `[skip ci]` on top). Evidence: `.work/reviews/2026-06-29-1322-auto-review.md`. **UPDATE (same cycle, during the state push): PR #1196 went green and AUTO-MERGED to develop (`d3a90b8`, *fixes #1193*).** Base=develop≠default → no auto-close, so Orc performed the on-merge handoff: flipped #1193 `status:in-progress`→`status:done` citing `d3a90b8` (Rule 1) + [Orc] comment asking QA to verify the empty/whitespace-query `INVALID_INPUT` reject vs the `--all`/`--role`/`--actionable` opt-ins (pure-Python CLI guard, no DLL → stale-DLL trap N/A). Branch `fix/issue-1193-empty-query` auto-deleted (Rule 14 clean; remote = main+develop+dependabot+#1170+#1194 heads). status:done open now = **#1193** (fresh, awaiting QA). develop HEAD now `0b11829` (orc `[skip ci]` atop the `d3a90b8` merge); #1196's CI was green pre-merge.)
>
> Last refreshed (prior): 2026-06-29 ~1252Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; queue UNCHANGED at 9. Two signals since 1225Z, both the loop working: (1) the P1 fix PR #1194 completed FULL-MATRIX GREEN — now one sign-off click from merge; (2) QA filed genuine NEW #1195 (3rd success-payload schema-drift instance) → Orc encoded a dev-cycle principle for the class. No Orc mutations to the wire beyond one [Orc] note on #1195; all guardrails held.** Since 1225Z: **(1) PR #1194 (`fixes #1190`, P1 reusable `app://*`-selector round-trip) went from green-in-flight to FULL-MATRIX GREEN** — every check SUCCESS (Lint/Version/Author/Win C++ build/**Windows DLL tests**/Ubuntu+macOS 3.9-3.13/2×CodeQL/CI Gate), MERGEABLE/CLEAN, auto-merge still **OFF by Dev's design** (public-surface sign-off, #1134 class; #1190 carries `needs:ace`). Orc did **NOT** enable auto-merge / merge (guardrail — public-API hold); the only thing between this P1 and merge is Ace's sign-off → flagged at the TOP of NEEDS-ACE.md as ready. **(2) QA cycle (~12:47 local) filed genuine NEW #1195** (bug/P2/from:qa, read-only repro): `find`'s UIA strategy omits `center_x`/`center_y` + reports `coordinate_frame:null` while `--image` populates both (both screen-absolute) → a consumer must branch on which strategy answered. **Step 1:** #1194 = team Dev PR, auto-merge OFF by design → untouched (guardrail). **#1170 (`--ocr`)** re-confirmed CONFLICTING/DIRTY, auto-merge ON (Ace-enabled 02:39Z), Ace-owned public-API gate → untouched (won't land while dirty; no churn). #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+`fix/issue-1060-find-ocr` [#1170]+`fix/issue-1190-wildcard-host-roundtrip` [#1194]; no orphans). **Step 2:** status:done open = **0** → no handoff owed (no merge since `2cb623c`). status:in-progress = #1193(empty-query footgun)+#1190(PR #1194 gated)+#1175(test-debt, 00:41Z ~12h <24h — aging watch, still no PR)+#1169(facet-2)+#1060(#1170 held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog self-servicing (#1195 freshly filed w/ root-cause; #1193/#1190 in flight) → no new ISSUE to file (Rule 9), but #1195 is the **3rd success-payload schema-drift instance** (after #886/#1184) on the schema-parity axis specifically — the recurrence the multi-cycle watch-item was waiting for → posted one [Orc] note on #1195 tying it to the lineage + recommending the fix double as a cross-strategy parity guard (success-side mirror of #1180). **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: ONE EVIDENCE-BACKED CHANGE SHIPPED** — added dev-cycle Step-3 self-review principle **"Output-schema parity (parallel result builders)"** (success-side mirror of error-code-registration; cite #886/#1184/#1195, 3 instances >1d apart; no existing principle covered SUCCESS-payload output-schema parity — "Cross-command parity" is flag-resolution, "Option coverage" is input options). Checklist 6→7 < ~8 → ADD not distill; `[skip ci]`. EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING + #1190 PR-gated + #1169 facet-2; #3 #766 in-progress; #4 #1190/#1193/#1195/#1189 open + #1170 half-finished) → **no auto-advance**. needs:ace UNCHANGED at **9**. develop GREEN HEAD real-CI `2cb623c` (#1191 Build&Test+CodeQL SUCCESS; orc `[skip ci]` on top). Evidence: `.work/reviews/2026-06-29-1252-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~1225Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; ONE NEW HUMAN GATE opened by Dev — PR #1194 (`fixes #1190`, the P1 reusable-selector round-trip) held auto-merge OFF + queued `needs:ace` (public-surface sign-off, #1134 class) → needs:ace 8→9. No Orc mutations to the wire; all guardrails held.** Since 1202Z: **Dev opened PR #1194** (`fix/issue-1190-wildcard-host-roundtrip`→develop, *fixes #1190*) — the emitted `app://*` wildcard-host selector now **round-trips by resolving across all top-level windows** (was `SELECTOR_NOT_FOUND` standalone) via a shared `_resolve_wildcard_host_forest` helper used by both `find --selector` and the click family. **Dev correctly held auto-merge OFF + added `needs:ace` + commented** "pending Ace public-surface sign-off (activates round-trip resolution semantics; human-only per #1134 guardrail)" — a textbook application of the 06-20 Dev-side public-API guardrail. **Step 1:** **PR #1194** = team Dev PR, auto-merge **OFF by design** (public-surface gate) → Orc did **NOT** enable auto-merge / merge (guardrail held); CI green-in-flight at review (Lint/Version/Author/Win-C++ build SUCCESS; cross-platform pytest + CodeQL still running — not red, fresh ~04:21Z). **#1170 (`--ocr`)** re-confirmed UNKNOWN/CONFLICTING, Ace-owned public-API gate → untouched (no churn). #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+`fix/issue-1060-find-ocr` [#1170]+`fix/issue-1190-wildcard-host-roundtrip` [#1194]; no orphans). **Step 2:** status:done open = **0** → no handoff owed (no merge since `2cb623c`; #1194 is a fresh PR not a status:done). status:in-progress = #1190(now PR #1194 in flight)+#1175(test-debt, 00:41Z ~3.7h <24h — aging watch)+#1169(facet-2)+#1060(#1170 held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog self-servicing (P1 #1190 now has a fix PR in flight + correctly gated) → **no new gap (Rule 9)**. **Watch-item RESOLVING FAVORABLY:** the #1190 "structural CI round-trip gate" gap (held across #886/#1184/#1190, pending "file if the requested round-trip test doesn't land") — **#1194 lands exactly that test** (`tests/test_selector_wildcard_host_roundtrip_1190.py`) → no structural gap to file. (#1175 aging re-check next cycle.) **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence; the one new signal is the existing rules SUCCEEDING.** #1194's hold = the 06-20 public-API guardrail working; **test-quality audit of `test_selector_wildcard_host_roundtrip_1190.py`: EXEMPLARY** — hermetic (mocked backend, no real desktop), BEHAVIOR-not-shape (emit via `find --hwnd` → paste back into `find --selector` with NO target flag → assert same named element; + click-family `_resolve_selector_target`), **discriminating negative control** (default/foreground window is a *different* app lacking the target → a pass proves the across-windows search, not the ambient desktop). It embodies the 1052Z qa-cycle principle 5 ("verify the advertised workflow itself, not a privileged proxy") now as a Dev regression test + the 06-20 hermeticity rule. Over-fit on a success = forbidden. Distillation: dev-cycle Step-3 6 principles + qa-cycle Step-2 6 items, both < ~8 → not due. EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING + #1190 PR-in-flight-but-gated + #1169 facet-2; #3 #766 in-progress; #4 #1190/#1193/#1189 open + #1170 half-finished) → **no auto-advance**. needs:ace now **9** (was 8 — Dev added #1190's public-surface sign-off). develop GREEN HEAD real-CI `2cb623c` (#1191 Build&Test+CodeQL SUCCESS; orc `[skip ci]` on top). Evidence: `.work/reviews/2026-06-29-1225-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~1202Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; short heartbeat (~10 min after 1152) — nothing merged/closed by anyone since. One Orc action: cross-linked the duplicate #1192⊂#1175 the 1152 cycle missed. No mutations to the wire beyond that one comment; all guardrails held. needs:ace UNCHANGED at 8.** Since 1152: only new signal is **#1192** (AcePeak, tech-debt P3, @03:03Z — filed *before* the 1152 review but unnoted there) = the **same defect as #1175 item #1** (`tests/test_cost_guardrails.py:14` bare `open()` missing `encoding="utf-8"`, identical GBK/cp936 `UnicodeDecodeError` repro + one-line fix; #1175 already bundles it with the `test_agent` total_time clock-flake). **Action:** posted one `[Orc]` consolidation note on #1192 (no prior cross-link; both comment-counts were 0) recommending Dev fix **both** `tests/` hermeticity items in one branch (`fixes #1192, fixes #1175`) and close the redundant one; did **NOT** close (Rule 1) or relabel (Ace filed both → consolidation is Dev/Ace's call). **Step 1:** #1170 (`--ocr`) re-confirmed CONFLICTING/DIRTY, auto-merge ON, base=develop, Ace-owned → untouched (no churn, public-API gate). #1167(dependabot, base=develop, auto-merge OFF)/#1055(community, base=main) human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+`fix/issue-1060-find-ocr` [#1170 head]; no orphans). **Step 2:** no handoff owed (no merge since `2cb623c`; #1192 is a fresh dup not a status:done). status:done open = **#1058** (awaiting QA, handed off 1152). status:in-progress = #1190(P1 reuse regression)+#1175(test-debt, ~3.3h <24h, now sharper via #1192 cross-link)+#1169(facet-2)+#1060(#1170 held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog self-servicing → **no new gap (Rule 9)**. Watch-items: (a) #1190 = 3rd success-side reuse-fidelity instance (#886+#1184+#1190) — its own issue requests the round-trip regression test → hold the structural "CI round-trip gate" gap one more cycle; (b) #1175 aging (<24h, no PR); (c) **NEW watch (1st instance):** AcePeak re-filed a sub-issue (#1192) already captured inside a bundled tech-debt issue (#1175) → not yet a pattern, watch for a 2nd before encoding any rule. **Step 3.5:** NOT due (<7d). **Step 3.6: no change** — the only signal is a duplicate-issue housekeeping catch (Orc's cross-link discipline working), not a product/test artifact to audit; over-fit forbidden; EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (#2 #1170 CONFLICTING + #1190 P1 + #1169 facet-2; #3 #766 in-progress; #4 #1190/#1193/#1189/#1192 open + #1170 half-finished) → **no auto-advance**. needs:ace UNCHANGED at 8. develop GREEN HEAD real-CI `2cb623c` (#1191 Build&Test+CodeQL SUCCESS). Evidence: `.work/reviews/2026-06-29-1202-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~1152Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; one Dev fix landed end-to-end — #1058 (`list windows --app` honest-help) merged via PR #1191 (`2cb623c`), Orc did the on-merge handoff (→status:done); QA filed P2 #1193. No Orc mutations to the wire beyond the #1058 handoff; all guardrails held. needs:ace UNCHANGED at 8.**
> Since 1052Z: **one completed Dev cycle + one completed QA cycle.** **(1) Dev merged PR #1191** (`2cb623c`, *fixes #1058*, team branch `fix/issue-1058-list-app-help`) — applied option (A) per Ace's triage + QA's write-up: the `list windows --app` `--help` text + docstring now honestly state `--app` matches process name **OR** window title (the intentional family-wide broad-targeting rule shared with `see`/`capture`/`click`), `--window` the narrowing flag. base=`develop`≠default → no auto-close → **Orc performed the on-merge handoff**: flipped #1058 `status:in-progress`→`status:done` citing `2cb623c` (Rule 1) + [Orc] ask QA to verify help-vs-behavior (doc/help-text fix, no DLL → stale-DLL trap N/A). **(2) QA @03:40Z exploratory** — develop GREEN reconfirmed @ `2cb623c`, filed genuine NEW **#1193** (bug/from:qa/P2 — `find ""`/`find -q ""` empty-query silently matches ALL elements `success:true` while `--selector ""`/`--image ""`/missing-arg all reject empty → `INVALID_INPUT`; footgun for `find "$VAR"` with empty var; lateral evidence table on-issue), read-only probes only (zero intrusive input). **Step 1:** **#1170 (`--ocr`) re-confirmed CONFLICTING/DIRTY**, auto-merge OFF, Ace de-queued/owns it → did **NOT** re-comment (churn), **NOT** merge/enable (public-API gate + Ace's call). #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+`fix/issue-1060-find-ocr` [#1170 head]; `fix/issue-1058-list-app-help` auto-deleted on merge → no orphans). **Step 2:** #1058 handoff done (now status:done awaiting QA); status:in-progress = #1190(P1 reuse regression)+#1175(test-debt, 00:41Z, ≈2.7h <24h — aging watch)+#1169(facet-2)+#1060(PR #1170 held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog self-servicing (#1190 P1 + #1189 P2 + #1193 P2 freshly filed w/ repro; #1169 facet-2 + #1175 in flight) → **no new gap (Rule 9)**. Watch-items: (a) #1190 = **3rd** success-side reuse-fidelity instance (#886+#1184+#1190) — #1190's own issue already requests a round-trip regression test, so hold the structural "CI round-trip gate" gap one more cycle (file if a 4th appears or that test doesn't land); (b) #1175 aging (no PR across heartbeats, still <24h) → re-check next cycle. **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** — both completed signals are the existing rules SUCCEEDING: #1191's new `test_list_windows_app_help_1058.py` is **exemplary** (pins help text BOTH directions [must say "process name" AND "window title"; old lying phrase "application name or process name" must be GONE] + proves behavior with a discriminating fixture whose titles deliberately don't contain process basenames so title-vs-process match is unambiguous; hermetic, BEHAVIOR-not-shape) = never-lie + #871-parity + hermeticity rules succeeding; QA's #1193 = a genuine product bug via anti-false read-only discipline, not an operating weakness. Noted **flag-to-watch (first instance):** the #871 harmonization (#1053) shipped a docstring under-describing `--app`'s scope → if a *2nd* harmonization PR under-describes a flag's scope, add a one-line dev-cycle rule (align help/docstring to broad behavior, pin with a help-text test); over-fit forbidden on one incident, and #1191 already added the both-directions guard. Distillation: dev-cycle Step-3 6 principles + qa-cycle Step-2 6 items, both < ~8 → not due. EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING + #1190 P1 reuse regression + #1169 facet-2; #3 #766 in-progress; #4 #1190/#1193/#1189 open + #1170 half-finished) → **no auto-advance**. needs:ace UNCHANGED at 8. develop GREEN HEAD real-CI `2cb623c` (#1191 Build&Test+CodeQL SUCCESS; orc `0bc1b27` `[skip ci]` on top). Evidence: `.work/reviews/2026-06-29-1152-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~1052Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; ACE CHECK-IN LANDED — Ace merged PR #1171 (signed off #1169's public-CLI gate), closed #972/#975, de-queued #915/#1060 → needs:ace 13→8. One genuine team-evolution change shipped this cycle. No Orc mutations to the wire; all guardrails held.**
> Since 1022Z: **Ace check-in + one QA cycle.** **(1) Ace @02:39Z merged PR #1171** (`3a5df92`, "honor `--backend`/`--depth` in `find --selector`, refs #1169") — the public-CLI-default gate (`uia`→`auto`) is **signed off by the human merge**; develop full CI **GREEN** (Build&Test + CodeQL SUCCESS on `3a5df92`); branch `fix/issue-1169-shortform-selector` auto-deleted (Rule 14 clean). PR was **"refs" #1169 (partial)** → `closingIssuesReferences` empty → **#1169 correctly stays `status:in-progress`** for the remaining facet-2 work (role-only match + desktop-wide "any app" search) → **NO Orc handoff flip owed** (Dev deliberately scoped it partial). **(2) Ace de-queued 5 needs:ace items** in the same check-in: **#972 CLOSED** (input-content safety guard, P0), **#975 CLOSED** (QA re-enable ratified), **#915** left OPEN but needs:ace removed (QA-403 recovery de-escalated), **#1060** needs:ace removed (still OPEN/in-progress; PR #1170 `--ocr` still CONFLICTING — Ace is handling `--ocr` directly, so Orc does NOT re-add the label, Ace's call), **#1169** needs:ace removed (gate signed off via the merge). Queue 13→**8**: #1168/#1136/#1105/#1057/#969/#935/#914/#897. **(3) QA @02:45Z (10:45 local) filed NEW P1 #1190** — the reusable `app://*`-wildcard-host selector that #1184/#1188 emit does **NOT round-trip standalone** (paste into click/type/`find --selector` with no `--hwnd`/`--app` → `SELECTOR_NOT_FOUND`); root-caused with a 7-row control table (concrete host / `--hwnd` / short `//`form all resolve; only the `*` host fails). Breaks the advertised see→copy→click workflow; **undercuts criterion #2's headline reuse promise** — Dev-actionable (fix options in issue), NOT a human gate. Distinct from #1189 (P2, error-message wording). **Step 1:** **#1170 (`--ocr`) re-confirmed CONFLICTING/DIRTY**, auto-merge OFF; Ace de-queued it but it's unmerged → my 23:24Z [Orc] rebase-flag is still its latest actionable comment → did **NOT** re-comment (churn), did **NOT** merge/enable (public-API gate + Ace owns it now). #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+`fix/issue-1060-find-ocr` [#1170 head]; no orphans). **Step 2:** no handoff owed (#1171 partial-by-design; #1190/#1189 are fresh bugs not status:done). **status:done open = 0** (#972 now closed by Ace). status:in-progress = **#1169**(facet-2 remaining, just updated)+**#1060**(PR #1170 held)+**#1058**(no PR, 01:41Z, <24h)+**#1175**(no PR, 00:41Z, ~2h11m <24h — aging watch-item, still not abandoned)+**#766**(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog self-servicing (#1190 P1 + #1189 P2 freshly filed with repro+fix; #1058/#1169 facet-2 in flight) → **no new gap (Rule 9)** — #1190 is the success-side reuse instance, already filed. Watch-items: (a) **#1190 = 3rd success-side payload/reuse-fidelity instance** (after #886 + #1184) — now a clear recurrence, but #1190's own issue already requests a round-trip regression test, so hold the *structural* "needs a CI round-trip gate" gap one more cycle (file if a 4th appears or the test doesn't land); (b) #1175 aging (no PR across heartbeats, still <24h) → re-check next cycle. **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: ONE CHANGE SHIPPED** — qa-cycle.md Step 2 principle #5 ("verify the advertised workflow itself, not a privileged proxy"): the #1184-verified-then-#1190-broke round-trip is a QA verification-completeness gap (false PASS via a scoped path) in Ace's 2026-06-29 test-quality family; no existing qa-cycle principle covered reuse-as-the-user-reuses-it; list was 5 < ~8 → ADD not distill; one cite, complements (not restates) Step-2.4's false-FAIL guard; EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING + **#1190 P1 fresh regression on `--selector` reuse** + #1169 facet-2; #3 #766 in-progress; #4 #1190 open + #1170 half-finished) → **no auto-advance**. needs:ace now **8** (was 13 — Ace check-in). develop GREEN HEAD real-CI `3a5df92` (#1171 Build&Test+CodeQL SUCCESS). Evidence: `.work/reviews/2026-06-29-1052-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~1022Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; clean convergence heartbeat — one QA cycle completed (1 exploratory PASS + filed #1189), Dev in flight on #1058. No Orc mutations to the wire; all guardrails held. needs:ace UNCHANGED at 13.**
> Since 0952Z: **one completed QA cycle, zero merges.** **QA @~02:15Z (10:15 local) ran an exploratory PASS on the post-#1188 find/selector integration reality** — find-emitted `selector` == see-emitted selector exactly (Document, all MenuItems incl. multi-attr `[@automationid="File", @name="文件"]`); round-trip `find --selector` re-resolves find-emitted selectors (incl. embedded-newline `Text[@name="行 1，\n列 1"]`); physical `click --selector` on a find-emitted Edit-menu selector opened the menu (screenshot-confirmed); post-#1180/#1182/#1183 error envelopes all six-key/distinct (malformed→INVALID_SELECTOR, no-match→SELECTOR_NOT_FOUND, no-app→WINDOW_NOT_FOUND). **Filed one genuine NEW bug #1189** (bug/P2/from:qa — `SELECTOR_NOT_FOUND` suggests saved-selector `selector list` even for structural `app://`/`//` path lookups → misdirects recovery; repro + suggested fix at `error_helpers.py:136`; Dev-actionable, NOT a human gate). QA caught its own `capture --out` typo before trusting a false failure (Step-2.4 discipline), set `MSYS2_ARG_CONV_EXCL`/`PYTHONUTF8=1`, benign-only intrusive input under the safe-input guard. **Step 1:** **#1170 (`--ocr`) re-confirmed CONFLICTING/DIRTY**, auto-merge OFF; my 23:24Z [Orc] rebase-flag is still its latest actionable comment → did **NOT** re-comment (churn), did **NOT** merge/enable (public-API gate, guardrail). **#1171 (`--selector` default) MERGEABLE/CLEAN**, auto-merge OFF, public-CLI-default gate → untouched. #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+2 live PR heads #1170/#1171; no orphans). **Step 2:** no handoff owed (no merge since `6e91ddd`; #1189 is a fresh bug not a status:done). status:done open = **#972** only (human-only, parked). status:in-progress = **#1058**(fresh, no PR, updated 01:41Z)+**#1175**(host-locale/clock bad-test fix, no PR, <24h)+#1169/#1060(PRs held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog self-servicing (#1189 freshly filed with repro+fix, #1058 in flight) → **no new gap (Rule 9)**. Carried **watch-items**: (a) success-side payload-builder drift (#886+#1184 = 2 instances) — still no 3rd recurrence → hold; (b) #1175 aging (in-progress, no PR across heartbeats, still <24h) — not yet avoidance evidence → re-check next cycle. **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (the one completed cycle = QA's anti-false-alarm discipline SUCCEEDING [caught own typo, ruled out harness false-alarm before filing]; #1189 is a genuine product bug not an operating weakness; no new tests authored this heartbeat to audit; over-fit forbidden; self-review 6 principles < ~8 distillation threshold; EVOLUTION row appended). **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING + #1171 held public-API gates; #3 #766 in-progress; #4 half-finished PRs #1170/#1171 + #1058/#1175 in flight + #1189 open) → **no auto-advance**. needs:ace UNCHANGED at 13. develop GREEN HEAD real-CI `6e91ddd` (#1188 Build&Test+CodeQL SUCCESS; orc `12463ae`/`dd358c6`/`ec34429` `[skip ci]` on top). Evidence: `.work/reviews/2026-06-29-1022-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~0952Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; clean convergence heartbeat — the #1188/#1184 handoff COMPLETED end-to-end:
> QA verified+closed #1184 (find↔see selector parity), and Dev picked up #1058. No Orc mutations to the wire; all guardrails held. needs:ace UNCHANGED at 13.**
> Since 0927Z: **one completed cycle + one Dev pick.** **(1) QA @~01:4XZ VERIFIED+CLOSED #1184** (PR #1188 `6e91ddd`) — `find` now emits the reusable unified `app://` `selector` field
> `see` emits; textbook **behavior** verify on live Win11 UIA: `find` Document selector **BYTE-IDENTICAL** to `see`'s for the same node (`app://*/Window[@name="无标题 - Notepad"]/Document
> [@name="文本编辑器"]`), round-trip `find <selector>` resolves the same node, `--all` 44 elems 0 missing, human output prints the `selector:` line, full discover→`selector save`→reuse chain
> works with the probe selector cleaned up (no residue), `test_find_selector_field_1184.py` 7/7; no-DLL fix → stale-DLL trap N/A; removed `status:done`+added `verified`+CLOSED. This
> completes the 0927Z on-merge handoff end-to-end. **(2) Dev cycle (ended 09:50 local) picked up #1058** (`list windows --app` help says "application name or process name" but it also
> substring-matches the window title, overlapping `--window`) — `status:in-progress` @01:41Z, **no branch/PR yet** (fresh, <24h → not abandoned); honest-output/help-accuracy family.
> **Step 1:** **#1170 (`--ocr`) re-confirmed CONFLICTING/DIRTY**, auto-merge OFF; my 23:24Z [Orc] rebase-flag is still its latest actionable comment → did **NOT** re-comment (churn), did
> **NOT** merge/enable (public-API gate, guardrail). **#1171 (`--selector` default)** CLEAN, auto-merge OFF, public-CLI-default gate → untouched. #1167(dependabot)/#1055(community) base=
> `main` human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+2 live PR heads #1170/#1171; no orphans). **Step 2:**
> no handoff owed (#1184 QA-verified+closed); status:done open = **#972** only (human-only, parked); status:in-progress = **#1058**(fresh, no PR)+**#1175**(host-locale/clock bad-test fix,
> no PR, ~71 min — <24h not abandoned)+#1169/#1060(PRs held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog
> self-servicing (#1184 landed+verified, #1058 in flight) → **no new gap (Rule 9)**. Carried **watch-item**: success-side payload-builder drift (#886+#1184 = 2 instances) — still no 3rd
> recurrence → hold (speculative to file now). **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (QA's #1184 verify = the existing rules
> SUCCEEDING; #1058 in flight, no product/tests to audit; over-fit forbidden; self-review 6 principles < ~8 distillation threshold; EVOLUTION row appended; noted #1175-aging watch — one
> heartbeat <24h is not yet avoidance evidence). **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING+#1171 held public-API gates; #3 #766 in-progress; #4
> half-finished PRs #1170/#1171 + #1058/#1175 in flight) → **no auto-advance**. needs:ace UNCHANGED at 13. develop GREEN HEAD real-CI `6e91ddd` (#1188 Build&Test+CodeQL SUCCESS; orc
> `ec34429`/`dd358c6` `[skip ci]` on top). Evidence: `.work/reviews/2026-06-29-0952-auto-review.md`.)
> Since 0852Z: **two work signals, both rules SUCCEEDING.** **(1) QA @01:11Z VERIFIED+CLOSED #1180** (`verified`, against `3ffd8f6`) — the self-maintaining error-envelope **source
> guard** Orc itself filed (03:22Z) to kill the #884→#1172→#1179 truncated-`-j`-envelope regression class is now landed AND QA-confirmed end-to-end; the error-side output-contract
> surface is structurally guarded. **(2) Dev @01:24Z opened PR #1188** (`fix/issue-1184-find-selector-field`→develop, *fixes #1184*) — `find` now emits the reusable unified `app://`
> `selector` field that `see` already emits (restores the discover-then-`selector save` workflow). **Auto-merge ON (squash)** — correct: additive output-contract parity field (same
> class as #886/#1172/#1179), NOT new public surface, so the public-API guardrail correctly did NOT fire → self-lands when CI is green; currently BLOCKED only on in-flight CI (Lint/
> Version/Author green; Ubuntu/macOS/Win tests + C++ build + CodeQL pending). **Orc did NOT merge** (auto-merge is Dev's; guardrail). **Step 1:** **#1188** team PR auto-merge ON,
> MERGEABLE → self-lands, untouched. **#1170 (`--ocr`) STILL CONFLICTING/DIRTY** (collides with #1186+#1187 error-helper touches); my 23:24Z [Orc] rebase-flag is still its latest
> comment + actionable → did **NOT re-comment** (churn), did **NOT merge/enable** (public-API gate). #1171 (`--selector` default) CLEAN/MERGEABLE, auto-merge OFF, public-API gate →
> untouched. #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot
> +3 live PR heads #1170/#1171/#1188; no orphans). **Step 2:** no handoff owed (#1180 already QA-verified+closed); status:done open = **#972** only (human-only, parked); status:in-progress
> = **#1184**(PR #1188 in flight)+**#1175**(host-locale/clock bad-test fix, fresh 00:41Z)+#1169/#1060(PRs held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1).
> **Step 3:** criterion #1 stays FULLY MET; #1180 net landed+verified, #1184 success-side parity fix in flight → backlog converging, **no new gap (Rule 9)**. Logged a **watch-item**:
> success-side element-payload parity (#886 see/find/MCP all dropped `keyboardShortcut`; #1184 find omits `selector`) hints at a "parallel payload builders drift" theme = the success-side
> mirror of #1180's net — **holding** until #1188 lands + a clear 3rd recurrence (filing now = speculative churn; prior cycle already deliberated this). **Step 3.5:** NOT due (<7d;
> tracker current to 06-28). **Step 3.6: no change — no new evidence.** Both signals are the existing rules SUCCEEDING; **test-quality audit** sampled #1188's new
> `test_find_selector_field_1184.py` — **SOUND** (mocks at the `_get_backend` boundary not the selector-builder under test; asserts the actual `app://` selector + find↔see parity =
> BEHAVIOR not shape; lateral `--all`/`--role`/`--actionable` + CJK fixture names). Encoding a rule atop successful outcomes = over-fit (forbidden); self-review 6 principles < ~8
> distillation threshold; EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING+held + #1171 held public-API gates; #3 #766
> in-progress; #4 half-finished PRs #1170/#1171/#1188) → **no auto-advance**. needs:ace UNCHANGED at 13. develop GREEN HEAD real-CI `3ffd8f6` (#1187 Build&Test+CodeQL SUCCESS; orc
> `bd6a1c9` `[skip ci]` on top). **UPDATE (same cycle, ~01:28Z): PR #1188 went green and AUTO-MERGED to develop (`6e91ddd`, *fixes #1184*; full CI Build&Test+CodeQL SUCCESS;
> branch auto-deleted → Rule 14 clean, remote now main+develop+dependabot+2 live PR heads #1170/#1171).** Base=develop≠default → no auto-close, so Orc performed the on-merge handoff:
> flipped #1184 `status:in-progress`→`status:done` citing `6e91ddd` (Rule 1) + [Orc] comment asking QA to verify the find↔see `app://` selector parity (Python-serialization fix → no
> stale-DLL trap). status:done open now = **#1184**(fresh, awaiting QA)+#972(human-only). develop GREEN HEAD now `ec34429` (orc `[skip ci]` atop `6e91ddd`). Evidence:
> `.work/reviews/2026-06-29-0927-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~0852Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; the #1180 STRUCTURAL NET LANDED — Dev merged PR #1187 (`3ffd8f6`,
> *fixes #1180*), the self-maintaining error-envelope SOURCE GUARD that kills the #884→#1172→#1179 regression class. No Orc mutations to the wire; all guardrails held. needs:ace UNCHANGED at 13.**
> Since 0752Z: **one completed Dev cycle.** **Dev @00:33Z merged PR #1187** (`3ffd8f6`, *fixes #1180*) — an AST source-guard test (`tests/test_error_envelope_source_guard_1180.py`)
> that fails CI if any `naturo/cli/**` module outside `error_helpers.py` hand-rolls a `{"success": False, ...}` error literal, **plus the 6 CLI fixes it surfaced** (ai/config/snapshot/
> clipboard/diagnostics/lifecycle now route through the canonical `json_error`/`emit_error`). A new command physically cannot ship a truncated `-j` error envelope and pass CI. Full
> required CI GREEN (Build & Test + CodeQL on `3ffd8f6`); public-API guardrail correctly did NOT fire (test + internal routing, no new surface); **Dev did the complete on-merge handoff
> itself** (PR #1187 MERGED comment, set #1180 `status:done` @00:34Z, asked QA to verify) → **no Orc handoff owed.** **Step 1:** **#1170 (`--ocr`) STILL CONFLICTING/DIRTY** (now collides
> with #1186 AND #1187's error-helper touches) — my 23:24Z [Orc] rebase-flag is still #1170's latest comment + actionable → did **NOT re-comment** (churn), did **NOT merge/enable**
> (public-API gate, guardrail). #1171 (`--selector` default) re-confirmed **MERGEABLE/CLEAN**, auto-merge OFF, public-API gate → untouched. #1167(dependabot)/#1055(community) base=`main`
> human-only (Rule 2) → untouched. Nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (`fix/issue-1180-error-envelope-guard` auto-deleted on merge; remote = main+develop+dependabot+
> 2 live PR heads #1170/#1171). **Step 2:** no handoff owed (Dev set #1180 status:done); status:done open = **#1180**(fresh, awaiting QA)+**#972**(human-only, parked); status:in-progress =
> **#1175**(fresh Dev pick — the two host-locale/clock-dependent bad tests self-filed off #1174, updated 00:41Z)+#1169/#1060(PRs held)+#766(Ace umbrella) → none stale/abandoned; closed
> nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; #1180 landing closes the structural-net gap **Orc itself filed** (the #884→#1172→#1179 error-envelope regression class now has
> a source-level guard) → backlog converging, no new gap (Rule 9) — the MCP-tool error surface (#882 `isError`) is explicitly out of #1180's scope and shows no recent drift, so a symmetric
> guard now would be speculative churn. **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence.** The one completed cycle (#1180/#1187) is the existing
> rules SUCCEEDING with an **exemplary** test: `test_no_handrolled_error_envelopes_in_cli` AST-scans real source (BEHAVIOR not shape) paired with `test_guard_detects_a_synthetic_handrolled_envelope`
> — a **positive control** that defeats the #1-risk vacuous-pass failure mode (a weakened detector would be caught) — plus a negative control (`success:True` must not trip). Test-quality
> audit SOUND; encoding a rule atop a successful outcome = over-fit (forbidden); self-review at 6 principles < ~8 distillation threshold; EVOLUTION row appended. **Step 3.7:** done-criteria
> 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING+held + #1171 held public-API gates; #3 #766 in-progress; #4 half-finished PRs — though #1180's net materially de-risks criterion #4's
> regression surface) → **no auto-advance**. needs:ace UNCHANGED at 13. develop GREEN HEAD real-CI `3ffd8f6` (#1187 Build&Test+CodeQL SUCCESS). Evidence:
> `.work/reviews/2026-06-29-0852-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~0752Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; the #1186 handoff COMPLETED end-to-end — QA
> verified+closed #1182 + #1183; clean no-Orc-mutation cycle. needs:ace UNCHANGED at 13.**
> Since 0722Z: **one completed cycle.** **QA @23:40Z VERIFIED+CLOSED #1182 + #1183** (PR #1186 `1c522f8`) — both per-code **BEHAVIOR**-asserted PASS:
> `find/click/type --selector` not-found now emits `category=session` + actionable `suggested_action` (parity with `SELECTOR_NOT_FOUND`); `INVALID_SELECTOR`→
> `category=validation`+hint (live runtime); `TREE_ERROR`→`category=automation`/`recoverable=True`+hint (registry); completeness guard `test_error_category_completeness_1101`
> + `test_error_envelope_884` green (76 passed); **lateral scan of all raw-string `_emit_error` codes confirmed all 6 registered** (no residual `category:"unknown"`
> gap); zero intrusive input. This completes the 0722Z on-merge handoff end-to-end. A **Dev cycle started 07:37 local**, in flight on **#1180** (structural net), no
> branch/PR yet (<24h → not abandoned). **Step 1:** **#1170 (`--ocr`) STILL CONFLICTING/DIRTY** (collides with #1186's error-registry touch) — my 23:24Z [Orc]
> rebase-flag is the latest comment + actionable → did **NOT re-comment** (churn), did **NOT merge/enable** (public-API gate, guardrail). #1171 (`--selector` default)
> CLEAN/MERGEABLE, auto-merge OFF, public-API gate → untouched. #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched. Nothing merged/closed BY
> Orc (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+2 live PR heads #1170/#1171). **Step 2:** no handoff owed (QA already verified+closed #1182/#1183);
> status:done open = **#972** only (human-only, parked); status:in-progress = **#1180**(fresh)+#1169/#1060(PRs held)+#766(Ace umbrella) → none stale/abandoned; closed
> nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; #1182/#1183 closed the last reported `find --selector` envelope-category gaps and #1180 (the structural net
> that kills the #884→#1172→#1179 regression class) is in flight → no new gap (Rule 9) — QA's #871 app-verb/`--app-id` targeting gap already re-verified+extended on-issue,
> not a dup. **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence.** The one completed cycle (QA's #1182/#1183 verify) is the
> existing rules SUCCEEDING — specifically the dev-cycle **"Error-code registration"** self-review principle (the #1086 eN-resolve evidence) is exactly what #1186 fixed
> and QA confirmed end-to-end with per-code BEHAVIOR assertions + a registered-code completeness scan; encoding a rule atop a rule that just worked = over-fit (forbidden).
> No new tests this heartbeat to sample (verify-only; #1186's per-code behavior tests already audited sound at 0722Z); self-review at **6 principles** (parity/attribution/
> registration/option-coverage/validation-order/hermeticity) **< ~8 distillation threshold**; EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion
> #1 ✅; #2 #1170 CONFLICTING+held + #1171 held public-API gates, #1180 in flight; #3 #766 in-progress; #4 half-finished PRs) → **no auto-advance**. needs:ace UNCHANGED at
> 13. develop GREEN HEAD real-CI `1c522f8` (#1186 Build&Test+CodeQL SUCCESS; orc `1b41632` `[skip ci]` on top). Evidence: `.work/reviews/2026-06-29-0752-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~0722Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; one Dev fix landed end-to-end — #1186 closed the
> `find --selector` error-envelope-category gaps (#1182+#1183), and the 0652Z watch-item resolved as the rules SUCCEEDING. No Orc mutations to the wire beyond an
> [Orc] rebase-flag on #1170. needs:ace UNCHANGED at 13.**
> Since 0652Z: **two completed cycles.** **(1) Dev @23:08Z merged PR #1186** (`1c522f8`, *fixes #1182 + #1183*) — promotes `SELECTOR_REF_ERROR`(session)/`INVALID_SELECTOR`
> (validation)/`TREE_ERROR`(automation,recoverable) to real `ErrorCode` members registered in `_ERROR_CATEGORIES`/`_RECOVERY_HINTS`, ending the `category:"unknown"`+null
> `suggested_action` degradation on `find --selector` error envelopes (#884→#1101 class). +173/-0 (`naturo/errors.py` + `naturo/cli/error_helpers.py` + one test file); full
> required CI GREEN (Build & Test + CodeQL on `1c522f8`); public-API guardrail correctly did NOT fire (#1101 class — codes already emitted as raw strings, only metadata
> corrected → `--auto` appropriate). **Dev did the complete on-merge handoff itself** (set both status:done, cited `1c522f8`, asked QA to verify) → **no Orc handoff owed.**
> **(2) QA @07:10Z exploratory** — develop GREEN reconfirmed; live Notepad UIA recognition pass (cascade 44/cov 0.893, no mojibake, `find --image` 1.0); **re-verified+extended
> #871** (targeting-flag matrix: all 8 app window verbs + get/set `--pid` still lack `--app-id` though `app list` advertises IDs — re-verify comment, no dup); #972 parked;
> 0 new bugs, zero intrusive input. **Step 1:** **#1170 (`--ocr`) went CONFLICTING** (#1186's registry touch collides with #1170's `OCR_NOT_AVAILABLE`/`OCR_FAILED` adds) →
> posted **[Orc] rebase-flag** so it doesn't rot; still a public-API gate, auto-merge OFF → **Orc did NOT merge / did NOT enable** (guardrail). #1171 (`--selector` default)
> MERGEABLE/CLEAN, auto-merge OFF, public-API gate → untouched. #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc
> (Rule 1); **Rule 14 clean** (#1186 branch auto-deleted; remote = main+develop+dependabot+2 live PR heads #1170/#1171). **Step 2:** no handoff owed (Dev completed the
> #1182/#1183 handoff @23:08Z); status:done open = **#1182**+**#1183**(fresh, awaiting QA)+**#972**(human-only, parked); status:in-progress = **#1180**(self-maintaining
> error-envelope contract test — fresh Dev pick, 23:13Z)+#1169/#1060(PRs held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1
> stays FULLY MET; #1186 closed the #1182/#1183 category-registration gaps and #1180 (the structural net that kills the whole #884→#1172→#1179 regression class) is now in
> flight → no new gap (Rule 9). **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — 0652Z watch-item RESOLVED as the rules SUCCEEDING** — Dev's
> first-ever two-issues-in-progress-at-once (#1182+#1183) landed as **ONE coherent registry fix** (one root cause, one test file with per-code BEHAVIOR assertions: concrete
> non-UNKNOWN category + non-null/non-empty `suggested_action` + correct `recoverable` + end-to-end CLI envelopes), the justified shared-root-cause exception not Rule-5
> sprawl; encoding a rule on a successful outcome = over-fit (forbidden); test-quality audit SOUND; self-review 5–6 principles < ~8 distillation threshold; EVOLUTION row
> appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170 CONFLICTING+held + #1171 held public-API gates, #1180 in flight; #3 #766 in-progress; #4
> half-finished PRs) → **no auto-advance**. needs:ace UNCHANGED at 13. develop GREEN HEAD real-CI `1c522f8` (#1186 Build&Test+CodeQL SUCCESS). Evidence:
> `.work/reviews/2026-06-29-0722-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~0652Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; clean no-change heartbeat — nothing merged/closed/verified
> since 0622Z; no Orc mutations to the wire; all guardrails held. needs:ace UNCHANGED at 13.**
> Since 0622Z: **zero Dev/QA cycles completed** — develop HEAD unchanged at real-CI `ad24c38` (#1185 Build&Test+CodeQL SUCCESS; orc `f1bcd4e` `[skip ci]` on top). A **Dev
> cycle started 06:37Z** and is **still in flight** on the error-envelope-category backlog (#1182 + #1183, both `status:in-progress`, **no branch/PR yet** — fresh picks,
> well within 24h → not abandoned). **Step 1:** team PRs #1170(`--ocr`)/#1171(`--selector` default) re-confirmed **MERGEABLE/CLEAN, autoMerge OFF** — public-API human gates
> → **Orc did NOT merge / did NOT enable** (guardrail); #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1);
> **Rule 14 clean** (remote = main+develop+dependabot+2 live PR heads #1170/#1171; no orphans). **Step 2:** status:done open = **#972** only (human-only, parked) → no handoff
> owed (#1179 already QA-closed @06:10Z last run); status:in-progress = **#1182**+**#1183**(fresh Dev picks, no branch)+#1169/#1060(PRs held)+#766(Ace umbrella) → none
> stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog actively self-serviced (Dev in flight on #1182/#1183; #1184 backlog; #1180 net
> open) → no new gap (Rule 9). **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** — the 0622Z watch-item (Dev's first-ever
> two-issues-in-progress-at-once #1182+#1183: one coherent registry fix vs Rule-5 sprawl?) **remains unresolved** (still no PR, no product to audit) → keep it open, re-check
> when the PR lands; acting now would over-fit an outcome-unknown incident (forbidden). No new tests authored → nothing to sample; self-review 5–6 principles < ~8 distillation
> threshold; EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170/#1171 PR-held gates + #1182/#1183/#1184 in-flight/backlog; #3 #766
> in-progress; #4 half-finished PRs) → **no auto-advance**. needs:ace UNCHANGED at 13. develop GREEN HEAD real-CI `ad24c38` (orc `[skip ci]` on top). Evidence:
> `.work/reviews/2026-06-29-0652-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~0622Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; clean no-change heartbeat with one exemplary completed
> product — QA verified+closed #1179 end-to-end since 0552Z; no Orc mutations to the wire; all guardrails held. needs:ace UNCHANGED at 13.**
> Since 0552Z: **(1) QA @06:10Z VERIFIED+CLOSED #1179** (`find --ai` error JSON dropped 4/6 #884 envelope keys) — a textbook **behavior** verify: real first-run path
> `find "…" --ai --json` (no API key) now emits all six #884 keys with `suggested_action` = the API-key hint the hand-rolled `json.dumps` had dropped; all 3 codes route
> through `_json_error_str`; old unregistered `AI_FIND_FAILED` no longer emitted. Lateral find-error-envelope sweep (--image/--image+--ai/--selector+query/--ocr) all clean,
> area already covered by open #1183/#1184 (no false re-file); ruled out 2 own-harness false-alarms (--image arg-eating, MSYS `//` mangling) before filing; zero intrusive
> input. This completes the 0552Z on-merge handoff end-to-end. **(2) Dev cycle (started 06:07Z) picked up #1182 + #1183** — both fresh `status:in-progress` @06:12Z, no
> branch yet (<24h → not abandoned); identical root cause (error codes unregistered in `_ERROR_CATEGORIES`/`_RECOVERY_HINTS` → `category:"unknown"` + null `suggested_action`
> — the #1180 structural-net target). **Step 1:** team PRs #1170(`--ocr`)/#1171(`--selector` default) re-confirmed MERGEABLE/CLEAN, **autoMerge OFF** — public-API human
> gates → **Orc did NOT merge / did NOT enable** (guardrail); #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc
> (Rule 1); **Rule 14 clean** (remote = main+develop+dependabot+2 live PR heads #1170/#1171; no orphans). **Step 2:** status:done open = **#972** only (human-only, parked);
> **#1179 already QA-closed → no handoff owed**; status:in-progress = **#1182**+**#1183**(fresh Dev picks)+#1169/#1060(PRs held)+#766(Ace umbrella) → none stale/abandoned;
> closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; backlog actively self-serviced (Dev on #1182/#1183 error-envelope-category class; #1184 backlog; #1180
> net open) → no new gap (Rule 9). **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence (one watch-item logged, not encoded):**
> the one completed product (QA's #1179 verify) = rules SUCCEEDING; Dev's #1182/#1183 in-flight (no PR, no product to audit); the novel signal — Dev set **two** issues
> in-progress at once (#1182+#1183, identical registry root cause) — is a **first** (not recurring) and plausibly a legitimate single fix, so encoding a Rule-5 rule on an
> in-flight outcome-unknown incident = over-fit (forbidden); logged as a watch-item to verify the resulting PR is one coherent registry fix with discriminating tests for
> both codes; self-review 5–6 principles < ~8 distillation threshold; EVOLUTION row appended. **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170/#1171
> PR-held gates + #1182/#1183/#1184 in-flight/backlog; #3 #766 in-progress; #4 half-finished PRs) → **no auto-advance**. needs:ace UNCHANGED at 13. develop GREEN HEAD
> real-CI `ad24c38` (#1185 Build&Test+CodeQL SUCCESS; orc `ff8c950` [skip ci] on top). Evidence: `.work/reviews/2026-06-29-0622-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~0552Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; the 6th #884 output-contract gap landed — Dev shipped+merged
> #1179's fix (PR #1185), Orc performed the on-merge handoff. needs:ace UNCHANGED at 13.**
> Since 0524Z: **two completed cycles, both exemplary.** **(1) Dev @05:49Z shipped+auto-merged PR #1185** (`ad24c38`, *fixes #1179* — `find --ai` error JSON dropped
> 4/6 #884 keys via a hand-rolled `json.dumps`): routed through the canonical `_json_error_str` envelope with *registered* codes (`AI_ANALYSIS_FAILED`/
> `AI_PROVIDER_UNAVAILABLE`/`CAPTURE_FAILED`, retiring off-taxonomy `AI_FIND_FAILED`→`unknown`), so category/`suggested_action`/`recoverable`/`context` now resolve and the
> API-key hint reaches the user; **public-API guardrail correctly did NOT fire** (restoring an existing #884 contract = bug fix, no new surface → auto-merge ON, same class
> as #1172/#1181). Full required CI GREEN (Build & Test + CodeQL on `ad24c38`). **(2) QA @05:42Z** ran a non-intrusive recognition live-verify (Notepad UIA cascade 44
> elems/cov 0.893 WORKING), **PASS-no-close on human-only #972**, **ruled out a cp936-console mojibake harness false-alarm** (checked on-disk UTF-8 bytes), filed genuine
> root-caused **#1184** (`find` JSON omits the reusable `selector` field `see` emits — output-contract family, Dev-actionable), **zero keystrokes**. **Step 1:** team PRs
> #1170(`--ocr`)/#1171(`--selector` default) re-confirmed public-API human gates, auto-merge OFF → **Orc did NOT merge / did NOT enable** (guardrail); #1167(dependabot)/
> #1055(community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (#1185 branch `fix/issue-1179-ai-error-envelope`
> auto-deleted on merge; remote = main+develop+dependabot+2 live PR heads #1170/#1171; no orphans). **Step 2 handoff:** PR #1185 base=`develop`≠default → no auto-close, so
> Orc **flipped #1179 `status:in-progress`→`status:done`** citing `ad24c38` (Rule 1) + [Orc] note asking QA to verify the six-key envelope (esp. `suggested_action`) on a
> failing `find --ai` path, no-DLL so stale-DLL trap N/A. status:done open now = **#1179**(fresh, awaiting QA)+**#972**(human-only, parked); status:in-progress = #1169/#1060
> (Dev PRs held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays FULLY MET; #1179 closes the 6th output-contract-fidelity
> gap of the run (after #1173/#886/#1159/#1172); structural net #1180 already filed; QA's #1184 is the success-side instance (Dev backlog) → backlog sharp, no new gap (Rule 9).
> **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (two completed cycles, both the existing rules SUCCEEDING — Dev's #1185
> behavior-asserting test [six keys AND category-resolves AND `suggested_action` non-empty AND message content, fails on old 2-key shape; not over-mocked/tautological; sibling
> #894 CJK test correctly updated `AI_FIND_FAILED`→`AI_ANALYSIS_FAILED`] + correct public-API non-trigger; QA's read-only verify + anti-false discipline + zero intrusive input;
> test-quality audit SOUND; encoding a rule atop the #1180-covered class = over-fit, forbidden; self-review 5–6 principles < ~8 distillation threshold; EVOLUTION row appended).
> **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170/#1171 PR-held gates + #1060/#1169 in-flight, #1179 awaiting QA; #3 #766 in-progress; #4 half-finished
> PRs) → **no auto-advance**. needs:ace UNCHANGED at 13 (#1179/#1180/#1184 are Dev-actionable, not human gates). develop GREEN HEAD real-CI `ad24c38` (#1185 Build&Test+CodeQL
> SUCCESS; orc [skip ci] on top). Evidence: `.work/reviews/2026-06-29-0552-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~0524Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; clean no-change heartbeat — nothing merged/closed/verified
> since 0453Z; no Orc mutations to the wire; all guardrails held. needs:ace UNCHANGED at 13.**
> Since 0453Z: **zero Dev/QA cycles completed** — no new merge, no new verify, no new loop-state marker past QA's 04:10Z #1172 entry. Dev's **#1179** (`find --ai`
> error JSON drops 4 of 6 #884 envelope keys) remains `status:in-progress` with **no PR branch yet** (fresh pick, well within 24h → not abandoned). **Step 1:** team
> PRs #1170(`--ocr`)/#1171(`--selector` default) re-confirmed public-API human gates, auto-merge OFF → **Orc did NOT merge / did NOT enable** (guardrail);
> #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+develop+
> dependabot+2 live PR heads #1170/#1171; no orphans). **Step 2:** status:done open = **#972** only (human-only, parked) — no handoff owed (#1172 already QA-closed
> last cycle); status:in-progress = **#1179**(fresh, no PR)+#1169/#1060(Dev PRs held)+#766(Ace umbrella) → none stale/abandoned; closed nothing (Rule 1). **Step 3:**
> criterion #1 stays FULLY MET; backlog sharp (6 output-contract-fidelity gaps self-serviced this run; structural net #1180 already filed) → no new gap (Rule 9).
> **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (zero completed cycles this heartbeat → no product to audit, no new
> tests to sample; freshest rules just succeeded last cycle = validation not gap; over-fit forbidden; self-review 5–6 principles < ~8 distillation threshold;
> EVOLUTION row appended). **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170/#1171 PR-held gates + #1060/#1169 + #1179 in-flight; #3 #766
> in-progress; #4 half-finished PRs) → **no auto-advance**. develop GREEN HEAD real-CI `e087c64` (#1181 Build&Test+CodeQL SUCCESS; orc [skip ci] on top). Evidence:
> `.work/reviews/2026-06-29-0524-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~0453Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; the #1172 fix is now QA-VERIFIED+CLOSED
> end-to-end, and Dev has picked up the next envelope-fidelity gap (#1179). No Orc mutations to the wire; all guardrails held. needs:ace UNCHANGED at 13.**
> Since 03:52Z: **(1) QA @04:08Z VERIFIED+CLOSED #1172** (saved-selector not-found leaked `KeyError`'s repr quotes into the envelope `message`) — a textbook
> **behavior** verify (QA-Mariana): ran each consumer on the clean path (direct invocation, JSON-to-file, the saved-selector resolver) and confirmed the user
> message no longer carries the repr quotes, cited the merged `e087c64` (Rule 1), zero keystrokes; the fix is message-only (no DLL) so the 01:22Z stale-DLL trap
> was correctly N/A. This completes the 03:52Z on-merge handoff (Orc flip→status:done + [Orc] ask) end-to-end. **(2) Dev @04:12Z picked up #1179** (`find --ai`
> error JSON drops 4 of 6 #884 envelope keys — hand-rolled `json.dumps` bypassing `json_error()`) → `status:in-progress`, **fresh (no PR yet), not abandoned**;
> this is the QA-filed gap from the 03:22Z cycle now in Dev's hands (hardest-first on the output-contract fidelity class). **Step 1:** team PRs #1170(`--ocr`)/
> #1171(`--selector` default) re-confirmed CLEAN/MERGEABLE, **autoMerge OFF**, public-API human gates → **Orc did NOT merge / did NOT enable** (guardrail);
> #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1); **Rule 14 clean** (remote = main+
> develop+dependabot+2 live PR heads #1170/#1171; #1181 branch deleted on merge last cycle — no orphans). **Step 2:** status:done open = **#972** only (human-only,
> parked); **#1172 QA-verified+closed → no handoff owed**; status:in-progress = **#1179**(fresh Dev pick)+#1169/#1060(Dev PRs held)+#766(Ace umbrella) → none
> stale/abandoned; closed nothing (Rule 1). **Step 3:** criterion #1 stays complete; #1179 in flight closes the 6th output-contract-fidelity gap of the run (after
> #1173/#886/#1159/#1172) and the **structural net is already filed (#1180** — self-maintaining error-envelope contract test) → backlog sharp, no new gap (Rule 9).
> **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (one completed work product = QA's #1172 behavior verify, the
> existing rules SUCCEEDING; stale-DLL trap correctly N/A on a no-DLL fix; Dev's #1179 still in-flight, no product to audit; verify-only cycle → no new tests to
> sample; self-review 5–6 principles < ~8 distillation threshold; over-fit forbidden; EVOLUTION row appended). **Step 3.7:** done-criteria 1–4 NOT all met
> (criterion #1 ✅; #2 #1170/#1171 PR-held human gates + #1060/#1169 + #1179 in-flight; #3 #766 in-progress; #4 half-finished PRs) → **no auto-advance**. needs:ace
> UNCHANGED at 13. develop GREEN HEAD real-CI `e087c64` (#1181 Build&Test+CodeQL SUCCESS; orc `c7a0784`/`1d7c8e7` [skip ci] on top). Evidence:
> `.work/reviews/2026-06-29-0453-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~03:52Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; the #1172 fix is now in flight — Dev opened PR #1181
> (auto-merge ON, lands itself when green); QA closed #1159 end-to-end. needs:ace UNCHANGED at 13.**
> Since 03:22Z: **(1) QA @03:42Z VERIFIED+CLOSED #1159** (non-codepage window-title corruption) — an exemplary exercise of the 01:22Z stale-DLL trap: deployed the
> canonical CI-built DLL (`f2979d9`, 130048 B) from the merged #1178 run, kept the stale pre-#1159 binary as a **discriminating negative control** (pre-fix `✳→?`/
> `😀→??`; post-fix raw bytes `e29cb3`+`f09f9880` lossless ⇒ effect is the fix not env; astral 4-byte survival proves the wide-API+UTF-8 path), lateral-checked
> list/app windows all lossless, cited merged `2ec4dbc` (Rule 1), zero keystrokes. **(2) Dev @03:50Z opened PR #1181** (`fix/issue-1172-selector-keyerror-quotes`→
> develop, *fixes #1172* — saved-selector not-found leaked `KeyError`'s repr quotes into the envelope `message`) with **auto-merge ON (SQUASH)** — correct, because the
> fix is **message-only** (new `SelectorNotFoundError` = `KeyError` subclass whose `__str__` drops the repr quotes; the error CODE `SELECTOR_REF_ERROR`/category/six-key
> #884 envelope all unchanged, every `except KeyError` caller still works), so the **public-API guardrail correctly did NOT fire** → Dev let it self-land. Currently
> **BLOCKED only on in-flight CI** (Ubuntu/Windows-DLL/lint/version/commit-author all green; macOS 3.9/3.12/3.13 + Analyze c-cpp pending) → lands itself when green;
> **Orc did NOT merge** (guardrail — auto-merge is already Dev's). New test `TestSelectorNotFoundMessageNoQuoteLeak1172` asserts the clean message across resolver+find+
> click/type (BEHAVIOR not shape); fresh-context adversarial verifier PASS. **Step 1:** team PRs #1170(`--ocr`)/#1171(`--selector` default) re-confirmed CLEAN, public-API
> human gates, auto-merge OFF → Orc did NOT merge/enable (guardrail); #1181 auto-merge ON by Dev (message-only, not a public gate) → left to self-land; #1167(dependabot)/
> #1055(community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1); Rule 14 clean (remote = main+develop+dependabot+3 live PR heads
> #1170/#1171/#1181; #1178 branch deleted on merge last cycle). **Step 2:** no handoff owed (QA already closed #1159; #1181 not yet merged → #1172 stays
> `status:in-progress`, flip deferred to merge per dev-cycle handoff). status:done open = **#972** only (human-only, parked). status:in-progress = **#1172**(PR #1181
> auto-merge pending)+#1169/#1060(Dev PRs held)+#766(Ace umbrella) → none stale/abandoned. **Step 3:** criterion #1 stays complete; #1172's fix in flight closes the
> 5th output-contract fidelity gap of the run (after #1173/#886/#1159/#1179), and the **structural net is already filed (#1180** — self-maintaining error-envelope
> contract test) → backlog sharp, no new gap (Rule 9). **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (two completed
> cycles both rules SUCCEEDING: Dev's #1181 correct message-only fix + public-API non-trigger + behavior-asserting test + auto-merge-ON discernment; QA's #1159 verify =
> the freshest rule [01:22Z stale-DLL trap] exercised cleanly a **3rd time on a 3rd native fix class** [JAB→UIA→window-title] = validation not gap; test-quality audit —
> #1181's new test asserts the message TEXT [behavior, not envelope shape], not tautological/over-mocked, sound; self-review 5 questions < ~8 distillation threshold;
> over-fit forbidden; EVOLUTION row appended). **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170/#1171 PR-held human gates + #1060; #3 #766
> in-progress; #4 half-finished PRs) → **no auto-advance**. needs:ace UNCHANGED at 13 (#1172/#1180/#1179 are Dev-actionable, not human gates). develop GREEN HEAD
> `2ec4dbc` (#1178 Build&Test+CodeQL SUCCESS, real CI; `f61f6ec` orc [skip ci] on top). **UPDATE (same cycle, ~03:55Z): #1181's pending CI went GREEN and it
> AUTO-MERGED to develop (`e087c64`, *fixes #1172*); branch auto-deleted (Rule 14 clean — remote now main+develop+dependabot+2 live PR heads #1170/#1171). Base=
> develop≠default → no auto-close, so Orc performed the on-merge handoff: flipped #1172 `status:in-progress`→`status:done` citing `e087c64` (Rule 1) + [Orc] comment
> for QA to verify the clean message then close. status:done open now = #1172(fresh, awaiting QA)+#972(human-only). develop GREEN HEAD now `c7a0784` (orc [skip ci]
> atop `e087c64`).** Evidence: `.work/reviews/2026-06-29-0352-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~03:22Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; a 4th consecutive recognition-fidelity
> native-core data-loss bug self-serviced — Dev shipped+merged #1159 since 02:52Z; criterion #1 stays FULLY MET. Orc filed one sharp structural gap (#1180).**
> Since 02:52Z: **Dev @02:57Z merged PR #1178** (`fix/issue-1159-wide-window-title`→develop, `2ec4dbc`, *fixes #1159*) — non-codepage window titles
> (emoji/cross-script) were `?`-mangled by the narrow `GetWindowTextA`/`QueryFullProcessImageNameA` ANSI read path in `core/src/window.cpp` (irreversible
> data loss before Python sees the bytes). Fix switches all three narrow read sites to wide `…W` + a new `wide_to_utf8()` in one sweep (no sibling leak;
> Python bridge already UTF-8-decodes per #1150); **public-API guardrail correctly did NOT fire** (data-loss fix on an already-emitted field = bug, no new
> surface); the new `@pytest.mark.desktop` test is exemplary (title built from **explicit code points** to dodge the PowerShell-ANSI-decode confounder,
> ASCII per-PID marker, distinct UTF-8 widths, **fails on pre-fix DLL = BEHAVIOR not shape**). Full required CI GREEN, branch auto-deleted. **QA @03:11Z**
> (read-only) filed **#1179** (`find --ai` error JSON drops 4 of 6 #884 envelope keys — hand-rolled `json.dumps` bypassing `json_error()`), correctly did
> NOT re-file the already-tracked #1172, zero intrusive input. **Step 1:** team PRs #1170(`--ocr`)/#1171(`--selector` default) re-confirmed public-API human
> gates, auto-merge OFF → **Orc did NOT merge/enable** (guardrail); #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched; nothing
> merged/closed BY Orc (Rule 1); Rule 14 clean (remote=main+develop+dependabot+2 live PR heads; #1178 branch deleted on merge). **Step 2 handoff:** **flipped
> #1159 `status:in-progress`→`status:done`** (PR base=develop ≠ default → no auto-close; merged `2ec4dbc` cited, Rule 1) — QA cycle picks it up. status:done
> open = **#1159**(fresh) + **#972**(human-only, parked). status:in-progress = **#1172**(fresh Dev pick) + #1169/#1060(Dev PRs held) + #766(Ace) → none
> stale/abandoned. **Step 3:** criterion #1 stays complete; #1159 closed a 4th native-core recognition-fidelity data-loss gap (after #1173/#886); **GAP FILED
> #1180** (tech-debt/P2/v0.3.4) — self-maintaining ERROR-envelope contract test (#884 unified the 6-key error envelope but left no structural guard → #1172/
> #1179 re-regress it; mirror the #979/#987 success-side Click-tree-walking contract for the error side, test-only, Dev-actionable). **Step 3.5:** NOT due
> (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (two completed cycles both rules SUCCEEDING — Dev's hardest-first #1159 native
> fix with exemplary discriminating test + correct public-API non-trigger; QA's read-only #1179 with no re-file/no intrusive input; the only structural
> signal is a *product* coverage gap → Step-3 action #1180, not a Step-3.6 doc edit; freshest rule [01:22Z stale-DLL trap] <8h old; self-review 5 questions <
> ~8 distillation threshold; over-fit forbidden; EVOLUTION row appended). **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170/#1171 PR-held
> human gates + #1060; #3 #766 in-progress; #4 half-finished PRs) → **no auto-advance**. needs:ace UNCHANGED at 13 (#1179/#1180 are Dev-actionable, not human
> gates). develop GREEN HEAD `2ec4dbc` (#1178 Build&Test+CodeQL SUCCESS, real CI). Evidence: `.work/reviews/2026-06-29-0322-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~02:52Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; the recognition-fidelity bug Dev shipped
> last cycle is now QA-VERIFIED+CLOSED end-to-end — #886 closed @02:45Z with a discriminating negative control; criterion #1 stays FULLY MET.**
> Since 02:22Z: **QA @02:45Z VERIFIED+CLOSED #886** (`keyboardShortcut` UIA AcceleratorKey/AccessKey null) — a textbook exercise of the 01:22Z
> stale-DLL trap: #886 is a `core/` native fix, so QA **deployed the canonical CI-built `naturo_core.dll` (129024 B) from the merged Build&Test run**
> (artifact `naturo-core-dll`), rejecting the worktree's stale untracked binary (124928 B), then ran a **discriminating negative control** (same window
> + `--backend uia`, swapped ONLY the DLL → pre-fix 43 nodes/0 populated; fix 43 nodes/15 populated — identical node count ⇒ effect is the fix not env)
> + a **lateral check on the persisted uiMap** (the issue's original repro vector also honors the fix: 15 vs 0). Cited merged `111031a` (Rule 1), added
> `verified`, closed #886, left human-only #972 parked. Read-only `see`, **zero keystrokes**. Meanwhile **Dev @02:37Z picked up #1159** (P2 from:qa —
> non-codepage window titles [emoji/cross-script] corrupted to `?` via the ANSI A-API read path in native core; a recognition-fidelity data-loss
> lateral to #1150) → `status:in-progress` set ~11min ago, no PR yet, **fresh not abandoned**. **Step 1:** team PRs #1170(`--ocr`)/#1171(`--selector`
> default) re-confirmed **MERGEABLE/CLEAN**, public-API human gates, auto-merge OFF → **Orc did NOT merge / did NOT enable** (guardrail); #1167(dependabot)/
> #1055(community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1); remote = main+develop+dependabot+2 live PR heads
> (#1170/#1171) → Rule 14 clean (#886 branch deleted by Dev on merge last cycle). **Step 2:** no handoff owed (QA already closed #886). status:done open =
> **#972** only (human-only, parked). status:in-progress = #1169/#1060 (Dev PRs held) + **#1159** (fresh Dev pick) + #766 (Ace umbrella) → none stale/abandoned.
> **Step 3:** criterion #1 stays complete; #886 closes the UIA output-fidelity gap; Dev is on another recognition-fidelity data-loss bug (#1159) hardest-
> first → backlog sharp, no new gap filed (Rule 9). **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (one
> completed cycle since 02:22Z = QA's #886 verify, which is the freshest rule [01:22Z stale-DLL trap, <1.5h old] SUCCEEDING on a *second, different* native
> fix class [#886 UIA vs its originating #1096 JAB] — validation, not a gap; encoding a rule atop a rule that just worked is the over-fit Step 3.6 forbids;
> no new tests this cycle [verify-only]; self-review at 6 principles < ~8 distillation threshold; EVOLUTION row appended). **Step 3.7:** done-criteria 1–4
> NOT all met (criterion #1 ✅; #2 #1170/#1171 PR-held human gates; #3 #766 in-progress; #4 half-finished PRs) → **no auto-advance**. needs:ace UNCHANGED
> at 13. develop GREEN HEAD `2e5d85f` (orc [skip ci] atop `111031a` #1177 Build&Test+CodeQL SUCCESS @18:22Z, real CI). Evidence:
> `.work/reviews/2026-06-29-0252-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~02:22Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; another recognition-fidelity bug
> self-serviced end-to-end — Dev shipped + merged #886 (`keyboardShortcut` UIA null) since 01:52Z; criterion #1 stays FULLY MET.**
> Since 01:52Z: **Dev merged PR #1177** (`fix/issue-886-uia-keyboard-shortcut`→develop, `111031a`, *fixes #886*) — the UIA C++ backend
> (`core/src/element.cpp`) never queried `UIA_AcceleratorKey/AccessKeyPropertyId`, so `keyboardShortcut` was 100% null (a SOUL "Never Lie"/
> silent-output-contract gap across 87k records). Fix adds a shared `read_keyboard_shortcut()` (AcceleratorKey→AccessKey→null) emitted in the
> cached tree, Current-fallback, AND `naturo_find_element` paths, BSTRs NULL-guarded/freed; **swept the sibling MCP `_snapshot.py` uiMap builder**
> that dropped the same field (recurring-class closure across UIA see/find + MCP). **FULL required CI GREEN** (`111031a` Build & Test + CodeQL
> SUCCESS @18:22Z), Step-3.5 adversarial verifier PASS with a discriminating negative control (pre-fix DLL → all 4 fixture buttons null = bug
> reproduced; post-fix → populated), public-API guardrail correctly NOT triggered (populating an ALREADY-documented field = bug fix, no new
> surface). Dev re-proved the native build (MSVC 14.44 + CMake) and flipped **#886 → `status:done`** on merge (awaiting QA; PR base develop ≠
> default branch → no auto-close, Rule 1 preserved) — **no Orc handoff owed.** **QA @02:15Z VERIFIED #972** (P0 input-safety guard, function-level,
> zero live keystrokes; left for Ace sign-off, did NOT close) + a live recognition pass (Notepad 44 elements, Chinese UI no mojibake) and **caught
> a harness-lie** (MSYS `//`→`/` arg mangling) → filed nothing false, zero intrusive input. **Step 1:** team PRs #1170(`--ocr`)/#1171(`--selector`
> default) base=develop, public-API human gates, auto-merge OFF → **Orc did NOT merge / did NOT enable** (guardrail); #1167(dependabot)/#1055
> (community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1); remote = main+develop+dependabot+2 live PR heads
> (#1170/#1171) → Rule 14 clean (#886 branch deleted by Dev, confirmed gone). **Step 2:** no handoff owed (Dev set #886 status:done; QA already
> verified #972). status:done open = **#972** (human-only, parked) + **#886** (fresh, awaiting QA — QA cycle will pick up). status:in-progress =
> #1169/#1060 (Dev PRs held) + #766 (Ace umbrella) → none stale/abandoned. **Step 3:** criterion #1 complete; #886 closed a Never-Lie recognition-
> fidelity gap; backlog sharp, Dev cleared the v0.3.2 hermetic queue and is pulling v0.3.4 hardest-first → no new gap filed (Rule 9). **Step 3.5:**
> NOT due (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (two completed cycles since 01:52Z, both the existing rules
> SUCCEEDING: Dev's hardest-first #886 pick over an easy additive win + Step-3.5 negative-control verifier that FOUND+fixed the MCP sibling-leak +
> correct public-API non-trigger; QA's clean #972 verify + caught harness-lie + zero false/zero intrusive input; test-quality audit — #886's desktop
> test [owned WPF fixture, FAILS on pre-fix DLL = BEHAVIOR not shape, discriminating] + hermetic MCP test [mocked at the snapshot-builder carrier
> boundary, not the field] are sound; the one harness-lie QA hit is the already-encoded msys-double-slash class → over-fit forbidden; self-review at
> 6 principles < ~8 distillation threshold; EVOLUTION row appended). **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170/#1171 PR-
> held human gates; #3 #766 in-progress; #4 half-finished PRs) → **no auto-advance**. needs:ace UNCHANGED at 13. develop GREEN HEAD `111031a`
> (Build&Test+CodeQL SUCCESS, real CI). NEEDS-ACE.md header stack trimmed (~375→lean). Evidence: `.work/reviews/2026-06-29-0222-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~01:52Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; v0.3.2 find-engine quality
> tightened — Dev shipped + QA verified #1173 (`find --limit` validation) since 01:22Z; recognition-moat criterion #1 stays FULLY MET.**
> Since 01:22Z: **Dev merged PR #1176** (`fix/issue-1173-limit-validation`→develop, `54e4ba6`, *fixes #1173*) — centralised `--limit >= 1`
> validation up front (platform-invariant, before the GUI gate; emits the existing INVALID_INPUT envelope), killing the silent
> `success:true/count:0` on non-positive `--limit` (the `[:limit]`-slice-from-end silently-wrong path); full required CI matrix GREEN,
> Step-3.5 adversarial verifier PASS, public-API guardrail correctly NOT triggered (tightening an existing flag = bug fix, no new surface).
> **QA @01:40Z VERIFIED+CLOSED #1173** (evidence table: `--limit 0/-3/-100` → rc1 INVALID_INPUT, inclusive boundary `--limit 1` accepted,
> parity with `--depth -5`) and **lateral-audited the full find numeric-param family** (depth/limit/threshold) → all sound, **filed nothing
> false**, zero intrusive input. **Step 1:** team PRs #1170(`--ocr`)/#1171(`--selector` default) re-checked **MERGEABLE/CLEAN** (no conflict
> from #1173's `_find.py` touch), auto-merge held OFF (public-API human gates) → **Orc did NOT merge / did NOT enable** (guardrail);
> #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1); remote =
> main+develop+dependabot+2 live PR heads (#1170/#1171) → Rule 14 clean (#1173 branch deleted). **Step 2:** no handoff owed (QA already
> closed #1173). status:done open = **#972** only (human-only, parked). status:in-progress = #1169/#1060 (Dev PRs held) + **#886** (P1
> from:qa keyboardShortcut/UIA, v0.3.4 — **freshly picked by the 01:37Z Dev cycle, updated ~10min before now**, NOT abandoned, no PR yet) +
> #766 (Ace umbrella) → none stale/abandoned. **Step 3:** criterion #1 complete; the find numeric-param validation family is now closed
> (depth/limit/threshold all reject non-positive); backlog sharp, Dev actively on #886 → no new gap filed (Rule 9). **Step 3.5:** NOT due
> (<7d; tracker current to 06-28). **Step 3.6: no change — no new evidence** (two completed cycles since 01:22Z, both the existing rules
> SUCCEEDING: Dev's hardest-first pick of #1173 over an easy additive win + correct public-API non-trigger + Step-3.5 verifier PASS; QA's
> clean cited verify + sound numeric-param family audit + zero false, zero intrusive input; test-quality audit — #1173's 10-case test
> asserts the INVALID_INPUT category + recoverable + inclusive boundary [BEHAVIOR not shape, not over-mocked/tautological]; the one thin spot
> [Dev self-caught + reverted a stray write to the main checkout] is a single self-caught instance already covered by Rule 4/10 → over-fit
> forbidden; self-review at 6 principles < ~8 distillation threshold; freshest rule [stale-DLL trap] landed <1d ago; EVOLUTION row appended).
> **Step 3.7:** done-criteria 1–4 NOT all met (criterion #1 ✅; #2 #1170/#1171 PR-held human gates; #3 #766 in-progress; #4 half-finished
> PRs) → **no auto-advance**. needs:ace UNCHANGED at 13. develop GREEN HEAD `54e4ba6` (Build&Test+CodeQL SUCCESS, real CI). Evidence:
> `.work/reviews/2026-06-29-0152-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~01:22Z (Orc autonomous cycle — **v0.3.2 DONE-CRITERION #1 NOW FULLY MET: QA live-verified+closed the
> P0 JAB blocker #1096; develop GREEN; the recognition moat is code-complete AND live-confirmed.** Since 00:57Z: **QA @01:20Z
> VERIFIED+CLOSED #1096** (criterion #1's last item) — live JAB attach on a real OpenJDK-21 Swing desktop, `test_jab_recognition_932.py
> -m desktop` 4/4 PASS, concrete cascade **UIA 6 → cascade 46, delta=+40, extra_sources={'jab':40}** matching the `docs/RECOGNITION.md`
> `+40` row, with a **discriminating negative control** (redeployed pre-fix DLL → delta 0/tests FAIL; swapped fix DLL back → delta 40/4-4
> PASS — proves the attach is the fix's effect, not env). Notably QA **did NOT trust the worktree's untracked DLL** (reset-to-develop left
> the OLD 122880-B pre-fix binary) — it **downloaded the canonical CI-built `naturo-core-dll` from the merged run** (md5 7036e02…) first.
> `verified` added, evidence comment posted, closed against `45768c1` (Rule 1). **Step 1:** team PRs #1170(`--ocr`)/#1171(`--selector`
> default) both CLEAN/MERGEABLE, full-green, auto-merge held OFF (public-API human gates) → **Orc did NOT merge / did NOT enable
> auto-merge** (guardrail); #1167(dependabot)/#1055(community) base=`main` human-only (Rule 2) → untouched; nothing merged/closed BY Orc
> (Rule 1); remote = main+develop+dependabot+2 live PR heads (#1170/#1171) → Rule 14 clean, no orphans. **Step 2:** no handoff owed (QA
> already closed #1096); status:done open now = **#972** only (human-only, parked); status:in-progress = #766(Ace) + #1060/#1169(Dev PRs
> held) + **#1173** (QA-filed `--limit` validation P2, **freshly picked up by Dev — status:in-progress set 17:11Z, ~12min before now**, NOT
> abandoned) → none stale/abandoned. **Step 3:** recognition moat criterion #1 COMPLETE; backlog sharp, Dev actively on #1173 → no new gap
> filed (Rule 9). **Step 3.5:** NOT due (<7d; tracker current to 06-28). **Step 3.6: CHANGE MADE (evidence-backed, not churn).** QA's #1096
> verify exposed a real structural hermeticity trap: `naturo_core.dll` is **not git-tracked**, so QA's Step-0 `reset --hard` leaves a STALE
> pre-fix DLL and Step 0 only copies the DLL *when absent* → a future QA could silently verify a native fix against a stale binary (false
> verdict; the DLL *is* the thing under test for every `core/`-touching moat fix). QA handled it by diligence this once but the doc didn't
> encode it. **Fix:** added the stale-`naturo_core.dll` trap to `qa-cycle.md` Step 2.4's harness-lies enumeration (beside the #969
> editable-install sibling — different mechanism, not redundant) + a directive to **deploy the canonical CI-built DLL from the merged run**
> for native fixes. One surgical change (Step-2.4 list 3→4 lies, no checklist bloat); EVOLUTION row appended. **Step 3.7:** done-criteria
> 1–4 NOT all met (criterion #1 ✅ NOW; #2 #1170/#1171 PR-held human gates; #3 #766 in-progress; #4 half-finished PRs) → **no auto-advance**,
> but criterion #1 converged. needs:ace UNCHANGED at 13. develop GREEN HEAD `45768c1` (Build&Test+CodeQL SUCCESS, real CI). Evidence:
> `.work/reviews/2026-06-29-0122-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~00:57Z (Orc autonomous cycle — **MAJOR CONVERGENCE: the P0 recognition-moat JAB blocker #1096 LANDED;
> develop GREEN; the recognition moat is now CODE-COMPLETE for v0.3.2.** Since 00:22Z: **Dev merged PR #1174** (`fix/issue-1096-jab-attach`
> →develop, `45768c1`, *fixes #1096*) — a bounded pump-and-retry JAB JVM handshake replacing the one-shot `Windows_run` that never completed
> the async AT↔JVM discovery. **Dev PROVED the block the prior cycle's [Orc] nudge demanded** (HARDEST-FIRST "prove, don't assume"): built the
> native core locally (MSVC 14.44 + CMake, surmounting the vcvars block two prior cycles deferred on), reproduced the bug first (red), live-verified
> on a provisioned desktop (OpenJDK 21 + Access Bridge: UIA 6 → cascade 46, **delta=40, extra_sources={'jab':40}**), ran the Step-3.5 adversarial
> verifier (PASS, byte-identical DLL + bounded-cost perf call1 5.05s/call2-3 0.156s), and republished the honest `docs/RECOGNITION.md` `+40` row
> + re-pinned the never-lie doc test both directions. Full CI matrix GREEN (`45768c1` Build & Test + CodeQL SUCCESS @16:46Z UTC). **Step 1:** PR
> #1174's branch already auto-deleted (Rule 14 clean — remote = main+develop+dependabot+2 live PR heads #1170/#1171); the two team PRs #1170
> (`--ocr`)/#1171 (`--selector` default change) stay full-green/MERGEABLE/CLEAN with auto-merge correctly held OFF (public-API human gates) →
> **Orc did NOT merge / did NOT enable auto-merge** (guardrail); the other 2 PRs (#1167 dependabot, #1055 community) base=`main`, human-only
> (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1). **Step 2 handoff:** **flipped #1096 `status:in-progress`→`status:done`** (Rule 1
> on-merge handoff; posted [Orc] note asking QA to confirm the live JAB attach + republished row from a Java-Swing desktop, then label `verified`);
> status:done open now = #1096 + #972 (human-only); status:in-progress = #1169/#1060 (Dev PRs held) + #766 (Ace) → none abandoned. **Step 3
> hygiene:** Dev self-filed tech-debt **#1175** (two latent bad tests the #1174 full-suite surfaced — `test_cost_guardrails.py` `open()` w/o
> `encoding=` non-hermetic on cp936 + `test_agent.py` `total_time > 0` clock-flake) → triaged **P2 / v0.3.4**. **Step 3.5:** NOT due (<7d, tracker
> current to 06-28). **Step 3.6: no change — no new evidence** (the one completed cycle is the existing rules SUCCEEDING on the hardest milestone
> item — HARDEST-FIRST/prove-the-block + Step-3.5 verifier + build-recipe-on-#1097 all fired; test-quality audit: #1174's new tests are sound
> [real cascade unmocked, skip-when-fixture-absent], and the two bad tests were self-caught + filed #1175 — over-fit forbidden; self-review at 6
> principles < ~8 distillation threshold; EVOLUTION row appended). **Step 3.7:** done-criteria 1–4 NOT all met → no auto-advance (criterion #1
> now code-complete, awaiting QA live-JAB verify; #1170/#1171 PR-ready-not-merged = human gates; #766 in-progress) — but criterion #1 materially
> advanced. needs:ace UNCHANGED at 13 (#1175 is Dev-actionable tech-debt, not a human gate). develop GREEN HEAD `45768c1` (real CI). Evidence:
> `.work/reviews/2026-06-29-0057-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-29 ~00:22Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; TWO PR-ready public-API
> sign-offs now on the v0.3.2 critical path — both criterion-#2 (find engine), both correctly held for Ace.** Since 15:52Z (f342913):
> **Dev opened PR #1171** (`fix/issue-1169-shortform-selector`→develop, *refs #1169* — `find --selector` now honors `--backend`/`--depth`,
> changing the default backend `uia`→`auto` so short-form `//Role` selectors resolve via the full cascade not UIA-only), **full CI matrix
> green / MERGEABLE / CLEAN / auto-merge OFF by Dev design** (public-CLI default change → human gate, same class as #1170). **Orc did NOT
> merge / did NOT enable auto-merge** (guardrail). **QA filed P2 #1172** (saved-selector "not found" leaks Python `KeyError` repr quotes
> into the user message across find/click/type — single source-side fix; Dev backlog, not human-only). **needs:ace 12→13** (#1169 gained
> the label): #1060(PR#1170)/#1169(PR#1171)/#1168/#1136/#1105/#1057/#975/#972/#969/#935/#915/#914/#897. **Step 1:** both team PRs
> (#1170 OCR, #1171 selector) full-green/held-OFF → untouched; the other 2 PRs (#1167 dependabot, #1055 community fork) base=`main`,
> human-only (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1); remote = main+develop+dependabot+2 live PR heads (Rule 14 clean,
> no orphans). **Step 2:** status:done open = #972 only (human-only); status:in-progress = #1169/#1096/#1060 (Dev) + #766 (Ace) → none
> abandoned, no handoff owed (Rule 1). **Step 3/3.7: HONEST RECLASSIFICATION of #1096 (criterion-#1 JAB, the last unlanded recognition
> item).** Prior "pure Dev execution / no human gate" framing is wrong — two consecutive headless Dev cycles deferred it: build is
> Dev-actionable (vcvars per #1097) but an unattended/RDP-disconnected cron session cannot honestly verify a live JAB attach against a
> running Java-Swing app. Corrected GOAL.md known-blockers; posted [Orc] nudge on #1096 to PROVE the block next cycle (build + live-verify
> attempt, paste output) per HARDEST-FIRST — **not yet a hard needs:ace gate** (prove first, no premature escalation). Done-criteria 1–4
> NOT all met → no auto-advance; critical-path advance needs Ace (#1170 + #1171 sign-off, #914 release). **Step 3.5:** NOT due (<7d).
> **Step 3.6: no change — no new evidence** (two exemplary cycles — Dev self-gated #1171's public default + auditable full suite + hermetic
> test; QA root-caused #1172 read-only, zero intrusive input; new test spot-checked sound [forwarded-kwargs assert, not shape/tautology];
> self-review checklist at 6 principles < ~8 distillation threshold; the #1096 build-not-attempted thin-spot handled on-issue not as a
> prompt edit; over-fit forbidden; EVOLUTION row appended). develop GREEN last real-CI `3fb7b5d`/#1166; HEAD `3350a54` `[skip ci]`.
> Evidence: `.work/reviews/2026-06-29-0022-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-28 ~16:02Z (Orc autonomous cycle — **NO STATE CHANGE since 15:52Z; develop GREEN; loop HEALTHY but
> IDLE ON HUMAN GATES.** Heartbeat with zero movement: no new merges, no new PRs, no QA closes; in-progress unchanged (#1169
> Dev / #1060 Dev-PR-held / #766 Ace umbrella); needs:ace identical (12): #1168/#1136/#1105/#1060/#1057/#975/#972/#969/#935/
> #915/#914/#897. **Step 1:** PR #1170 (`find --ocr`→develop, *fixes #1060*) full-matrix GREEN (17 SUCCESS/1 SKIPPED), auto-merge
> OFF by Dev design (public-API gate) → **Orc did NOT merge / did NOT enable auto-merge** (guardrail); other 2 open PRs (#1167
> dependabot checkout-7 [Build&Test FAILING], #1055 community fork) base=`main`, human-only (Rule 2) → untouched; nothing
> merged/closed by Orc (Rule 1); remote = main+develop+dependabot+`fix/issue-1060-find-ocr` (Rule 14 clean, no orphans).
> **Step 2:** status:done open = #972 only (human-only); no handoff owed, nothing abandoned (Rule 1). **Step 3:** NO churn —
> #1170 already queued+reviewed, #1096 unblock pointer already on-issue, digest already accurate (Rule 9); no GitHub action
> taken this cycle. **Step 3.5:** NOT due (<7d). **Step 3.6: no change — no new evidence** (zero completed cycles since 15:52Z;
> over-fit forbidden). **Step 3.7:** done-criteria 1–4 NOT all met (#1096 JAB unblocked-not-landed [pure Dev, UNPICKED — no
> Dev session alive, root cause #1168]; #1060/PR#1170 PR-ready-not-merged [human gate]; #766 in-progress) → no auto-advance.
> Critical-path advance now needs Ace: **#1170 sign-off** + **#914 release**. develop GREEN last real-CI `3fb7b5d`/#1166,
> HEAD `f342913` `[skip ci]`. Evidence: `.work/reviews/2026-06-28-1602-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-28 ~15:52Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; done-criterion #2
> (`find --ocr`) is PR-READY & FULL-MATRIX GREEN — but a public-API HUMAN GATE is back on the v0.3.2 critical path.** Since
> 15:22Z: **Dev opened PR #1170** (`fix/issue-1060-find-ocr`→`develop`, *fixes #1060* — `naturo find --ocr` via RapidOCR),
> entire CI matrix PASS (Ubuntu+macOS 3.9/3.12/3.13, Windows-DLL, C++ core, CodeQL, Lint, Version, Commit-Author),
> `MERGEABLE`/`CLEAN`, and **deliberately held auto-merge OFF** — it adds new public CLI/API surface (`--ocr` flag,
> `OCR_NOT_AVAILABLE`/`OCR_FAILED` codes, `naturo.ocr_match` module, `naturo[ocr]` extra), a human-only public-API sign-off
> (same class as #1136/#1105). **Orc did NOT merge / did NOT enable auto-merge** (guardrail); posted one `[Orc]` review
> comment + queued it. **CORRECTION to the 15:22Z claim "done-criteria 1–4 now have NO human gate":** #1170 reintroduces a
> public-API gate on criterion #2 — it is now the closest-to-done critical-path item and the TOP needs:ace actionable.
> **needs:ace 11→12** (#1060 gained the label): **#1060(PR#1170)**/#1168/#1136/#1105/#1057/#975/#972/#969/#935/#915/#914/#897.
> **Step 1:** the other 2 open PRs (#1167 dependabot checkout-7, #1055 community fork) are base=`main`, human-only (Rule 2)
> → untouched; nothing merged/closed BY Orc (Rule 1); remote = main+develop+dependabot+`fix/issue-1060-find-ocr` (#1170's
> live head — Rule 14 clean, no orphans). **Step 2:** status:done open = #972 only (human-only); status:in-progress = #1169
> (Dev, fresh) + #1060 (Dev, PR held) + #766 (Ace umbrella) → none abandoned, no handoff owed, closed nothing (Rule 1).
> **Step 3:** `--ocr` is the in-flight find-engine moat piece (reaches canvas/game controls the a11y tree can't); backlog
> sharp, no new gap (Rule 9). **Step 3.5:** NOT due (tracker row 06-28 current, <7d). **Step 3.6: no change — no new
> evidence** (two completed cycles since 15:22Z both exemplary — Dev self-gated the public-API PR per the guardrail [the
> existing rule succeeding, not a gap] + 20 hermetic tests + full-suite 6772 passed; QA evidenced #1154 already-resolved,
> read-only, zero intrusive input, no false close; over-fit forbidden; EVOLUTION row appended). **Step 3.7:** done-criteria
> 1–4 NOT all met (#1096 JAB unblocked-not-landed [pure Dev]; #1060 `--ocr` PR-ready-not-merged [human gate]; #766
> in-progress) → no auto-advance. GOAL.md "Known blockers" + criterion #2 updated. develop GREEN last real-CI `3fb7b5d`
> (#1166), HEAD `31e09b9` `[skip ci]`. Evidence: `.work/reviews/2026-06-28-1552-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-28 ~15:22Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; Ace cleared the
> LAST native-build blocker — v0.3.2 recognition-moat work is now pure Dev execution.** Since 14:52Z: **Ace provisioned
> the C++ toolchain on NATUROBOT** (MSVC 14.44 + CMake + Ninja; full `core` Release build proven → `naturo_core.dll`) →
> **#1097 CLOSED 15:04Z** → **#1096 (JAB attach fix) UNBLOCKED** (now Dev-buildable+verifiable locally; build recipe on
> #1097; pointer + async-JVM-handshake root-cause already on #1096). This clears done-criterion #1's last native block.
> **Dev picked #1060 `find --ocr`** (done-criterion #2) → now `status:in-progress` (15:14Z, in flight, no PR yet). **QA
> filed #1169** (P2 bug/from:qa/v0.3.2 — find short-form `//Role`: role-only never matches & 'any app' desktop-wide search
> doesn't search; regression vs #615; Dev-actionable). **Net: done-criteria 1–4 now have NO human gate** — #1096 (JAB) +
> #1060 (OCR) are both pure Dev work, one in flight, one pickable; only #1168 (persistent scheduler) still gates loop
> durability. **needs:ace 12→11** (#1097 dropped): #1168/#1136/#1105/#1057/#975/#972/#969/#935/#915/#914/#897. **Step 1:**
> NO team-Dev PR; 2 open PRs both base=`main` human-only (Rule 2) — #1167 dependabot checkout-7 (UNSTABLE), #1055
> community fork→#1057; nothing merged/closed BY Orc (Rule 1); remote = main+develop+1 dependabot (Rule 14 clean).
> **Step 2:** status:done open = #972 only (human-only); status:in-progress = #1060 (Dev, fresh) + #766 (Ace umbrella) →
> no handoff owed, nothing abandoned, closed nothing (Rule 1). **Step 3:** the move (build-unblock pointer on #1096) was
> already posted by Ace at 15:04Z → no churn (Rule 9); backlog sharp, no new gap. **Step 3.5:** NOT due (tracker row 06-28
> current, <7d). **Step 3.6: no change — no new evidence** (one completed cycle since 14:52Z = QA filing #1169, exemplary —
> read-only find exploration, regression-cited vs #615, ruled out harness, zero intrusive input; Dev in-flight on #1060;
> single signal → over-fit forbidden; EVOLUTION row appended). **Step 3.7:** done-criteria 1–4 NOT all met (#1096 JAB
> unblocked-not-landed; #1060 in-flight-not-shipped; #766 in-progress) → no auto-advance; remaining critical path is now
> pure Dev execution (no human gate). GOAL.md "Known blockers" updated (native-build block struck). develop GREEN last
> real-CI `3fb7b5d` (#1166), HEAD `[skip ci]`. Evidence: `.work/reviews/2026-06-28-1522-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-28 ~14:52Z (Orc autonomous cycle — **LOOP HEALTHY & MOVING POST-RESUME; develop GREEN;
> Ace cleared a real convergence blocker.** Since the 14:22Z cycle: **QA verified+closed #1164 & #1162** (both
> `--json` contract bugs, cited merged commits per Rule 1, zero intrusive input) → `status:done` queue now empty
> except human-only #972. **Ace DECIDED #1077 (OCR engine) at 14:50Z → #1077 closed → #1060 `naturo find --ocr`
> UNBLOCKED**: RapidOCR optional extra (`pip install naturo[ocr]`; MIT/Apache, fully offline, Chinese-strong,
> bundled ~10MB ONNX, `OCR_NOT_AVAILABLE` recoverable error when absent). #1060 is OPEN/P1/v0.3.2/unassigned with
> Ace's implementation spec on the issue → **Dev-actionable now, top of the v0.3.2 queue** (it is done-criterion #2
> of the current sub-goal). GOAL.md "Known blockers" updated (OCR blocker struck). **needs:ace 13→12**
> (#1077 dropped): #1168/#1136/#1105/#1097/#1057/#975/#972/#969/#935/#915/#914/#897. **Step 1:** NO team-Dev PR;
> 2 open PRs both base=`main` human-only (Rule 2) — #1167 dependabot checkout-7 (UNSTABLE), #1055 community fork→#1057;
> nothing merged/closed BY Orc (Rule 1); remote branches = main+develop+1 dependabot (Rule 14 clean). **Step 2:** no
> handoff owed (#1164/#1162 already QA-closed). **Step 3:** #1060 unblock is the move; backlog sharp, no new gap
> (Rule 9). **Step 3.5:** NOT due (tracker row 06-28 current, <7d). **Step 3.6: no change — no new evidence** (only
> completed cycle since 14:22Z = QA verifying #1164/#1162, exemplary; single signal → over-fit forbidden; EVOLUTION
> row appended). **Step 3.7:** done-criteria 1–4 NOT all met (#1096 JAB native-build-blocked #1097; #1060 unblocked
> but not yet shipped; #766 in-progress) → no auto-advance; biggest remaining sub-goal blocker = #1097 (native build
> for JAB #1096), stays top of needs:ace. develop GREEN last real-CI `3fb7b5d` (#1166), HEAD `[skip ci]`. Evidence:
> `.work/reviews/2026-06-28-1452-auto-review.md`.)
>
> Last refreshed (prior): 2026-06-28 ~14:22Z (Orc autonomous cycle, **FIRST since loop resume** — **develop GREEN; ROOT-CAUSE
> CORRECTION + weekly competitiveness caught up (12d overdue).** The ~6-day freeze was **NOT** #1168's session-only crons
> as the 06-26/27/28 daily-reviews assumed — the loop-state log + git show **Ace globally PAUSED all roles 06-22
> (`ba7d6ac`) and RESUMED today (`d16a91e`)**; last Dev/QA cycles ran 06-22 ~09:56 local, none in the paused window.
> #1168 stays valid as the *future*-durability meta-blocker but did not cause this stall; loop is live again now.
> develop GREEN real-CI `3fb7b5d` (#1166, [skip ci] orc/runner on top, no new CI). **Step 1:** NO team-Dev PR; 2 open PRs
> both main-base human-only (Rule 2): #1167 dependabot checkout-7 / #1055 community fork→#1057; nothing merged/closed BY
> Orc (Rule 1, Rule 14 clean). **Step 2:** no handoff owed; status:done #1164/#1162 unverified ~6.4d (QA was paused →
> resumes now) + #972 (human-only); status:in-progress #766 (Ace umbrella) → left. **Step 3:** backlog sharp, no new gap
> (Rule 9). **Step 3.5 RAN (Trend FURTHER):** naturo ⭐5 flat, Terminator 1,542 (+12), Windows-MCP 6,262 (+204), UFO²
> 9,153 (+139); gap→Terminator **−1,537** (was −1,525, widened). Landscape: **UFO²→UFO³ "Galaxy"** (orchestration-layer,
> doesn't touch recognition moat); Terminator shipped NodeJS SDK + YAML workflows + OS-event→YAML recording; widening
> axis = distribution (#922/#927). Tracker row + HTML report refreshed to 06-28. **Step 3.6: no change — no new evidence**
> (no Dev/QA cycle in the paused window; EVOLUTION row appended). needs:ace=13 unchanged, stars=5 flat. Milestones:
> v0.3.2=17/v0.3.3=12/v0.3.4=31/v0.4.0=1/v0.5.0=4. v0.3.2 ship-gate FULLY MET (release is Ace's call, #914). Evidence:
> `.work/reviews/2026-06-28-1422-auto-review.md`.**)
>
> Last refreshed (prior): 2026-06-28 ~07:02Z (Orc daily review, 2nd pass today — **NO-CHANGE confirmation; nothing moved on the
> wire in the ~3h since 04:01Z. Still nothing merged/closed since #1166 (06-22 01:55Z, now ~6.4d). develop GREEN real-CI
> `3fb7b5d` (orc [skip ci] on top, no new CI). PR queue empty + no orphans (remote = main+develop+1 dependabot, Rule 14
> clean). 2 open PRs both main-base human-only (Rule 2): #1167 dependabot checkout-7 (Build&Test 'failure' = Feishu-
> notify step only) / #1055 community fork→#1057. status:in-progress=#766 (Ace, 06-21, ~7d stale); status:done
> #1162/#1164/#972 STILL unverified ~6d (QA loop down). needs:ace=13, stars=5 flat, no external activity. Milestones:
> v0.3.2=17/v0.3.3=12/v0.3.4=31/v0.4.0=1/v0.5.0=4. #1168 (persistent-scheduler, P1 needs:ace, my own 06-27 04:03Z)
> STILL 0 comments ~1.3d — THE meta-blocker; every needs:ace item is downstream of it. #914/#915 last comments = MY OWN
> [Orc] escalations 06-25 (~3.3d UNANSWERED → Rule 9, did NOT re-post). v0.2.0 still OPEN w/ 0 open issues (sort|first
> milestone-picker hazard — suggest Ace close). No new issues (version 0.3.1, Phase 3.5 N/A). Loop has nothing self-
> serviceable; freeze is entirely an Ace-decision bottleneck (#1168 first). Evidence:
> `.work/reviews/2026-06-28-0702-daily-review.md`.**)
>
> Last refreshed (prior): 2026-06-28 ~04:01Z (Orc daily review — **NO-CHANGE, ~6.3d frozen. Nothing merged/closed since #1166
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
