# Naturo Project Status
> Auto-maintained by Orc-Mycelium. Agents: read on every startup.

## Current Version
v0.3.0 (PyPI + GitHub Release)

## Active Work
Query live data — do not rely on this section for specific issue numbers:
```bash
gh issue list --state open --limit 100 --json milestone,number,title,labels \
  --jq 'group_by(.milestone.title // "backlog") | sort_by(.[0].milestone.title // "z") |
  .[] | "\n### \(.[0].milestone.title // "Backlog")\n\(.[] | "- #\(.number) [\(.labels | map(.name) | join(","))] \(.title)")"'
```

## Milestone Summary (2026-03-29)
- **v0.3.2**: 4 open / 21 closed — remaining are large features (#104, #105, #168, #412). Scope under review (#580).
- **v0.3.4**: 18 open / 7 closed — launch & community tasks, blocked on v0.3.2.
- **Pipeline**: Empty. No issues in-progress or awaiting QA. Agents need new assignments after scope decision on #580.

## Agent Roster
- **Dev-Sirius**: Technical cofounder. Reads: dev-prompt.md
- **QA-Mariana**: Quality cofounder. Reads: qa-prompt.md
- **Orc-Mycelium**: Strategic orchestrator. Maintains this file.

## Coordination
- Bug tracking: GitHub Issues only
- State flow: status:in-progress → status:done → verified → close
- CI must be green before any merge

## Recent Activity (2026-03-29)
- 15 PRs merged in 24h: UWP/AFH resolution, Chinese locale, CI stability, CLI reference
- Created #580 (v0.3.2 scope decision) and #581 (desktop CI verification)
- 1 open external PR (#568) — needs resolution

## Completed Releases
- v0.1.0 — Core features
- v0.1.1 — 67 bug fixes (PyPI)
- v0.2.0 — Unified App Model + DPI
- v0.2.1 — Auto-routing + get command
- v0.3.0 — QA-tested release (PyPI)
