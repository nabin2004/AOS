<!--
Sync Impact Report:
- Version change: 1.0.0 -> 1.1.0
- Modified principles:
  - Added: VI. Code Legibility, Cleanliness & Modularity (NON-NEGOTIABLE)
- Added sections:
  - Code Quality & Readability Standards (under Technology Stack & Infrastructure Requirements)
- Removed sections: None
- Follow-up TODOs: None
-->

# AOS (Agentic Orchestration System) Constitution

## Core Principles

### I. Monorepo & Package Management Integrity (`uv`)
The codebase MUST strictly use `uv` workspace management with Python `>= 3.12`. All dependencies MUST be synchronized using `uv sync` from the repository root, and all execution commands MUST run via `uv run`. Direct `pip install` calls are prohibited; dependencies MUST be explicitly specified in relevant `pyproject.toml` manifests.

### II. Schema & IR Consistency (Strict Typing)
Data exchanged across agent pipeline stages MUST strictly adhere to Pydantic models defined in `packages/ir`. Text and LaTeX visual elements MUST explicitly populate `SceneObject.content` rather than relying on untyped parameter dictionaries (e.g., `params["tex"]`). Schemas MUST enforce non-empty content before passing data to Manim compilation.

### III. Resilience & Graceful Fallback (Best-Effort Audio & Repair Loops)
Component failures MUST NOT cause full pipeline crashes when non-blocking fallback mechanisms exist. Lecture generation schema and semantic validation errors MUST trigger structured repair loops (up to `--max-repairs`). Audio narration failures (Pocket TTS / Kyutai DSM) MUST fall back gracefully to video-only rendering.

### IV. Test-Driven Verification & Docker Rendering Controls
Code updates and pipeline components MUST be verified through empirical test execution (`uv run pytest`). Manim animation compilation and rendering MUST run within isolated Docker containers (`manimcommunity/manim`) using persistent containers (`aos-manim-<hash>`). Fast draft previews (`-ql`) MUST be used for development before high-resolution rendering.

### V. Commit Traceability & Protected Trajectories
Every completed task, feature tweak, or bug fix MUST be committed in clear logical chunks and immediately pushed to remote repositories (`git push origin master`) to maintain synchronization with cloud/Kaggle environments. When training or evaluating, 100% of high-quality trajectory dataset samples (`aos_agent_trajectories` / `prompts_andrej_400`) MUST be protected and retained in training splits.

### VI. Code Legibility, Cleanliness & Modularity (NON-NEGOTIABLE)
All written code MUST prioritize clarity, self-documentation, and low cognitive overhead:
- **Single Responsibility**: Functions MUST remain focused. Functions exceeding 50 lines or 3 levels of indentation MUST be refactored into descriptive, reusable helpers.
- **Explicit Naming & Type Hints**: Variable and function names MUST clearly convey intent (avoid single-character names except standard math symbols like `i`, `x`, `t`). Comprehensive Python type hints and docstrings MUST be provided for all public modules, functions, and Pydantic models.
- **Zero Dead Code**: Prune unused variables, dead code paths, obsolete comments, and temporary debugging snippets before committing.

## Technology Stack & Infrastructure Requirements

### Core Architecture & Frameworks
- Agent graph orchestration MUST use Pydantic AI (`pydantic_graph`).
- Animation generation MUST target Manim (Community Edition / OpenGL).
- Audio synthesis MUST utilize Pocket TTS for offline CPU beat narration and Kyutai DSM for streaming STT/TTS and millisecond-accurate word alignment.

### Runtime & Compute Environment
- Windows local environments MUST maintain an active Docker engine service for Manim containers.
- Remote training runs (Kaggle / cloud GPU) MUST verify PyTorch CUDA availability (`torch.cuda.is_available()`) before package re-installation.

### Code Quality & Readability Standards
- Modular design patterns MUST be enforced across `apps/` and `packages/`.
- Logic MUST be structured to prevent deep nesting, cryptic list comprehensions, or ambiguous magic numbers/strings.

## Development & Fine-Tuning Workflow

### Execution Integrity
- Pipeline runs MUST execute through `apps/agents/cli.py` or `graph.py`. Legacy script `apps/agents/main.py` is deprecated and MUST NOT be used for graph execution.

### Fine-Tuning & Trajectory Logging
- Credentials for HuggingFace (`HF_TOKEN`) and Weights & Biases (`WANDB_API_KEY`) MUST be pulled automatically from environment variables or secure secrets clients.
- W&B experiment runs MUST use dynamic, model-identifying names (e.g., `qwen3-8b-manim-sft`).

## Governance

The AOS Constitution supersedes informal development guidelines across all workspace modules (`apps/`, `packages/`). Amendments to core schemas in `packages/ir` or pipeline graph transitions require validation against the full test suite and updates to `AGENTS.md`.

All PRs, commits, and code additions MUST pass `uv run pytest`, satisfy code readability guidelines, and follow Conventional Commits (`feat`, `fix`, `docs`, `refactor`). Runtime development context is maintained in `AGENTS.md`.

**Version**: 1.1.0 | **Ratified**: 2026-09-03 | **Last Amended**: 2026-09-03
