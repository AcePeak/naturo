<#
.SYNOPSIS
  Agent-side client for the elevated install worker (software-support-installer.ps1).
  Drops a request on the queue and waits for the result. Non-elevated; safe to run
  from the agent session. Does nothing privileged itself — the elevated worker,
  stood up once by Ace, does the actual install/uninstall.

.EXAMPLE
  powershell -File agents\local\request-install.ps1 -Action list      -Id 7zip.7zip
  powershell -File agents\local\request-install.ps1 -Action install   -Id NetEase.CloudMusic -Version 3.1.37.205354
  powershell -File agents\local\request-install.ps1 -Action uninstall  -Id NetEase.CloudMusic
#>
param(
  [Parameter(Mandatory)][ValidateSet('install','uninstall','list')][string]$Action,
  [Parameter(Mandatory)][string]$Id,
  [string]$Version = '',
  [int]$TimeoutSec = 600
)
$ErrorActionPreference = 'Stop'
$Base    = Join-Path $env:USERPROFILE '.naturo-installer'
$Queue   = Join-Path $Base 'queue'
$Results = Join-Path $Base 'results'
$Heart   = Join-Path $Base 'heartbeat.txt'
if (-not (Test-Path $Queue)) {
  throw "Install channel not set up ($Queue missing). Ace must run agents\local\software-support-installer.ps1 from an ELEVATED PowerShell first."
}
if (Test-Path $Heart) {
  $age = (New-TimeSpan -Start (Get-Content -Raw $Heart).Trim() -End (Get-Date)).TotalSeconds
  if ($age -gt 120) { Write-Warning ("worker heartbeat is {0:n0}s old — worker may be down" -f $age) }
}
$nonce   = 'req-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + (Get-Random -Maximum 99999)
$reqPath = Join-Path $Queue   "$nonce.json"
$resPath = Join-Path $Results "$nonce.json"
$req = @{ action = $Action; id = $Id; version = $Version } | ConvertTo-Json -Compress
Set-Content -LiteralPath $reqPath -Value $req -Encoding utf8
Write-Output "queued: $Action $Id $Version  ($nonce)"
$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
  if (Test-Path $resPath) {
    Get-Content -Raw -LiteralPath $resPath
    exit 0
  }
  Start-Sleep -Milliseconds 800
}
Write-Error "timeout after ${TimeoutSec}s waiting for result $resPath"
exit 1
