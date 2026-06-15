# NEEDS-ACE — Human-Decision Queue

> The autonomous naturo loop (Dev / QA / Orch) runs unattended and self-closes everything it can.
> This file is the short list of things **only Ace can decide**. Refreshed by the Orchestrator each
> review cycle. Read this first on a check-in. Each item also has a GitHub issue labelled `needs:ace`.

_Last refreshed: 2026-06-15 (initial — loop just went autonomous)._

## Open decisions
| # | Decision | Why it's yours | Orc recommendation |
|---|----------|----------------|--------------------|
| — | _Self-hosted desktop CI runner (#842) offline / cloud-VM (#860) unassigned_ | infra spend | Decide: revive runner, fund a cloud Windows VM, or accept GitHub-hosted-only CI (desktop tests stay on the local QA loop). |
| — | _v0.3.2 ship-gate sign-off_ | release / tag to `main` = PyPI publish | #885 fix is now MERGED (PR #911). Once QA verifies it + the 5 `status:done` issues on the real desktop, the gate is clear — your call to cut the release. |
| — | _Community PRs #892 / #904 disposition_ | external-contributor relationship | Team completed #885 via the merged PR #911 (credited the contributor). Close #892 (and #904 once its fix lands) with thanks — confirm you're OK with that. |

## Ship-gate status
- **v0.3.2 gate:** (1) epic **#885** — fix **MERGED** (PR #911, closes #868/#875/#878/#883/#893); now
  awaiting QA desktop verification before close. (2) QA-verify 5 `status:done` (#786, #788, #807, #840, #843)
  on a real desktop session.

## Blocks
- Desktop CI runner #842 offline (chronic). Local QA loop covers real-desktop verification in the meantime.

---
_How this works: anything irreversible or human-only is queued here instead of acted on. Everything else
the loop does itself — opens PRs, merges green ones to develop, verifies on the real desktop, closes issues,
files new work. See `agents/local/README.md`._
