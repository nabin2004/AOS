# AOS

## Setup

```bash
uv sync
cp apps/agents/.env.example apps/agents/.env   # then fill in OPENROUTER_API_KEY
```

See [`apps/agents/README.md`](apps/agents/README.md#model-configuration) for
local/cloud model switching (`AOS_MODEL_PROFILE`, `OLLAMA_BASE_URL`).

## Run the full lecture pipeline

The pipeline (`apps/agents/graph.py`) is a `pydantic_graph` graph:
`Classify → PlanLecture → MakeStoryboard → CreateScenes → AddBeats →
AddNarration → Validate ⇄ Repair → Narrate → Inspect`. `apps/agents/cli.py`
(Animus) wraps it in a runnable CLI:

```bash
cd apps/agents
uv run python cli.py generate "Explain the derivative of x squared"
```

Prints an intro effect (`--no-banner` to skip it), streams each node as the
graph advances (`-> Classify`, `-> PlanLecture`, ...), then prints the
inspector's summary and any outstanding validation issues. `--max-repairs N`
caps the Validate/Repair retry loop (default 3).

Each run gets its own directory under `apps/agents/workspace/runs/{timestamp}-{slug}/`
containing every intermediate step's output/messages, plus the final
pipeline artifacts:

| File/dir | Produced by | Contents |
| --- | --- | --- |
| `lecture.py` | `Inspect` (via `tools/compile.py`) | Compiled Manim source, one class per scene |
| `lecture_ir.json` | `Inspect` | The full `LectureIR` document |
| `audio/{SceneClass}_{beat:02d}.wav` | `Narrate` (via `tools/narrate.py`) | Per-beat narration audio, synthesized from `Beat.narration.text` with Pocket TTS |
| `audio/{SceneClass}_track.wav` | `tools/assemble.py` | IR-timed narration track per scene (silence during animation, speech during hold) |
| `videos/{SceneClass}_with_audio.mp4` | `tools/assemble.py` | Per-scene Manim render muxed with narration |
| `lecture_final.mp4` | `tools/pipeline.py` `run_full_pipeline` | Full lecture — all scenes concatenated in storyboard order |
| `render_results.json` | `Inspect` / `run_full_pipeline` (via `tools/render.py`) | Per-scene `{success, output_path, log}` from the Docker/Manim render |
| `pipeline_result.json` | `tools/assemble.py` | Mux/concat summary (scene paths, skipped scenes) |

### Prerequisite: Docker Desktop and ffmpeg

The render step runs every scene through `manimcommunity/manim` in Docker
(`tools/render.py`). **Docker Desktop must be running** before you render.

The mux/concat step (`tools/assemble.py`) requires **ffmpeg** (and `ffprobe`)
on your PATH to combine narration audio with rendered video and stitch scenes
into `lecture_final.mp4`.

Pull the Manim image once ahead of time:

```bash
docker pull manimcommunity/manim
```

### Deterministic video pipeline (no agents)

After `lecture_ir.json` and `audio/` exist in a workspace, re-render and
assemble the final video without re-running the agent graph:

```bash
cd apps/agents
uv run python assemble_runner.py runs/final_final_graph
```

Or call `run_full_pipeline(lecture_ir, ToolDeps(workspace_dir=...))` from
`tools/pipeline.py` — compile → narrate → Docker render → mux →
`lecture_final.mp4`.

### Narration audio

`Narrate` uses `apps/audio_service`'s `Narrator` (Kyutai Pocket TTS, CPU,
~6x real-time) to synthesize one `.wav` per beat that has narration text. The
model is loaded once per process (lazily, on first use) and reused across
scenes. If `pocket-tts`/`torch` aren't installed or synthesis throws for any
reason, `Narrate` logs the error and the pipeline continues on to `Inspect`
rather than failing the whole run — narration is best-effort, not a gate.

### Coder agent voiceover

The coder agent can also embed narration directly in Manim scenes via
[Manim Voiceover](https://voiceover.manim.community/en/stable/) and our local
`AOSSpeechService` (Pocket TTS). See
[`apps/agents/docs/MANIM_VOICEOVER.md`](apps/agents/docs/MANIM_VOICEOVER.md).

> **Known issue:** with the default `openrouter:openai/gpt-4o-mini` model,
> `AddBeats` (`list[Beat]` structured output) can fail with `Grammar error:
> Pointer '/$defs/Beat' does not exist` — some free-tier providers OpenRouter
> routes to can't resolve nested `$ref`/`$defs` JSON schemas. Point the
> agents at a model that supports structured output reliably (e.g. an
> OpenAI or Anthropic model) if you hit this.

`apps/agents/main.py` is stale scratch code (predates the per-agent modules
`classifier_agent.py`, `lecture_planner.py`, etc.) and does not run — use
`graph.py` instead.

## CLI

Pydantic AI ships a CLI for chatting with individual agents. In this
project's venv its console-script is installed as `pai` (the tool still
identifies itself as "clai" internally, so treat `pai` and `clai` as the same
program):

```bash
cd apps/agents
uv run pai --agent classifier_agent:classifier_agent "I want to learn about eigenvalues"
```

Any `module:variable` pointing at an `Agent` instance works — e.g.
`lecture_planner:lecture_planner_agent`, `validation_agent:validation_agent`.
Omit the prompt to start an interactive session (`/exit`, `/markdown`,
`/multiline`, `/cp` are available as special commands there).

```bash
uv run pai --list-models          # list all available models
uv run pai -m anthropic:claude-sonnet-4-6 "..."   # one-shot, no custom agent
```

## Web Chat UI

```bash
cd apps/agents
uv run pai web --agent classifier_agent:classifier_agent
```

Starts a browser chat UI at `http://127.0.0.1:7932` (override with `--host`/
`--port`). Without `--agent`, `-m` selects which model(s) are offered
(first one is the default):

```bash
uv run pai web -m openai:gpt-5 -m anthropic:claude-sonnet-4-6
```

Run `uv run pai web --help` for the full option list (`--tool`,
`--instructions`, `--html-source`, etc.).

## Packages

- [`apps/agents/prompt_optimization/`](apps/agents/prompt_optimization/README.md) — prompts for every IR layer, GEPA optimizer, DSPy integration
