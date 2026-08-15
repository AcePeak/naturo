# PR Requests Queue

Dev-Sirius writes PR requests here when GitHub tools are unavailable.
Orc-Mycelium processes them and creates the actual PRs.

Format:
```
## PR Request: <branch-name>
- **Base**: develop
- **Title**: <type>: <description> (fixes #N)
- **Body**: <what changed, how tested>
- **Auto-merge**: yes
- **Date**: YYYY-MM-DD
- **Status**: pending | created (PR #X) | conflict
```

---

> Queue cleared by Orc-Mycelium on 2026-05-13. All Dev-Sirius PR requests from
> 2026-04-05 are merged as PRs #845–#855 (and #838). No pending requests.
> Dev-Sirius idle since 2026-04-05 (38 days). Awaiting either runner restoration
> (#842) or Ace authorization to ship a partial v0.3.2.

---

> **STALE-QUEUE NOTICE — Orc-Mycelium, 2026-07-24.** This queue has been empty since
> 2026-05-13 (~2 months). `session-log.md`'s "next session should" list still references
> 2026-04-05 work. Dev-Sirius has produced **zero product code since 2026-07-02** — its
> last 14 commits are runner/GOAL bookkeeping only. Phase 0.5 of the Orc runbook processes
> this dead queue every cycle. Do not read the entries above as a live backlog; the real
> backlog is GitHub issues (102 open). Root cause of the idle producer: #1168.
