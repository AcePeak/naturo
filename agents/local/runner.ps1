<#
.SYNOPSIS
  Headless launcher for the naturo local multi-agent loop (unattended, persistent).

.DESCRIPTION
  Runs exactly ONE bounded agent cycle for a role (dev | qa | orch) by invoking a
  headless `claude -p` session inside that role's git worktree. Designed to be driven by
  Windows Task Scheduler so the loop runs whenever a desktop session is logged in — no
  interactive Claude session required.

  - dev  -> ../naturo-dev,  reads agents/local/dev-cycle.md
  - qa   -> ../naturo-qa,   reads agents/local/qa-cycle.md   (needs the real desktop)
  - orch -> main checkout,  reads agents/local/orch-review.md (autonomous review)

  Guardrails for unattended operation come from agents/RULES.md, GitHub branch protection
  (main is locked), worktree isolation, and the hard constraints baked into each cycle
  prompt. `--dangerously-skip-permissions` is required because there is no human present to
  approve tool calls; the cycle prompts must therefore never push to main, never exceed the
  token budget, and escalate anything irreversible to the needs:ace queue instead of acting.

.PARAMETER Role
  One of: dev, qa, orch.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File agents\local\runner.ps1 -Role dev
#>
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('dev', 'qa', 'orch')]
  [string]$Role
)

$ErrorActionPreference = 'Stop'

# --- Fixed machine-local paths (siblings of the main checkout; state lives outside the repo) ---
$Main     = 'C:\Users\Naturobot\naturo'
$StateLog = 'C:\Users\Naturobot\naturo-loop-state.log'
$WorkDir  = 'C:\Users\Naturobot\naturo-loop-locks'
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

# QA re-enabled 2026-06-17 with Ace's explicit authorization, after the live-injection-test gate was MET:
#   1. CULPRIT fixed at the SOURCE — tests/QA_AGENT.md 第七轮 (the standing-playbook origin, added 2026-03-21
#      in 2006314) is now locked to argv/pytest-level only, NEVER reproduced via live `naturo type` (7a10b18);
#      all three hardcoded dangerous payloads (QA_AGENT.md / R-SEC-012 / test_recording_cli.py) neutralized;
#      every on-disk worktree copy reset so no `rm -rf /` remains anywhere.
#   2. CODE BACKSTOP verified end-to-end — with the guard armed (the qa arm below), `naturo type` refuses
#      every command-like payload (9/9 blocked incl. `$(echo INJECTED)` → UNSAFE_INPUT_BLOCKED, nothing typed)
#      and passes benign content (QA_PROBE etc.). So even if the agent attempts dangerous live input, no
#      keystroke is emitted. Verified via .work/verify_input_guard.py + a live CLI `naturo type` refusal.
# Re-disabling needs Ace's explicit authorization again (the classifier blocks the agent from self-re-enabling).

function Write-State([string]$line) {
  $stamp = (Get-Date).ToString('o')
  Add-Content -Path $StateLog -Value "$stamp  [runner:$Role]  $line"
}

switch ($Role) {
  'dev'  { $Wt = 'C:\Users\Naturobot\naturo-dev'; $Cycle = 'agents/local/dev-cycle.md' }
  'qa'   {
    $Wt = 'C:\Users\Naturobot\naturo-qa';  $Cycle = 'agents/local/qa-cycle.md'
    # (#960) code-enforced input-content guard for the unattended QA loop. Two
    # independent signals activate it so it survives env-inheritance gaps (#972):
    #   1. the env var (inherited by direct children of this process), and
    #   2. a sentinel lock file under ~/.naturo, which every `naturo` invocation
    #      probes regardless of how it was spawned.
    $env:NATURO_SAFE_INPUT = '1'
    $SafeInputLock = Join-Path $env:USERPROFILE '.naturo\safe-input.lock'
    New-Item -ItemType File -Force -Path $SafeInputLock | Out-Null
    Write-State "input-safety guard armed (NATURO_SAFE_INPUT=1 + sentinel $SafeInputLock)"
  }
  'orch' { $Wt = $Main;                           $Cycle = 'agents/local/orch-review.md' }
}

