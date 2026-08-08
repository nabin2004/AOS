# AOS Agents

> **Setting up local development?** See [apps/ui/aos/LOCAL_DEV.md](../ui/aos/LOCAL_DEV.md) for the full guide covering both the web UI and this Manim pipeline.

## Model configuration

Pipeline agents read model selection from [`llm_config.py`](llm_config.py) and
[`apps/agents/.env`](.env.example). Copy `.env.example` → `.env` and set
`OPENROUTER_API_KEY` (cloud) and `OLLAMA_BASE_URL` (local).

### Profiles

Set `AOS_MODEL_PROFILE` to switch the whole animation pipeline at once:

| Profile | Classifier / planner / orchestrator | Coder |
| --- | --- | --- |
| `cloud` (recommended for UI Animate) | OpenRouter (`gpt-4o-mini`) | OpenRouter |
| `hybrid` | OpenRouter (`gpt-4o-mini`) | Local Ollama (fine-tuned Gemma) |
| `local` | Ollama | Ollama |

```bash
# Fully cloud (no Ollama) — what the UI Celery Animate worker forces
export AOS_MODEL_PROFILE=cloud

# Cloud planning + local Manim coder
export AOS_MODEL_PROFILE=hybrid
export OLLAMA_BASE_URL=http://localhost:11434/v1

# Fully local (requires Ollama + pulled GGUF model)
export AOS_MODEL_PROFILE=local
```

### Per-role overrides

Optional env vars beat the profile for a single agent:

- `AOS_CLASSIFIER_MODEL`
- `AOS_PLANNER_MODEL`
- `AOS_CODER_MODEL`
- `AOS_ANIMATION_MODEL`

Example — cloud coder with Kimi:

```bash
export AOS_CODER_MODEL=openrouter:moonshotai/kimi-k2.5
```

### Local model token limits

Ollama models default to `num_ctx=16384` (see
[`apps/sft/templates/Modelfile.gemma4-31b-manim`](../sft/templates/Modelfile.gemma4-31b-manim)).
The agents pipeline also passes `options.num_ctx` on every Ollama request via
`AOS_OLLAMA_NUM_CTX` (default `16384`) so runtime context is not silently capped
by VRAM-based defaults (e.g. 4096 on CPU).

The coder's system prompt + tools consume much of that budget, so local models
get an explicit output cap:

- `AOS_CODER_MAX_TOKENS` (default `2048`)
- `AOS_MAX_TOKENS` (default `2048`) for other local roles
- `AOS_OLLAMA_NUM_CTX` (default `16384`) for the context window
- `AOS_OLLAMA_THINKING` (default `0`) — disable Gemma reasoning/thinking on Ollama
  to keep multi-turn CodeMode retries from filling the context window. The coder also
  stops echoing prior `reasoning` fields back to the model on later turns.

Keep `prompt + max_tokens <= num_ctx`. If you still hit token-limit errors,
lower output caps (e.g. `1024`) or raise `AOS_OLLAMA_NUM_CTX` / Modelfile
`num_ctx` and recreate the Ollama model. As a server-side fallback you can also
set `OLLAMA_CONTEXT_LENGTH=16384` when starting `ollama serve`.

## Web UI

Chat with the full pipeline (classify → lecture plan → Manim code) or the code agent alone:

```bash
cd apps/agents
uv run pai web --agent agent_graph:animation_agent   # full graph
uv run pai web --agent coder_agent:coder_agent         # code agent only
```

`pai web` uses streaming (`run_stream_events`), which DBOS durable workflows do **not** support. Keep the web UI on plain agents (default).

Agent compiles default to Manim `-ql` (fast). SFT uses code/tool traces, not video pixels. For a sharper preview: `export AOS_MANIM_QUALITY=h`.

## Durable execution (DBOS + Logfire)

For graph/batch runs, enable DBOS so classifier → planner → coder can resume after crashes. Model requests and `@DBOS.step` tools (manim write/compile/read/narration) are checkpointed. DBOS OTLP spans join existing Pydantic AI Logfire traces (`enable_otlp=True`).

```bash
cd apps/agents

# durable graph/batch (SQLite under workspace/dbos_sys.sqlite)
export AOS_DBOS=1
uv run python -c "import asyncio; from agent_graph import run_pipeline; print(asyncio.run(run_pipeline('Teach me eigenvalues')))"

# optional Postgres instead of SQLite
export DBOS_SYSTEM_DATABASE_URL=postgresql://user:pass@localhost/dbos

# pai web stays non-durable (streaming)
uv run pai web --agent agent_graph:animation_agent
```

## SFT data collection (Code Agent)

Collect tool-calling traces from the Code Agent (`coder_agent.py` via `agent_graph.py`) for LLM finetuning. Training data is captured at the **application layer** into local JSONL — no Logfire parsing required.

### Prerequisites

- `apps/agents/.env` with OpenRouter (or configured model) API keys
- Optional: Logfire **write** token — production observability only (`coder_agent.py` / `agent_graph.py`)
- Optional (Logfire export path): `export_traces/.env` with `LOGFIRE_READ_TOKEN`

