# QA Status
Last updated: 2026-04-02 11:14
Current round: 93
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 1 passed, 1 failed (#785), 8 skipped (commit fad72e2); E2E: 9 passed, 3 xfailed, 1 xpassed
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass — type/click/keyboard/JSON verified, menu click fail #786)
- Regression: 3/8 passed, 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none (all findings confirmed existing issues #783-#787)
- Total active test cases: 25
- Tests run: 8 regression + 8 exploratory + 7 Chinese user simulation = 23

## Top 3 Risks
1. **UWP Calculator invisible** (#785) — P0, Calculator launches but invisible to naturo. CI tests also fail.
2. **type -E drops newlines** (#784) — P1, multiline text via keystroke simulation broken. Users must use --paste workaround.
3. **UWP menu click non-functional** (#786) — P1, click eN on UWP Notepad menu items reports success but menu does not open.
