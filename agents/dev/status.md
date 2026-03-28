# Dev Status
Last updated: 2026-03-28T18:20:00Z
Session: PR merges + docs fixes + dead code cleanup

## This Session
- **Merged PR #550** (commit `9e81e49`): CLI reference generator (fixes #414)
- **Fixed #551**: marked Excel COM as shipped in ROADMAP.md
  - PR #552 created and merged (commit `587042c`)
- **Fixed #553**: removed dead java/sap CLI stubs (130 lines of unreachable code)
  - PR #554 created, CI running
- **Created #553**: dead code issue for unregistered java/sap command stubs
- Product gap analysis: CLI help output is clean, README is accurate
- Tests: 2192 passed, 497 skipped, 0 failures
- Linter: clean
- PRs: #550 merged, #552 merged, #554 pending CI

## Current State
- Earliest open milestone: none (all milestones clear)
- CI: green on main
- Open PRs by me: #554 (refactor: remove dead java/sap stubs)
- All open issues are backlog P2 tasks/enhancements (40 issues)

## Next Session Should
1. **Merge PR #554** if CI green, or fix if CI fails
2. **Backlog triage**: backends/windows.py splitting (#411) is the biggest tech debt (4064 lines)
3. **Consider v0.4.0 milestone**: Unified Selector engine items need a milestone
4. **README badges**: add CI status, PyPI version, license badges for professional appearance
5. **Excel hidden=True**: issue #551 suggested unhiding the excel group — evaluate if it should be visible in --help
