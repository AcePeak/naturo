# QA Status
Last updated: 2026-04-02 10:21
Current round: 92
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 1 failed (#785), 1 passed, 8 skipped (commit 279601c); E2E: 9 passed, 3 xfailed, 1 xpassed
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass), Explorer (pass), Calculator (fail — #785)
- Regression: 4/9 passed, 5 failed (all known issues), 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none (all bugs already tracked)
- Total active test cases: 20
- Tests run: 9 regression + CI suite + E2E

## Top 3 Risks
1. **UWP Calculator invisible** (#785) — P0, Calculator launches but invisible to naturo. CI tests also fail.
2. **Cross-process app filter contamination** (#789) — P1, --app matches Chrome when searching for "notepad" because Chrome tab title contains "notepad". Enterprise RPA dev could automate wrong app.
3. **UWP menu click non-functional** (#786) — P1, click eN on UWP Notepad menu items reports success but menu does not open. Blocks menu-driven automation.
