# Refresh the AOS Docker dev stack and ensure HOST Celery is running for Animate.
# Docker celery_worker cannot run uv/Manim - keep it stopped (profile docker-celery).
#
# Usage (from apps/ui/aos):
#   .\scripts\dev-refresh.ps1              # up infra/API + start host Celery
#   .\scripts\dev-refresh.ps1 -Rebuild     # rebuild image + recreate app/flower
#   .\scripts\dev-refresh.ps1 -AgentsOnly  # restart host Celery only
#   .\scripts\dev-refresh.ps1 -Logs        # follow host Celery + MinIO logs
#   .\scripts\dev-refresh.ps1 -DockerCelery  # also start Compose celery (advanced; Animate will fail)

[CmdletBinding()]
param(
    [switch]$Rebuild,
    [switch]$AgentsOnly,
    [switch]$Logs,
    [switch]$DockerCelery
)

$ErrorActionPreference = "Stop"

$AosRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$RepoRoot = Resolve-Path (Join-Path $AosRoot "..\..\..")
$BackendRoot = Join-Path $AosRoot "backend"
$AgentsRoot = Join-Path $RepoRoot "apps\agents"
$ComposeFile = Join-Path $AosRoot "docker-compose.dev.yml"
$ComposeArgs = @("-f", $ComposeFile)
$LogDir = Join-Path $AosRoot ".local"
$HostCeleryLog = Join-Path $LogDir "celery-worker.log"
$HostCeleryPid = Join-Path $LogDir "celery-worker.pid"

function Invoke-Compose {
    param([Parameter(Mandatory = $true)][string[]]$ComposeCmdArgs)
    & docker compose @ComposeArgs @ComposeCmdArgs
    if ($LASTEXITCODE -ne 0) {
        throw ("docker compose failed (exit " + $LASTEXITCODE + "): " + ($ComposeCmdArgs -join " "))
    }
}

function Test-HostCeleryRunning {
    if (Test-Path $HostCeleryPid) {
        $pidVal = (Get-Content $HostCeleryPid -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
        if ($pidVal -match "^\d+$") {
            try {
                $null = Get-Process -Id ([int]$pidVal) -ErrorAction Stop
                return [int]$pidVal
            } catch {
                Remove-Item $HostCeleryPid -Force -ErrorAction SilentlyContinue
            }
        }
    }
    $backendEscaped = [regex]::Escape($BackendRoot)
    $hit = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and (
                $_.CommandLine -match "aos celery worker" -or
                $_.CommandLine -match "celery -A app\.worker\.celery_app worker" -or
                $_.CommandLine -match "celery\.exe.*worker"
            ) -and $_.CommandLine -match $backendEscaped
        } | Select-Object -First 1
    if ($hit) { return [int]$hit.ProcessId }
    return $null
}

