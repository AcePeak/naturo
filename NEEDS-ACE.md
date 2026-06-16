# NEEDS-ACE — Human-Decision Queue

> The autonomous naturo loop (Dev / QA / Orch) runs unattended and self-closes everything it can.
> This file is the short list of things **only Ace can decide**. Refreshed by the Orchestrator each
> review cycle. Read this first on a check-in. Each item also has a GitHub issue labelled `needs:ace`.

_Last refreshed: 2026-06-17 00:30 (Orc autonomous cycle — stuck-PR triage. Fixed the only red item: team PR **#945** (refactor #856) was BLOCKED on 9 `mypy` `has-type` errors from an import-cycle alias in the `_browser` split; **Dev force-pushed a structural fix** (`_group.py`); it cleared Lint and **#945 auto-merged to develop (`6112800`)** this cycle. Orc did the post-merge handoff (flipped #856→status:done, branch deleted). Orc had built a parallel fix in an isolated worktree and **backed off** when Dev's landed first — a **second near-miss of #935** (Orc-vs-Dev push race), but **no work lost** thanks to Rule-4 worktree isolation; evidence appended to #935. develop CI **green**. **No new human-decision items** — queue unchanged below.)._

## Open decisions
| # | Decision | Why it's yours | Orc recommendation |
|---|----------|----------------|--------------------|
| [#935](https://github.com/AcePeak/naturo/issues/935) **(NEW)** | Two Dev cycles ran **concurrently in the shared `naturo-dev` worktree** (~18:07) — the 2nd cycle's Step 0 `reset --hard` wiped the 1st's in-flight uncommitted branch (#910). **Rule 4 violation at the orchestration layer.** | orchestration / scheduling policy (runner.ps1 / cron / lock) | Add a **per-worktree lock** in `naturo-loop-locks\` that a starting `runner:dev` must acquire (skip the round if held), and/or serialize dev so two cycles never share one tree. Self-fixing is unsafe — concurrent git ops would corrupt the peer cycle. |
| [#915](https://github.com/AcePeak/naturo/issues/915) | QA loop auth — **recovering, no longer down.** After the proxy auto-detect fix (`2ccbcf0`) QA authenticated and verified real work; the last 403 was the 16:00 round — now **6 clean runner rounds since (16:43, 17:42, 18:50, 20:45 #844, 21:40 #777, 22:40 #861)**. _Honest caveat: recovery is on the runner/proxy path; the bare hourly `claude -p` logs still 403 — not yet root-caused._ | credentials / auth / proxy | **One more clean day → close #915.** The ship-gate auth block is gone (#863 SendInput is now the binding verify gate). No longer the top item. |
| [#863](https://github.com/AcePeak/naturo/issues/863) | **`SendInput` blocked in the unattended agent session** — true end-to-end runtime verification of `type`/`click`/`press` is impossible, so QA can't fully close input-family ship-gate bugs (#788 deferred for this) | session/desktop input policy (RDP/headless vs interactive console) | This now gates the *remaining* ship-gate verification more than #915. Decide how QA gets a real interactive input session (console autologon / unlocked physical session / dedicated VM). Unit tests pass; only live runtime closure is blocked. |
| [#842](https://github.com/AcePeak/naturo/issues/842) / [#860](https://github.com/AcePeak/naturo/issues/860) | Desktop CI: self-hosted runner ROBOT-COMPILE offline (#842) vs fund a cloud Windows VM (#860) | infra spend | Decide: revive the runner, fund a cloud Windows VM, or accept GitHub-hosted-only CI. A cloud VM (#860) could also solve #863 (a real interactive session for input verification). |
| [#914](https://github.com/AcePeak/naturo/issues/914) | v0.3.2 ship-gate sign-off | release / tag to `main` = PyPI publish | **Closer now** — requirement (1) (epic #885) is verified+closed. Remaining: verify 5 `status:done` bugs (#786/#788/#807/#840/#843); input-family ones gated on #863. When all flip to `verified`, cutting v0.3.2 is your call. |

_Resolved since last cycle: **#913** (dispose community PRs #892 / #904) — closed 2026-06-16; both
community PRs are now closed (#892 superseded by merged #911, #904 by the team's #844 carry-forward)._

## Ship-gate status — v0.3.2
- (1) Epic **#885** (silent-failure cluster): **CLOSED + verified 2026-06-16** (with #868/#875/#878/#883/#893).
  Fix landed via PR #911. **Requirement (1) MET.**
- (2) QA-verify 5 `status:done` bugs on a real desktop: **#786, #788, #807, #840, #843**. QA is running
  again and is picking these up. **#788 and #843 both deferred** pending **#863** (input commands and
  #843's final menu-capture acceptance need a real `SendInput`-capable session); #843's composite-capture
  path was otherwise verified non-intrusively (7/7 unit + live `capture --pid`). #807/#840 are input-class
  (gated on #863); #786 is a UWP menu *click* (also input-gated). **Net: all 5 are now gated on #863** —
  the auth block (#915) is no longer the obstacle. Cutting v0.3.2 effectively waits on the #863 session
  decision (or the cloud VM #860 that would provide it).

## Blocks
- **#863 (P0)** — `SendInput` blocked in the unattended agent session; gates true end-to-end verification
  of input-family ship-gate bugs. This is now the binding ship-gate verification constraint.
- **#915** — QA auth **recovering** (~5 clean runner rounds, last 403 = 16:00 hourly); monitor one more day, then close. No longer a hard block.
- Desktop CI runner **#842** offline (chronic).
- `develop` CI: **green** (no block this cycle).
- _Related (not a human decision):_ [#917](https://github.com/AcePeak/naturo/issues/917) (P1,
  `silent-failure`) — `runner.ps1` still has no failure-streak watchdog; the earlier ~5-day 403 outage
  went undetected. Code-only for Dev; equally useful for confirming the recovery is durable.

---
_How this works: anything irreversible or human-only is queued here instead of acted on. Everything else
the loop does itself — opens PRs, merges green ones to develop, verifies on the real desktop, closes issues,
files new work. See `agents/local/README.md`._
