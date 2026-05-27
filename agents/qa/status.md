# QA Status
Last updated: 2026-05-28 00:10
Current round: 120
Current milestone: v0.3.2 (27 open / 82 closed, 75%)

## This Round
- Persona: First-time User (hour 00 % 8 = 0)
- CI Desktop Tests: skipped (no interactive desktop in QA session; blocker #863, now 4th consecutive round; `.last-ci-sha` NOT advanced)
- Targeted unit tests for the 5 blocked status:done issues: **109 passed / 24 skipped** (code health green for #786/#788/#807/#840/#843)
- Issues verified + closed: **none** — all 5 status:done still blocked on #863 (round 120 data point posted to #863)
- E2E tests: skipped (no desktop)
- Regression (Phase 5): 2 testable cases pass — **TC-0041** (consec 30), **TC-0046** (consec 21). 2 fail — **TC-0054** (#866 unchanged), **TC-0055** (new, confirms #867)
- New issues created: **#867** (bug, P2, from:qa, v0.3.4) — `Did you mean` typo suggestions leak hidden `snapshot` command. Discovered during First-time User simulation.
- New test cases created: **TC-0055** (`exploratory/hidden-snapshot-typo-leak.yaml`)
- Test cases cleaned up: none
- Total active test cases: 34 active / 22 retired
- Tests run: 109 unit + 4 regression TCs + ~20 first-time-user CLI probes (help, typo paths, flag positions, boundary values, README example flags)

## Status:done queue
- Started: 5
- Verified + closed: 0
- Rejected: 0
- Partial-verify, retained: 5 (no movement from rounds 117/118/119)
- **End of round**: 5 (#786, #788, #807, #840, #843) — all blocked on #863

## Top 3 Risks
1. **v0.3.2 verification stuck at 5 issues — #863 now 4 consecutive rounds.** Either run QA from console session 2 (not RDP/disconnected session 1), or accept unit-test evidence + Ace manual smoke for the 5 remaining issues. No mechanism in place to recover the desktop binding from inside the QA session itself.
2. **Self-hosted runner offline day 60 (#842)** — no Ace response since 2026-05-08. Cloud VM proposal (#860) day 21 unassigned.
3. **First-time-user CLI polish gap.** #867 adds to the rolling set with #864 (`--id` non-uniformity), #865 (JSON-envelope inconsistency), #866 (input cmd exit-code drift). All P2 individually, but a newcomer hits 2–3 of them in their first 15 minutes. Recommend a single "CLI polish" PR before any v0.3.4 marketing push.
