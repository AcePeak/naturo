# QA Status
Last updated: 2026-05-28 18:10
Current round: 138
Current milestone: v0.3.2 (28 open, ship-gated by epic #885 + 5 SendInput-blocked status:done from console session)

## This Round
- CI Desktop Tests: skipped (no new code since `70e6591` — only QA-report commits R136/R137 in interval). `.last-ci-sha` reconciled to `ceecfd5`.
- Persona: Enterprise RPA Dev (hour 18 mod 8 = 2)
- Session: NO_DESKTOP_SESSION (NATUROBOT, no interactive desktop bind)
- Issues verified: none (5 status:done all SendInput-blocked from this session — no state change since R137)
- E2E tests: skipped (no desktop)
- Regression: 8/8 testable-from-NO_DESKTOP TCs re-confirmed FAIL on HEAD `ceecfd5` (TC-0054, 0057, 0061, 0062, 0063, 0064, 0067, 0076). All bugs still reproduce.
- Phase 4 (Enterprise RPA Dev): designed multi-step `wait --gone … && click …` workflow gate. Discovered `naturo wait --gone <anything>` silent-success in NO_DESKTOP — returns `success:true exit 0 wait_time:0.0` for a `--timeout 5` request (0.236s actual). The most agent-hostile silent-failure in the cluster yet.
- New issues created: **#893** (P1 v0.3.2, silent-failure — wait --gone bypasses NO_DESKTOP guard)
- Comments added: **#885** (added wait-family row to silent-failure surface matrix), **#884** (added wait-family envelope shape E — no `error` object at all in -j failure mode)
- New test cases created: **TC-0079** (regression/wait-gone-silent-success, source #893)
- Test cases updated: TC-0054, TC-0062, TC-0071 (R138 notes appended)
- Test cases cleaned up: none
- Total active test cases: **58** (+1)
- Tests run: ~25 CLI probes + 8 regression re-verifications + 1 workflow-chain scenario

## Top 3 Risks
1. **`wait --gone` silent success (#893) is the most agent-hostile silent-failure in the cluster so far.** Workflow gate before destructive ops (close-with-unsaved, submit, delete) gets a fabricated green light; `--timeout` is completely ignored (5s requested, 0.236s actual). The README's "Post-Action Verify" claim is indefensible while this exists. Promote #893 alongside #885 — same fix, same ship.
2. **The silent-failure surface is now 6 entrypoints** (`app windows`/`dialog detect`/`taskbar list`/`tray list`/`wait --gone` CLI + `capture_screen`/`list_windows` MCP). All share the per-command guard root cause. The #885 centralized middleware + CI gate is the only structural fix — every new desktop-required command shipped without it grows this matrix.
3. **5 SendInput-blocked status:done remain unverified ~25h** after restructured ship gate (R137 risk #3 unchanged). v0.3.2 cannot ship even with #885 closed unless someone drives the console-session QA run. Escalate to Ace.

## Environment
- Windows 11 Pro 10.0.26200
- naturo 0.3.1 (HEAD `ceecfd5`)
- Runner: NATUROBOT, NO_DESKTOP_SESSION
