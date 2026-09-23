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
    class MockResult:
        async def stream_text(self, delta: bool):
            yield "# A plan long enough to avoid fallback\n" + ("details\n" * 20)

    class MockAgent:
        def run_stream(self, *args, **kwargs):
            from contextlib import asynccontextmanager
            @asynccontextmanager
            async def _ctx():
                yield MockResult()
            return _ctx()

    def fake_get_composer_agent(*args, **kwargs):
        return MockAgent()

    import app.agents.hitl_agents as hitl_agents
    monkeypatch.setattr(hitl_agents, "get_composer_agent", fake_get_composer_agent)

    frames = [
        json.loads(frame.removeprefix("data: ").strip())
        async for frame in manim_studio.compose_plan_stream_service("Explain a derivative")
    ]

    assert {frame["type"] for frame in frames} >= {"start", "status", "token", "done"}


def test_extract_manim_code():
    from app.agents.hitl_agents import extract_manim_code

    # 1. Fenced with python tag
    fenced_python = """Here is the scene:
```python
from manim import *

class CircleScene(Scene):
    def construct(self):
        c = Circle()
        self.play(Create(c))
```
Enjoy!"""
    code, scene = extract_manim_code(fenced_python)
    assert "class CircleScene(Scene):" in code
    assert scene == "CircleScene"
    assert "from manim import *" in code

    # 2. ThreeDScene inheritance
    fenced_3d = """```py
class Sphere3DScene(ThreeDScene):
    def construct(self):
        pass
```"""
    code, scene = extract_manim_code(fenced_3d)
    assert scene == "Sphere3DScene"
    assert "from manim import *" in code

    # 3. Missing `from manim import *` automatically added
    raw_snippet = """class VectorScene(Scene):
    def construct(self):
        pass"""
    code, scene = extract_manim_code(raw_snippet)
    assert scene == "VectorScene"
    assert code.startswith("from manim import *")


def test_error_classifier_and_guidance():
    from app.agents.error_classifier import classify_error, get_repair_guidance, ErrorCategory

    # Auth error should not be repairable
    auth_err = classify_error("401 Unauthorized: Invalid API Key")
    assert auth_err.category == ErrorCategory.AUTHENTICATION_ERROR
    assert auth_err.is_repairable is False

    # LaTeX error should be repairable with LaTeX guidance
    latex_err = classify_error("! LaTeX Error: File `standalone.cls` not found")
    assert latex_err.category == ErrorCategory.MANIM_RENDER_ERROR
    assert latex_err.is_repairable is True
    guidance = get_repair_guidance(latex_err)
    assert "LaTeX" in guidance or "MathTex" in guidance

    # Mobject index error
    index_err = classify_error("IndexError: list index out of range in formula[5]")
    assert index_err.category == ErrorCategory.MANIM_RENDER_ERROR
    assert index_err.is_repairable is True
    guidance = get_repair_guidance(index_err)
    assert "Mobject index" in guidance


@pytest.mark.anyio
async def test_repair_code_service_rejects_non_repairable_errors():
    from fastapi import HTTPException
    from app.services.manim_studio import repair_code_service

    with pytest.raises(HTTPException) as exc_info:
        await repair_code_service(
            code="class S(Scene): pass",
            error="401 Unauthorized: Invalid API key",
        )
    assert exc_info.value.status_code == 400
    assert "AUTHENTICATION_ERROR" in str(exc_info.value.detail)


@pytest.mark.anyio
async def test_code_stream_sse_frames(monkeypatch):
    class MockResult:
        async def stream_text(self, delta: bool):
            yield "```python\nfrom manim import *\n\nclass WaveScene(Scene):\n    def construct(self):\n        pass\n```"

    class MockAgent:
        def run_stream(self, *args, **kwargs):
            from contextlib import asynccontextmanager
            @asynccontextmanager
            async def _ctx():
                yield MockResult()
            return _ctx()

    def fake_get_coder_agent(*args, **kwargs):
        return MockAgent()

    import app.agents.hitl_agents as hitl_agents
    monkeypatch.setattr(hitl_agents, "get_coder_agent", fake_get_coder_agent)

    frames = [
        json.loads(frame.removeprefix("data: ").strip())
        async for frame in manim_studio.synthesize_code_stream_service("Plan content")
    ]

    types = [f["type"] for f in frames]
    assert "start" in types
    assert "status" in types
    assert "token" in types
    assert "done" in types

    done_frame = next(f for f in frames if f["type"] == "done")
    assert done_frame["scene_name"] == "WaveScene"
    assert "class WaveScene(Scene):" in done_frame["code"]
