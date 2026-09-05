# AGENTS.md — Developer & AI Agent Guide for EduClaw

Welcome to **EduClaw**, a coding harness for Manim animation agents featuring a Pydantic AI loop, Dagestan temporal memory graph, Docker sandbox rendering, rich CLI/TUI interfaces, and optional Kitaru durable agents.

---

## 1. Project Overview & Architecture

EduClaw is built around several core components:

- **CLI & Interface Layer** ([`educlaw/cli.py`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/cli.py), [`educlaw/tui.py`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/tui.py)): Built with Typer and Rich. Supports interactive REPL, full terminal TUI, single-shot CLI runs, memory curation, and configuration management.
- **Agent Harness** ([`educlaw/agent/`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/agent)): Leverages `pydantic-ai` for tool integration, prompt framing, context compaction, and execution loops.
- **Animate Workflow** ([`educlaw/animateworkflow/`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/animateworkflow)): Contains scene generation logic, multi-agent animation orchestration, and Manim script creation workflows.
- **Temporal Memory** ([`educlaw/memory/`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/memory)): Integrates with the `dagestan` temporal graph storage at `<cwd>/.aos/memory/graph.json`.
- **Sandbox Execution & Keyframe Probing** ([`educlaw/sandbox/`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/sandbox)): Safe containerized execution environment for rendering Manim scenes via Docker. Supports rapid `-ql -s` keyframe probing via `test_render_manim`.
- **Manim Spatial Skills** ([`.agents/skills/manim-spatial-rules/SKILL.md`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/.agents/skills/manim-spatial-rules/SKILL.md)): On-demand spatial heuristics, 16:9 coordinate boundaries, and LaTeX raw-string rules.
- **Durability Layer** ([`educlaw/durable.py`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/durable.py)): Wraps Pydantic AI agents with `KitaruAgent` for fault-tolerant execution when `educlaw[durable]` is installed.

---


## 2. Environment & Tooling

### Python Environment
- Requires **Python 3.12+**.
- Uses `uv` for package management.
- Executables are located in the local `.venv` directory (Windows: `.venv\Scripts\python.exe`).

### Installation Commands
```bash
# Standard dev setup
uv sync --package educlaw --extra dev

# Setup with durable Kitaru integration
uv sync --package educlaw --extra durable --extra dev
```

---

## 3. Testing & Verification Guidelines

Always verify code changes by running tests.

### Running Pytest
```bash
# Standard test suite execution
.venv\Scripts\python.exe -m pytest

# Run tests ignoring optional kitaru extra if not installed
.venv\Scripts\python.exe -m pytest -k "not test_maybe_wrap_kitaru_when_enabled"
```

### Offline & Mock Testing Flags
To run tests or test the CLI offline without calling live LLM APIs:
```bash
# Set environment variables for offline test model & memory stub
$env:EDUCLAW_TEST_MODEL="1"
$env:EDUCLAW_MEMORY_STUB="1"

# Or use CLI flag
.venv\Scripts\python.exe -m educlaw --model test --yes run "Render a simple circle"
```

---

## 4. Coding Standards & Conventions

1. **Type Annotations**: Use strict type hints on all function signatures (`def fn(x: str) -> bool:`).
2. **Pydantic AI Schemas**: Define Pydantic models for structured tool outputs and dependency state objects (`AgentDeps`).
3. **Async / Await**: Agent execution loops and Docker sandbox interactions must preserve proper `async`/`await` patterns.
4. **Error Handling**: Handle missing dependencies gracefully (e.g. `ImportError` for optional extras like `kitaru_pydantic_ai` with clear error messages).
5. **No Blind Fallbacks**: Never suppress runtime tracebacks silently. Log or propagate errors appropriately.

---

## 5. File Structure Reference

```
educlaw/
├── agent/             # Pydantic AI agent creation, tools, compaction & loop
├── animateworkflow/    # Manim script animation agent workflow
├── cli.py             # Main CLI entrypoint (Typer commands)
├── config/            # Settings & configuration management
├── context/           # System prompt context management
├── durable.py         # Kitaru durability agent wrapper
├── lsp/               # Code diagnostic and language server tooling
├── memory/            # Dagestan temporal graph memory binding
├── sandbox/           # Docker containerized execution for Manim
├── session.py         # Session state handling
├── settings.py        # Environment variables & runtime settings
├── tui.py             # Rich full-terminal TUI interface
evals/                 # Evaluation scripts and smoke tests
tests/                 # Pytest suite
pyproject.toml         # Build setup & dependencies
```