function Stop-DockerCelery {
    Write-Host "Stopping Docker celery_worker / celery_beat (if present)..." -ForegroundColor DarkGray
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & docker compose @ComposeArgs stop celery_worker celery_beat 2>&1 | Out-Null
        & docker compose @ComposeArgs rm -f celery_worker celery_beat 2>&1 | Out-Null
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Start-HostCelery {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv not found on PATH - install uv, then re-run this script."
    }
    if (-not (Test-Path (Join-Path $AgentsRoot "cli.py"))) {
        throw ("agents CLI not found at " + $AgentsRoot)
    }

    $existing = Test-HostCeleryRunning
    if ($existing) {
        Write-Host ("Host Celery already running (PID " + $existing + ").") -ForegroundColor Green
        return $existing
    }

    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    if (Test-Path $HostCeleryLog) {
        Move-Item $HostCeleryLog ($HostCeleryLog + ".bak") -Force -ErrorAction SilentlyContinue
    }

    Write-Host "Starting host Celery worker..." -ForegroundColor Cyan
    Write-Host ("  AGENTS_DIR=" + $AgentsRoot) -ForegroundColor DarkGray
    Write-Host "  S3_VIDEO_ENDPOINT=http://localhost:9010" -ForegroundColor DarkGray
    Write-Host ("  log: " + $HostCeleryLog) -ForegroundColor DarkGray

    $envBlock = @"
`$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath '$BackendRoot'
`$env:AGENTS_DIR = '$AgentsRoot'
`$env:AGENTS_UV_CMD = 'uv'
`$env:CELERY_BROKER_URL = 'redis://localhost:6379/0'
`$env:CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
`$env:S3_VIDEO_ENDPOINT = 'http://localhost:9010'
`$env:POSTGRES_HOST = 'localhost'
`$env:REDIS_HOST = 'localhost'
Remove-Item Env:VIRTUAL_ENV -ErrorAction SilentlyContinue
uv run celery -A app.worker.celery_app worker --loglevel=info --pool=solo --concurrency=1 2>&1 | Tee-Object -FilePath '$HostCeleryLog' -Append
"@

    $proc = Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $envBlock) `
        -WorkingDirectory $BackendRoot `
        -WindowStyle Hidden `
        -PassThru

    $proc.Id | Set-Content -Path $HostCeleryPid -Encoding ascii

    Start-Sleep -Seconds 3
    $alive = Test-HostCeleryRunning
    if (-not $alive) {
        Write-Host ("Celery may still be starting - check " + $HostCeleryLog) -ForegroundColor Yellow
        return $proc.Id
    }
    Write-Host ("Host Celery started (PID " + $alive + ").") -ForegroundColor Green
    return $alive
}

function Stop-HostCelery {
    $pidVal = Test-HostCeleryRunning
    if ($pidVal) {
        Write-Host ("Stopping host Celery PID " + $pidVal + "...") -ForegroundColor DarkGray
        try {
            Stop-Process -Id $pidVal -Force -ErrorAction SilentlyContinue
            Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
                Where-Object { $_.ParentProcessId -eq $pidVal } |
                ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        } catch {}
    }
    Remove-Item $HostCeleryPid -Force -ErrorAction SilentlyContinue
}

function Write-StackBanner {
    param([int]$CeleryPid)
    Write-Host ""
    Write-Host "Dev stack:" -ForegroundColor Green
    Write-Host "   API:           http://localhost:8000"
    Write-Host "   Docs:          http://localhost:8000/docs"
    Write-Host "   Flower:        http://localhost:5555"
    Write-Host "   MinIO console: http://localhost:9011  (minioadmin / minioadmin)"
    Write-Host "   MinIO API:     http://localhost:9010"
    Write-Host "   Frontend:      http://localhost:3000  (cd frontend; bun dev)"
    Write-Host ""
    Write-Host ("Animate Celery = HOST (auto). PID: " + $CeleryPid) -ForegroundColor Yellow
    Write-Host ("  Log: " + $HostCeleryLog)
    Write-Host "  Diagnose: .\scripts\diagnose-animate.ps1"
    Write-Host "Do not use Docker celery_worker for video (no uv/Manim)." -ForegroundColor DarkGray
    Write-Host "Optional Docker Celery: .\scripts\dev-refresh.ps1 -DockerCelery  (profile docker-celery)" -ForegroundColor DarkGray
    Write-Host ""
}

Push-Location $AosRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "docker not found - start Docker Desktop first."
    }

    if ($Logs) {
        Write-Host "Following host Celery log + MinIO (Ctrl+C to stop)..." -ForegroundColor Cyan
        if (-not (Test-Path $HostCeleryLog)) {
            Write-Host ("No host log yet at " + $HostCeleryLog + " - start with .\scripts\dev-refresh.ps1 first.") -ForegroundColor Yellow
        } else {
            Write-Host ("--- " + $HostCeleryLog + " (last 40 lines) ---") -ForegroundColor DarkGray
            Get-Content -LiteralPath $HostCeleryLog -Tail 40
        }
        Write-Host "--- minio logs (follow; Ctrl+C) ---" -ForegroundColor DarkGray
        & docker compose @ComposeArgs logs -f --tail=20 minio
        return
    }

    if ($AgentsOnly) {
        Stop-DockerCelery
        Stop-HostCelery
        $pid = Start-HostCelery
        Write-StackBanner -CeleryPid $pid
        return
    }

    if ($Rebuild) {
        Write-Host "Building backend image..." -ForegroundColor Cyan
        Invoke-Compose @("build", "app")
        Write-Host "Recreating app + flower (no Docker Celery)..." -ForegroundColor Cyan
        Invoke-Compose @("up", "-d", "--force-recreate", "app", "flower")
        Invoke-Compose @("up", "-d")
    }
    else {
        Write-Host "Ensuring stack is up (infra + API + Flower; no Docker Celery)..." -ForegroundColor Cyan
        Invoke-Compose @("up", "-d")
    }

    Stop-DockerCelery

    if ($DockerCelery) {
        Write-Host "Starting Compose celery with profile docker-celery (Animate likely broken)..." -ForegroundColor Yellow
        & docker compose @ComposeArgs --profile docker-celery up -d celery_worker celery_beat
    }

    $celeryPid = Start-HostCelery

    Write-Host "Service status:" -ForegroundColor Cyan
    Invoke-Compose @("ps")
    Write-StackBanner -CeleryPid $celeryPid
}
finally {
    Pop-Location
}
