#!/usr/bin/env python3
"""Unit tests for tool-call parsing / CodeMode payload unwrap (no GPU)."""

from __future__ import annotations

from infer_tools import (
    _codemode_preflight,
    assistant_message_from_generation,
    extract_run_code_source,
    parse_gemma_tool_calls,
    parse_model_tool_calls,
    parse_qwen_tool_calls,
    strip_tool_call_markup,
)


def test_parse_run_code_with_input_string() -> None:
    raw = '<|tool_call>call:run_code{input:<|"|>{"code": "print(1)"}<|"|>}<tool_call|>'
    calls = parse_gemma_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "run_code"
    args = calls[0]["function"]["arguments"]
    assert "input" in args
    assert extract_run_code_source(args) == "print(1)"


def test_parse_manim_write_nested_args() -> None:
    raw = (
        "<|tool_call>call:manim_write{"
        'code:<|"|>class Scene(Scene): pass<|"|>,'
        'scene_name:<|"|>Demo<|"|>'
        "}<tool_call|>"
    )
    calls = parse_gemma_tool_calls(raw)
    assert calls[0]["function"]["name"] == "manim_write"
    args = calls[0]["function"]["arguments"]
    assert args["scene_name"] == "Demo"
    assert "class Scene" in args["code"]


def test_parse_qwen_tool_call() -> None:
    raw = (
        '<tool_call>\n{"name": "run_code", "arguments": {"code": "print(1)"}}\n'
        "</tool_call>"
    )
    calls = parse_qwen_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "run_code"
    assert extract_run_code_source(calls[0]["function"]["arguments"]) == "print(1)"


def test_parse_model_tool_calls_defaults_to_qwen() -> None:
    raw = (
        '<tool_call>\n{"name": "run_code", "arguments": {"input": "x=1"}}\n'
        "</tool_call>"
    )
    calls = parse_model_tool_calls(raw, model_id="Qwen/Qwen2.5-Coder-7B-Instruct")
    assert calls[0]["function"]["arguments"]["input"] == "x=1"


def test_strip_leaves_prose() -> None:
    raw = (
        "Here we go.\n"
        '<|tool_call>call:run_code{input:<|"|>{"code": "x=1"}<|"|>}<tool_call|>'
    )
    assert strip_tool_call_markup(raw) == "Here we go."


def test_strip_qwen_leaves_prose() -> None:
    raw = (
        "Here we go.\n"
        '<tool_call>\n{"name": "run_code", "arguments": {"code": "x=1"}}\n'
        "</tool_call>"
    )
    assert strip_tool_call_markup(raw) == "Here we go."


def test_assistant_message_tool_only() -> None:
    raw = '<|tool_call>call:run_code{code:<|"|>print(2)<|"|>}<tool_call|><eos>'
    msg = assistant_message_from_generation(raw, family="gemma")
    assert msg["role"] == "assistant"
    assert msg["content"] is None
    assert msg["tool_calls"][0]["function"]["name"] == "run_code"
    assert extract_run_code_source(msg["tool_calls"][0]["function"]["arguments"]) == (
        "print(2)"
    )


def test_assistant_message_qwen_tool_only() -> None:
    raw = (
        '<tool_call>\n{"name": "run_code", "arguments": {"code": "print(2)"}}\n'
        "</tool_call><|im_end|>"
    )
    msg = assistant_message_from_generation(
        raw, model_id="Qwen/Qwen2.5-Coder-7B-Instruct"
    )
    assert msg["role"] == "assistant"
    assert msg["tool_calls"][0]["function"]["name"] == "run_code"
    assert extract_run_code_source(msg["tool_calls"][0]["function"]["arguments"]) == (
        "print(2)"
    )


def test_extract_run_code_from_dict_code() -> None:
    assert extract_run_code_source({"code": "await manim_write(code='x')"}) == (
        "await manim_write(code='x')"
    )


def test_codemode_preflight_rejects_star_import() -> None:
    err = _codemode_preflight("from manim import *\nclass Demo(Scene):\n    pass")
    assert err is not None
    assert err["error"] == "codemode_star_import"


def test_codemode_preflight_allows_nested_star_import() -> None:
    code = (
        "code = '''from manim import *\\nclass Demo(Scene): pass'''\\n"
        "await manim_write(code=code, scene_name='Demo')"
    )
    assert _codemode_preflight(code) is None

    multiline = (
        "code = '''from manim import *\n"
        "class Demo(Scene): pass'''\n"
        "await manim_write(code=code, scene_name='Demo')"
    )
    assert _codemode_preflight(multiline) is None


if __name__ == "__main__":
    test_parse_run_code_with_input_string()
    test_parse_manim_write_nested_args()
    test_parse_qwen_tool_call()
    test_parse_model_tool_calls_defaults_to_qwen()
    test_strip_leaves_prose()
    test_strip_qwen_leaves_prose()
    test_assistant_message_tool_only()
    test_assistant_message_qwen_tool_only()
    test_extract_run_code_from_dict_code()
    test_codemode_preflight_rejects_star_import()
    test_codemode_preflight_allows_nested_star_import()
    print("OK")
