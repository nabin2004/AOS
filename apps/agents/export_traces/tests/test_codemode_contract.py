"""CodeMode star-import contract checks for tool_trace SFT rows."""

from __future__ import annotations

from export_traces.codemode_contract import (
    codemode_violations,
    run_code_has_multiline_single_quoted_string,
    run_code_has_nested_run_code,
    run_code_has_star_import,
    run_code_has_tool_redefinition,
    tool_trace_violates_codemode,
)
from export_traces.validate import validate_messages_row


def test_nested_manim_write_passes() -> None:
    code = (
        "code = '''from manim import *\\nclass Demo(Scene):\\n"
        "    def construct(self):\\n        pass'''\\n"
        "await manim_write(code=code, scene_name='Demo')"
    )
    assert not run_code_has_star_import(code)
    row = {
        "messages": [
            {"role": "user", "content": "animate"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "run_code",
                            "arguments": {"code": code},
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "c1",
                "name": "run_code",
                "content": '{"ok": true}',
            },
        ]
    }
    assert tool_trace_violates_codemode(row) == []
    assert validate_messages_row(row, format_name="tool_trace") == []


def test_top_level_star_import_fails() -> None:
    code = (
        "from manim import *\n"
        "from manim_voiceover import VoiceoverScene\n"
        "class Demo(VoiceoverScene):\n"
        "    def construct(self):\n"
        "        pass\n"
    )
    assert run_code_has_star_import(code)
    row = {
        "messages": [
            {"role": "user", "content": "animate"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "run_code",
                            "arguments": {"code": code},
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "c1",
                "name": "run_code",
                "content": "error",
            },
        ]
    }
    assert tool_trace_violates_codemode(row) == ["codemode_star_import"]
    errors = validate_messages_row(row, format_name="tool_trace")
    assert "codemode_star_import" in errors


def test_string_arguments_json_detected() -> None:
    code = "from manim import *\nprint(1)\n"
    row = {
        "messages": [
            {"role": "user", "content": "x"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "run_code",
                            "arguments": '{"code": "from manim import *\\nprint(1)\\n"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "c1",
                "content": "ok",
            },
        ]
    }
    assert run_code_has_star_import(code)
    assert tool_trace_violates_codemode(row) == ["codemode_star_import"]


def test_nested_run_code_fails() -> None:
    code = "await run_code(code='pass')"
    assert run_code_has_nested_run_code(code)
    row = {
        "messages": [
            {"role": "user", "content": "animate"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "run_code",
                            "arguments": {"code": code},
                        },
                    }
                ],
            },
        ]
    }
    assert "codemode_nested_run_code" in tool_trace_violates_codemode(row)


def test_multiline_single_quote_fails() -> None:
    code = 'await manim_write(code="line1\nline2", scene_name="Demo")'
    assert run_code_has_multiline_single_quoted_string(code)
    assert "codemode_multiline_single_quote" in codemode_violations(code)


def test_async_def_compile_manim_code_fails() -> None:
    """Lorenz-style mock: model redefines compile_manim_code inside run_code."""
    code = (
        "async def compile_manim_code(code: str, scene_name: str = 'scene') -> str:\n"
        "    import json\n"
        '    return json.dumps({"status": "success"})\n'
        "\n"
        'code = """\n'
        "from manim import *\n"
        "class LorenzAttractor(Scene):\n"
        "    def construct(self):\n"
        "        pass\n"
        '"""\n'
        "print(await compile_manim_code(code=code, scene_name='LorenzAttractor'))\n"
    )
    assert run_code_has_tool_redefinition(code)
    assert "codemode_tool_redefinition" in codemode_violations(code)
    row = {
        "messages": [
            {"role": "user", "content": "lorenz"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "run_code",
                            "arguments": {"code": code},
                        },
                    }
                ],
            },
        ]
    }
    assert "codemode_tool_redefinition" in tool_trace_violates_codemode(row)


def test_await_compile_without_redefinition_passes() -> None:
    code = (
        'code = """\n'
        "from manim import *\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        pass\n"
        '"""\n'
        "await manim_write(code=code, scene_name='Demo')\n"
        "await compile_manim_code(code=code, scene_name='Demo')\n"
    )
    assert not run_code_has_tool_redefinition(code)
    assert "codemode_tool_redefinition" not in codemode_violations(code)


def test_tool_name_only_inside_manim_string_passes() -> None:
    code = (
        'code = """\n'
        "from manim import *\n"
        "# mention compile_manim_code in a comment inside the scene string\n"
        "class Demo(Scene):\n"
        "    def construct(self):\n"
        "        pass\n"
        '"""\n'
        "await compile_manim_code(code=code, scene_name='Demo')\n"
    )
    assert not run_code_has_tool_redefinition(code)


def test_from_tools_import_fails() -> None:
    code = (
        "from tools import compile_manim_code\n"
        "await compile_manim_code(code='x', scene_name='Demo')\n"
    )
    assert run_code_has_tool_redefinition(code)
    assert "codemode_tool_redefinition" in codemode_violations(code)
