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


def test_keeps_init_voiceover_exception() -> None:
    text = (
        "WARNING  SoX could not be found!\n"
        "Animation 0: Partial movie file written\n"
        "Traceback (most recent call last):\n"
        "  File \"scene.py\", line 28, in construct\n"
        "    with self.voiceover(text=\"Let's explore this identity further.\"):\n"
        "Exception: You need to call init_voiceover() before adding a voiceover.\n"
    )
    summary = summarize_diagnostic_output(text, max_chars=1200, max_errors=3)
    assert "init_voiceover" in summary
    assert "You need to call init_voiceover" in summary


def test_rich_traceback_with_sox_warning() -> None:
    text = (
        "[09/09/26 21:32:44] WARNING  SoX could not be found!             __init__.py:10\n"
        "                                 If you do not have SoX, proceed\n"
        "                             here: http://sox.sourceforge.net/\n"
        "Manim Community v0.20.1\n"
        "+--------------------- Traceback (most recent call last) ---------------------+\n"
        "| scene.py:16 in construct                                                    |\n"
        "|   pos = np.random.uniform(-3, 3, 2)                                         |\n"
        "|   charge = Dot(point=pos, color=WHITE)                                      |\n"
        "+-----------------------------------------------------------------------------+\n"
        "ValueError: operands could not be broadcast together with shapes (32,3) (2,)\n"
    )
    summary = summarize_diagnostic_output(text, max_chars=1200, max_errors=3)
    assert "ValueError: operands could not be broadcast" in summary
    assert "Dot(point=pos" in summary
    assert "SoX could not be found" not in summary


