"""Compaction helpers: micro (truncate tools) and full ([summary, *tail])."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence

from pydantic_ai.messages import ModelMessage

from educlaw.agent.context import (
    compact_to_summary_and_tail,
    estimate_messages_tokens,
    flatten_message_text,
    truncate_tool_returns,
)

Summarizer = Callable[[str], Awaitable[str] | str]


async def maybe_summarize(text: str, summarizer: Summarizer | None) -> str:
    if not text.strip():
        return "(empty history)"
    if summarizer is None:
        clipped = text.strip()
        if len(clipped) > 2000:
            clipped = clipped[:2000] + "\n…"
        return clipped
    result = summarizer(text)
    if isinstance(result, str):
        return result
    return await result


async def run_micro_compaction(messages: list[ModelMessage]) -> list[ModelMessage]:
    return truncate_tool_returns(messages)


async def run_full_compaction(
    messages: list[ModelMessage],
    *,
    tail_count: int = 6,
    summarizer: Summarizer | None = None,
) -> list[ModelMessage]:
    if len(messages) <= tail_count:
        return list(messages)
    head = messages[:-tail_count]
    summary = await maybe_summarize(flatten_message_text(head), summarizer)
    return compact_to_summary_and_tail(messages, summary, tail_count=tail_count)


def over_threshold(
    messages: Sequence[ModelMessage],
    window_tokens: int,
    threshold: float,
    last_usage_total: int | None = None,
) -> bool:
    if window_tokens <= 0:
        return False
    used = estimate_messages_tokens(list(messages), last_usage_total)
    return used >= int(window_tokens * threshold)
