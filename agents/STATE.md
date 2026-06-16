# Naturo Project Status
> Maintained by Orc-Mycelium. Agents: read on every startup.
> Last refreshed: 2026-06-17 07:24 (Orc autonomous cycle — **quiet/healthy; #881 post-merge handoff
> completed**. Since the 06:22 refresh: the Dev cycle's in-flight #881 work landed — team Dev PR **#953**
> (`fix/issue-881-mcp-typed-error-codes`, fixes #881 — map MCP `NaturoCoreError` to typed error codes
> without leaking C++ class names) **MERGED** to `develop` (`aeb50e5`) at 23:21Z, auto-merge self-landed,
> source branch **deleted** (Rule 14 verified — only `develop`+`main` remain). Orc did the **post-merge
> handoff: flipped #881 `status:in-progress` → `status:done`** (awaiting QA) and posted the verification
> note. **`status:in-progress` now empty; #881 is the sole `status:done` item.** **No open PRs.**
> `develop` CI **GREEN** (Build & Test + CodeQL success on HEAD `aeb50e5`). v0.3.2 ship-gate **FULLY MET**
> — cutting/tagging the release (#914) remains Ace's call (Rule 2). needs:ace live queue
> **#935/#915/#914/#860/#842** (unchanged); standing recommended closures **#915** (durability proven) +
> **#863** (premise disproven, QA-owned). Weekly competitiveness **not due** (baseline 2026-06-16, <7d).
> Next recognition move still **#932** (Java JAB proof, env-blocked). No new sharp gap worth filing;
> backlog already sharp. No new human-decision items._
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
