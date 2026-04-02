# QA Status
Last updated: 2026-04-02 21:17
Current round: 100
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 14 passed, 1 failed (#777 unicode path), 18 skipped (commit e3d77d9). E2E: 9 passed, 3 xfail, 1 xpass
- Issues verified: none pending
- E2E tests: Notepad (pass), Explorer (pass)
- Regression: 7/11 passed, 4 failed (known: #783, #784, #786, #787, #807)
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none (all failures match existing issues)
- Total active test cases: 25
- Tests run: 11 regression + E2E + exploratory + accessibility user simulation

## Top 3 Risks
1. **press --app focus mismatch (#807)** — P1: Keyboard shortcuts sent to wrong process, blocks accessibility users
2. **type -E newline drop (#784)** — P1: Multiline text automation broken in keystroke mode; workaround: use --paste
3. **UWP menu click (#786)** — P1: click eN on UWP Notepad menu items does not open menu
