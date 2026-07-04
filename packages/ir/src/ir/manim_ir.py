"""
Intermediate Representation (IR)
=====================================================

A version-pinned, statically-checkable representation of an educational
Manim lecture. The IR is the contract between the planner, the code
compiler, the incremental (beat-by-beat) renderer, and the training
pipeline. Everything downstream of it is meant to be deterministic.

Layer stack — each layer answers exactly ONE question:

    Lecture     -> WHAT are we teaching?          (content, no animation)
    Storyboard  -> HOW should it be taught?       (pedagogy, no Manim)
    Scene       -> WHERE do things live?          (scene graph + camera)
    Beat        -> WHAT changes now?              (state transition)
    [compiler]  -> emit self.play(...) Manim code (not in this file)

Two invariants are enforced here, before any render:

  1. Reference integrity — a beat may only operate on objects that are
     currently live in the scene graph. Creating twice, removing a
     ghost, or touching an undeclared id is rejected. This is the
     IR-level cousin of the undefined-symbol check.

  2. Cognitive load — per-beat limits on new objects, equations, colors,
     simultaneous motion and narration length are enforced against a
     CognitiveLoadPolicy, so an overloaded beat cannot pass validation.

The beat is also the unit of incremental execution: one beat -> one
visual delta -> one frame that can be fed back to the model.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)


# ---------------------------------------------------------------------------
# Frame geometry (ManimCE default frame is ~14.22 wide x 8 tall)
# ---------------------------------------------------------------------------
FRAME_X_SAFE = 7.0   # |x| beyond this drifts off the visible frame
FRAME_Y_SAFE = 4.0   # |y| beyond this drifts off the visible frame


# ===========================================================================
# Controlled vocabularies
#
# These are closed sets on purpose: the model learns a small, real API and
# the compiler owns the (op -> Manim call) mapping. Free-text verbs are how
# you get hallucinated APIs; enums are how you prevent them.
# ===========================================================================
class Subject(str, Enum):
    MATH = "math"
    CS = "cs"
    AI = "ai"


class EntityType(str, Enum):
    # primitives
    CIRCLE = "circle"
    SQUARE = "square"
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    LINE = "line"
    ARROW = "arrow"
    DOT = "dot"
    ARC = "arc"
    POLYGON = "polygon"
    # text / symbolic
    TEXT = "text"                 # -> Text
    MATH_TEX = "math_tex"         # -> MathTex  (an "equation")
    TITLE = "title"               # -> Title
    CODE_BLOCK = "code_block"     # -> Code
    TABLE = "table"               # -> Table
    # coordinate systems
    AXES = "axes"
    NUMBER_LINE = "number_line"
    NUMBER_PLANE = "number_plane"
    COMPLEX_PLANE = "complex_plane"
    GRAPH = "graph"               # plotted function
    # vectors / fields
    VECTOR = "vector"
    VECTOR_FIELD = "vector_field"
    # 3D
    SURFACE = "surface"
    SPHERE = "sphere"
    CUBE = "cube"
    # grouping / mascot
    GROUP = "group"
    PI_CREATURE = "pi_creature"   # NB: not in vanilla ManimCE; compiler must
                                  # target a bundled asset or manim_pi plugin.


class OperationType(str, Enum):
    # --- introduce (CREATE family: make an object newly visible) ---
    CREATE = "create"             # Create
    WRITE = "write"               # Write            (text / tex)
    FADE_IN = "fade_in"           # FadeIn
    DRAW_BORDER = "draw_border"   # DrawBorderThenFill
    GROW = "grow"                 # GrowFromCenter
    # --- transform ---
    TRANSFORM = "transform"       # Transform / ReplacementTransform
    MORPH = "morph"               # TransformMatchingTex / Shapes
    # --- move in space ---
    MOVE = "move"                 # .animate.move_to
    SHIFT = "shift"               # .animate.shift
    ROTATE = "rotate"             # Rotate
    SCALE = "scale"               # .animate.scale
    RESCALE_TO_CORNER = "rescale_to_corner"  # shrink + park (Grant's move)
    # --- emphasise (no state change, pure attention) ---
    HIGHLIGHT = "highlight"       # Indicate / Circumscribe
    FLASH = "flash"               # Flash
    WIGGLE = "wiggle"             # Wiggle
    RECOLOR = "recolor"           # .animate.set_color
    # --- value-driven ---
    UPDATE_VALUE = "update_value" # ValueTracker-driven .animate
    # --- remove (make an object no longer live) ---
    FADE_OUT = "fade_out"         # FadeOut
    UNCREATE = "uncreate"         # Uncreate
    REMOVE = "remove"             # self.remove (instant)


CREATE_FAMILY = {
    OperationType.CREATE,
    OperationType.WRITE,
    OperationType.FADE_IN,
    OperationType.DRAW_BORDER,
    OperationType.GROW,
}
REMOVE_FAMILY = {
    OperationType.FADE_OUT,
    OperationType.UNCREATE,
    OperationType.REMOVE,
}
INSTANT_OPS = {OperationType.REMOVE}  # produce no animation, run_time == 0


class AmbientType(str, Enum):
    """Continuous, low-amplitude motion so a scene never fully freezes."""
    BLINK = "blink"               # pi-creature eyes
    BREATHE = "breathe"           # subtle scale oscillation
    CAMERA_DRIFT = "camera_drift"
    GLOW_PULSE = "glow_pulse"
    OSCILLATE = "oscillate"
    ARROW_FLOW = "arrow_flow"
    SHIMMER = "shimmer"


class StoryboardMove(str, Enum):
    """Pedagogical intent of a storyboard step (the teaching strategy)."""
    HOOK = "hook"
    INTRODUCE = "introduce"
    MOTIVATE = "motivate"
    DEFINE = "define"
    EXAMPLE = "example"
    COUNTEREXAMPLE = "counterexample"
    DERIVE = "derive"
    CONNECT = "connect"
    INSIGHT = "insight"
    RECAP = "recap"
    SUMMARIZE = "summarize"


class SceneTransition(str, Enum):
    FADE_TO_BLACK = "fade_to_black"
    CROSSFADE = "crossfade"
    MORPH_INTO = "morph_into"
    SLIDE = "slide"
    CLEAR_KEEP = "clear_keep"        # wipe most, keep a named subset
    CAMERA_MOVE = "camera_move"
    RESCALE_TO_CORNER = "rescale_to_corner"


class TemplateType(str, Enum):
    """First-class 'magnum opus' animations the planner can reach for."""
    GRADIENT_BOWL = "gradient_bowl"
    NEURAL_NETWORK = "neural_network"
    ATTENTION = "attention"
    COMPLEX_PLANE = "complex_plane"
    FOURIER_CIRCLES = "fourier_circles"
    TAYLOR_APPROX = "taylor_approx"
    GRAPH_TRAVERSAL = "graph_traversal"
    BACKPROP = "backprop"
    VECTOR_FIELD_FLOW = "vector_field_flow"
    DECISION_BOUNDARY = "decision_boundary"
    EPSILON_DELTA = "epsilon_delta"


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    UL = "up_left"
    UR = "up_right"
    DL = "down_left"
    DR = "down_right"


# ===========================================================================
# Leaf value objects
# ===========================================================================
class Branding(BaseModel):
    """Global look. Styles reference this so a single change re-themes all."""
    model_config = ConfigDict(extra="forbid")

    brand_name: str = "AOS"
    tagline: str = "by nabin :-)"
    primary_color: str = "#3B82F6"
    secondary_color: str = "#F59E0B"
    accent_color: str = "#10B981"
    background_color: str = "#0E0E10"
    font_family: str = "sans-serif"
    math_font: str = "Latin Modern Math"
    base_font_size: int = 36
    logo_paths: list[str] = Field(default_factory=list)


class Position(BaseModel):
    """
    Absolute frame coordinates OR relative placement next to another object.
    Frame-safety is validated so objects don't silently drift off-screen.
    """
    model_config = ConfigDict(extra="forbid")

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    # relative placement (mutually informative with x/y): "next to <id>"
    next_to: Optional[str] = None
    direction: Optional[Direction] = None
    buff: float = 0.25

    @model_validator(mode="after")
    def _check_frame_safe(self) -> "Position":
        if self.next_to is None:  # only absolute coords can be range-checked
            if abs(self.x) > FRAME_X_SAFE or abs(self.y) > FRAME_Y_SAFE:
                raise ValueError(
                    f"position ({self.x}, {self.y}) is off the safe frame "
                    f"(|x|<={FRAME_X_SAFE}, |y|<={FRAME_Y_SAFE})"
                )
        return self


class Style(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color: Optional[str] = None
    fill_opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    stroke_width: float = Field(default=4.0, ge=0.0)
    font_size: Optional[int] = None
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    z_index: int = 0


class CognitiveLoadPolicy(BaseModel):
    """
    Learning constraints, not renderer constraints. These encode Grant's
    restraint: reveal little at a time. Enforced per beat by Scene.
    """
    model_config = ConfigDict(extra="forbid")

    max_new_objects_per_beat: int = 3
    max_new_equations_per_beat: int = 1
    max_new_colors_per_beat: int = 2
    max_simultaneous_motion: int = 2
    max_narration_seconds: float = 20.0


DEFAULT_LOAD_POLICY = CognitiveLoadPolicy()


# ===========================================================================
# Scene graph nodes
# ===========================================================================
class SceneObject(BaseModel):
    """
    A node in the scene graph. Declared once, mutated by beats (React-style).
    `visible=False` means it exists in the cast but hasn't been created yet;
    a CREATE-family op brings it on screen.
    """
    model_config = ConfigDict(extra="forbid")

    id: str
    entity_type: EntityType
    position: Position = Field(default_factory=Position)
    style: Style = Field(default_factory=Style)
    layer: int = 0                       # z-ordering within the scene
    visible: bool = False                # initial visibility (pre-first-beat)
    # type-specific payload, e.g. {"radius": 1.5} or {"tex": r"e^{i\pi}=-1"}
    params: dict[str, Any] = Field(default_factory=dict)
    label: str = ""                      # human note for planners / SFT

    @property
    def is_equation(self) -> bool:
        return self.entity_type == EntityType.MATH_TEX


class Camera(BaseModel):
    model_config = ConfigDict(extra="forbid")

    center: Position = Field(default_factory=Position)
    zoom: float = Field(default=1.0, gt=0.0)
    phi: float = 0.0                     # 3D polar (radians)
    theta: float = 0.0                   # 3D azimuth (radians)
    is_3d: bool = False


# ===========================================================================
# Beat: the state transition (animation + narration + ambient)
# ===========================================================================
class Operation(BaseModel):
    """An action == an operation applied to one entity. There is no
    standalone 'Actions' concept: Operation(target)."""
    model_config = ConfigDict(extra="forbid")

    target: str                          # SceneObject.id
    op: OperationType
    run_time: float = Field(default=1.0, ge=0.0)
    params: dict[str, Any] = Field(default_factory=dict)
    # optional: play concurrently with the previous op instead of after it
    with_previous: bool = False

    @model_validator(mode="after")
    def _instant_ops_have_zero_runtime(self) -> "Operation":
        if self.op in INSTANT_OPS and self.run_time != 0.0:
            raise ValueError(f"{self.op.value} is instant; run_time must be 0")
        return self


class NarrationSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    # estimate; ~2.7 words/sec is a calm lecture pace
    est_seconds: float = Field(default=0.0, ge=0.0)
    emphasis: list[str] = Field(default_factory=list)  # phrases to stress

    @model_validator(mode="after")
    def _estimate_duration(self) -> "NarrationSegment":
        if self.est_seconds == 0.0 and self.text.strip():
            words = len(self.text.split())
            object.__setattr__(self, "est_seconds", round(words / 2.7, 1))
        return self


class AmbientAnimation(BaseModel):
    """Runs continuously across a beat's hold so nothing freezes."""
    model_config = ConfigDict(extra="forbid")

    type: AmbientType
    target: Optional[str] = None         # entity id, or None for camera/scene
    amplitude: float = Field(default=0.1, ge=0.0)
    period: float = Field(default=2.0, gt=0.0)


