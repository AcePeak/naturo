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
each. A runtime state log is kept **outside** the repo (machine-local).

## Two ways to drive the loop

### A. Interactive (you are present)
Start an orchestrator Claude session and have it register session crons (see `orch-playbook.md`).
These fire only while that session is open — good for supervised, hands-on work.

### B. Persistent / unattended (the machine runs the loop on its own)
For self-evolving operation when no one is logged in to babysit a session, drive the cycles with
**Windows Task Scheduler** invoking the headless launcher `runner.ps1`:

```
powershell -ExecutionPolicy Bypass -File agents\local\runner.ps1 -Role dev    # | qa | orch
```

`runner.ps1` runs exactly one bounded `claude -p` cycle for the role inside its worktree, with an
overlap lock and `--dangerously-skip-permissions` (no human is present to approve tool calls; the
safety envelope is `agents/RULES.md` + GitHub branch protection on `main` + worktree isolation + the
hard constraints in each cycle prompt). Suggested schedule: **Dev hourly :07, Orch :22, QA :37**.

**Critical requirement — a live desktop session.** QA performs real UI verification (the whole reason
it runs locally), so the machine must have an **interactive desktop session logged in**. Enable
auto-login (and disable sleep) so the session persists across reboots, then register the tasks to
**"run only when the user is logged on"**. A pure Session-0 "run whether logged on or not" task has no
desktop and would break QA. Keep one session alive; lock the screen if you want privacy.

The headless Orchestrator cycle is `orch-review.md` (autonomous — it acts itself and pushes
human-only decisions to the `needs:ace` queue + top-level `NEEDS-ACE.md`, which Ace reads on a 1–2 day
check-in). `dev-cycle.md` and `qa-cycle.md` are shared by both modes.
