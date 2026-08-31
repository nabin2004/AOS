from pathlib import Path
from uuid import uuid4

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from educlaw.animateworkflow.contracts import (
    AnimationCall,
    Audience,
    CompileError,
    CompileResult,
    FailureCategory,
    FinalCode,
    LessonPlan,
    NarrationPlan,
    NarrationStep,
    OutputType,
    PipelineState,
    RequestClassification,
    SceneObject,
    SceneStep,
    VideoPlan,
    VoiceoverBookMark,
)
from educlaw.animateworkflow.loop import (
    CATEGORY_GUIDANCE,
    WorkflowOrchestrator,
    normalize_lesson_plan,
)


def test_normalize_lesson_plan_updates_and_validates():
    video_id = uuid4()
    classification = RequestClassification(
        video_id=video_id,
        topic="Lorenz Attractor",
        subject="Physics",
        audience=Audience.EXPLORING,
        output_type=OutputType.MANIM_VIDEO,
    )
    plan = LessonPlan(
        videos=[
            VideoPlan(
                video_id=uuid4(),  # Different ID initially
                title="Lorenz Intro",
                duration_minutes=2.0,
                scenes=[],
            )
        ]
    )
    normalized = normalize_lesson_plan(plan, classification)
    assert normalized.videos[0].video_id == video_id


def test_category_guidance_contains_all_critical_failure_categories():
    assert FailureCategory.HALLUCINATED_KWARGS in CATEGORY_GUIDANCE
    assert FailureCategory.MISSING_IMPORTS in CATEGORY_GUIDANCE
    assert FailureCategory.MALFORMED_POINT_ARRAYS in CATEGORY_GUIDANCE
    assert FailureCategory.LATEX_ERROR in CATEGORY_GUIDANCE
    assert FailureCategory.SYNTAX_ERROR in CATEGORY_GUIDANCE
    assert FailureCategory.RENDER_TIMEOUT in CATEGORY_GUIDANCE


@pytest.mark.asyncio
async def test_workflow_orchestrator_step_classify():
    video_id = uuid4()
    test_classification = RequestClassification(
        video_id=video_id,
        topic="calculus derivatives",
        subject="Mathematics",
        audience=Audience.GRADE,
        output_type=OutputType.MANIM_VIDEO,
    )

    agent1 = Agent(
        model=TestModel(custom_output_args=test_classification.model_dump(mode="json")),
        output_type=RequestClassification,
    )
    agent2 = Agent(model=TestModel(call_tools=[]), output_type=LessonPlan)
    agent3 = Agent(model=TestModel(call_tools=[]), output_type=NarrationPlan)
    agent4 = Agent(model=TestModel(call_tools=[]), output_type=FinalCode)

    orchestrator = WorkflowOrchestrator(agents=(agent1, agent2, agent3, agent4))
    result = await orchestrator.step_classify("Teach derivatives visually")

    assert result.topic == "calculus derivatives"
    assert orchestrator.state.request is result


