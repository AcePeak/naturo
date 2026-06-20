# NEEDS-ACE — Human-Decision Queue

> The autonomous naturo loop (Dev / QA / Orch) runs unattended and self-closes everything it can.
> This file is the short list of things **only Ace can decide**. Refreshed by the Orchestrator each
> review cycle. Read this first on a check-in. Each item also has a GitHub issue labelled `needs:ace`.

_Last refreshed: 2026-06-20 15:26Z (Orc autonomous cycle — **NO new human-only item; queue unchanged
#1077/#1057/#975/#972/#969/#935/#915/#914/#897. develop NOT red, nothing closed by Orc (Rule 1).** Since the
14:54Z cycle: **QA** ran a clean exploratory L1 envelope sweep (15:12Z, **NO NEW BUG**, correctly ruled out 3
harness lies via the 20:22Z harness rule); **Dev** is **actively running** on **#1059** (find/click `--image`),
building the `naturo click --image` shortcut (the unmerged half of #1059; PR #1066 landed only `find --image`).
**Step 1 PR sweep:** no open team-Dev PR; only open PR = community **#1055** (already queued
**[#1057](https://github.com/AcePeak/naturo/issues/1057)**, base `main`, UNSTABLE) — Orc did **not**
comment/take-over/close it (community-PR handling is yours). **Step 2 health:** `status:in-progress` = **#1059**
only (active Dev cycle — Orc left the label + `naturo-dev` worktree untouched, Rule 4; legitimate in-scope
continuation, not abandoned); `status:done` open = **#972** only (human-only security, queued). Nothing for Orc
to close (Rule 1). **Step 3:** no new untriaged issue; top-updated issues all already triaged; milestones intact →
no new issue (Rule 9). **Step 3.6 (evolve the team): no change — no new evidence** — only completed signal is an
exemplary QA cycle; the #1059 re-claim was investigated and ruled NOT a weakness (in-scope multi-PR progress);
over-fit ban → honest ledger row. **Live needs:ace queue
#1077/#1057/#975/#972/#969/#935/#915/#914/#897.** `develop` CI: HEAD `afc6dde` (#1092) full **SUCCESS** (Build &
Test + CodeQL); orc tip `5292cf7` `[skip ci]` → **develop NOT red.** v0.3.2 ship-gate unchanged (FULLY MET —
release is your call, #914). Weekly competitiveness step not due (<7d since 06-16)._

## Open decisions
| # | Decision | Why it's yours | Orc recommendation |
|---|----------|----------------|--------------------|
| [#1077](https://github.com/AcePeak/naturo/issues/1077) | **Pick the OCR engine for `naturo find --ocr` (#1060)** — the last find-engine slice (#809). Dev parked it (2026-06-20 18:25Z) because the backend is a bundling/licensing/distribution choice. | **dependency/distribution decision** — bundle size, licensing, extra system binaries, Windows-only vs cross-platform; Orc must not pick a packaging path unattended | **Windows.Media.Ocr** (WinRT) — built into Win10/11, **no extra binary/model**, native to the Windows-first moat; keep it behind a thin interface so Tesseract can be added later as an optional cross-platform fallback. Once you pick, Dev lands #1060 in one cycle. |
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
- `develop` CI: **green** — Build & Test + CodeQL **SUCCESS** on `afc6dde`/#1092 (HEAD) → **not red.** Recent team-Dev lands (#766 migration-equivalence matrix): **#1092** (`hover-reveal-menu` → `afc6dde`), **#1091** (`image-captcha click-offset` + fix dead `captcha-image.html` fixture → `a14a46d`), **#1090** (`tab-management` + dead `tabs.html` fixture → `bcda034`), **#1087** (`network interception` → `9fa3183`). Earlier: **#1076** (`add --remote-allow-origins to browser launch so CDP can connect`, fixes #1075 → `847dc99`, **#1075 status:done awaiting QA**), **#1074** (`JAB auto-fallback test desktop-determinism`, fixes #1069 → `832a1ac`, **QA-verified+closed 18:10Z**), **#1073** (`offline browser migration fixtures`, part of #766 → `f56a760`), **#1072** (`honor find --image --screenshot` → `91ce240`, **QA-verified+closed 17:10Z**), preceded by #1068 (JAB auto-cascade) + #1071 (find `--selector`). All Rule-1 ancestors; branches auto-deleted (Rule 14 clean — `gh api branches` = develop + main only). The earlier `find --image` (#1066) + JAB init (#932) moats remain LIVE. One open PR: community **#1055** (base `main`, `UNSTABLE`) — queued as #1057, not merged/touched (its head lives on the contributor's fork).
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
