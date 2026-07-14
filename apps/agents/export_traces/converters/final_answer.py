from __future__ import annotations

import json
from typing import Any

from export_traces.config import (
    AGENT_PROFILES,
    DEFAULT_AGENT_PROFILE,
    AgentProfile,
    FinalOutputMode,
)
from export_traces.otel_messages import (
    extract_normalized_messages,
    final_result_from_span,
    first_user_text,
    parts_to_text,
    strip_validation_retry_turns,
)


def _profile_for_span(span: dict[str, Any]) -> AgentProfile:
    from export_traces.otel_messages import agent_name_from_span

    name = agent_name_from_span(span)
    return AGENT_PROFILES.get(name, DEFAULT_AGENT_PROFILE)


def _serialize_final_result(result: Any, profile: AgentProfile) -> str | None:
    if result is None:
        return None
    if profile.final_output_mode == FinalOutputMode.SOURCE:
        if isinstance(result, dict):
            source = result.get(profile.source_field or "source")
            if source:
                return str(source)
        return None
    if profile.final_output_mode == FinalOutputMode.JSON:
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return str(result)


def _last_assistant_text(messages: list[dict[str, Any]], *, keep_thinking: bool) -> str | None:
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        text = parts_to_text(msg.get("parts") or [], keep_thinking=keep_thinking)
        if text.strip():
            return text.strip()
    return None


def _system_content(messages: list[dict[str, Any]]) -> str | None:
    for msg in messages:
        if msg.get("role") != "system":
            continue
        text = parts_to_text(msg.get("parts") or [])
        if text.strip():
            return text.strip()
    return None


def _user_content(messages: list[dict[str, Any]]) -> str | None:
    user_parts: list[str] = []
    for msg in messages:
        if msg.get("role") != "user":
            continue
        text = parts_to_text(msg.get("parts") or [])
        if text.strip():
            user_parts.append(text.strip())
    if not user_parts:
        return None
    return user_parts[0] if len(user_parts) == 1 else "\n\n".join(user_parts)


def convert_final_answer(
    span: dict[str, Any],
    *,
    keep_thinking: bool = False,
) -> dict[str, Any] | None:
    """Convert span to TRL-ready messages with final assistant answer only."""
    messages = extract_normalized_messages(span)
    if not messages:
        return None

    messages = strip_validation_retry_turns(messages)
    profile = _profile_for_span(span)
    final_result = final_result_from_span(span)

    system = _system_content(messages)
    user = _user_content(messages) or first_user_text(messages)
    if not user:
        return None

    assistant = _serialize_final_result(final_result, profile)
    if not assistant:
        assistant = _last_assistant_text(messages, keep_thinking=keep_thinking)
    if not assistant:
        return None

    out_messages: list[dict[str, str]] = []
    if system:
        out_messages.append({"role": "system", "content": system})
    out_messages.append({"role": "user", "content": user})
    out_messages.append({"role": "assistant", "content": assistant})
    return {"messages": out_messages}
