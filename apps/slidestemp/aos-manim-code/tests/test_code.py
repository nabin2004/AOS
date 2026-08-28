import pytest
from aos_manim_core import get_theme, set_theme
from aos_manim_code import (
    CodeWindow,
    StackFrameMobject,
    CallStackMobject,
    trace_factorial_execution,
    trace_fibonacci_execution,
    AstSyntaxValidator,
    StackDepthValidator,
)


def test_code_window():
    set_theme("academic_oxford")
    code = "def add(a, b):\n    return a + b"
    win = CodeWindow(code=code, filename="math_ops.py")
    assert len(win.line_mobs) == 2
    win.highlight_line(2)
    assert win.highlight_bar.get_fill_opacity() > 0
    from aos_manim_core import Cue, CueAction

    win.apply_cue(None, Cue(mark="s0", target_id="code0", action=CueAction.STEP, payload={"i": 0}))
    assert win.highlight_bar.get_fill_opacity() > 0


def test_stack_frame_and_call_stack():
    frame = StackFrameMobject("factorial", {"n": 4, "res": 24})
    assert frame.box is not None

    call_stack = CallStackMobject()
    call_stack.push_frame(frame)
    assert len(call_stack.frames_group) == 1

    popped = call_stack.pop_frame()
    assert popped == frame
    assert len(call_stack.frames_group) == 0


def test_recursion_tracers():
    fact_trace = trace_factorial_execution(4)
    assert fact_trace["result"] == 24
    assert len(fact_trace["events"]) > 0

    fib_trace = trace_fibonacci_execution(5)
    assert fib_trace["result"] == 5
    assert len(fib_trace["events"]) > 0


def test_code_validators():
    ast_val = AstSyntaxValidator()
    assert ast_val.validate("def valid_func():\n    return 100").is_valid
    assert not ast_val.validate("def invalid_syntax(:::").is_valid

    stack_val = StackDepthValidator(max_depth=10)
    assert stack_val.validate(5).is_valid
    assert not stack_val.validate(15).is_valid
