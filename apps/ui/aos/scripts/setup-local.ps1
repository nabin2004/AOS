# AOS local development bootstrap (Windows PowerShell)
# Installs dependencies, creates env files, and (by default) starts the UI
# Docker stack with migrations + admin seed - Windows equivalent of `make bootstrap`.
#
# Usage:
#   cd apps/ui/aos
#   .\scripts\setup-local.ps1
#   .\scripts\setup-local.ps1 -SkipStack          # deps/env only
#   .\scripts\setup-local.ps1 -SkipAgents         # UI only (skip agents uv sync)

[CmdletBinding()]
param(
    [switch]$SkipStack,
    [switch]$SkipAgents
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
$AosRoot = Join-Path $RepoRoot "apps\ui\aos"
$BackendRoot = Join-Path $AosRoot "backend"
$FrontendRoot = Join-Path $AosRoot "frontend"
$AgentsRoot = Join-Path $RepoRoot "apps\agents"
$ComposeFile = Join-Path $AosRoot "docker-compose.dev.yml"
$ComposeArgs = @("-f", $ComposeFile)

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-ToolRuns {
    param(
        [string]$Name,
        [string[]]$VersionArgs = @("--version")
    )
    if (-not (Test-CommandExists $Name)) {
        return $false
    }
    try {
        # Avoid Select-Object -First 1: it can stop the pipeline and trip catch blocks.
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & $Name @VersionArgs 1>$null 2>$null
        $code = $LASTEXITCODE
        $ErrorActionPreference = $prevEap
        if ($null -eq $code) { return $true }
        return ($code -eq 0)
    } catch {
        return $false
    }
}

function Get-ToolVersionLine {
    param(
        [string]$Name,
        [string[]]$VersionArgs = @("--version")
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $line = (& $Name @VersionArgs 2>&1 | Out-String).Trim().Split("`n")[0]
    $ErrorActionPreference = $prevEap
    return $line
}

function Copy-EnvIfMissing {
    param([string]$Example, [string]$Target)
    if (-not (Test-Path $Example)) {
        Write-Warning "  Example not found: $Example"
        return
    }
    if (Test-Path $Target) {
        Write-Host "  Already exists: $Target"
    } else {
        Copy-Item $Example $Target
        Write-Host "  Created: $Target"
    }
}

function Invoke-Compose {
    param([string[]]$ComposeCommand)
    # Pass args as an array so flags like -T are not parsed as PowerShell parameters.
    # Docker writes progress to stderr; with $ErrorActionPreference=Stop that becomes a
    # terminating error when merged via 2>&1. Temporarily continue, then restore.
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & docker @("compose") @ComposeArgs @ComposeCommand 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    foreach ($line in @($out)) {
        Write-Host $line
    }
    if ($null -eq $code) {
        return 0
    }
    return [int]$code
}

function Wait-ForPostgres {
    param([int]$Attempts = 30)
    Write-Host "  Waiting for PostgreSQL..."
    for ($i = 1; $i -le $Attempts; $i++) {
        & docker @("compose") @ComposeArgs @("exec", "-T", "db", "pg_isready", "-U", "postgres") 1>$null 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  DB ready"
            return
        }
        Write-Host "  ." -NoNewline
        Start-Sleep -Seconds 2
    }
    Write-Host ""
    throw "PostgreSQL not ready after $($Attempts * 2)s - check: docker compose -f docker-compose.dev.yml logs db"
}

function Wait-ForApiHealth {
    param([int]$Attempts = 45)
    Write-Host "  Waiting for API health..."
    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) {
                Write-Host "  API healthy"
                return
            }
        } catch {
            # still starting
        }
        Write-Host "  ." -NoNewline
        Start-Sleep -Seconds 2
    }
    Write-Host ""
    throw "API not healthy after $($Attempts * 2)s - check: docker compose -f docker-compose.dev.yml logs app"
}

