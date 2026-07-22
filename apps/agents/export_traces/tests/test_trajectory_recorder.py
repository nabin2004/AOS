from __future__ import annotations

from pathlib import Path


from export_traces.converters.tool_trace import convert_normalized_messages
from export_traces.otel_messages import normalize_model_messages
from export_traces.trajectory_select import select_trajectories
from export_traces.validate import validate_messages_row
from trajectory_recorder import sanitize, steps_from_messages


FIXTURES = Path(__file__).parent / "fixtures"


def _sample_normalized_messages() -> list[dict]:
    return [
        {
            "role": "user",
            "parts": [{"type": "text", "content": "internal coder prompt with plan"}],
        },
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool_call",
                    "id": "call_1",
                    "name": "manim_write",
                    "arguments": '{"code": "class Demo(Scene): pass"}',
                }
            ],
        },
        {
            "role": "user",
            "parts": [
                {
                    "type": "tool_call_response",
                    "id": "call_1",
                    "name": "manim_write",
                    "result": '{"ok": true, "scene_file": "Demo.py"}',
                }
            ],
        },
        {
            "role": "assistant",
            "parts": [
                {
                    "type": "tool_call",
                    "id": "call_2",
                    "name": "compile_manim_code",
                    "arguments": '{"scene_name": "Demo"}',
                }
            ],
        },
        {
            "role": "user",
            "parts": [
                {
                    "type": "tool_call_response",
                    "id": "call_2",
                    "name": "compile_manim_code",
                    "result": '{"ok": false, "error": "SyntaxError"}',
                }
            ],
        },
    ]


def test_steps_from_messages_pairs_tool_calls() -> None:
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        ToolCallPart,
        ToolReturnPart,
        UserPromptPart,
    )

    messages = [
        ModelRequest(parts=[UserPromptPart(content="Write Manim code")]),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="manim_write",
                    args={"code": "class Demo(Scene): pass"},
                    tool_call_id="call_1",
                )
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="manim_write",
                    content='{"ok": true}',
                    tool_call_id="call_1",
                )
            ]
        ),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="compile_manim_code",
                    args={"scene_name": "Demo"},
                    tool_call_id="call_2",
                )
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="compile_manim_code",
                    content='{"ok": false, "error": "SyntaxError"}',
                    tool_call_id="call_2",
                )
            ]
        ),
    ]

    steps = steps_from_messages(messages)

    assert len(steps) == 2
    assert steps[0].tool_name == "manim_write"
    assert steps[0].is_error is False
    assert steps[1].tool_name == "compile_manim_code"
    assert steps[1].is_error is True


def test_sanitize_strips_absolute_paths() -> None:
    raw = (
        "/home/nabin/myallprojects/AOS/apps/agents/workspace/coder_runs/"
        "20260101-120000-demo/output_dir=/tmp/evil"
    )
    cleaned = sanitize(raw)
    assert "/home/nabin" not in cleaned
    assert "/tmp/" not in cleaned
    assert "workspace/coder_runs/<run>" in cleaned


def test_select_trajectories_keeps_shortest_success() -> None:
    prompt = "Explain eigenvectors visually"
    records = [
        {
            "user_prompt": prompt,
            "success": True,
            "trajectory": [{"type": "tool_call"}] * 4,
            "timestamp": "2026-01-01T00:00:00",
        },
        {
            "user_prompt": prompt,
            "success": True,
            "trajectory": [{"type": "tool_call"}] * 2,
            "timestamp": "2026-01-02T00:00:00",
        },
        {
            "user_prompt": prompt,
            "success": False,
            "trajectory": [{"type": "tool_call"}],
            "timestamp": "2026-01-03T00:00:00",
        },
    ]
    result = select_trajectories(records)
    assert len(result.selected) == 1
    assert len(result.selected[0]["trajectory"]) == 2


def test_convert_normalized_messages_with_user_override() -> None:
    row = convert_normalized_messages(
        _sample_normalized_messages(),  # type: ignore[arg-type]
        user_prompt_override="Explain eigenvectors visually",
    )
    assert row is not None
    assert row["messages"][0]["role"] == "user"
    assert row["messages"][0]["content"] == "Explain eigenvectors visually"
    assert any(m.get("role") == "assistant" for m in row["messages"])
    assert validate_messages_row(row, format_name="tool_trace") == []


def test_trajectory_round_trip_fixture() -> None:
    from pydantic_ai.messages import (
        ModelMessagesTypeAdapter,
        ModelRequest,
        ModelResponse,
        ToolCallPart,
        ToolReturnPart,
        UserPromptPart,
    )

    messages = [
        ModelRequest(parts=[UserPromptPart(content="internal prompt")]),
        ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name="manim_write",
                    args={"code": "class Demo(Scene): pass"},
                    tool_call_id="call_1",
                )
            ]
        ),
        ModelRequest(
            parts=[
                ToolReturnPart(
                    tool_name="manim_write",
                    content='{"ok": true}',
                    tool_call_id="call_1",
                )
            ]
        ),
    ]
    fixture = FIXTURES / "sample_messages.json"
    fixture.write_bytes(ModelMessagesTypeAdapter.dump_json(messages, indent=2))

    raw_messages = ModelMessagesTypeAdapter.validate_json(fixture.read_bytes())
    steps = steps_from_messages(raw_messages)
    assert steps

    normalized = normalize_model_messages(raw_messages)
    row = convert_normalized_messages(
        normalized,
        user_prompt_override="Teach eigenvectors with Manim",
    )
    assert row is not None
    assert validate_messages_row(row, format_name="tool_trace") == []