### Workflow

```text
topics.txt  →  generate_prompts.py  →  prompts.jsonl
                                              ↓
                                    collect_traces.py
                                              ↓
              batch_runs.jsonl + workspace/coder_runs/*/traces/
              + training_data/trajectories.jsonl
                                              ↓
                              export_local_sft.py  →  coder_sft/tool_trace*.jsonl
                                              ↓
                              upload_dataset.py  →  Hugging Face (nabin2004/AOS-Trajectories)

(Logfire remains optional for prod debugging; export_coder_sft.py is secondary)
```

**Step 1 — prompts (optional)**

Generate synthetic user requests from topic seeds:

```bash
cd apps/agents
uv run python sft_data_gen/generate_prompts.py \
  --num 500 \
  --output sft_data_gen/prompts.jsonl \
  --topics sft_data_gen/topics.txt
```

`topics.txt` seeds the prompt generator; it is **not** passed directly to the coding agent.

**Step 2 — collect traces**

Recommended fast batch (disables Logfire/DBOS overhead, skips narration; use concurrency 2–4):

```bash
uv run python sft_data_gen/collect_traces.py \
  --limit 200 \
  --fast \
  --convert-after-local \
  --resume \
  --concurrency 4
```

Scale to multi-thousand compile-ok trajectories (~5k target): expand prompts first, then run waves via `sft_data_gen/run_waves.sh` and monitor with `sft_data_gen/status.py`. Details in [`sft_data_gen/README.md`](sft_data_gen/README.md).

Standard run (classify → plan → coder):

```bash
uv run python sft_data_gen/collect_traces.py \
  --prompts sft_data_gen/prompts.jsonl \
  --limit 50 \
  --resume
```

Useful flags:

- `--fast` — disable Logfire + DBOS, skip narration, preload RAG index (recommended for batch SFT)
- `--concurrency 2` — parallel runs (default: 2; use `1` if rate-limited)
- `--dry-run --limit 3` — preview selected prompts without API calls
- `--indices 0,3,7` — run specific prompt indices
- `--convert-after-local` — run `export_local_sft.py` when the batch finishes (recommended)
- `--export-after` — run Logfire export (`export_coder_sft.py`) when the batch finishes

Batch env vars (set automatically by `--fast`, or override manually):

- `AOS_LOGFIRE=0` — no OTLP export (avoids timeout stalls during batch)
- `AOS_DBOS=0` — plain agents, no durable checkpointing
- `AOS_SFT_BATCH=1` — coder skips `synthesize_narration`

Each run writes:

```text
workspace/coder_runs/{timestamp}-{slug}/
  scene.py, manifest.json, run_result.json
  logs/compile.log, audio/*.wav, media/
  traces/messages.json      # pydantic-ai message history
  traces/trajectory.json    # structured SFT record
  traces/meta.json
training_data/trajectories.jsonl   # append-only global bank
```

Progress is logged to `sft_data_gen/batch_runs.jsonl` (resume skips indices with `"status": "ok"`).

**Step 3 — export SFT JSONL (local, no Logfire)**

Convert accumulated trajectories to training format:

```bash
uv run python export_local_sft.py
```

- Default input: `training_data/trajectories.jsonl`
- `--scan-workspace` — rebuild from `workspace/coder_runs/*/traces/trajectory.json`
- Output: `export_traces/coder_sft/`
- Prefer **`tool_trace*.jsonl`** for tool-use / CodeMode finetuning
- `final_answer*.jsonl` is a text-only collapse (secondary)
- Dedup: one row per `user_prompt`; keeps the **shortest successful** trajectory

**Step 4 — publish to Hugging Face (optional)**

Upload trajectories and tool_trace exports to the public dataset:

```bash
export HF_TOKEN=hf_...   # write token; never commit
cd ../sft
uv run python upload_dataset.py
```

