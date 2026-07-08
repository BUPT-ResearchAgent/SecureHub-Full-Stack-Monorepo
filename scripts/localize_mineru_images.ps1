# Status: real

param(
    [switch]$DryRun,
    [switch]$Overwrite,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$argsList = @(
    "scripts/localize_markdown_images.py",
    "--host", "cdn-mineru.openxlab.org.cn",
    "--in-place",
    "--sleep", "0.05"
)

if ($DryRun) {
    $argsList += "--dry-run"
}
if ($Overwrite) {
    $argsList += "--overwrite"
}

& $Python @argsList
exit $LASTEXITCODE
