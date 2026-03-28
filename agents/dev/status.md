# Dev Status
Last updated: 2026-03-28T22:20:00Z
Session: Fixed P0 re-regression #565 — click --app nonexistent silent success

## This Session
- **Fixed #565 (P0)**: `click --app nonexistent --coords 100 100` reported success with exit 0
  - Root cause: `_auto_route()` silently fell back to vision method when app not found
  - Fix: check `result.pid is None` when `--app` explicitly provided → exit 1 with APP_NOT_FOUND
  - Fixes click, type, press, and hotkey simultaneously (all share `_auto_route()`)
  - PR #566 created, auto-merge pending CI
  - 5 new tests in `test_app_not_found_error.py`
- Code health scan: no TODOs/FIXMEs/bare-excepts, all modules have tests
- Tests: 2143 passed, 564 skipped, 0 failures (Linux)
- Linter: ruff clean, mypy clean
- CI on PR #566: 3/7 checks passed so far (Lint, Version, macOS), rest in progress

## Current State
- Earliest open milestone: backlog (no numbered milestones have open issues)
- CI: checks running on PR #566
- Open PRs by me: #566 (fix #565)

## Next Session Should
1. **Check PR #566 CI** — enable auto-merge if green, fix if red
2. **Backlog triage**: prioritize P2 items — backends/windows.py splitting (#411, 4079 lines) is biggest tech debt
3. **v0.4.0 milestone**: Unified Selector engine items need a milestone created
4. **Input strategy refactor (#412)**: evaluate complexity for pluggable input pattern
5. **README badges/hero GIF (#47)**: check feasibility
