# QA Status
Last updated: 2026-04-04 22:15
Current round: 112
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 1 failed, 1 passed, 8 skipped (commit 42443f1)
- CI E2E Tests: 9 passed, 3 xfailed, 1 xpassed (commit 42443f1)
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass — type/see/json/filter; fail — menu click #786), Calculator (fail — invisible #785)
- Regression: 5/9 passed, 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: #841
- Total active test cases: 26
- Tests run: 9 regression + E2E + exploratory + scripter simulation

## Top 3 Risks
1. Type command drops newlines (#840/#784) — P1, affects all multiline use cases
2. Calculator UWP invisible (#785/#841) — P0, app launch success but app completely unusable, CI fails
3. Menu click silent failure (#786) — P1, reports success but menu doesn't open
