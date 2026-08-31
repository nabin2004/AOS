# EduClaw

Coding harness for Manim agents: Pydantic AI loop, Dagestan memory, Docker sandbox, permissions, skills, `ty` diagnostics, Rich TUI, optional Kitaru durability, and Logfire spans.

See [docs/agent.md](docs/agent.md) and [docs/harness.md](docs/harness.md).

## Install

```bash
uv sync --package educlaw --extra dev
# durable extra (KitaruAgent via kitaru-pydantic-ai):
uv sync --package educlaw --extra durable --extra dev
```

## Environment

| Variable | Purpose |
|----------|---------|
| `EDUCLAW_MODEL` | Pydantic AI model string (default `openai:gpt-4o-mini`) |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `EDUCLAW_API_KEY` | Provider key |
| `EDUCLAW_HARNESS_HOME` | Graph + harness data (default `<cwd>/.aos`) |
| `EDUCLAW_CONTEXT_WINDOW` | Override context-window tokens |
| `EDUCLAW_COMPACTION_THRESHOLD` | Fraction that triggers compaction (default `0.7`) |
| `EDUCLAW_MEMORY_STUB` | `1` for Dagestan stub extraction |
| `EDUCLAW_TEST_MODEL` | `1` for Pydantic AI `TestModel` |
| `EDUCLAW_PERMISSION_MODE` | `default` / `edit` / `auto` |
| `EDUCLAW_MANIM_IMAGE` | default `manimcommunity/manim:stable` |
| `EDUCLAW_DOCKER_USER` | `uid:gid` for Linux volume writes |
| `EDUCLAW_MANIM_QUALITY` | `l` / `m` / `h` / `k` |
| `EDUCLAW_KITARU` | `1` to wrap the agent with `KitaruAgent` |
| `EDUCLAW_LOGFIRE` / `LOGFIRE_TOKEN` | instrument Pydantic AI |

## Run

```bash
# Interactive REPL harness
educlaw
educlaw repl

# Rich Full-terminal TUI
educlaw tui

# Single-shot execution
educlaw run "What should a first Manim scene include?" --yes
educlaw --headless --yes -p "What should a first Manim scene include?"
educlaw run "Render a circle scene" --durable --yes

# Diagnostics & Configuration
educlaw doctor
educlaw config

# Dagestan Memory Inspection & Curation
educlaw memory show
educlaw memory query "preferences"
educlaw memory curate
```

Offline: `EDUCLAW_TEST_MODEL=1 EDUCLAW_MEMORY_STUB=1` or `educlaw --model test --yes`.

### Slash commands

`/compact` `/clear` `/memory` `/curate` `/steer` `/abort` `/yes` `/no` `/help` `/quit`

## Tests and smoke

```bash
pytest
python -m evals.smoke
# Run Audio Test Suite (Pocket TTS, DSM Aligner, Server Status):
python -m evals.audio_eval
```

Live Docker render and live Kitaru replay need Docker and `educlaw[durable]` respectively.

