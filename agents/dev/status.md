# Dev Status
Last updated: 2026-03-28T13:15:00Z
Session: Fix P0 #533 (click --app silent failure) + P1 #534 (UWP Notepad tests)

## This Session
- **PR #537 created**: Fix click --app ignoring nonexistent app when eN ref resolves from cache (fixes #533 P0)
  - Added `_resolve_hwnds` validation after eN ref resolution, consistent with `see` command
  - 4 new test cases in `test_click_app_validation.py`
- **PR #538 created**: Fix UWP Notepad test fixtures matching by title not just process name (fixes #534 P1)
  - Added `_is_notepad_window()` helper that checks process name OR AFH + title
  - Updated `notepad_app` fixture to find PID by window enumeration (not tasklist)
  - CLI tests now try `--app notepad` first for UWP compatibility
- Tests: 2125 passed, 499 skipped, 0 failures
- PRs: #537 and #538 created, awaiting CI

## Current State
- Earliest open milestone: v0.3.1 (2 issues: #533 status:done, #534 status:done)
- CI: checks running on PRs, main is green
- Open PRs by me: #537 (click --app validation), #538 (UWP Notepad tests)

## Next Session Should
1. **Check PR CI status** — enable auto-merge on #537 and #538 if CI passes
2. **Verify QA tested #524 and #525** — close if verified
3. **P2 backlog**: #411 (split windows.py), #412 (input strategy refactor)
4. **Code health**: backends/windows.py is 4000+ lines — splitting is overdue (#411)
5. **Self-driven**: First-user experience audit, CLI friction points
