# QA Status
Last updated: 2026-04-03 00:23
Current round: 103
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 5 passed, 1 failed (#777 known), 18 skipped, 1 xpassed (commit 2308b68)
- CI E2E Tests: 9 passed, 3 xfailed, 1 xpassed
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass), Calculator (fail — UWP registration broken)
- Regression: 6/10 passed, 4 failed (all known bugs), 14 reviewed not executed
- Test cases retired: none
- New test cases created: none
- New issues created: none
- Total active test cases: 29
- Tests run: 10

## Top 3 Risks
1. **Calculator UWP broken on runner** — cannot launch or test, blocks multiple test cases
2. **type -E newline drop (#784)** — P1: breaks multi-line automation, no workaround
3. **press --app focus mismatch (#807)** — P1: hotkeys sent to wrong process