@pytest.mark.asyncio
async def test_workflow_orchestrator_replan_loop(monkeypatch, tmp_path):
    video_id = uuid4()
    scene_id = uuid4()

    classification = RequestClassification(
        video_id=video_id,
        topic="waves",
        subject="Physics",
        audience=Audience.EXPLORING,
        output_type=OutputType.MANIM_VIDEO,
    )

    scene = SceneStep(
        scene_id=scene_id,
        name="wave_intro",
        purpose="show wave",
        code="class Wave: pass",
        visual_description="sine wave",
        objects=[SceneObject(name="wave_curve", obj_type="ParametricFunction")],
        animations=[AnimationCall(animation_type="Create", targets=["wave_curve"])],
    )

    lesson_plan = LessonPlan(
        videos=[VideoPlan(video_id=video_id, title="Wave Video", duration_minutes=1.0, scenes=[scene])]
    )

    narration_plan = NarrationPlan(
        steps=[
            NarrationStep(
                scene_id=scene_id,
                narration="Here is a traveling sinusoidal wave.",
                bookmarks=[VoiceoverBookMark(mark="B0", voiceover_text="traveling wave")],
            )
        ]
    )

    attempt_counter = 0

    def fake_compile_final_code(final_code, *, cwd, quality="l", timeout=180):
        nonlocal attempt_counter
        attempt_counter += 1
        if attempt_counter == 1:
            return CompileResult(
                success=False,
                errors=[CompileError(category=FailureCategory.SYNTAX_ERROR, message="unexpected EOF", line=12)],
            )
        return CompileResult(success=True, output_path=str(cwd / "wave.mp4"))

    monkeypatch.setattr("educlaw.animateworkflow.loop.compile_final_code", fake_compile_final_code)

    code_output = FinalCode(code="class WaveScene: pass", scene_name="WaveScene")
    agent4 = Agent(
        model=TestModel(custom_output_args=code_output.model_dump(mode="json")),
        output_type=FinalCode,
    )

    agent1 = Agent(model=TestModel(call_tools=[]), output_type=RequestClassification)
    agent2 = Agent(model=TestModel(call_tools=[]), output_type=LessonPlan)
    agent3 = Agent(model=TestModel(call_tools=[]), output_type=NarrationPlan)

    orchestrator = WorkflowOrchestrator(
        agents=(agent1, agent2, agent3, agent4),
        max_replans=3,
    )

    final_code, compile_result = await orchestrator.step_generate_and_compile(
        "Teach waves",
        lesson_plan,
        narration_plan,
        workspace_dir=tmp_path,
    )

    assert attempt_counter == 2
    assert compile_result.success
    assert compile_result.output_path == str(tmp_path / "wave.mp4")
    assert final_code.scene_name == "WaveScene"


@pytest.mark.asyncio
async def test_full_workflow_run(monkeypatch, tmp_path):
    video_id = uuid4()
    scene_id = uuid4()

    classification = RequestClassification(
        video_id=video_id,
        topic="Pendulum",
        subject="Physics",
        audience=Audience.EXPLORING,
        output_type=OutputType.MANIM_VIDEO,
    )

    lesson_plan = LessonPlan(
        videos=[
            VideoPlan(
                video_id=video_id,
                title="Pendulum Motion",
                duration_minutes=1.5,
                scenes=[
                    SceneStep(
                        scene_id=scene_id,
                        name="pendulum_swing",
                        purpose="harmonic motion",
                        code="class Pendulum: pass",
                        visual_description="swinging bob",
                        objects=[SceneObject(name="bob", obj_type="Dot")],
                        animations=[AnimationCall(animation_type="Create", targets=["bob"])],
                    )
                ],
            )
        ]
    )

    narration_plan = NarrationPlan(
        steps=[
            NarrationStep(
                scene_id=scene_id,
                narration="A simple pendulum oscillates in periodic harmonic motion.",
            )
        ]
    )

    final_code = FinalCode(code="class PendulumScene: pass", scene_name="PendulumScene")

    def fake_compile(code, *, cwd, quality="l", timeout=180):
        return CompileResult(success=True, output_path=str(cwd / "pendulum.mp4"))

    monkeypatch.setattr("educlaw.animateworkflow.loop.compile_final_code", fake_compile)

    agent1 = Agent(
        model=TestModel(custom_output_args=classification.model_dump(mode="json")),
        output_type=RequestClassification,
    )
    agent2 = Agent(
        model=TestModel(custom_output_args=lesson_plan.model_dump(mode="json")),
        output_type=LessonPlan,
    )
    agent3 = Agent(
        model=TestModel(custom_output_args=narration_plan.model_dump(mode="json")),
        output_type=NarrationPlan,
    )
    agent4 = Agent(
        model=TestModel(custom_output_args=final_code.model_dump(mode="json")),
        output_type=FinalCode,
    )

    events = []

    class FakeDeps:
        cwd = tmp_path
        memory = None

        def emit(self, event, payload):
            events.append((event, payload))

    orchestrator = WorkflowOrchestrator(
        agents=(agent1, agent2, agent3, agent4),
        deps=FakeDeps(),  # type: ignore[arg-type]
    )

    state = await orchestrator.run("Explain pendulum physics", workspace_dir=tmp_path)

    assert state.request.topic == "Pendulum"
    assert state.lesson_plan.videos[0].title == "Pendulum Motion"
    assert state.narration_plan.steps[0].scene_id == scene_id
    assert state.final_code.scene_name == "PendulumScene"
    assert state.compile_result.success
    assert len(events) > 0
