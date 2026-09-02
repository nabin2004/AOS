from __future__ import annotations

import json
from pathlib import Path

from curate_sft_5k import (
    synthesize_api_grounding,
    synthesize_traceback_repairs,
    synthesize_updaters,
    synthesize_scientific,
    synthesize_pedagogical,
    curate_5k_dataset,
)
from manim_api_lint import is_lint_clean, extract_python
import random


def test_synthesize_api_grounding_clean():
    rng = random.Random(42)
    rows = synthesize_api_grounding(10, rng)
    assert len(rows) == 10
    for r in rows:
        code = extract_python(r["messages"][-1]["content"])
        assert is_lint_clean(code)


def test_synthesize_updaters_clean():
    rng = random.Random(42)
    rows = synthesize_updaters(10, rng)
    assert len(rows) == 10
    for r in rows:
        code = extract_python(r["messages"][-1]["content"])
        assert "always_redraw" in code or "add_updater" in code or "ValueTracker" in code


def test_synthesize_scientific_clean():
    rng = random.Random(42)
    rows = synthesize_scientific(10, rng)
    assert len(rows) == 10
    for r in rows:
        code = extract_python(r["messages"][-1]["content"])
        assert "np." in code or "sp." in code or "scipy" in code


def test_curate_5k_dataset_output(tmp_path: Path):
    rows = curate_5k_dataset(tmp_path)
    assert len(rows) == 5_000
    out_file = tmp_path / "train.jsonl"
    assert out_file.is_file()

    with out_file.open(encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]
    assert len(lines) == 5_000
