# setup_desktop.ps1 — full desktop calibration setup for study 001.
#
# Run from an elevated PowerShell on the desktop:
#
#     cd \\wsl$\Ubuntu\home\tlifke\Projects\morel-research      # or wherever you cloned
#     .\studies\001-tool-calibration\harness\setup_desktop.ps1
#
# What this does (all idempotent — safe to re-run):
#
#   1. Runs the WSL-side ollama installer (`setup_ollama_desktop.sh`)
#      via `wsl bash`. Skips steps that are already done.
#   2. Re-reads WSL2's current IP and refreshes the Windows portproxy
#      so the host listens on 11434 and forwards to WSL. WSL2 IP
#      changes on every boot — re-run this script after reboots.
#   3. Ensures the Windows Firewall rule for inbound 11434 exists.
#   4. Smoke-tests `http://127.0.0.1:11434/api/tags` from the
#      Windows host.

[CmdletBinding()]
param(
    # Path to the repo inside WSL. Defaults to the conventional clone
    # location on this machine.
    [string]$WslRepoPath = "/home/tlifke/Projects/morel-research"
)

$ErrorActionPreference = "Stop"

function Require-Admin {
    $current = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($current)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "This script must run from an elevated PowerShell (Run as Administrator)."
    }
}
Require-Admin

$shScript = "$WslRepoPath/studies/001-tool-calibration/harness/setup_ollama_desktop.sh"

Write-Host "==> Step 1: WSL-side ollama setup" -ForegroundColor Cyan
$exists = wsl test -f $shScript; $rc = $LASTEXITCODE
if ($rc -ne 0) {
    throw "Expected WSL-side script at $shScript not found. Did you clone the repo to that path?"
}
wsl bash $shScript
if ($LASTEXITCODE -ne 0) { throw "WSL setup_ollama_desktop.sh exited non-zero." }

Write-Host ""
Write-Host "==> Step 2: refresh WSL2 portproxy" -ForegroundColor Cyan
$wslIp = (wsl hostname -I).Trim().Split()[0]
Write-Host "    WSL IP: $wslIp"
# Drop any existing rule, then add fresh. `delete` is non-fatal if absent.
netsh interface portproxy delete v4tov4 listenport=11434 listenaddress=0.0.0.0 2>$null | Out-Null
netsh interface portproxy add v4tov4 `
    listenport=11434 listenaddress=0.0.0.0 `
    connectport=11434 connectaddress=$wslIp | Out-Null

Write-Host ""
Write-Host "==> Step 3: Windows Firewall rule" -ForegroundColor Cyan
$ruleName = "Ollama (Tailscale)"
if (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue) {
    Write-Host "    rule already exists; leaving alone"
} else {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound `
        -LocalPort 11434 -Protocol TCP -Action Allow | Out-Null
    Write-Host "    rule added"
}

Write-Host ""
Write-Host "==> Step 4: verify portproxy" -ForegroundColor Cyan
netsh interface portproxy show v4tov4

Write-Host ""
Write-Host "==> Step 5: local smoke test" -ForegroundColor Cyan
try {
    $tag = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5).Content
    Write-Host "    /api/tags response (truncated): $($tag.Substring(0, [Math]::Min(200, $tag.Length)))"
} catch {
    Write-Host "    WARNING: localhost:11434 not responding. Re-check ollama status." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "All set. From the laptop:" -ForegroundColor Green
Write-Host "  curl http://100.97.4.17:11434/api/tags"
