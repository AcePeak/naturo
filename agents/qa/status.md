# QA Status
Last updated: 2026-04-01 09:12
Current round: 77
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 9 passed, 3 failed, 3 xfailed (commit cf607cb)
- Issues verified: #729 (partial — `--app notepad` works, `--app a1` doesn't), #702 (blocked)
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 9/11 passed, 0 retired
- New test cases created: TC-0039
- Test cases cleaned up: none
- New issues created: #752
- Total active test cases: 23
- Tests run: 11

## Top 3 Risks
1. UWP Notepad enumeration on Chinese Windows (#749) — blocks CI and multiple test cases
2. App ID filter discoverability (#752) — first-time user friction
3. Zombie UWP processes accumulating — system-level process lifecycle issue
