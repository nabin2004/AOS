import json

import pytest
from app.services import manim_studio
from app.services.manim_studio import classify_text_for_manim, _generate_fallback_plan, _generate_fallback_code


def test_classify_taylors_formula():
    sample_text = """
    Taylor's formula, named after Brook Taylor, is a mathematical tool that approximates a function using an infinite sum of terms derived from its derivatives at a specific point.
    Key Concepts:
    Taylor Series:
    $$ f(x) = f(a) + f'(a)(x-a) + \\frac{f''(a)}{2!}(x-a)^2 + \\cdots $$
    Maclaurin Series (Special Case):
    When $ a = 0 $, the formula simplifies to:
    $$ f(x) = f(0) + f'(0)x + \\frac{f''(0)}{2!}x^2 + \\cdots $$
    """
    res = classify_text_for_manim(sample_text)
    assert res.animatable is True
    assert res.subject == "math"
    assert "Taylor" in res.topic or "Series" in res.topic or "Formula" in res.topic


def test_classify_general_non_animatable():
    sample_text = "The Roman Empire was the post-Republican period of ancient Rome. It included large territorial holdings around the Mediterranean Sea."
    res = classify_text_for_manim(sample_text)
    assert res.animatable is False
    assert res.subject == "unknown"


def test_fallback_plan_generation():
    plan = _generate_fallback_plan("Taylor's formula approximation", "Taylor's Formula")
    assert "Visualizing Taylor's Formula" in plan
    assert "## Scene 1:" in plan
    assert "## Color Palette" in plan
    assert "## Mathematical Content" in plan


def test_fallback_code_generation():
    code, scene_name = _generate_fallback_code("plan", "Taylor's formula")
    assert "from manim import *" in code
    assert "class TaylorFormulaScene(Scene):" in code
    assert "def construct(self):" in code
    assert scene_name == "TaylorFormulaScene"


@pytest.mark.anyio
async def test_plan_stream_forwards_provider_reasoning_and_status(monkeypatch):
    async def fake_llm_stream(*args, **kwargs):
        yield "status", "Connecting to test-model…"
        yield "thinking", "I will introduce the equation first."
        yield "token", "# A plan long enough to avoid fallback\n" + ("details\n" * 20)

    monkeypatch.setattr(manim_studio, "call_llm_stream", fake_llm_stream)

    frames = [
        json.loads(frame.removeprefix("data: ").strip())
        async for frame in manim_studio.compose_plan_stream_service("Explain a derivative")
    ]

    assert {frame["type"] for frame in frames} >= {"start", "status", "thinking", "token", "done"}
    assert any(frame.get("text") == "I will introduce the equation first." for frame in frames)
