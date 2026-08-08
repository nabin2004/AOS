# Local Development Setup

Guide for running the **AOS web UI** and the **prompt-to-Manim agents pipeline** on your machine. Chat can enqueue Manim jobs via Celery; compiled MP4s land in MinIO and play in chat with Video.js.

---

## Architecture

```mermaid
flowchart TB
    subgraph uiStack [UI Stack — apps/ui/aos]
        FE[Next.js frontend :3000]
        BE[FastAPI backend :8000]
        CW[Celery worker]
        PG[(PostgreSQL)]
        RD[(Redis)]
        MNIO[(MinIO :9010)]
        FE --> BE
        BE --> PG
        BE --> RD
        CW --> RD
        CW --> MNIO
        CW --> PG
    end

    subgraph manimStack [Manim Stack — apps/agents]
        CLI["cli.py animate|generate --json"]
        OLL[Ollama :11434]
        OR[OpenRouter API]
        MANIM[Manim compile]
        CLI --> OLL
        CLI --> OR
        CLI --> MANIM
    end

    BE -->|"WS video_mode"| CW
    CW -->|"subprocess uv run"| CLI
    FE -->|"Video.js /api/videos/id/stream"| BE
```

| Stack | Location | Purpose |
|-------|----------|---------|
| **UI** | `apps/ui/aos` | Web app — chat, auth, RAG, billing, video jobs |
| **Manim** | `apps/agents` | Prompt → Manim code → compiled video |

### Chat → video flow

1. In chat **Settings**, set **Video generation** to **Animate** or **Lecture**.
2. Send a prompt — the WebSocket turn skips the normal assistant and enqueues `generate_video_task`.
3. Celery runs `uv run python cli.py animate|generate "…" --json --no-banner` under `apps/agents`.
4. The worker uploads the MP4 to MinIO bucket `aos-videos` and stores `minio_key` on `video_generations`.
5. Chat receives `video_status` / `tool_result` and renders the player via `/api/videos/{id}/stream`.

**Required for video jobs:** Docker for Redis / MinIO / API (`make dev` or `.\scripts\dev-refresh.ps1`), plus **host Celery** (auto-started by `dev-refresh.ps1` — Docker `celery_worker` cannot run `uv`/Manim). Also `OPENROUTER_API_KEY` or BYOK LLM fields. For **Lecture**, also Docker Manim + ffmpeg.

Why host Celery: the Compose image has no `uv`, mounts agents read-only, and lacks Manim. Profile `docker-celery` is advanced-only.

```powershell
cd apps\ui\aos
.\scripts\dev-refresh.ps1              # infra + API + HOST Celery
.\scripts\dev-refresh.ps1 -Rebuild     # Dockerfile / deps changed
.\scripts\dev-refresh.ps1 -AgentsOnly  # restart host Celery only
.\scripts\dev-refresh.ps1 -Logs        # host celery log + minio
.\scripts\diagnose-animate.ps1         # hop-by-hop PASS/FAIL
```

Host worker uses `AGENTS_DIR` → `apps/agents`, broker `redis://localhost:6379/0`, `S3_VIDEO_ENDPOINT=http://localhost:9010`. Log: `apps/ui/aos/.local/celery-worker.log`.

**Day-to-day Animate checklist**

1. `.\scripts\dev-refresh.ps1` — Postgres, Redis, MinIO, API, **host Celery**
2. Frontend: `cd frontend && bun dev`
3. Confirm: `.\scripts\diagnose-animate.ps1` (celery inspect PASS) or Flower http://localhost:5555
4. Chat Controls → Video generation → Animate → send a short prompt
5. Expect: Queued → Starting / Classifying… → completed player; re-run diagnose → `status=completed` + `minio_key`

If Queued forever: diagnose script / `.local/celery-worker.log` — ensure Docker `celery_worker` is **stopped** so it does not steal jobs without being able to run agents.

### Animate E2E debug

| Hop | Success signal |
|-----|----------------|
| Enqueue | `video_generations` row `pending` → `running`; Flower / host log `generate_video_task` |
| Agents | Host log: `Running agents CLI` / `-> Classifier`… |
| Compile | `apps/agents/workspace/coder_runs/...` with mp4 |
| MinIO | `minio_key` set; console `:9011` bucket `aos-videos` |
| UI | Completed player via `/api/videos/{id}/stream` |

Run `.\scripts\diagnose-animate.ps1` after a failed Animate — `error_message` on the latest DB row names the hop.

### Animate smoke test (OpenRouter + `agent_graph.py`)

