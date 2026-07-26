"""Unit tests for SFT-local CodeMode star-import filter helpers."""

from __future__ import annotations

from codemode_contract import (
    codemode_violations,
    messages_violate_codemode,
    run_code_has_multiline_single_quoted_string,
    run_code_has_nested_run_code,
    run_code_has_star_import,
)


def test_nested_star_import_allowed() -> None:
    code = (
        "code = '''from manim import *\nclass Demo(Scene): pass'''\n"
        "await manim_write(code=code, scene_name='Demo')"
    )
    assert not run_code_has_star_import(code)


def test_top_level_star_import_rejected() -> None:
    assert run_code_has_star_import("from manim import *\nclass X(Scene):\n    pass\n")


def test_messages_violate_detects_bad_run_code() -> None:
    good = [
        {"role": "user", "content": "go"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "1",
                    "type": "function",
                    "function": {
                        "name": "run_code",
                        "arguments": {
                            "code": (
                                "code = '''from manim import *\\nclass D(Scene): pass'''\n"
                                "await manim_write(code=code, scene_name='D')"
                            )
                        },
                    },
                }
            ],
        },
    ]
    bad = [
        {"role": "user", "content": "go"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "1",
                    "type": "function",
                    "function": {
                        "name": "run_code",
                        "arguments": {"code": "from manim import *\npass\n"},
                    },
                }
            ],
        },
    ]
    assert not messages_violate_codemode(good)
    assert messages_violate_codemode(bad)


def test_codemode_preflight_uses_shared_helper() -> None:
    from infer_tools import _codemode_preflight

    assert _codemode_preflight("from manim import *\npass") is not None
    nested = (
        "code = '''from manim import *\\nclass Demo(Scene): pass'''\\n"
        "await manim_write(code=code, scene_name='Demo')"
    )
    assert _codemode_preflight(nested) is None


def test_nested_run_code_rejected() -> None:
    code = 'await run_code(code=\'await manim_write(code="x", scene_name="X")\')'
    assert run_code_has_nested_run_code(code)
    assert "codemode_nested_run_code" in codemode_violations(code)


def test_multiline_single_quoted_string_rejected() -> None:
    code = 'await manim_write(code="from manim import *\nclass X(Scene): pass", scene_name="X")'
    assert run_code_has_multiline_single_quoted_string(code)
    assert "codemode_multiline_single_quote" in codemode_violations(code)


def test_triple_quoted_multiline_allowed() -> None:
    code = "await manim_write(code='''from manim import *\\nclass X(Scene): pass''', scene_name='X')"
    assert not run_code_has_multiline_single_quoted_string(code)
