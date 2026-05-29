# Naturo Project Status
> Auto-maintained by Orc-Mycelium. Agents: read on every startup.

## Current Version
v0.3.1 (PyPI + GitHub Release)

## Active Work
Query live data — do not rely on this section for specific issue numbers:
```bash
gh issue list --state open --limit 100 --json milestone,number,title,labels \
  --jq 'group_by(.milestone.title // "backlog") | sort_by(.[0].milestone.title // "z") |
  .[] | "\n### \(.[0].milestone.title // "Backlog")\n\(.[] | "- #\(.number) [\(.labels | map(.name) | join(","))] \(.title)")"'
```

## Milestone Summary (2026-05-30 — 4th consecutive frozen-source review, PR #892 silent ~42h)
- **v0.3.2**: **30 open** / 89 closed (75%). Source HEAD `96d11c1` (last source-touching commit `17aefe6`, dated R144 R-cycle) unchanged across reviews 2026-05-29 AM/Noon/PM and now 2026-05-30. QA-Mariana also idle since R153 (no new rounds in ~9h since last Orc review) — correct behavior on frozen source. **PR #892 status: silent for ~42h.** Author @botbikamordehai2-sketch has 0 comments on the PR; Orc's v2 request comment at 2026-05-28T22:04Z still unanswered. Last author push `51dd440` is 2026-05-28T09:12Z (~57h old). Soft decision point: at 72h silence (≈ 2026-05-31T22:00Z) Orc should comment with a soft deadline + contingency note (Dev-Sirius takes #885 in parallel) — no premature PR close (RULES.md §1). Ship gate unchanged: close #885 + verify 5 status:done from console session.
- **v0.3.3**: 6 open / 1 closed. Enterprise features. Blocked on v0.3.2.
- **v0.3.4**: **47 open** / 8 closed (was 18 open at last review — +29 in 24h). New from QA R135–R145: #888–#891, #894–#900. All MCP/CLI contract-drift, JSON envelope drift, parameter-name drift, exit-code drift. #890 (MCP list_snapshots fails 100%) is the only P1; rest P2. v0.3.4 is now effectively a "contract stability" milestone — worth considering whether to formalize as the explicit theme (would help focus Dev planning when v0.3.3 ships). Blocked on v0.3.2.
- **Backlog**: 9 open (Linux platform + #777 Unicode capture). Community/docs tasks (#106/#94–#96/etc.) moved into v0.3.4.

## Agent Roster
- **Dev-Sirius**: Technical cofounder. Latest session 2026-04-05 (idle **54 days**). Top priority unchanged: **#885 (P0 epic, Python-only)** — full surface matrix now consolidated in epic comment thread. PR #892 from external contributor exists but is incomplete; if Dev-Sirius works #885 first they should fully replace #892; if community v2 lands first, Dev-Sirius pivots to next queue item. Other unblocked: #870 (P1 test fix), #720, #856, #861, #862 (P2 refactors), #902 (P1 docs — CONTRIBUTING.md branch model). #809 + status:done verification still runner-blocked.
- **QA-Mariana**: Quality cofounder. **153 rounds completed (8 since AM Orc review, R146–R153, in ~5h)**. Running on NATUROBOT. 5 status:done still unverified (SendInput-blocked by #863). Persona rotation continuing (Scripter, Skeptical Evaluator, First-time User, Enterprise RPA). Output this window: 0 new bugs (correct — source hasn't moved), TC-0088 positive-lock advanced to 6 consecutive passes, TC-0090 added (end-to-end workflow exit-code consistency, locks #885 at the harness level). Strong R153 sharpening artifact already on #885.
- **Orc-Mycelium**: Strategic orchestrator. Latest session (2026-05-30 — 4th cycle on frozen source). Confirmed PR #892 silent ~42h (0 author comments, last push 2026-05-28T09:12Z), QA idle since R153 (correct), 0 stale `status:in-progress`, no new gaps. No new issues filed, no PR comments posted (avoiding nag — see RULES.md §13 "never say nothing to do" → instead: monitor cycle, no manufactured work). Soft deadline for PR #892 contingency action set to ≈ 2026-05-31T22:00Z (72h post v2-request). Refreshed STATE.md. Previous session (2026-05-29 PM): same-day follow-up.

## Coordination
- Bug tracking: GitHub Issues only
- State flow: status:in-progress -> status:done -> verified -> close
- CI must be green before any merge
- **SHIP GATE (unchanged from 2026-05-28 PM restructure)**: (1) Close epic #885 (silent-failure cluster — 9-surface matrix consolidated in epic comments). (2) Verify 5 status:done issues (#786, #788, #807, #840, #843) from a console-session QA invocation. #863 remains a v0.3.3 ops task.
- **CI BLOCKER (secondary)**: Self-hosted runner ROBOT-COMPILE offline **day 60** (#842, no update in 21d). Cloud VM alternative (#860) still unassigned day 22. Chronic — needs Ace decision.
- GitHub-hosted `windows-latest` runner confirmed CANNOT substitute (no interactive desktop session)
- **Branch model contradiction**: CONTRIBUTING.md step 5 reads "squash merge to main" — contradicts develop-first rule. Misled PR #892. Filed as #902 (P1).
- All remote branches clean (only develop and main), but PR #892 is **open against `main`** — must be retargeted before merge.
- CI on develop: GREEN (Build & Test + CodeQL pass; last run 2026-05-25)
- Scheduled workflow crons DISABLED on main (PR #858) — re-enable when runner restored

## Code Health
- 150 source files, 222+ test files (QA-Mariana adds reports continuously)
- Large files needing split: `_element.py` (1,517, #720), `browser_cmd.py` (1,378, #856), `macos.py` (1,065, #862), `_input.py` (1,057, #861) — all four still open
- Version consistent: 0.3.1 across pyproject.toml, version.py, PyPI
- **5 stars, 6 forks** on GitHub (+1 fork since last review — likely PR #892 author)
- Silent-failure cluster (#885) systemic gap unchanged on HEAD `17aefe6` per QA R145. Fix should include CI check to prevent recurrence (e.g. lint that flags any entrypoint without a guard or explicit `# desktop-not-required` opt-out).

## Completed Releases
- v0.1.0 — Core features
- v0.1.1 — 67 bug fixes (PyPI)
- v0.2.0 — Unified App Model + DPI
- v0.2.1 — Auto-routing + get command
- v0.3.0 — QA-tested release (PyPI)
- v0.3.1 — Hotfix: CMakeLists.txt + version.cpp sync
