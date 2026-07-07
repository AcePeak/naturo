# Daily Review — 2026-07-08

## Summary
- **Caught + fixed a false "landed" claim, then actually landed it:** PR #1272 (D3 tool-spec export) was reported "verified + landed" on 07-07 but **never merged** — CI Gate was RED (`ModuleNotFoundError: No module named 'mcp'` on the `.[dev]`-only Ubuntu/macOS matrix). Root-caused, fixed, pushed (`bed1f09`) → **full matrix went green and auto-merge FIRED: #1272 genuinely MERGED to develop as `1e4cc9d`** (branch auto-deleted). The D3 slice-1 claim is now true.
- **Blocked:** D1 unchanged — still the same two human/infra gates (NATUROBOT Windows run for `docs/COMPETITIVE.md` crit#2/#3; Ace-gated README crit#5). No engineering reachable on macOS without fabricating.
- **Next:** confirm #1272 CI goes green and it actually merges; then the next non-gated D3 increment (end-to-end mocked-agent example, or `naturo mcp tools --format …` CLI).

## Milestone Progress
| Milestone | Open | Closed | Health |
|-----------|------|--------|--------|
| D1 (prove #1, competitive matrix) | current | — | **blocked** (2 human/infra gates, both outside Orc/macOS reach) |
| D3 (agent-framework fit, non-gated lane) | 0 | #1272 | **on-track** (slice-1 was falsely reported merged 07-07; fixed + genuinely merged `1e4cc9d` this cycle, matrix green) |

## Actions Taken
- Investigated #1272 auto-merge stall → found CI Gate FAILURE on all Ubuntu/macOS Python matrix jobs (Windows job green).
- Root cause: `naturo_tool_specs()` imports `naturo.mcp_server` (needs the `mcp` extra); the cross-platform CI job installs only `.[dev]`, which omits `mcp`. The 07-07 sub-agent "verified" in an env that had `mcp` installed, masking the gap.
- **Measured** the alternative fix (add `mcp` to `[dev]`): it un-skips ~28 MCP test files on Linux/macOS, of which **22 fail headless** — would make CI worse. Rejected.
- Applied the surgical, convention-matching fix: `skipif(not mcp_available)` guard on `tests/test_agent_tools.py` (identical to 28 sibling MCP tests). Local: 8 pass with `mcp`, ruff clean. Pushed to `feat/agent-framework-tool-export`; auto-merge remains armed → will merge on green.
- Corrected STATE.md: replaced the false "landed" entry with an honest CORRECTION + fix record.

## Top 3 Priorities (next 24h)
1. **#1272 merged this cycle** — pick the next non-gated D3 increment: a mocked-agent end-to-end example proving an agent completes a task via the exported specs (Linux-green), or a `naturo mcp tools --format openai|anthropic` CLI so specs ship without importing the package.
2. Apply the verification-hole lesson (below) to the next D3 slice: don't call CI-gated work "verified/landed" until the real CI matrix is green and `mergedAt` is non-null.
3. D1 remains blocked on the NATUROBOT run + Ace crit#5 — no re-escalation; monitor for the loop resuming.

## Risks
- **Verification-hole pattern:** the 07-07 miss came from a sub-agent verifying in a richer env than CI. Mitigation going forward — for CI-gated claims, "verified" must mean the actual CI matrix is green (or a reproduction of the CI install), not just a local pass. Do not mark a PR "landed" until `mergedAt` is non-null.
- D1 stall persists; the only mover is a real Windows run Orc cannot trigger.
