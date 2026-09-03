from uuid import uuid4

import pytest

from educlaw.animateworkflow.compiler import compile_final_code
from educlaw.animateworkflow.prompts import CODE_GENERATOR_INSTRUCTIONS
from educlaw.animateworkflow.contracts import (
    AnimationCall,
    CompileError,
    CompileResult,
    FailureCategory,
    FinalCode,
    NarrationStep,
    SceneObject,
    SceneStep,
    LessonPlan,
    VideoPlan,
    RequestClassification,
    Audience,
    OutputType,
)
from educlaw.animateworkflow.validator import validate_generated_code


def make_scene(*, target: str = "title") -> SceneStep:
    return SceneStep(
        scene_id=uuid4(),
        name="intro",
        purpose="introduce the topic",
        code="class Intro: pass",
        visual_description="title",
        objects=[SceneObject(name="title", obj_type="Text")],
        animations=[AnimationCall(animation_type="Write", targets=[target])],
    )


def test_agents_module_imports_without_api_key():
    import educlaw.animateworkflow.agents as agents

    assert callable(agents.build_agents)


def test_scene_rejects_unknown_animation_targets():
    with pytest.raises(ValueError, match="unknown scene objects"):
        make_scene(target="missing")


def test_narration_scene_id_is_uuid():
    scene_id = uuid4()

    narration = NarrationStep(scene_id=scene_id, narration="Explain the idea")

    assert narration.scene_id == scene_id


def test_compile_result_requires_consistent_output():
    with pytest.raises(ValueError, match="output path"):
        CompileResult(success=True)

    result = CompileResult(
        success=False,
        errors=[CompileError(category=FailureCategory.SYNTAX_ERROR, message="bad code")],
    )

    assert result.is_consistent


def test_compile_final_code_uses_sandbox(monkeypatch, tmp_path):
    class FakeProcess:
        returncode = 0
        stdout = ""
        stderr = ""

    class FakeSandbox:
        def __init__(self, cwd, *, quality):
            self.cwd = cwd

        def manim_argv(self, scene_file, scene_name):
            return ["fake-manim", scene_file, scene_name]

        def run(self, argv, timeout):
            output = self.cwd / "media" / "videos" / "generated_scene" / "480p15"
            output.mkdir(parents=True)
            (output / "Intro.mp4").write_bytes(b"video")
            return FakeProcess()

    monkeypatch.setattr("educlaw.animateworkflow.compiler.DockerSandbox", FakeSandbox)

    result = compile_final_code(
        FinalCode(code="class Intro: pass", scene_name="Intro"),
        cwd=tmp_path,
    )

    assert result.success
    assert result.output_path and result.output_path.endswith("Intro.mp4")


@pytest.mark.parametrize(
    ("code", "category"),
    [
        ("class Intro(: pass", FailureCategory.SYNTAX_ERROR),
        ("class Intro:\n    def construct(self):\n        self.play(Background(WHITE))", FailureCategory.HALLUCINATED_KWARGS),
        ("class Intro:\n    def construct(self):\n        self.play(Voiceover('hi'))", FailureCategory.HALLUCINATED_KWARGS),
    ],
)
def test_generated_code_preflight_detects_known_failures(code, category):
    errors = validate_generated_code(FinalCode(code=code, scene_name="Intro"))

    assert errors
    assert errors[0].category == category


def test_compile_docker_failure_is_environment_error(monkeypatch, tmp_path):
    class FakeSandbox:
        def __init__(self, cwd, *, quality):
            pass

        def manim_argv(self, scene_file, scene_name):
            return ["docker", "run"]

        def run(self, argv, timeout):
            raise FileNotFoundError("dockerDesktopLinuxEngine pipe not found")

    monkeypatch.setattr("educlaw.animateworkflow.compiler.DockerSandbox", FakeSandbox)
    result = compile_final_code(FinalCode(code="class Intro: pass", scene_name="Intro"), cwd=tmp_path)

    assert result.errors[0].category == FailureCategory.ENVIRONMENT_ERROR


def test_lesson_plan_can_validate_request_video_id():
    video_id = uuid4()
    plan = LessonPlan(videos=[VideoPlan(video_id=video_id, title="Intro", duration_minutes=1, scenes=[])])
    request = RequestClassification(
        video_id=video_id,
        topic="fractions",
        subject="mathematics",
        audience=Audience.GRADE,
        output_type=OutputType.MANIM_VIDEO,
    )

    assert plan.validate_video_ids(request.video_id) is plan


def test_prompt_requires_voiceover_and_numerical_ode_rules():
    assert "self.voiceover" in CODE_GENERATOR_INSTRUCTIONS
    assert "numerical integration" in CODE_GENERATOR_INSTRUCTIONS
    assert "Background(...)" in CODE_GENERATOR_INSTRUCTIONS


def test_bookmark_validation_detects_undefined_bookmarks():
    code = """\
from manim import *
from manim_voiceover import VoiceoverScene

class MyScene(VoiceoverScene):
    def construct(self):
        with self.voiceover(text="Here is a step <bookmark mark='step1'/>") as tracker:
            self.wait_until_bookmark("nonexistent_step")
"""
    errors = validate_generated_code(FinalCode(code=code, scene_name="MyScene"))
    assert errors
    assert any("undefined bookmark" in err.message for err in errors)


def test_manim_voiceover_service_sandbox(tmp_path):
    from pathlib import Path
    from educlaw.sandbox.docker import DockerSandbox, ManimVoiceoverService

    sandbox = DockerSandbox(tmp_path)
    service = ManimVoiceoverService(sandbox, voice="alba")
    cache_path = service.ensure_cache_dir()
    assert cache_path.exists()
    snippet = service.generate_service_code()
    assert "set_speech_service" in snippet

