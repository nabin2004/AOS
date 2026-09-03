# Implementation Plan: Complete EduClaw Harness & Manim Animation Engine

**Branch**: `001-educlaw-harness-complete` | **Date**: 2026-09-03 | **Spec**: [specs/001-educlaw-harness-complete/spec.md](file:///c:/Users/nabin/Desktop/myall/AOS/specs/001-educlaw-harness-complete/spec.md)

**Input**: Feature specification from `specs/001-educlaw-harness-complete/spec.md`

## Summary

Complete the remaining implementation gaps in the **EduClaw Harness** to establish an elite multi-agent system for generating high-fidelity Manim animations, synchronized voiceover narration, and engaging educational learning experiences. The plan introduces a **Pedagogical Theme Engine & Visual Component Gallery**, **Multimodal Keyframe Visual QC Gate**, **Manim API Lookup Knowledge Base**, **Voiceover Bookmark Sync**, and **Multi-Scene Video Concatenation**.

---

## Technical Context

**Language/Version**: Python >= 3.12 (`uv` monorepo workspace)  
**Primary Dependencies**: `pydantic-ai`, `manim`, `rich`, `typer`, `ffmpeg-python`, `pillow`, `kitaru-pydantic-ai`  
**Storage**: Dagestan JSON temporal memory graph (`.aos/memory/graph.json`) & SQLite ledger  
**Testing**: `pytest`, `evals.smoke`, `evals.audio_eval`, `evals.visual_qc_eval`  
**Target Platform**: Windows local (with Docker Engine) / Linux container environments  
**Project Type**: Multi-agent harness CLI & library (`apps/educlaw`)  
**Performance Goals**: < 100ms bookmark audio-visual sync, 100% keyframe visual QA pass rate, sub-3-minute total generation & compilation loop for 2-minute animation  
**Constraints**: Zero unhandled tracebacks, zero host-system command execution (all render commands sandboxed in Docker)  

---

## Constitution Check

*GATE: Passed against AOS Constitution v1.1.0.*

- **I. Monorepo & Package Management (`uv`)**: Compliant. All dependencies specified in `apps/educlaw/pyproject.toml` and executed via `uv run`.
- **II. Schema & IR Consistency (Strict Typing)**: Compliant. Models explicitly define typed fields (`EduClawTheme`, `VisualQCReport`, `ManimSymbolDoc`).
- **III. Resilience & Graceful Fallback**: Compliant. Visual QC failures re-route to error remediation loop; audio errors fall back gracefully.
- **IV. Test-Driven Verification & Docker Controls**: Compliant. All Manim code execution takes place in Docker sandbox containers (`manimcommunity/manim:stable`).
- **V. Commit Traceability & Protected Trajectories**: Compliant. Trajectory logs saved to SFT dataset folders.
- **VI. Code Legibility, Cleanliness & Modularity**: Compliant. Modules kept under 50 lines per function, max nesting depth <= 3, full type hints provided.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-educlaw-harness-complete/
├── plan.md              # Implementation plan
├── research.md          # Phase 0 research decisions
├── data-model.md        # Data models and state machine diagrams
├── quickstart.md        # End-to-end validation scenarios
└── contracts/
    └── tools.md         # Interface contracts for new tools and CLI flags
```

### Source Code (`apps/educlaw`)

```text
apps/educlaw/educlaw/
├── agent/
│   ├── audio_tools.py      # Audio synthesis & alignment tools
│   ├── deps.py             # Agent dependency state
│   ├── factory.py          # Agent instantiation
│   ├── loop.py             # Interactive execution loop
│   ├── steering.py         # Steering & human-in-the-loop controls
│   └── tools.py            # Sandbox, render, LSP & API lookup tools
├── animateworkflow/
│   ├── agents.py           # Classifier, Planner, Coder & Inspector agents
│   ├── compiler.py         # Docker Manim compiler & error categorizer
│   ├── components.py       # Visual component template gallery [NEW]
│   ├── contracts.py        # Pydantic schemas (VisualQCReport, FinalCode)
│   ├── loop.py             # 6-stage workflow orchestrator loop
│   ├── manim_kb.py         # Manim API lookup knowledge base [NEW]
│   ├── theme.py            # Pedagogical theme engine [NEW]
│   ├── validator.py        # AST preflight validator
│   └── visual_qc.py        # Keyframe extractor & multimodal inspector [NEW]
├── sandbox/
│   └── docker.py           # Docker container wrapper & ffmpeg video tools
└── cli.py                  # Typer CLI commands & `--theme` flags
```

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *None* | All features comply strictly with Constitution v1.1.0 | N/A |
