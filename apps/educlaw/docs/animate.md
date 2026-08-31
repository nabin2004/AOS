# Animate Workflow: Multi-Agent Manim + Voiceover Pipeline

This document explains the architecture, design choices, and usage of the **Animate Workflow** loop in EduClaw (`educlaw/animateworkflow/`).

---

## Why a Dedicated Workflow Loop?

Generating educational Manim animations paired with synchronized voiceover narration is more complex than standard code generation. A single LLM prompt often breaks due to hallucinated Manim APIs, improper voiceover context manager usage, syntax errors, or LaTeX rendering glitches.

To make animation generation reliable, we built a dedicated 5-stage pipeline driven by **`WorkflowOrchestrator`** ([`educlaw/animateworkflow/loop.py`](../educlaw/animateworkflow/loop.py)).

---

## How It Works Under the Hood

```
User Request 
     │
     ▼
[ 1. Request Classification ] ──► (Retrieves past memory from Dagestan)
     │
     ▼
[ 2. Scene Planning ] ─────────► (Normalizes video & scene UUIDs)
     │
     ▼
[ 3. Narration Planning ] ──────► (Validates scene ID bookmarks)
     │
     ▼
[ 4. Code Generation & 5. Compile Verification Loop ]
     │
     ├── (Preflight AST Check via validator.py)
     ├── (Docker Render in sandbox)
     └── Failure? ──► [ Categorize Error & Inject Remediation Guidance ] ──► (Retry up to N replans)
     │
     ▼
[ 6. Memory Ingestion ] ────────► (Saves lesson & scene summary to Dagestan graph & digest)
```

---

## The 5 Pipeline Stages

### 1. Request Classification (`step_classify`)
- **Agent**: `RequestAnalyser`
- **Output**: `RequestClassification` (topic, domain, audience grade, visual style, video count, duration).
- **Memory Integration**: Queries the project's Dagestan temporal graph memory to recall past user style preferences or related topic concepts.

### 2. Scene & Lesson Planning (`step_scene_plan`)
- **Agent**: `ScenePlannerAgent`
- **Output**: `LessonPlan` (structured list of `VideoPlan` and `SceneStep` objects).
- **Validation**: Enforces unique scene IDs and normalizes video IDs using `normalize_lesson_plan(...)`.

### 3. Voiceover Narration Planning (`step_narration_plan`)
- **Agent**: `NarrationPlannerAgent`
- **Output**: `NarrationPlan` (spoken beats and bookmark identifiers like `B0`, `B1` mapped to scenes).
- **Validation Gate**: Verifies that every narration step references a valid scene ID from the lesson plan before proceeding to code generation.

### 4 & 5. Code Generation & Sandbox Replan Loop (`step_generate_and_compile`)
- **Agent**: `CodeGeneratorAgent`
- **Pre-flight AST Check**: `validate_generated_code(...)` checks for common traps before calling Docker:
  - Hallucinated `Background(...)` or `Voiceover(...)` as animations instead of context managers.
  - Missing `VoiceoverScene` imports.
  - `ParametricFunction` called with invalid `points` arrays.
- **Sandboxed Compilation**: Runs `compile_final_code(...)` inside the Docker sandbox (`manimcommunity/manim:stable`).
- **Targeted Error Remediation**: If rendering fails, errors are categorized into `FailureCategory`:
  - `HALLUCINATED_KWARGS`: Guides the agent to use `with self.voiceover(...) as tracker:`.
  - `MISSING_IMPORTS`: Reminds the agent to import required modules.
  - `MALFORMED_POINT_ARRAYS`: Ensures `ParametricFunction` uses 3D numpy coordinate vectors.
  - `LATEX_ERROR`: Recommends raw string syntax `r"..."` for LaTeX.
  - `RENDER_TIMEOUT`: Suggests reducing animation durations or loop counts.

### 6. Memory Ingestion (`ingest_memory`)
- Upon completion, the orchestrator ingests the user request and generated lesson details into the workspace Dagestan temporal graph memory (`.aos/memory/graph.json`) and appends a digest entry to `MEMORY.md`.

---

## Developer Usage

### CLI Command

Generate an animation directly from your terminal:

```bash
# Render a video with default medium quality
educlaw animate "Teach the Lorenz Attractor chaos system visually"

# Specify custom quality (l, m, h, k) or model
educlaw animate "Teach BODMAS rules" --quality h --model openai:gpt-4o-mini
```

### Python API

```python
from pathlib import Path
import asyncio
from educlaw.animateworkflow.loop import WorkflowOrchestrator
from educlaw.settings import Settings

async def main():
    settings = Settings.from_env()
    orchestrator = WorkflowOrchestrator(settings=settings)
    
    state = await orchestrator.run(
        "Teach Pythagoras theorem visually",
        workspace_dir=Path.cwd() / "workspace" / "coder",
    )

    if state.compile_result and state.compile_result.success:
        print(f"Video saved at: {state.compile_result.output_path}")

asyncio.run(main())
```

---

## Testing

Unit tests for the workflow orchestrator are located in `tests/test_animateworkflow_loop.py`.

Run tests locally:

```bash
.venv\Scripts\python.exe -m pytest tests/test_animateworkflow_loop.py
```
