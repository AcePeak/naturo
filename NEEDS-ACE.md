# NEEDS-ACE — Human-Decision Queue

> The autonomous naturo loop (Dev / QA / Orch) runs unattended and self-closes everything it can.
> This file is the short list of things **only Ace can decide**. Refreshed by the Orchestrator each
> review cycle. Read this first on a check-in. Each item also has a GitHub issue labelled `needs:ace`.

_Last refreshed: 2026-06-29 00:57Z (Orc autonomous cycle — **MAJOR CONVERGENCE — the P0 recognition-moat JAB blocker #1096 LANDED;
develop GREEN; the v0.3.2 recognition moat is now CODE-COMPLETE.** Dev merged **PR #1174** (`fixes #1096`, `45768c1`) — a bounded
pump-and-retry JAB JVM handshake, **built + live-verified on a real Java desktop** (UIA 6 → cascade 46, **delta=40, sources={'jab':40}**),
Step-3.5 adversarial verifier PASS, full CI matrix green. This is the item two prior headless cycles deferred on; the on-issue [Orc]
"prove-the-block" nudge worked. Orc flipped **#1096 `status:in-progress`→`status:done`** (awaiting QA's live-JAB confirmation — **not** a
human gate). **Queue UNCHANGED at 13** (the new tech-debt #1175 is Dev-actionable, not human-only):
**#1060(PR#1170)**/**#1169(PR#1171)**/#1168/#1136/#1105/#1057/#975/#972/#969/#935/#915/#914/#897.
**TOP-2 ACTIONABLE — both close criterion #2 (find engine), both need ONE sign-off (unchanged from 00:22Z):**
**(1) #1060 / PR #1170 (`naturo find --ocr`)** — full CI green, MERGEABLE/CLEAN, auto-merge OFF (new public surface). **Ratify + merge**, then QA verifies with `pip install naturo[ocr]`.
**(2) #1169 / PR #1171 (`find --selector` honors `--backend`/`--depth`, default `uia`→`auto`)** — full CI green, MERGEABLE/CLEAN, auto-merge OFF (public-CLI default change). **Ratify + merge**, or revise the default. **The loop will NOT merge either (guardrail).**
With #1096 landed, criterion #1 needs only **QA's live-JAB verify** (Java-Swing desktop) — already strongly evidenced by Dev's in-cycle
desktop verify + independent verifier (delta=40). **The critical-path human gates on done-criteria 1–4 are now exactly #1170 + #1171**
(+ release sign-off #914, criterion #5). **Step 1:** the other 2 PRs (#1167 dependabot, #1055 community fork) base=`main`, human-only
(Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1); Rule 14 clean. **Step 3.5** NOT due (tracker current to 06-28, <7d).
**Step 3.6** no change — no new evidence (the one completed cycle is the existing rules *succeeding* on the hardest milestone item —
HARDEST-FIRST/prove-the-block + Step-3.5 verifier all fired; #1174's new tests sound + the two latent bad tests self-caught & filed #1175;
self-review at 6 principles < ~8 distillation threshold; over-fit forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release is your call,
#914). Prior header below kept as history.)

_Earlier: 2026-06-29 00:22Z (Orc autonomous cycle — **loop healthy & converging; develop GREEN; TWO PR-ready public-API
sign-offs now on the v0.3.2 critical path (#1170 + NEW #1171), both full-matrix green & auto-merge correctly held OFF.**
**Queue 12 → 13** (#1169 gained `needs:ace` — Dev self-flagged the `find --selector` default-backend behavior change): now
**#1060(PR#1170)**/**#1169(PR#1171)**/#1168/#1136/#1105/#1057/#975/#972/#969/#935/#915/#914/#897.
**TOP-2 ACTIONABLE — both close criterion #2 (find engine) and both need ONE sign-off:**
**(1) #1060 / PR #1170 (`naturo find --ocr` via RapidOCR)** — full CI matrix green, `MERGEABLE`/`CLEAN`, auto-merge OFF: new public
surface (`--ocr` flag, `OCR_NOT_AVAILABLE`/`OCR_FAILED`, `naturo.ocr_match`, `naturo[ocr]` extra). **Ratify + merge** (recommended),
then QA verifies with `pip install naturo[ocr]`.
**(2) #1169 / PR #1171 (`find --selector` honors `--backend`/`--depth`)** — full CI matrix green, `MERGEABLE`/`CLEAN`, auto-merge OFF
**because it changes a public CLI default** (`find --selector` default backend `uia` → `auto`, so a short-form selector now resolves via
the full cascade, not UIA-only). Behavior change on a shipped command = public-contract sign-off (same class as #1170). **Ratify + merge**
(recommended — it makes `find --selector` consistent with the query path's auto-cascade; refs #1169, facet-2 + live verify remain), or
revise the default. **The loop will NOT merge either (guardrail).**
**CRITERION-#1 watch — #1096 (JAB attach):** the last recognition item not yet landed. **Honest reclassification this cycle:** it is
NOT "pure headless Dev" — two consecutive headless cycles deferred it (build is vcvars-gated but doable per #1097; the binding gate is
that an unattended/RDP-disconnected cron session can't honestly verify a live JAB attach against a running Java-Swing app). Posted an
[Orc] nudge on #1096 directing the next Dev cycle to **prove the block** (actually build via vcvars + attempt the live verify, paste
output). If the live verify is truly impossible unattended → I'll escalate a `needs:ace` env gate next cycle (attended-console verify
run, or land build-only with an honest `RECOGNITION.md` JAB caveat). **Not yet a hard human gate — proving it first (no premature
escalation).**
**Also since 15:52Z:** QA filed P2 #1172 (saved-selector "not found" leaks Python `KeyError` quotes into the user message across
find/click/type) — normal Dev backlog work, single source-side fix, no action from you. **Step 1:** the other 2 open PRs (#1167
dependabot checkout-7, #1055 community fork) are base=`main`, human-only (Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1).
**Step 3.5** NOT due (tracker current to 06-28, <7d). **Step 3.6** no change — no new evidence (two exemplary cycles — Dev self-gated the
#1171 public-default change + ran the full suite auditably; QA root-caused #1172 read-only with zero intrusive input; self-review
checklist at 6 principles, < the ~8 distillation threshold; over-fit forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release is your
call, #914). Prior header below kept as history.)

_Earlier: 2026-06-28 15:52Z (Orc autonomous cycle — **loop healthy & converging; develop GREEN; done-criterion #2
(`find --ocr`) is PR-ready & full-matrix green — and now needs ONE sign-off from you.** **Queue 11 → 12** (#1060 gained
`needs:ace` — Dev self-flagged the OCR public surface): now **#1060(PR#1170)**/#1168/#1136/#1105/#1057/#975/#972/#969/#935/#915/#914/#897.
**TOP ACTIONABLE — #1060 / PR #1170 (`naturo find --ocr` via RapidOCR):** Dev opened it full-matrix green
(Ubuntu+macOS 3.9/3.12/3.13, Windows-DLL, C++ core, CodeQL, Lint, Version all pass), `MERGEABLE`/`CLEAN`, and
**correctly held auto-merge OFF** because it adds new public CLI/API surface (`--ocr` flag, `OCR_NOT_AVAILABLE`/
`OCR_FAILED` codes, `naturo.ocr_match` module, `naturo[ocr]` extra) — a **public-API sign-off**, same class as
#1136/#1105. **The loop will NOT merge it (guardrail).** This is the closest-to-done item on the v0.3.2 critical path:
**sign off + merge #1170**, then QA verifies end-to-end with `pip install naturo[ocr]`. **Correction to the 15:22Z note:**
done-criteria 1–4 are **NOT** "no human gate left" — #1170 reintroduces this public-API gate on criterion #2.
**#1096 (JAB)** remains pure Dev execution (native build cleared) — the only criterion-#1 recognition item still to land.
**#1168** (persistent scheduler) is about *future* loop durability, not a 1–4 blocker.
**Also since 15:22Z:** QA evidenced open P2 #1154 as already-resolved (range validation predates the issue) — no action
from you. **Step 1:** the other 2 open PRs (#1167 dependabot checkout-7, #1055 community fork) are base=`main`, human-only
(Rule 2) → untouched; nothing merged/closed BY Orc (Rule 1). **Step 3.5** NOT due (tracker current to 06-28). **Step 3.6**
no change — no new evidence (two exemplary cycles; the public-API self-gate is the existing rule succeeding; over-fit
forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release is your call, #914). Prior header below kept as history.)

_Earlier: 2026-06-28 14:22Z (Orc autonomous cycle, **first since the loop resumed** — **develop GREEN; queue
unchanged at 13; ROOT-CAUSE CORRECTION on the 6-day freeze; weekly competitiveness row finally caught up (was 12d
overdue).** Queue: #1168/#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
**Freeze root cause (corrected):** the ~6-day stall (no merge/verify since #1166, 06-22) was NOT (only) #1168's
session-only crons as the 06-26/27/28 daily-reviews assumed — the loop-state log shows **you globally PAUSED all
roles on 06-22 (`ba7d6ac`) and RESUMED today (`d16a91e`)**. The loop is now live again; Dev/QA will resume on their
crons. #1168 (persistent scheduler) remains valid and is still THE meta-blocker for *future* unattended durability,
but it did not cause this particular window. **develop GREEN** — last real-CI `3fb7b5d` (#1166) Build & Test + CodeQL
both SUCCESS; everything since is `[skip ci]` orc/runner → no STOP. **Step 1:** NO open team-Dev PR; the only 2 open PRs
(#1167 dependabot checkout-7, #1055 community fork) are both base=`main`, human-only (Rule 2) → untouched; nothing
merged/closed BY Orc (Rule 1). **Step 2:** no handoff owed (nothing merged this window); `status:done` open =
#1164/#1162 (unverified ~6.4d — QA was paused, will pick up now) + #972 (human-only); `status:in-progress` = #766 (Ace
umbrella) → left. **Step 3:** backlog sharp & self-feeding → no new gap (Rule 9). **Step 3.5 competitiveness — RAN
(12d overdue; last row 06-16): Trend = FURTHER.** naturo ⭐5 (flat), Terminator 1,542 (+12), Windows-MCP 6,262 (+204),
UFO² 9,153 (+139); **gap → Terminator −1,537 (was −1,525, widened +12)**. Landscape: **UFO² → UFO³ "Galaxy"**
(multi-device agent orchestration — an *orchestration-layer* move, doesn't touch naturo's recognition-depth moat);
**Terminator shipped NodeJS SDK + YAML workflows + OS-event→YAML recording**. The widening axis remains
**distribution** (#922/#927 — not yet on MCP registries / uvx). Tracker row + HTML report
(`naturo-competitive-report-2026-06.html`) refreshed to 06-28. **Step 3.6: no change — no new evidence** (no Dev/QA
cycle ran in the paused window; EVOLUTION ledger row appended). v0.3.2 ship-gate unchanged (FULLY MET — release is your
call, #914). Prior header below kept as history.)

_Earlier: 2026-06-22 16:04Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; two real-CI fixes
merged since 07:52Z (#1165 *fixes #1164*, #1166 *fixes #1162*) both now `status:done` awaiting QA; NO open team PR;
NO new human-only item** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — HEAD `3fb7b5d` (#1166, *fixes #1162*) **Build & Test + CodeQL both SUCCESS**; prior real-CI
`4721b67` (#1165, *fixes #1164*) both SUCCESS → no STOP. **Step 1:** NO open team-Dev PR (#1165/#1166 auto-merged +
branches deleted, Rule 14 clean). Only open PR = **#1167** (dependabot `actions/checkout` 6→7, base `main`,
human-only per Rule 2 → left). Nothing merged/closed BY Orc (Rule 1). **Step 2:** no handoff owed (#1162/#1164
flipped `status:done` by Dev on merge → QA verifies). `status:done` open = #1164/#1162 (fresh, awaiting QA) + **#972**
(human-only) → untouched; `status:in-progress` = **#766** only (Ace umbrella, AcePeak — left). **Step 3:** backlog
sharp & self-feeding → no new gap (Rule 9). **Step 3.5 competitiveness: NOT due** (6d < 7; due 06-23) — advance
intel: naturo ⭐5 flat, Terminator 1,540, Windows-MCP 6,194, UFO² 9,084; gap → Terminator −1,535 (widening).
**NEW landscape signal worth your read — Microsoft "Windows Agent Runtime"** (Build 2026, Jun 2–3): first-party
agentic OS substrate. Commoditization risk for generic UIA automation; it *sharpens* naturo's multi-framework
recognition moat (Java/Electron/SAP, which a UIA runtime won't cover). The widening gap is **distribution** — rivals
are on the MCP Registry / `uvx` / Claude Desktop Extensions (Windows-MCP ~2M installs); naturo is not yet. Already
tracked by #922/#928/#997/#923 — highest-leverage ship-gate-independent work once v0.3.2 ships. Posted on epic #919;
full 7-day tracker row lands 06-23. v0.3.2 ship-gate unchanged (FULLY MET — release is your call, #914). Prior header
below kept as history.)

_Earlier: 2026-06-22 07:52Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; #1146 (find --help
saved-selector examples) now QA-verified+closed (handoff fully complete); NO open team PR; one Dev cycle in-flight;
NO new human-only item; Step 3.6 honest no-change** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — last real-CI `aa0f983` (#1163, *fixes #1146*) **Build & Test + CodeQL both SUCCESS**; HEAD
`e54bc9e` is prior orc `[skip ci]` (no run) → no STOP. **Step 1:** NO open team-Dev PR (remote = `develop`+`main`
only, Rule 14 clean). Community **#1055** (base `main`, fork, UNSTABLE → queued #1057, human-only) → untouched;
nothing merged/closed BY Orc (Rule 1). **Step 2:** handoff complete — **#1146 QA-verified+closed @07:39Z** (clean-path
verify, no pipe, strict UTF-8, cited merged `aa0f983` per Rule 1). `status:done` open now = **#972** only (human-only)
→ untouched; `status:in-progress` = **#766** only (Ace umbrella, `from:ace` — left). **Step 3:** backlog sharp &
self-feeding (#1162/#1160/#1159/#1154/#897 feed Dev) → no new gap (Rule 9). **Step 3.5** competitiveness not due
(6d < 7; due 06-23). **Step 3.6: no change — no new evidence** (only completed signal since 07:22Z = QA @07:39Z
verifying #1146, exemplary — clean-path verify, cited merged commit, lateral-grepped residual `@name` mentions and
ruled them non-user-facing, zero intrusive input, left #972 queued; Dev cycle in-flight; freshest dev-cycle.md
HEAD-check rule landed <1d ago → over-fit forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release is your
call, #914). Prior header below kept as history.)

_Earlier: 2026-06-22 07:22Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; one open team-Dev
PR #1163 (*fixes #1146* find --help saved-selector examples) MERGEABLE + auto-merge SQUASH ON, landing itself;
QA filed one fresh P2 (#1162 — UNKNOWN_OPTION/UNKNOWN_COMMAND `-j` category miss) feeding Dev; NO new human-only
item; Step 3.6 honest no-change** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — last real-CI `d79647f` (#1161, *fixes #1100*) **Build & Test + CodeQL both SUCCESS**; HEAD
`c4a8207` is prior orc `[skip ci]` (no run) → no STOP. **Step 1:** ONE open team-Dev PR **#1163**
(`fix/issue-1146-find-help-saved-selector`→`develop`, *fixes #1146*) is **MERGEABLE + auto-merge SQUASH ON**;
`BLOCKED` only on the still-running Python test matrix + Analyze c-cpp, every completed check SUCCESS (Build C++,
Lint & Type, Version, Commit Author, Analyze python) → left to land on its own (pure docs/help-text, no public-API).
Community **#1055** (base `main`, fork, UNSTABLE → queued #1057, human-only) → untouched; nothing merged/closed BY
Orc (Rule 1). **Step 2:** no handoff owed (no team PR merged — #1163 still in CI; its `status:done` flip is Dev's
on-merge job). `status:done` open = **#972** only (human-only) → untouched; `status:in-progress` = **#1146** (active,
PR #1163 in CI) + **#766** (Ace umbrella, `from:ace` — left). **Step 3:** backlog sharp & self-feeding
(#1162/#1160/#1159/#1154/#897 feed Dev) → no new gap (Rule 9). **Step 3.5** competitiveness not due (6d < 7; due
06-23). **Step 3.6: no change — no new evidence** (both completed cycles since 06:52Z exemplary — QA @07:12Z filed
P2 #1162 [usage-path `-j` category miss; ruled out the 39-Calculator `list apps` anomaly as machine clutter, filed
nothing false; zero intrusive input]; Dev @07:20Z shipped PR #1163 [re-proved native block, adopted+finished a
near-complete prior-cycle fix the safe #935 way, fixed every saved-selector example + a regression test walking the
docstring AND every option-help string, applied the 18:52Z HEAD-check rule]; freshest dev-cycle.md HEAD-check rule
landed <1d ago → over-fit forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release is your call, #914). Prior
header below kept as history.)

_Earlier: 2026-06-22 06:52Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; #1100
(test_verify NonWindows hermeticity) now QA-verified+closed (handoff fully complete); NO open team PR;
one Dev cycle in-flight; NO new human-only item; Step 3.6 honest no-change** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — last real-CI `d79647f` (#1161, *fixes #1100*) **Build & Test + CodeQL both SUCCESS**; HEAD
`e029b2d` is prior orc `[skip ci]` (no run) → no STOP. **Step 1:** NO open team-Dev PR (remote = `develop`+`main`
only, Rule 14 clean). Community **#1055** (base `main`, fork, UNSTABLE → queued #1057, human-only) → untouched;
nothing merged/closed BY Orc (Rule 1). **Step 2:** handoff complete — **#1100 QA-verified+closed @06:38Z** (both
prev-red tests PASS on the real Windows desktop, full `test_verify.py` 81 passed, cited `d79647f` per Rule 1).
`status:done` open now = **#972** only (human-only) → untouched; `status:in-progress` = **#766** only (Ace
umbrella, `from:ace` — left). **Step 3:** backlog sharp & self-feeding (#1160/#1159/#1154/#1152/#1146/#897 feed
Dev) → no new gap (Rule 9). **Step 3.5** competitiveness not due (6d < 7; due 06-23). **Step 3.6: no change — no
new evidence** (only completed signal since 06:22Z = QA @06:38Z verifying #1100, exemplary — real-desktop runtime
check, cited merged commit, zero intrusive input, left #972 queued; Dev cycle in-flight; freshest dev-cycle.md
HEAD-check rule landed <1d ago → over-fit forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release is your
call, #914). Prior header below kept as history.)

_Earlier: 2026-06-22 06:22Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; team-Dev PR #1161
(*fixes #1100* test_verify NonWindows hermeticity) auto-merged itself green this cycle; #1100 already `status:done`
(handoff complete); NO open team PR; QA filed one fresh P2 (#1160 — bare `type --paste` bypasses the
input-content guard) feeding Dev; NO new human-only item; Step 3.6 honest no-change** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — HEAD `d79647f` (#1161, *fixes #1100*) **Build & Test + CodeQL both SUCCESS** → no STOP. **Step 1:**
NO open team-Dev PR — #1161 auto-merged itself (`d79647f`, full CI matrix green), **branch auto-deleted** (Rule 14
clean — remote = `develop`+`main` only). Community **#1055** (base `main`, fork, UNSTABLE → queued #1057,
human-only) → untouched; nothing merged/closed BY Orc (Rule 1). **Step 2:** handoff already complete — #1100 is
**`status:done`** (Dev flipped on merge; PR base `develop` ≠ default branch → no auto-close, Rule 1 preserved).
`status:done` open = **#1100** (awaiting QA) + **#972** (human-only) → #972 untouched; `status:in-progress` =
**#766** only (Ace umbrella, `from:ace` — left). **Step 3:** QA filed **#1160** (P2 — bare `naturo type --paste`
clipboard path issues raw Ctrl+V WITHOUT the input-content guard; guard gated on `if text is not None` at
`_type.py:143`, bare-paste branch bypasses it; mocked-backend demo, zero live keystrokes) — Dev-actionable backlog
bug, lateral to #960/#972, not human-only → no queue change. **Step 3.5** competitiveness not due (6d < 7; due
06-23). **Step 3.6: no change — no new evidence** (both completed cycles since 05:52Z exemplary — QA @06:12Z filed
#1160 [true new code path, mocked backend, zero intrusive input]; Dev @06:20Z shipped #1100 [re-proved the native
block first, surgical test-only fix, auditable stash-rerun gate]; freshest dev-cycle.md HEAD-check rule landed <1d
ago → over-fit forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release is your call, #914). Prior header below
kept as history.)

_Earlier: 2026-06-22 05:52Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; NO open team PR;
QA filed one fresh P2 (#1159 — native A-API title data-loss, lateral to #1150) feeding Dev; Dev cycle in-flight
(#1100 test_verify hermeticity); NO new human-only item; Step 3.6 honest no-change** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — last real-CI `959411d` (#1158, *fixes #1156*) **CodeQL + Build & Test both SUCCESS** @20:53Z;
HEAD `46fccf5` is prior orc `[skip ci]` (no run) → no STOP. **Step 1:** NO open team-Dev PR (Rule 14 clean —
remote = `develop`+`main` only). Community **#1055** (base `main`, fork, UNSTABLE → queued #1057, human-only) →
untouched; nothing merged/closed BY Orc (Rule 1). **Step 2:** no handoff owed (no team PR merged). `status:done`
open = **#972** only (human-only) → untouched; `status:in-progress` = **#1100** (Dev active, #1133 family — not
abandoned) + **#766** (Ace umbrella). **Step 3:** QA filed **#1159** (P2 — emoji/cross-script titles → `?`/0x3F
via native `GetWindowTextA` lossy conversion; the #1150/#1157 Python codepage-decode fix can't recover; true fix
= native `GetWindowTextW`+`CP_UTF8`, gated on native-build #1097) — Dev-actionable backlog bug, not a duplicate,
not human-only → no queue change. **Step 3.5** competitiveness not due (6d < 7; due 06-23). **Step 3.6: no change
— no new evidence** (only completed signal since 05:22Z = QA @05:40Z filing #1159, exemplary — independent
`GetWindowTextW` ground truth + raw-byte 0x3F evidence, distinguished from #1150, zero false needs:ace, zero
intrusive input; Dev #1100 in-flight; freshest dev-cycle.md HEAD-check rule landed <1d ago → over-fit forbidden).
v0.3.2 ship-gate unchanged (FULLY MET — release is your call, #914). Prior header below kept as history.)

_Earlier: 2026-06-22 05:22Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; #1156
(electron-decode/hermeticity, via PR #1158) now QA-verified+closed; NO open team PR; one Dev cycle in-flight
(#1100 test_verify hermeticity); NO new human-only item; Step 3.6 honest no-change** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — merge commit `959411d` (#1158, *fixes #1156*) **CodeQL + Build & Test both SUCCESS** @20:53Z;
HEAD `7138f8d` is prior orc `[skip ci]` (no run) → no STOP. **Step 1:** NO open team-Dev PR (#1158 auto-merged
itself `959411d`, branch auto-deleted, Rule 14 clean). Community **#1055** (base `main`, fork, UNSTABLE → queued
#1057, human-only) → untouched; nothing merged/closed BY Orc (Rule 1). **Step 2:** no handoff owed — #1156
already flipped `status:done` by Dev on merge, then **QA verified+closed it @05:08Z** (cited `959411d`, Rule 1).
`status:done` open = **#972** only (human-only) → untouched; `status:in-progress` = **#1100** (Dev active, #1133
family — not abandoned) + **#766** (Ace umbrella). **Step 3.5** competitiveness not due (6d < 7; due 06-23).
**Step 3.6: no change — no new evidence** (only completed signal since 04:52Z = QA #1156-verify, exemplary —
live 669-process no-crash runtime check the offline runner can't do + forced-`stdout=None` mock, cited merged
commit, traced a pytest tmp-dir PermissionError to a harness artifact and filed nothing false; Dev #1100
in-flight; freshest dev-cycle.md HEAD-check rule landed <1d ago → over-fit forbidden; honest no-change row).
v0.3.2 ship-gate unchanged (FULLY MET — release is your call, #914). Prior header below kept as history.)

_Earlier: 2026-06-22 04:52Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; one NEW team-Dev
PR #1158 (*fixes #1156* electron-decode/hermeticity) MERGEABLE + auto-merge ON, landing itself; NO new
human-only item; Step 3.6 honest no-change** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — last real-CI `5226d9f` (#1157, *fixes #1150*) **Build & Test + CodeQL both SUCCESS** @19:53Z;
HEAD `7e36ce8` is prior orc `[skip ci]` (no run) → no STOP. **Step 1:** one NEW team-Dev PR **#1158**
(`fix/issue-1156-electron-decode-hermeticity`→`develop`, *fixes #1156*) is **MERGEABLE + auto-merge SQUASH ON**;
`BLOCKED` only on still-running macOS/c-cpp checks, every completed check green → left to land on its own.
Community **#1055** (base `main`, fork, UNSTABLE → queued #1057, human-only) → untouched; nothing merged/closed
BY Orc (Rule 1). **Step 2:** no handoff owed — no team PR MERGED this cycle (#1158 still in CI; its
`status:done` flip is Dev's on-merge job). `status:done` open = **#972** only (human-only) → untouched;
`status:in-progress` = **#1156** (active, PR #1158 in CI) + **#766** (Ace umbrella, `from:ace`, not abandoned).
**Step 3.5** competitiveness not due (6d < 7; due 06-23). **Step 3.6: no change — no new evidence** (both
completed cycles exemplary — Dev @04:37Z shipped PR #1158 hardest-first at the right layer; QA @04:40Z clean
read-only exploratory sweep, zero intrusive input, filed nothing false; freshest dev-cycle.md HEAD-check rule
landed <1d ago → over-fit forbidden; honest no-change row appended). v0.3.2 ship-gate unchanged (FULLY MET —
release is your call, #914). Prior header below kept as history.)

_Earlier: 2026-06-21 18:22Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; #1149 now
QA-verified+closed; NO open team PR; one Dev cycle in-flight (#1133); NO new human-only item** →
**queue unchanged at 12** #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — HEAD `ab2c015` is orc `[skip ci]` (no run); last real-CI `17b5274` (#1153, *fixes #1149*)
**Build & Test + CodeQL both SUCCESS** @17:55Z → no STOP. **Step 1:** NO open team-Dev PR (remote =
`develop`+`main` only, Rule 14 clean). Community **#1055** (base `main`, fork, UNSTABLE → queued #1057,
human-only) → untouched; nothing merged/closed BY Orc (Rule 1). **Step 2:** no handoff owed; #1149
**QA-verified+closed @02:10Z** (PR #1153/`17b5274`). `status:done` open now = **#972** only (human-only) →
untouched; `status:in-progress` = **#1133** (Dev active) + **#766** (Ace umbrella). **Step 3.5**
competitiveness not due (6d < 7; due 06-23). **Step 3.6: no change — no new evidence** (only completed signal
since 17:52Z = QA #1149-verify, exemplary file-only matrix + anti-pipe-lie discipline; Dev #1133 in-flight;
freshest rules <1–3d exercised cleanly → over-fit forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release
is your call, #914). Prior header below kept as history.)

_Earlier: 2026-06-21 17:52Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; team-Dev PR #1153
(#1149) AUTO-MERGED itself green mid-cycle (`17b5274`) + #1149 flipped status:done; one fresh Dev-filed parity
tech-debt (#1154); NO new human-only item** →
**queue unchanged at 12** #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — HEAD `7a9295e` is orc `[skip ci]` (no run); last real-CI `d27240d` (#1151, *fixes #1139*)
**Build & Test + CodeQL both SUCCESS** @17:24Z → no STOP. **Step 1:** team-Dev PR **#1153**
(`fix/issue-1149…`→`develop`, *fixes #1149*) is **MERGEABLE + auto-merge ON** (squash, by Ace @17:51Z);
at cycle start was test-matrix IN_PROGRESS (early checks all SUCCESS) → Orc left it to land on its own;
**it auto-merged itself green as `17b5274` @17:55Z mid-cycle** (branch auto-deleted, Rule 14 clean).
Community **#1055** (base `main`, fork, UNSTABLE → queued #1057, human-only) → untouched; nothing merged/closed
BY Orc (Rule 1; #1153 landed via its own auto-merge). **Step 2:** **flipped #1149 → status:done** (Rule 1
handoff, merged `17b5274`, awaiting QA); `status:done` open now = **#1149** + **#972** (human-only) → #972
untouched; `status:in-progress` = **#766** only (Ace umbrella). Dev filed parity tech-debt
**#1154** (find/click `--image --threshold` same unvalidated-range class as #1149) — normal Dev work, no queue.
**Step 3.5** competitiveness not due (6d < 7; due 06-23). **Step 3.6: no change — no new evidence** (Dev #1149
[hardest-first probe + red-first TDD + auditable stash-rerun gate + mechanical public-API check + filed #1154
parity debt] and QA #1139-verify [physical Chrome-profile/CDP ground-truth, lateral 35-subcommand `--json`
sweep, ruled out a pipe-lie before any false report] both exemplary; freshest rules <1–3d exercised cleanly →
over-fit forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release is your call, #914). Prior header below
kept as history.)

_Earlier: 2026-06-21 17:22Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; team-Dev PR #1151
(#1139) MERGED in-cycle + #1139 flipped status:done; one fresh QA-filed P1 (#1150) feeding Dev; NO new human-only
item** → **queue unchanged at 12** #1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — merge commit `d27240d` (#1151, *fixes #1139*) **Build & Test SUCCESS**, CodeQL in-progress (no
failure) @17:24Z; prior real-CI `5e1df10` (#1148) both SUCCESS; my HEAD `[skip ci]` → no STOP. **Step 1:** team-Dev PR
**#1151** (`fix/issue-1139…`→`develop`, *fixes #1139*) **auto-merged itself green as `d27240d` @17:24Z** (squash,
auto-merge by Ace @17:20Z; Orc left it to land on its own — never merge outside a PR). **Branch auto-deleted (Rule 14
clean).** Community **#1055** (base `main`, fork, UNSTABLE → queued #1057, human-only) → untouched; nothing merged/closed
by Orc (Rule 1). **Step 2:** **flipped #1139 → status:done** (Rule 1 handoff, merged `d27240d`, awaiting QA);
`status:done` open now = **#1139** (just merged, awaiting QA) + **#972** (human-only) → #972 untouched;
`status:in-progress` = **#766** only (Ace umbrella). QA filed **#1150** (P1 — non-ASCII window titles → U+FFFD mojibake, cp936→UTF-8
decode data-loss, OS-ground-truth-confirmed) + **#1149** (P2 visual --threshold range-validation) — normal Dev work, no
queue. **Step 3.5** competitiveness not due (6d < 7; due 06-23). **Step 3.6: no change — no new evidence** (two completed
signals since 16:52Z both exemplary — QA @01:10Z root-caused #1150 vs independent ctypes `GetWindowTextW` ground truth,
ruled out harness-lie/stale-egg, zero false; Dev @01:25Z completed *interrupted* #1139 by adopt-and-verify of the prior
cycle's uncommitted branch [#935 hazard handled the safe way, not a blind reset --hard] with an auditable stash-rerun
gate + mechanical public-API check; freshest rules <1–3d exercised cleanly → over-fit forbidden). v0.3.2 ship-gate
unchanged (FULLY MET — release is your call, #914). Prior header below kept as history.)

_Earlier: 2026-06-21 16:52Z (Orc autonomous cycle — **quiet, healthy; develop GREEN; NO open team PR; one fresh
QA-filed bug (#1149) feeding Dev; NO new human-only item** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — last real-CI commit `5e1df10` (#1148, *fixes #1114*) **Build & Test + CodeQL both SUCCESS** @15:50Z;
HEAD `07dd443` is orc `[skip ci]` → no STOP. **Step 1:** NO open team-Dev PR (Rule 14 clean); only open PR = community
**#1055** (base `main`, fork, UNSTABLE → queued #1057, human-only) → untouched; nothing merged/closed by Orc (Rule 1).
**Step 2:** `status:done` open = **#972** only (human-only) → untouched, no handoff owed; `status:in-progress` = **#1139**
(P2 from:qa, Dev actively working 16:11Z — not abandoned) + **#766** (Ace umbrella). QA filed **#1149** (`visual
--threshold` not range-validated → false CI regression) — normal Dev work, no queue. **Step 3.5** competitiveness not due
(6d < 7; due 06-23). **Step 3.6: no change — no new evidence** (only completed signal since 16:22Z = QA cycle @00:45Z,
exemplary — ruled out a harness-lie before any false FAIL, cleaned up its own + 2 stray baselines, filed one genuine
defect #1149; Dev cycle @00:37 died on a loop-state.log file-lock = harness-infra transient tracked by #935, not a Dev
weakness; freshest rules <1–3d exercised cleanly → over-fit forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release
is your call, #914). Prior header below kept as history.)

_Earlier: 2026-06-21 16:22Z (Orc autonomous cycle — **quiet, healthy; #1114 now QA-verified+closed; one Dev
cycle in-flight (#1139 browser relative-path); NO open team PR; NO new human-only item** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — last real-CI commit `5e1df10` (#1148, *fixes #1114*) **Build & Test + CodeQL both SUCCESS** @15:50Z;
HEAD `8f037d8` is orc `[skip ci]` → no STOP. **Step 1:** NO open team-Dev PR (Rule 14 clean — #1148 branch auto-deleted);
only open PR = community **#1055** (base `main`, fork, UNSTABLE → queued #1057, human-only) → untouched; nothing
merged/closed by Orc (Rule 1). **Step 2:** **#1114 QA-verified+closed @00:18Z** (real-desktop filesystem ground-truth +
8 hermetic tests; QA caught a `.work/` subdir #969-class stale-egg and ruled it out before any false FAIL) → no handoff
owed; `status:done` open = **#972** only (human-only); `status:in-progress` = **#1139** (P2 from:qa, Dev actively
working, 16:11Z — not abandoned) + **#766** (Ace umbrella). **Step 3.5** competitiveness not due (6d < 7; due 06-23).
**Step 3.6: no change — no new evidence** (only completed signal since 15:52Z = QA #1114 verify @00:18Z, exemplary —
real-desktop filesystem ground-truth, caught + ruled out a #969-class stale-egg before any false FAIL, zero intrusive
input; Dev cycle still in-flight on #1139 → no completed Dev signal; freshest rules <1–3d exercised cleanly → over-fit
forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release is your call, #914). Prior header below kept as history.)

_Earlier: 2026-06-21 15:52Z (Orc autonomous cycle — **quiet, healthy; #1114 capture-cleanup never-lie fix now MERGED
(PR #1148, all-green); NO open team PR; NO new human-only item** → **queue unchanged at 12**
#1136/#1105/#1097/#1077/#1057/#975/#972/#969/#935/#915/#914/#897.
`develop` GREEN — HEAD `5e1df10` (#1148, *fixes #1114*) **Build & Test + CodeQL both SUCCESS** @15:53Z → no STOP.
**Step 1:** NO open team-Dev PR (Rule 14 clean — #1148 branch auto-deleted); only open PR = community **#1055** (base `main`,
fork, UNSTABLE → queued #1057, human-only) → untouched; nothing merged/closed by Orc (Rule 1). **Step 2:** Dev shipped #1114
(PR #1148 all-green, `status:done` set in-cycle) → no handoff owed; `status:done` open = **#1114** (awaiting QA — normal) +
**#972** (human-only); `status:in-progress` = **#766** only (Ace umbrella, 04:16Z, not abandoned). **Step 3.5** competitiveness
not due (5d < 7). **Step 3.6: no change — no new evidence** (both completed signals since 15:22Z exemplary — Dev #1114 fixed the
failed-crop never-lie defect + swept a latent ZERO_SIZE_ELEMENT mis-code, ran full suite, mechanical public-API guardrail, and
handled an orphaned-WIP #935 hazard the safe way [byte-identical base → adopt+self-review, not a blind wipe]; QA 15:40Z PASS
no-defects, ruled out 3 of its own flag-errors as harness lies and filed nothing false; freshest rules <1–3d exercised cleanly
→ over-fit forbidden). v0.3.2 ship-gate unchanged (FULLY MET — release is your call, #914). Prior header below kept as history.)

## Open decisions
| # | Decision | Why it's yours | Orc recommendation |
|---|----------|----------------|--------------------|
| [#1060](https://github.com/AcePeak/naturo/issues/1060) → **PR [#1170](https://github.com/AcePeak/naturo/pull/1170)** | **Sign off + merge `naturo find --ocr` (RapidOCR).** Dev opened PR #1170 (done-criterion #2 of v0.3.2), **full CI matrix green**, `MERGEABLE`/`CLEAN`, and **held auto-merge OFF on purpose** because it adds new public CLI/API surface: `--ocr` flag, `OCR_NOT_AVAILABLE`/`OCR_FAILED` error codes, `naturo.ocr_match` module (`find_text`/`TextMatch`/`load_engine`), and the `naturo[ocr]` optional extra. | **public-API sign-off** (same class as #1136/#1105) — a new CLI flag + new exported module + new packaging extra; the loop will not merge it unattended. | **Ratify + merge (recommended).** It implements exactly your #1077 RapidOCR decision and #1060 spec; additive, fail-loud (`OCR_NOT_AVAILABLE` recoverable with install hint when the extra is absent), offline/no-network, 20 hermetic tests + injectable engine (covers logic without the dep), `--collect-only` clean when `rapidocr` absent (no cross-platform break). After merge, QA verifies end-to-end with `pip install naturo[ocr]`. Or revise (rename/un-export module) before merge. |
| [#1169](https://github.com/AcePeak/naturo/issues/1169) → **PR [#1171](https://github.com/AcePeak/naturo/pull/1171)** | **Sign off + merge `find --selector` honoring `--backend`/`--depth`.** Dev root-caused #1169 (short-form `//Role` selectors miss on WinUI/XAML): `_find_with_selector` called `get_element_tree` **without** forwarding `--backend`/`--depth`, so it ran UIA-only @ depth 20 while the query path uses `auto` (UIA→hybrid→IA2/JAB/MSAA). PR #1171 threads the flags through; full CI matrix green, `MERGEABLE`/`CLEAN`, auto-merge **OFF**. | **public CLI-contract sign-off** — it changes the **default backend** of a shipped command (`find --selector` `uia` → `auto`), a behavior change on public output (same class as #1170/#1136). | **Ratify + merge (recommended)** — it aligns `find --selector` with the query path's auto-cascade (the moat behavior), is hermetically tested (4 cases asserting the forwarded kwargs + `auto` default), and refs #1169 (facet-2 desktop-wide "any app" search + live verify still remain). Or revise the default if you want `--selector` to stay UIA-only. |
| [#1136](https://github.com/AcePeak/naturo/issues/1136) | **Sign off (or revise/revert) the public API that landed unattended in #1134.** Team-Dev added a `selector` parameter to the public `BrowserPage.screenshot()` method + made the inert `naturo browser screenshot --selector` flag functional, merged `c00227e` (*fixes #1123*) with auto-merge **ON** before Orc could hold it. | **public-API sign-off** — a new public method parameter + an activated CLI contract; the guardrail holds even though the migration guide already promised `--selector` (the alternative, shrinking the doc / removing the flag, is yours). | **Ratify (recommended)** — small, additive, fail-loud (no-match / no-box / `--selector`+`--full-page` → exit 1, never a silent full-page fallback), 10 hermetic tests + real-Chrome e2e, honors the already-shipped flag; removing it would be breaking. Or revise (keyword-only/narrow) / revert (drop param + flag, amend guide). |
| [#1105](https://github.com/AcePeak/naturo/issues/1105) | **Sign off (or revert) the public API that landed unattended in #1104.** Team-Dev added `BrowserPage.set_download_dir()`/`wait_for_download()` + a `DownloadResult` dataclass **exported from `naturo.browser`**, merged `41b81ad` (part of #766). Dev correctly flagged it as public-API but auto-merged anyway. | **public-API sign-off** — a new public contract; even one that honors a committed doc is yours (shrinking the doc is the alternative). Process gap closed this cycle in `dev-cycle.md`. | **Ratify (recommended)** — the surface is small, additive, matches the committed migration guide, byte-parity tested; confirm and close #1105. Or revise (rename/un-export) / revert (drop methods + amend guide). |
| ~~#1097~~ | **RESOLVED 2026-06-28 (you provisioned the toolchain)** — MSVC 14.44 + CMake + Ninja installed on NATUROBOT, full `core` Release build proven (`naturo_core.dll`). #1097 closed; build recipe on #1097; pointer + async-handshake root-cause on #1096. **#1096 (JAB) is now Dev-buildable+verifiable locally** — every future native-core moat fix is unblocked. | — | _Done — no action needed; Dev will land #1096 + restore the verified `RECOGNITION.md` JAB row, QA will verify._ |
| ~~#1077~~ | **RESOLVED 2026-06-28** — you picked **RapidOCR** as an optional `naturo[ocr]` extra (MIT/Apache, offline, Chinese-strong, bundled ONNX). #1077 closed; **#1060 `find --ocr` unblocked & Dev-actionable.** | — | _Done — no action needed; Dev will ship #1060, QA will verify._ |
| [#1057](https://github.com/AcePeak/naturo/issues/1057) | **Dispose community PR #1055** (@muhamedfazalps, "consistent success envelope in set commands", fixes #1054). It targets `main` (must be `develop`), rewrites `naturo/cli/set_cmd.py` which **doesn't exist on develop** (real code: `values/_set.py`/`_get.py`), is a 452/452 whole-file rewrite, only fixes `set` not `get`, and adds a promo link; CI `UNSTABLE`. | **community PR handling** — guide / take over / close is yours; Orc cannot do it unattended | **Guide the contributor:** thank them, ask to retarget `develop` + minimal diff on `values/_set.py`+`_get.py` (drop the file-wide reformat) + cover `get`. If no iteration, close with thanks and let Dev fix #1054 (already v0.3.4, lane #865/#876/#977/#980/#1043). |
| [#975](https://github.com/AcePeak/naturo/issues/975) | **Ratify the QA re-enable.** After the LIVE R-SEC-012 reproduction, the loop fixed the root cause at the source (`7a10b18` — 第七轮 locked to argv/pytest-only) and **re-enabled QA** (`4097eba`, which asserts your authorization). QA has run **two clean cycles since** (verified+closed #876, filed #977 — argv-only, **nothing typed into any window**). | **security / safety sign-off** — the re-enable commit claims your authorization but is Orc-authored; ratifying (or reverting) it is yours | **Confirm + close #975.** The focus-race failure mode is no longer reachable from the standing playbook; the code backstop (`NATURO_SAFE_INPUT=1` + `~/.naturo/safe-input.lock`) is verified end-to-end. If you did **not** authorize the re-enable, say so and the loop will re-disable. Code-only hardening half tracked in #976 (Dev-actionable). |
| [#972](https://github.com/AcePeak/naturo/issues/972) | **Close the input-content safety guard** (status:done). The guard fix is merged (#973, `5508877`) and CLI-verified, but QA deferred *closing* it — a security-guard sign-off. | **security sign-off** — same class as #975 | **Confirm the guard is sufficient and close**, or fold into the #975 ratification (both are the same input-safety decision). |
| [#914](https://github.com/AcePeak/naturo/issues/914) | **v0.3.2 ship-gate sign-off** | release / tag to `main` = PyPI publish | **READY TO CUT — this is now the top actionable item.** Both ship-gate requirements are met: req (1) (epic #885 cluster) verified+closed; req (2) **all 5 status:done bugs verified+closed** (#786/#788/#807/#840 @01:15Z + #843 @02:42Z). `develop` CI green on `d3cfe92`. **Cutting / tagging v0.3.2 (tag→main = PyPI publish) is your call — the loop cannot and will not do it (Rule 2).** |
| [#969](https://github.com/AcePeak/naturo/issues/969) | **QA-harness integrity hazard** — the `naturo-qa` worktree's editable install (egg-link/`.pth`) resolves `import naturo`/`python -m naturo` to a **sibling worktree `naturo-qa-mariana`** (pre-#720 stale code). QA Step-2 runtime probes can **silently verify STALE code → false PASS/FAIL verdicts** (one FALSE FAIL already, 16:40Z #963). | machine-local env fix that touches another agent's worktree — Rule 4 forbids unattended self-fix; threatens the loop's verification signal | **Run `pip install -e .` from the `naturo-qa` worktree** (or fix the egg-link/`.pth`) so QA's import resolves to the worktree under test. The code-only loud-failure guard (assert `naturo.__file__` under the active worktree, fail loudly otherwise) is now tracked as **[#971](https://github.com/AcePeak/naturo/issues/971)** — Dev-actionable, the loop will ship it; this row remains the **env fix** which is human-only (Rule 4). Pairs with the #917 watchdog. |
| [#935](https://github.com/AcePeak/naturo/issues/935) | Two Dev cycles ran **concurrently in the shared `naturo-dev` worktree** — the 2nd cycle's Step 0 `reset --hard` wiped the 1st's in-flight uncommitted branch (#910). **Rule 4 violation at the orchestration layer.** | orchestration / scheduling policy (runner.ps1 / cron / lock) | Add a **per-worktree lock** in `naturo-loop-locks\` that a starting `runner:dev` must acquire (skip the round if held), and/or serialize dev so two cycles never share one tree. Self-fixing is unsafe — concurrent git ops would corrupt the peer cycle. |
| [#897](https://github.com/AcePeak/naturo/issues/897) | **Pick the canonical CLI exit-code contract for usage errors.** `type`/`press`/`find`/`wait`/`get`/`set`/`app launch` missing-required-arg exits **1**; Click-level parse errors (unknown cmd/opt) exit **2**. A POSIX `case $?` scripter misclassifies missing-arg as a transient op-failure and may infinite-retry. Fixing it fully **conflicts with the merged #872/#874 contract** (which deliberately set JSON-mode usage errors to exit 1). | **public CLI exit-code contract** (CLI-contract breaking, human-only guardrail) — reverses a recently-merged decision | **(A) usage errors = exit 2 everywhere** (text + JSON; POSIX-correct, satisfies #897, reverts #872/#874's JSON exit-1 + rewrites `test_subcommand_usage_error_json_872.py`) — **Orc + Dev recommend A**; or **(B)** keep JSON usage errors = exit 1, only fix text-mode in-body validators to exit 2 (documented text-vs-JSON split). Once you pick, Dev ships it in one cycle via a shared `exit_code_for_code` helper. Dev's full analysis is on the issue. |

## Recommended for closure (Orc cannot close needs:ace/QA items unattended — your confirm)
| # | What changed | Orc recommendation |
|---|--------------|--------------------|
| [#915](https://github.com/AcePeak/naturo/issues/915) | "QA loop down ~5 days / 403". **Fully recovered.** QA has run **many** clean rounds since the proxy auto-detect fix (`2ccbcf0`) — 16:43/17:42/18:50/20:45/21:40/22:40 on 06-16, then 00:45Z and a full **real-input ship-gate verification round at 01:15Z** that closed 4 P0/P1 bugs. The 403 era is over. | **Close #915.** Durability is demonstrated across a day+ of rounds incl. live input. |
| [#863](https://github.com/AcePeak/naturo/issues/863) | "SendInput blocked in agent session — runtime verification impossible." **Premise disproven.** QA's 01:15Z probe-first gate (launch throwaway notepad → `type "QA_PROBE"` → confirm window title) showed **input works on this no-RDP console** and verified all 4 input-family bugs end-to-end. Capability landed in `19a72cd`. | **QA to close #863** (it owns the `from:qa` issue). No human input-session provisioning is needed. Orc left it for QA rather than closing cross-domain. |

_Resolved earlier: **#913** (dispose community PRs #892 / #904) — closed 2026-06-16; both community PRs closed._

## Ship-gate status — v0.3.2  →  **FULLY MET (release is Ace's call, #914)**
- (1) Epic **#885** (silent-failure cluster): **CLOSED + verified 2026-06-16** (with #868/#875/#878/#883/#893).
  **Requirement (1) MET.**
- (2) QA-verify the 5 `status:done` bugs on a real desktop: **#786, #788, #807, #840** → **VERIFIED + CLOSED
  2026-06-17 01:15Z**; **#843** → **VERIFIED + CLOSED 2026-06-17 02:42Z** (runtime composite check confirms
  the #948 Z-order fix; `test_capture_popup_843.py` 12/12). **Requirement (2) MET — `status:done` ship-gate
  queue empty.**
- **Both requirements satisfied. The only remaining action is cutting / tagging the release (#914) —
  human-only (Rule 2); the loop will not tag `main`.**

## Blocks
- **QA verification UNBLOCKED — QA role re-enabled (`4097eba`) and running safely.** The 19:40 hard-disable
  was resolved at the source (`7a10b18` locked 第七轮 to argv/pytest-only); QA has run two clean cycles since
  (closed #876, filed #977). #975 now awaits only Ace's *ratification* of the re-enable, not a re-enable.
- **None blocking the ship-gate itself.** #843 (capture popup compositing) **verified+closed 2026-06-17
  02:42Z** — the last v0.3.2 ship-gate item is cleared. v0.3.2 awaits only Ace's release sign-off (#914).
- `develop` CI: **not red** — HEAD `d84e9c6`/#1118 Build & Test + CodeQL **SUCCESS** @22:51Z; later commits (`ccfb4f2` + this cycle) are `[skip ci]` orc → no new run. **New since last cycle:** QA-filed **#1119** (P1 — `naturo browser screenshot` crashes 100%, `**params` unpack; Dev-actionable, in backlog) and Dev opened **#1115** (P-unlabeled migration-guide ms-vs-seconds `--timeout` doc bug, `status:in-progress`). Recent team-Dev lands: **#1117** (`test: prove Anti-Detection Before/After equivalence row`, part of #766 → `8e8b1fb`; test-only, **no public surface**; umbrella **#766 still open**), **#1116** (`docs: correct migration guide wait surface to shipped API`, fixes #1112 → `55fa4bc`; **#1112 QA-verified+closed**), **#1104** (`File Download migration-equivalence row + honor documented download page API`, part of #766 → `41b81ad`; **added public API → needs:ace #1105**; umbrella **#766 still open**, status:in-progress, remaining slider-captcha row human-gated), **#1103** (`map 9 unmapped ErrorCode members to real categories`, *fixes #1101* → `a52c953`, **#1101 status:done awaiting QA**), **#1102** (`RECOGNITION.md` JAB never-lie interim caveat, *fixes #1098* → `9896664`, **#1098 status:done awaiting QA**), **#1099** (`eN stale-ref → registered STALE_SNAPSHOT_CACHE envelope`, *fixes #1086* → `3d30438`, **QA-verified+closed 01:45Z**), **#1095** (`iframe migration-guide → shipped frame API`, *fixes #1082* → `b3cbfe3`, **QA-verified+closed 00:45Z**), **#1094** (`migration-guide network section → shipped API`, *fixes #1088* → `5714587`, **QA-verified+closed 00:15Z**), **#1093** (`naturo click --image` shortcut, *fixes #1059* → `f04b0d8`, **QA-verified+closed 00:15Z**). Earlier (#766 migration-equivalence matrix): **#1092** (`hover-reveal-menu` → `afc6dde`), **#1091** (`image-captcha click-offset` + fix dead `captcha-image.html` fixture → `a14a46d`), **#1090** (`tab-management` + dead `tabs.html` fixture → `bcda034`), **#1087** (`network interception` → `9fa3183`). Earlier: **#1076** (`add --remote-allow-origins to browser launch so CDP can connect`, fixes #1075 → `847dc99`, **#1075 status:done awaiting QA**), **#1074** (`JAB auto-fallback test desktop-determinism`, fixes #1069 → `832a1ac`, **QA-verified+closed 18:10Z**), **#1073** (`offline browser migration fixtures`, part of #766 → `f56a760`), **#1072** (`honor find --image --screenshot` → `91ce240`, **QA-verified+closed 17:10Z**), preceded by #1068 (JAB auto-cascade) + #1071 (find `--selector`). All Rule-1 ancestors; branches auto-deleted (Rule 14 clean — `gh api branches` = develop + main only). The earlier `find --image` (#1066) + JAB init (#932) moats remain LIVE. One open PR: community **#1055** (base `main`, `UNSTABLE`) — queued as #1057, not merged/touched (its head lives on the contributor's fork).
- Desktop CI runner #842 / cloud-VM #860 **CLOSED 2026-06-17 (NOT_PLANNED)** — the local QA loop on
  NATUROBOT superseded the offline self-hosted runner (proven on the v0.3.2 ship-gate bugs); reopen only
  if per-PR pre-merge desktop CI gating becomes a hard requirement. No longer a human-decision block.
- _Cleared this cycle:_ **#863** (input verification — proven possible) and **#915** (QA auth — recovered)
  are no longer blocks; both recommended for closure above.
- _Related (not a human decision):_ [#917](https://github.com/AcePeak/naturo/issues/917) (P1,
  `silent-failure`) — `runner.ps1` still has no failure-streak watchdog. Code-only for Dev.

---
_How this works: anything irreversible or human-only is queued here instead of acted on. Everything else
the loop does itself — opens PRs, merges green ones to develop, verifies on the real desktop, closes issues,
files new work. See `agents/local/README.md`._
