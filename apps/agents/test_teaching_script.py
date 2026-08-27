"""Teaching script model, filler checks, and coder prompt shaping."""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError
from pydantic_ai import ModelRetry

_AGENTS = Path(__file__).resolve().parent
if str(_AGENTS) not in sys.path:
    sys.path.insert(0, str(_AGENTS))

from coder_prompt import (  # noqa: E402
    build_coder_user_prompt,
    compact_plan_for_local_coder,
)
from teaching_script import (  # noqa: E402
    TeachingBeat,
    TeachingScript,
    _require_teaching_beats,
)
from tools.voiceover_quality import is_filler_narration  # noqa: E402


def _beat(i: int, narration: str | None = None) -> TeachingBeat:
    return TeachingBeat(
        id=f"b{i}",
        takeaway=f"takeaway {i}",
        visual=f"show object {i}",
        narration=narration
        or (
            f"This step shows why idea {i} matters for the student learning the concept."
        ),
    )


def test_is_filler_narration() -> None:
    assert is_filler_narration("Let's look at this on the board.")
    assert is_filler_narration("Here we have Let's explore the magic.")
    assert is_filler_narration("Watch this next step.")
    assert not is_filler_narration(
        "Euler's formula shows a complex exponential can be written using cosine and sine."
    )


def test_teaching_beat_rejects_filler() -> None:
    try:
        TeachingBeat(
            id="b1",
            takeaway="see the formula",
            visual="Write euler_formula",
            narration="Let's look at this on the board.",
        )
    except ValidationError:
        return
    raise AssertionError("expected ValidationError for filler narration")


def test_require_teaching_beats_count() -> None:
    script = TeachingScript(
        scene_class_name="EulerScene",
        throughline="Connect exponentials to trig.",
        beats=[_beat(i) for i in range(5)],
    )
    try:
        _require_teaching_beats(script)
    except ModelRetry:
        return
    raise AssertionError("expected ModelRetry for too few beats")


def test_require_teaching_beats_ok() -> None:
    script = TeachingScript(
        scene_class_name="EulerScene",
        throughline="Connect exponentials to trig.",
        beats=[_beat(i) for i in range(6)],
    )
    assert _require_teaching_beats(script) is script


def test_compact_plan_keeps_full_teaching_narration() -> None:
    long_line = "A" * 220
    payload = {
        "topic": "Euler's Formula",
        "objectives": ["Understand Euler"],
        "teaching_script": {
            "scene_class_name": "EulersFormulaScene",
            "throughline": "Bridge exponentials and trigonometry.",
            "beats": [
                {
                    "id": "b1",
                    "takeaway": "equality of two representations",
                    "visual": "Write the formula",
                    "narration": long_line,
                    "bookmark_marks": ["exp"],
                }
            ],
        },
        "storyboard_beats": [{"title": "x", "narration": "ignored", "visual": "x"}],
    }
    compact = compact_plan_for_local_coder(payload)
    assert compact["teaching_script"]["beats"][0]["narration"] == long_line
    assert "beats" not in compact


def test_build_coder_user_prompt_includes_teaching_script() -> None:
    prompt = build_coder_user_prompt(
        topic="Euler's Formula",
        subject="math",
        output_dir="/tmp/run",
        plan_payload={
            "topic": "Euler's Formula",
            "teaching_script": {
                "scene_class_name": "EulersFormulaScene",
                "throughline": "Bridge representations.",
                "beats": [
                    {
                        "id": "b1",
                        "takeaway": "two sides are equal",
                        "visual": "Write formula",
                        "narration": "Euler's formula connects exponentials with sine and cosine.",
                    }
                ],
            },
        },
        compact=True,
    )
    assert "teaching_script" in prompt
    assert "Implement teaching_script narration verbatim" in prompt
    assert "Euler's formula connects exponentials with sine and cosine." in prompt


if __name__ == "__main__":
    tests = [
        test_is_filler_narration,
        test_teaching_beat_rejects_filler,
        test_require_teaching_beats_count,
        test_require_teaching_beats_ok,
        test_compact_plan_keeps_full_teaching_narration,
        test_build_coder_user_prompt_includes_teaching_script,
    ]
    for fn in tests:
        fn()
        print(f"ok {fn.__name__}")
    print("all passed")
