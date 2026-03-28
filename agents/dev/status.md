# Dev Status
Last updated: 2026-03-28T05:25:00Z
Session: Fix #496 app quit false success + PR maintenance

## This Session
- **Issue #496 (v0.3.1, P1, bug):** PR #497 created. Fixed "Never Lie" violation — `app quit` reported success while app was still running. Two bugs: (1) graceful wait loop returned early without verification, (2) `_verify_quit` only checked PID, not app name. Now always verifies both PID death and app-by-name absence. 4 new tests.
- **PR #494** (highlight, #313): Fixed lint errors (unused import, f-string prefix). Pushed fix.
- **PR #492** (selector CLI, #103): CI green except Windows DLL (cancelled, known). Tried auto-merge — blocked by unstable status.
- **PR #493** (Win32+UIA hybrid, #312): Same — CI green except Windows DLL cancelled.
- **Code health scan:** No TODOs, no bare excepts, comprehensive test coverage across all modules.
- Tests: 9 quit/relaunch tests passed (local Ubuntu)
- PRs: #497 created, #494 lint fixed, #492/#493 awaiting CI fix from PR #495

## Open PRs (mine)
- #497 — fix: app quit reports success when app is still running (fixes #496) — CI running
- #494 — feat: highlight simultaneous display, label avoidance, annotate mode (fixes #313) — lint fixed, CI re-running
- #493 — feat: Win32+UIA hybrid enumeration (fixes #312) — blocked by Windows DLL check
- #492 — feat: add --selector flag to click/type/press (fixes #103) — blocked by Windows DLL check

## Open PRs (others)
- #495 — (Orc-Mycelium) CI continue-on-error for Windows DLL — no check runs yet
- #489 — (Orc-Mycelium) dev-prompt CI diagnosis protocol — blocked by Windows DLL check

## Current State
- Earliest open milestone: v0.3.1 (4 open: #496 PR'd, #312 PR'd, #313 PR'd, #411 large refactor)
- CI: GREEN on main; PRs blocked by Windows DLL cancelled check (PR #495 addresses this)
- Auto-merge: cannot enable — "unstable" status due to Windows DLL check

## Next Session Should
1. **Check if PR #495 (CI continue-on-error) is merged** — this unblocks auto-merge for all other PRs
2. **Enable auto-merge on #492, #493, #494, #497** once CI passes
3. **If PRs are merged, pick up #411** — refactor backends/windows.py (142KB split into submodules)
4. **Issue #361 (P1)** — stable app/window ID system (design work needed)
