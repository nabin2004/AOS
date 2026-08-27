from pydantic_ai.models.test import TestModel

from educlaw.agent.factory import build_agent, maybe_wrap_kitaru
from educlaw.testing import make_settings


def test_maybe_wrap_kitaru_when_enabled() -> None:
    settings = make_settings(kitaru=True)
    agent = build_agent(
        make_settings(),
        model=TestModel(call_tools=[], custom_output_text="ok"),
        wrap_kitaru=False,
    )
    wrapped = maybe_wrap_kitaru(agent, settings)
    assert wrapped is not None
    assert wrapped is not agent or type(wrapped).__name__ == "KitaruAgent"