function Start-UiStack {
    Push-Location $AosRoot
    try {
        Write-Host ""
        Write-Host "Starting UI Docker stack..." -ForegroundColor Yellow

        Write-Host "  Building backend image..."
        $code = Invoke-Compose -ComposeCommand @("build", "app")
        if ($code -ne 0) { throw "docker compose build app failed (exit $code)" }

        Write-Host "  Starting services..."
        $code = Invoke-Compose -ComposeCommand @("up", "-d")
        if ($code -ne 0) {
            Write-Warning "  First start failed. Tearing down orphans and retrying once..."
            $null = Invoke-Compose -ComposeCommand @("down", "--remove-orphans")
            $code = Invoke-Compose -ComposeCommand @("up", "-d")
            if ($code -ne 0) { throw "docker compose up failed (exit $code)" }
        }

        Wait-ForPostgres

        Write-Host "  Applying migrations..."
        $code = Invoke-Compose -ComposeCommand @("exec", "-T", "app", "aos", "db", "upgrade")
        if ($code -ne 0) { throw "aos db upgrade failed (exit $code)" }

        # App may have crashed on first boot if tables were missing; restart after migrate.
        Write-Host "  Restarting app after migrations..."
        $code = Invoke-Compose -ComposeCommand @("restart", "app")
        if ($code -ne 0) { throw "docker compose restart app failed (exit $code)" }

        Wait-ForApiHealth

        Write-Host "  Seeding admin user (admin@example.com)..."
        $userList = & docker @("compose") @ComposeArgs @("exec", "-T", "app", "aos", "user", "list") 2>&1 | Out-String
        if ($userList -match "admin@example.com") {
            Write-Host "  (admin@example.com already exists - nothing to do)"
        } else {
            $code = Invoke-Compose -ComposeCommand @(
                "exec", "-T", "app", "aos", "user", "create",
                "--email", "admin@example.com",
                "--password", "admin123",
                "--superuser"
            )
            if ($code -ne 0) { throw "admin seed failed (exit $code)" }
            Write-Host "  Admin created"
        }
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "=== AOS Local Development Setup ===" -ForegroundColor Cyan
Write-Host "Repo root: $RepoRoot"
if ($SkipStack) { Write-Host "Mode: deps/env only (-SkipStack)" }
if ($SkipAgents) { Write-Host "Mode: UI only (-SkipAgents)" }
Write-Host ""

# --- Prerequisites ---
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

$missing = @()

if (Test-CommandExists "docker") {
    Write-Host "  OK  Docker: $(Get-ToolVersionLine 'docker')"
    & docker info 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAIL  Docker daemon not running - start Docker Desktop" -ForegroundColor Red
        $missing += "Docker Desktop (daemon running)"
    } else {
        Write-Host "  OK  Docker daemon"
    }
} else {
    Write-Host "  MISSING  Docker" -ForegroundColor Red
    $missing += "Docker"
}

if (Test-CommandExists "uv") {
    Write-Host "  OK  uv: $(Get-ToolVersionLine 'uv')"
} else {
    Write-Host "  MISSING  uv" -ForegroundColor Red
    $missing += "uv"
}

$ollamaOk = Test-ToolRuns "ollama"
if ($ollamaOk) {
    Write-Host "  OK  Ollama: $(Get-ToolVersionLine 'ollama')"
} else {
    if ($SkipAgents) {
        Write-Host "  SKIP  Ollama (not required with -SkipAgents)" -ForegroundColor DarkYellow
    } else {
        Write-Host "  WARN  Ollama not found - needed for Manim agents only" -ForegroundColor DarkYellow
        Write-Host "        Install from https://ollama.com (UI stack can still start)"
    }
}

# Frontend package manager: bun only if it actually runs; else npm
$frontendPm = $null
if (Test-ToolRuns "bun") {
    $frontendPm = "bun"
    Write-Host "  OK  bun: $(Get-ToolVersionLine 'bun')"
} elseif (Test-CommandExists "bun") {
    Write-Host "  WARN  bun is installed but does not run - falling back to npm" -ForegroundColor DarkYellow
}

if (-not $frontendPm) {
    if (Test-ToolRuns "npm") {
        $frontendPm = "npm"
        Write-Host "  OK  npm: $(Get-ToolVersionLine 'npm')"
    } else {
        Write-Host "  MISSING  bun or npm (needed for frontend)" -ForegroundColor Red
        $missing += "bun or npm"
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Install / fix missing tools before continuing:" -ForegroundColor Red
    foreach ($m in $missing) { Write-Host "  - $m" }
    Write-Host ""
    Write-Host "  Docker:  https://docs.docker.com/get-docker/"
    Write-Host "  uv:      https://docs.astral.sh/uv/"
    Write-Host "  Ollama:  https://ollama.com  (Manim agents only)"
    Write-Host "  bun:     https://bun.sh  (or use Node.js / npm)"
    exit 1
}

# --- Environment files ---
Write-Host ""
Write-Host "Creating environment files..." -ForegroundColor Yellow

Copy-EnvIfMissing (Join-Path $BackendRoot ".env.example") (Join-Path $BackendRoot ".env")
Copy-EnvIfMissing (Join-Path $FrontendRoot ".env.example") (Join-Path $FrontendRoot ".env.local")
if (-not $SkipAgents) {
    Copy-EnvIfMissing (Join-Path $AgentsRoot ".env.example") (Join-Path $AgentsRoot ".env")
}

# --- Install dependencies ---
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow

if (-not $SkipAgents) {
    Write-Host "  uv sync (repo root - Manim agents workspace)..."
    Push-Location $RepoRoot
    uv sync
    if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
    Pop-Location
} else {
    Write-Host "  SKIP  uv sync (repo root) - -SkipAgents"
}

Write-Host "  uv sync (UI backend)..."
Push-Location $BackendRoot
uv sync
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "  Installing frontend packages ($frontendPm)..."
Push-Location $FrontendRoot
if ($frontendPm -eq "bun") {
    bun install
} else {
    npm install --legacy-peer-deps
}
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

# --- UI Docker stack (make bootstrap equivalent) ---
if (-not $SkipStack) {
    Start-UiStack
} else {
    Write-Host ""
    Write-Host "Skipping Docker stack (-SkipStack)." -ForegroundColor DarkYellow
}

# --- Done ---
Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Add API keys to env files (required for chat / Manim):"
Write-Host "     apps/ui/aos/backend/.env          -> OPENROUTER_API_KEY"
if (-not $SkipAgents) {
    Write-Host "     apps/agents/.env                  -> OPENROUTER_API_KEY"
}
Write-Host ""
if (-not $SkipStack) {
    Write-Host "2. Start the frontend (separate terminal):"
    Write-Host "     cd apps\ui\aos\frontend"
    if ($frontendPm -eq "bun") {
        Write-Host "     bun dev"
    } else {
        Write-Host "     npm run dev"
    }
    Write-Host ""
    Write-Host "3. Open:"
    Write-Host "     Frontend:  http://localhost:3000"
    Write-Host "     API docs:  http://localhost:8000/docs"
    Write-Host "     Admin:     http://localhost:8000/admin"
    Write-Host "     Login:     admin@example.com / admin123"
} else {
    Write-Host "2. Start the UI stack:"
    Write-Host "     cd apps\ui\aos"
    Write-Host "     .\scripts\setup-local.ps1          # full bootstrap (no -SkipStack)"
    Write-Host "     # or WSL/Git Bash: make bootstrap"
    Write-Host ""
    Write-Host "3. Start the frontend:"
    Write-Host "     cd apps\ui\aos\frontend"
    Write-Host "     npm run dev   # or: bun dev"
}
Write-Host ""
if (-not $SkipAgents) {
    Write-Host "Optional - Manim agents:"
    Write-Host "     ollama pull huggingface.co/nabin2004/AOS-gemma4-31b-manim-gguf:Q4_K_M"
    Write-Host "     cd apps\agents"
    Write-Host "     uv run python cli.py animate `"Draw a circle`""
    Write-Host ""
}
Write-Host "Day-to-day (PowerShell, from apps\ui\aos):"
Write-Host "     docker compose -f docker-compose.dev.yml up -d"
Write-Host "     docker compose -f docker-compose.dev.yml down"
Write-Host "     docker compose -f docker-compose.dev.yml logs -f"
Write-Host ""
Write-Host "Full guide: apps/ui/aos/LOCAL_DEV.md"
Write-Host ""
