# Builds the Zyn wheel: the file people install with  pipx install <wheel>
# Output: dist\zyn_harness-<version>-py3-none-any.whl  (attach it to a GitHub release)
Set-Location (Split-Path $PSScriptRoot -Parent)
$ErrorActionPreference = "Stop"

Write-Host "Building the review screen..."
Push-Location web
if (-not (Test-Path node_modules)) { npm install --no-fund --no-audit }
npm run build
Pop-Location
if (-not (Test-Path web\dist\index.html)) { throw "Review screen build failed; no wheel made." }

Write-Host "Building the wheel..."
if (Test-Path build) { Remove-Item -Recurse -Force build }
.\.venv\Scripts\python -m pip wheel . --no-deps --no-build-isolation -w dist
Get-ChildItem dist\*.whl | Sort-Object LastWriteTime | Select-Object -Last 1
