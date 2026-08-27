# Durable execution (Kitaru)

EduClaw wraps the Pydantic AI agent with **Kitaru**, not `pydantic_ai.durable_exec`:

```python
from kitaru.adapters.pydantic_ai import KitaruAgent  # or kitaru_pydantic_ai
agent = KitaruAgent(agent)  # checkpoint_strategy="calls" when the adapter supports it
```

Enable with `EDUCLAW_KITARU=1` or `educlaw --headless --durable -p "..."`.

Install the extra (`kitaru-pydantic-ai`, which provides `KitaruAgent`):

```bash
uv sync --package educlaw --extra durable
```

`--durable` uses a `@kitaru.flow` named `educlaw_headless_turn` when the `kitaru` package is installed so replay has a stable entry. Local runs can also use Kitaru's automatic flow creation.

This slice does **not** start a remote Kitaru worker swarm or Modal HITL.
