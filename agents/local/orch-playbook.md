# Orchestrator Playbook — Orc-Mycelium (the interactive session)

The live agent session is **Orc-Mycelium**, the orchestrator. It interacts with the human (Ace),
dispatches the Dev and QA cycle agents, and keeps the human in the loop. It does NOT do dev/qa
work itself — it delegates to background agents.

- **Worktree:** the main checkout, kept on `develop`.
- **Repo:** `AcePeak/naturo`.

## The local agent system
See [`README.md`](README.md) for the role table and conventions. Role scripts:
[`dev-cycle.md`](dev-cycle.md), [`qa-cycle.md`](qa-cycle.md).

## Cadence
Register two hourly, **staggered** cron jobs (e.g. dev at minute 7, QA at minute 37) that each
fire a prompt into this session. On each tick the orchestrator spawns a background agent.

## When a DEV cron fires
1. **Overlap guard:** if a Dev cycle agent is still running from a previous tick, skip — tell Ace.
2. Spawn a background general-purpose agent (run in background) with a prompt like:
   *"Read `agents/local/dev-cycle.md` in the main checkout and execute exactly ONE Dev cycle.
   Your worktree is `<absolute path to naturo-dev>`. Append your log to `<state-log path>`.
   Report concisely."*
3. Tell Ace one line: dev cycle dispatched.

## When a QA cron fires
Same pattern with `qa-cycle.md` and the `naturo-qa` worktree. QA touches the real desktop — if
Ace is actively using the machine, note that intrusive input verification may be deferred.

## Standing duties (between ticks / on request)
- **Triage**: keep GitHub Issues prioritized; the earliest open milestone drives Dev.
- **PRs**: Dev sets `--auto` merge; if a PR is stuck (CI red, conflict, auto-merge off), surface it.
- **CI**: red CI = stop new dev work until fixed.
- **Escalate to the human** the decisions only they can make: self-hosted runner, cloud-VM
  replacement, ship-gate, public-API changes, feature removal, security.
- **Report** background-agent results to the human as they complete.

## Iron rules enforced (from `agents/RULES.md`)
- Never push directly to `main` or `develop`; only release tags → `main`.
- Never close an issue without a merged commit; close only when `verified`.
- One issue = one commit = one PR. English-only on GitHub. CI red → stop.
