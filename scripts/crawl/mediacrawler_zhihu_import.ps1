# Status: real

param(
  [string]$RawDir = "data/raw/mediacrawler/zhihu/jsonl",
  [string]$Domain = "course_websec",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$RawPath = Join-Path $Root $RawDir
$RightsNote = "知乎 UGC 用户内容；仅学习用途保留摘要与引用；不批量搬运。"

if (-not (Test-Path -LiteralPath $RawPath -PathType Container)) {
  throw "RawDir does not exist: $RawPath"
}

$files = @(Get-ChildItem -LiteralPath $RawPath -Recurse -File -Include *.json,*.jsonl,*.csv)
if ($files.Count -eq 0) {
  throw "No MediaCrawler export files found under: $RawPath"
}

Write-Host "[mediacrawler_zhihu_import] raw_dir=$RawPath"
Write-Host "[mediacrawler_zhihu_import] files=$($files.Count)"
foreach ($file in $files) {
  Write-Host "  - $($file.FullName)"
}

if ($DryRun) {
  Write-Host "[mediacrawler_zhihu_import] DryRun only performs file discovery; no database writes were made."
  exit 0
}

Push-Location (Join-Path $Root "backend")
try {
  uv run python ..\scripts\crawl\mediacrawler_export_import.py `
    "$RawPath" `
    --platform zhihu `
    --domain "$Domain" `
    --storage-prefix "$Domain/mediacrawler" `
    --rights-note "$RightsNote"
}
finally {
  Pop-Location
}
