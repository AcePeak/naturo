# QA Status
Last updated: 2026-03-31 20:27
Current round: 70
Current milestone: v0.3.1

## This Round
- CI Desktop Tests: 132 passed, 4 failed, 4 skipped, 2 timeouts (commit db090e9)
- Issues verified: none (no status:done issues)
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 10/12 passed, 1 blocked (TC-0007), 1 failed (TC-0034)
- New test cases created: none
- Test cases cleaned up: none
- New issues created: #697
- Total active test cases: 22
- Tests run: 12

## Top 3 Risks
1. **CI test infrastructure fragile** — Notepad UIA detection and lifecycle tests consistently fail in test runner but work manually. 6 tests affected (#697).
2. **Chinese/Unicode file paths broken** — `naturo capture` fails with Chinese paths (#693). Blocks Chinese user adoption.
3. **AI vision cascade misdirects** — Vision cascade captures terminal instead of target app (#694). Impacts hybrid detection quality.
