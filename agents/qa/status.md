# QA Status
Last updated: 2026-04-02 07:17 UTC
Current round: 90
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 130 passed, 4 failed, 1 skipped (commit 896ba10); E2E: 9 passed, 2 xfailed, 2 xpassed
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass), Calculator (blocked #785)
- Regression: 5/9 passed, 2 failed, 1 skipped, 1 retired
- New test cases created: TC-0045
- Test cases cleaned up: none
- New issues created: #788
- Total active test cases: 24
- Tests run: 9 regression + CI suite

## Top 3 Risks
1. **Silent failure on stale PID routing** (#788) — type/click report success but target wrong process after app restart. Deal-breaker for adoption.
2. **Cross-process app filter contamination** (TC-0011) — --app matches wrong process when app name appears in other window titles. Confirmed with JSON evidence.
3. **UWP Calculator invisible** (#785) — Cannot test Calculator at all. CI tests also fail for Calculator UIA detection.
