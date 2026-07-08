# Status: real

param(
  [string]$Domain = "",
  [int]$BatchSize = 10,
  [int]$Limit = 0,
  [switch]$RetryFailed,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$argsList = @("-m", "app.knowledge.loaders.embed_chunks", "--batch-size", "$BatchSize")
if ($Domain) { $argsList += @("--domain", $Domain) }
if ($Limit -gt 0) { $argsList += @("--limit", "$Limit") }
if ($RetryFailed) { $argsList += "--retry-failed" }
if ($DryRun) { $argsList += "--dry-run" }

Push-Location (Join-Path $Root "backend")
try {
  uv run python @argsList
}
finally {
  Pop-Location
}
