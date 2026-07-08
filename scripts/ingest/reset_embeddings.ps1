# Status: real

param(
  [string]$FromProfile = "",
  [string]$ToProfile = "",
  [switch]$IncludeLegacyUnprofiledReady,
  [switch]$Yes
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$argsList = @("..\scripts\ingest\reset_embeddings.py")
if ($FromProfile) { $argsList += @("--from-profile", $FromProfile) }
if ($ToProfile) { $argsList += @("--to-profile", $ToProfile) }
if ($IncludeLegacyUnprofiledReady) { $argsList += "--include-legacy-unprofiled-ready" }
if ($Yes) { $argsList += "--yes" }

Push-Location (Join-Path $Root "backend")
try {
  uv run python @argsList
}
finally {
  Pop-Location
}
