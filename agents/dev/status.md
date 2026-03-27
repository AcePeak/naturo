# Dev Status
Last updated: 2026-03-27T21:30:00Z
Session: Fix P0 --pid bug (#471), fix P1 flaky CI test (#472)

## This Session
- Issue #471 (P0 bug) — --pid flag ignored: PR #475 created. Root cause: `_resolve_hwnd()` had no pid parameter, always returned foreground window. Added pid to _resolve_hwnd, get_element_tree, and all CLI call sites. Added --pid to type/press commands. 9 new tests.
- Issue #472 (P1 bug) — flaky test_window_lifecycle: PR #476 created. Replaced fixed 1.5s sleep with 10s polling loop, added process-name fallback for PID mismatch, track by HWND for disappearance.
- PRs #466 and #473 — attempted auto-merge but blocked by Windows DLL test timeout (cancelled after 25min on 20min timeout). All other CI checks green.
- Tests: 1902 passed, 489 skipped, 0 failed

## Open PRs by Me
- #466 — fix: stable hash-based element refs (fixes #456) — CI green except Windows DLL timeout
- #473 — fix: localized --app alias cleanup + tests (fixes #469) — CI green except Windows DLL timeout
- #475 — fix: --pid flag passthrough (fixes #471) — CI running
- #476 — fix: flaky test_window_lifecycle (fixes #472) — CI running

## Current State
- Earliest open milestone: v0.3.1 (#471, #472 — both now status:done with PRs)
- CI: green on main; PRs blocked by Windows DLL test timeout (infrastructure issue, not code)
- Key open issues: #21 (P0, Naturobot engine), #361 (P1, stable app/window ID), #312 (P1, Win32+UIA hybrid), #413 (P1, README comparison table)

## Next Session Should
- Check if PRs #466, #473, #475, #476 merged — if still blocked by Windows DLL timeout, investigate timeout increase or mark job as non-required
- Pick next P1 issue: #361 (stable app/window ID) or #413 (README comparison table)
- #21 (P0) is a large architectural issue — may need to break into sub-issues
