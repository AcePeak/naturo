# QA Status
Last updated: 2026-05-29 06:07
Current round: 150
Current milestone: v0.3.2

## This Round
- Persona (hour 06 → index 6): Scripter/Automator
- CI Desktop Tests: skipped (no new source commits since 17aefe6 — all intervening commits are `[skip ci]` QA reports)
- Issues verified: none — 5 status:done (#786/#788/#807/#840/#843) are SendInput/desktop-dependent, un-runtime-verifiable in this no-desktop session (#863)
- E2E tests: BLOCKED — no interactive desktop in this session
- Regression: 5/6 fail (bug-repro TCs still reproduce: TC-0062/0063/0065/0079/0081), 1/6 pass (TC-0088 positive-lock, passes 2→3), 0 retired
- New test cases created: none (no new bug; cluster already covered)
- Test cases cleaned up: none
- New issues created: none (all findings map to open issues; extended #893 with sharper repro)
- Total active test cases: ~70 active
- Tests run: full NO_DESKTOP_SESSION guard matrix (~22 command probes) + 6 regression TCs

## This Round's Findings (all confirmations / extensions on c15be18)
- #885 cluster persists unchanged: app windows (#878), dialog/taskbar/tray (#875), wait --gone (#893) bypass guard; see/capture/list/app list/menu-inspect/find/highlight refuse correctly
- #878 sharpened: intra-`app`-group split (app list refuses, app windows bypasses); both -j and non-json bypass
- #893 sharpened: `wait --gone explorer` = verifiably false negative (explorer.exe named alive in same-session guard msg); --timeout ignored; silent success propagates in workflow chains
- #869 refined: pyvda install prompt is TTY-gated — clean MISSING_DEPENDENCY JSON under piped stdin, not a script-hang

## Top 3 Risks
1. #885 (P0 silent-failure cluster) unstarted and unchanged — source hasn't moved; it's the v0.3.2 ship gate and the worst bug class (agents act on false success:true). Matrix fully specified, waiting on Dev.
2. QA structurally blind from this SSH/service session (#863): 5 status:done fixes unverifiable + Phase 2 impossible. The "verify 5 from a console session" ship-gate step has no scheduled console runner — process gap.
3. Broad envelope/exit-code drift (#872/#876/#879/#884/#895/#897 + guard-bypass exit-0 set) makes scripting hostile; undermines README "AI Agent Ready: JSON output" claim (#887) until cluster lands.
</content>
