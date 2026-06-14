param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8000,
  [string]$App = "app.main:app",
  [switch]$KeepProxy,
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$UvicornArgs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

if (-not $KeepProxy) {
  @(
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
    "ALL_PROXY",
    "all_proxy"
  ) | ForEach-Object {
    Remove-Item -Path "Env:\$_" -ErrorAction SilentlyContinue
  }
}

Write-Host "Starting SecureHub backend at http://${BindHost}:$Port"

$uvicornArgs = @("uvicorn", $App, "--host", $BindHost, "--port", [string]$Port) + $UvicornArgs
if (Get-Command uv -ErrorAction SilentlyContinue) {
  & uv run @uvicornArgs
  exit $LASTEXITCODE
}

$pythonArgs = @("-m", "uvicorn", $App, "--host", $BindHost, "--port", [string]$Port) + $UvicornArgs
if (Get-Command python -ErrorAction SilentlyContinue) {
  & python @pythonArgs
  exit $LASTEXITCODE
}

Write-Error "Neither 'uv' nor 'python' was found in PATH."
exit 127
