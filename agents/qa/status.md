# QA Status
Last updated: 2026-04-01 18:16
Current round: 78
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 5 passed, 1 failed, 18 skipped, 2 xpassed (commit 2434ab1)
- Issues verified: #724, #729, #749, #750, #752, #754, #757, #702 (all pass, all closed)
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 19/19 passed, 1 retired (TC-0028)
- New test cases created: TC-0040
- Test cases cleaned up: TC-0028 (retired — #586 closed, 5 passes)
- New issues created: #777
- Total active test cases: 25
- Tests run: 19 regression + 2 E2E + 5 exploratory + 14 CI = 40

## Top 3 Risks
1. CI unicode path failure (#777) — naturo_core.dll cannot save to paths with Chinese chars, affects 35%+ of Chinese Windows users
2. AI vision dedup untestable without API key on runner — #702 verified only via unit tests, not live
3. v0.3.2 scope tripled (31 open issues) — browser automation + AI registry + original UWP fixes may delay release
