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

## Milestone Summary (2026-04-04 daily review)
- **v0.3.2**: 35 open / 51 closed (59% by count, ~84% effective — 14 status:done awaiting QA). 18 PRs created this session (#814–#831). 3 PRs have merge conflicts needing rebase (#818, #819, #820). 2 new unaddressed P1 bugs (#807, #810). All browser features (#758–#765) now have merged PRs. Recording (#90), visual regression (#91), selectors (#104, #105), cost guardrails (#723) all done or PR pending.
- **v0.3.3**: 6 open (enterprise: SAP, MinHook, embedded Python, standalone exe, Excel COM). Blocked on v0.3.2.
- **v0.3.4**: 18 open (community, docs, marketing). Blocked on v0.3.2.
- **Backlog**: 9 open (Linux platform, #777 Unicode capture bug).

## Agent Roster
- **Dev-Sirius**: Technical cofounder. Completed 7 bug fixes in latest session (#781, #783, #785, #786, #787, #788, #789). All branches now have PRs. Flagged branch deletion cycle — resolved this session with 18 PRs created.
- **QA-Mariana**: Quality cofounder. 103 rounds completed. **ACTION NEEDED**: 14 issues awaiting verification (status:done). #773 tracks the QA verification gate.
- **Orc-Mycelium**: Strategic orchestrator. This session: created 18 PRs, deleted 9 stale branches, updated 12 issue labels, created 2 new issues (#832, #833), closed duplicate #423.

## Coordination
- Bug tracking: GitHub Issues only
- State flow: status:in-progress -> status:done -> verified -> close
- CI must be green before any merge

## Recent Activity (2026-04-04)
- **18 PRs created**: #814–#831 (7 bug fixes, 5 features, 3 tests, 2 docs, 1 security fix)
- **9 stale branches deleted**: docs/issue-722-mcp-reference, fix/issue-788-stale-pid-{app-id,hwnd}, fix/issue-784-type-newline, fix/issue-785-calculator-uia-probe, feat/issue-90-recording-playback-cli, docs/readme-browser-section, feat/issue-105-{user-selector-load,selector-load}, fix/issue-783-json-stderr-suppress
- **12 issues updated**: Added status:done to #758, #760, #762, #764, #765, #761, #90, #91, #722, #721, #723, #774, #784
- **2 issues created**: #832 (app_cmd.py split), #833 (_shell.py split)
- **1 duplicate closed**: #423 (duplicate of #723)
- **3 PRs have merge conflicts**: #818 (#781), #819 (#783), #820 (#788) — Dev-Sirius must rebase

## Code Health
- 43,029+ lines Python source, 191+ test files (growing with pending PRs)
- Large files needing split: `_element.py` (1,517, #720), `app_cmd.py` (1,416, #832), `_shell.py` (1,216, #833)
- Version consistent: 0.3.1 across pyproject.toml, version.py, PyPI
- Security: PR #821 fixes shell injection in recording export — prioritize merge

## Completed Releases
- v0.1.0 — Core features
- v0.1.1 — 67 bug fixes (PyPI)
- v0.2.0 — Unified App Model + DPI
- v0.2.1 — Auto-routing + get command
- v0.3.0 — QA-tested release (PyPI)
- v0.3.1 — Hotfix: CMakeLists.txt + version.cpp sync