class Beat(BaseModel):
    """
    One logical animation step == one visual delta == one renderable frame.
    A beat may animate then hold; during the hold, narration plays and
    ambient animations keep subtle motion alive.
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"beat_{uuid4().hex[:8]}")
    animation_segment: list[Operation] = Field(default_factory=list)
    narration: Optional[NarrationSegment] = None
    hold_seconds: float = Field(default=0.0, ge=0.0)   # dwell after animating
    ambient: list[AmbientAnimation] = Field(default_factory=list)

    @property
    def moving_ops(self) -> list[Operation]:
        return [o for o in self.animation_segment if o.op not in INSTANT_OPS]

    @property
    def total_seconds(self) -> float:
        anim = sum(o.run_time for o in self.animation_segment)
        narr = self.narration.est_seconds if self.narration else 0.0
        return round(max(anim + self.hold_seconds, narr), 1)


# ===========================================================================
# Scene: the visual arrangement + the beats that mutate it
# ===========================================================================
class Scene(BaseModel):
    """
    Owns a scene graph and an ordered list of beats. This is where the two
    core invariants are enforced. Scenes are composable/reusable: a
    COMPLEX_PLANE scene can be pulled into Euler, Fourier, roots-of-unity.
    """
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = ""
    reusable: bool = False
    template: Optional[TemplateType] = None
    camera: Camera = Field(default_factory=Camera)
    scene_graph: list[SceneObject] = Field(default_factory=list)
    beats: list[Beat] = Field(default_factory=list)
    enter_transition: Optional[SceneTransition] = None
    exit_transition: Optional[SceneTransition] = None

    @field_validator("scene_graph")
    @classmethod
    def _unique_ids(cls, graph: list[SceneObject]) -> list[SceneObject]:
        ids = [o.id for o in graph]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate scene object id(s): {sorted(dupes)}")
        return graph

    @model_validator(mode="after")
    def _validate_dynamics(self, info: ValidationInfo) -> "Scene":
        """Walk the beats as a mini-interpreter: enforce reference integrity
        and cognitive-load limits. A CognitiveLoadPolicy may be injected via
        validation context, else the default is used."""
        policy = DEFAULT_LOAD_POLICY
        ctx = getattr(info, "context", None) or {}
        if isinstance(ctx.get("load_policy"), CognitiveLoadPolicy):
            policy = ctx["load_policy"]

        types: dict[str, EntityType] = {o.id: o.entity_type for o in self.scene_graph}
        live: set[str] = {o.id for o in self.scene_graph if o.visible}

        for bi, beat in enumerate(self.beats):
            new_objects = 0
            new_equations = 0
            new_colors: set[str] = set()

            for op in beat.animation_segment:
                if op.target not in types:
                    raise ValueError(
                        f"beat[{bi}] {op.op.value} targets undeclared id "
                        f"'{op.target}' (not in scene_graph of '{self.id}')"
                    )
                if op.op in CREATE_FAMILY:
                    if op.target in live:
                        raise ValueError(
                            f"beat[{bi}] creates '{op.target}' which is "
                            f"already live in scene '{self.id}'"
                        )
                    live.add(op.target)
                    new_objects += 1
                    if types[op.target] == EntityType.MATH_TEX:
                        new_equations += 1
                elif op.op in REMOVE_FAMILY:
                    if op.target not in live:
                        raise ValueError(
                            f"beat[{bi}] removes '{op.target}' which is not "
                            f"live in scene '{self.id}'"
                        )
                    live.discard(op.target)
                else:  # transform / move / emphasise
                    if op.target not in live:
                        raise ValueError(
                            f"beat[{bi}] {op.op.value} on '{op.target}' before "
                            f"it is created in scene '{self.id}'"
                        )
                if "color" in op.params and op.params["color"]:
                    new_colors.add(str(op.params["color"]))

            # --- cognitive-load gates ---
            if new_objects > policy.max_new_objects_per_beat:
                raise ValueError(
                    f"beat[{bi}] introduces {new_objects} objects "
                    f"(max {policy.max_new_objects_per_beat})"
                )
            if new_equations > policy.max_new_equations_per_beat:
                raise ValueError(
                    f"beat[{bi}] introduces {new_equations} equations "
                    f"(max {policy.max_new_equations_per_beat})"
                )
            if len(new_colors) > policy.max_new_colors_per_beat:
                raise ValueError(
                    f"beat[{bi}] introduces {len(new_colors)} new colors "
                    f"(max {policy.max_new_colors_per_beat})"
                )
            if len(beat.moving_ops) > policy.max_simultaneous_motion:
                raise ValueError(
                    f"beat[{bi}] has {len(beat.moving_ops)} concurrent moving "
                    f"ops (max {policy.max_simultaneous_motion})"
                )
            if beat.narration and beat.narration.est_seconds > policy.max_narration_seconds:
                raise ValueError(
                    f"beat[{bi}] narration is {beat.narration.est_seconds}s "
                    f"(max {policy.max_narration_seconds}s)"
                )
        return self

    @property
    def duration_seconds(self) -> float:
        return round(sum(b.total_seconds for b in self.beats), 1)


# ===========================================================================
# Storyboard + Lecture (content / pedagogy layers — no Manim)
# ===========================================================================
class StoryboardStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    move: StoryboardMove
    goal: str                            # why we show this
    scene_id: str                        # which Scene realizes it


class Storyboard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str                            # e.g. "Introduce Euler's formula"
    steps: list[StoryboardStep] = Field(default_factory=list)


class Lecture(BaseModel):
    """Content layer: what to teach. No animation lives here."""
    model_config = ConfigDict(extra="forbid")

    topic: str
    subject: Subject
    greeting: str = ""                   # time-of-day aware (filled at runtime)
    assumptions: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    opener: str = ""                     # the "solid opener" hook
    learning_outcomes: list[str] = Field(default_factory=list)


class OpeningScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_name: str = "AOS"
    tagline: str = "by Nabin :-)"
    dedication: list[str] = Field(default_factory=list)
    credit_logos: list[str] = Field(default_factory=list)


class EndingScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closer: str = ""
    repo_url: str = ""
    show_qr: bool = True
    suggested_next_topics: list[str] = Field(default_factory=list)


# ===========================================================================
# Top-level document
# ===========================================================================
class LectureIR(BaseModel):
    """
    The full, self-contained, version-pinned lecture. Ordering of `scenes`
    is playback order; the storyboard references scenes by id.
    """
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(default_factory=lambda: uuid4().hex)
    manim_version: str = "0.18.1"        # the pinned target; kills fork drift
    ir_version: str = "1.0.0"
    duration_target_seconds: Optional[float] = None

    branding: Branding = Field(default_factory=Branding)
    load_policy: CognitiveLoadPolicy = Field(default_factory=CognitiveLoadPolicy)

    lecture: Lecture
    storyboard: Storyboard
    scenes: list[Scene] = Field(default_factory=list)

    opening: OpeningScene = Field(default_factory=OpeningScene)
    ending: EndingScene = Field(default_factory=EndingScene)

    @model_validator(mode="after")
    def _storyboard_refs_exist(self) -> "LectureIR":
        scene_ids = {s.id for s in self.scenes}
        dupes = {s.id for s in self.scenes if [x.id for x in self.scenes].count(s.id) > 1}
        if dupes:
            raise ValueError(f"duplicate scene id(s): {sorted(dupes)}")
        for step in self.storyboard.steps:
            if step.scene_id not in scene_ids:
                raise ValueError(
                    f"storyboard step '{step.move.value}' references unknown "
                    f"scene_id '{step.scene_id}'"
                )
        return self

    @property
    def duration_seconds(self) -> float:
        return round(sum(s.duration_seconds for s in self.scenes), 1)