# AOS (Agentic Orchestration System) — Agent Guidelines & Repository Context

Welcome to the **AOS** repository. This document provides core instructions, conventions, architectural patterns, and execution workflows for AI agents working in this workspace.

---

## 1. Repository Architecture & Directory Structure

AOS is a multi-agent educational video and animation generation platform leveraging **Pydantic AI**, **Manim**, **Pocket TTS**, and custom **SFT/GRPO/DPO** fine-tuning pipelines.

The codebase is organized as a `uv` monorepo workspace:

```text
AOS/
├── AGENTS.md                  # Main project guide for agents
├── README.md                  # High-level overview & quickstart
├── pyproject.toml             # UV workspace configuration and root dependencies
├── apps/
│   ├── agents/                # Core Pydantic AI agent graph & lecture generation pipeline
│   │   ├── graph.py           # pydantic_graph definition (Classify -> Plan -> Storyboard -> Scenes -> Beats -> Narration -> Validate -> Repair -> Narrate -> Inspect)
│   │   ├── cli.py             # Animus CLI for running the full lecture pipeline
│   │   ├── agent_graph.py     # Streaming / interactive pipeline graph
│   │   ├── coder_agent.py     # Code mode agent for Manim scene synthesis
│   │   ├── tools/             # Pipeline tools: compile.py, render.py, narrate.py, assemble.py, pipeline.py
│   │   ├── sft_data_gen/      # SFT prompt generation, batch collection, and wave runner
│   │   ├── prompt_optimization/# DSPy and GEPA prompt optimization for IR layers
│   │   └── workspace/         # Ephemeral run artifacts (ignored by git)
│   ├── audio_service/         # Audio synthesis module using Kyutai Pocket TTS
│   ├── sft/                   # Supervised Fine-Tuning pipelines, GGUF conversion, HF upload
│   ├── grpo/                  # Group Relative Policy Optimization training
│   ├── dpo/                   # Direct Preference Optimization pipelines
│   ├── qwenCoder/             # Qwen-specific fine-tuning, DPO, and Ollama export
│   ├── educlaw/               # Educational knowledge extraction and curation
│   ├── manimator/             # Manim helper sub-agents & UI integrations
│   ├── server/                # Backend API service
│   ├── tui/                   # Terminal User Interface
│   ├── ui/                    # Web UI frontend
│   └── slidestemp/            # Manim slides templates & core components
├── packages/
│   ├── ir/                    # Core Pydantic data structures (LectureIR, SceneObject, Beat, etc.)
│   └── store/                 # Storage abstractions & vector/knowledge store
└── tests/                     # Test suites
```

---

## 2. Environment & Dependency Management

- **Package Manager**: Use `uv` for package management and script execution.
- **Python Version**: `>= 3.12`.
- **Sync Dependencies**: `uv sync` from repository root.
- **Running Python Commands**: Always run commands using `uv run python ...` or `uv run <cli_tool>`.
- **DO NOT** run `pip install` directly; edit `pyproject.toml` or relevant `apps/*/pyproject.toml` and run `uv sync`.

---

## 3. Core Agent Pipeline Workflow

### Graph Structure (`apps/agents/graph.py`)
The primary lecture generation flow follows a structured `pydantic_graph`:
1. **Classify**: Determines subject area, difficulty, prerequisites, and target audience.
2. **PlanLecture**: Generates high-level lecture outline, objectives, and pedagogical strategy.
3. **MakeStoryboard**: Breaks lecture into ordered visual scenes.
4. **CreateScenes**: Populates scene structures with visual elements and layouts.
5. **AddBeats**: Adds granular animation beats and timings.
6. **AddNarration**: Generates voiceover script aligned with beat transitions.
7. **Validate ⇄ Repair**: Strict schema and semantic validation loop (up to `--max-repairs` times).
8. **Narrate**: Synthesizes beat audio via `apps/audio_service` (Pocket TTS).
9. **Inspect**: Compiles Manim source code (`lecture.py`) and generates final `lecture_ir.json`.

### Key CLI Commands
- **Run Full Pipeline**:
  ```bash
  cd apps/agents
  uv run python cli.py generate "Explain the Fourier Transform"
  ```
- **Deterministic Assembly (No Agents)**:
  ```bash
  cd apps/agents
  uv run python assemble_runner.py runs/<run-slug>
  ```
- **Interactive Pydantic AI Agent Chat**:
  ```bash
  cd apps/agents
  uv run pai --agent classifier_agent:classifier_agent "Topic"
  ```
- **Web UI Chat**:
  ```bash
  cd apps/agents
  uv run pai web --agent agent_graph:animation_agent
  ```

---

## 4. Key Rules & Code Conventions

### Schema & IR Consistency (`packages/ir`)
- **`SceneObject.content` vs `params`**: Always use `obj.content: str` for literal text / LaTeX in `math_tex` or `text` entities. Do not rely on free-form `params["tex"]` or `params["text"]`.
- **Validation**: Ensure `math_tex`/`text` objects have non-empty `content` before passing to Manim compilation.
- **Model Flexibility**: `SceneObject.model_config` uses `extra="allow"` to prevent hard-fails during structured output generation, but explicit fields must remain clean and typed.

### Stale Scripts Warning
- `apps/agents/main.py` is stale legacy code. **Do not use or modify it** for graph execution; use `apps/agents/graph.py` or `apps/agents/cli.py`.

### Rendering & Docker
- Docker image `manimcommunity/manim` is required for rendering.
- `tools/render.py` maintains persistent containers named `aos-manim-<hash>` for performance.
- Use `manim -ql` for rapid development and testing; avoid high-res `-qk` unless specifically requested.

### Audio & Narration
- Narration uses Pocket TTS via `apps/audio_service`.
- Narration failure is designed to be non-blocking (best-effort); the pipeline will fall back gracefully to video-only rendering if audio synthesis fails.

---

## 5. Model Profiles & Configuration

Configure models via `apps/agents/.env`:
- `AOS_MODEL_PROFILE=cloud`: OpenRouter (e.g. `gpt-4o-mini`, `claude-sonnet-4-6`)
- `AOS_MODEL_PROFILE=hybrid`: OpenRouter for planning + Local Ollama for Manim coding
- `AOS_MODEL_PROFILE=local`: Full local Ollama
- `AOS_DBOS=1`: Enable DBOS durable workflow execution and checkpointing.
