# Harness slice

This document describes what is implemented today. The longer vision lives in [agent.md](agent.md).

## Loop

`AgentTurnHandler.run_turn` in [`educlaw/agent/loop.py`](../educlaw/agent/loop.py):

1. Drain the steering queue (safe boundary: before the next model call).
2. Priority gate: **steer now**, **answer later**, or **abort**.
3. Compact if the estimated tokens exceed `window * EDUCLAW_COMPACTION_THRESHOLD`.
4. Build instructions: `AGENTS.md` + Dagestan `strategy()` + `retrieve(user_text)`.
5. `await agent.run(..., message_history=..., deps=...)` with sandbox/LSP/skill tools.
6. Ingest the turn into Dagestan (`source=session_id`).
7. Periodically append a digest line to `MEMORY.md`.

Entry points: `educlaw` REPL, `educlaw tui`, `educlaw --headless -p "..."`.

## Modules

| Module | Doc |
|--------|-----|
| Capstone End-to-End | [end_to_end_harness.md](end_to_end_harness.md) |
| Animate Workflow | [animate.md](animate.md) |
| Memory | [memory.md](memory.md) |
| Sandbox | [sandbox.md](sandbox.md) |
| Permissions | [permissions.md](permissions.md) |
| Durable / Kitaru | [durable.md](durable.md) |
| Skills | `.decode/skills/*/SKILL.md` via `pydantic_ai_skills` |
| LSP | `syntax_check`, `lsp_definition`, `lsp_symbols` ([lsp.md](lsp.md)) |
| Logfire | `EDUCLAW_LOGFIRE=1` or `LOGFIRE_TOKEN` |

## Compaction

Not a module — a harness behavior ([`educlaw/agent/compaction.py`](../educlaw/agent/compaction.py)).

- **Micro:** truncate old `ToolReturnPart` bodies; keep the recent tail.
- **Full:** squash the old head into a summary message: `[summary, *tail]`.
- **Manual:** `/compact` and `/clear`.

## Steering queue

In-memory FIFO ([`educlaw/agent/steering.py`](../educlaw/agent/steering.py)). No broker.

`/steer` and `/abort` enqueue from the REPL/TUI. Lines typed while `handler.running` are queued.

## Deferred

Modal cloud sandboxes, remote Kitaru worker swarm, full JSON-RPC `ty` language server, Terminal-Bench-scale evals.
