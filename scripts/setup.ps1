$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $repoRoot "backend"
$frontendPath = Join-Path $repoRoot "frontend"
$venvPath = Join-Path $backendPath ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

function Assert-NativeSuccess([string]$commandName) {
    if ($LASTEXITCODE -ne 0) {
        throw "$commandName failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    python -m venv $venvPath
    Assert-NativeSuccess "python -m venv"
}

& $venvPython -m pip install --upgrade pip
Assert-NativeSuccess "pip upgrade"
& $venvPython -m pip install -e "$backendPath[dev]"
Assert-NativeSuccess "backend dependency installation"

Push-Location $frontendPath
try {
    npm ci
    Assert-NativeSuccess "frontend dependency installation"
}
finally {
    Pop-Location
}

$environmentFile = Join-Path $backendPath ".env"
if (-not (Test-Path -LiteralPath $environmentFile)) {
    Copy-Item -LiteralPath (Join-Path $backendPath ".env.example") -Destination $environmentFile
}

Write-Host "Setup complete. Add OPENAI_API_KEY to backend\.env before live analysis."
