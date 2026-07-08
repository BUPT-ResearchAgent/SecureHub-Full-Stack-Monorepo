# Status: real

param(
  [string]$RawDir = "data/raw/mediacrawler/xhs/jsonl",
  [string]$Domain = "course_websec",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$RawPath = Join-Path $Root $RawDir
$RightsNote = "小红书 UGC 用户内容；仅学习用途保留摘要与引用；不批量搬运。"

if (-not (Test-Path -LiteralPath $RawPath -PathType Container)) {
  Write-Host "[mediacrawler_xhs_import] RawDir does not exist, gracefully skipped: $RawPath"
  exit 0
}

$files = @(Get-ChildItem -LiteralPath $RawPath -Recurse -File -Include *.json,*.jsonl,*.csv)
if ($files.Count -eq 0) {
  Write-Host "[mediacrawler_xhs_import] No MediaCrawler export files found, gracefully skipped: $RawPath"
  exit 0
}

Write-Host "[mediacrawler_xhs_import] raw_dir=$RawPath"
Write-Host "[mediacrawler_xhs_import] files=$($files.Count)"
foreach ($file in $files) {
  Write-Host "  - $($file.FullName)"
}

if ($DryRun) {
  Write-Host "[mediacrawler_xhs_import] DryRun only performs file discovery; no database writes were made."
  exit 0
}

Push-Location (Join-Path $Root "backend")
try {
  uv run python ..\scripts\crawl\mediacrawler_export_import.py `
    "$RawPath" `
    --platform xhs `
    --domain "$Domain" `
    --storage-prefix "$Domain/mediacrawler" `
    --rights-note "$RightsNote"
}
finally {
  Pop-Location
}
