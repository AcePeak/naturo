<#
.SYNOPSIS
  Register the naturo unattended loop as Windows Scheduled Tasks. RUN THIS YOURSELF (Ace).

.DESCRIPTION
  Creates three hourly, staggered tasks that drive the local multi-agent loop headlessly via
  agents/local/runner.ps1 — Dev (:07), Orch (:22), QA (:37). Each runs as the current user,
  "only when logged on" (so QA has a real desktop), and won't start a new instance while the
  previous one is still running.

  This must be run by you, not by an in-session agent: standing up an unattended loop that calls
  `claude -p --dangerously-skip-permissions` is a deliberate security decision the agent is
  correctly blocked from making on its own. Review runner.ps1 + the cycle prompts first.

  Prerequisites:
    - bootstrap.sh has been run (../naturo-dev and ../naturo-qa exist with the DLL copied)
    - `claude` and `gh` are on PATH and authenticated for the current user
    - Auto-login is enabled and sleep disabled, so a desktop session is always present
      (Task Scheduler "run only when logged on" needs it; QA needs the desktop)

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File agents\local\install-tasks.ps1
  # remove later:
  powershell -ExecutionPolicy Bypass -File agents\local\install-tasks.ps1 -Uninstall
#>
param([switch]$Uninstall)

$ErrorActionPreference = 'Stop'
$runner = Join-Path $PSScriptRoot 'runner.ps1'
$uid    = "$env:COMPUTERNAME\$env:USERNAME"
$jobs = @(
  @{ Name = 'Naturo-Dev';  Role = 'dev';  At = '00:07' },
  @{ Name = 'Naturo-Orch'; Role = 'orch'; At = '00:22' },
  @{ Name = 'Naturo-QA';   Role = 'qa';   At = '00:37' }
)

if ($Uninstall) {
  foreach ($j in $jobs) {
    Unregister-ScheduledTask -TaskName $j.Name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "removed $($j.Name)"
  }
  return
}

if (-not (Test-Path $runner)) { throw "runner.ps1 not found at $runner" }

foreach ($j in $jobs) {
  $action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
              -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$runner`" -Role $($j.Role)"
  $trigger = New-ScheduledTaskTrigger -Once -At $j.At -RepetitionInterval (New-TimeSpan -Hours 1)
  $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
              -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
              -ExecutionTimeLimit (New-TimeSpan -Minutes 50)
  # Interactive = run only when the user is logged on (QA needs a real desktop session).
  $principal = New-ScheduledTaskPrincipal -UserId $uid -LogonType Interactive -RunLevel Limited
  Register-ScheduledTask -TaskName $j.Name -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null
  Write-Output "registered $($j.Name)  (role=$($j.Role), hourly at :$($j.At.Substring(3)))"
}
Write-Output ''
Write-Output 'Done. Verify:  Get-ScheduledTask Naturo-* | Select TaskName,State'
Write-Output 'Run one now:   Start-ScheduledTask Naturo-Orch    (watch C:\Users\Naturobot\naturo-loop-state.log)'
