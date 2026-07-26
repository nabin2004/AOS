"""Tests for sandbox/compile diagnostic summarization."""

from error_feedback import summarize_diagnostic_output


def test_passthrough_short_text() -> None:
    text = "Syntax error in code:\nunexpected EOF"
    assert summarize_diagnostic_output(text) == text


def test_deduplicates_repeated_monty_cascade() -> None:
    block = (
        "Type error in code:\n"
        "error[unresolved-import]: Cannot resolve imported module `manim`\n"
        " --> main.py:1:6\n"
        "  |\n"
        "1 | from manim import *\n"
        "  |      ^^^^^\n"
    )
    text = block + "\n\n" + block + "\n\n" + block
    summary = summarize_diagnostic_output(text, max_chars=1200, max_errors=3)
    assert summary.count("error[unresolved-import]") == 1
    assert "duplicate blocks omitted" in summary
    assert len(summary) < len(text)


def test_keeps_first_distinct_errors() -> None:
    text = (
        "Syntax error in code:\nmissing closing quote at line 1\n\n"
        "Type error in code:\nerror[unresolved-import]: Cannot resolve imported module `manim`\n\n"
        "Runtime error:\nNameError: name 'Scene' is not defined\n"
    )
    summary = summarize_diagnostic_output(text, max_chars=1200, max_errors=2)
    assert "Syntax error in code:" in summary
    assert "Type error in code:" in summary
    assert "Runtime error:" not in summary


def test_compile_log_tail_is_capped() -> None:
    filler = "INFO: rendering frame\n" * 200
    text = filler + "Compilation failed with return code 1.\nLaTeX Error: missing $"
    summary = summarize_diagnostic_output(text, max_chars=400, max_errors=2)
    assert len(summary) <= 400
    assert "Compilation failed" in summary or "LaTeX Error" in summary
