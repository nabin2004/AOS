from pathlib import Path
from uuid import uuid4

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from educlaw.animateworkflow.contracts import (
    Audience,
    CompileResult,
    FinalCode,
    LessonPlan,
    NarrationPlan,
    NarrationStep,
    SceneObject,
    SceneStep,
    VideoPlan,
)
from educlaw.courses.contracts import (
    Course,
    CourseSyllabus,
    LectureSpec,
    RenderStatus,
    VisualGrammar,
)
from educlaw.courses.orchestrator import CourseOrchestrator


@pytest.fixture
def mock_course_agents():
    scene_id_1 = uuid4()
    scene_id_2 = uuid4()

    mock_syllabus = CourseSyllabus(
        title="Fourier Analysis",
        topic="Fourier transform and series",
        subject="Mathematics",
        overview="Unraveling signals into frequency domain.",
        lectures=[
            LectureSpec(
                lecture_number=1,
                title="Fourier Series and Rotating Vectors",
                description="Circles wrapping around circles.",
                key_concepts=["Epicycles", "Harmonics"],
            ),
            LectureSpec(
                lecture_number=2,
                title="Continuous Fourier Transform",
                description="Taking period to infinity.",
                key_concepts=["Frequency spectrum", "Integration"],
            ),
        ],
    )

    mock_scene_plan = LessonPlan(
        videos=[
            VideoPlan(
                video_id=uuid4(),
                title="Epicycles",
                duration_minutes=2.0,
                scenes=[
                    SceneStep(
                        scene_id=scene_id_1,
                        name="circle_step",
                        purpose="intro",
                        code="self.play(Create(Circle()))",
                        visual_description="A spinning circle",
                        objects=[SceneObject(name="circle", obj_type="Circle")],
                        animations=[],
                    )
                ],
            )
        ]
    )

    mock_narration_plan = NarrationPlan(
        steps=[
            NarrationStep(
                scene_id=scene_id_1,
                narration="Behold the spinning vector trace out frequencies.",
            )
        ]
    )

    mock_code = FinalCode(
        code="class FourierScene(VoiceoverScene):\n    def construct(self):\n        pass",
        scene_name="FourierScene",
    )

    agent_curriculum = Agent(
        model=TestModel(custom_output_args=mock_syllabus.model_dump(mode="json")),
        output_type=CourseSyllabus,
    )
    agent_scene = Agent(
        model=TestModel(custom_output_args=mock_scene_plan.model_dump(mode="json")),
        output_type=LessonPlan,
    )
    agent_narration = Agent(
        model=TestModel(custom_output_args=mock_narration_plan.model_dump(mode="json")),
        output_type=NarrationPlan,
    )
    agent_code = Agent(
        model=TestModel(custom_output_args=mock_code.model_dump(mode="json")),
        output_type=FinalCode,
    )
    agent_notes = Agent(
        model=TestModel(custom_output_text="# Fourier Series Notes\nKey intuition on rotating vectors."),
        output_type=str,
    )

    return (agent_curriculum, agent_scene, agent_narration, agent_code, agent_notes)


@pytest.mark.asyncio
async def test_orchestrator_plan_syllabus(mock_course_agents, tmp_path):
    orchestrator = CourseOrchestrator(agents=mock_course_agents)
    course = await orchestrator.plan_syllabus(
        "Fourier Analysis",
        num_lectures=2,
        workspace_dir=tmp_path,
    )

    assert course.title == "Fourier Analysis"
    assert course.slug == "fourier-analysis"
    assert len(course.lectures) == 2
    assert course.lectures[0].status == RenderStatus.PENDING


@pytest.mark.asyncio
async def test_orchestrator_generate_course_end_to_end(mock_course_agents, tmp_path, monkeypatch):
    # Mock compile_final_code so it returns success without needing Docker daemon during test
    fake_video = tmp_path / "fake_video.mp4"
    fake_video.write_text("dummy video")

    def mock_compile(final_code, cwd, quality="l", timeout=180):
        return CompileResult(success=True, output_path=str(fake_video))

    monkeypatch.setattr("educlaw.courses.orchestrator.compile_final_code", mock_compile)

    orchestrator = CourseOrchestrator(agents=mock_course_agents)
    course = await orchestrator.generate_course(
        "Fourier Analysis",
        num_lectures=2,
        render=True,
        workspace_dir=tmp_path,
    )

    assert course.slug == "fourier-analysis"
    assert len(course.lectures) == 2
    assert course.lectures[0].status == RenderStatus.RENDERED
    assert course.lectures[1].status == RenderStatus.RENDERED
    assert course.lectures[0].study_notes is not None
    assert course.lectures[0].final_code is not None

    # Check files on disk
    course_dir = tmp_path / ".educlaw" / "courses" / "fourier-analysis"
    assert (course_dir / "course.json").exists()
    assert (course_dir / "course_manifest.json").exists()
    assert (course_dir / "lecture_01" / "scene.py").exists()
    assert (course_dir / "lecture_01" / "notes.md").exists()
    assert (course_dir / "lecture_02" / "scene.py").exists()


@pytest.mark.asyncio
async def test_orchestrator_resume_course(mock_course_agents, tmp_path, monkeypatch):
    fake_video = tmp_path / "fake_video.mp4"
    fake_video.write_text("dummy video")

    def mock_compile(final_code, cwd, quality="l", timeout=180):
        return CompileResult(success=True, output_path=str(fake_video))

    monkeypatch.setattr("educlaw.courses.orchestrator.compile_final_code", mock_compile)

    orchestrator = CourseOrchestrator(agents=mock_course_agents)
    # Generate without rendering (leaves status at CODED)
    course = await orchestrator.generate_course(
        "Fourier Analysis",
        num_lectures=2,
        render=False,
        workspace_dir=tmp_path,
    )
    assert course.lectures[0].status == RenderStatus.CODED

    # Resume with rendering enabled
    resumed_course = await orchestrator.resume_course(
        course.slug,
        render=True,
        workspace_dir=tmp_path,
    )
    assert resumed_course.lectures[0].status == RenderStatus.RENDERED
    assert resumed_course.lectures[1].status == RenderStatus.RENDERED