1. Set `OPENROUTER_API_KEY` in `apps/ui/aos/backend/.env` (and optionally `apps/agents/.env`).
2. `.\scripts\dev-refresh.ps1` + frontend.
3. In chat **Settings**, set **Video generation** to **Animate**.
4. Send a short prompt (e.g. `draw a bouncing ball`).
5. Expect: tool card → pending/running → completed player; `.\scripts\diagnose-animate.ps1` shows completed + minio_key.

CLI equivalent (no UI):

```bash
cd apps/agents
# Ensure OPENROUTER_API_KEY is set; cloud profile uses OpenRouter for coder too
set AOS_MODEL_PROFILE=cloud   # PowerShell: $env:AOS_MODEL_PROFILE="cloud"
uv run python cli.py animate "draw a bouncing ball" --json --no-banner
```

If compile fails, pull the Manim Docker image (`docker pull manimcommunity/manim`) — the coder still needs a working Manim compile path.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| **Docker Desktop** | 24+ | [docker.com/get-docker](https://docs.docker.com/get-docker/) |
| **uv** | latest | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| **bun** or **npm** | bun 1.x / node 18+ | [bun.sh](https://bun.sh) or [nodejs.org](https://nodejs.org) |
| **Ollama** | latest (optional — only for `hybrid`/`local` Manim profiles) | [ollama.com](https://ollama.com) |
| **Make** (optional) | GNU Make | macOS/Linux, or WSL2 / Git Bash on Windows |

### Windows notes

- **Preferred:** PowerShell + [`scripts/setup-local.ps1`](scripts/setup-local.ps1) — full UI bootstrap (deps, Docker, migrations, admin seed) with **no Make/WSL required**.
- Docker Desktop must be running before the script starts the UI stack.
- Make targets still work in **WSL2** or **Git Bash** if you prefer that workflow.
- Frontend: PowerShell + `npm run dev` (or `bun dev` if bun works on your machine).

### Optional (full lecture-to-video pipeline)

| Tool | Needed for |
|------|-----------|
| LaTeX (MiKTeX / TeX Live) | `MathTex` / `Tex` scenes |
| ffmpeg | Final video assembly (`lecture_final.mp4`) |
| Docker + `manimcommunity/manim` image | Full IR pipeline render step |

For UI **Animate** via OpenRouter only, Ollama is not required (`AOS_MODEL_PROFILE=cloud`). For fast local coder iteration with `hybrid`/`local`, use **Ollama + OpenRouter + uv sync**.

---

## First-time setup

### Option A — PowerShell bootstrap (Windows)

```powershell
cd apps\ui\aos
.\scripts\setup-local.ps1
```

This is the Windows equivalent of `make bootstrap`. It:

1. Checks prerequisites (Docker daemon, uv, npm/bun)
2. Creates env files if missing
3. Installs Python/frontend dependencies
4. Builds and starts `docker-compose.dev.yml`
5. Waits for Postgres, applies migrations, restarts the API, seeds `admin@example.com`

Switches:

| Switch | Effect |
|--------|--------|
| `-SkipStack` | Deps + env only (do not start Docker) |
| `-SkipAgents` | UI only — skip repo-root `uv sync` and agents `.env` |

Then start the frontend:

```powershell
cd frontend
npm run dev          # preferred on Windows if bun is broken/missing
# or: bun dev
```

### Option B — Manual setup

#### 1. Clone and install dependencies

```bash
# From repo root
cd C:\Users\nabin\Desktop\myall\AOS
uv sync

# UI backend (separate Python env)
cd apps/ui/aos/backend
uv sync

# UI frontend
cd ../frontend
bun install          # preferred
# or: npm install --legacy-peer-deps
```

#### 2. Create environment files

```bash
cp apps/ui/aos/backend/.env.example   apps/ui/aos/backend/.env
cp apps/ui/aos/frontend/.env.example  apps/ui/aos/frontend/.env.local
cp apps/agents/.env.example           apps/agents/.env
```

#### 3. Add API keys

**UI backend** — edit `apps/ui/aos/backend/.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-...    # required for chat + Celery Animate (passed to agents CLI)
# Optional: absolute path if auto-detect fails
# AGENTS_DIR=C:/Users/you/Desktop/myall/AOS/apps/agents
S3_VIDEO_ENDPOINT=http://localhost:9010
```

**Manim agents** — edit `apps/agents/.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-...
AOS_MODEL_PROFILE=cloud            # recommended for UI Animate (no Ollama)
# For hybrid local coder instead:
# AOS_MODEL_PROFILE=hybrid
# OLLAMA_BASE_URL=http://localhost:11434/v1
```

Get an OpenRouter key at [openrouter.ai/keys](https://openrouter.ai/keys).

#### 4. Pull the local Manim coder model (optional — hybrid/local only)

```bash
ollama pull huggingface.co/nabin2004/AOS-gemma4-31b-manim-gguf:Q4_K_M
```

Verify:

```bash
curl http://localhost:11434/v1/models
```

---

## Running the UI stack

### Windows (PowerShell)

First time (or re-bootstrap):

```powershell
cd apps\ui\aos
.\scripts\setup-local.ps1
cd frontend
npm run dev
```

Day-to-day (stack already bootstrapped):

```powershell
cd apps\ui\aos
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml logs -f   # optional
# separate terminal:
cd frontend
npm run dev
```

Stop the stack:

```powershell
docker compose -f docker-compose.dev.yml down
```

### macOS / Linux / WSL (Make)

```bash
cd apps/ui/aos
make bootstrap    # first time: Docker up + migrations + admin seed
```

Day-to-day:

```bash
make dev                          # start backend + Postgres + Redis + Milvus
cd frontend && bun dev            # http://localhost:3000
# or: npm run dev
```

### Access URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Admin panel | http://localhost:8000/admin |

Default admin (after setup seed): `admin@example.com` / `admin123`

### Useful Make targets (bash / WSL / Git Bash)

```bash
make dev           # start dev stack (idempotent)
make seed          # create admin user (one-shot)
make dev-down      # stop all services
make dev-logs      # tail container logs
make dev-rebuild   # rebuild backend image after pyproject.toml change
```

### Backend on host (for IDE debugging)

```bash
make install
docker compose -f docker-compose.dev.yml up -d db redis milvus etcd minio
make db-upgrade
make run           # uvicorn with --reload on :8000
```

PowerShell equivalent:

```powershell
cd apps\ui\aos\backend
uv sync
cd ..
docker compose -f docker-compose.dev.yml up -d db redis milvus etcd minio
docker compose -f docker-compose.dev.yml exec -T app aos db upgrade
# or host-side: cd backend; uv run aos db upgrade
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

---

## Running prompt-to-Manim

The Manim pipeline lives in `apps/agents` and **is connected to the web UI** via Celery (`generate_video_task`). Prefer Chat → Animate for end-to-end; use the CLI below for isolated debugging.

### CLI (recommended for pipeline debugging)

```bash
cd apps/agents
uv run python cli.py animate "Explain eigenvectors in 2D with a unit circle animation"
```

Optional flags:

- `--fast` — skip narration synthesis
- `--no-banner` — skip intro animation

Output directory:

```
apps/agents/workspace/coder_runs/{timestamp}-{slug}/
├── scene.py          # generated Manim source
├── manifest.json     # scene metadata
├── media/            # compiled .mp4
├── audio/            # narration (if enabled)
└── logs/compile.log
```

### Interactive web UI

```bash
cd apps/agents
uv run pai web --agent agent_graph:animation_agent
# Opens http://127.0.0.1:7932
```

Code agent only:

```bash
uv run pai web --agent coder_agent:coder_agent
```

### Model profiles

Set in `apps/agents/.env`:

| Profile | Classifier / planner | Coder |
|---------|---------------------|-------|
| `cloud` (recommended for UI Animate) | OpenRouter | OpenRouter |
| `hybrid` | OpenRouter | Local Ollama |
| `local` | Ollama | Ollama |

See [apps/agents/README.md](../../agents/README.md) for per-role overrides and token limits.

### Full lecture pipeline (optional)

Generates a complete lecture with narration and final video:

```bash
cd apps/agents
uv run python cli.py generate "Explain the derivative of x squared"
```

Requires Docker running and the Manim image:

```bash
docker pull manimcommunity/manim
```

Output: `apps/agents/workspace/runs/{timestamp}-{slug}/lecture_final.mp4`

---

## Verification checklist

Run these after setup to confirm everything works:

| Check | Command / URL | Expected |
|-------|--------------|----------|
| Docker running | `docker ps` | Lists UI stack containers (after setup / `make dev`) |
| UI API healthy | `curl http://127.0.0.1:8000/api/v1/health` (or browser) | `{"status":"ok"}` |
| UI frontend | http://localhost:3000 | Marketing / login loads |
| Ollama running (optional) | `curl http://localhost:11434/v1/models` | Manim GGUF listed when using `hybrid`/`local` |
| Prompt-to-Manim (OpenRouter) | `AOS_MODEL_PROFILE=cloud uv run python cli.py animate "draw a circle" --json --no-banner` | JSON `VideoArtifact` with `ok` / `video_path` |
| Manim compile | Check `coder_runs/.../media/` | `.mp4` file present |
| UI Animate | Chat Settings → Animate → send prompt | Prompt on tool card + Video.js after MinIO upload |

---

## Troubleshooting

### `make` not found on Windows

You do not need Make. Use the PowerShell bootstrap:

```powershell
cd apps\ui\aos
.\scripts\setup-local.ps1
```

Or use WSL2 / Git Bash for `make` targets. Manual compose (migrate only — prefer the script for seed + health waits):

```powershell
cd apps\ui\aos
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml exec -T app aos db upgrade
docker compose -f docker-compose.dev.yml restart app
```

### Docker Desktop not running

`setup-local.ps1` requires a live Docker daemon (`docker info`). Start Docker Desktop, wait until it is idle/ready, then re-run the script.

### API unhealthy after first boot / missing tables

If the API crashed before migrations (e.g. `relation "channel_bots" does not exist`), re-run:

```powershell
.\scripts\setup-local.ps1
```

The script applies migrations and restarts `app` so health can recover. Or manually: `aos db upgrade` then `docker compose -f docker-compose.dev.yml restart app`.

### Port 8000 already in use

The UI backend and vLLM (if running) both default to port 8000. Stop the conflicting service or change the UI port in `docker-compose.dev.yml`.

### `bun` not found or fails on Windows

Install from [bun.sh](https://bun.sh), or use npm (recommended fallback):

```powershell
cd apps\ui\aos\frontend
npm install --legacy-peer-deps
npm run dev
```

`setup-local.ps1` automatically falls back to npm if `bun --version` does not run.

### Ollama context / token limit errors

Lower output caps in `apps/agents/.env`:

```env
AOS_CODER_MAX_TOKENS=1024
AOS_OLLAMA_NUM_CTX=16384
```

Or raise Ollama's context when starting the server:

```bash
OLLAMA_CONTEXT_LENGTH=16384 ollama serve
```

### Missing LaTeX for MathTex scenes

Install MiKTeX (Windows) or TeX Live (WSL/Linux). Manim needs `standalone.cls` and related packages for math rendering.

### Manim compile fails silently

Check the compile log:

```
apps/agents/workspace/coder_runs/{run}/logs/compile.log
```

Common causes: missing LaTeX, invalid scene class name, syntax error in generated code.

### Docker services won't start

PowerShell:

```powershell
cd apps\ui\aos
docker compose -f docker-compose.dev.yml down -v --remove-orphans   # WARNING: deletes local DB data
.\scripts\setup-local.ps1
```

Make (WSL / Git Bash):

```bash
make dev-down
make docker-clean    # WARNING: deletes local DB data
make bootstrap
```

### OpenRouter / model errors

Ensure `OPENROUTER_API_KEY` is set in both:

- `apps/ui/aos/backend/.env`
- `apps/agents/.env`

For agents, use `AOS_MODEL_PROFILE=cloud` for OpenRouter-only runs. `hybrid` needs both OpenRouter and Ollama. Celery Animate jobs force `cloud` and inject the backend `OPENROUTER_API_KEY`.

---

## Development workflow

Typical day developing prompt-to-Manim animations via the UI:

1. **Terminal 1** — Docker infra/API + **host Celery** (one script) and frontend:
   ```powershell
   cd apps\ui\aos
   .\scripts\dev-refresh.ps1
   .\scripts\diagnose-animate.ps1   # optional: hop check
   cd frontend; bun dev
   ```

2. **Optional Terminal 2** — Manim CLI for isolated debugging:
   ```bash
   cd apps/agents
   uv run python cli.py animate "your prompt here"
   ```

3. **Inspect output** — chat player, Flower `:5555`, MinIO `:9011`, or `workspace/coder_runs/{latest}/`.

4. **Iterate** — adjust prompts or agent code. After backend/worker edits, re-run `.\scripts\dev-refresh.ps1` (or `-AgentsOnly`).

For agent-only work, skip the UI stack and use `cli.py animate` or `pai web`.

---

## Related docs

| Doc | Contents |
|-----|----------|
| [README.md](README.md) | UI app overview and quick start |
| [ENV_VARS.md](ENV_VARS.md) | UI backend env var reference |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Code style and testing |
| [apps/agents/README.md](../../agents/README.md) | Manim model config, SFT, render perf |
| [Root README.md](../../../README.md) | Full lecture pipeline docs |
