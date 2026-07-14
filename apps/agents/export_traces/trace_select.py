from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from export_traces.otel_messages import (
    agent_name_from_span,
    conversation_id_from_span,
    extract_normalized_messages,
    first_user_text,
    span_success_score,
)


@dataclass
class DropStats:
    failed: int = 0
    empty: int = 0
    duplicate: int = 0
    retry_skipped: int = 0
    error_status: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "failed": self.failed,
            "empty": self.empty,
            "duplicate": self.duplicate,
            "retry_skipped": self.retry_skipped,
            "error_status": self.error_status,
        }


@dataclass
class SelectionResult:
    selected_spans: list[dict[str, Any]] = field(default_factory=list)
    retry_spans: list[dict[str, Any]] = field(default_factory=list)
    drop_stats: DropStats = field(default_factory=DropStats)


def grouping_key(span: dict[str, Any]) -> str:
    conversation_id = conversation_id_from_span(span)
    if conversation_id:
        return f"conv:{conversation_id}"
    trace_id = span.get("trace_id") or "unknown"
    agent = agent_name_from_span(span)
    return f"trace:{trace_id}|agent:{agent}"


def user_prompt_hash(span: dict[str, Any]) -> str | None:
    messages = extract_normalized_messages(span)
    user_text = first_user_text(messages)
    if not user_text:
        return None
    return hashlib.sha256(user_text.encode("utf-8")).hexdigest()


def select_best_span(spans: list[dict[str, Any]]) -> dict[str, Any]:
    return max(spans, key=span_success_score)


def select_spans(
    spans: list[dict[str, Any]],
    *,
    include_errors: bool = False,
    include_retries: bool = False,
    min_chars: int = 0,
    max_chars: int | None = None,
    deduplicate: bool = True,
) -> SelectionResult:
    """Group spans, pick best per conversation, apply quality filters."""
    result = SelectionResult()
    groups: dict[str, list[dict[str, Any]]] = {}
    for span in spans:
        key = grouping_key(span)
        groups.setdefault(key, []).append(span)

    seen_hashes: set[tuple[str, str]] = set()

    for group_spans in groups.values():
        sorted_spans = sorted(
            group_spans,
            key=lambda s: str(s.get("start_timestamp") or ""),
        )
        best = select_best_span(sorted_spans)

        if not include_retries:
            for span in sorted_spans:
                if span is not best:
                    result.retry_spans.append(span)
                    result.drop_stats.retry_skipped += 1

        if not include_errors and not span_success_score(best)[1]:
            result.drop_stats.failed += 1
            continue

        if best.get("otel_status_code") == "ERROR" and not include_errors:
            result.drop_stats.error_status += 1
            continue

        messages = extract_normalized_messages(best)
        if not messages:
            result.drop_stats.empty += 1
            continue

        agent = agent_name_from_span(best)
        prompt_hash = user_prompt_hash(best)
        if deduplicate and prompt_hash:
            dedup_key = (agent, prompt_hash)
            if dedup_key in seen_hashes:
                result.drop_stats.duplicate += 1
                continue
            seen_hashes.add(dedup_key)

        user_text = first_user_text(messages) or ""
        assistant_len = sum(
            len(str(p.get("content", "")))
            for msg in messages
            if msg.get("role") == "assistant"
            for p in msg.get("parts") or []
            if p.get("type") in ("text", "thinking", "tool_call")
        )
        total_len = len(user_text) + assistant_len
        if total_len < min_chars:
            result.drop_stats.empty += 1
            continue
        if max_chars is not None and total_len > max_chars:
            result.drop_stats.empty += 1
            continue

        result.selected_spans.append(best)
        if include_retries:
            for span in sorted_spans:
                if span is not best:
                    result.retry_spans.append(span)

    return result
