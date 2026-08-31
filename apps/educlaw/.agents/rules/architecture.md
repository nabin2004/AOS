# EduClaw Architecture & Component Map

## Module Map

- [`educlaw/cli.py`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/cli.py): Main entrypoint CLI built using `typer`. Defines subcommands `run`, `tui`, `repl`, `doctor`, `config`, `memory`.
- [`educlaw/agent/`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/agent): Agent creation factories, Pydantic AI integration, prompt context construction, context compaction.
- [`educlaw/animateworkflow/`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/animateworkflow): Manim animation generation pipelines, prompt formatting, and multi-agent workflow runners.
- [`educlaw/memory/`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/memory): Integration with `dagestan` temporal graph storage (`.aos/memory/graph.json`).
- [`educlaw/sandbox/`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/sandbox): Docker sandbox isolation for compiling and rendering Manim Python scripts.
- [`educlaw/durable.py`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/durable.py): Kitaru durable execution adapter for Pydantic AI agents.
- [`educlaw/tui.py`](file:///c:/Users/nabin/Desktop/myall/AOS/apps/educlaw/educlaw/tui.py): Full terminal interactive TUI using `rich`.

## Data Flow
1. User prompt is received via CLI / TUI / REPL.
2. `educlaw.agent.factory` initializes a Pydantic AI `Agent` with `AgentDeps` (settings, memory graph, sandbox handle).
3. If memory stub is inactive, `educlaw.memory` queries Dagestan graph for relevant context.
4. Agent generates Python Manim animation code.
5. `educlaw.sandbox` executes code inside container and returns stdout/stderr/renders.
6. Execution facts are extracted and appended to `.aos/memory/graph.json` and summarized in `MEMORY.md`.
