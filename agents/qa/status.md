# QA Status
Last updated: 2026-05-28 22:08
Current round: 142
Current milestone: v0.3.2 (27 open, ship-gated by epic #885 + 5 SendInput-blocked status:done from console session)

## This Round
- CI Desktop Tests: skipped (no source changes since `b7b90ed` — only QA-report `[skip ci]` commit R141 `ca7a9bc` in interval). Reconciling `.last-ci-sha` to `ca7a9bc` on commit.
- Persona: Scripter/Automator (hour 22 mod 8 = 6)
- Session: NO_DESKTOP_SESSION (ROBOT-COMPILE / Naturobot user, SSH session — no interactive desktop bind)
- Issues verified: none (5 status:done all SendInput-blocked from this session — no state change since R141, no fresh comments per Orc-Mycelium "piling on has diminishing value" escalation)
- E2E tests: skipped (no desktop)
- Regression: **9/9 testable-from-NO_DESKTOP TCs re-confirmed FAIL on HEAD `ca7a9bc`** (TC-0054, 0055, 0062, 0065, 0067, 0071, 0079, 0080, 0081)
- Phase 4 (Scripter/Automator): wrote a real Scripter-style dispatcher `case $? in 2) usage_error ;; 1) op_failed ;; esac` and ran it across 9 invocation classes. **Found a contract drift**: missing-required-arg path returns exit **1** for `type/press/find/wait/get/set/app launch` (custom INVALID_INPUT validators), while Click's own argument-validation path returns exit **2** for unknown subcommand / missing flag value / no-subcommand-on-group. A Scripter's standard dispatcher misclassifies `naturo type` (missing TEXT) as `OPERATION_FAILED` and may infinite-retry. Distinct from #866 (NO_DESKTOP runtime axis) — this is the missing-arg axis. Cross-checked JSON pipe-friendliness (stdout-only, stderr-quiet, parseable) — those work as advertised in the cases tested. Filed.
- New issues created: **#897** (P2 v0.3.4 — missing-required-arg exit code drift: `type/press/find/wait/get/set/app launch` exit 1 instead of 2).
- Comments added: none.
- New test cases created: **TC-0083** (exploratory/missing-arg-exit-code-drift, source #897).
- Test cases updated: TC-0054 notes extended with R142 adjacent-finding cross-reference.
- Test cases cleaned up: none.
- Total active test cases: **62** (+1).
- Tests run: 9 regression re-verifications + ~15 Scripter exit-code/JSON pipe probes + 1 new TC drafted + 1 new issue filed.

## Top 3 Risks
1. **Exit-code contract is currently un-script-able.** With #897 (this round, missing-arg axis: custom validator → exit 1) and #866 (existing, NO_DESKTOP runtime axis: input commands → exit 2 text mode / exit 1 -j mode), there is no single exit code a Scripter can use to distinguish "you called me wrong" from "I tried but the desktop is missing". A standard POSIX `case $?` dispatcher misclassifies *both* directions. Combined with the README's "AI Agent Ready" framing, this is a credibility risk for Scripter and Enterprise RPA Dev personas. Both fixes are mechanical (bind exit codes to the right `sys.exit` calls). Together they would close TC-0054 and TC-0083.
2. **#885 epic still unstaffed for 53+ days.** R142 adds another contract-drift finding (#897). The exit-code surface now has 2 filed bugs (#866, #897); the envelope-shape cluster has 15+ (#864–#884, #886, #895, #896). #897 is the first that's purely a *runtime exit code* drift inside naturo's own validators, not a Click/envelope drift. Until a centralized contract test lands as part of #885, persona rounds will continue to peel layers off the same onion.
3. **5 SendInput-blocked `status:done` unverified ~30h** after restructured ship gate. R142 made no progress; only Ace's console-session run or a #863 workaround can move this. v0.3.2 ship gate still locked on `#885 + 5 status:done from console`.

## Environment
- Windows 11 Pro 10.0.26200.8457
- naturo 0.3.1 (HEAD `ca7a9bc`)
- Runner: ROBOT-COMPILE (Naturobot user), NO_DESKTOP_SESSION
