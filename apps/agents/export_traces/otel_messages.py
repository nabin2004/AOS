from __future__ import annotations

import json
from typing import Any

from export_traces.config import VALIDATION_FEEDBACK_PREFIX

PartType = str
NormalizedPart = dict[str, Any]
NormalizedMessage = dict[str, Any]


def coerce_json(value: Any) -> Any:
    """Parse JSON strings from Logfire attribute columns."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return value
    return value


def get_attributes(span: dict[str, Any]) -> dict[str, Any]:
    attrs = span.get("attributes") or {}
    if isinstance(attrs, str):
        attrs = coerce_json(attrs)
    return attrs if isinstance(attrs, dict) else {}


def agent_name_from_span(span: dict[str, Any]) -> str:
    attrs = get_attributes(span)
    return (
        attrs.get("gen_ai.agent.name")
        or attrs.get("agent_name")
        or "Unknown Agent"
    )


def conversation_id_from_span(span: dict[str, Any]) -> str | None:
    attrs = get_attributes(span)
    return attrs.get("gen_ai.conversation.id")


def final_result_from_span(span: dict[str, Any]) -> Any | None:
    attrs = get_attributes(span)
    result = attrs.get("final_result")
    if result is None:
        return None
    return coerce_json(result)


def usage_from_span(span: dict[str, Any]) -> dict[str, Any]:
    attrs = get_attributes(span)
    return {
        "input_tokens": attrs.get("gen_ai.aggregated_usage.input_tokens"),
        "output_tokens": attrs.get("gen_ai.aggregated_usage.output_tokens"),
        "reasoning_tokens": attrs.get(
            "gen_ai.aggregated_usage.details.reasoning_tokens"
        ),
    }


def metadata_from_span(span: dict[str, Any]) -> dict[str, Any]:
    attrs = get_attributes(span)
    usage = usage_from_span(span)
    return {
        "trace_id": span.get("trace_id"),
        "span_id": span.get("span_id"),
        "agent_name": agent_name_from_span(span),
        "model_name": attrs.get("model_name") or attrs.get("gen_ai.request.model"),
        "conversation_id": conversation_id_from_span(span),
        "duration": span.get("duration"),
        "timestamp": span.get("start_timestamp"),
        "operation": attrs.get("gen_ai.operation.name"),
        "usage": usage,
    }


def _normalize_part(part: dict[str, Any]) -> NormalizedPart | None:
    part_type = part.get("type", "")
    if part_type == "text":
        content = part.get("content", "")
        return {"type": "text", "content": str(content)} if content else None
    if part_type == "thinking":
        content = part.get("content", "")
        return {"type": "thinking", "content": str(content)} if content else None
    if part_type == "tool_call":
        arguments = part.get("arguments", "{}")
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments, ensure_ascii=False)
        return {
            "type": "tool_call",
            "id": part.get("id", ""),
            "name": part.get("name", ""),
            "arguments": arguments,
        }
    if part_type == "tool_call_response":
        return {
            "type": "tool_call_response",
            "id": part.get("id", ""),
            "name": part.get("name", ""),
            "result": str(part.get("result", part.get("response", ""))),
        }
    if part_type in ("image", "audio"):
        return {"type": part_type, "content": f"[{part_type.upper()}]"}
    content = part.get("content") or part.get("text")
    if content:
        return {"type": "text", "content": str(content)}
    return None


def _parts_from_otel_message(msg: dict[str, Any]) -> list[NormalizedPart]:
    parts: list[NormalizedPart] = []
    for part in msg.get("parts") or []:
        if isinstance(part, dict):
            normalized = _normalize_part(part)
            if normalized:
                parts.append(normalized)
    return parts


def _message_from_role_parts(role: str, parts: list[NormalizedPart]) -> NormalizedMessage | None:
    if not parts:
        return None
    return {"role": role, "parts": parts}


def _extract_from_pydantic_ai(attrs: dict[str, Any]) -> list[NormalizedMessage]:
    raw = attrs.get("pydantic_ai.all_messages")
    if not raw:
        return []
    messages_data = coerce_json(raw)
    if not isinstance(messages_data, list):
        return []

    messages: list[NormalizedMessage] = []
    for msg in messages_data:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        parts: list[NormalizedPart] = []
        for part in msg.get("parts") or []:
            if isinstance(part, dict):
                normalized = _normalize_part(part)
                if normalized:
                    parts.append(normalized)
        normalized_msg = _message_from_role_parts(role, parts)
        if normalized_msg:
            if msg.get("finish_reason"):
                normalized_msg["finish_reason"] = msg["finish_reason"]
            messages.append(normalized_msg)
    return messages


def _extract_from_gen_ai(attrs: dict[str, Any]) -> list[NormalizedMessage]:
    messages: list[NormalizedMessage] = []

    system_instructions = coerce_json(attrs.get("gen_ai.system_instructions"))
    if system_instructions:
        if isinstance(system_instructions, list):
            text_parts = []
            for item in system_instructions:
                if isinstance(item, dict):
                    text_parts.append(str(item.get("content", "")))
                else:
                    text_parts.append(str(item))
            system_text = "\n".join(p for p in text_parts if p.strip())
        else:
            system_text = str(system_instructions)
        if system_text.strip():
            messages.append(
                {
                    "role": "system",
                    "parts": [{"type": "text", "content": system_text.strip()}],
                }
            )

    input_messages = coerce_json(attrs.get("gen_ai.input.messages"))
    if isinstance(input_messages, list):
        for msg in input_messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                parts = _parts_from_otel_message(msg)
                normalized = _message_from_role_parts(role, parts)
                if normalized:
                    messages.append(normalized)

    output_messages = coerce_json(attrs.get("gen_ai.output.messages"))
    if isinstance(output_messages, list):
        for msg in output_messages:
            if isinstance(msg, dict):
                role = msg.get("role", "assistant")
                parts = _parts_from_otel_message(msg)
                normalized = _message_from_role_parts(role, parts)
                if normalized:
                    messages.append(normalized)

    return messages


def extract_normalized_messages(span: dict[str, Any]) -> list[NormalizedMessage]:
    """Extract conversation messages using pydantic_ai first, then gen_ai fallback."""
    attrs = get_attributes(span)
    messages = _extract_from_pydantic_ai(attrs)
    if messages:
        return messages
    return _extract_from_gen_ai(attrs)


def parts_to_text(parts: list[NormalizedPart], *, keep_thinking: bool = False) -> str:
    chunks: list[str] = []
    for part in parts:
        part_type = part.get("type")
        if part_type == "text":
            chunks.append(str(part.get("content", "")))
        elif part_type == "thinking" and keep_thinking:
            chunks.append(f"[THINKING]\n{part.get('content', '')}\n[/THINKING]")
    return "\n".join(c for c in chunks if c.strip()).strip()


def first_user_text(messages: list[NormalizedMessage]) -> str | None:
    for msg in messages:
        if msg.get("role") != "user":
            continue
        text = parts_to_text(msg.get("parts") or [])
        if text.strip():
            return text.strip()
    return None


def is_validation_feedback_message(msg: NormalizedMessage) -> bool:
    if msg.get("role") != "user":
        return False
    text = parts_to_text(msg.get("parts") or [])
    return text.strip().startswith(VALIDATION_FEEDBACK_PREFIX)


def strip_validation_retry_turns(messages: list[NormalizedMessage]) -> list[NormalizedMessage]:
    """Remove validation feedback user turns and the assistant turn before each."""
    result: list[NormalizedMessage] = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if is_validation_feedback_message(msg):
            if result and result[-1].get("role") == "assistant":
                result.pop()
            i += 1
            continue
        result.append(msg)
        i += 1
    return result


def span_has_final_result(span: dict[str, Any]) -> bool:
    return final_result_from_span(span) is not None


def span_is_successful(span: dict[str, Any]) -> bool:
    if span.get("is_exception"):
        return False
    if span.get("otel_status_code") == "ERROR":
        return False
    attrs = get_attributes(span)
    messages = extract_normalized_messages(span)
    for msg in reversed(messages):
        if msg.get("role") != "assistant":
            continue
        if msg.get("finish_reason") == "error":
            return False
        for part in msg.get("parts") or []:
            if part.get("type") == "thinking" and part.get("finish_reason") == "error":
                return False
        break
    if attrs.get("error.type"):
        return False
    return True


def span_success_score(span: dict[str, Any]) -> tuple[int, int, str]:
    """Higher is better: (has_final_result, is_successful, timestamp)."""
    has_final = 1 if span_has_final_result(span) else 0
    successful = 1 if span_is_successful(span) else 0
    ts = str(span.get("start_timestamp") or "")
    return (has_final, successful, ts)
