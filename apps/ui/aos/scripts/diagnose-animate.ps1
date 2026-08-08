# Diagnose Animate end-to-end hops: Compose -> Redis -> Celery -> DB -> MinIO.
#
# Usage (from apps/ui/aos):
#   .\scripts\diagnose-animate.ps1

[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"

$AosRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$RepoRoot = Resolve-Path (Join-Path $AosRoot "..\..\..")
$BackendRoot = Join-Path $AosRoot "backend"
$AgentsRoot = Join-Path $RepoRoot "apps\agents"
$ComposeFile = Join-Path $AosRoot "docker-compose.dev.yml"
$ComposeArgs = @("-f", $ComposeFile)
$LogDir = Join-Path $AosRoot ".local"
$HostCeleryLog = Join-Path $LogDir "celery-worker.log"
$HostCeleryPid = Join-Path $LogDir "celery-worker.pid"

$script:pass = 0
$script:fail = 0
$script:warn = 0

function Write-Hop {
    param(
        [string]$Name,
        [ValidateSet("PASS", "FAIL", "WARN", "INFO")][string]$Status,
        [string]$Detail
    )
    $color = switch ($Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        default { "Cyan" }
    }
    Write-Host ("[{0}] {1}: {2}" -f $Status, $Name, $Detail) -ForegroundColor $color
    switch ($Status) {
        "PASS" { $script:pass++ }
        "FAIL" { $script:fail++ }
        "WARN" { $script:warn++ }
    }
}

function Invoke-Compose {
    param([Parameter(Mandatory = $true)][string[]]$ComposeCmdArgs)
    & docker compose @ComposeArgs @ComposeCmdArgs 2>&1
}

Write-Host ""
Write-Host "=== Animate E2E diagnose ===" -ForegroundColor Cyan
Write-Host "AOS root: $AosRoot"
Write-Host ""

# 1. Docker available
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Hop "docker" "FAIL" "docker not found - start Docker Desktop"
    Write-Host ""
    Write-Host "Summary: $($script:pass) PASS / $($script:fail) FAIL / $($script:warn) WARN" -ForegroundColor Red
    exit 1
}
Write-Hop "docker" "PASS" "docker CLI available"

# 2. Compose services
$psOut = (Invoke-Compose @("ps", "--format", "json")) | Out-String
$services = @{}
try {
    $lines = ($psOut -split "`n") | Where-Object { $_.Trim().StartsWith("{") }
    foreach ($line in $lines) {
        $obj = $line | ConvertFrom-Json
        if ($obj.Service) { $services[$obj.Service] = $obj }
        elseif ($obj.Name) { $services[$obj.Name] = $obj }
    }
} catch {
    # Fallback: plain ps text
}

$required = @("app", "db", "redis", "minio")
foreach ($svc in $required) {
    $row = $services[$svc]
    if (-not $row) {
        $plain = (Invoke-Compose @("ps", $svc)) | Out-String
        if ($plain -match "Up|running|healthy") {
            Write-Hop "compose:$svc" "PASS" "appears up"
        } else {
            Write-Hop "compose:$svc" "FAIL" "not running - run .\scripts\dev-refresh.ps1"
        }
        continue
    }
    $state = "$($row.State) $($row.Health) $($row.Status)".Trim()
    if ($state -match "running|Up" -or $row.Health -eq "healthy") {
        Write-Hop "compose:$svc" "PASS" $state
    } else {
        Write-Hop "compose:$svc" "FAIL" $state
    }
}

$dockerCelery = $services["celery_worker"]
if ($dockerCelery -and ("$($dockerCelery.State) $($dockerCelery.Status)" -match "running|Up")) {
    Write-Hop "compose:celery_worker" "WARN" "Docker celery is running - Animate needs HOST celery. Stop via refresh."
} else {
    Write-Hop "compose:celery_worker" "PASS" "not consuming (expected - use host Celery)"
}

