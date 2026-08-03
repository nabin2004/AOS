# AOS local development bootstrap (Windows PowerShell)
# Installs dependencies and creates env files. Does NOT start Docker services.
#
# Usage:
#   cd apps/ui/aos
#   .\scripts\setup-local.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..\..")
$AosRoot = Join-Path $RepoRoot "apps\ui\aos"
$BackendRoot = Join-Path $AosRoot "backend"
$FrontendRoot = Join-Path $AosRoot "frontend"
$AgentsRoot = Join-Path $RepoRoot "apps\agents"

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
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

Write-Host ""
Write-Host "=== AOS Local Development Setup ===" -ForegroundColor Cyan
Write-Host "Repo root: $RepoRoot"
Write-Host ""

# --- Prerequisites ---
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

$checks = @(
    @{ Name = "Docker"; Cmd = "docker"; Args = @("--version") },
    @{ Name = "uv"; Cmd = "uv"; Args = @("--version") },
    @{ Name = "Ollama"; Cmd = "ollama"; Args = @("--version") }
)

$missing = @()
foreach ($c in $checks) {
    if (Test-CommandExists $c.Cmd) {
        $ver = & $c.Cmd @($c.Args) 2>&1 | Select-Object -First 1
        Write-Host "  OK  $($c.Name): $ver"
    } else {
        Write-Host "  MISSING  $($c.Name)" -ForegroundColor Red
        $missing += $c.Name
    }
}

# Frontend package manager: bun preferred, npm fallback
$frontendPm = $null
if (Test-CommandExists "bun") {
    $frontendPm = "bun"
    $ver = & bun --version 2>&1
    Write-Host "  OK  bun: $ver"
} elseif (Test-CommandExists "npm") {
    $frontendPm = "npm"
    $ver = & npm --version 2>&1
    Write-Host "  OK  npm (bun not found, using npm): $ver"
} else {
    Write-Host "  MISSING  bun or npm (needed for frontend)" -ForegroundColor Red
    $missing += "bun or npm"
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Install missing tools before continuing:" -ForegroundColor Red
    foreach ($m in $missing) { Write-Host "  - $m" }
    Write-Host ""
    Write-Host "  Docker:  https://docs.docker.com/get-docker/"
    Write-Host "  uv:      https://docs.astral.sh/uv/"
    Write-Host "  Ollama:  https://ollama.com"
    Write-Host "  bun:     https://bun.sh  (or use npm with --legacy-peer-deps)"
    exit 1
}

# --- Environment files ---
Write-Host ""
Write-Host "Creating environment files..." -ForegroundColor Yellow

Copy-EnvIfMissing (Join-Path $BackendRoot ".env.example") (Join-Path $BackendRoot ".env")
Copy-EnvIfMissing (Join-Path $FrontendRoot ".env.example") (Join-Path $FrontendRoot ".env.local")
Copy-EnvIfMissing (Join-Path $AgentsRoot ".env.example") (Join-Path $AgentsRoot ".env")

# --- Install dependencies ---
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow

Write-Host "  uv sync (repo root — Manim agents workspace)..."
Push-Location $RepoRoot
uv sync
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

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

# --- Done ---
Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Add API keys to env files:"
Write-Host "     apps/ui/aos/backend/.env          -> OPENROUTER_API_KEY"
Write-Host "     apps/agents/.env                  -> OPENROUTER_API_KEY"
Write-Host ""
Write-Host "2. Pull the local Manim coder model (Ollama):"
Write-Host "     ollama pull huggingface.co/nabin2004/AOS-gemma4-31b-manim-gguf:Q4_K_M"
Write-Host ""
Write-Host "3. Start the UI stack (requires WSL2 or Git Bash for make):"
Write-Host "     cd apps/ui/aos"
Write-Host "     make bootstrap          # first time"
Write-Host "     cd frontend && bun dev  # or: npm run dev"
Write-Host ""
Write-Host "4. Run prompt-to-Manim (separate terminal):"
Write-Host "     cd apps/agents"
Write-Host "     uv run python cli.py animate `"Draw a circle`""
Write-Host ""
Write-Host "Full guide: apps/ui/aos/LOCAL_DEV.md"
Write-Host ""