# --- Proxy: the cycle needs the internet (Claude API + GitHub). The interactive `pon` is a cmd
# doskey and does not exist in a scheduled-task PowerShell, so route through the local Clash-style
# proxy directly if one is listening. Auto-detected, so this stays portable on machines without it. ---
$ProxyPort = 7890
if (Get-NetTCPConnection -LocalPort $ProxyPort -State Listen -ErrorAction SilentlyContinue) {
  $env:HTTP_PROXY  = "http://127.0.0.1:$ProxyPort"
  $env:HTTPS_PROXY = "http://127.0.0.1:$ProxyPort"
  $env:ALL_PROXY   = "socks5://127.0.0.1:$ProxyPort"
  Write-State "proxy on 127.0.0.1:$ProxyPort -> routing claude/gh through it (git uses its own global http.proxy)"
} else {
  Write-State "WARNING: no proxy listening on 127.0.0.1:$ProxyPort — if this network needs it, the cycle may fail to reach the Claude API / GitHub"
}

# --- Watchdog + overlap guard ---------------------------------------------------------------------
# A healthy in-flight cycle => skip (don't double-run). But a cycle that is still "alive" yet has run
# PAST the max cycle time is HUNG (e.g. a subprocess like `cmd /c ver` that never returns, #1204, or a
# wedged claude/pytest) — the old guard would then skip this role FOREVER, silently freezing it. So:
# reclaim a hung cycle by killing its whole process tree, and reclaim a stale (dead-pid) lock. This is
# the loop's self-recovery from a wedged cycle (part of #917). Age comes from the lock file's mtime.
$MaxCycleMin = 25                                  # cadence is 30m; a cycle older than this is wedged
$Lock = Join-Path $WorkDir "$Role.lock"
if (Test-Path $Lock) {
  $oldPid = (Get-Content $Lock -ErrorAction SilentlyContinue | Select-Object -First 1)
  $alive  = $oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)
  $ageMin = [int]((Get-Date) - (Get-Item $Lock).LastWriteTime).TotalMinutes
  if ($alive -and $ageMin -lt $MaxCycleMin) {
    Write-State "SKIP — previous $Role cycle still running (pid $oldPid, age ${ageMin}m)"
    exit 0
  }
  if ($alive) {
    Write-State "WATCHDOG — $Role cycle HUNG (pid $oldPid, age ${ageMin}m > ${MaxCycleMin}m): killing process tree + reclaiming"
    & taskkill.exe /PID $oldPid /T /F 2>&1 | Out-Null   # /T kills the wedged child subprocess too
    Start-Sleep -Seconds 2
  } else {
    Write-State "stale lock for $Role (pid $oldPid not running) — reclaiming"
  }
  Remove-Item $Lock -ErrorAction SilentlyContinue
}
$PID | Out-File -FilePath $Lock -Encoding ascii

$bootstrap = @"
Read $Cycle in the main checkout at $Main and execute exactly ONE autonomous $Role cycle, following it and agents/RULES.md strictly. Your worktree is $Wt — operate only there (orch operates in the main checkout). This is an UNATTENDED, headless run: no human is watching, so act fully within the guardrails, NEVER push to main, stop new work if develop CI is red, stay within the token budget, and for anything irreversible or human-only (infra spend, public-API change, security, ship-gate sign-off, ambiguous product direction, taking over/closing a community PR) do NOT act — instead record it in the needs:ace queue. Append a concise cycle log block to $StateLog. End with a one-line summary.
"@

Push-Location $Wt
try {
  Write-State "cycle START (worktree $Wt, prompt $Cycle)"
  $out = Join-Path $WorkDir "$Role-last.out"
  & claude -p $bootstrap --dangerously-skip-permissions --add-dir $Main --add-dir $Wt *>&1 |
    Tee-Object -FilePath $out | Out-Null
  Write-State "cycle END (exit $LASTEXITCODE, transcript $out)"
}
catch {
  Write-State "cycle ERROR — $($_.Exception.Message)"
  throw
}
finally {
  Pop-Location
  Remove-Item $Lock -ErrorAction SilentlyContinue
}
