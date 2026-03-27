# Dev Status
Last updated: 2026-03-27T13:22Z
Session: Fix PR #434 lint, close 3 issues (#427, #428, #409), enable auto-merge on all PRs

## This Session
- PR #434 (fixes #430): Fixed mypy lint failure — added `type: ignore[attr-defined]` for Windows-only ctypes.windll calls. Pushed fix.
- Issue #427 (P1, CI) — PR #437 created: Assert HWND uniqueness instead of PID in multi-window Notepad test (Win11 tabs share 1 PID)
- Issue #428 (P2, CI) — PR #438 created: Replace fixed sleep with polling loop for window disappearance in lifecycle test
- Issue #409 (P1, task) — PR #439 created: Add pytest-cov + Codecov upload to all 3 CI jobs, badge in README
- Enabled auto-merge (squash) on PRs #429, #433, #434, #435, #436, #437, #438, #439
- Tests: 26 passed (routing), all lint/ruff clean
- PRs: #437, #438, #439 created; #434 lint fix pushed

## Current State
- Earliest open milestone: v0.3.1 — all issues now have PRs, awaiting CI + merge
- CI: green on #429, #435, #436; #434 re-pushed (awaiting new CI run); #433 had Windows tests cancelled (may need retry)
- Open PRs by me: #429, #433, #434, #435, #436, #437, #438, #439 (8 total, all with auto-merge)
- v0.3.1 issues with PRs: #425→#433, #426→#429, #427→#437, #428→#438, #408→#436, #409→#439, #410→#435

## Next Session Should
- Check if any PRs have merged via auto-merge — if so, v0.3.1 may be closeable
- Check PR #433 (IME fix) — Windows tests were cancelled, may need re-trigger or investigation
- If v0.3.1 is clear, advance to next milestone
- Address any review feedback on open PRs
- Look at #430 (backlog, P1) — PR #434 covers this, ensure it merges
