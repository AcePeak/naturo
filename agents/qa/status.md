# QA Status
Last updated: 2026-05-27 20:05
Current round: 116
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: skipped (full pytest suite not run this round — focused on direct CLI verification on real desktop instead; last full CI sha cf3e1fd, current 746ed92)
- Issues verified: #781 ✅ (JSON mode exit code on failure), #783 ✅ (no duplicate stderr in JSON mode) — both closed
- Power User persona (hour mod 8 = 4):
  - `naturo list apps` → 5 apps discovered (Terminal × 2, Clash for Windows, Explorer × 2)
  - `naturo see --app "Clash for Windows" -j` → valid JSON tree, e1=Pane "Clash for Windows" with children
  - `naturo capture --app "Clash for Windows" -o ...` → clean 1277×907 PNG, no other windows leaked (vision-confirmed: shows Profiles tab, no Terminal/Explorer bleed-through)
  - `--app nonexistent-app-12345` → JSON error WINDOW_NOT_FOUND, exit=1, clean stderr — error path correct
- Regression: not run this round (will run next round)
- New test cases created: none (no new bugs found this round)
- Test cases cleaned up: none
- New issues created: none
- Status:done remaining (was 13, now 11): #786, #788, #807, #810, #832, #833, #834, #840, #841, #843, #844
- Tests run: 8 scenarios

## Top 3 Risks
1. **11 status:done issues still pending verification** — all have merged PRs; 7 are runtime-verifiable on this desktop, 4 require specific scenarios (UWP Notepad, Calculator UIA, multi-window popup, stale PID). Need a multi-round plan to drain them.
2. **Last full CI desktop run was cf3e1fd (Apr 5)** — 82 commits behind. While each PR was unit-tested, integration regression coverage is stale. CI runner #842 still offline (day 59).
3. **Spot-check found `--id` flag inconsistency**: `naturo click --id eN` accepts eN refs (interprets as ref, returns REF_NOT_FOUND on miss), but `naturo type` has no `--id` flag at all — uses `--on`. Same eN value, different option name across sister commands. Not filed yet; will deepen the check next round before opening a UX issue.
