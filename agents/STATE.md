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

## Milestone Summary (2026-05-13 review — Day 45 no-op)
- **v0.3.2**: 25 open / 82 closed (77%). **No progress since Apr 5** — project stalled **38 days** on offline runner. 13 issues `status:done` awaiting QA verification (all have merged PRs). **Day-44 categorization carried over**: 8 of 13 are credibly unit-test-verifiable (#781, #783, #810, #832, #833, #834, #840, #844); 5 require a real desktop session (#786, #788, #807, #841, #843). Dev issues: #809 (unified find, P1, needs runner), **#720 and #856 UNBLOCKED** (pure Python refactors). **BLOCKER**: self-hosted runner offline **day 45** (#842). #860 (cloud VM proposal) day 7 — 0 assignees, 0 comments. **Proposal held**: ship v0.3.2 = 8 unit-testable issues, defer 5 desktop-required to v0.3.3 — requires explicit Ace authorization (see 2026-05-12 review). 9th consecutive day no GitHub escalation posted.
- **v0.3.3**: 6 open / 1 closed. Enterprise features. Blocked on v0.3.2.
- **v0.3.4**: 18 open / 8 closed. Community, docs, marketing. Blocked on v0.3.2.
- **Backlog**: 9 open (Linux platform, #777 Unicode capture).

## Agent Roster
- **Dev-Sirius**: Technical cofounder. Latest session (2026-04-05): pushed 12 branches — all merged as PRs #845-#855. Idle 37 days. **UNBLOCKED tasks: #720 (split _element.py), #856 (split browser_cmd.py)** — pure Python, no runner needed. #809 (unified find) still blocked on runner.
- **QA-Mariana**: Quality cofounder. 115 rounds completed. Self-hosted runner offline ~38 days — QA fully blocked. 13 issues awaiting verification. **CRITICAL**: QA is the primary bottleneck for v0.3.2 release.
- **Orc-Mycelium**: Strategic orchestrator. Latest session (2026-05-13 00:01): Day 45 no-op. State unchanged since 2026-05-12 15:01. Escalation suppression continues (day 9 of 9). Loop fires daily despite 2026-05-09 15:01 pause request. Ace has not responded to day 38–41 #842 escalations or to #860 (7 days unassigned). State machine still deadlocked pending Ace decision. Cleared stale pr-requests.md queue (12 merged Dev-Sirius branches from 2026-04-05).

## Coordination
- Bug tracking: GitHub Issues only
- State flow: status:in-progress -> status:done -> verified -> close
- CI must be green before any merge
- **BLOCKER**: Self-hosted runner ROBOT-COMPILE offline day 42 (#842). **ALTERNATIVE**: #860 (cloud Windows VM) — P1, awaiting Ace decision since 2026-05-07 (3 days unassigned)
- GitHub-hosted `windows-latest` runner confirmed CANNOT substitute (no interactive desktop session)
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
