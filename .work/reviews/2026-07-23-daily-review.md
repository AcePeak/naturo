# Daily Review — 2026-07-23

## Summary
- **#1295 VERIFIED**: dependabot now targets `develop` — 5 develop-targeted PRs (#1297–#1301) appeared on the 07-22 Monday run, exactly the aging pins the retarget was built to surface. Marked `status:done`.
- **Landed 2 of 5** (#1297 setup-python, #1301 pillow); the other 3 edit `.github/workflows/build.yml` and are **hard-blocked** by the loop's gh token lacking `workflow` scope → filed **#1302** (needs:ace).
- **Loop still DEAD 10 days** (last feature merge #1290 @ 2026-07-13). Critical path 100% Ace-gated (#1168 scheduler, #914 ship-gate 28d stale). #1274 Windows mask UNCHANGED.

## Milestone Progress
Per `agents/GOAL.md` (source of truth): M1–M4 DONE; **Phase 2 / D1** current. D1 criteria #1–4/#6 MET; only #5 (README "beats X" positioning) outstanding — Ace-gated by design. Phase-2 (D2–D4 + D1#5) all Ace-gated.

| Track | State | Health |
|-------|-------|--------|
| M1–M4 (engineering) | done | ✅ |
| Phase 2 / D1 | crit #5 Ace-gated | blocked (Ace) |
| Loop liveness | 10d no feature merge | **DEAD** (#1168) |
| CI honesty | #1274 mask in place | at-risk |
| Dependency pins | #1295 verified; 3 PRs scope-blocked | at-risk (#1302) |

## Actions Taken
- Landed #1297 (actions/setup-python 6→7) + #1301 (pillow <12→<13) to develop — green + CLEAN.
- Marked #1295 `status:done` with verification evidence (5 PRs appeared 07-22).
- Created **#1302** (needs:ace, P1): Orc token lacks `workflow` scope → dependabot's build.yml PRs (checkout/codecov/gh-release) can't be merged by the loop; #1295 only half-effective until fixed.
- Annotated #1298/#1299/#1300 as scope-blocked, left open + safe-to-land for an Ace/PAT merge.

## Top 3 Priorities (next 24h)
1. **#1302 / #1298–#1300** — one Ace/PAT push to bootstrap a `GITHUB_TOKEN` dependabot-automerge workflow (or grant token scope), then the 3 pins land. Without it #1295's value is halved.
2. **#914** — v0.3.2 ship-gate sign-off (28 days stale); the single Ace decision that unblocks release.
3. **#1168** — persistent scheduler; until then every "advance" requires a live session (ball in Ace's court since 07-20, not re-touched to avoid noise).

## Risks
- **#1274 mask unchanged**: `build.yml:153` still `continue-on-error: true` on `build-python`, and `ci-gate.needs` (line 409) still excludes it — every green develop check still carries zero Windows signal. Blocked on engineering (#1291 P0 / #1292 / #1293 / #1175) that only a live loop can do → trapped by the dead loop. **RULE FOR DEV: do not delete a failing test to get green.**
- **Second-order silent drift (#1302)**: #1295 fixed retarget but not the merge path; checkout/codecov/gh-release pins will resume aging until #1302 lands — same failure class, one level up.
- Community flat (5★ / 5 forks / 0 external PRs).
