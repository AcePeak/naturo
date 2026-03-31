# QA Status
Last updated: 2026-03-31 19:25
Current round: 69
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 5 passed, 1 timeout, 18 skipped (desktop); 7 passed, 3 failed (e2e) — commit 4b752a3 — failures covered by #683
- Issues verified: #683 (cannot verify — PR #690 not merged)
- E2E tests: Notepad (pass), Calculator (pass)
- Regression: 13/16 passed, 1 blocked (TC-0007), 1 retired (TC-0016), 1 new fail (TC-0034)
- New test cases created: TC-0034 (capture Chinese file paths)
- Test cases cleaned up: TC-0016 retired (5 passes, #469 closed)
- New issues created: #693 (capture fails with Chinese/Unicode file paths)
- Total active test cases: 18
- Tests run: 16

## Regression Details (Round 69)
| TC | Name | Result |
|----|------|--------|
| TC-0003 | Chinese app name matching | PASS (5) |
| TC-0004 | Calculator E2E | PASS (24) |
| TC-0007 | Click short text | BLOCKED (Chinese locale) |
| TC-0008 | Multi-window targeting | PASS (10) |
| TC-0011 | App filter cross-process | PASS (4) |
| TC-0012 | --pid targeting | PASS (2) |
| TC-0014 | Scripted Notepad workflow | PASS (17) |
| TC-0015 | app quit silent failure | PASS (10) |
| TC-0016 | UWP app name matching | RETIRED (5 passes, #469 closed) |
| TC-0024 | Background window click | PASS (2) |
| TC-0028 | UWP multi-tab quit | PASS (2) |
| TC-0030 | type backslash escape | PASS (3) |
| TC-0031 | Notepad menu click | PASS (2) |
| TC-0032 | Title matching multiwindow | PASS (1) |
| TC-0033 | MCP click element_id | PASS (1) — was FAIL, fixed by #688 |
| TC-0034 | Chinese path capture | FAIL (new) — filed as #693 |

## Phase 4 Findings (Chinese User Simulation)
- `--app 记事本` correctly matches Notepad on Chinese Windows
- Chinese text typing (你好世界) works perfectly
- Emoji + mixed Unicode/Chinese/English text works
- `naturo find` with Chinese search terms works
- **BUG**: `naturo capture -o <Chinese path>` fails — C++ DLL uses narrow string for file I/O (#693)

## Top 3 Risks
1. **CI tests failing (#683)** — PR #690 open, all CI Notepad tests fail. Blocks CI green status.
2. **#693 Chinese file path capture** — affects Chinese users (primary audience on Chinese Windows)
3. **AI Vision tests not run** — TC-0025/26/27 require DPI/vision setup; persistent coverage gap
