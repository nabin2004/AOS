"""Kitaru durable entry. Uses kitaru.adapters.pydantic_ai, not pydantic_ai.durable_exec."""

from __future__ import annotations

from pathlib import Path

from educlaw.observability import configure_logfire
from educlaw.session import create_session
from educlaw.settings import Settings


async def run_durable_turn(prompt: str, cwd: Path, settings: Settings) -> str:
    """Stable flow body for `educlaw --headless --durable`."""
    configure_logfire(settings)
    handler = create_session(cwd=cwd, settings=settings)
    return await handler.run_turn(prompt)


def wrap_flow():
    """Return a @kitaru.flow-wrapped callable when Kitaru is installed."""
    try:
        import kitaru
    except ImportError as exc:
        raise RuntimeError("Install educlaw[durable] to use --durable") from exc

    flow_deco = getattr(kitaru, "flow", None)

    async def educlaw_headless_turn(prompt: str, cwd: str) -> str:
        settings = Settings.from_env()
        settings.kitaru = True
        return await run_durable_turn(prompt, Path(cwd), settings)

    if flow_deco is None:
        return educlaw_headless_turn
    return flow_deco(educlaw_headless_turn)
