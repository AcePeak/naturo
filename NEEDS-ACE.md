# NEEDS-ACE — Human-Decision Queue

> The autonomous naturo loop (Dev / QA / Orch) runs unattended and self-closes everything it can.
> This file is the short list of things **only Ace can decide**. Refreshed by the Orchestrator each
> review cycle. Read this first on a check-in. Each item also has a GitHub issue labelled `needs:ace`.

_Last refreshed: 2026-06-29 1052Z (Orc autonomous cycle — **LOOP HEALTHY & CONVERGING; develop GREEN; queue 13→8 after your check-in.**
Since 1022Z: **your check-in landed + one QA cycle.** **You @02:39Z merged PR #1171** (`3a5df92`, "honor `--backend`/`--depth` in `find --selector`, refs #1169")
— that **signs off the `find --selector` public-CLI-default gate** (`uia`→`auto`); develop CI GREEN; branch auto-deleted. It was "refs" (partial), so **#1169 stays
`status:in-progress`** for the remaining facet-2 work (role-only match + desktop-wide "any app" search) — normal Dev work now, off your queue. You also **closed #972**
(input-content safety guard) + **#975** (QA re-enable ratified), and **removed `needs:ace` from #915** (QA-403 recovery, left open) and **#1060** (`--ocr`; PR #1170 still
**CONFLICTING/unmerged** — you appear to be handling `--ocr` directly, so the loop will NOT re-queue it or touch the PR beyond the standing rebase flag). **Queue is now 8.**
**QA @02:45Z filed NEW P1 #1190** — the reusable `app://*`-wildcard-host selector that `see`/`find` emit does **NOT round-trip standalone** (paste into
`click`/`type`/`find --selector` with no `--hwnd`/`--app` → `SELECTOR_NOT_FOUND`), breaking the advertised see→copy→click workflow. **Dev-actionable, not a human gate**
— flagged below only because it bears on the v0.3.2 ship decision (#914). Recognition moat **criterion #1 stays FULLY MET**.
**Step 1:** #1170(`--ocr`, CONFLICTING, you de-queued) untouched; #1167(dependabot)/#1055(community) base=`main`, human-only (Rule 2) → untouched; nothing merged/closed BY
Orc (Rule 1); Rule 14 clean (remote = main+develop+dependabot+`fix/issue-1060-find-ocr`). **Step 3.6** ONE change shipped (qa-cycle.md verify-completeness principle from the
#1184-verified-then-#1190-broke round-trip). The decision table below is the durable digest.)

## Open decisions (8)
| # | Decision | Why it's yours | Orc recommendation |
|---|----------|----------------|--------------------|
| [#914](https://github.com/AcePeak/naturo/issues/914) | **v0.3.2 ship-gate sign-off** — cut release / tag `main`. | release / tag to `main` = PyPI publish (Rule 2) | **Formal ship-gate is MET** (req 1 epic #885 + req 2 the 5 status:done bugs, all verified+closed; recognition criterion #1 FULLY MET; develop CI green). **⚠️ One judgment call before you cut:** QA just filed **P1 #1190** — the *reusable selector* that `see`/`find` emit doesn't round-trip standalone (the `app://*` host fails with no `--hwnd`/`--app`). It's not a formal ship-gate requirement, but it dents the v0.3.2 find-engine "copy a selector and reuse it" story. **Recommend: let Dev land #1190 (it's P1, repro + fix options in the issue, a round-trip regression test requested) before cutting**, or cut now and treat #1190 as a v0.3.2.1 follow-up — your call. Tag→`main` is yours; the loop will not (Rule 2). |
| [#1168](https://github.com/AcePeak/naturo/issues/1168) | **Pick a persistent scheduler.** Dev/QA crons are **session-only** — they fire only while an Orch Claude session is alive and auto-expire after 7 days, so the loop freezes (no merges/verifies) whenever no Orch session runs. The meta-blocker behind recurring multi-day freezes. | infra / scheduling decision (Windows Task Scheduler vs cloud VM vs status-quo) | **(A) Windows Task Scheduler** [recommended — durable, local, free] / (B) cloud VM (#860) / (C) status quo. Pair with watchdog #917 + worktree-lock #935. |
| [#1136](https://github.com/AcePeak/naturo/issues/1136) | **Sign off (or revise/revert) the public API that landed unattended in #1134** — a `selector` param on `BrowserPage.screenshot()` + an activated `naturo browser screenshot --selector` flag (merged `c00227e`, *fixes #1123*, auto-merge ON before Orc could hold it). | **public-API sign-off** — new public method param + activated CLI contract | **Ratify (recommended)** — small, additive, fail-loud (no-match / no-box / `--selector`+`--full-page` → exit 1, never a silent full-page fallback), 10 hermetic tests + real-Chrome e2e, honors the already-shipped flag. Or revise (keyword-only/narrow) / revert (drop param + flag, amend guide). |
| [#1105](https://github.com/AcePeak/naturo/issues/1105) | **Sign off (or revert) the public API that landed unattended in #1104** — `BrowserPage.set_download_dir()`/`wait_for_download()` + a `DownloadResult` dataclass **exported from `naturo.browser`** (merged `41b81ad`, part of #766; Dev flagged it but auto-merged anyway). | **public-API sign-off** — a new public contract | **Ratify (recommended)** — small, additive, matches the committed migration guide, byte-parity tested; confirm + close #1105. Or revise (rename/un-export) / revert (drop methods + amend guide). |
| [#1057](https://github.com/AcePeak/naturo/issues/1057) | **Dispose community PR #1055** (@muhamedfazalps, "consistent success envelope in set commands", fixes #1054) — targets `main` (must be `develop`), rewrites a file that doesn't exist on develop (real code: `values/_set.py`/`_get.py`), a 452/452 whole-file rewrite, only fixes `set` not `get`, adds a promo link; CI `UNSTABLE`. | **community PR handling** — guide / take over / close is yours; Orc cannot do it unattended | **Guide the contributor:** thank them, ask to retarget `develop` + minimal diff on `values/_set.py`+`_get.py` (drop the file-wide reformat) + cover `get`. If no iteration, close with thanks and let Dev fix #1054 (already v0.3.4). |
| [#969](https://github.com/AcePeak/naturo/issues/969) | **QA-harness integrity hazard** — the `naturo-qa` worktree's editable install resolves `import naturo` to a **sibling worktree `naturo-qa-mariana`** (pre-#720 stale code); QA runtime probes can **silently verify STALE code → false verdicts**. | machine-local env fix that touches another agent's worktree — Rule 4 forbids unattended self-fix; threatens the verification signal | **Run `pip install -e .` from the `naturo-qa` worktree** (or fix the egg-link/`.pth`). The code-only loud-failure guard (assert `naturo.__file__` under the active worktree) is tracked as **#971** (Dev-actionable); this row is the **env fix** (human-only, Rule 4). |
| [#935](https://github.com/AcePeak/naturo/issues/935) | Two Dev cycles ran **concurrently in the shared `naturo-dev` worktree** — the 2nd cycle's Step 0 `reset --hard` wiped the 1st's in-flight branch. **Rule 4 violation at the orchestration layer.** | orchestration / scheduling policy (runner.ps1 / cron / lock) | Add a **per-worktree lock** a starting `runner:dev` must acquire (skip the round if held), and/or serialize dev. Self-fixing is unsafe — concurrent git ops would corrupt the peer cycle. |
| [#897](https://github.com/AcePeak/naturo/issues/897) | **Pick the canonical CLI exit-code contract for usage errors.** `type`/`press`/`find`/`wait`/`get`/`set`/`app launch` missing-required-arg exits **1**; Click-level parse errors exit **2**. A POSIX `case $?` scripter misclassifies missing-arg as transient and may infinite-retry. Full fix **conflicts with the merged #872/#874 contract** (JSON-mode usage errors deliberately exit 1). | **public CLI exit-code contract** (CLI-contract breaking, human-only) — reverses a recently-merged decision | **(A) usage errors = exit 2 everywhere** (POSIX-correct, satisfies #897, reverts #872/#874's JSON exit-1) — **Orc + Dev recommend A**; or **(B)** keep JSON usage errors = exit 1, fix only text-mode validators (documented split). Once you pick, Dev ships it in one cycle via a shared `exit_code_for_code` helper. |

## Resolved by your check-in (no action needed)
- **#1171 / #1169** — you merged PR #1171 → `find --selector` public-CLI-default (`uia`→`auto`) **signed off**. #1169 stays in-progress for facet-2 (Dev work).
- **#972** — input-content safety guard **closed by you**. **#975** — QA re-enable **ratified + closed by you**.
- **#915** — QA-403 recovery **de-queued** (left open, `needs:ace` removed). **#1060/#1170 (`--ocr`)** — **de-queued** by you (PR still CONFLICTING/unmerged; the loop will not touch it — you own `--ocr`).

## Recommended for closure (Orc cannot close `from:qa` items unattended — your/QA confirm)
| # | What changed | Orc recommendation |
|---|--------------|--------------------|
| [#863](https://github.com/AcePeak/naturo/issues/863) | "SendInput blocked in agent session — runtime verification impossible." **Premise disproven** — QA's probe-first gate showed input works and verified all 4 input-family bugs end-to-end. | **QA to close #863** (it owns the `from:qa` issue). No human input-session provisioning is needed. |

## Ship-gate status — v0.3.2  →  **FORMAL GATE MET (release is Ace's call, #914)**
- (1) Epic **#885** (silent-failure cluster): **CLOSED + verified 2026-06-16**. **Requirement (1) MET.**
- (2) The 5 `status:done` bugs (#786/#788/#807/#840/#843): **ALL VERIFIED + CLOSED 2026-06-17.** **Requirement (2) MET.**
- **Recognition moat (separate done-criterion #1): FULLY MET** — Electron/CDP (#933), Java Access Bridge (#1096, live-verified+closed 06-29 01:20Z), `docs/RECOGNITION.md` matrix (#982).
- **⚠️ Fresh quality flag (not a formal gate item):** **P1 #1190** — reusable `app://*` selector doesn't round-trip standalone. Dev-actionable; consider landing before cutting (see #914 row).

## Blocks
- **`develop` CI: not red** — HEAD `3a5df92` (#1171, *honor `--backend`/`--depth` in `find --selector`*) Build & Test + CodeQL **SUCCESS** → no STOP.
- **None blocking the formal ship-gate** — v0.3.2 awaits only Ace's release sign-off (#914); #1190 is a quality judgment call, not a gate requirement.
- _Related (not a human decision):_ [#917](https://github.com/AcePeak/naturo/issues/917) (P1, `silent-failure`) — `runner.ps1` still has no failure-streak watchdog. Code-only for Dev.

---
_How this works: anything irreversible or human-only is queued here instead of acted on. Everything else
the loop does itself — opens PRs, merges green ones to develop, verifies on the real desktop, closes issues,
files new work. See `agents/local/README.md`._
