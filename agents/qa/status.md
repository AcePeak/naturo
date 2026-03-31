# QA Status
Last updated: 2026-04-01 00:15
Current round: 73
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 12 passed, 4 failed, 21 skipped/xfailed (commit 2f59abe)
- Issues verified: none new (all status:done already verified)
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 12/14 passed, 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none (all failures tracked in #728, #704, #729)
- Total active test cases: 20
- Tests run: 14 regression + full E2E + exploratory

## Top 3 Risks
1. **CI Notepad discovery broken** (#729) — 4 CI tests fail because `app launch notepad` can't find the window. Blocks automated CI validation.
2. **Chinese filepath capture** (#728) — `naturo capture -o` fails with Unicode paths. Affects Chinese/CJK users.
3. **Standalone modifier keys** (#704) — `press alt/ctrl/shift` individually rejected. Blocks keyboard-only accessibility workflows.
