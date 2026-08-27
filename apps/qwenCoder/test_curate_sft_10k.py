from __future__ import annotations

import random

from curate_sft_10k import (
    _chat,
    _hash_text,
    scale_targets,
    synthesize_api,
    synthesize_errors,
    synthesize_latex,
    take_unique,
)
from manim_api_lint import is_lint_clean, extract_python


def test_scale_targets_10000() -> None:
    t = scale_targets(10_000)
    assert sum(t.values()) == 10_000
    assert t["api_grounding"] == 800
    assert t["error_correction"] == 1500


def test_synthesize_api_lint_clean() -> None:
    rows = synthesize_api(24, random.Random(0))
    assert len(rows) >= 16
    for row in rows:
        code = extract_python(row["messages"][-1]["content"])
        assert is_lint_clean(code)
        assert row["metadata"]["bucket"] == "api_grounding"


def test_synthesize_latex_no_unicode() -> None:
    rows = synthesize_latex(20, random.Random(0))
    assert len(rows) == 20
    for row in rows:
        text = row["messages"][-1]["content"]
        assert "\u2081" not in text
        assert is_lint_clean(extract_python(text))


def test_synthesize_errors_include_traceback() -> None:
    rows = synthesize_errors([], 14, random.Random(0))
    assert len(rows) == 14
    assert any("element_color" in r["messages"][1]["content"] for r in rows)
    assert any("w\u2081" in r["messages"][1]["content"] or "U+2081" in r["messages"][1]["content"] for r in rows)
    for row in rows:
        assert is_lint_clean(extract_python(row["messages"][-1]["content"]))


def test_take_unique_dedupes() -> None:
    a = _chat("u", "assistant-a", bucket="x", source="t")
    b = _chat("u", "assistant-a", bucket="x", source="t")
    c = _chat("u", "assistant-c", bucket="x", source="t")
    used: set[str] = set()
    out = take_unique([a, b, c], 10, used)
    assert len(out) == 2
    assert _hash_text("assistant-a") in used