# 3. MinIO live
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:9010/minio/health/live" -UseBasicParsing -TimeoutSec 5
    if ($resp.StatusCode -eq 200) {
        Write-Hop "minio:health" "PASS" "http://localhost:9010/minio/health/live OK"
    } else {
        Write-Hop "minio:health" "FAIL" ("status " + $resp.StatusCode)
    }
} catch {
    Write-Hop "minio:health" "FAIL" $_.Exception.Message
}

# 4. Redis
$redisOut = (Invoke-Compose @("exec", "-T", "redis", "redis-cli", "ping")) | Out-String
if ($redisOut -match "PONG") {
    Write-Hop "redis" "PASS" "PONG"
} else {
    Write-Hop "redis" "FAIL" $redisOut.Trim()
}

# 5. Host Celery process / pid file
$hostCeleryRunning = $false
if (Test-Path $HostCeleryPid) {
    $pidVal = (Get-Content $HostCeleryPid -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($pidVal -match "^\d+$") {
        try {
            $proc = Get-Process -Id ([int]$pidVal) -ErrorAction Stop
            Write-Hop "host:celery" "PASS" ("PID " + $pidVal + " (" + $proc.ProcessName + ") - log: " + $HostCeleryLog)
            $hostCeleryRunning = $true
        } catch {
            Write-Hop "host:celery" "FAIL" ("stale PID file " + $pidVal + " - run .\scripts\dev-refresh.ps1")
        }
    }
}
if (-not $hostCeleryRunning) {
    $celeryProcs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -match "celery.*worker|aos celery worker" }
    if ($celeryProcs) {
        $ids = ($celeryProcs | ForEach-Object { $_.ProcessId }) -join ", "
        Write-Hop "host:celery" "PASS" ("found process(es): " + $ids)
        $hostCeleryRunning = $true
    } else {
        Write-Hop "host:celery" "FAIL" "no host worker - run .\scripts\dev-refresh.ps1"
    }
}

# 6. Celery inspect ping (from backend with host Redis)
$inspectOk = $false
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Push-Location $BackendRoot
    try {
        $env:CELERY_BROKER_URL = "redis://localhost:6379/0"
        $env:CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
        $pingOut = & uv run celery -A app.worker.celery_app inspect ping -t 5 2>&1 | Out-String
        $pingTrim = $pingOut.Trim()
        if ($pingTrim -match "pong|ok" -and $pingTrim -notmatch "Error communicating|No nodes replied") {
            $snippet = $pingTrim -replace "\s+", " "
            if ($snippet.Length -gt 120) { $snippet = $snippet.Substring(0, 120) }
            Write-Hop "celery:inspect" "PASS" $snippet
            $inspectOk = $true
        } else {
            $snippet = $pingTrim
            if ($snippet.Length -gt 160) { $snippet = $snippet.Substring(0, 160) }
            Write-Hop "celery:inspect" "FAIL" ("no pong - " + $snippet)
        }
    } catch {
        Write-Hop "celery:inspect" "FAIL" $_.Exception.Message
    } finally {
        Pop-Location
    }
} else {
    Write-Hop "celery:inspect" "WARN" "uv not on PATH - skip inspect ping"
}

# 7. Docker worker uv / agents (if container exists)
$inspectDocker = (Invoke-Compose @("ps", "celery_worker")) | Out-String
if ($inspectDocker -match "Up|running") {
    $uvScript = 'command -v uv; if [ $? -ne 0 ]; then echo NO_UV; fi'
    $whichUv = (Invoke-Compose @("exec", "-T", "celery_worker", "sh", "-c", $uvScript)) | Out-String
    if ($whichUv -match "NO_UV" -or $whichUv -notmatch "uv") {
        Write-Hop "docker:uv" "WARN" "uv missing in celery_worker (expected - stop Docker celery via refresh)"
    } else {
        Write-Hop "docker:uv" "PASS" $whichUv.Trim()
    }
    $cliScript = 'if [ -f /agents/cli.py ]; then echo HAS_CLI; else echo NO_CLI; fi'
    $cliCheck = (Invoke-Compose @("exec", "-T", "celery_worker", "sh", "-c", $cliScript)) | Out-String
    if ($cliCheck -match "HAS_CLI") {
        Write-Hop "docker:agents" "WARN" "/agents/cli.py present but mount is often :ro - compile needs host"
    } else {
        Write-Hop "docker:agents" "WARN" "/agents/cli.py missing in Docker worker"
    }
}

