import json

import pytest
from app.services import manim_studio
from app.services.manim_studio import (
    classify_text_for_manim,
    classify_text_for_manim_sync,
    classify_text_heuristic,
    _generate_fallback_plan,
    _generate_fallback_code,
)


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
    res = classify_text_heuristic(sample_text)
    assert res.animatable is True
    assert res.subject == "math"
    assert "Taylor" in res.topic or "Series" in res.topic or "Formula" in res.topic


def test_classify_for_manim_sync(monkeypatch):
    import app.agents.hitl_agents as hitl_agents

    class MockSuccessAgent:
        async def run(self, *args, **kwargs):
            class Res:
                output = VideoClassifyResponse(
                    animatable=True,
                    subject="math",
                    topic="Taylor Series",
                    reason="Approximation polynomial formulas",
                )
            return Res()

    monkeypatch.setattr(hitl_agents, "get_classifier_agent", lambda *a, **k: MockSuccessAgent())
    sync_res = classify_text_for_manim_sync("Taylor series")
    assert sync_res.animatable is True
    assert sync_res.topic == "Taylor Series"


def test_classify_general_non_animatable():
    sample_text = "The Roman Empire was the post-Republican period of ancient Rome. It included large territorial holdings around the Mediterranean Sea."
    res = classify_text_heuristic(sample_text)
    assert res.animatable is False
    assert res.subject == "unknown"


@pytest.mark.anyio
async def test_classify_text_for_manim_agent_fallback(monkeypatch):
    import app.agents.hitl_agents as hitl_agents

    class FailingAgent:
        async def run(self, *args, **kwargs):
            raise RuntimeError("API timeout simulation")

    monkeypatch.setattr(hitl_agents, "get_classifier_agent", lambda *a, **k: FailingAgent())
    sample_text = "Taylor series expansion $$ f(x) = \\sum f^{(n)}(a)(x-a)^n/n! $$"
    res = await classify_text_for_manim(sample_text)
    assert res.animatable is True
    assert res.subject == "math"


@pytest.mark.anyio
async def test_pydantic_ai_classifier_agent_structured_output():
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    from app.agents.hitl_agents import CLASSIFIER_SYSTEM_PROMPT
    from app.schemas.video_generation import VideoClassifyResponse

    agent = Agent(
        model=TestModel(
            custom_output_args={
                "animatable": True,
                "subject": "math",
                "topic": "Fourier Transform",
                "reason": "Decomposes functions into sinusoidal frequencies suitable for Manim animation.",
            }
        ),
        system_prompt=CLASSIFIER_SYSTEM_PROMPT,
        output_type=VideoClassifyResponse,
    )
    result = await agent.run("Explain the Fourier Transform")
    assert isinstance(result.output, VideoClassifyResponse)
    assert result.output.animatable is True
    assert result.output.subject == "math"
    assert result.output.topic == "Fourier Transform"
    assert "sinusoidal" in result.output.reason


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

    async def fake_classify(*args, **kwargs):
        from app.schemas.video_generation import VideoClassifyResponse
        return VideoClassifyResponse(
            animatable=True,
            subject="math",
            topic="Derivative",
            reason="Calculus rate of change",
        )

    monkeypatch.setattr(manim_studio, "classify_text_for_manim", fake_classify)

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


@pytest.mark.anyio
async def test_hitl_agent_skills():
    from app.agents.hitl_agents import (
        get_composer_agent,
        get_coder_agent,
        get_repair_agent,
    )
    from pydantic_ai_harness import Skills
    from pydantic_ai.models.test import TestModel

    # 1. Composer Agent has Skills capability exposing manim-composer
    composer = get_composer_agent()
    comp_skills = [
        cap for cap in composer.root_capability.capabilities if isinstance(cap, Skills)
    ]
    assert len(comp_skills) == 1
    assert "manim-composer" in comp_skills[0].include
    assert "manimce-best-practices" in comp_skills[0].include

    with composer.override(
        model=TestModel(
            call_tools=[],
            custom_output_text="# Scene Plan",
        )
    ):
        res_comp = await composer.run("Create plan")
        assert res_comp.output == "# Scene Plan"

    # 2. Coder Agent has Skills capability exposing manimce-best-practices & manim-render
    coder = get_coder_agent()
    coder_skills = [
        cap for cap in coder.root_capability.capabilities if isinstance(cap, Skills)
    ]
    assert len(coder_skills) == 1
    assert "manimce-best-practices" in coder_skills[0].include
    assert "manim-render" in coder_skills[0].include

    with coder.override(
        model=TestModel(
            call_tools=[],
            custom_output_text="```python\nfrom manim import *\n```",
        )
    ):
        res_coder = await coder.run("How to position objects")
        assert "from manim import *" in res_coder.output

    # 3. Repair Agent has Skills capability exposing manimce-best-practices & manim-render
    repair = get_repair_agent()
    repair_skills = [
        cap for cap in repair.root_capability.capabilities if isinstance(cap, Skills)
    ]
    assert len(repair_skills) == 1
    assert "manimce-best-practices" in repair_skills[0].include
    assert "manim-render" in repair_skills[0].include

    with repair.override(
        model=TestModel(
            call_tools=[],
            custom_output_text="```python\n# Repaired\n```",
        )
    ):
        res_repair = await repair.run("Fix syntax error")
        assert "Repaired" in res_repair.output


