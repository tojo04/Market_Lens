$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $repoRoot "backend"
$frontendPath = Join-Path $repoRoot "frontend"
$venvPython = Join-Path $backendPath ".venv\Scripts\python.exe"

function Assert-NativeSuccess([string]$commandName) {
    if ($LASTEXITCODE -ne 0) {
        throw "$commandName failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Backend virtual environment not found. Run scripts\setup.ps1 first."
}

Push-Location $backendPath
try {
    & $venvPython -m evaluation.run_evaluation
    Assert-NativeSuccess "offline evaluation"
    & $venvPython -m pytest
    Assert-NativeSuccess "backend tests"
    & $venvPython -m ruff check . (Join-Path $repoRoot "sample-data\generate_demo_pdf.py")
    Assert-NativeSuccess "backend lint"
    & $venvPython -m ruff format --check . (Join-Path $repoRoot "sample-data\generate_demo_pdf.py")
    Assert-NativeSuccess "backend format check"
    & $venvPython -m pip check
    Assert-NativeSuccess "backend dependency check"
}
finally {
    Pop-Location
}

Push-Location $frontendPath
try {
    npm run lint
    Assert-NativeSuccess "frontend lint"
    npm run typecheck
    Assert-NativeSuccess "frontend typecheck"
    npm run build
    Assert-NativeSuccess "frontend production build"
    npm audit --omit=dev
    Assert-NativeSuccess "frontend dependency audit"
}
finally {
    Pop-Location
}

Write-Host "All MarketLens checks passed."
