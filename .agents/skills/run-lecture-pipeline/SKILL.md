---
name: run-lecture-pipeline
description: >-
  Use this skill when the user asks to run, test, or troubleshoot the full AOS educational lecture generation pipeline.
---

# Run Full Lecture Pipeline

This skill provides the exact sequence of steps to generate a complete educational Manim video from a topic prompt using the AOS multi-agent graph.

## Prerequisites

1. Ensure dependencies are synced:
   ```bash
   uv sync
   ```
2. Verify `.env` is configured in `apps/agents/.env`:
   - `OPENROUTER_API_KEY` (if using cloud/hybrid profile)
   - `OLLAMA_BASE_URL` (if using local/hybrid profile)
3. Ensure Docker Desktop is running and the Manim image is pulled:
   ```bash
   docker pull manimcommunity/manim
   ```

## Execution Steps

### 1. Run Pipeline via CLI
Navigate to `apps/agents` and execute the pipeline:
```bash
cd apps/agents
uv run python cli.py generate "<TOPIC_PROMPT>"
```
Example:
```bash
uv run python cli.py generate "Explain the Chain Rule in Calculus" --no-banner
```

### 2. Inspect Generated Run Artifacts
Each run creates a folder in `apps/agents/workspace/runs/<timestamp>-<slug>/`:
- `lecture.py`: Generated Manim source code.
- `lecture_ir.json`: Complete serialized `LectureIR`.
- `audio/`: Synthesized narration clips per beat.
- `videos/`: Rendered scenes.
- `lecture_final.mp4`: Final stitched video with audio narration.

### 3. Re-assembling Video (Deterministic / Post-Processing)
To re-render or re-assemble without re-running agents:
```bash
cd apps/agents
uv run python assemble_runner.py runs/<run-folder-name>
```
