# QA Status
Last updated: 2026-04-02 12:15
Current round: 94
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 1 failed (#785), 1 passed, 8 skipped (commit 7ac1674); E2E: 9 passed, 3 xfailed, 1 xpassed
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass — type/click/keyboard/JSON verified, menu click fail #786)
- Regression: 3/10 passed, 0 retired
- New test cases created: TC-0046 (see exit code 0 on error, non-JSON)
- Test cases cleaned up: none
- New issues created: none (commented on #781 with non-JSON extension)
- Total active test cases: 23
- Tests run: 10 regression + 9 exploratory + 5 power user simulation = 24

## Top 3 Risks
1. **Stale PID routing** (#788) — P0, commands silently target wrong processes after app restart
2. **UWP Calculator invisible** (#785) — P0, Calculator launches but invisible to naturo. CI tests also fail.
3. **--app filter cross-process** (#789) — P1, title-based matching causes wrong process targeting in multi-app environments
