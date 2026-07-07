# Status: real

param(
    [string[]]$Textbooks = @("crypto-basics", "network-security", "reverse-engineering"),
    [switch]$ForceReingest
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$mineruRoot = Join-Path $repoRoot "data\storage\course_websec\mineru"
$cli = Join-Path $repoRoot "scripts\ingest_pdf_mineru.py"
$backendDir = Join-Path $repoRoot "backend"

$titleMap = @{
    "crypto-basics" = "现代密码学教程（第2版）"
    "network-security" = "网络安全原理与实践"
    "reverse-engineering" = "汇编语言（第3版）"
}

foreach ($name in $Textbooks) {
    if ($name -eq "websec-textbook" -or $name -eq "websec-upload") {
        Write-Host "[ingest_pdf_mineru_batch] skipped preserved seed: $name"
        continue
    }

    $textbookDir = Join-Path $mineruRoot $name
    $pdfPath = Join-Path $textbookDir "$name.pdf"
    $markdownPath = Join-Path $textbookDir "full.md"
    if (-not (Test-Path -LiteralPath $pdfPath)) {
        throw "PDF not found for ${name}: $pdfPath"
    }
    if (-not (Test-Path -LiteralPath $markdownPath)) {
        throw "MinerU full.md not found for ${name}: $markdownPath"
    }

    $cliArgs = @(
        "run",
        "python",
        $cli,
        $pdfPath,
        "--mineru-output",
        $textbookDir,
        "--title",
        $titleMap[$name]
    )
    if ($ForceReingest) {
        $cliArgs += "--force-reingest"
    }

    Write-Host "[ingest_pdf_mineru_batch] importing $name"
    Push-Location $backendDir
    try {
        & uv @cliArgs
    }
    finally {
        Pop-Location
    }
}
