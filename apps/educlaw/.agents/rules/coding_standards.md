# Python & EduClaw Coding Standards

## 1. Python Standards
- **Python Version**: Write code compatible with Python 3.12+. Use modern standard library features (`type` statements, `match/case`, union types `A | B`).
- **Strict Typing**: All function arguments and return values must be explicitly typed.
- **Async Conventions**: Ensure `async` functions are properly awaited. Do not perform blocking I/O on main loops without yielding or running in background threads.

## 2. Pydantic AI Conventions
- Agent definitions must specify dependencies (`AgentDeps`) and output types explicitly.
- Use `@agent.tool` or `@agent.tool_plain` cleanly with docstrings as descriptions for the LLM.
- Validate inputs using Pydantic `BaseModel` schemas wherever structured input/output is involved.

## 3. Imports & Optional Extras
- Optional dependencies (e.g. `kitaru-pydantic-ai`, `docker`, `logfire`) must be safely imported using `try...except ImportError` blocks with actionable user messages detailing how to install the extra (e.g., `uv sync --extra durable`).
