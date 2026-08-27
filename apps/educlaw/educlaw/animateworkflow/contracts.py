from enum import Enum
from anyio import current_time
from pydantic import BaseModel, Field
from uuid import UUID, uuid4



class Audience(str, Enum):
    GRADE = "grade"
    SELF_LEARNER = "self_learner"
    EXPLORING = "exploring"


class VisualStyle(str, Enum):
    STEP_BY_STEP = "step_by_step"
    CINEMATIC = "cinematic"
    CARTOON = "cartoon"


class OutputType(str, Enum):
    MANIM_VIDEO = "manim_video"
    CHAT_MESSAGE = "chat_message"


class FailureCategory(str, Enum):
    HALLUCINATED_KWARGS = "hallucinated_kwargs"
    MISSING_IMPORTS = "missing_imports"
    MALFORMED_POINT_ARRAYS = "malformed_point_arrays"
    LATEX_ERROR = "latex_error"
    SYNTAX_ERROR = "syntax_error"
    RENDER_TIMEOUT = "render_timeout"

"""
USER: Teach me about the Lorenz attractor
----
[1] RequestAnalyzerAgent:
    - topic: "Lorenz attractor"
    - subject: "Mathematics / Dynamical Systems"
    - audience: EXPLORING
    - visual_style: CINEMATIC
    - narration: true
    - output_type: MANIM_VIDEO

[PARALLEL: 2a, 2b — both depend only on `request`]

[2a] CapabilityPlannerAgent:
    - required_tools: ["manim", "manim-voiceover", "latex", "scipy"]
    - tts_service: "elevenlabs"
    - sequencing_strategy: "concept_before_formalism"
    - rationale: "3D parametric scene + chaotic-system narration needs
                  scipy for numerical integration, not just symbolic Manim"

[2b] KnowledgeAgent:
    - concepts: ["chaos theory", "sensitive dependence on initial conditions",
                 "strange attractor", "phase space", "ODE system"]
    - facts: [
        "Lorenz system: dx/dt=σ(y-x), dy/dt=x(ρ-z)-y, dz/dt=xy-βz",
        "Classic parameters: σ=10, ρ=28, β=8/3",
        "Discovered by Edward Lorenz in 1963 studying atmospheric convection"
      ]
    - manim_apis: ["ThreeDScene", "ParametricFunction", "ThreeDAxes",
                   "Create", "MoveCamera", "always_redraw"]
    - relevant_skills: ["3d-scene-camera-control", "ode-numerical-integration"]
    - rag_result: [
        RagChunk(source="manim_docs/three_d_scene.md",
                 content="ThreeDScene camera orientation via set_camera_orientation",
                 score=0.91),
        RagChunk(source="kb/lorenz_attractor.md",
                 content="Standard integration via scipy.integrate.odeint",
                 score=0.88),
      ]

[2c] ScenePlannerAgent:
    - LessonPlan.steps:
        SceneStep(scene_id="s0", name="intro", purpose="hook",
            visual_description="Title card, camera slowly pulls back from black",
            objects=[SceneObject(name="title", obj_type="Text")],
            animations=[AnimationCall(animation_type="Write", targets=["title"])])
        SceneStep(scene_id="s1", name="phase_space_setup",
            purpose="establish 3D axes",
            visual_description="ThreeDAxes fades in, camera tilts to isometric",
            objects=[SceneObject(name="axes", obj_type="ThreeDAxes")],
            animations=[AnimationCall(animation_type="Create", targets=["axes"])])
        SceneStep(scene_id="s2", name="single_trajectory",
            purpose="show one solution curve",
            visual_description="One Lorenz curve traces out, butterfly shape emerges",
            objects=[SceneObject(name="curve1", obj_type="ParametricFunction")],
            animations=[AnimationCall(animation_type="Create",
                targets=["curve1"], params={"run_time": "6"})])
        SceneStep(scene_id="s3", name="sensitivity_demo",
            purpose="show divergence from nearby initial conditions",
            visual_description="Second curve from ε-perturbed start diverges visibly",
            objects=[SceneObject(name="curve2", obj_type="ParametricFunction")],
            animations=[AnimationCall(animation_type="Transform",
                targets=["curve1", "curve2"])])
        SceneStep(scene_id="s4", name="outro",
            purpose="recap + fade",
            visual_description="Both curves fade, equations remain, fade to black",
            objects=[SceneObject(name="eqns", obj_type="MathTex")],
            animations=[AnimationCall(animation_type="FadeOut", targets=["curve1","curve2"])])

[2d] NarrationPlannerAgent:
    - NarrationPlan.steps:
        NarrationStep(scene_id="s0",
            narration="In 1963, a meteorologist trying to predict the weather stumbled onto one of math's strangest shapes.",
            bookmarks=[BookMark(bookmark_id="B0", narration_fragment="stumbled onto")])
        NarrationStep(scene_id="s2",
            narration="This is the Lorenz attractor: a solution curve that never repeats, never settles, never escapes.",
            bookmarks=[BookMark(bookmark_id="B1", narration_fragment="never repeats")],
            duration=6.0)
        NarrationStep(scene_id="s3",
            narration="Nudge the starting point by a hair, and the paths tear apart completely — this is the butterfly effect.",
            bookmarks=[BookMark(bookmark_id="B2", narration_fragment="tear apart")])

[5] CodeGeneratorAgent:
    - FinalCode.scene_name: "LorenzAttractorScene"
    - FinalCode.code: |
        class LorenzAttractorScene(ThreeDScene, VoiceoverScene):
            def construct(self):
                self.set_speech_service(ElevenLabsService())
                axes = ThreeDAxes()
                with self.voiceover(text="In 1963, ...") as tracker:
                    self.play(Create(axes))
                ... # curve1/curve2 via scipy.integrate.odeint + ParametricFunction
    - lint: pyflakes clean, manim_api_check passed (no hallucinated kwargs)

[6] CompilerAgent tool:
    - render_manim(FinalCode) → CompileResult
    - success: true
    - output_path: "/render/lorenz_attractor.mp4"
    - errors: []
    - stream: TV-static buffer shown to user while render_manim runs

RUN:
1 --> [2a, 2b, 2c, 2d] --> 5 --> 6

RETRY EDGE (not triggered this run):
CompileResult.errors[].category == RENDER_TIMEOUT  --> retry [5] with reduced run_time hints
CompileResult.errors[].category == MALFORMED_POINT_ARRAYS --> retry [3] (bad SceneObject spec)
"""

