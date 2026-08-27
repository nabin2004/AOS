import pytest
from pydantic_ai.messages import ModelRequest, ToolReturnPart, UserPromptPart

from educlaw.agent.compaction import run_full_compaction, run_micro_compaction
from educlaw.agent.context import compact_to_summary_and_tail


def _user(text: str) -> ModelRequest:
    return ModelRequest.user_text_prompt(text)


def _tool_request(body: str) -> ModelRequest:
    return ModelRequest(
        parts=[
            UserPromptPart("after tool"),
            ToolReturnPart(tool_name="bash", content=body, tool_call_id="call-1"),
        ]
    )


@pytest.mark.asyncio
async def test_micro_truncates_old_tool_bodies() -> None:
    bulky = "x" * 800
    messages = [_tool_request(bulky), _user("1"), _user("2"), _user("3"), _user("4"), _user("5")]
    compacted = await run_micro_compaction(messages)
    first = compacted[0]
    tool = next(part for part in first.parts if isinstance(part, ToolReturnPart))
    assert "truncated by micro-compaction" in str(tool.content)
    assert len(str(tool.content)) < 800


@pytest.mark.asyncio
async def test_full_compaction_keeps_tail_and_inserts_summary() -> None:
    messages = [_user(f"turn {i}") for i in range(10)]

    async def summarizer(text: str) -> str:
        assert "turn 0" in text
        return "HEAD SUMMARY"

    compacted = await run_full_compaction(messages, tail_count=3, summarizer=summarizer)
    assert compacted[0].parts[0].content.startswith("[Conversation summary]")
    assert "HEAD SUMMARY" in compacted[0].parts[0].content
    tail_texts = [part.content for msg in compacted[1:] for part in msg.parts]
    assert tail_texts == ["turn 7", "turn 8", "turn 9"]


def test_compact_to_summary_and_tail_shape() -> None:
    messages = [_user("a"), _user("b"), _user("c"), _user("d")]
    result = compact_to_summary_and_tail(messages, "s", tail_count=2)
    assert len(result) == 3
    assert "s" in result[0].parts[0].content
