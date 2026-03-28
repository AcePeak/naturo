# Dev Status
Last updated: 2026-03-28T12:25:00Z
Session: Fix P1 bugs (#524, #525) + merge dependabot PRs

## This Session
- **Dependabot PRs #527-531 merged**: Bumped codecov-action, checkout, upload-artifact, codeql-action, download-artifact
- **PR #535 created + merged**: Fix --app explorer matching Program Manager instead of File Explorer (fixes #524 P1)
- **PR #536 created + merged**: Fix click --on for Chinese accessibility names with --app-id (fixes #525 P1)
- Tests: 2100 passed, 499 skipped, 0 failures
- PRs: 7 merged this session, 0 open

## Current State
- Earliest open milestone: v0.3.1 (both P1 bugs now status:done, awaiting QA verification)
- CI: GREEN on main
- Open PRs: none
- Code health: no TODO/FIXME/HACK markers, no bare excepts

## Next Session Should
1. **Check if QA verified #524 and #525** — close issues if verified
2. **Branch protection**: auto-merge still fails due to "Python Tests with DLL (Windows)" required check — remind Ace to update to require only "CI Gate"
3. **P2 backlog**: #411 (split windows.py 4064 lines), #412 (input strategy refactor), #419 (release notes automation)
4. **Self-driven**: Test first-user experience end-to-end, find CLI friction points
5. **Code health**: `backends/windows.py` is 4064 lines — splitting is overdue (#411)
