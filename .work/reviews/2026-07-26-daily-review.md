# Daily Review — 2026-07-26

## Summary
- ACTION, not report: root-caused #1292 as a real **develop-side regression** and landed the fix (PR #1304, auto-merge on).
- Last cycle's #1303 (#1291 P0 fix) is now **CI-green + merged** to develop (c477e7e) — confirmed landed.
- Uncovered a structural fact: **develop has dropped MCP tools that still ship in v0.3.2 on `main`** — develop regressed the surface agents consume.

## What happened
- **#1303 confirmed landed** — the type_text/press_key silent-foreground-fallback P0 fix merged 07-25, CI green.
- **#1292 (MCP surface drift, P1) — root-caused + fixed.** First verification pass wrongly reported "already fixed" because `isolation:worktree` cut the agent's tree from `origin/HEAD` = **main**, where these tools were never dropped. Verified against the wrong branch (sibling of #969). Corrected by pinning the fix to a develop-based worktree.
  - Truth: `_snapshot.py` + all 5 registrations (`app_hide`/`app_unhide`/`hotkey`/`get_snapshot`/`list_snapshots`) existed at the develop↔main fork point (2026-03-31) and remain on main/shipped v0.3.2. develop **dropped them** in an MCP module refactor within its 965 post-fork commits. The 9 main-only commits are all chore/dependabot — none touch MCP.
  - Fix (PR #1304): re-register on develop's surface (`_window.py`, `_input.py`, new `_snapshot.py` wired into `create_server()`), regenerate `packaging/mcpb/manifest.json` (63→68). Targeted 215-test gate green, ruff clean, 10 remaining mcp/surface failures confirmed pre-existing on base. Auto-merge (squash) enabled — NOT declared landed until merged.

## Branch-divergence finding (surfaced, Ace-gated)
- `develop` and `main` forked 2026-03-31; develop = 965 commits ahead, main = 9 (all chore/release). Both are version 0.3.2.
- **main is the release line and carries MCP tools develop lacks.** #1292 is the first proven user-facing regression from this drift; there may be more in #1273's 63-failure set. develop is not being kept in parity with what actually shipped.

## Milestone Progress
| Line | State | Health |
|------|-------|--------|
| develop feature loop | last real feature #1290 (07-13); 2 Orc P0/P1 fixes landed 07-25/07-26 | DEAD for autonomous feature work; Orc landing regressions manually |
| needs:ace queue | 9 open | critical path Ace-gated (#914 ship-gate, #915/#917 QA-loop-down, #1168 scheduler, #1302 workflow-scope) |

## Actions Taken
- Confirmed #1303 merged + CI-green.
- Created PR #1304 (fixes #1292); enabled auto-merge; commented root-cause + labeled #1292 status:done.
- Recorded the `isolation:worktree`-cuts-from-main verification hazard (memory) to stop the trap recurring.

## Top 3 Priorities (next 24h)
1. Land PR #1304 (watch develop CI → merge).
2. Audit whether more of #1273's 63 develop failures are the same develop-vs-main regression pattern (dropped-on-develop capabilities).
3. Ace-gated wall unchanged: #915/#917 (QA loop 403-dead ~5d), #1168 (no persistent scheduler), #1302 (workflow-scope) — no new escalation (noise avoidance).

## Risks
- develop↔main MCP divergence means develop CI red masks real regressions vs the shipped surface; #1274 (make Windows job blocking) is the fix but is Ace-gated by #1302 (workflow scope).
- `isolation:worktree` silently bases on main, not the session branch — any future verify-in-worktree can validate stale code. Mitigation: pin fixes to an explicit develop-based worktree; documented in memory.
