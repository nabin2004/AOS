from __future__ import annotations

import json
from pathlib import Path

import pytest

from export_traces.converters.final_answer import convert_final_answer
from export_traces.converters.tool_trace import convert_tool_trace
from export_traces.logfire_export import load_spans
from export_traces.otel_messages import extract_normalized_messages, span_is_successful
from export_traces.trace_select import select_spans
from export_traces.validate import validate_messages_row


FIXTURES = Path(__file__).parent / "fixtures"
MANIM_TRACES = Path(__file__).resolve().parent.parent / "manim_traces.jsonl"


@pytest.fixture
def manim_spans() -> list[dict]:
    if not MANIM_TRACES.exists():
        pytest.skip("manim_traces.jsonl not available")
    return load_spans(MANIM_TRACES)


def test_load_spans_legacy_format(manim_spans: list[dict]) -> None:
    assert len(manim_spans) > 0
    assert "trace_id" in manim_spans[0]
    assert "attributes" in manim_spans[0]


def test_failed_span_not_successful(manim_spans: list[dict]) -> None:
    failed = next(
        s for s in manim_spans if s.get("trace_id") == "019f4c005e1b6871e82ca569f28162f7"
        and "final_result" not in (s.get("attributes") or {})
    )
    assert not span_is_successful(failed)


def test_selection_picks_successful_manim_span(manim_spans: list[dict]) -> None:
    trace_spans = [
        s for s in manim_spans if s.get("trace_id") == "019f4c005e1b6871e82ca569f28162f7"
    ]
    result = select_spans(trace_spans, include_errors=False)
    assert len(result.selected_spans) == 1
    selected = result.selected_spans[0]
    assert selected["attributes"].get("final_result") is not None
    assert selected["attributes"]["final_result"]["class_name"] == "MountainClimbingScene"


def test_final_answer_uses_source_not_tool_blob(manim_spans: list[dict]) -> None:
    success = next(
        s
        for s in manim_spans
        if s.get("span_id") == "a8607e9501d507b2"
    )
    row = convert_final_answer(success)
    assert row is not None
    messages = row["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assistant = messages[2]
    assert assistant["role"] == "assistant"
    assert "[TOOL_CALLS]" not in assistant["content"]
    assert assistant["content"].startswith("class MountainClimbingScene")
    assert "def construct(self):" in assistant["content"]


def test_tool_trace_preserves_tool_calls(manim_spans: list[dict]) -> None:
    success = next(
        s for s in manim_spans if s.get("span_id") == "a8607e9501d507b2"
    )
    row = convert_tool_trace(success)
    assert row is not None
    roles = [m["role"] for m in row["messages"]]
    assert "assistant" in roles
    assistant_msgs = [m for m in row["messages"] if m["role"] == "assistant"]
    assert any(m.get("tool_calls") for m in assistant_msgs)
    tool_msgs = [m for m in row["messages"] if m["role"] == "tool"]
    assert len(tool_msgs) >= 1
    assert tool_msgs[0].get("tool_call_id")


def test_validate_final_answer_row(manim_spans: list[dict]) -> None:
    success = next(
        s for s in manim_spans if s.get("span_id") == "a8607e9501d507b2"
    )
    row = convert_final_answer(success)
    assert row is not None
    errors = validate_messages_row(row, format_name="final_answer")
    assert errors == []


def test_validate_rejects_empty_assistant() -> None:
    row = {
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": ""},
        ]
    }
    errors = validate_messages_row(row, format_name="final_answer")
    assert "message_1_empty_assistant" in errors


def test_extract_messages_from_span(manim_spans: list[dict]) -> None:
    success = next(
        s for s in manim_spans if s.get("span_id") == "a8607e9501d507b2"
    )
    messages = extract_normalized_messages(success)
    assert any(m.get("role") == "system" for m in messages)
    assert any(m.get("role") == "user" for m in messages)
    assert any(m.get("role") == "assistant" for m in messages)
