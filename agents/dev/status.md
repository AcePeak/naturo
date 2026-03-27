# Dev Status
Last updated: 2026-03-27T20:25:00Z
Session: PR housekeeping, localized --app alias fix (#469)

## This Session
- PR #470 (fixes #448) — skip auto-routing for eN ref clicks: **merged** (59b6f0b)
- PR #460 (Orc) — dev-prompt pull latest main: **merged** (57b2747)
- PR #463 (Orc) — dev agent handle open PRs: **merged** (2be10a3)
- PR #464 (Orc) — QA agent app lifecycle: **merged** (9515266)
- PR #466 (fixes #456) — stable hash-based element refs: branch updated, CI running (5/6 green, Windows DLL test in progress)
- Issue #469 (P1 bug) — --app localized app names: PR #473 created. Alias map already worked; cleaned up non-ASCII values, added WordPad/截图工具 aliases, 18 new tests.
- Tests: 1854 passed, 547 skipped, 0 failed
- PRs merged: #470, #460, #463, #464 | PRs pending CI: #466, #473

## Open PRs by Me
- #466 — fix: stable hash-based element refs (fixes #456) — 5/6 CI green, Windows DLL test running
- #473 — fix: localized --app alias cleanup + tests (fixes #469) — 2/5 CI green, rest running

## Current State
- Earliest open milestone: backlog (no milestones assigned to remaining issues)
- CI: green on main
- Key open issues: #21 (P0, Naturobot engine), #361 (P1, stable app/window ID), #312 (P1, Win32+UIA hybrid), #413 (P1, README comparison table)

## Next Session Should
- Check CI on PRs #466 and #473 — merge if green, fix if failing
- If both merged, pick next P1 issue: #361 (stable app/window ID) or #312 (Win32+UIA hybrid)
- #21 (P0) is a large architectural issue — may need to break into sub-issues
- Consider expanding _APP_ALIASES with more common apps (Office suite, Photos, etc.) as a follow-up
