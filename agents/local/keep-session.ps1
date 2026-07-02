<#
.SYNOPSIS
  Keep the interactive desktop session ACTIVE after you disconnect mstsc/RDP, so the QA loop
  keeps working. RUN THIS YOURSELF (Ace), elevated.

.DESCRIPTION
  On Windows client, disconnecting an RDP session leaves it *disconnected + locked* — no rendered
  desktop — which breaks UI automation (capture goes black, click/type don't reach windows). This
  is the same NO_DESKTOP_SESSION class the project tests (#863/#868/#885).

  The fix is to redirect your RDP session to the physical **console** session, where it stays
  ACTIVE (unlocked) even after RDP disconnects and with no monitor attached.

  Default (manual): run this right before you leave. Your mstsc window drops immediately, but the
  session lives on the console and the loop keeps running. Reconnect with mstsc anytime to take it
  back. Requires administrator (auto-elevates).

  Optional (-InstallAuto): register a SYSTEM scheduled task that fires on every RDP *disconnect*
  event and runs the same redirect automatically, so you can just close mstsc. Remove with -Uninstall.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File agents\local\keep-session.ps1
  powershell -ExecutionPolicy Bypass -File agents\local\keep-session.ps1 -InstallAuto
  powershell -ExecutionPolicy Bypass -File agents\local\keep-session.ps1 -Uninstall
#>
param([switch]$InstallAuto, [switch]$Uninstall)

$ErrorActionPreference = 'Stop'

# --- self-elevate ---
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
  $argline = "-ExecutionPolicy Bypass -NoProfile -File `"$PSCommandPath`""
  if ($InstallAuto) { $argline += " -InstallAuto" }
  if ($Uninstall)   { $argline += " -Uninstall" }
  Start-Process powershell.exe -Verb RunAs -ArgumentList $argline
  return
}

$TaskName = 'Naturo-KeepSession'

if ($Uninstall) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Output "removed $TaskName"
  return
}

if ($InstallAuto) {
  # On every RDP *disconnect*, redirect the disconnected session back to the console so it stays
  # ACTIVE. The session ID is read directly from the disconnect event (TerminalServices-
  # LocalSessionManager/Operational, Event 24) via a ValueQuery — language-independent and precise,
  # so it works on a non-English Windows where the `query session` state column is localized.
  # `$(SessionID)` below is a Task Scheduler value reference, NOT a PowerShell expression — it must
  # stay literal, hence the single-quoted here-string.
  $xml = @'
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Redirect a disconnected RDP session back to the console so the naturo QA loop keeps an active desktop.</Description>
  </RegistrationInfo>
  <Triggers>
    <EventTrigger>
      <Enabled>true</Enabled>
      <Subscription>&lt;QueryList&gt;&lt;Query Id="0" Path="Microsoft-Windows-TerminalServices-LocalSessionManager/Operational"&gt;&lt;Select Path="Microsoft-Windows-TerminalServices-LocalSessionManager/Operational"&gt;*[System[(EventID=24)]]&lt;/Select&gt;&lt;/Query&gt;&lt;/QueryList&gt;</Subscription>
      <ValueQueries>
        <Value name="SessionID">Event/UserData/EventXML/SessionID</Value>
      </ValueQueries>
    </EventTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT1M</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>cmd.exe</Command>
      <Arguments>/c tscon $(SessionID) /dest:console</Arguments>
    </Exec>
  </Actions>
</Task>
'@
  Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force | Out-Null
  Write-Output "registered $TaskName — on RDP disconnect, that session is auto-redirected to console (stays active)."
  Write-Output "Test: reconnect via mstsc, then just close the window; the QA loop should keep running."
  return
}

# --- manual one-shot: move the current session to console now ---
$sid = (Get-Process -Id $PID).SessionId
Write-Output "Redirecting session $sid to console. Your RDP window will drop; the session stays ACTIVE."
Start-Sleep -Seconds 1
& tscon $sid /dest:console
