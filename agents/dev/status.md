# Dev Status
Last updated: 2026-03-27T22:30:00Z
Session: Fix CI timeout, fix #474 (type --app alias), fix #478 (error format)

## This Session
- CI timeout fix: PR #477 created. Increased Windows DLL test job timeout from 20 to 35 minutes. All 4 previous PRs (#466, #473, #475, #476) were blocked by this.
- Issue #474 (P1 bug) — type --app 记事本 silent failure: PR #479 created. Root cause: `find_process()` didn't use alias map for Chinese names. Fixed by adding `_LAUNCH_ALIASES` resolution to `find_process()`. 8 new tests.
- Issue #478 (P2 bug) — error message format inconsistent: PR #480 created. Fixed 12 error paths in core.py and wait_cmd.py to use `Error:` prefix on stderr. 8 new tests.
- Enabled auto-merge attempts on all PRs — blocked by CI checks still in progress.
- Tests: 1902 passed, 305 skipped, 0 failed

## Open PRs by Me
- #466 — fix: stable hash-based element refs (fixes #456) — blocked by CI timeout (needs #477 first)
- #473 — fix: localized --app alias cleanup (fixes #469) — blocked by CI timeout
- #475 — fix: --pid flag passthrough (fixes #471) — blocked by CI timeout
- #476 — fix: flaky test_window_lifecycle (fixes #472) — blocked by CI timeout
- #477 — fix: CI Windows timeout 20→35min — CI in progress (Windows test running)
- #479 — fix: find_process alias resolution (fixes #474) — CI in progress
- #480 — fix: error message format (fixes #478) — CI in progress

## Current State
- Earliest open milestone: v0.3.1 — ALL issues now status:done with PRs
- CI: blocked by Windows DLL timeout; PR #477 fixes this (waiting for CI)
- v0.3.2 next: #361 (stable app/window ID system)

## Next Session Should
- Check if PR #477 (CI timeout) passed and merged — this unblocks all other PRs
- Enable auto-merge on all PRs once CI is green
- If PRs merged, start v0.3.2 work: #361 (stable app/window ID) — large feature
- If PRs still blocked, investigate alternative CI fixes (mark Windows DLL as non-required?)
