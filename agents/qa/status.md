# QA Status
Last updated: 2026-04-02 18:16
Current round: 97 (continued)
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 5 passed, 1 failed (#777 unicode path), 18 skipped (commit 5553ad5). E2E: 9 passed, 3 xfail, 1 xpass
- Issues verified: none pending
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 8/11 passed, 3 failed, 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none
- Total active test cases: ~20
- Tests run: 11 regression + 7 exploratory + 10-step RPA workflow

## Top 3 Risks
1. **type -E newline drop (#784)** — P1: Multiline text automation broken in keystroke mode; workaround: use --paste
2. **JSON stderr duplication (#783)** — P2: Partially fixed (see clean, click still emits); workaround: redirect stderr separately
3. **click coords out-of-bounds (#787)** — P2: Silent success for impossible coordinates; no workaround
