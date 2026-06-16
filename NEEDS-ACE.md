# NEEDS-ACE — Human-Decision Queue

> The autonomous naturo loop (Dev / QA / Orch) runs unattended and self-closes everything it can.
> This file is the short list of things **only Ace can decide**. Refreshed by the Orchestrator each
> review cycle. Read this first on a check-in. Each item also has a GitHub issue labelled `needs:ace`.

_Last refreshed: 2026-06-16 16:14 (Orc autonomous cycle)._

## Open decisions
| # | Decision | Why it's yours | Orc recommendation |
|---|----------|----------------|--------------------|
| [#842](https://github.com/AcePeak/naturo/issues/842) / [#860](https://github.com/AcePeak/naturo/issues/860) | Desktop CI: self-hosted runner ROBOT-COMPILE offline (#842) vs fund a cloud Windows VM (#860) | infra spend | Decide: revive the runner, fund a cloud Windows VM, or accept GitHub-hosted-only CI (desktop tests stay on the local QA loop, which is currently covering verification). |
| [#914](https://github.com/AcePeak/naturo/issues/914) | v0.3.2 ship-gate sign-off | release / tag to `main` = PyPI publish | **Not actionable yet** — waiting on QA to verify #885 + the 5 `status:done` bugs. When all six flip to `verified`, the gate is clear and cutting v0.3.2 is your call. |
| [#913](https://github.com/AcePeak/naturo/issues/913) | Dispose of community PRs #892 / #904 | external-contributor relationship | #892 is superseded by the merged PR #911 (contributor co-credited) — close it with thanks. Hold #904 open until the team's replacement fix for #844 lands, then close the same way. |

## Ship-gate status — v0.3.2
- (1) Epic **#885** (silent-failure cluster): fix **MERGED** (PR #911, closes #868/#875/#878/#883/#893).
  Now `status:done`, awaiting QA desktop verification before the epic closes.
- (2) QA-verify 5 `status:done` bugs on a real desktop: **#786, #788, #807, #840, #843**.
  These have been `status:done` since **2026-05-27 (~20 days)** — verification has not been picked up
  yet. The local QA loop (QA-Mariana on NATUROBOT) is the path; if it keeps not landing, the desktop
  CI runner decision (#842/#860) is the likely root cause.

## Blocks
- Desktop CI runner **#842** offline (chronic). Local QA loop covers real-desktop verification in the
  meantime, but the 5 ship-gate bugs aging ~20 days suggests it needs attention (see #842/#860).
- `develop` CI: **green** (no block this cycle).

---
_How this works: anything irreversible or human-only is queued here instead of acted on. Everything else
the loop does itself — opens PRs, merges green ones to develop, verifies on the real desktop, closes issues,
files new work. See `agents/local/README.md`._
