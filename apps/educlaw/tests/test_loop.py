from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from educlaw.agent.factory import build_agent
from educlaw.agent.loop import AgentTurnHandler
from educlaw.testing import make_deps, make_settings


def _handler(tmp_path: Path) -> AgentTurnHandler:
    settings = make_settings()
    deps = make_deps(tmp_path)
    agent = build_agent(settings, model=TestModel(call_tools=[], custom_output_text="ok"))
    return AgentTurnHandler(agent=agent, deps=deps, settings=settings)


@pytest.mark.asyncio
async def test_run_turn_with_test_model(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("Keep scenes short.", encoding="utf-8")
    handler = _handler(tmp_path)
    output = await handler.run_turn("Explain a circle animation.")
    assert isinstance(output, str)
    assert handler.message_history


@pytest.mark.asyncio
async def test_clear_resets_history(tmp_path: Path) -> None:
    handler = _handler(tmp_path)
    await handler.run_turn("hello")
    handler.clear()
    assert handler.message_history == []
