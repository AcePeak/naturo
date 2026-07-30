<#
.SYNOPSIS
  Stand up an on-demand, ELEVATED winget install/uninstall worker for the naturo
  software-support program. RUN THIS YOURSELF (Ace), once, from an elevated shell.

.DESCRIPTION
  The software-support session (docs/software_support/) must install and uninstall
  ~100 desktop apps to test naturo against them. That needs Administrator elevation,
  which a headless, non-interactive agent session cannot obtain (there is no UAC
  prompt to answer). The `Naturobot` account IS a local Administrator (its token is
  merely UAC-filtered), so this registers a Scheduled Task that runs a small worker
  with the account's FULL (elevated) token — the standard headless-elevation pattern,
  mirroring install-tasks.ps1 in this same folder.

  The agent then requests an install/uninstall by dropping a small JSON file into a
  queue directory; the elevated worker performs it and writes a result file back.

  ─────────────────────────────────────────────────────────────────────────────
  SECURITY MODEL — read before running:
    * The worker runs ELEVATED and takes work from a queue directory the
      (non-elevated) agent can write to. To keep that from being an arbitrary
      local-privilege-escalation channel, the worker NEVER executes shell strings.
      It only ever runs, with ARRAY arguments (no shell parsing), exactly one of:
          winget install   --id <ID> [--version <VER>] --exact --silent
                            --accept-package-agreements --accept-source-agreements
          winget uninstall --id <ID> --exact --silent
          winget list      --id <ID> --exact
    * ACTION is restricted to install | uninstall | list.
    * ID and VERSION are validated against a strict charset BEFORE use; anything
      that fails validation is rejected and logged, never executed.
    * So the worst a queue writer can do is install/uninstall a winget package —
      it cannot run code of its own choosing.
    * Every action is appended to worker.log with a timestamp for your audit.
    * Tear the whole channel down at any time:
          powershell -ExecutionPolicy Bypass -File <thisfile> -Uninstall

  Opening an elevated channel is a deliberate security decision, which is why an
  in-session agent is (correctly) blocked from doing it and you run this yourself.
  ─────────────────────────────────────────────────────────────────────────────

  Agent-side contract:
    request : write   %USERPROFILE%\.naturo-installer\queue\<nonce>.json
              content { "action":"install|uninstall|list", "id":"<winget-id>",
                        "version":"<optional>" }
    result  : appears %USERPROFILE%\.naturo-installer\results\<nonce>.json
              content { ok, exit, action, id, version, output, ts }
    health  : %USERPROFILE%\.naturo-installer\heartbeat.txt (worker updates each loop)

.EXAMPLE
  # Ace, from an elevated PowerShell:
  powershell -ExecutionPolicy Bypass -File agents\local\software-support-installer.ps1
  # remove later:
  powershell -ExecutionPolicy Bypass -File agents\local\software-support-installer.ps1 -Uninstall
#>
param(
  [switch]$Uninstall,
  [System.Security.SecureString]$Password
)

$ErrorActionPreference = 'Stop'
$TaskName  = 'Naturo-SoftwareInstaller'
$Base      = Join-Path $env:USERPROFILE '.naturo-installer'
$Queue     = Join-Path $Base 'queue'
$Results   = Join-Path $Base 'results'
$WorkerPs  = Join-Path $Base 'worker.ps1'
$uid       = "$env:COMPUTERNAME\$env:USERNAME"

if ($Uninstall) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Output "removed scheduled task $TaskName"
  Write-Output "queue/results/logs left under $Base for audit (delete manually if desired)"
  return
}

# --- require elevation (this is the whole point) ---
$principalCheck = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principalCheck.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
  throw "Run this from an ELEVATED PowerShell (Run as administrator). Current token is not elevated."
}

New-Item -ItemType Directory -Force -Path $Base, $Queue, $Results | Out-Null

# --- the worker: written to a STABLE location so it does not depend on any git worktree ---
$worker = @'
$ErrorActionPreference = 'Continue'
$Base      = Join-Path $env:USERPROFILE '.naturo-installer'
$Queue     = Join-Path $Base 'queue'
$Results   = Join-Path $Base 'results'
$LogFile   = Join-Path $Base 'worker.log'
$Heartbeat = Join-Path $Base 'heartbeat.txt'
$IdRe  = '^[A-Za-z0-9][A-Za-z0-9._+-]{0,80}$'
$VerRe = '^[A-Za-z0-9][A-Za-z0-9._-]{0,40}$'

function Log($m) { $ts = (Get-Date).ToString('s'); "$ts  $m" | Out-File -Append -Encoding utf8 $LogFile }
function Find-Winget {
  $c = Get-Command winget.exe -ErrorAction SilentlyContinue
  if ($c) { return $c.Source }
  $p = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WindowsApps\winget.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($p) { return $p.FullName }
  return $null
}

