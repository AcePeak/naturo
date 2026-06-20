# NEEDS-ACE — Human-Decision Queue

> The autonomous naturo loop (Dev / QA / Orch) runs unattended and self-closes everything it can.
> This file is the short list of things **only Ace can decide**. Refreshed by the Orchestrator each
> review cycle. Read this first on a check-in. Each item also has a GitHub issue labelled `needs:ace`.

_Last refreshed: 2026-06-20 14:52 (Orc autonomous cycle — **quiet/healthy; NO new human-only item — queue
unchanged.** develop NOT red, nothing closed by Orc (Rule 1), one priority-honesty triage (milestoned QA bug
#1065 → v0.3.4).** 🟢 **THE RECOGNITION MOAT IS LIVE:** since 14:22 the Dev cycle **landed #932 (Java Access
Bridge) as `866193e`** (PR #1064) — root cause was a never-correct native init (`jab.cpp` resolved
`initializeAccessBridge`, a symbol the shipped DLL never exported; real export is `Windows_run`) + a missing
message-pump settle. Dev fixed it, **verified end-to-end** (UIA sees 0 Swing controls; `naturo see --backend
jab` recovers Submit/Cancel buttons, Customer-Name edit, Express-Shipping checkbox, Catalog tree via a
CI-built DLL), and **CI's Build C++ Core (Windows) passed**. #932 stays OPEN (multi-part: RECOGNITION.md
numbers + click/type-via-JAB remain) — Dev self-cleared `status:in-progress`. This is the #1 standing
priority (recognition supremacy) **shipped, not just unblocked.** The 14:37Z Dev cycle then picked up the
next moat slice **#1059** (`find --image`, `status:in-progress`, fresh) → left untouched (Rule 4). QA's
14:42Z cycle filed new bug **#1065** (`app focus/move/… --app` matches window title only, not process name —
inconsistent with `see`/`capture`/`list windows`); sibling of #1058 under the #871 umbrella, a bug-fix toward
consistency → Orc milestoned **#1065 → v0.3.4** (not human-only). The one open PR is still community **#1055**
(already queued **[#1057](https://github.com/AcePeak/naturo/issues/1057)**) — Orc did **not** comment/take-over/
close it. **Step 3.6 (evolve the team):** the #871 harmonization shipped surface-only parity (aligned which
flags each command accepts, not what `--app` *resolves to*) → two QA bugs #1058+#1065 in back-to-back cycles;
added a `dev-cycle.md` self-review rule requiring a **cross-command parity test** for shared flags vs the
gold-standard command (logged in `agents/EVOLUTION.md`). **Live needs:ace queue
#1057/#975/#972/#969/#935/#915/#914/#897 (unchanged).** `develop` CI: HEAD `866193e` (#1064)
**Build & Test + CodeQL SUCCESS** → **develop not red.** v0.3.2 ship-gate unchanged (FULLY MET — release is
your call, #914). Weekly competitiveness step not due (<7d since 06-16)._

## Open decisions
| # | Decision | Why it's yours | Orc recommendation |
|---|----------|----------------|--------------------|
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
- `develop` CI: **green** — Build & Test + CodeQL **SUCCESS** on `866193e`/#1064 (HEAD) → **not red.** Team-Dev **PR #1064 landed** (`fix: initialize Java Access Bridge via Windows_run + pumped settle (#932)`) — **the v0.3.2 recognition moat is now LIVE** (JAB recognition working + verified end-to-end against a CI-built DLL; Build C++ Core Windows green). #932 stays OPEN (multi-part: RECOGNITION.md numbers + JAB click/type follow-ups), Dev self-cleared `status:in-progress` → pickable; source branch auto-deleted (Rule 14 clean). One open PR: community **#1055** (base `main`, `UNSTABLE`) — queued as #1057, not merged/touched (its head lives on the contributor's fork). New QA bug **#1065** (`app … --app` matches title only, not process name) milestoned **v0.3.4** this cycle (sibling of #1058, #871 umbrella).
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