class RequestClassification(BaseModel):
    video_id: UUID = Field(default_factory=uuid4)
    topic: str = Field(..., description="The concept/lesson to teach, e.g. 'BODMAS'")
    subject: str = Field(..., description="Broader domain, e.g. 'Mathematics'")
    audience: Audience
    visual_style: VisualStyle | None = None
    narration: bool = Field(default=True, description="Whether to include narration")
    output_type: OutputType
    required_capabilities: list[str] = Field(default_factory=list)
    no_of_videos: int = Field(default=1, description="Number of videos to generate")
    duration_per_video: float | None = Field(default=None, description="Duration in minutes per video")

class RagChunk(BaseModel):
    source: str
    content: str
    score: float | None = None


class KnowledgeResult(BaseModel):
    request: RequestClassification
    concepts: list[str]
    facts: list[str]
    manim_apis: list[str]
    relevant_skills: list[str]
    rag_result: list[RagChunk] = Field(default_factory=list)


class SceneObject(BaseModel):
    name: str
    obj_type: str  # e.g. "MathTex", "Circle"
    properties: dict[str, str] = Field(default_factory=dict)


class AnimationCall(BaseModel):
    animation_type: str  # e.g. "Transform", "Write"
    targets: list[str]  # SceneObject.name refs
    params: dict[str, str] = Field(default_factory=dict)


class SceneStep(BaseModel):
    scene_id: str
    name: str
    purpose: str
    code: str  # Manim code
    visual_description: str
    objects: list[SceneObject]
    animations: list[AnimationCall]

class VideoPlan(BaseModel):
    video_id: UUID
    title: str
    duration_minutes: float
    scenes: list[SceneStep]

class LessonPlan(BaseModel):
    videos: list[VideoPlan]
    # steps: list[SceneStep]
    no_of_videos: int = Field(default=1, description="Number of videos to generate")
    duration_per_video: float | None = Field(default=None, description="Duration in minutes per video")


class BookMark(BaseModel):
    bookmark_id: str  # <bookmark mark='T1'/>
    narration_fragment: str


class NarrationStep(BaseModel):
    scene_id: str  # references SceneStep.scene_id
    narration: str
    bookmarks: list[BookMark] = Field(default_factory=list)
    duration: float | None = None


class NarrationPlan(BaseModel):
    steps: list[NarrationStep]


class FinalCode(BaseModel):
    code: str
    scene_name: str


class CompileError(BaseModel):
    category: FailureCategory
    message: str
    line: int | None = None


class CompileResult(BaseModel):
    success: bool
    output_path: str | None = None
    errors: list[CompileError] = Field(default_factory=list)

    @property
    def is_consistent(self) -> bool:
        return self.success == (len(self.errors) == 0)


class PipelineState(BaseModel):
    """Shared state threaded through your LangGraph nodes (1→2,3,4,5→6→7)."""
    request: RequestClassification | None = None
    knowledge: KnowledgeResult | None = None
    lesson_plan: LessonPlan | None = None
    narration_plan: NarrationPlan | None = None
    final_code: FinalCode | None = None
    compile_result: CompileResult | None = None