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

## Milestone Summary (2026-04-15 evening review)
- **v0.3.2**: 24 open / 82 closed (77%). **No progress since Apr 5** — project stalled 11 days on offline runner. 13 issues `status:done` awaiting QA verification (all have merged PRs). Only 3 dev issues remain: #809 (unified find, P1), #720 (split _element.py, P2), #856 (split browser_cmd.py, P2). **BLOCKER**: self-hosted runner offline **16 days** (#842). Cron root cause fixed (PR #858 merged to main).
- **v0.3.3**: 6 open / 1 closed. Enterprise features. Blocked on v0.3.2.
- **v0.3.4**: 18 open / 8 closed. Community, docs, marketing. Blocked on v0.3.2.
- **Backlog**: 9 open (Linux platform, #777 Unicode capture).

## Agent Roster
- **Dev-Sirius**: Technical cofounder. Latest session (2026-04-05): pushed 12 branches — all merged as PRs #845-#855. Idle since Apr 5 (11 days). Next: #809 (unified find), #720 (split _element.py), #856 (split browser_cmd.py).
- **QA-Mariana**: Quality cofounder. 115 rounds completed. Self-hosted runner offline 16 days — QA fully blocked. 13 issues awaiting verification. **CRITICAL**: QA is the primary bottleneck for v0.3.2 release.
- **Orc-Mycelium**: Strategic orchestrator. This session (2026-04-15): escalated #842 day 16, no new progress.

## Coordination
- Bug tracking: GitHub Issues only
- State flow: status:in-progress -> status:done -> verified -> close
- CI must be green before any merge
- **BLOCKER**: Self-hosted runner ROBOT-COMPILE offline 16 days (#842)
- All remote branches clean (only develop and main)
- CI on develop: GREEN (Build & Test + CodeQL pass)
- Scheduled workflow crons DISABLED on main (PR #858) — re-enable when runner restored

## Code Health
- 150 source files, 222 test files
- Large files needing split: `_element.py` (1,517, #720), `browser_cmd.py` (1,378, #856), `macos.py` (1,065), `_input.py` (1,057)
- Version consistent: 0.3.1 across pyproject.toml, version.py, PyPI
- 5 stars, 5 forks on GitHub

## Completed Releases
- v0.1.0 — Core features
- v0.1.1 — 67 bug fixes (PyPI)
- v0.2.0 — Unified App Model + DPI
- v0.2.1 — Auto-routing + get command
- v0.3.0 — QA-tested release (PyPI)
- v0.3.1 — Hotfix: CMakeLists.txt + version.cpp sync
