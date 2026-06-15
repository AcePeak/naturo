#!/usr/bin/env bash
# Bootstrap the local multi-agent dev loop on a new machine.
#
# Creates two sibling git worktrees (naturo-dev, naturo-qa) from origin/develop and copies the
# gitignored compiled core DLL into each. Run from the main checkout (on develop, DLL present).
#
# After this, start an orchestrator session and have it register the hourly cron jobs and
# dispatch the Dev/QA cycle agents (see orch-playbook.md).
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
PARENT="$(dirname "$REPO_ROOT")"
DEV_WT="$PARENT/naturo-dev"
QA_WT="$PARENT/naturo-qa"
DLL="naturo/bin/naturo_core.dll"

cd "$REPO_ROOT"
git fetch origin

create_worktree() {
  local path="$1" branch="$2"
  if git worktree list --porcelain | grep -q "^worktree $path$"; then
    echo "worktree already exists: $path"
  else
    git worktree add -b "$branch" "$path" origin/develop
    echo "created worktree: $path ($branch)"
  fi
  # Copy the gitignored DLL into the worktree so the package is runnable.
  if [ -f "$REPO_ROOT/$DLL" ]; then
    mkdir -p "$path/$(dirname "$DLL")"
    cp "$REPO_ROOT/$DLL" "$path/$DLL"
    echo "  DLL copied into $path"
  else
    echo "  WARNING: $DLL not found in main checkout — build/install naturo first."
  fi
}

create_worktree "$DEV_WT" dev-work
create_worktree "$QA_WT" qa-work

echo
echo "Bootstrap complete:"
git worktree list
