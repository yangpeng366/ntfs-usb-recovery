<#
.SYNOPSIS
  Run the ntfs-usb-recovery quality gate locally: lint, tests, encoding sweep.

.DESCRIPTION
  Mirrors .github/workflows/ci.yml step for step.  A push is "ready" when
  this script exits 0.  Pass -SkipTests to run only the fast checks.

.EXAMPLE
  pwsh -NoProfile -File examples\quality-gate.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

$failures = @()

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        $script:failures += $Name
        Write-Host "    FAILED (exit $LASTEXITCODE)" -ForegroundColor Red
    }
    else {
        Write-Host "    ok" -ForegroundColor Green
    }
}

try {
    Invoke-Step "Lint (ruff)" { python -m ruff check . }
    if (-not $SkipTests) {
        Invoke-Step "Tests (pytest)" { python -m pytest tests/ -q }
    }
    Invoke-Step "Encoding sweep (no BOM, UTF-8)" { python examples/bom-sweep.py }
}
finally {
    Pop-Location
}

Write-Host ""
if ($failures.Count -gt 0) {
    Write-Host "FAILED: $($failures -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "OK: all checks passed" -ForegroundColor Green
exit 0
