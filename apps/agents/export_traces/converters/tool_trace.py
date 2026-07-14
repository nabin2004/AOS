from __future__ import annotations

import json
from typing import Any

from export_traces.otel_messages import (
    extract_normalized_messages,
    parts_to_text,
    strip_validation_retry_turns,
)


def _truncate(text: str, max_chars: int | None) -> str:
    if max_chars is None or len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _assistant_message(
    parts: list[dict[str, Any]],
    *,
    keep_thinking: bool,
) -> dict[str, Any] | None:
    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    for part in parts:
        part_type = part.get("type")
        if part_type == "text":
            content = str(part.get("content", "")).strip()
            if content:
                text_parts.append(content)
        elif part_type == "thinking":
            if keep_thinking:
                content = str(part.get("content", "")).strip()
                if content:
                    text_parts.append(f"[THINKING]\n{content}\n[/THINKING]")
        elif part_type == "tool_call":
            arguments = part.get("arguments", "{}")
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments, ensure_ascii=False)
            tool_calls.append(
                {
                    "id": part.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": part.get("name", ""),
                        "arguments": arguments,
                    },
                }
            )

    if not text_parts and not tool_calls:
        return None

    msg: dict[str, Any] = {"role": "assistant"}
    if text_parts:
        msg["content"] = "\n".join(text_parts)
    else:
        msg["content"] = None
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def _tool_message(part: dict[str, Any], *, max_tool_result_chars: int | None) -> dict[str, Any]:
    result = str(part.get("result", ""))
    return {
        "role": "tool",
        "tool_call_id": part.get("id", ""),
        "name": part.get("name", ""),
        "content": _truncate(result, max_tool_result_chars),
    }


def convert_tool_trace(
    span: dict[str, Any],
    *,
    keep_thinking: bool = False,
    max_tool_result_chars: int | None = 8192,
    strip_validation_retries: bool = True,
) -> dict[str, Any] | None:
    """Convert span to OpenAI-style tool-call conversation rows."""
    messages = extract_normalized_messages(span)
    if not messages:
        return None

    if strip_validation_retries:
        messages = strip_validation_retry_turns(messages)

    out_messages: list[dict[str, Any]] = []

    for msg in messages:
        role = msg.get("role", "")
        parts = msg.get("parts") or []

        if role == "system":
            text = parts_to_text(parts, keep_thinking=keep_thinking)
            if text.strip():
                out_messages.append({"role": "system", "content": text.strip()})
            continue

        if role == "user":
            text_parts: list[str] = []
            tool_responses = [p for p in parts if p.get("type") == "tool_call_response"]
            for part in parts:
                if part.get("type") == "text":
                    content = str(part.get("content", "")).strip()
                    if content:
                        text_parts.append(content)
            if text_parts:
                out_messages.append(
                    {"role": "user", "content": "\n".join(text_parts).strip()}
                )
            for part in tool_responses:
                out_messages.append(
                    _tool_message(part, max_tool_result_chars=max_tool_result_chars)
                )
            continue

        if role == "assistant":
            assistant = _assistant_message(parts, keep_thinking=keep_thinking)
            if assistant:
                out_messages.append(assistant)
            continue

        if role == "tool":
            for part in parts:
                if part.get("type") == "tool_call_response":
                    out_messages.append(
                        _tool_message(part, max_tool_result_chars=max_tool_result_chars)
                    )

    if not out_messages:
        return None

    has_user = any(m.get("role") == "user" for m in out_messages)
    has_assistant = any(m.get("role") == "assistant" for m in out_messages)
    if not has_user or not has_assistant:
        return None

    return {"messages": out_messages}
