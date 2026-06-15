# Local Multi-Agent Dev Loop

This directory defines a **portable, machine-local** way to run naturo development as a
3-role multi-agent loop, on any Windows desktop with a working naturo install. It is the
local counterpart to the cloud-cron design in `agents/orchestrator/` (which assumes a Linux
agent with no desktop and no GitHub API).

## Roles

| Role | Who | Worktree | Cadence | Task source |
|------|-----|----------|---------|-------------|
| **Orch** | the live agent session (Orc-Mycelium) | main checkout (on `develop`) | interactive | — |
| **Dev** | hourly background agent (Dev-Sirius) | `../naturo-dev` | hourly cron | GitHub Issues (P0→P2) |
| **QA** | hourly background agent (QA-Mariana) | `../naturo-qa` | hourly cron (offset) | GitHub Issues `status:done` |

- **Orch** interacts with the human, dispatches Dev/QA each cron tick, watches CI/PRs, and
  escalates the decisions only the human can make. It does not do dev/qa work itself.
- **Dev** picks one open issue by priority, TDD-fixes it, opens a PR to `develop`, and enables
  auto-merge (squash) so it lands when CI is green.
- **QA** verifies `status:done` issues on the **real desktop** (runtime verification the cloud
  runner cannot do), then labels `verified` + closes, or kicks the issue back to Dev.

Role scripts: [`dev-cycle.md`](dev-cycle.md), [`qa-cycle.md`](qa-cycle.md),
[`orch-playbook.md`](orch-playbook.md). All follow `agents/RULES.md`.

## Conventions (portable across machines)

- The two agent worktrees are **siblings of the main checkout**: if the repo is at
  `.../naturo`, they live at `.../naturo-dev` and `.../naturo-qa`.
- Worktree isolation needs **no virtualenv**: running `python` / `python -m pytest` from
  inside a worktree directory makes that worktree's `naturo/` package win over any editable
  install (cwd precedes site-packages on `sys.path`).
- The compiled core `naturo/bin/naturo_core.dll` is **gitignored**, so it is NOT present in a
  fresh worktree. `bootstrap.sh` copies it from the main checkout into each worktree.
- The orchestrator passes each background agent the **absolute** path of its worktree at
  dispatch time; the scripts themselves use repo-relative language so they stay portable.

## Bootstrap on a new machine

```bash
# from the main checkout (on develop, with the DLL present / naturo installed):
bash agents/local/bootstrap.sh
```

This creates `../naturo-dev` and `../naturo-qa` from `origin/develop` and copies the DLL into
each. Then start an orchestrator session and have it register the hourly cron jobs (see
`orch-playbook.md`). A runtime state log is kept **outside** the repo (machine-local).
