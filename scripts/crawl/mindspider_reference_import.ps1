# Status: real

param(
    [string]$Fixture = "data/raw/mindspider/hot_topics_fixture.json",
    [string]$Domain = "news"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$FixturePath = Join-Path $Root $Fixture

if (-not (Test-Path -LiteralPath $FixturePath -PathType Leaf)) {
    throw "MindSpider fixture does not exist: $FixturePath"
}

Push-Location (Join-Path $Root "backend")
try {
    uv run python ..\scripts\crawl\mindspider_reference_import.py `
        --fixture "$FixturePath" `
        --domain "$Domain" `
        --storage-prefix "$Domain/mindspider_reference"
}
finally {
    Pop-Location
}
