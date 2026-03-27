# Dev Status
Last updated: 2026-03-27T23:35:00Z
Session: Fix CI timeout (merged), rebase all PRs, #413 comparison table, #422 .work cleanup

## This Session
- **CI timeout fix (critical):** PR #477 merged (d456189). Increased Windows timeout 20→45min + added pip caching. First run passed in ~2.5min with warm cache.
- **Rebased all 6 blocked PRs** (#466, #473, #475, #476, #479, #480) onto new main. Windows CI running (cold cache, ~25min expected for first run).
- **Issue #413 (P1 docs):** PR #481 created. Added comparison table (naturo vs PyAutoGUI/pywinauto/AutoIt/WinAppDriver) to README.
- **Issue #422 (P2 chore):** PR #482 created. Removed 42 stale files from .work/, added .gitignore patterns.
- Tests: 1836 passed, 363 skipped, 0 failed

## Open PRs by Me
- #466 — fix: stable hash-based element refs (fixes #456) — Windows CI running
- #473 — fix: localized --app alias cleanup (fixes #469) — Windows CI running
- #475 — fix: --pid flag passthrough (fixes #471) — Windows CI running
- #476 — fix: flaky test_window_lifecycle (fixes #472) — Windows CI running
- #479 — fix: find_process alias resolution (fixes #474) — Windows CI running
- #480 — fix: error message format (fixes #478) — Windows CI running
- #481 — docs: comparison table (fixes #413) — Windows CI running
- #482 — chore: clean .work/ (fixes #422) — Windows CI running

## Current State
- Earliest open milestone: v0.3.4
- CI: GREEN on main. All PR Windows tests running with cold pip cache (~25min first run).
- All 6 bug issues + 2 new issues have PRs awaiting CI completion.

## Next Session Should
1. **Check all 8 PRs CI status** — merge any that passed (squash), enable auto-merge on others
2. **If merge conflicts** from sequential merges — rebase each PR onto updated main
3. **After PRs clear**, pick next P1 issues: #361 (stable app/window ID), #312 (Win32+UIA hybrid)
4. **If CI still failing** — investigate Windows test hanging (check CI logs for which step is slow)
