# Naturo Project Status
> Auto-maintained by Orc-Mycelium. Agents: read on every startup.

## Current Version
v0.3.1 (PyPI + GitHub Release)

## Active Work
Query live data — do not rely on this section for specific issue numbers:
```bash
gh issue list --state open --limit 100 --json milestone,number,title,labels \
  --jq 'group_by(.milestone.title // "backlog") | sort_by(.[0].milestone.title // "z") |
  .[] | "\n### \(.[0].milestone.title // "Backlog")\n\(.[] | "- #\(.number) [\(.labels | map(.name) | join(","))] \(.title)")"'
```

## Milestone Summary (2026-06-01 05:01Z — 11th cycle, **deadline-pass cycle: pre-staged actions FIRED**; PR #892 silent 78.9h post v2-request)
- **v0.3.2**: **30 open** / 89 closed (75%). Source HEAD `22642335` (PR #853 tests-only commit, 2026-04-05) unchanged across all 11 reviews 2026-05-29 → 2026-06-01. QA-Mariana idle since R153 comment at 2026-05-29T02:05Z (~75h, correct on frozen source). **PR #892 status: silent 78.9h post v2-request (deadline passed by ~6.9h).** Author @botbikamordehai2-sketch zero activity post Orc v2 request at 2026-05-28T22:04Z. Last author push `51dd440` at 2026-05-28T09:12Z. PR base = `main` (still unretargeted). **Pre-staged plan FIRED today**: (a) 48h FINAL-window comment posted on #892 (closes 2026-06-02T22:04Z) — `#issuecomment-4589450297`; (b) Dev-Sirius unblock comment posted on #885 directing #902 (warm-up) → #885 surface matrix on base=develop — `#issuecomment-4589450641`; (c) #902 promoted as Dev warm-up — `#issuecomment-4589450799`; (d) #892 remains OPEN per RULES.md §1, no close/force-push/retarget. Ship gate unchanged: close #885 + verify 5 status:done from console session.
- **v0.3.3**: 6 open / 1 closed. Enterprise features. Blocked on v0.3.2.
- **v0.3.4**: **47 open** / 8 closed. New from QA R135–R145: #888–#891, #894–#900. All MCP/CLI contract-drift, JSON envelope drift, parameter-name drift, exit-code drift. #890 (MCP list_snapshots fails 100%) is the only P1; rest P2. v0.3.4 is effectively a "contract stability" milestone — worth formalizing as the explicit theme when v0.3.3 ships. Blocked on v0.3.2.
- **Backlog**: 9 open (Linux platform + #777 Unicode capture). Community/docs tasks already migrated to v0.3.4.

## Agent Roster
- **Dev-Sirius**: Technical cofounder. Latest session 2026-04-05 (idle **57 days**). **EXPLICITLY UNBLOCKED today (2026-06-01)** via comment on #885 to proceed in parallel with #892. Recommended sequence: **#902 (30-min docs warm-up, fixes CONTRIBUTING.md `main` vs `develop` contradiction that misled #892) → #885 (P0 epic, full silent-failure cluster surface matrix on base=develop)**. Pivot-cleanly clause: if #892 author revives within 48h FINAL window (until 2026-06-02T22:04Z) and lands first, Dev pivots away; if Dev lands first, #885 fully replaces #892 (close #892 with credit). Other unblocked: #870 (P1 test fix), #720, #856, #861, #862 (P2 refactors). #809 + status:done verification still runner-blocked. **4th cycle flagged for strategic escalation** — manual nudge from Ace remains warranted; the unblock comment is the formal signal but Dev historically responds to direct Ace prompts.
- **QA-Mariana**: Quality cofounder. **153 rounds completed**. Running on NATUROBOT. 5 status:done still unverified (SendInput-blocked by #863). Idle since R153 comment at 2026-05-29T02:05Z (~75h, correct — frozen source). Strong R153 sharpening artifact (TC-0090 end-to-end workflow exit-code consistency) already on #885.
- **Orc-Mycelium**: Strategic orchestrator. Latest session (2026-06-01 05:01Z — **11th cycle, deadline-pass cycle, pre-staged actions FIRED**). Confirmed PR #892 still silent at 78.9h post Orc v2 review (`UNSTABLE`/MERGEABLE, external fork — checks `action_required`, base still `main`, 1 PR comment total, 0 author activity since v2 request). QA idle since R153 (correct). 0 stale `status:in-progress`. No orphan branches (only develop + main). **5 stars / 6 forks unchanged**. **No new issues since #902 (2026-05-28T22:05Z)** filed by anyone. Today's actions: 3 comments posted (#892 FINAL window, #885 Dev unblock, #902 root-cause link), pending-issues.md refreshed, no new issues filed (no new gaps surfaced — code-health and ship-gate coverage already complete). **Cadence shift recommendation**: switch from time-driven (q9h) to **event-driven** for next cycle — triggers are (a) Dev-Sirius activity, (b) PR #892 author revival, (c) 2026-06-02T22:04Z FINAL deadline, (d) q48h safety-net light health check (for scheduled-workflow visibility on 2026-06-01 CodeQL/Dependabot runs). Marginal signal per review across 11 frozen-source cycles approached zero; event-driven mode reserves cycles for true state changes.

## Coordination
- Bug tracking: GitHub Issues only
- State flow: status:in-progress -> status:done -> verified -> close
- CI must be green before any merge
- **SHIP GATE (unchanged from 2026-05-28 PM restructure)**: (1) Close epic #885 (silent-failure cluster — 9-surface matrix consolidated in epic comments). (2) Verify 5 status:done issues (#786, #788, #807, #840, #843) from a console-session QA invocation. #863 remains a v0.3.3 ops task.
- **CI BLOCKER (secondary)**: Self-hosted runner ROBOT-COMPILE offline **day 60** (#842, no update in 21d). Cloud VM alternative (#860) still unassigned day 22. Chronic — needs Ace decision.
- GitHub-hosted `windows-latest` runner confirmed CANNOT substitute (no interactive desktop session)
- **Branch model contradiction**: CONTRIBUTING.md step 5 reads "squash merge to main" — contradicts develop-first rule. Misled PR #892. Filed as #902 (P1).
- All remote branches clean (only develop and main), but PR #892 is **open against `main`** — must be retargeted before merge.
- CI on develop: GREEN (Build & Test + CodeQL pass; last run 2026-05-25)
- Scheduled workflow crons DISABLED on main (PR #858) — re-enable when runner restored

## Code Health
- 150 source files, 222+ test files (QA-Mariana adds reports continuously)
- Large files needing split: `_element.py` (1,517, #720), `browser_cmd.py` (1,378, #856), `macos.py` (1,065, #862), `_input.py` (1,057, #861) — all four still open
- Version consistent: 0.3.1 across pyproject.toml, version.py, PyPI
- **5 stars, 6 forks** on GitHub (stable — last fork delta was PR #892 author 2026-05-28)
- Silent-failure cluster (#885) systemic gap unchanged on source HEAD `22642335` (2026-04-05) per QA R153. Fix should include CI check to prevent recurrence (e.g. lint that flags any entrypoint without a guard or explicit `# desktop-not-required` opt-out).

## Completed Releases
- v0.1.0 — Core features
- v0.1.1 — 67 bug fixes (PyPI)
- v0.2.0 — Unified App Model + DPI
- v0.2.1 — Auto-routing + get command
- v0.3.0 — QA-tested release (PyPI)
- v0.3.1 — Hotfix: CMakeLists.txt + version.cpp sync
