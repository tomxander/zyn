# Opens the Zyn review screen in your browser. Close this window to stop it.
Set-Location $PSScriptRoot
if (-not (Test-Path web\dist\index.html)) {
    Write-Host "Building the review screen (first run only)..."
    Push-Location web
    if (-not (Test-Path node_modules)) { npm install --no-fund --no-audit }
    npm run build
    Pop-Location
}
.\.venv\Scripts\python.exe -m harness serve
