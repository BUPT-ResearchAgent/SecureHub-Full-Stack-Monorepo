# Status: real

[CmdletBinding()]
param(
    [string[]]$PytestPattern = @(
        "tests/rag",
        "tests/hallucination",
        "tests/knowledge",
        "tests/resource",
        "tests/identity",
        "tests/db/test_seed_smoke.py"
    )
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"

Write-Host "[demo-smoke] SecureHub / CyberLadder P0 smoke"
Write-Host "[demo-smoke] backend: $BackendDir"

Push-Location $BackendDir
try {
    Write-Host "[demo-smoke] pytest $($PytestPattern -join ' ')"
    $Uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($Uv) {
        uv run pytest $PytestPattern
    }
    elseif (Test-Path ".\.venv\Scripts\python.exe") {
        .\.venv\Scripts\python.exe -m pytest $PytestPattern
    }
    elseif (Test-Path ".\.venv\bin\python") {
        .\.venv\bin\python -m pytest $PytestPattern
    }
    else {
        python -m pytest $PytestPattern
    }
    if ($LASTEXITCODE -ne 0) {
        throw "pytest failed with exit code $LASTEXITCODE"
    }
    Write-Host "[demo-smoke] OK: RAG, no-evidence, loaders, resources, capabilities, seed smoke"
}
finally {
    Pop-Location
}