$amAdmin = (New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
"elevated=$amAdmin pid=$PID ts=$((Get-Date).ToString('s'))" | Out-File -Encoding utf8 (Join-Path $Base 'elevated.txt')
Log "worker start (pid=$PID) elevated=$amAdmin"
while ($true) {
  try { (Get-Date).ToString('s') | Out-File -Encoding utf8 $Heartbeat } catch {}
  $reqs = Get-ChildItem -Path $Queue -Filter *.json -File -ErrorAction SilentlyContinue | Sort-Object Name
  foreach ($r in $reqs) {
    $resPath = Join-Path $Results ($r.BaseName + '.json')
    $out = $null
    try {
      $req = Get-Content -Raw -LiteralPath $r.FullName | ConvertFrom-Json
    } catch {
      Log "bad json $($r.Name): $_"
      Move-Item -LiteralPath $r.FullName "$($r.FullName).bad" -Force -ErrorAction SilentlyContinue
      continue
    }
    $action = [string]$req.action; $id = [string]$req.id; $ver = [string]$req.version
    if ($action -notin @('install','uninstall','list')) {
      $out = @{ ok = $false; error = "rejected: bad action '$action'" }
    } elseif ($id -notmatch $IdRe) {
      $out = @{ ok = $false; error = "rejected: bad id '$id'" }
    } elseif ($ver -and ($ver -notmatch $VerRe)) {
      $out = @{ ok = $false; error = "rejected: bad version '$ver'" }
    } else {
      $wg = Find-Winget
      if (-not $wg) {
        $out = @{ ok = $false; error = 'winget not found' }
      } else {
        if ($action -eq 'install') {
          $wargs = @('install','--id',$id,'--exact','--silent','--accept-package-agreements','--accept-source-agreements','--disable-interactivity')
          if ($ver) { $wargs += @('--version',$ver) }
        } elseif ($action -eq 'uninstall') {
          $wargs = @('uninstall','--id',$id,'--exact','--silent','--disable-interactivity')
        } else {
          $wargs = @('list','--id',$id,'--exact','--accept-source-agreements')
        }
        Log "run: winget $($wargs -join ' ')"
        $stdout = & $wg @wargs 2>&1 | Out-String
        $code = $LASTEXITCODE
        $tail = if ($stdout.Length -gt 4000) { $stdout.Substring($stdout.Length - 4000) } else { $stdout }
        $out = @{ ok = ($code -eq 0); exit = $code; action = $action; id = $id; version = $ver; output = $tail }
        Log "done: id=$id action=$action exit=$code"
      }
    }
    $out.ts = (Get-Date).ToString('s')
    try { ($out | ConvertTo-Json -Depth 5) | Out-File -Encoding utf8 -LiteralPath $resPath } catch { Log "write result failed: $_" }
    Remove-Item -LiteralPath $r.FullName -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep -Seconds 3
}
'@
Set-Content -LiteralPath $WorkerPs -Value $worker -Encoding utf8
Write-Output "wrote worker    -> $WorkerPs"

# --- register the elevated worker as a scheduled task ---
$action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
            -Argument "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$WorkerPs`""
# On this headless box UAC is on and an Interactive+Highest task inherits the SSH logon
# session's UAC-FILTERED (non-elevated) token, so the worker was not actually elevated.
# Running "whether logged on or not" (LogonType Password) with -RunLevel Highest gives the
# task its OWN session with the account's FULL, elevated token — independent of any SSH login.
if (-not $Password) {
  $Password = Read-Host -AsSecureString "Windows password for $uid (so the worker runs elevated whether logged on or not)"
}
$pwPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
             [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password))
# AtStartup keeps it alive across reboots without needing a logon; the -Once repetition is an
# immediate start + watchdog that restarts the loop if it ever dies (IgnoreNew = never duplicated).
$tStart  = New-ScheduledTaskTrigger -AtStartup
$tRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date) `
            -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::FromDays(3650))
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
            -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $tStart,$tRepeat `
  -Settings $settings -User $uid -Password $pwPlain -RunLevel Highest -Force | Out-Null
$pwPlain = $null
Write-Output "registered task -> $TaskName (elevated worker, run whether logged on or not, RunLevel Highest)"

Stop-ScheduledTask  -TaskName $TaskName -ErrorAction SilentlyContinue
Start-ScheduledTask -TaskName $TaskName
Write-Output ""
Write-Output "Done. The elevated install worker is live."
Write-Output "  queue : $Queue"
Write-Output "  results: $Results"
Write-Output "  log    : $(Join-Path $Base 'worker.log')"
Write-Output "Verify:   Get-ScheduledTask $TaskName | Select TaskName,State"
Write-Output "Smoke:    '{""action"":""list"",""id"":""7zip.7zip""}' | Set-Content $Queue\smoke.json -Encoding utf8 ; then check $Results\smoke.json"
Write-Output "Remove:   powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Uninstall"
