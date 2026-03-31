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

## Milestone Summary (2026-03-29 evening)
- **v0.3.2**: 5 open / 24 closed — #168 (clipboard) completed today. Remaining: #104 (selector templates), #105 (selector mgmt), #412 (input strategy refactor), plus meta-issues #580 (scope decision) and #581 (desktop CI). Awaiting Ace's decision on #580.
- **v0.3.4**: 18 open / 7 closed — launch & community tasks, blocked on v0.3.2.
- **Pipeline**: Empty. No issues in-progress or awaiting QA. Agents blocked pending #580 scope decision.

## Agent Roster
- **Dev-Sirius**: Technical cofounder. Reads: dev-prompt.md
- **QA-Mariana**: Quality cofounder. Reads: qa-prompt.md
- **Orc-Mycelium**: Strategic orchestrator. Maintains this file.

## Coordination
- Bug tracking: GitHub Issues only
- State flow: status:in-progress → status:done → verified → close
- CI must be green before any merge

## Recent Activity (2026-03-29)
- **35 PRs merged in one day** — the most productive day in project history
- Morning sprint: P0 bug fixes (click targeting #610, DPI coordinates #622, coverage estimation #621, AI vision parsing #618), P1 fixes (type/press focus #614, app quit #623, type escape #624), new feature (#607 clipboard, #626 CDP cascade), QA scenarios #616
- Afternoon sprint: Major refactors (#627 windows.py split, #638 MCP server split), selector usability #628, silent except patterns #631, CI auto-merge #632, 87 new unit tests (#633, #636, #637)
- Commented on #580 recommending v0.3.2 ship as-is, move #104/#105/#412 to v0.4.0
- 1 open external PR (#568) — reviewed, recommending closure (targets already-resolved issue)

## Completed Releases
- v0.1.0 — Core features
- v0.1.1 — 67 bug fixes (PyPI)
- v0.2.0 — Unified App Model + DPI
- v0.2.1 — Auto-routing + get command
- v0.3.0 — QA-tested release (PyPI)
