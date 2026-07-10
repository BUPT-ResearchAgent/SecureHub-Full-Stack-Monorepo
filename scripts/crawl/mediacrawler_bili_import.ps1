# Status: real

param(
  [string]$RawDir = "data/raw/mediacrawler/bili/jsonl",
  [string]$Domain = "course_websec",
  [string]$RightsNote = "",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RightsNote)) {
  $RightsNote = -join ([char[]]@(
    0x0042, 0x0069, 0x006C, 0x0069, 0x0062, 0x0069, 0x006C, 0x0069,
    0x0020, 0x0055, 0x0047, 0x0043, 0x0020, 0x7528, 0x6237, 0x5185,
    0x5BB9, 0xFF0C, 0x4EC5, 0x5B66, 0x4E60, 0x7528, 0x9014, 0x4FDD,
    0x7559, 0x6458, 0x8981, 0x4E0E, 0x5F15, 0x7528, 0xFF1B, 0x4E0D,
    0x4E0B, 0x8F7D, 0x539F, 0x89C6, 0x9891, 0xFF0C, 0x4E0D, 0x6279,
    0x91CF, 0x8F6C, 0x8F7D, 0x3002
  ))
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$RawPath = Join-Path $Root $RawDir

if (-not (Test-Path -LiteralPath $RawPath -PathType Container)) {
  throw "RawDir does not exist: $RawPath"
}

$files = @(Get-ChildItem -LiteralPath $RawPath -Recurse -File -Include *.json,*.jsonl,*.csv)
if ($files.Count -eq 0) {
  throw "No MediaCrawler export files found under: $RawPath"
}

Write-Host "[mediacrawler_bili_import] raw_dir=$RawPath"
Write-Host "[mediacrawler_bili_import] files=$($files.Count)"
foreach ($file in $files) {
  Write-Host "  - $($file.FullName)"
}

if ($DryRun) {
  Write-Host "[mediacrawler_bili_import] DryRun only performs file discovery; current Python importer dry-run is not implemented, so no database writes were made."
  exit 0
}

$Backend = Join-Path $Root "backend"
Set-Location $Backend

uv run python ..\scripts\crawl\mediacrawler_export_import.py `
  "$RawPath" `
  --platform bili `
  --domain "$Domain" `
  --storage-prefix "$Domain/mediacrawler" `
  --rights-note "$RightsNote"
