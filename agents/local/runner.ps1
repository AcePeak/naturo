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

switch ($Role) {
  'dev'  { $Wt = 'C:\Users\Naturobot\naturo-dev'; $Cycle = 'agents/local/dev-cycle.md' }
  'qa'   { $Wt = 'C:\Users\Naturobot\naturo-qa';  $Cycle = 'agents/local/qa-cycle.md' }
  'orch' { $Wt = $Main;                           $Cycle = 'agents/local/orch-review.md' }
}

function Write-State([string]$line) {
  $stamp = (Get-Date).ToString('o')
  Add-Content -Path $StateLog -Value "$stamp  [runner:$Role]  $line"
}

# --- Overlap guard: skip if a previous cycle for this role is still running ---
$Lock = Join-Path $WorkDir "$Role.lock"
if (Test-Path $Lock) {
  $oldPid = (Get-Content $Lock -ErrorAction SilentlyContinue | Select-Object -First 1)
  if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
    Write-State "SKIP — previous $Role cycle still running (pid $oldPid)"
    exit 0
  }
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
