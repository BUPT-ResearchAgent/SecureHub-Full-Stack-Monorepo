# Status: real

[CmdletBinding()]
param(
    [string]$BackendUrl = "http://127.0.0.1:8000",
    [int]$TimeoutSeconds = 45,
    [switch]$NoStartBackend
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$WorkspaceRoot = Split-Path -Parent $RepoRoot
$SmokeLogDir = Join-Path $RepoRoot "data\demo\smoke"
$BackendProcess = $null
$StartedBackend = $false

$UserId = "00000000-0000-0000-0000-000000000001"
$KpId = "00000000-0000-0000-0000-000000000201"

function Initialize-SmokeEnvironment {
    New-Item -ItemType Directory -Force -Path $SmokeLogDir | Out-Null

    $ProcessPath = [Environment]::GetEnvironmentVariable("Path", "Process")
    if (-not $ProcessPath) {
        $ProcessPath = [Environment]::GetEnvironmentVariable("PATH", "Process")
    }
    if ($ProcessPath) {
        [Environment]::SetEnvironmentVariable("Path", $ProcessPath, "Process")
        [Environment]::SetEnvironmentVariable("PATH", $null, "Process")
    }

    if (-not $env:UV_CACHE_DIR) {
        $env:UV_CACHE_DIR = Join-Path $WorkspaceRoot ".uv-cache"
    }
    if (-not $env:TMP) {
        $env:TMP = Join-Path $WorkspaceRoot ".tmp"
    }
    if (-not $env:TEMP) {
        $env:TEMP = Join-Path $WorkspaceRoot ".tmp"
    }
    New-Item -ItemType Directory -Force -Path $env:UV_CACHE_DIR | Out-Null
    New-Item -ItemType Directory -Force -Path $env:TMP | Out-Null
    New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null

    $SharedVenv = Join-Path $WorkspaceRoot ".securehub-backend-venv"
    $BackendVenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
    if ((-not $env:UV_PROJECT_ENVIRONMENT) -and
        (Test-Path (Join-Path $SharedVenv "Scripts\python.exe")) -and
        (-not (Test-Path $BackendVenvPython))) {
        $env:UV_PROJECT_ENVIRONMENT = $SharedVenv
    }

    if (-not $env:LLM_PROVIDER) {
        $env:LLM_PROVIDER = "fixture"
    }
    if (-not $env:ENABLE_LLM_LIVE_TESTS) {
        $env:ENABLE_LLM_LIVE_TESTS = "false"
    }
}

function New-SmokeResult {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    [PSCustomObject]@{
        Step = $Name
        Status = $(if ($Passed) { "PASS" } else { "FAIL" })
        Detail = $Detail
    }
}

$Results = New-Object System.Collections.Generic.List[object]

function Add-SmokeResult {
    param(
        [string]$Name,
        [bool]$Passed,
        [string]$Detail
    )
    $Result = New-SmokeResult -Name $Name -Passed $Passed -Detail $Detail
    $Results.Add($Result) | Out-Null
    Write-Host ("[{0}] {1} - {2}" -f $Result.Status, $Name, $Detail)
}

function Invoke-SmokeJson {
    param(
        [ValidateSet("GET", "POST")]
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )
    $Uri = "$BackendUrl$Path"
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $Uri -TimeoutSec 20
    }
    $JsonBody = $Body | ConvertTo-Json -Depth 16
    return Invoke-RestMethod -Method $Method -Uri $Uri -ContentType "application/json" -Body $JsonBody -TimeoutSec 30
}

function Invoke-SmokeText {
    param(
        [string]$Path,
        [object]$Body
    )
    $Uri = "$BackendUrl$Path"
    $JsonBody = $Body | ConvertTo-Json -Depth 16
    $Params = @{
        Method = "POST"
        Uri = $Uri
        ContentType = "application/json"
        Body = $JsonBody
        TimeoutSec = 45
    }
    if ($PSVersionTable.PSVersion.Major -lt 6) {
        $Params["UseBasicParsing"] = $true
    }
    $Response = Invoke-WebRequest @Params
    return $Response.Content
}

function Test-BackendHealth {
    try {
        $Health = Invoke-SmokeJson -Method "GET" -Path "/api/v1/health"
        return $null -ne $Health
    }
    catch {
        return $false
    }
}

