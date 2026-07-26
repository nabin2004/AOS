"""
Intermediate Representation (IR) — v2
=====================================================

A version-pinned, statically-checkable representation of an educational
Manim lecture. The IR is the contract between the planner, the code
compiler, the incremental (beat-by-beat) renderer, and the training
pipeline. Everything downstream of it is meant to be deterministic.

Layer stack — each layer answers exactly ONE question:

    Lecture     -> WHAT are we teaching?          (content, no animation)
    Storyboard  -> HOW should it be taught?       (pedagogy, no Manim)
    Scene       -> WHERE do things live?          (scene graph + camera + class)
    Beat        -> WHAT changes now?              (state transition)
    [compiler]  -> emit a `class <ClassName>(Scene)` with self.play(...)

Invariants enforced here, before any render:

  1. Structural wiring — behaviors, computations and trackers referenced by
     scene-graph objects must exist. Duplicate ids and reserved names are
     rejected.

  2. 3D discipline — a 3D scene that declares `begin_in_2d` must actually
     move the camera into orientation at least once (don't slam into 3D);
     `fix_in_frame` only means something in a 3D scene.

Beat-level reference integrity and cognitive-load limits are advisory: the
agent pipeline sanitizes/heals common LLM mistakes instead of hard-failing.
`CognitiveLoadPolicy` on LectureIR is metadata for prompts, not a gate.

The beat is also the unit of incremental execution: one beat -> one
visual delta -> one frame that can be fed back to the model.

------------------------------------------------------------------------
What v2 adds (from the field notes)
------------------------------------------------------------------------
- Scene.class_name + Scene.runtime_params : every scene is a real Manim
  class with typed knobs, so scenes are reusable/parameterizable.
- 2D->3D discipline : Scene.is_3d / begin_in_2d + camera Operations
  (move/pan/zoom/set_orientation) targeting a reserved camera id.
- Computation layer : back animations with actual maths. A closed set of
  libraries (numpy/scipy/sympy/pandas/python-chess) keeps scope to the
  Math/CS/AI domain. E.g. Lorenz via scipy.solve_ivp.
- SymbolSource : an equation can be authored inline or fetched from
  Wikipedia / Wikidata.
- rate_func on every Operation : lean on Manim's easing to look good.
- Persistent Behaviors (add_updater) : traced tails, endpoint-tracking
  dots, glow, follow-a-tracker, always_redraw. These persist across beats.
- ValueTrackers : first-class state you can teach with.
- Richer op vocabulary : TransformFromCopy, FlashAround, Circumscribe,
  FocusOn — every glyph (even the "H" in "Hello") is transformable, and
  sub-part targeting rides on op.params.
- RenderConfig : a real quality ladder for the video renderer.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
from uuid import uuid4

from pydantic import (
    AliasChoices,
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
FRAME_X_SAFE = 7.0  # |x| beyond this drifts off the visible frame
FRAME_Y_SAFE = 4.0  # |y| beyond this drifts off the visible frame

# Reserved scene-graph id for the camera. Camera Operations target this
# sentinel; it is always "live" and is never declared as a SceneObject.
CAMERA_TARGET = "__camera__"


# ===========================================================================
# Controlled vocabularies
#
# Closed sets on purpose: the model learns a small, real API and the
# compiler owns the (op -> Manim call) mapping. Free-text verbs are how you
# get hallucinated APIs; enums are how you prevent them.
# ===========================================================================
class Subject(str, Enum):
    MATH = "math"
    CS = "cs"
    AI = "ai"
    UNKNOWN = "unknown"


class Classification(BaseModel):
    subject: Subject
    topic: str


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
    TEXT = "text"  # -> Text
    MATH_TEX = "math_tex"  # -> MathTex  (an "equation")
    TITLE = "title"  # -> Title
    CODE_BLOCK = "code_block"  # -> Code
    TABLE = "table"  # -> Table
    # coordinate systems
    AXES = "axes"
    THREE_D_AXES = "three_d_axes"  # -> ThreeDAxes
    NUMBER_LINE = "number_line"
    NUMBER_PLANE = "number_plane"
    COMPLEX_PLANE = "complex_plane"
    GRAPH = "graph"  # plotted function
    PARAMETRIC_CURVE = "parametric_curve"  # -> ParametricFunction (2D/3D)
    # vectors / fields
    VECTOR = "vector"
    VECTOR_FIELD = "vector_field"
    # 3D
    SURFACE = "surface"
    SPHERE = "sphere"
    CUBE = "cube"
    # grouping / mascot
    GROUP = "group"  # -> VGroup (use *unpacking to build it)
    PI_CREATURE = "pi_creature"  # NB: not in vanilla ManimCE; compiler must
    # target a bundled asset or manim_pi plugin.


class OperationType(str, Enum):
    # --- introduce (CREATE family: make an object newly visible) ---
    CREATE = "create"  # Create
    WRITE = "write"  # Write            (text / tex)
    FADE_IN = "fade_in"  # FadeIn
    DRAW_BORDER = "draw_border"  # DrawBorderThenFill
    GROW = "grow"  # GrowFromCenter
    TRANSFORM_FROM_COPY = "transform_from_copy"  # TransformFromCopy(src,tgt):
    # leaves src, brings tgt on screen
    # --- transform ---
    TRANSFORM = "transform"  # Transform / ReplacementTransform
    MORPH = "morph"  # TransformMatchingTex / Shapes
    # --- move in space ---
    MOVE = "move"  # .animate.move_to
    SHIFT = "shift"  # .animate.shift
    ROTATE = "rotate"  # Rotate
    SCALE = "scale"  # .animate.scale
    RESCALE_TO_CORNER = "rescale_to_corner"  # shrink + park (Grant's move)
    # --- emphasise (no state change, pure attention) ---
    HIGHLIGHT = "highlight"  # Indicate
    FLASH = "flash"  # Flash
    FLASH_AROUND = "flash_around"  # FlashAround
    CIRCUMSCRIBE = "circumscribe"  # Circumscribe
    FOCUS_ON = "focus_on"  # FocusOn
    WIGGLE = "wiggle"  # Wiggle
    RECOLOR = "recolor"  # .animate.set_color
    # --- value-driven ---
    UPDATE_VALUE = "update_value"  # ValueTracker-driven .animate
    # --- camera (target must be CAMERA_TARGET) ---
    MOVE_CAMERA = "move_camera"  # self.move_camera(...)
    PAN_CAMERA = "pan_camera"  # camera.frame.animate.shift
    ZOOM_CAMERA = "zoom_camera"  # camera.frame.animate.scale
    SET_CAMERA_ORIENTATION = "set_camera_orientation"  # phi/theta -> enter 3D
    # --- remove (make an object no longer live) ---
    FADE_OUT = "fade_out"  # FadeOut
    UNCREATE = "uncreate"  # Uncreate
    REMOVE = "remove"  # self.remove (instant)


CREATE_FAMILY = {
    OperationType.CREATE,
    OperationType.WRITE,
    OperationType.FADE_IN,
    OperationType.DRAW_BORDER,
    OperationType.GROW,
    OperationType.TRANSFORM_FROM_COPY,  # brings the *target* on screen
}
REMOVE_FAMILY = {
    OperationType.FADE_OUT,
    OperationType.UNCREATE,
    OperationType.REMOVE,
}
EMPHASIS_OPS = {
    OperationType.HIGHLIGHT,
    OperationType.FLASH,
    OperationType.FLASH_AROUND,
    OperationType.CIRCUMSCRIBE,
    OperationType.FOCUS_ON,
    OperationType.WIGGLE,
    OperationType.RECOLOR,
}
CAMERA_OPS = {
    OperationType.MOVE_CAMERA,
    OperationType.PAN_CAMERA,
    OperationType.ZOOM_CAMERA,
    OperationType.SET_CAMERA_ORIENTATION,
}
# Camera ops that establish/rotate the 3D viewpoint (used to enforce the
# "don't slam into 3D — pan into it" discipline).
CAMERA_ORIENTATION_OPS = {
    OperationType.MOVE_CAMERA,
    OperationType.SET_CAMERA_ORIENTATION,
}
INSTANT_OPS = {OperationType.REMOVE}  # produce no animation, run_time == 0


class RateFunction(str, Enum):
    """Manim easing. Lean on these — flat linear motion reads as cheap."""

    LINEAR = "linear"
    SMOOTH = "smooth"
    EASE_IN_OUT = "ease_in_out_sine"
    EASE_IN = "ease_in_sine"
    EASE_OUT = "ease_out_sine"
    RUSH_INTO = "rush_into"
    RUSH_FROM = "rush_from"
    SLOW_INTO = "slow_into"
    DOUBLE_SMOOTH = "double_smooth"
    THERE_AND_BACK = "there_and_back"
    THERE_AND_BACK_WITH_PAUSE = "there_and_back_with_pause"
    WIGGLE = "wiggle"
    EXPONENTIAL_DECAY = "exponential_decay"


class ComputeLibrary(str, Enum):
    """
    Closed set of numeric/symbolic backends, scoped to the Math/CS/AI
    domain. The planner may only reach for real maths through these, so a
    Lorenz trajectory is `solve_ivp` output, not invented coordinates.
    """

    NUMPY = "numpy"
    SCIPY = "scipy"  # e.g. scipy.integrate.solve_ivp
    SYMPY = "sympy"
    PANDAS = "pandas"
    PYTHON_CHESS = "python_chess"  # chess-themed CS videos


class SymbolSource(str, Enum):
    """Where a Text/MathTex payload comes from."""

    INLINE = "inline"  # tex written directly in params
    WIKIPEDIA = "wikipedia"  # fetched via the Wikipedia tool
    WIKIDATA = "wikidata"  # fetched via Wikidata (structured)


class BehaviorType(str, Enum):
    """
    Persistent updaters (compiler emits `mob.add_updater(...)`). Unlike an
    AmbientAnimation (scoped to one beat's hold), a Behavior turns on when
    its object is created and runs until the object is removed.
    """

    TRACE_PATH = "trace_path"  # TracedPath tail behind a mover
    TRACK_ENDPOINT = "track_endpoint"  # dot pinned to the end of a path
    FOLLOW_TRACKER = "follow_tracker"  # position/value driven by a tracker
    GLOW_PULSE = "glow_pulse"  # animated glow (functions can glow)
    CONTINUOUS_ROTATE = "continuous_rotate"
    ALWAYS_REDRAW = "always_redraw"  # recompute the mobject each frame


class AmbientType(str, Enum):
    """Continuous, low-amplitude motion so a scene never fully freezes.
    Scoped to a single beat's hold (contrast with persistent Behaviors)."""

    BLINK = "blink"  # pi-creature eyes
    BREATHE = "breathe"  # subtle scale oscillation
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
    CLEAR_KEEP = "clear_keep"  # wipe most, keep a named subset
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
    LORENZ_ATTRACTOR = "lorenz_attractor"  # 2D warm-up -> pan into 3D
    STRANGE_ATTRACTOR = "strange_attractor"


class SemanticLabel(str, Enum):
    """Teaching role of a scene-graph object for beat/narration planners."""

    PRIMARY_FOCUS = "primary_focus"
    SUPPORTING_CONTEXT = "supporting_context"
    ANNOTATION = "annotation"
    CONTRAST = "contrast"
    METAPHOR = "metaphor"
    REVEAL = "reveal"


class Direction(str, Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    UL = "up_left"
    UR = "up_right"
    DL = "down_left"
    DR = "down_right"
    IN = "in"  # +z toward viewer (3D)
    OUT = "out"  # -z away (3D)


class Quality(str, Enum):
    """Render ladder for the video renderer."""

    LOW = "low_quality"  # 854x480 @ 15fps  (fast iteration)
    MEDIUM = "medium_quality"  # 1280x720 @ 30fps
    HIGH = "high_quality"  # 1920x1080 @ 60fps
    PRODUCTION = "production_quality"  # 2560x1440 @ 60fps
    FOURK = "fourk_quality"  # 3840x2160 @ 60fps


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
    z is honoured in 3D scenes.
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
    # "functions can take glow" — a static glow halo (Behavior.GLOW_PULSE
    # animates it). glow_color defaults to `color` at compile time.
    glow: bool = False
    glow_color: Optional[str] = None


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
# State / maths backing (v2)
# ===========================================================================
class ValueTracker(BaseModel):
    """
    First-class scene state. Beats mutate it with UPDATE_VALUE; objects can
    ride it with a FOLLOW_TRACKER behaviour. This is how you 'use state to
    teach' — one knob drives many mobjects.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    initial: float = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    label: str = ""


class Computation(BaseModel):
    """
    The real maths under an animation. A GRAPH / PARAMETRIC_CURVE / surface
    can reference a Computation by id; the compiler runs the routine at
    build time and feeds the samples into the mobject. Scope is the closed
    ComputeLibrary set, keeping the system inside Math/CS/AI.

    Example (Lorenz):
        Computation(id="lorenz", library=ComputeLibrary.SCIPY,
                    routine="solve_ivp",
                    params={"sigma":10,"rho":28,"beta":8/3,"t_end":40},
                    produces="Lorenz trajectory (N,3) array")
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    library: ComputeLibrary
    routine: str  # e.g. "solve_ivp", "linspace"
    params: dict[str, Any] = Field(default_factory=dict)
    produces: str = ""  # human note about the output


class Behavior(BaseModel):
    """
    A persistent updater attached to a SceneObject. Turns on when the object
    is created, runs until it is removed. This is the `add_updater(...)`
    layer: traced tails, endpoint dots, glow, tracker-following, redraws.
    """

    model_config = ConfigDict(extra="forbid")

    type: BehaviorType
    of: Optional[str] = None  # id of another object this behaviour reads
    # (e.g. the path a TRACK_ENDPOINT dot rides)
    tracker: Optional[str] = None  # ValueTracker id (FOLLOW_TRACKER)
    params: dict[str, Any] = Field(default_factory=dict)


class SceneParameter(BaseModel):
    """A typed runtime knob for a Scene, so scenes are reusable.
    e.g. SceneParameter(name='rho', py_type='float', default=28.0)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    py_type: str = "float"  # "int" | "float" | "str" | "bool"
    default: Any = None
    description: str = ""

    @field_validator("name")
    @classmethod
    def _valid_identifier(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"scene parameter name '{v}' is not a valid identifier")
        return v

    @field_validator("py_type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        if v not in {"int", "float", "str", "bool"}:
            raise ValueError(f"unsupported py_type '{v}'")
        return v


# ===========================================================================
# Scene graph nodes
# ===========================================================================
class SceneObject(BaseModel):
    """
    A node in the scene graph. Declared once, mutated by beats (React-style).
    `visible=False` means it exists in the cast but hasn't been created yet;
    a CREATE-family op brings it on screen.
    """

    # extra="allow": small/cheap planner models drift on this schema (extra
    # keys, slightly-off shapes) and extra="forbid" turned that into a hard
    # validation failure -> ModelRetry loop, which in practice was settling
    # on empty-but-valid params (e.g. MathTex(tex="")) just to pass. Allowing
    # extra keys through unvalidated is a stopgap; a stricter, better-fitted
    # schema is the real fix.
    model_config = ConfigDict(extra="allow")

    id: str
    entity_type: EntityType
    position: Position = Field(default_factory=Position)
    style: Style = Field(default_factory=Style)
    layer: int = 0  # z-ordering within the scene
    visible: bool = False  # initial visibility (pre-first-beat)
    # The literal tex/text payload for MATH_TEX and TEXT entities. A typed
    # string field, not a free-form dict key — structured-output models
    # reliably fill a declared string field but tend to leave open-ended
    # dict[str, Any] keys (like the old params["tex"]) empty, since nothing
    # in the schema tells them the key even exists.
    content: str = Field(
        default="",
        description="Literal text or LaTeX shown on screen (required for text/math_tex/title).",
    )
    # type-specific payload for everything else, e.g. {"radius": 1.5} or
    # {"x_range": [-3, 3, 1]}. Not for tex/text — use `content` instead.
    params: dict[str, Any] = Field(default_factory=dict)
    label: str = Field(
        default="",
        description=(
            "Semantic teaching role: primary_focus, supporting_context, "
            "annotation, contrast, metaphor, or reveal."
        ),
    )

    # --- v2 ---
    # equation/text provenance
    symbol_source: SymbolSource = SymbolSource.INLINE
    symbol_query: Optional[str] = None  # search term for wiki* sources
    # maths backing (id of a Computation on the owning Scene)
    computation: Optional[str] = None
    # persistent updaters
    behaviors: list[Behavior] = Field(default_factory=list)
    # 3D: keep this glued to the camera frame (add_fixed_in_frame_mobjects).
    # Only meaningful in a 3D scene; validated at Scene level.
    fix_in_frame: bool = False

    @property
    def is_equation(self) -> bool:
        return self.entity_type == EntityType.MATH_TEX

    @model_validator(mode="after")
    def _wiki_needs_query(self) -> "SceneObject":
        if self.symbol_source != SymbolSource.INLINE and not self.symbol_query:
            raise ValueError(
                f"object '{self.id}' uses symbol_source="
                f"{self.symbol_source.value} but has no symbol_query"
            )
        return self


class Camera(BaseModel):
    model_config = ConfigDict(extra="forbid")

    center: Position = Field(default_factory=Position)
    zoom: float = Field(default=1.0, gt=0.0)
    phi: float = 0.0  # 3D polar (radians)
    theta: float = 0.0  # 3D azimuth (radians)
    is_3d: bool = False


# ===========================================================================
# Beat: the state transition (animation + narration + ambient)
# ===========================================================================
class Operation(BaseModel):
    """An action == an operation applied to one entity. There is no
    standalone 'Actions' concept: Operation(target).

    Sub-part targeting (the 'H' in 'Hello' is transformable) rides on
    params, e.g. {"parts": ["H"]} or {"index": 0}. Camera ops target the
    reserved CAMERA_TARGET id."""

    model_config = ConfigDict(extra="forbid")

    target: str  # SceneObject.id or CAMERA_TARGET
    op: OperationType
    run_time: float = Field(default=1.0, ge=0.0)
    rate_func: Optional[RateFunction] = None
    params: dict[str, Any] = Field(default_factory=dict)
    # optional: play concurrently with the previous op instead of after it
    with_previous: bool = False

    @model_validator(mode="after")
    def _op_shape(self) -> "Operation":
        if self.op in INSTANT_OPS and self.run_time != 0.0:
            raise ValueError(f"{self.op.value} is instant; run_time must be 0")
        if self.op in CAMERA_OPS and self.target != CAMERA_TARGET:
            raise ValueError(
                f"camera op {self.op.value} must target '{CAMERA_TARGET}', "
                f"got '{self.target}'"
            )
        if self.op not in CAMERA_OPS and self.target == CAMERA_TARGET:
            raise ValueError(
                f"'{CAMERA_TARGET}' is reserved for camera ops; "
                f"{self.op.value} cannot target it"
            )
        if self.op == OperationType.TRANSFORM_FROM_COPY:
            src = self.params.get("source") or self.params.get("from")
            if not src:
                raise ValueError(
                    "transform_from_copy requires params['source'] (the id copied from)"
                )
        return self

    @property
    def copy_source(self) -> Optional[str]:
        if self.op == OperationType.TRANSFORM_FROM_COPY:
            return self.params.get("source") or self.params.get("from")
        return None


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
    """Runs continuously across a beat's hold so nothing freezes.
    (Persistent, cross-beat behaviour lives on SceneObject.behaviors.)"""

    model_config = ConfigDict(extra="forbid")

    type: AmbientType
    target: Optional[str] = None  # entity id, or None for camera/scene
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
    scene_id: str = ""
    visual_intent: str = ""
    animation_seconds: float = Field(default=1.0, ge=0.0)
    animation_segment: list[Operation] = Field(default_factory=list)
    narration: Optional[NarrationSegment] = None
    hold_seconds: float = Field(default=0.0, ge=0.0)  # dwell after animating
    ambient: list[AmbientAnimation] = Field(default_factory=list)

    @property
    def moving_ops(self) -> list[Operation]:
        return [o for o in self.animation_segment if o.op not in INSTANT_OPS]

    @property
    def object_moving_ops(self) -> list[Operation]:
        """Motion that counts against cognitive load (excludes camera)."""
        return [o for o in self.moving_ops if o.op not in CAMERA_OPS]

    @property
    def total_seconds(self) -> float:
        if self.animation_segment:
            anim = sum(o.run_time for o in self.animation_segment)
        else:
            anim = self.animation_seconds
        narr = self.narration.est_seconds if self.narration else 0.0
        return round(max(anim + self.hold_seconds, narr), 1)


# ===========================================================================
# Scene: the visual arrangement + the beats that mutate it
# ===========================================================================
class Scene(BaseModel):
    """
    Owns a scene graph and an ordered list of beats. Every scene compiles to
    a `class <class_name>(Scene | ThreeDScene)`. This is where the core
    invariants are enforced. Scenes are composable/reusable: a COMPLEX_PLANE
    scene can be pulled into Euler, Fourier, roots-of-unity, with different
    runtime_params.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    class_name: str = "GeneratedScene"  # the emitted Manim class name
    title: str = ""

    pedagogical_intent: str = Field(
        default="",
        description="The exact pedagogical goal from the storyboard step. "
        "Downstream agents (Beat, Narration) use this to make "
        "high-level decisions without inferring intent from geometry.",
    )
    visual_brief: str = Field(
        default="",
        description="Free-text creative brief for the Manim code writer — "
        "what the viewer should see, without prescribing IR objects.",
    )

    reusable: bool = False
    template: Optional[TemplateType] = None
    runtime_params: list[SceneParameter] = Field(default_factory=list)

    # dimensionality
    is_3d: bool = False
    begin_in_2d: bool = True  # if 3D: warm up flat, then pan in

    camera: Camera = Field(default_factory=Camera)
    scene_graph: list[SceneObject] = Field(default_factory=list)
    trackers: list[ValueTracker] = Field(default_factory=list)
    computations: list[Computation] = Field(default_factory=list)
    beats: list[Beat] = Field(default_factory=list)
    enter_transition: Optional[SceneTransition] = None
    exit_transition: Optional[SceneTransition] = None

    @field_validator("class_name")
    @classmethod
    def _valid_class_name(cls, v: str) -> str:
        if not v.isidentifier():
            raise ValueError(f"class_name '{v}' is not a valid Python identifier")
        if not v[0].isupper():
            raise ValueError(f"class_name '{v}' should be PascalCase (upper first)")
        return v

    @field_validator("scene_graph")
    @classmethod
    def _unique_ids(cls, graph: list[SceneObject]) -> list[SceneObject]:
        ids = [o.id for o in graph]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate scene object id(s): {sorted(dupes)}")
        if CAMERA_TARGET in ids:
            raise ValueError(
                f"'{CAMERA_TARGET}' is reserved and cannot be an object id"
            )
        return graph

    @model_validator(mode="after")
    def _validate_dynamics(self, _info: ValidationInfo) -> "Scene":
        """Walk the beats as a mini-interpreter: enforce static-reference
        wiring (trackers / computations / behaviors) and 3D discipline.
        Beat-level liveness and cognitive-load issues are tolerated — the
        agent pipeline sanitizes them before compile."""
        # camera consistency
        if self.is_3d and not self.camera.is_3d:
            raise ValueError(f"scene '{self.id}' is_3d=True but camera.is_3d=False")

        types: dict[str, EntityType] = {o.id: o.entity_type for o in self.scene_graph}
        tracker_ids = {t.id for t in self.trackers}
        comp_ids = {c.id for c in self.computations}

        # --- static wiring checks (before walking beats) ---
        for o in self.scene_graph:
            if o.fix_in_frame and not self.is_3d:
                raise ValueError(
                    f"object '{o.id}' sets fix_in_frame in a 2D scene "
                    f"'{self.id}' (only meaningful in 3D)"
                )
            if o.computation and o.computation not in comp_ids:
                raise ValueError(
                    f"object '{o.id}' references unknown computation "
                    f"'{o.computation}' in scene '{self.id}'"
                )
            for b in o.behaviors:
                if b.of is not None and b.of not in types:
                    raise ValueError(
                        f"object '{o.id}' behavior {b.type.value} reads "
                        f"unknown object '{b.of}' in scene '{self.id}'"
                    )
                if b.type == BehaviorType.FOLLOW_TRACKER and not b.tracker:
                    raise ValueError(
                        f"object '{o.id}' FOLLOW_TRACKER behavior needs a tracker"
                    )
                if b.tracker is not None and b.tracker not in tracker_ids:
                    raise ValueError(
                        f"object '{o.id}' behavior references unknown tracker "
                        f"'{b.tracker}' in scene '{self.id}'"
                    )
                if b.type == BehaviorType.TRACK_ENDPOINT and not b.of:
                    raise ValueError(
                        f"object '{o.id}' TRACK_ENDPOINT behavior needs `of` "
                        f"(the path it tracks)"
                    )

        # --- dynamic walk ---
        live: set[str] = {o.id for o in self.scene_graph if o.visible}
        saw_camera_orientation = False

        for beat in self.beats:
            for op in beat.animation_segment:
                # camera ops: skip declaration/liveness; just note orientation
                if op.op in CAMERA_OPS:
                    if op.op in CAMERA_ORIENTATION_OPS:
                        saw_camera_orientation = True
                    continue

                if op.target not in types:
                    if op.op in CREATE_FAMILY:
                        types[op.target] = EntityType.TEXT
                    else:
                        continue

                # TransformFromCopy needs a live source; brings target on screen
                if op.op == OperationType.TRANSFORM_FROM_COPY:
                    src = op.copy_source
                    if src not in types or src not in live:
                        continue

                if op.op in CREATE_FAMILY:
                    if op.target in live:
                        continue
                    live.add(op.target)
                elif op.op in REMOVE_FAMILY:
                    if op.target not in live:
                        continue
                    live.discard(op.target)
                else:  # transform / move / emphasise / value
                    if op.target not in live:
                        continue

        # --- 3D discipline: don't slam into 3D, pan into it ---
        if self.is_3d and self.begin_in_2d and not saw_camera_orientation:
            raise ValueError(
                f"scene '{self.id}' is 3D and begin_in_2d=True but never moves "
                f"the camera into orientation — add a move_camera / "
                f"set_camera_orientation op (reveal 3D, don't snap to it)"
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

    scene_id: str  # snake_case identifier, e.g., "scene_ball_rolls"
    pedagogical_move: StoryboardMove  # the "why" of this step
    pedagogical_goal: str  # what the viewer should *understand* after this step
    visual_description: (
        str  # what appears on screen, including colors, shapes, motion, camera
    )
    narration_script: str  # the actual spoken words (or key phrases)
    viewer_question: Optional[str] = (
        None  # a question we pose to the viewer (to engage prediction)
    )
    transition_from_previous: Optional[str] = (
        None  # how we flow from the previous scene
    )
    emotional_tone: str  # e.g., curiosity, confusion, revelation, satisfaction
    estimated_duration_seconds: int = 10  # rough pacing


class Storyboard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str  # short title for the whole animation
    overall_emotional_arc: (
        str  # e.g., "Curiosity → Prediction → Failure → Insight → Awe"
    )
    steps: List[StoryboardStep]


class Lecture(BaseModel):
    """Content layer: what to teach. No animation lives here."""

    model_config = ConfigDict(extra="forbid")

    topic: str
    subject: Subject
    greeting: str = ""  # time-of-day aware (filled at runtime)
    needed_formulas: list[str] = Field(
        default_factory=list,
        description="List of formulas that will be used in the lecture for programmting the manim video.",
    )
    class_names: list[str] = Field(
        default_factory=list,
        description="List of class names for each scenes that will be used in the lecture for programmting the manim video.",
    )
    does_it_needs_3d: bool = Field(
        validation_alias=AliasChoices("does_it_needs_3d", "does_it_need_3d"),
        description="Does the lecture needs 3D scenes for programmting the manim video. Use true for 3D and false for only using the 2D.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="List of assumptions that will be used in the lecture for audience.",
    )
    list_of_external_library_needed: list[str] = Field(
        default_factory=list,
        description="List of external libraries that will be used in the lecture for programmting the manim video like scipy, numpy,networkx, etc.",
    )
    animation_needed: list[str] = Field(
        default_factory=list,
        description="List of Manim animations functions that will be needed in the lecture for programing the manim video like gradient_bowl, neural_network, etc.",
    )
    animation_updaters_needed: list[str] = Field(
        default_factory=list,
        description="List of animation updaters that will be used in the lecture for programmting the manim video like trace_path, track_endpoint, etc.",
    )
    camera_needed: list[str] = Field(
        default_factory=list,
        description="List of camera operations that will be used in the lecture for programmting the manim video like move_camera, pan_camera, etc.",
    )
    Mobjects_needed: list[str] = Field(
        default_factory=list,
        description="List of manim objects that will be used in the lecture for programmting the manim video like Circle, Square, etc.",
    )
    objectives: list[str] = Field(
        default_factory=list,
        description="List of objectives that will be used in the lecture for audience.",
    )
    opener: str = Field(
        default="",
        description="The 'solid opener' hook make it bit longer than a single sentence, but it should be a single paragraph that is the hook for the lecture. It should be a story or a question that makes the audience curious about the topic of the lecture.",
    )
    learning_outcomes: list[str] = Field(
        default_factory=list,
        description="List of learning outcomes that will be used in the lecture for audience.",
    )


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


class RenderConfig(BaseModel):
    """Video renderer settings — the quality ladder from the notes."""

    model_config = ConfigDict(extra="forbid")

    quality: Quality = Quality.HIGH
    fps: int = Field(default=60, gt=0)
    resolution: tuple[int, int] = (1920, 1080)
    output_format: str = "mp4"  # mp4 | mov | gif | png_sequence
    transparent: bool = False
    preview: bool = False  # open the player after render

    @field_validator("output_format")
    @classmethod
    def _known_format(cls, v: str) -> str:
        if v not in {"mp4", "mov", "gif", "png_sequence"}:
            raise ValueError(f"unsupported output_format '{v}'")
        return v


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
    manim_version: str = "0.18.1"  # the pinned target; kills fork drift
    ir_version: str = "2.0.0"
    duration_target_seconds: Optional[float] = None

    branding: Branding = Field(default_factory=Branding)
    load_policy: CognitiveLoadPolicy = Field(default_factory=CognitiveLoadPolicy)
    render: RenderConfig = Field(default_factory=RenderConfig)

    lecture: Lecture
    storyboard: Storyboard
    scenes: list[Scene] = Field(default_factory=list)

    opening: OpeningScene = Field(default_factory=OpeningScene)
    ending: EndingScene = Field(default_factory=EndingScene)

    @model_validator(mode="after")
    def _storyboard_refs_exist(self) -> "LectureIR":
        scene_ids = {s.id for s in self.scenes}
        dupes = {
            s.id for s in self.scenes if [x.id for x in self.scenes].count(s.id) > 1
        }
        if dupes:
            raise ValueError(f"duplicate scene id(s): {sorted(dupes)}")
        # class names should be unique too — they become Python classes
        class_names = [s.class_name for s in self.scenes]
        cdupes = {c for c in class_names if class_names.count(c) > 1}
        if cdupes:
            raise ValueError(f"duplicate scene class_name(s): {sorted(cdupes)}")
        for step in self.storyboard.steps:
            if step.scene_id not in scene_ids:
                raise ValueError(
                    f"storyboard step '{step.pedagogical_move.value}' references unknown "
                    f"scene_id '{step.scene_id}'"
                )
        return self

    @property
    def duration_seconds(self) -> float:
        return round(sum(s.duration_seconds for s in self.scenes), 1)
