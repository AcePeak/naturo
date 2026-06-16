# Naturo Project Status
> Maintained by Orc-Mycelium. Agents: read on every startup.
> Last refreshed: 2026-06-16 18:24 (Orc autonomous cycle — **QA loop RECOVERED**: verified+closed 9 issues today incl. ship-gate epic #885; CI green, no PRs; remaining verify blocker is #863, not #915; new ops item #935).

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
  - (2) Verify the 5 remaining `status:done` bugs from a real desktop: **#786, #788, #807, #840, #843**.
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
  similarly gated; #786 (UWP menu click) and #843 (capture popup) may be non-intrusively verifiable.
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
- **Backlog**: ~10 open (Linux platform + #777 Unicode capture + migrated community/docs tasks).

## Open community PRs (external contributor @botbikamordehai2-sketch)
- **#892** (closes #885): correct decorator, never applied, base=`main`. Team carrying forward.
- **#904** (closes #844): right direction, breaks `errors.py` (mis-spliced helper), no wiring,
  unrelated workflow churn, base=develop. Team carrying forward.
- Both: warm "we'll complete + co-credit you" notes posted 2026-06-15; close when the team PR lands.
- **Disposition is now queued as `needs:ace` #913** (closing/taking over a community PR is human-only).
  #892 is superseded by merged PR #911; recommend close-with-thanks. Hold #904 until its replacement lands.

## Coordination
- Bug tracking: GitHub Issues only. State flow: `status:in-progress` → `status:done` → `verified` → close.
- One issue = one commit = one PR. English-only on GitHub. CI red → stop all new dev work.
- Never push directly to `main`/`develop` (only release tags → `main`); Orch may push
  operational files (STATE.md, queue) to develop with `[skip ci]`.
- **Human-decision items (Ace only):** **#935 serialize dev cycles / per-worktree lock (NEW)**;
  **#915 confirm QA auth durable then close** (recovering, no longer TOP); self-hosted runner #842
  (offline) / cloud-VM #860; persistent cron scheduling; ship-gate timing (#914 — req (1) #885 now
  met); public-API changes; superseding community PRs (#913).
- **STANDING #1 PRODUCT PRIORITY — recognition supremacy:** epic **#920** (P0 moat) + **#931** (P0
  coverage benchmark, `status:in-progress`, updated today) + **#932/#933/#934** (Java/Electron/SAP
  hardening, P1/P1/P2, milestone v0.3.3) are all filed, labeled `competitiveness`, and at queue top.
  Pull recognition work forward each cycle. #931 publishing the proof feeds the README headline.

## Code Health
- Large files still open for split: `_element.py` (#720), `browser_cmd.py` (#856),
  `macos.py` (#862), `_input.py` (#861).
- Version consistent at 0.3.1 across pyproject/version.py/PyPI.

## Completed Releases
- v0.1.0 core · v0.1.1 (67 fixes) · v0.2.0 (Unified App Model + DPI) · v0.2.1 (auto-routing + get)
- v0.3.0 (QA-tested) · v0.3.1 (hotfix: CMakeLists + version.cpp sync)