def test_oop_hitl_agent_architecture():
    from app.agents.hitl_agents import (
        HitlLLMResolver,
        HitlCodeExtractor,
        HitlAgentTools,
        HitlAgentFactory,
        HitlRepairRunner,
        HitlAgentService,
        hitl_agent_service,
    )

    resolver = HitlLLMResolver()
    key, url, model = resolver.resolve(api_key="custom-key", base_url="http://localhost:11434", model_name="qwen2.5-coder")
    assert key == "custom-key"
    assert "localhost:11434" in url
    assert model == "qwen2.5-coder"

    extractor = HitlCodeExtractor()
    code, scene = extractor.extract_code(
        "```python\nfrom manim import *\nclass MyCoolScene(Scene):\n    def construct(self):\n        pass\n```",
        default_scene="DefaultScene",
    )
    assert scene == "MyCoolScene"
    assert "class MyCoolScene(Scene):" in code

    tools = HitlAgentTools()
    syntax_valid = tools.validate_syntax("x = 1 + 2")
    assert syntax_valid["valid"] is True
    syntax_invalid = tools.validate_syntax("def invalid syntax:")
    assert syntax_invalid["valid"] is False

    factory = HitlAgentFactory(resolver=resolver)
    assert factory.resolver is resolver

    runner = HitlRepairRunner(extractor=extractor, tools=tools)
    assert runner.extractor is extractor
    assert runner.tools is tools

    custom_service = HitlAgentService(
        resolver=resolver,
        extractor=extractor,
        tools=tools,
        factory=factory,
        repair_runner=runner,
    )
    assert custom_service.resolver is resolver
    assert hitl_agent_service is not None


@pytest.mark.anyio
async def test_oop_manim_studio_architecture():
    from app.services.manim_studio import (
        ManimTextClassifier,
        ManimPlanComposer,
        ManimCodeSynthesizer,
        ManimCodeRepairer,
        ManimRenderEngine,
        ManimStudioService,
        manim_studio_service,
        manim_studio,
    )
    from pathlib import Path
    import tempfile

    classifier = ManimTextClassifier()
    res_heuristic = classifier.classify_heuristic("Integral of e^x dx is e^x + C")
    assert res_heuristic.animatable is True
    assert res_heuristic.subject == "math"

    composer = ManimPlanComposer()
    fallback_plan = composer.generate_fallback_plan("Derivation of Euler's formula", "Euler's Formula")
    assert "Visualizing Euler's Formula" in fallback_plan
    assert "## Scene 1:" in fallback_plan

    synthesizer = ManimCodeSynthesizer()
    fallback_code, scene_name = synthesizer.generate_fallback_code(fallback_plan)
    assert "class EulerFormulaScene(Scene):" in fallback_code
    assert scene_name == "EulerFormulaScene"

    repairer = ManimCodeRepairer()
    assert repairer is not None

    renderer = ManimRenderEngine()
    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_path = Path(tmp_dir)
        # Should gracefully return error log if no manim or docker is available or if execution fails
        mp4_path, err = renderer.execute_render(
            code="invalid code",
            scene_name="TestScene",
            quality="l",
            workspace_dir=fake_path,
        )
        assert mp4_path is None
        assert isinstance(err, str)

    # Test master facade and dependency injection
    studio = ManimStudioService(
        classifier=classifier,
        composer=composer,
        synthesizer=synthesizer,
        repairer=repairer,
        renderer=renderer,
    )
    assert studio.classifier is classifier
    assert studio.composer is composer
    assert studio.synthesizer is synthesizer
    assert studio.repairer is repairer
    assert studio.renderer is renderer

    assert manim_studio_service is not None
    assert manim_studio is manim_studio_service

