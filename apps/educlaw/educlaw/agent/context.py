"""Context-window resolution and token estimates."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic_ai.messages import ModelMessage, ModelRequest, ToolReturnPart

FALLBACK_WINDOW = 200_000

# Conservative static table. Explicit EDUCLAW_CONTEXT_WINDOW always wins.
STATIC_WINDOWS: dict[str, int] = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4.1": 1_047_576,
    "claude-sonnet-4-20250514": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-7-sonnet": 200_000,
    "gemini-2.5-pro": 1_000_000,
    "test": 16_000,
}


def estimate_text_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def _part_text(part: object) -> str:
    content = getattr(part, "content", None)
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return str(content)


def flatten_message_text(messages: Sequence[ModelMessage]) -> str:
    chunks: list[str] = []
    for message in messages:
        for part in getattr(message, "parts", ()):
            text = _part_text(part)
            if text:
                chunks.append(text)
    return "\n".join(chunks)


def estimate_messages_tokens(messages: Sequence[ModelMessage], last_usage_total: int | None = None) -> int:
    if last_usage_total is not None and last_usage_total > 0:
        return last_usage_total
    return estimate_text_tokens(flatten_message_text(messages))


class ContextWindow:
    tokens: int

    def __init__(self, tokens: int = FALLBACK_WINDOW) -> None:
        self.tokens = tokens

    @staticmethod
    def probe(provider_llm: object, model_id: str) -> int | None:
        """Ask a provider for the model's context window. Returns None if unsupported."""
        del provider_llm, model_id
        return None

    @classmethod
    def resolve(
        cls,
        *,
        explicit: int | None,
        model_id: str | None = None,
        provider_llm: object | None = None,
    ) -> ContextWindow:
        if explicit is not None and explicit > 0:
            return cls(explicit)
        if provider_llm is not None and model_id:
            probed = cls.probe(provider_llm, model_id)
            if probed:
                return cls(probed)
        if model_id:
            lowered = model_id.lower()
            for key, value in STATIC_WINDOWS.items():
                if key in lowered:
                    return cls(value)
        return cls(FALLBACK_WINDOW)

    def resolve_context_window(self) -> int:
        return self.tokens

    def resolve_context_window_detail(self) -> dict[str, int]:
        return {"tokens": self.tokens}

    def get_context_window(self) -> int:
        return self.tokens


def truncate_tool_returns(
    messages: list[ModelMessage],
    *,
    keep_recent: int = 4,
    max_tool_chars: int = 400,
) -> list[ModelMessage]:
    """Drop bulky old tool-return bodies; keep the recent tail intact."""
    if len(messages) <= keep_recent:
        return list(messages)
    cutoff = len(messages) - keep_recent
    updated: list[ModelMessage] = []
    for index, message in enumerate(messages):
        if index >= cutoff or not isinstance(message, ModelRequest):
            updated.append(message)
            continue
        new_parts = []
        changed = False
        for part in message.parts:
            if isinstance(part, ToolReturnPart):
                text = _part_text(part)
                if len(text) > max_tool_chars:
                    part = ToolReturnPart(
                        tool_name=part.tool_name,
                        content=text[:max_tool_chars] + "\n…[truncated by micro-compaction]",
                        tool_call_id=part.tool_call_id,
                    )
                    changed = True
            new_parts.append(part)
        if changed:
            updated.append(ModelRequest(parts=new_parts, instructions=message.instructions))
        else:
            updated.append(message)
    return updated


def compact_to_summary_and_tail(
    messages: list[ModelMessage],
    summary: str,
    *,
    tail_count: int = 6,
) -> list[ModelMessage]:
    """Replace the old head with a summary message and keep the recent tail."""
    tail = list(messages[-tail_count:]) if tail_count > 0 else []
    summary_msg = ModelRequest.user_text_prompt(f"[Conversation summary]\n{summary.strip()}")
    return [summary_msg, *tail]
