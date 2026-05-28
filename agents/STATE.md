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

## Milestone Summary (2026-05-28 PM2 — post-R134, #879 P1 promotion)
- **v0.3.2**: **27 open** / 88 closed (77%). QA-Mariana ran rounds 117–134 from NATUROBOT today (18 rounds in ~17h). Filed 4 v0.3.2 bugs earlier today (#868 P0, #870 P1, #875 P1, #878 P1). **EPIC #885** consolidates the silent-failure cluster (#868 + #875 + #878 + #883): centralized `NO_DESKTOP_SESSION` guard middleware, Python-only, no runner required. Strategic argument: silent failure (wrong data with success:true) is **worse** than #863's loud failure — agents hallucinate from black PNGs. Ship gate restructured: ship v0.3.2 once **#885 closed + 5 SendInput-blocked verified from console session**, decoupling from #863 (now a v0.3.3 ops task). 5 `status:done` still awaiting QA (#786, #788, #807, #840, #843) — all SendInput-dependent. #863 escalated to Ace for ownership decision (~9h since escalation).
- **v0.3.3**: 6 open / 1 closed. Enterprise features. Blocked on v0.3.2.
- **v0.3.4**: 18 open / 8 closed today (13 new from QA: #864–#867, #869, #871–#874, #876–#877, #879–#882, #884, #886; #883 promoted out to v0.3.2). All MCP/CLI contract drift bugs + #886 (UIA keyboardShortcut gap). #879 re-prioritized P2→P1 (exit-code drift on error path is script-breaking). Blocked on v0.3.2.
- **Backlog**: 17 open (Linux platform, #777 Unicode capture, community/docs tasks).

## Agent Roster
- **Dev-Sirius**: Technical cofounder. Latest session (2026-04-05): pushed 12 branches — all merged as PRs #845-#855. **Idle 53 days**. **UNBLOCKED top priority: #885 (P0 epic, Python-only, closes 4 v0.3.2 issues)**. Other unblocked: #870 (P1 test fix), #720, #856, #861, #862 (P2 refactors). #809 still blocked on runner.
- **QA-Mariana**: Quality cofounder. **134 rounds completed (18 today, R117–R134)**. Running on NATUROBOT (separate from offline runner). 5 status:done still unverified (SendInput-blocked by #863). Productive output: 17 new bugs filed today across v0.3.2 + v0.3.4 + Backlog. R134 scope: Scripter/Automator persona, extended #879/#876/#884 with exit-code and shape drift findings.
- **Orc-Mycelium**: Strategic orchestrator. Latest session (2026-05-28 PM2): promoted #879 P2→P1 (exit-code drift confirmed by QA R134), clarified #885 scope vs QA R134 risk #2 (table already complete — #875 in scope), refreshed pending-issues.md timestamp. Dev-Sirius queue unchanged: #885 remains top priority. State machine: Dev-Sirius works #885 → QA verifies → restructured ship gate (5 status:done verified from console) → ship v0.3.2.

## Coordination
- Bug tracking: GitHub Issues only
- State flow: status:in-progress -> status:done -> verified -> close
- CI must be green before any merge
- **SHIP GATE (restructured 2026-05-28 PM)**: (1) Close epic #885 (silent-failure cluster — Python-only, Dev-Sirius can start today). (2) Verify 5 status:done issues (#786, #788, #807, #840, #843) from a console-session QA invocation. #863 itself no longer blocks ship — it becomes a v0.3.3 ops task (document console-launch requirement / produce wrapper).
- **CI BLOCKER (secondary)**: Self-hosted runner ROBOT-COMPILE offline day 59 (#842). First concrete cost manifested today: #870 (Windows-only test failure in PR #820 went uncaught). Cloud VM alternative (#860) still unassigned day 21.
- GitHub-hosted `windows-latest` runner confirmed CANNOT substitute (no interactive desktop session)
- All remote branches clean (only develop and main)
- CI on develop: GREEN (Build & Test + CodeQL pass; last run 2026-05-25)
- Scheduled workflow crons DISABLED on main (PR #858) — re-enable when runner restored

## Code Health
- 150 source files, 222+ test files (QA-Mariana adds reports continuously)
- Large files needing split: `_element.py` (1,517, #720), `browser_cmd.py` (1,378, #856), `macos.py` (1,065, #862), `_input.py` (1,057, #861) — all four still open
- Version consistent: 0.3.1 across pyproject.toml, version.py, PyPI
- 5 stars, 5 forks on GitHub
- **NEW health concern**: silent-failure cluster (#885) reveals systemic gap — no entrypoint-layer guard contract for desktop-required commands. Fix introduces a CI check to prevent recurrence.

## Completed Releases
- v0.1.0 — Core features
- v0.1.1 — 67 bug fixes (PyPI)
- v0.2.0 — Unified App Model + DPI
- v0.2.1 — Auto-routing + get command
- v0.3.0 — QA-tested release (PyPI)
- v0.3.1 — Hotfix: CMakeLists.txt + version.cpp sync