Dataset: [nabin2004/AOS-Trajectories](https://huggingface.co/datasets/nabin2004/AOS-Trajectories). Phase 1 SFT (`apps/sft/run.py`) loads from this Hub repo by default.

**Optional — Logfire export**

For spans already sent to Logfire (production traffic):

```bash
uv run python export_coder_sft.py --days 30
```

Export-only or convert-only:

```bash
uv run python export_coder_sft.py --days 7 --export-only
uv run python export_coder_sft.py --skip-export --input export_traces/coder_traces.jsonl
```

### Quality tips

- Start with `--limit 10` before large batches (each run = multiple LLM calls + Manim compile).
- Filter on `"compile_ok": true` in `batch_runs.jsonl` or `run_result.json` for higher-quality SFT rows.
- Loop caps per run: `request_limit=20`, `tool_calls_limit=40` (see `coder_run.py`).
- Logfire = live debugging; `training_data/trajectories.jsonl` = local training gold; [nabin2004/AOS-Trajectories](https://huggingface.co/datasets/nabin2004/AOS-Trajectories) = published Hub copy.
- More detail: [`sft_data_gen/README.md`](sft_data_gen/README.md)

---

## Scene content: `content` vs `params`

`SceneObject` (`packages/ir/src/ir/manim_ir.py`) has a dedicated `content: str`
field for the literal text/LaTeX shown by `math_tex`/`text` entities. It used
to live in the free-form `params` dict (`params={"tex": "..."}`), but
open-ended `dict[str, Any]` fields are unreliable for structured-output
models — nothing in the JSON schema tells the model the key `"tex"` is
expected, so smaller models (e.g. `gemini-2.5-flash-lite`) would routinely
leave it out, compiling to a blank `MathTex("")`. A declared string field
gets filled far more consistently.

- `scene_planner_agent`'s output validator (`_require_scene_per_step` in
  `scene_planner_agent.py`) rejects any `math_tex`/`text` object with empty
  `content` and retries with feedback — cheap to fix there vs. downstream
  where there's no scene graph left to repair against.
- `tools/compile.py` reads `obj.content` first, falling back to the legacy
  `params["tex"]`/`params["text"]` for any already-generated IR.
- `SceneObject.model_config` is `extra="allow"` (was `extra="forbid"`) — a
  stopgap so a model that drifts slightly (extra keys, minor shape
  mismatches) doesn't hard-fail into a `ModelRetry` loop. A tighter,
  better-fitted schema is the real long-term fix.

## Manim render performance

Rendering is the slowest part of the pipeline (`tools/render.py`, Docker +
`manimcommunity/manim`). These are the levers that actually move wall-clock
time in production, roughly in order of impact.

### Implemented in `tools/render.py`

- **Persistent container, `docker exec` instead of `docker run`.**
  `docker run --rm` pays for a fresh container filesystem/network namespace
  on every call; for short scenes that startup cost can exceed the render
  itself. `render_manim_scene`/`render_manim_scenes` keep one idle container
  per workspace alive (`tail -f /dev/null`, named by a hash of the mounted
  volume) and `docker exec` into it. Disable with
  `ToolDeps(persistent_container=False)` if you need fully isolated one-off
  runs.
- **Parallel scene rendering.** Manim/Cairo rendering is single-threaded per
  scene. `render_manim_scenes` fans independent scenes in a lecture out
  across a `ThreadPoolExecutor` (bounded by CPU count), each as its own
  `manim` process via `docker exec`, so a multi-scene lecture scales
  ~linearly with cores instead of rendering scene-by-scene.
- **`-v WARNING` logging.** Cuts per-frame progress-bar/log chatter, which
  keeps stdout small (cheaper `_parse_output_path` regex work) and avoids
  needless I/O in the container.
- **Manim's own frame cache stays on.** We never pass `--disable_caching` or
  `--flush_cache`. Because the workspace is bind-mounted (not copied into
  the container), `media/videos/.../partial_movie_files` persists across
  renders, so re-rendering a scene after only editing later beats is fast —
  unedited beats replay from cache instead of re-rendering.

### Additional tips (needs to apply per scene/project as needed)

- **Render at `-qh`/1080p @ 30fps for iteration, not `-qk`/4K @ 60fps.**
  Only use the top of the `Quality` ladder (`PRODUCTION`/`FOURK`) for the
  final pass; drafts should use `LOW`/`MEDIUM`.
- **Pre-render LaTeX to SVG where possible.** Every `Tex`/`MathTex` call
  invokes LaTeX; for static formulas, compiling once to SVG and loading via
  `SVGMobject` removes LaTeX from the hot path entirely.
- **Prefer `SVGMobject` over `ImageMobject`** for graphics — Cairo redraws
  raster images per frame at full resolution, while SVGs are vector paths.
  Keep SVGs simple (low path count).
- **Batch animations into one `self.play(...)`/`AnimationGroup`** instead of
  many sequential `play()` calls — `compile.py` already does this via
  `with_previous` grouping in `_compile_beat`.
- **Cache static backgrounds as a single pre-rendered image** instead of
  redrawing many static `VMobject`s every frame.
- **`docker pull manimcommunity/manim` ahead of time** in production so the
  first `_ensure_container` call doesn't block on a registry pull.

### Cleaning up persistent render containers

Containers created by `_ensure_container` are named `aos-manim-<hash>` and
are left running intentionally (that's the point — reuse). To reclaim them:

```bash
docker ps --filter "name=aos-manim-" -q | xargs -r docker rm -f
```


#########################################################

Fields to fill:
  topic             — the lecture title (from classification)
  subject           — "math", "cs", "ai", or "unknown"
  greeting          — Add a greeting message to the viewer. Keep it short and friendly. for eg: welcome to this lecture on {topic}!
  assumptions       — 2-4 things the viewer is expected to already know.
  objectives        — 3-5 bullets starting with action verbs (Understand, Derive,Apply, Visualize, Prove). These are promises to the viewer.
  opener            — The opener should feel like the beginning of an exceptional educational video,similar in spirit to the strongest science and mathematics explainers not sensational, but intellectually irresistible. learning_outcomes — 3-5 specific skills the viewer will walk away with.
  learning_outcomes: list[str] = Field(default_factory=list)
