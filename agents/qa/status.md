# QA Status
Last updated: 2026-04-01 05:02 UTC
Current round: 75
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 1 failed, 5 passed, 18 skipped (commit 5d8d101); E2E: 2 failed, 8 passed
- Issues verified: #717, #713, #712, #730 (pass); #714, #702 (deferred, PRs not merged)
- E2E tests: Notepad (pass), Calculator (pass)
- Regression: 10/11 passed, 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none
- Total active test cases: 20
- Tests run: 11

## Top 3 Risks
1. #743 — `app quit` with Chinese app name targets wrong PID (P1, reproducible every round)
2. #729 — CI desktop tests fail (Notepad window not found after launch), blocking CI green status
3. PRs #741 and #742 still open — coverage threshold and AI vision dedup fixes not yet on develop