function Start-SmokeBackend {
    if ($NoStartBackend) {
        return
    }
    if (Test-BackendHealth) {
        Write-Host "[demo-smoke] reusing running backend at $BackendUrl"
        return
    }

    Write-Host "[demo-smoke] starting backend at $BackendUrl"
    $OutLog = Join-Path $SmokeLogDir "backend.stdout.log"
    $ErrLog = Join-Path $SmokeLogDir "backend.stderr.log"
    $UvicornArgs = @("run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000")
    $Uv = Get-Command uv -ErrorAction SilentlyContinue

    if ($Uv) {
        $script:BackendProcess = Start-Process -FilePath $Uv.Source -ArgumentList $UvicornArgs -WorkingDirectory $BackendDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog
    }
    elseif (Test-Path (Join-Path $BackendDir ".venv\Scripts\python.exe")) {
        $Python = Join-Path $BackendDir ".venv\Scripts\python.exe"
        $script:BackendProcess = Start-Process -FilePath $Python -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $BackendDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog
    }
    else {
        $script:BackendProcess = Start-Process -FilePath "python" -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $BackendDir -PassThru -WindowStyle Hidden -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog
    }

    $script:StartedBackend = $true
    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        if ($script:BackendProcess.HasExited) {
            throw "backend exited during startup; see $ErrLog"
        }
        if (Test-BackendHealth) {
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "backend did not become healthy within $TimeoutSeconds seconds; see $ErrLog"
}

function Run-SmokeStep {
    param(
        [string]$Name,
        [scriptblock]$Block
    )
    try {
        $Detail = & $Block
        Add-SmokeResult -Name $Name -Passed $true -Detail ([string]$Detail)
    }
    catch {
        Add-SmokeResult -Name $Name -Passed $false -Detail $_.Exception.Message
    }
}

Write-Host "[demo-smoke] SecureHub / CyberLadder API smoke"
Write-Host "[demo-smoke] backend: $BackendDir"
Write-Host "[demo-smoke] url: $BackendUrl"

Initialize-SmokeEnvironment

try {
    Start-SmokeBackend

    Run-SmokeStep "health" {
        $Health = Invoke-SmokeJson -Method "GET" -Path "/api/v1/health"
        if (-not $Health.status) {
            throw "missing status"
        }
        "status=$($Health.status)"
    }

    Run-SmokeStep "llm/health" {
        $Llm = Invoke-SmokeJson -Method "GET" -Path "/api/v1/llm/health"
        if ($Llm.status -ne "available") {
            throw "llm status=$($Llm.status)"
        }
        "provider=$($Llm.provider), mode=$($Llm.mode), live_enabled=$($Llm.live_enabled)"
    }

    Run-SmokeStep "courses" {
        $Courses = Invoke-SmokeJson -Method "GET" -Path "/api/v1/courses"
        $CourseList = @($Courses)
        if ($Courses.items) {
            $CourseList = @($Courses.items)
        }
        $WebSec = $CourseList | Where-Object { $_.code -eq "WEB-SEC-101" } | Select-Object -First 1
        if (-not $WebSec) {
            throw "WEB-SEC-101 not found"
        }
        "count=$($CourseList.Count), websec=$($WebSec.id)"
    }

    Run-SmokeStep "rag/search" {
        $Rag = Invoke-SmokeJson -Method "POST" -Path "/api/v1/rag/search" -Body @{
            domain = "course_websec"
            query = "SQL injection parameterized queries"
            top_k = 3
        }
        if (-not $Rag.hits -or $Rag.hits.Count -lt 1) {
            throw "no rag hits"
        }
        "hits=$($Rag.hits.Count), fallback=$($Rag.fallback)"
    }

    Run-SmokeStep "course plan" {
        $Plan = Invoke-SmokeJson -Method "POST" -Path "/api/v1/courses/course-websec/plan" -Body @{
            user_id = $UserId
            target_node_id = $KpId
            options = @{
                depth = 3
            }
        }
        if (-not $Plan.path) {
            throw "missing path"
        }
        "course_id=$($Plan.course_id), path=$($Plan.path.Count)"
    }

    Run-SmokeStep "resources/generate" {
        $Events = Invoke-SmokeText -Path "/api/v1/courses/course-websec/resources/generate?type=doc" -Body @{
            type = "doc"
            user_id = $UserId
            kp_id = $KpId
            options = @{
                query = "Generate fixture doc for SQL injection"
            }
        }
        if ($Events -notmatch "event: evidence") {
            throw "missing evidence event"
        }
        if ($Events -notmatch "event: artifact") {
            throw "missing artifact event"
        }
        if ($Events -notmatch "event: done") {
            throw "missing done event"
        }
        "sse events include evidence/artifact/done"
    }

    Run-SmokeStep "agent_runs" {
        $Runs = Invoke-SmokeJson -Method "GET" -Path "/api/v1/agent-runs?limit=5"
        if ($null -ne $Runs.items) {
            return "items=$($Runs.items.Count), total=$($Runs.total)"
        }
        $RunList = @($Runs)
        "items=$($RunList.Count)"
    }
}
finally {
    if ($StartedBackend -and $BackendProcess -and (-not $BackendProcess.HasExited)) {
        Write-Host "[demo-smoke] stopping backend pid=$($BackendProcess.Id)"
        Stop-Process -Id $BackendProcess.Id -Force
    }
}

Write-Host ""
Write-Host "[demo-smoke] summary"
$Results | Format-Table -AutoSize

$Failures = @($Results | Where-Object { $_.Status -ne "PASS" })
if ($Failures.Count -gt 0) {
    Write-Host "[demo-smoke] FAILED: $($Failures.Count) step(s)"
    exit 1
}

Write-Host "[demo-smoke] PASSED: $($Results.Count) step(s)"