# 8. AGENTS_DIR on host
if (Test-Path (Join-Path $AgentsRoot "cli.py")) {
    Write-Hop "host:agents" "PASS" $AgentsRoot
} else {
    Write-Hop "host:agents" "FAIL" ("cli.py not found at " + $AgentsRoot)
}

# 9. Last video_generations row
$sql = @'
SELECT id::text, status, COALESCE(left(error_message, 120), '') AS err,
       COALESCE(celery_task_id, '') AS task, COALESCE(minio_key, '') AS minio_key,
       created_at::text
FROM video_generations
ORDER BY created_at DESC NULLS LAST
LIMIT 3;
'@
$dbOut = (Invoke-Compose @("exec", "-T", "db", "psql", "-U", "postgres", "-d", "aos", "-c", $sql)) | Out-String
if ($dbOut -and ($dbOut -match "status|id")) {
    Write-Hop "db:video_generations" "INFO" "latest rows:"
    Write-Host $dbOut
    if ($dbOut -match "completed" -and $dbOut -match "videos/") {
        Write-Hop "db:last_ok" "PASS" "recent completed row with minio_key"
    } elseif ($dbOut -match "failed|pending|running") {
        Write-Hop "db:last_status" "WARN" "see error_message above - that names the failing hop"
    } elseif ($dbOut -match "\(0 rows\)" -or $dbOut -match "0 rows") {
        Write-Hop "db:last_status" "INFO" "no generations yet - Animate once in chat then re-run"
    }
} else {
    $snippet = if ($dbOut) { $dbOut.Trim() } else { "(empty)" }
    if ($snippet.Length -gt 200) { $snippet = $snippet.Substring(0, 200) }
    Write-Hop "db:video_generations" "FAIL" $snippet
}

# 10. API health
try {
    $h = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -UseBasicParsing -TimeoutSec 5
    Write-Hop "api:health" "PASS" ("status " + $h.StatusCode)
} catch {
    try {
        $h2 = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
        Write-Hop "api:health" "PASS" ("status " + $h2.StatusCode)
    } catch {
        Write-Hop "api:health" "WARN" "could not hit health endpoint - is app up?"
    }
}

Write-Host ""
Write-Host "=== Hop map ===" -ForegroundColor Cyan
Write-Host "Enqueue (API) -> Redis broker -> HOST Celery -> apps/agents (uv+manim) -> MinIO aos-videos -> UI stream"
Write-Host "Flower:        http://localhost:5555"
Write-Host "MinIO console: http://localhost:9011  (minioadmin / minioadmin)"
Write-Host "Host celery log: $HostCeleryLog"
Write-Host "Expected after smoke: status=completed + minio_key set; re-run this script."
Write-Host "Diagnose again after Animate: .\scripts\diagnose-animate.ps1"
Write-Host ""

$summaryColor = if ($script:fail -gt 0) { "Red" } elseif ($script:warn -gt 0) { "Yellow" } else { "Green" }
Write-Host ("Summary: {0} PASS / {1} FAIL / {2} WARN" -f $script:pass, $script:fail, $script:warn) -ForegroundColor $summaryColor

if (-not $inspectOk -or -not $hostCeleryRunning) {
    Write-Host ""
    Write-Host "Fix: cd apps\ui\aos; .\scripts\dev-refresh.ps1" -ForegroundColor Yellow
    Write-Host "Then Animate a short prompt and re-run this script - expect status=completed + minio_key." -ForegroundColor Yellow
}

if ($script:fail -gt 0) { exit 1 } else { exit 0 }
