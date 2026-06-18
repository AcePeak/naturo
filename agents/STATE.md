# Naturo Project Status
> Maintained by Orc-Mycelium. Agents: read on every startup.
> Last refreshed: 2026-06-18 11:22 (Orc autonomous cycle — **quiet/healthy; one stuck Dev PR diagnosed +
> dispatched (#867 / PR #995, genuine red CI); develop not red; no new human-only item**. Since the 10:22
> refresh: the in-flight **#867** pickup surfaced as **PR #995** (`fix: exclude hidden commands from typo
> suggestions`, author AcePeak/team Dev, auto-merge SQUASH on 03:16Z) — but it is `BLOCKED` on **genuine red
> CI**: its own new `tests/test_fuzzy_group.py` hidden-command tests fail on the **Ubuntu 3.12 + macOS 3.12**
> lanes (`test_hidden_command_not_suggested` + `TestRealCliHiddenSuggestions::*` — all show
> `Error: No such command 'interna'. Did you mean 'internal'?`, i.e. the hidden command is still suggested),
> while passing on the Windows desktop. **Root cause (verified): CI runners resolve `click 8.4.1`; the desktop
> has `click 8.3.1`.** click ≥8.4 added a **native** command typo-suggester to `Group.resolve_command` that
> ignores `hidden=True`; PR #995's `FuzzyGroup._suggestable_commands` filters hidden commands only in its own
> `difflib` path, then falls through to `super().resolve_command()`, which on click 8.4.1 re-suggests the hidden
> command. The 8.3.1 desktop base resolver has no command-level "Did you mean" (confirmed locally: a plain
> `click.Group` emits only `No such command 'interna'.`), so the fix looked complete on the desktop — the classic
> "green on Windows, red on Linux/macOS". **Per orch-review Step 1 this is Dev-fixable, not human-only → dispatched
> a precise diagnostic + fix-direction comment on PR #995** (own the not-found path: when `cmd is None`, `ctx.fail`
> with a suggestion drawn only from `_suggestable_commands`, instead of delegating to `super().resolve_command()`;
> reproduce against click 8.4.1 on Linux, not the 8.3.1 desktop). Did **not** merge (red), did **not** touch the
> branch (Rule 4), auto-merge correctly held by the gate. **`status:in-progress` = #867** (active, PR #995 held by
> red gate); **`status:done` = #972** (input-content guard, code-verified, close = human security sign-off, queued).
> Branches `develop`+`main`+`fix/issue-867-...` (open PR — fine). **Step 3 (drive product): no new issue filed** —
> the #995 diagnosis/dispatch was the cycle's real Step-1 work; backlog is sharp + correctly prioritized
> (distribution next: **#926** `.mcpb` P1/pickable, **#922** registries P1, **#930** hero demo; recognition
> hardening env-blocked — #932 Java/no JDK, #934 SAP/no install). The desktop `click 8.3.1` vs CI `click 8.4.1`
> divergence is an env-honesty class (akin to #910/#969) but is addressed by the #995 fix being click-version-robust,
> so no standalone issue filed yet (Rule 9). Evidence in `.work/reviews/2026-06-18-1122-auto-review.md`. **needs:ace
> live queue unchanged #975/#972/#969/#935/#915/#914** (+ infra #860/#842) — **no new human-only item this cycle.**
> `develop` CI: last code commit `142bfe5` **Build & Test + CodeQL success** (HEAD `5d92fcb` = orc `[skip ci]`) →
> **not red** (the red is PR-branch-only). v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call, #914).
> Weekly competitiveness **not due** (baseline 2026-06-16, <7d).)_
>
> ---
> _Prior refresh: 2026-06-18 10:22 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA lap (#929
> quickstart verified+closed) + one active in-flight Dev pickup (#867); no open PRs, no new human-only
> item**. Since the 09:23 refresh: **QA verified+closed #929** @01:38:56Z (`verified`+`status:done` —
> the 5-minute Notepad/Claude quickstart, `docs/QUICKSTART.md`; QA replayed every copy-paste command on a
> real Win11 desktop with the live DLL — `--version`, `mcp tools` (64 live), tool descriptions,
> `list windows`, `see --window`, README above-fold link). Clean Dev→QA lifecycle, no Orc flip needed —
> this completes the **distribution onboarding arm's first concrete asset** (epic #922). The 10:07 Dev
> cycle then **picked up #867** (`'Did you mean' suggestions leak hidden 'snapshot' command`; P2/from:qa/
> v0.3.4) at 02:13:50Z (~8 min before sweep, **no branch pushed → active in-flight, left untouched, Rule
> 4**). **`status:in-progress` = #867** (active); **`status:done` = #972** (input-content guard,
> code-verified, close = human security sign-off, queued). **No open PRs;** branches `develop`+`main` only
> (Rule 14 clean). **Step 3 (drive product): no new issue filed** — backlog sharp + correctly
> prioritized. Recognition doc/proof arm complete (benchmark #931 + Electron #933 + #982 + README headline);
> remaining hardening env-blocked (#932 Java JAB, no JDK; #934 SAP, no install). Distribution is the next
> non-env-blocked thrust (**#926** `.mcpb` extension P1/pickable = recommended next Dev pickup, **#922**
> registry epic P1, **#930** hero demo, **#928** P2). #915 staleness ("QA down ~5d/403") already fully
> documented (Orc close-recs through 06-16 + NEEDS-ACE.md "Recommended for closure") → no re-spam (Rule 9).
> Evidence in `.work/reviews/2026-06-18-1022-auto-review.md`. **needs:ace live queue unchanged
> #975/#972/#969/#935/#915/#914** (+ infra #860/#842) — **no new human-only item this cycle.** `develop` CI:
> last code commit `142bfe5` **Build & Test success + CodeQL success** (HEAD `671c1c6` = orc `[skip ci]`)
> → not red. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call, #914). Weekly competitiveness
> **not due** (baseline 2026-06-16, <7d).)_
>
> ---
> _Prior refresh: 2026-06-18 09:23 (Orc autonomous cycle — **quiet/healthy; clean Dev self-land +
> post-merge handoff (#929 quickstart landed via PR #994) + Step-3 backlog sharpening; no open PRs, no
> new human-only item**. Since the 08:23 refresh: the in-flight Dev pickup **#929** ("docs: Automate
> Notepad in 5 minutes with Claude" quickstart; P1/v0.3.3, `from:orc`+`competitiveness`) **landed as PR
> #994** (`142bfe5`, `docs: 5-minute Notepad quickstart, copy-paste, first-try verifiable`, **fixes #929**)
> → `develop`. Source branch auto-deleted (only `develop`+`main` remain, Rule 14 clean). **Dev did the
> post-merge handoff itself** — #929 already `status:done` (flipped 01:14Z right after merge), **no Orc flip
> needed** → awaiting QA. **`status:in-progress` empty;** `status:done` = **#929** (Notepad quickstart,
> awaiting QA) **+ #972** (input-content guard, code-verified, close = human security sign-off, queued).
> **No open PRs.** This lands the **distribution onboarding arm's first concrete asset** (time-to-first-
> success quickstart), feeding epic #922. **Step 3 (drive product — backlog sharpening): commented on #923**
> (umbrella "5-minute Claude/Cursor quickstart + one-line install + hero demo") recommending **close-as-
> superseded** — all three of its scope items are now covered elsewhere: (1) Notepad quickstart → **#929
> landed** (PR #994); (2) one-line MCP install snippets → **#927 closed** (PR #965 + `test_readme_mcp_install.py`);
> (3) hero GIF/asciinema → tracked as **#930** (open). Nothing actionable remains under #923 not already done
> or in #930. **Did NOT close it** — it's an Ace-filed umbrella; left the close to Ace/next triage (Rule 9
> caution, avoid unattended closure of human-filed umbrellas). **No new issue filed** — distribution backlog
> is sharp + correctly prioritized (**#926** `.mcpb` extension P1/pickable = recommended next Dev pickup,
> **#922** registry epic P1, **#930** hero demo, **#928** registries-listing P2); a duplicate would be noise.
> Recognition doc arm complete (benchmark #931 + Electron #933 + #982 + README headline all done); recognition
> hardening remaining is env-blocked (#932 Java JAB, no JDK; #934 SAP, no install). Evidence in
> `.work/reviews/2026-06-18-0923-auto-review.md`. **needs:ace live queue unchanged
> #975/#972/#969/#935/#915/#914** (+ infra #860/#842) — **no new human-only item this cycle.** `develop` CI:
> HEAD `142bfe5` **Build & Test success + CodeQL success** → not red. v0.3.2 ship-gate unchanged (FULLY MET —
> release is Ace's call, #914). Weekly competitiveness **not due** (baseline 2026-06-16, <7d).)_
>
> ---
> _Prior refresh: 2026-06-18 08:23 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA lap (#982
> verified+closed) + one active in-flight Dev pickup (#929 quickstart); no open PRs, no new human-only
> item**. Since the 07:24 refresh: **QA verified+closed #982** @23:38Z (`verified`+`status:done` — the
> RECOGNITION.md headline coverage-matrix + per-framework how-to; clean Dev→QA lifecycle, no Orc flip
> needed). This completes the recognition moat's **documentation arm** (benchmark #931 + Electron #933 +
> #982 + README headline all done). The 00:07 Dev cycle then **picked up #929** ("docs: Automate Notepad
> in 5 minutes with Claude quickstart"; P1/v0.3.3, `from:orc`+`competitiveness`) at 00:11Z, ~12 min before
> sweep, **no branch pushed → active in-flight, left untouched (Rule 4)**. This is the distribution
> feed-forward pickup recommended last cycle. **`status:in-progress` = #929** (active); **`status:done` =
> #972** (input-content guard, code-verified, close = human security sign-off, queued). **No open PRs;**
> branches `develop`+`main` only (Rule 14 clean). **Step 3 (drive product): no new issue filed** — the
> recognition doc arm is complete; the next thrust is **distribution** (epic #922) and its backlog is sharp
> + correctly prioritized (**#926** `.mcpb` extension P1/pickable, **#923** quickstart+hero P1/pickable,
> **#922** registry epic P1; #927 closed), with **#929 in flight** — a duplicate would be noise (Rule 9).
> Recognition hardening remaining is env-blocked (#932 Java JAB, no JDK; #934 SAP, no install). Evidence in
> `.work/reviews/2026-06-18-0823-auto-review.md`. **needs:ace live queue unchanged
> #975/#972/#969/#935/#915/#914** (+ infra #860/#842) — **no new human-only item this cycle.** `develop`
> CI: HEAD `183b947` **Build & Test success + CodeQL success** → not red. v0.3.2 ship-gate unchanged (FULLY
> MET — release is Ace's call, #914). Weekly competitiveness **not due** (baseline 2026-06-16, <7d).)_
>
> ---
> _Prior refresh: 2026-06-18 07:24 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA handoff lap —
> the recognition headline pickup (#982) landed; no open PRs, no new human-only item**. Since the 06:23
> refresh: team Dev landed **PR #992** (`183b947`, `docs: copy-paste see/find/click how-to against the
> owned Electron fixture`, **fixes #982** — the RECOGNITION.md headline coverage-matrix + per-framework
> how-to that had been the recommended next recognition pickup since the 03:24 cycle) → `develop`. Source
> branch auto-deleted (only `develop`+`main` remain, Rule 14). **Dev did the post-merge handoff itself** —
> #982 already `status:done` (no Orc flip needed), awaiting QA. **`status:in-progress` empty;** `status:done`
> = **#982** (RECOGNITION.md headline, awaiting QA) **+ #972** (input-content guard, code-verified, close =
> human security sign-off, queued). **No open PRs.** **Step 3 (drive product): no new issue filed** — the
> recognition moat's documentation arm is now complete: #931 (benchmark) + #933 (Electron) closed, #982
> landed, and the **README headline is already done** (`README.md:13` "Why naturo?" leads with the
> multi-framework claim + links `docs/RECOGNITION.md` proof) → the Step-3 "coverage matrix as README
> headline" follow-through is SATISFIED. Remaining recognition hardening is **env-blocked** (#932 Java JAB,
> P0 — re-confirmed no JDK on PATH; #934 SAP, P2 — needs SAP install). **Next non-env-blocked move =
> distribution feed-forward** (#922/#927): #927 (MCP install snippets) closed; **recommended next Dev
> pickup = #926** (Claude Desktop Extension `.mcpb` — the highest-leverage one-click-install lever now that
> the recognition proof exists), with #923/#929 (quickstart/hero) also pickable P1. Evidence in
> `.work/reviews/2026-06-18-0724-auto-review.md`. **needs:ace live queue unchanged
> #975/#972/#969/#935/#915/#914** (+ infra #860/#842) — **no new human-only item this cycle.** `develop` CI:
> HEAD `183b947` **Build & Test success + CodeQL success** → not red. v0.3.2 ship-gate unchanged (FULLY MET —
> release is Ace's call, #914). Weekly competitiveness **not due** (baseline 2026-06-16, <7d).)_
>
> ---
> _Prior refresh: 2026-06-18 06:23 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA handoff lap
> (#866 landed via PR #990; Dev flipped it to status:done itself) + no open PRs; no new human-only
> item**. Since the 05:23 refresh: the in-flight Dev pickup **#866** (input-command exit-code contract —
> type/press/click now exit **1**, not Click's usage-error **2**, on NO_DESKTOP_SESSION; P2/from:qa)
> **landed as PR #990 → `a7f993b`** at 22:13Z, adding `tests/test_no_desktop_exit_contract_866.py`
> (new contract test). **Dev did the post-merge handoff itself** — #866 flipped `status:in-progress →
> status:done` at 22:14:52Z (right after merge), **no Orc flip needed** → awaiting QA. Source branch
> auto-deleted (Rule 14 — only `develop`+`main` remain). **`status:in-progress` empty;** `status:done` =
> **#866** (NO_DESKTOP exit-code contract, awaiting QA) **+ #972** (input-content guard, code-verified,
> close = human security sign-off, queued). **No open PRs.** **Step 3 (drive product): no new issue
> filed** — backlog sharp; the `-j` envelope drift class stays STRUCTURALLY CLOSED (#979 layer-1 + #987
> layer-2 both landed+verified) and #866 closes the NO_DESKTOP exit-code contract gap. **Recommended next
> recognition pickup = #982** (RECOGNITION.md headline matrix + per-framework how-to — re-confirmed
> OPEN/P1/v0.3.2/unassigned/pickable, `competitiveness`+`from:orc`; the non-env-blocked Step-3
> follow-through; #932 Java JAB still env-blocked, no JDK); already P1, no re-label. Evidence in
> `.work/reviews/2026-06-18-0623-auto-review.md`. **needs:ace live queue unchanged
> #975/#972/#969/#935/#915/#914** (+ infra #860/#842) — **no new human-only item this cycle.** `develop`
> CI: HEAD `a7f993b` **Build & Test success + CodeQL success** → not red. v0.3.2 ship-gate unchanged
> (FULLY MET — release is Ace's call, #914). Weekly competitiveness **not due** (baseline 2026-06-16, <7d).)_
>
> ---
> _Prior refresh: 2026-06-18 05:23 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA lap (#971
> verified+closed) + one active in-flight Dev pickup (#866); no new human-only item**. Since the 04:22
> refresh: (a) **QA verified+closed #971** @04:39 local — the code-only loud-failure worktree-integrity
> guard (9/9 `test_worktree_guard.py`; live WorktreeMismatchError on a mismatched root, exit 0 on
> correct/unset; clean Dev→QA lifecycle, no Orc flip needed); (b) the 05:07 Dev cycle **picked up #866**
> (input-command exit-code contract — type/press/click exit 2 vs see/capture/list exit 1 on
> NO_DESKTOP_SESSION; P2, from:qa) at ~21:18Z, ~5 min old at sweep, **no branch pushed → active in-flight,
> left untouched (Rule 4)**. **`status:in-progress` = #866** (active); **`status:done` = #972** (input-content
> guard — close is human security sign-off, queued). **No open PRs;** branches `develop`+`main` only (Rule 14
> clean). **Step 3 (drive product): no new issue filed** — backlog sharp, loop hourly, #866 in flight; the
> **`-j` envelope drift class stays STRUCTURALLY CLOSED** (#979 layer-1 + #987 layer-2 both landed+verified;
> a future `-j` regression is unmergeable). **Recommended next recognition pickup = #982** (RECOGNITION.md
> headline matrix + per-framework how-to — confirmed OPEN/P1/v0.3.2/unassigned/pickable; the non-env-blocked
> Step-3 follow-through; #932 Java JAB still env-blocked, no JDK); left pickable, already P1, no re-label.
> Evidence in `.work/reviews/2026-06-18-0523-auto-review.md`. **needs:ace live queue
> #975/#972/#969/#935/#915/#914** (+ infra #860/#842) — **no new human-only item this cycle.** `develop` CI:
> last code commit `53368b3` **CodeQL success + Build & Test success** (HEAD `5fb8c16` is an orc `[skip ci]`
> state commit) → not red. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call, #914). Weekly
> competitiveness **not due** (baseline 2026-06-16, <7d).)_
>
> ---
> _Prior refresh: 2026-06-18 04:22 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA lap + one Dev PR
> self-landing; no new human-only item**. Since the 03:24 refresh: (a) **QA verified+closed #987** @~03:39
> local — the layer-2 global `-j` stdout-purity contract (180/180 + guard-teeth proof: a deliberate stdout
> leak failed the contract across every walked node, then reverted clean; clean Dev→QA lifecycle, no Orc
> flip needed); (b) team Dev landed **PR #989** (`53368b3`, **fixes #971** — the code-only loud-failure
> guard that aborts when imported `naturo.__file__` resolves outside the active worktree; the Dev-shippable
> half of the #969 stale-sibling hazard, #969 env-fix remains human-only per Rule 4). Auto-merged 20:20Z;
> source branch **deleted** (Rule 14 — only `develop`+`main` remain). **#971 already `status:done`**
> (post-merge handoff done, awaiting QA) — no Orc flip needed. **`status:in-progress` empty;** `status:done`
> = **#971** (worktree-integrity guard, awaiting QA) **+ #972** (input-content guard, code-verified, close =
> human sign-off, queued). **No open PRs.** **Step 3 (drive product): no new issue filed** — backlog already
> sharp; the `-j` envelope drift class stays **STRUCTURALLY CLOSED** (#979 layer 1 + #987 layer 2 both
> landed+verified; a future `-j` regression is unmergeable). **Recommended next recognition pickup = #982**
> (RECOGNITION.md headline matrix + per-framework how-to, P1, v0.3.2, OPEN/pickable) — the non-env-blocked
> Step-3 follow-through (unlike #932, Java JAB, still env-blocked: no JDK on desktop); left pickable, already
> P1, no re-label. Evidence in `.work/reviews/2026-06-18-0422-auto-review.md`. **needs:ace live queue
> #975/#972/#969/#935/#915/#914** (+ infra #860/#842) — **no new human-only item this cycle.** `develop` CI:
> HEAD `53368b3` **CodeQL success, Build & Test in progress, no failures** (prior `73439ac` fully green) →
> not red. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call, #914). Weekly competitiveness
> **not due** (baseline 2026-06-16, <7d).)_
>
> ---
> _Prior refresh: 2026-06-18 03:24 (Orc autonomous cycle — **quiet/healthy; landed the #987 `-j`
> stdout-purity contract (layer 2) → the `-j` envelope drift class is now STRUCTURALLY CLOSED by two
> self-maintaining contracts**. Since the 02:28 refresh: team Dev landed **PR #988** (`73439ac`,
> `test: self-maintaining -j stdout-purity contract (layer 2)`, **fixes #987**) → develop, auto-merge
> SQUASH; source branch **deleted** (Rule 14 — only `develop`+`main` remain). This is the layer-2 contract
> I filed last cycle as the Dev-actionable follow-up to #979. **Dev did the post-merge handoff itself** —
> #987 already `status:done` (19:20:36Z, right after merge), no Orc flip needed. **`status:in-progress`
> empty;** `status:done` = **#987** (layer-2 contract, awaiting QA) **+ #972** (input-content guard,
> code-verified, close = human sign-off, queued). **No open PRs.**
> **Class-killer complete:** the reactive one-at-a-time `-j` cadence (#876→#977→#980→#874→#869→#872, ~6
> Dev+QA rounds in ~24h) is now covered by **two landed self-maintaining contracts** — **#979** (layer 1,
> `a8402af`, `@collection_read`/`success_envelope()` + Click-tree-walk; fails CI if any collection read
> drops `{success,<collection>,count}`) **and #987** (layer 2, `73439ac`; every command + eager option
> under `-j` emits exactly one JSON doc, zero extra stdout bytes — catches the #874/#869/#872 stray-text/
> eager-option sub-class the collection walk misses). A future `-j` regression is now **unmergeable, not a
> reactive fix** — joins the contract pattern (#912 desktop guard, #957 window-selector). **Step 3 (drive
> product): no new issue filed** — backlog already sharp. #932 (Java JAB proof) **re-confirmed env-blocked**
> (no JDK on desktop). **Recommended next recognition pickup = #982** (RECOGNITION.md headline matrix +
> per-framework how-to, P1, v0.3.2, pickable) — the Step-3 follow-through that is NOT env-blocked, unlike
> #932; left pickable, already correctly P1, no re-label. Evidence in
> `.work/reviews/2026-06-18-0324-auto-review.md`. **needs:ace live queue #975/#972/#969/#935/#915/#914**
> (+ infra #860/#842) — **no new human-only item this cycle.** `develop` CI: HEAD `73439ac` **CI Gate
> success, all required lanes green** (only Ubuntu/macOS 3.9 failed = non-blocking #910 tomllib gap) → not
> red. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call, #914). Weekly competitiveness **not
> due** (baseline 2026-06-16, <7d).)_
>
> ---
> _Prior refresh: 2026-06-18 02:28 (Orc autonomous cycle — **quiet/healthy; landed the #979 `-j` envelope
> CLASS-KILLER via a flaky-CI rescue + filed its layer-2 follow-up**. Since the 01:24 refresh: **QA
> verified+closed #872** @17:39Z (`-j` usage-error stray text — clean Dev→QA lap, no Orc flip needed) →
> `status:done` had drained to just **#972**. Team Dev's 02:07 cycle opened **PR #986**
> (`test/issue-979-json-envelope-contract` → develop, **fixes #979**, auto-merge SQUASH on) — the
> self-maintaining `-j` collection-read envelope contract I'd been pulling forward at P1. **It was BLOCKED on
> red CI**, so this :22 sweep diagnosed it: the **Ubuntu/macOS 3.9** failures are the **#910 tomllib gap**
> (continue-on-error, non-blocking — develop's own HEAD shows the same 3.9 reds with CI Gate still green); the
> **required `macOS 3.12`** lane failed on a **flaky** `test_browser_download.py::test_timeout_stuck_partial`
> timing assertion (passes on develop; #986 touches no browser code). **Root cause of the block = flakiness,
> not anything #986 introduced** (its own new `test_json_envelope_contract.py` passed). The failed jobs were
> already re-running; **monitored to completion → macOS 3.12 passed → CI Gate green → PR #986 auto-merged
> (`a8402af`, 18:26:49Z)**; source branch **deleted** (Rule 14 — only develop+main remain). Base ≠ default
> branch so no auto-close → **Orc post-merge handoff: flipped #979 `status:in-progress` → `status:done`**
> (awaiting QA) + QA verification note (run the contract test; confirm it discovers the known collection reads
> and that a deliberately-broken read fails it). **`status:in-progress` now empty;** `status:done` = **#979**
> (awaiting QA) **+ #972** (input-content guard, code-verified, close = human sign-off, queued). **No open PRs.**
> **Step 3 (drive product): filed #987** (`test`, `from:orc`, **P1**, v0.3.4) — the **global `-j` stdout-purity
> contract (layer 2)**. #979 (just landed) is layer 1 and kills the *collection-read* drift class
> (#876→#977→#980); it does **not** catch the **stray-text/eager-option** sub-class — **#874** (`-j --version`
> /`--help`), **#869** (install-prompt leak), **#872** (usage-error banner), three Dev+QA rounds in ~24h, none
> a missing `count`. #987 asserts every command + eager option under `-j` emits exactly one JSON doc with zero
> extra stdout bytes. This is the documented "layer 2" from #979's thread — filed as its own issue so it
> survives #979's closure; Dev-actionable, not human-only. Evidence in
> `.work/reviews/2026-06-18-0228-auto-review.md`. **needs:ace live queue #975/#972/#969/#935/#915/#914** (+ infra
> #860/#842) — **no new human-only item this cycle.** `develop` CI: merge commit `a8402af` Build&Test + CodeQL
> **in progress, no failures** (PR #986's checks were green at merge; prior HEAD `8b28270` GREEN) → not red.
> v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call, #914). Weekly competitiveness **not due**
> (baseline 2026-06-16, <7d). Recognition next move still **#932** (Java JAB proof — env-blocked, JDK absent).)_
>
> ---
> _Prior refresh: 2026-06-18 01:24 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA lap + one
> Dev PR self-landing; no new human-only item; no comment-spam on the `-j` class-killer**. Since the
> 00:27 refresh: **QA verified+closed #869** @16:39Z (`verified`+`status:done` — the `-j` optional-dep
> install-prompt leak; clean Dev→QA lifecycle, no Orc flip needed) → `status:done` drained to just
> **#972** (input-content guard, code-verified; close = human security sign-off, already queued). Team
> Dev opened **PR #985** (`fix/issue-872-subcommand-usage-error-json` → develop, **fixes #872** — unknown
> subcommand emits plain Click usage text in `-j` mode, bypassing the JSON envelope) with auto-merge
> SQUASH on (AcePeak 17:22Z) and **MERGED mid-cycle** (`8b28270`, @17:24Z) once its checks went green;
> source branch **deleted** (Rule 14 — only `develop`+`main` remain). Base ≠ default branch so it did NOT
> auto-close #872 → **Orc post-merge handoff: flipped #872 `status:in-progress` → `status:done`** (awaiting
> QA) + QA verification note (run a known-bad subcommand under `-j`, confirm stdout is exactly one
> `{success:false,…}` envelope, no plain Click banner, non-zero exit). **`status:in-progress` now empty;**
> `status:done` = **#872** (awaiting QA) **+ #972** (input-content guard, code-verified, close = human
> sign-off, queued). **No open PRs.**
> **Step 3 (drive product — the `-j` envelope class): #872/PR #985 is the THIRD `-j` bypass to land as a
> one-at-a-time fix** (after **#874** eager-options, **#984/#869** install-prompt leak): a usage-error
> stray-text leak — **not** a collection-read `count` drop, so #979's current collection-read-only scope
> would **not** catch it, but the **stdout-purity layer (2)** already recommended on #979 (16:26Z comment)
> would. The reactive cadence (#876→#977→#980→#874→#869→#872) continues unabated → **#979 is the correct
> class-killer; stays P1/pickable.** **Deliberately did NOT re-comment on #979** — the 13:24Z + 16:26Z
> Orc comments already document the two-layer (per-collection `count` **+** global `-j` stdout-purity)
> recommendation in full; a third comment in ~3h would be noise (Rule 9). Evidence recorded in
> `.work/reviews/2026-06-18-0124-auto-review.md`. **needs:ace live queue #975/#972/#969/#935/#915/#914**
> (+ infra #860/#842) — **no new human-only item this cycle.** `develop` CI: merge commit `8b28270` CI
> **in progress, no failures** (PR #985's own checks were green at merge; prior HEAD `01faff8` Build &
> Test + CodeQL GREEN) → not red. v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call, #914).
> Weekly competitiveness **not due** (baseline 2026-06-16, <7d). Recognition next move still **#932**
> (Java JAB proof — env-blocked, JDK absent).)_
>
> ---
> _Prior refresh: 2026-06-18 00:27 (Orc autonomous cycle — **quiet/healthy; clean Dev self-land +
> post-merge handoff + sharpened the `-j` class-killer**. Since the 23:24 refresh: team Dev landed **PR #984**
> (`01faff8`, `fix/issue-869-json-dep-prompt-leak` → develop, **fixes #869** — suppress the optional-dependency
> install prompt under `-j/--json` so stdout stays a single clean machine-parseable envelope instead of
> leaking the human-readable "install …?" prompt; `from:qa`, P2). Auto-merged 16:21Z, branch **deleted**
> (Rule 14 — only `develop`+`main` remain). Base ≠ default branch (`main`) so it did NOT auto-close →
> **Orc post-merge handoff: flipped #869 `status:in-progress` → `status:done`** (awaiting QA) + QA note.
> **`status:in-progress` now empty;** `status:done` = **#869** (awaiting QA) **+ #972** (input-content guard,
> code-verified, close = human sign-off, queued). **No open PRs.** **Step 3 (drive product — sharpen the
> backlog): commented on #979** widening the self-maintaining `-j` envelope contract. #869 is now the **second**
> `-j` bypass (after **#874**, the eager-option case) to land as a one-at-a-time fix that #979's current
> *collection-read-only* enumeration would **not** have caught — #869 is a stray-human-text leak, #874 an
> eager-option bypass, neither a missing `count`. Recommended #979 assert two layers: (1) the existing
> per-collection `count` check **+** (2) a **global `-j` stdout-purity** check (parse stdout → exactly one
> `{success,…}` JSON doc, zero extra bytes, for every command incl. `--version`/`--help`). Layer (2) is what
> kills the #874/#869 sub-class. #979 stays **P1/pickable**. **needs:ace live queue
> #975/#972/#969/#935/#915/#914** (+ infra #860/#842) — **no new human-only item this cycle.** `develop` CI:
> **Build & Test GREEN on HEAD `01faff8`**, CodeQL analyzing (no failures) → **not red**. v0.3.2 ship-gate
> unchanged (FULLY MET — release is Ace's call, #914). Weekly competitiveness **not due** (baseline 2026-06-16,
> <7d). Recognition next move still **#932** (Java JAB proof — env-blocked, JDK absent).)_
>
> ---
> _Prior refresh: 2026-06-17 23:24 (Orc autonomous cycle — **quiet/healthy; clean Dev self-land +
> post-merge handoff; no new human-only item**. Since the 22:24 refresh: team Dev landed **PR #983**
> (`20bb15f`, `fix/issue-874-json-eager-options` → develop, **fixes #874** — honour the global `-j/--json`
> flag on Click **eager options** so `naturo -j --version` / `-j --help` emit the JSON success envelope
> instead of plain text; +`tests/test_json_eager_options.py`, 11 cases). Auto-merged 15:21Z, branch
> **deleted** (Rule 14 — only `develop`+`main` remain). Base ≠ default branch (`main`) so it did NOT
> auto-close → **Orc post-merge handoff: flipped #874 `status:in-progress` → `status:done`** (awaiting QA)
> + QA verification note. **`status:in-progress` now empty;** `status:done` = **#874** (awaiting QA) **+
> #972** (input-content guard, code-verified, close = human sign-off, queued). **No open PRs.** **Step 3
> observation (left for #979's owner, not filed):** #874 is an envelope-honesty sibling of the
> #876→#977→#980 list/show drift class but is an **eager-option** bypass (`--version`/`--help`), *not* a
> collection read — so #979's self-maintaining `-j` contract (auto-enumerates collection reads for
> `{success,<collection>,count}`) would **not** have caught it; worth widening #979's scope to eager-option
> commands. #979 stays P1/pickable. **needs:ace live queue #975/#972/#969/#935/#915/#914** (+ infra
> #860/#842) — **no new human-only item this cycle.** `develop` CI: **Build & Test GREEN on HEAD
> `20bb15f`**, CodeQL python GREEN / c-cpp analyzing (no failures) → **not red**. v0.3.2 ship-gate unchanged
> (FULLY MET — release is Ace's call, #914). Weekly competitiveness **not due** (baseline 2026-06-16, <7d).
> Recognition next move still **#932** (Java JAB proof — env-blocked, JDK absent).)_
>
> ---
> _Prior refresh: 2026-06-17 22:24 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA lap + one
> priority-honesty triage**. Since the 21:25 refresh: **QA verified+closed #980** (the `list windows -j` /
> `list screens -j` missing-`count` envelope drift, sibling of #876/#977) — clean Dev→QA lifecycle, no Orc
> flip needed; `status:done` drained to just **#972** (security guard, code-verified, close = human
> sign-off, already queued). **No open PRs;** `status:in-progress` **empty**. **Orc this cycle (Step 3 —
> priority honesty): milestoned #910 → v0.3.4** (+ framing comment). #910 was floating unmilestoned but is a
> real **honest-claims defect**, not just a red non-required lane: `pyproject.toml` declares
> `requires-python=">=3.9"` and ships 3.9/3.10 classifiers, yet the code imports stdlib `tomllib` (3.11+)
> with **no `tomli` fallback** → the package **does not import on 3.9/3.10**; the 3.9 CI lane only looks
> non-blocking because it's `continue-on-error:true`, which hides the broken claim. Fix is Dev-shippable
> (tomli fallback + `tomli; python_version<"3.11"` dep) or an honest classifier narrowing (public-contract
> change → fallback preferred) — now pickable. **needs:ace live queue #975/#972/#969/#935/#915/#914**
> (+ infra #860/#842) — **no new human-only item this cycle.** `develop` CI: **Build & Test + CodeQL GREEN
> on HEAD `a30426a`** (`0bb3e48` is prior orc `[skip ci]` state commit) → not red. v0.3.2 ship-gate
> unchanged (FULLY MET — release is Ace's call, #914). #979 (P1 self-maintaining `-j` envelope contract)
> remains the class-killer for the #876→#977→#980 drift — pickable, left for Dev. Weekly competitiveness
> **not due** (baseline 2026-06-16, <7d). Recognition next move still **#932** (Java JAB proof — env-blocked,
> JDK absent).)_
>
> ---
> _Prior refresh: 2026-06-17 21:25 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA→Dev lifecycle
> lap + pulled the envelope class-killer forward to P1**. Since the 20:25 refresh: QA verified+closed
> **#977** (visual list / selector show `-j` envelope) and, in a lateral sweep, filed **#980** (a fresh
> sibling — `list windows -j` / `list screens -j` omitted top-level `count`); Dev landed it as PR **#981**
> (`a30426a`), branch auto-deleted, flipped **#980 → status:done** (awaiting QA — Dev did the handoff
> itself, no Orc flip needed). **Orc this cycle (Step 3 — priority honesty): bumped #979 P2 → P1.** #979 is
> the self-maintaining `-j` success-envelope contract (auto-enumerate collection reads, fail CI if any
> drops `{success,<collection>,count}`). The drift class keeps recurring — **#876 → #977 → #980**, each a
> full Dev+QA round — and #980 was found *after* #979 was filed, proving the reactive cadence won't stop on
> its own; Dev keeps fixing instance N while the contract that makes instance N+1 unmergeable sits unpicked.
> Raising it above further single-command fixes is justified pull-forward. **No open PRs.**
> `status:in-progress` **empty**; **status:done = #980** (awaiting QA) **+ #972** (security guard, code
> verified, close = human sign-off, already queued). **needs:ace live queue #975/#972/#969/#935/#915/#914**
> (+ infra #860/#842 in NEEDS-ACE.md) — no new human-only item this cycle. `develop` CI: **Build & Test
> GREEN on HEAD `a30426a`**, CodeQL in-progress (no failures) → not red. v0.3.2 ship-gate unchanged (FULLY
> MET — release is Ace's call, #914). #975 (ratify QA re-enable) + #972 (close guard) remain the top safety
> items; loop left QA running safely, did NOT churn-flip it again. #915 still recommended-for-closure (QA
> durability demonstrated). Weekly competitiveness **not due** (baseline 2026-06-16, <7d). Recognition next
> move still **#932** (Java JAB proof — env-blocked, JDK absent).)_
>
> ---
> _Prior refresh: 2026-06-17 20:25 (Orc autonomous cycle — **quiet/healthy; QA recovered & running safely —
> reconciled the now-stale "QA disabled" docs + filed a self-maintaining envelope contract (Step 3)**. The
> 19:40 refresh recorded a LIVE input-safety incident with QA hard-disabled; since then the loop **resolved
> it at the source and resumed normally**: `7a10b18` locked `tests/QA_AGENT.md` 第七轮 (the standing-playbook
> culprit) to **argv/pytest-only** (all 3 hardcoded dangerous payloads neutralized), and `4097eba`
> **re-enabled the QA role** in `runner.ps1` (asserts Ace authorization; code backstop verified end-to-end —
> 9/9 dangerous blocked, INJECTED refused at CLI, nothing typed). QA has since run **two clean cycles**:
> verified+closed **#876** (argv-only, no live typing) and filed **#977**; Dev then landed **PR #978**
> (`5a44c88`, fixes #977 — `visual list -j` / `selector show -j` success envelope), branch auto-deleted,
> **#977 → status:done** (awaiting QA, now live). **Orc this cycle (Step 3): filed #979** (`test`, `from:orc`,
> P2, v0.3.4) — a **self-maintaining `-j` success-envelope contract** that auto-enumerates collection-read
> commands and fails CI if any drops `{success,<collection>,count}`, converting the reactive one-at-a-time
> list/show drift class (#876→#977, siblings #865/#895/#874/#872/#877/#866/#882/#897) into a coverage
> contract (project pattern: #912 desktop guard, #957 window-selector). **Step 4:** posted a status comment
> on **#975** (re-enable) — root cause fixed, QA running safely; **left open for Ace's ratification only**
> (security sign-off is human-only; cannot independently verify the asserted authorization). Did **NOT**
> re-disable the now-safe QA (would be a 4th churn flip — root cause is fixed). **needs:ace live queue now
> #975/#972/#969/#935/#915/#914/#860/#842** (#975 reframed: was "blocks all QA" → now "ratify/confirm";
> #972 = security-guard close human sign-off). `develop` CI **GREEN** (Build & Test + CodeQL success on HEAD
> `5a44c88`). `status:in-progress` empty; **status:done = #977/#972** (awaiting QA). v0.3.2 ship-gate
> unchanged (FULLY MET — release is Ace's call, #914). #915 still recommended-for-closure (QA durability now
> strongly demonstrated). Weekly competitiveness **not due** (baseline 2026-06-16, <7d). Recognition next
> move still **#932** (Java JAB proof — env-blocked, JDK absent).)_
>
> ---
> _Prior refresh: 2026-06-17 19:40 (Orc autonomous cycle — **LIVE input-safety incident: QA hard-disabled;
> filed #975 needs:ace + #976 Dev fix; #876 handoff**. Since the 18:20 refresh a serious safety event
> occurred: even after #972/#973 hardened the input guard with a sentinel lock (`~/.naturo/safe-input.lock`),
> a QA cycle **typed the command-like sentinel `$(echo INJECTED)` into a live Notepad window — R-SEC-012
> reproduced LIVE**. The content was harmless, but typing any shell-metacharacter string into a live focused
> window violates policy (focus race). Dev **hard-disabled the QA role** in `agents/local/runner.ps1`
> (`610412d`): every `runner:qa` cycle now logs `EMERGENCY-DISABLED` and exits 0 (Dev/Orch unaffected). This
> is the 3rd disable/re-enable churn (`49a0104` hard-disable → `205dd54` re-enable w/ Ace auth → `610412d`
> re-disable). **Orc this cycle:** (a) **filed #975** (`needs:ace`, P0, `from:orc`) — re-enabling QA is Ace's
> **security sign-off**, the loop will NOT re-enable a role that typed metacharacters into a live window;
> (b) **filed #976** (P0, `test`/`silent-failure`, `from:orc`, v0.3.4) — the **code-only root-cause fix**:
> make the injection/sanitization test **pytest-only/in-process** (assert guard returns `UNSAFE_INPUT_BLOCKED`,
> zero keystrokes, against mocked SendInput — never a live window) + a runner guard so QA physically cannot
> type metacharacters into a live window (#976 is the loop-shippable half; #975 the human re-enable, paired
> like #971/#969); (c) **post-merge handoff for #876** — PR **#974** (`381701c`, `selector/record list -j`
> success envelope) merged, branch deleted; flipped #876 `status:in-progress` → `status:done` (awaiting QA,
> which is disabled). **No open PRs.** `status:in-progress` empty; **#876/#972 are `status:done`** but cannot
> be QA-verified while QA is stopped. **needs:ace live queue now #975/#969/#935/#915/#914/#860/#842** (#975
> is the new top item — blocks ALL QA verification). `develop` CI **GREEN** (Build & Test + CodeQL success on
> HEAD `610412d`). v0.3.2 ship-gate unchanged (FULLY MET — release is Ace's call, #914). #915 still safe to
> close. Weekly competitiveness **not due** (baseline 2026-06-16, <7d). Recognition next move still **#932**
> (Java JAB proof — env-blocked, JDK absent).)_
>
> ---
> _Prior refresh: 2026-06-17 18:20 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA lifecycle lap +
> filed a code-only Dev guard for the live #969 harness hazard**. Since the 17:22 refresh: PR **#970**
> (fixes **#873** — MCP `serverInfo.version` reports naturo's version `0.3.1`, not the leaked mcp SDK
> `1.26.0`) **merged** (`8355d7a`) and **QA verified+closed #873 @09:39Z** (over-the-wire stdio handshake +
> in-process `server_version` + regression test all PASS) — clean Dev→QA lifecycle, no Orc flip needed.
> `status:done` and `status:in-progress` both **empty**; **no open PRs**. **Orc this cycle (Step 3): filed
> #971** (P1, `silent-failure`, `from:orc`, v0.3.4) — a **code-only** loud-failure guard that aborts a QA
> round when `naturo.__file__` resolves **outside the active worktree**. This is the loop-shippable half of
> the **#969** stale-sibling hazard (the *env* fix stays human-only, Rule 4); confirmed live this cycle —
> QA's #873 verification had to **hand-force `sys.path`/`PYTHONPATH`** to dodge #969 (fragile manual
> workaround #971 removes). #971 pairs with #917 (watchdog catches a *dead* loop; #971 catches a *lying*
> loop); cross-linked from #969. **needs:ace live queue unchanged: #969/#935/#915/#914/#860/#842** (no new
> human-only item — #971 is deliberately Dev-actionable). `develop` CI **GREEN** (Build & Test + CodeQL
> success on HEAD `8355d7a`; the two red 3.9 lanes on PR #970 are the pre-existing tomllib gap #910 —
> non-required, `mcp` needs 3.10+). v0.3.2 ship-gate **FULLY MET** — cutting/tagging the release (#914)
> remains Ace's call (Rule 2). #915 still safe to close (loop healthy). Weekly competitiveness **not due**
> (baseline 2026-06-16, <7d). Recognition next move still **#932** (Java JAB proof — env-blocked, JDK
> absent, milestoned v0.3.3 gated behind #914)._
>
> ---
> _Prior refresh: 2026-06-17 17:22 (Orc autonomous cycle — **quiet/healthy; one Dev PR self-landing +
> filed a QA-harness integrity hazard to needs:ace**. Since the 16:24 refresh: QA's 16:40Z round
> **verified+closed #963** (MCP `find_element` window scoping; `741457a`/PR #968) — clean Dev→QA lifecycle,
> `status:done` queue now empty. Dev's 17:07 cycle picked up **#873** (MCP `serverInfo.version` reports MCP
> SDK version, not naturo version) and opened **PR #970** (`fix/issue-873-mcp-serverinfo-version` →
> `develop`) with **auto-merge SQUASH enabled** (AcePeak 09:24Z); checks IN_PROGRESS, no failures —
> normal self-landing Dev PR, left untouched (Rule 4; `BLOCKED` = required checks not yet complete).
> **Orc this cycle (Step 3/4): filed #969** (`needs:ace`, `from:qa`, P1) for a real **QA-harness
> integrity hazard** surfaced in the 16:40Z QA log — the `naturo-qa` worktree's editable install
> (egg-link/`.pth`) resolves `import naturo`/`python -m naturo` to a **sibling worktree
> `naturo-qa-mariana`** holding pre-#720 stale code, so QA's Step-2 runtime probes can **silently verify
> STALE code → false PASS/FAIL verdicts** (already caused one FALSE FAIL this cycle). Human-only: the fix
> is a machine-local env change touching another agent's worktree (Rule 4 forbids unattended self-fix);
> recommend `pip install -e .` from `naturo-qa` + optional Dev hardening (assert `naturo.__file__` under
> the active worktree). **needs:ace live queue now #969/#935/#915/#914/#860/#842.** `develop` CI **GREEN**
> (Build & Test + CodeQL success on HEAD `741457a`). v0.3.2 ship-gate **FULLY MET** — cutting/tagging the
> release (#914) remains Ace's call (Rule 2). #915 still safe to close (loop healthy). Weekly
> competitiveness **not due** (baseline 2026-06-16, <7d). Recognition next move still **#932** (Java JAB
> proof — env-blocked, JDK absent, AND milestoned v0.3.3 which is gated behind the #914 ship decision)._
>
> ---
> _Prior refresh: 2026-06-17 16:24 (Orc autonomous cycle — **quiet/healthy; two Dev PRs merged + clean
> window-selector silent-fallback class fully closed + post-merge handoff**. Since the 15:24 refresh: team
> Dev landed **two PRs** to `develop` — **#967** (`0f2d6f2`, R-SEC-012: the input-sanitization security test
> no longer hardcodes a real destructive `$(rm -rf /)` payload — replaced with a harmless `$(echo INJECTED)`
> sentinel that proves the same literal-not-executed property and is safe even if it races onto a live shell)
> and **#968** (`741457a`, fixes **#963** — MCP `find_element` now resolves `window_title` through
> `_resolve_hwnd` up front: unmatched title → `WINDOW_NOT_FOUND` loud failure, matched title scopes the
> search, explicit hwnd still wins, no selector keeps the foreground default). Both branches **auto-deleted**
> (only `develop`+`main` remain — Rule 14 verified). **#964** (CLI `get`/`set --window` loud-failure) was
> **verified+closed by QA** since the last cycle — clean Dev→QA lifecycle, no Orc flip needed. **Orc this
> cycle: post-merge handoff for #963** — PR #968 base ≠ default branch so it did not auto-close; flipped
> **#963 `status:in-progress` → `status:done`** and posted the QA verification note. **This closes the entire
> window-selector silent-fallback class** (#954/#956/#963/#964 all done/closed + **#957** the self-maintaining
> loud-failure contract verified+closed — its contract test now auto-guards `find_element`). **#963 is now the
> sole `status:done` item** (awaiting QA); `status:in-progress` **empty**. **No open PRs.** `develop` CI: HEAD
> `741457a` — **CodeQL success, Build & Test in progress, no failures** (PR #968's own checks were green at
> merge). v0.3.2 ship-gate **FULLY MET** — cutting/tagging the release (#914) remains Ace's call (Rule 2).
> needs:ace live queue **#935/#915/#914/#860/#842** (unchanged, no new human-only item); **#915** safe to
> close (loop healthy — QA verified+closed #964 this lap). Weekly competitiveness **not due** (baseline
> 2026-06-16, <7d). Next recognition move still **#932** (Java JAB proof — needs an owned Swing fixture + a
> JRE on the desktop)._
>
> ---
> _Prior refresh: 2026-06-17 15:24 (Orc autonomous cycle — **quiet/healthy; one Dev PR self-landing +
> backlog triage**. Since the 14:22 refresh: team Dev opened PR **#966**
> (`fix/issue-964-cli-window-loud-failure` → `develop`, fixes **#964** — CLI `get`/`set --window <unmatched>`
> must fail loudly with `WINDOW_NOT_FOUND` instead of silently foregrounding) with **auto-merge SQUASH
> enabled** (AcePeak @07:21Z) and **MERGED mid-cycle** (`64080d0`) once its checks went green. Base ≠
> default branch, so it did NOT auto-close #964 — Orc did the **post-merge handoff: flipped #964
> `status:in-progress` → `status:done`** and posted the QA verification note (`get`/`set --window <no-match>`
> must now fail loudly with `WINDOW_NOT_FOUND`; special attention to `set`'s prior data-integrity hazard).
> Source branch **deleted** (only `develop`+`main` remain — Rule 14 verified). Merge-commit CI running
> (CodeQL/Build&Test in progress, no failures; PR checks were green at merge). **#964 is now the sole
> `status:done` item** (awaiting QA); `status:in-progress` **empty**. **Step 3 triage:** milestoned two unmilestoned actionable bugs
> to **v0.3.4** — **#916** (P2 from:qa — taskbar/tray list returns empty `success:true` on a populated
> desktop, silent-failure class) and **#917** (P1 from:orc — `runner.ps1` failure-streak watchdog, code-only;
> was P1-with-no-milestone, a priority-honesty gap). **#963** (MCP `find_element` ignores `window_title`)
> already milestoned v0.3.4, pickable. **No open PRs.** `develop` CI **GREEN** pre-merge (HEAD before #966 was
> `4d19823`, Build & Test + CodeQL success); merge commit `64080d0` CI in progress, no failures. v0.3.2 ship-gate **FULLY MET** — cutting/tagging the release
> (#914) remains Ace's call (Rule 2). needs:ace live queue **#935/#915/#914/#860/#842** (unchanged, no new
> human-only item); **#915** safe to close (loop healthy). Weekly competitiveness **not due** (baseline
> 2026-06-16, <7d). Next recognition move still **#932** (Java JAB proof, env-blocked — no Java app on
> desktop)._
>
> ---
> _Prior refresh: 2026-06-17 14:22 (Orc autonomous cycle — **quiet/healthy; two Dev PRs merged + clean
> QA lap + post-merge handoff + light triage**. Since the 12:23 refresh: team Dev landed **two PRs** to
> `develop` — **#962** (`8517b4d`, fixes **#957**, routes MCP window-selector resolution through a
> loud-failure helper) and **#965** (`4d19823`, fixes **#927**, one-line MCP install snippets for Claude
> Code / Cursor / VS Code / Windsurf at README top + `test_readme_mcp_install.py`); both branches
> auto-deleted. **QA verified+closed #957** at 04:40Z (clean Dev→QA lifecycle, no Orc flip needed). QA then
> ran an exploratory lap and filed **two silent-failure window-selector bugs**: **#963** (MCP `find_element`
> accepts `window_title` but backend ignores it → foreground fallback; already milestoned v0.3.4) and
> **#964** (P1 — CLI `get`/`set --window <title>` silently falls back to foreground on no-match instead of
> `WINDOW_NOT_FOUND`; data-integrity hazard for `set`). **Orc this cycle:** (a) **post-merge handoff** —
> flipped **#927 `status:in-progress` → `status:done`** (PR #965 base ≠ default branch so it did not
> auto-close; QA verification note posted); (b) **triaged #964** (was `m=none`) → **v0.3.4**. **#927 is now
> the sole `status:done` item** (awaiting QA); `status:in-progress` empty. **No open PRs.** `develop` CI
> **GREEN** (Build & Test + CodeQL success on HEAD `4d19823`). v0.3.2 ship-gate **FULLY MET** —
> cutting/tagging the release (#914) remains Ace's call (Rule 2). needs:ace live queue
> **#935/#915/#914/#860/#842** (unchanged, no new human-only item); **#915** safe to close (loop healthy).
> Weekly competitiveness **not due** (baseline 2026-06-16, <7d). Next recognition move still **#932** (Java
> JAB proof, env-blocked — no Java app on desktop)._
>
> ---
> _Prior refresh: 2026-06-17 12:23 (Orc autonomous cycle — **quiet/healthy; clean Dev→QA lifecycle lap +
> active in-flight Dev work + light backlog triage**. Since the 11:23 refresh: **QA verified+closed #960**
> (03:42Z — the env-gated input-content safety guard; closed with `verified`+`status:done`, correct
> lifecycle, no Orc flip needed) → **`status:done` queue now empty**; and **Dev picked up #957** (P1,
> from:orc — window-selector silent-fallback → loud-failure contract class) at 04:15Z (`status:in-progress`,
> assigned, **no branch pushed**; 8 min old — active in-flight, left untouched per Rule 4). **Orc backlog
> triage (Step 3):** milestoned 4 untriaged `from:qa` contract/test bugs to **v0.3.4** — **#958** (UWP
> PID drift), **#952** (handle/hwnd field drift), **#946** (path-test POSIX slashes), **#944** (Windows
> test fail); they were `m=none`. **No open PRs.** `develop` CI **GREEN** (Build & Test + CodeQL success on
> HEAD `68c5747`). v0.3.2 ship-gate **FULLY MET** — cutting/tagging the release (#914) remains Ace's call
> (Rule 2). needs:ace live queue **#935/#915/#914/#860/#842** (unchanged); **#915** safe to close (loop
> healthy). Weekly competitiveness **not due** (baseline 2026-06-16, <7d). Next recognition move still
> **#932** (Java JAB proof, env-blocked — no Java app on desktop)._
>
> ---
> _Prior refresh: 2026-06-17 11:23 (Orc autonomous cycle — **quiet/healthy; QA-safety self-defense loop
> closed a lap; clean Dev handoff, no intervention needed**. Since the 10:23 refresh: team Dev landed the
> **env-gated input-content safety guard** — **#960** (P0, from:orc; `naturo type`/MCP `type` refuse
> shell-command-like keystrokes when `NATURO_SAFE_INPUT=1`, returning `UNSAFE_INPUT_BLOCKED`, exit 1, typing
> nothing; `runner.ps1` exports the env for the qa role only) via PR **#961** (`68c5747`, MERGED to
> `develop`, branch auto-deleted — only `develop`+`main` remain; 35 new CI-safe tests). This codifies the
> three preceding doc-only SAFETY commits (`159961c`/`81c80dd` — a `$(rm -rf)` keystroke fragment had once
> raced onto the command line during a qa input probe) into an **enforced guard**. **Dev did the handoff
> itself** (set #960 `status:in-progress` → `status:done`); no Orc flip needed. **`status:in-progress` is
> empty; #960 is the sole `status:done` item** (awaiting QA). Class-level silent-fallback fix **#957**
> (P1, from:orc) stays open/pickable; QA contract bugs (#958/#952/#946/#944) remain pickable for Dev.
> **No open PRs.** `develop` CI **GREEN** (Build & Test + CodeQL success on HEAD `68c5747`). v0.3.2
> ship-gate **FULLY MET** — cutting/tagging the release (#914) remains Ace's call (Rule 2). needs:ace live
> queue **#935/#915/#914/#860/#842** (unchanged); **#915** safe to close (loop healthy). Weekly
> competitiveness **not due** (baseline 2026-06-16, <7d). Next recognition move still **#932** (Java JAB
> proof, env-blocked — no Java app on desktop)._
>
> ---
> _Prior refresh: 2026-06-17 10:23 (Orc autonomous cycle — **quiet/healthy; MCP silent-failure loop closed
> another lap; clean post-merge handoff**. Since the 09:22 refresh: team Dev fixed **#956** (MCP
> `create_snapshot` bundled a foreground screenshot with a *different* window's element tree, `success:true`,
> when `window_title` named a non-foreground window) via PR **#959** (`792c46c`, MERGED to `develop`, branch
> auto-deleted — only `develop`+`main` remain). The PR did not auto-close the issue (base ≠ default branch),
> so Orc did the **post-merge handoff: flipped #956 `status:in-progress` → `status:done`** and posted the QA
> verification note (call `create_snapshot` on a non-foreground `window_title`; confirm screenshot+tree share
> one resolved hwnd and unresolvable titles fail loudly). **`status:in-progress` is now empty; #956 is the
> sole `status:done` item** (awaiting QA). The class-level fix **#957** (P1, from:orc — self-maintaining
> loud-failure contract for the window-selector fallback class; #954/#956 were instances) stays open and
> pickable for Dev. **No open PRs.** `develop` CI **GREEN** (Build & Test + CodeQL success on HEAD `792c46c`).
> v0.3.2 ship-gate **FULLY MET** — cutting/tagging the release (#914) remains Ace's call (Rule 2). needs:ace
> live queue **#935/#915/#914/#860/#842** (unchanged); **#915** even safer to close (loop healthy across
> #954/#956 laps). **Step 3:** backlog already sharp — the silent-fallback class is captured by #957 and QA
> has fresh contract bugs filed (#958 UWP PID, #952 handle/hwnd field drift, #946 path-test slashes); no
> duplicate gap worth filing this cycle. Weekly competitiveness **not due** (baseline 2026-06-16, <7d). Next
> recognition move still **#932** (Java JAB proof, env-blocked — no Java app on desktop)._
>
> ---
> _Prior refresh: 2026-06-17 09:22 (Orc autonomous cycle — **quiet/healthy; MCP silent-failure loop ran a
> full lap + drove the product**. Since the 07:24 refresh: team Dev fixed **#954** (MCP `capture_window`
> silently ignored `window_title`, captured foreground with `success:true`) via PR **#955** (`0eff973`,
> branch deleted), and **QA verified+closed #954** at 00:42Z — clean end-to-end Dev→QA lifecycle, no Orc
> intervention needed. QA filed the sibling **#956** (MCP `create_snapshot` bundles a foreground screenshot
> with a *different* window's element tree, `success:true`) which **Dev picked up** (`status:in-progress`,
> created 00:44Z, in flight, **no branch pushed** — only `develop`+`main`; left untouched per Rule 4).
> **Step 3 product drive:** Orc filed **#957** (P1, `silent-failure`, `from:orc`, v0.3.4) to convert this
> whole **window-selector silent-fallback class into a self-maintaining loud-failure contract** — confirmed
> *more* unfixed instances in `naturo/mcp/_inspect.py` (`set_element_value`/`toggle_element`/+2 swallow
> `_resolve_hwnd` failure at debug level then act on foreground). Scoped to not overlap #956 (one-issue-one-PR).
> **No open PRs.** `develop` CI **GREEN** (Build & Test + CodeQL success on HEAD `0eff973`). v0.3.2 ship-gate
> **FULLY MET** — cutting/tagging the release (#914) remains Ace's call (Rule 2). needs:ace live queue
> **#935/#915/#914/#860/#842** (unchanged); **#915** even safer to close (QA verified+closed #954 this lap);
> **#863** premise disproven, QA-owned. Weekly competitiveness **not due** (baseline 2026-06-16, <7d). Next
> recognition move still **#932** (Java JAB proof, env-blocked)._
>
> ---
> _Prior refresh: 2026-06-17 06:22 (Orc autonomous cycle — **quiet/healthy; active Dev work in flight,
> no intervention needed**. Since the 04:24 refresh (= 20:24Z): QA **verified+closed #879** (browser
> launch `-j` success envelope) at 05:40 local — `status:done` queue now **empty**. The Dev cron cycle
> that started 06:07 local (22:07Z) **picked up #881** (MCP errors leak `NaturoCoreError` C++ names
> instead of typed codes) and set it `status:in-progress` at 22:16Z — **active in-flight work, left
> untouched** (no branch pushed yet; only `develop`+`main`; well inside the >24h-abandoned threshold;
> Rule 4 — do not touch Dev's tree). **No open PRs.** `develop` CI **GREEN** (Build & Test + CodeQL
> success on HEAD `d3cfe92`). v0.3.2 ship-gate **FULLY MET** — cutting/tagging the release (#914) remains
> Ace's call (Rule 2). needs:ace live queue **#935/#915/#914/#860/#842** (unchanged); standing
> recommended closures **#915** (durability proven) + **#863** (premise disproven, QA-owned). Weekly
> competitiveness **not due** (baseline 2026-06-16, <7d). No new sharp gap worth filing; backlog already
> sharp. No new human-decision items.
>
> ---
> _Prior refresh: 2026-06-17 04:24 (Orc autonomous cycle — **quiet/healthy; one team Dev PR merged,
> self-landed**. Since the 04:23 refresh: team Dev PR **#951**
> (`fix/issue-879-browser-launch-success-envelope`, fixes #879 — standardize browser launch `-j` output
> to the success-boolean envelope) **MERGED** to `develop` (`d3cfe92`), both checks green. Post-merge
> handoff already clean: **#879 → `status:done`** (awaiting QA); source branch **deleted** (Rule 14
> verified — `gh api .../branches` shows only `develop`+`main`). `status:in-progress` **empty**; **#879**
> is the sole `status:done` item (awaiting QA). QA progressed since last cycle: **#901** (MCP `app_inspect`
> PID validation) and **#887** (README honest claims) both **verified + closed** — QA loop healthy.
> `develop` CI **GREEN** (Build & Test + CodeQL success on HEAD `d3cfe92`). **No open PRs.** v0.3.2
> ship-gate **FULLY MET** — cutting/tagging the release (#914) remains Ace's call (Rule 2). needs:ace live
> queue **#935/#915/#914/#860/#842** (unchanged); standing recommended closures **#915** (durability proven)
> + **#863** (premise disproven, QA-owned). Weekly competitiveness **not due** (baseline 2026-06-16, <7d).
> No new sharp gap worth filing; backlog already sharp. No new human-decision items.
>
> ---
> _Prior refresh: 2026-06-17 04:23 (Orc autonomous cycle — **quiet/healthy; one team Dev PR in flight,
> self-landing**. Since the 03:22 refresh: team Dev opened PR **#950**
> (`fix/issue-901-mcp-app-inspect-pid-validation`, fixes #901 — validate direct PID in MCP `app_inspect`
> so bogus PIDs fail loudly), base=`develop`, `MERGEABLE`, **auto-merge SQUASH enabled** (AcePeak @20:20Z).
> **#950 MERGED mid-cycle** (`4e0ca65`) once its checks went green. Orc did the **post-merge handoff:
> flipped #901 `status:in-progress` → `status:done`** (now awaiting QA verification of the MCP PID-validation
> fix) and confirmed the source branch is **deleted** (GitHub auto-delete; verified gone, Rule 14).
> `status:in-progress` is now **empty**; **#901** is the sole `status:done` item (awaiting QA). The merge
> commit's CI (`4e0ca65`) is running (CodeQL/Build&Test in progress, **no failures**); prior HEAD `ce4694f`
> was green. v0.3.2 ship-gate **FULLY MET** — cutting/tagging the
> release (#914) remains Ace's call (Rule 2, unchanged). needs:ace live queue **#935/#915/#914/#860/#842**
> (unchanged); standing recommended closures **#915** (durability proven) + **#863** (QA-owned, premise
> disproven). Weekly competitiveness **not due** (baseline 2026-06-16, <7d). No new sharp gap worth filing;
> backlog already sharp. No new human-decision items._
>
> ---
> _Prior refresh: 2026-06-17 03:22 (Orc autonomous cycle — **v0.3.2 SHIP-GATE FULLY MET; release is
> Ace's call**. Since the 02:24 refresh QA **verified+closed #843** (02:42Z — runtime composite check:
> the #948 Z-order fix makes the File-menu popup survive compositing even under 5 overlapping full-size
> siblings; `test_capture_popup_843.py` 12/12; input probe-gate confirmed input works on this no-RDP
> console). **All 5 ship-gate bugs are now verified+closed** (#786/#788/#807/#840 @01:15Z + #843 @02:42Z)
> and the #885 cluster is closed — **both ship-gate requirements (1) and (2) are satisfied. `status:done`
> queue is empty of ship-gate items.** The sole remaining v0.3.2 action is **cutting/tagging the release
> (#914) — human-only (Rule 2, tag→main = PyPI publish); QA explicitly does not sign off.** QA posted the
> full "precondition met" note to #914 (18:41Z-clock). Separately, Dev landed docs PR **#949**
> (`fix/issue-887-readme-honest-claims` → `ce4694f`, softened the README "AI Agent Ready" cell while the
> -j envelope is still standardizing; branch deleted) — **#887 now `status:done` awaiting QA** (correct
> lifecycle, no Orc flip needed). **No open PRs. `status:in-progress` empty.** `develop` CI **GREEN**
> (Build & Test + CodeQL success on HEAD `ce4694f`). needs:ace live queue **#935/#915/#914/#860/#842**
> (unchanged); **#863** QA-owned (premise disproven — input verified working; QA to close); **#915**
> recommended for closure (durability proven). Weekly competitiveness **not due** (baseline 2026-06-16,
> <7d). Backlog sharp — recognition #920/#932/#934/#937 + ~30 from:qa contract bugs; #932 (Java JAB
> proof) still env-blocked (no Java app on desktop). No new human-decision items; no new issue filed.
>
> ---
> _Prior refresh: 2026-06-17 02:24 (Orc autonomous cycle — **ship-gate one QA-check from ready**.
> Since the 01:22 refresh, the last remaining v0.3.2 ship-gate bug **#843** (capture omits same-PID
> popup menus) had its **Dev fix MERGED**: PR **#948** (`fix/issue-843-zorder-composite` →
> `73d7d32`, Z-order-aware compositing of `capture --app/--pid` windows) landed at 17:32Z and the
> branch is **deleted** (Rule 14). Orc did the **post-merge handoff: flipped #843
> `status:in-progress` → `status:done`** and posted a QA verification comment (open #32768 popup via
> input → `capture --app/--pid` → confirm menu survives compositing). **#843 is now the sole
> `status:done` item** and the last ship-gate blocker — once QA verifies it, v0.3.2 req (2) is fully
> met and cutting the release (#914) is Ace's call. **No open PRs. `status:in-progress` empty.**
> `develop` CI **GREEN** (Build & Test + CodeQL success on HEAD `73d7d32`). Confirmed prior handoffs
> clean: #862 (PR #947 macos split) already **verified+closed** by QA. needs:ace live queue
> **#935/#915/#914/#860/#842** (unchanged; #863 already de-labeled — now QA-owned `from:qa`, awaiting
> QA close). Weekly competitiveness step **not due** (baseline 2026-06-16, <7d). No new
> human-decision items; no new issue filed (backlog sharp: ~30 `from:qa` contract bugs + recognition
> #920/#932/#934/#937).
>
> ---
> _Prior refresh: 2026-06-17 00:30 (Orc autonomous cycle — **stuck-PR triage**. One open PR: **#945**
> (refactor `browser_cmd.py` → `_browser/` modules, fixes #856, team Dev, auto-merge SQUASH on) was
> **BLOCKED on red CI** — `Lint & Type Check` failed with **9 `mypy` `Cannot determine type of "browser"
> [has-type]` errors**: each submodule aliased the shared group via the module-level attribute
> `browser = browser_cmd.browser`, which participates in the `browser_cmd`↔submodule registration import
> cycle that mypy can't resolve. Orc reproduced it in an isolated detached worktree and built a fix
> (direct `from naturo.cli.browser_cmd import browser, _get_page`), **but on push discovered Dev had
> force-pushed a better structural fix** (`98995419`→`012dff9`, extracting the group into
> `_browser/_group.py` to break the cycle at the source). Orc **discarded its own commit and backed off**
> — Dev's fix cleared Lint and **#945 auto-merged to `develop` (`6112800`)** during this cycle. Orc did the
> **post-merge handoff: flipped #856 → status:done** and confirmed the `refactor/issue-856-split-browser-cmd`
> branch is **deleted** (Rule 14). No manual merge was performed.
> This was a **second near-miss of the #935 concurrency hazard** (Orc-vs-Dev push race on one branch) —
> but because Orc used a *separate* worktree (Rule 4), **no work was lost** (vs the original shared-tree
> `reset --hard` data loss); supporting evidence appended to #935. `develop` CI green pre-merge (9ba505f);
> #945's own checks were green at merge. `status:done` now 6 (5 ship-gate bugs #786/#788/#807/#840/#843,
> all gated on #863, **+ #856** awaiting QA structural check). `status:in-progress` **empty**.
> needs:ace queue unchanged (#935/#915/#914/#863/#860/#842),
> no new human-decision items. Weekly competitiveness step not due (baseline 2026-06-16)._
>
> ---
> _Prior refresh: 2026-06-16 23:22 (Orc autonomous cycle — quiet/healthy. Since the 22:24 cycle: **two code-health refactors merged + cleared CI** — PR #942 (`_input.py` → `_input/` submixins, #861) and PR #943 (`_element.py` → focused submodules, #720). **develop CI GREEN** (Build&Test+CodeQL success on **9ba505f = HEAD**). QA **verified+closed #861** at 22:40 (non-intrusive structural/API-parity check, 470 passed) — the **6th consecutive clean QA runner round** (16:43/17:42/18:50/20:45/21:40/22:40), further strengthening #915 durability. Orc flipped **#720 → status:done** (post-merge handoff for PR #943; was left `status:in-progress`) — now awaiting QA. `status:in-progress` empty. 5 input-class `status:done` bugs remain (#786/#788/#807/#840/#843, gated on #863) + #720 (refactor, QA-pickable non-intrusively). Reconciled the needs:ace queue: **added the `needs:ace` label to #863** (was documented in NEEDS-ACE.md as a human-only session/input-policy decision but missing the label) → live queue now #935/#915/#914/#863/#860/#842. No new human-decision items. Recognition proofs (#931 benchmark + #933 Electron CDP) remain verified+closed; next recognition move still #932 (Java JAB, env-blocked). Competitive tracker baseline set today — weekly step not due._

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
