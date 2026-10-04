"""MotionGram 📽️ — The grammar of motion graphics (pre-alpha stubs)."""

from __future__ import annotations

__version__ = "0.1.0a0"

from motiongram.animate import (
    Animator,
    Anticipate,
    Blur,
    CameraPan,
    CameraZoom,
    CircleOutline,
    Delay,
    ExaggerateEase,
    FadeIn,
    FadeOut,
    FollowThrough,
    MoveAlongPath,
    MoveArc,
    MoveX,
    MoveY,
    Parallel,
    Rotate,
    ScaleX,
    ScaleY,
    Sequence,
    SquashStretch,
    Stagger,
    TimeScale,
    WithSecondary,
    apply_timeline,
    lerp,
    smoothstep,
)
try:
    from motiongram.audio import KittenVoiceOverBackend, VoiceOver
except (ImportError, ModuleNotFoundError, Exception):
    KittenVoiceOverBackend = None  # type: ignore[assignment]
    VoiceOver = None  # type: ignore[assignment]

from motiongram.canvas import Canvas, NullCanvas, RecordingCanvas
from motiongram.composition import (
    PHI,
    TAU,
    GesturePath,
    GoldenSpiral,
    RuleOfThirdsGrid,
    align,
    distribute_evenly,
    stack_vertical,
)
from motiongram.core import Camera, Circle, Node, Scene, Timeline
from motiongram.easing import (
    cubic_bezier,
    ease_in_back,
    ease_in_out_cubic,
    ease_in_out_quad,
    ease_out_back,
    ease_out_bounce,
    ease_out_elastic,
    linear,
    overshoot,
)
from motiongram.engine import step_frame

try:
    from motiongram.export import PyAVEncoder
except (ImportError, ModuleNotFoundError, Exception):
    PyAVEncoder = None  # type: ignore[assignment]

from motiongram.form import Cube, Cylinder, Sphere
from motiongram.perspective import PerspectiveGrid
from motiongram.recipes import add_blink, add_squash_stretch_drop

try:
    from motiongram.render import SkiaCanvas, SkiaRenderer
except (ImportError, ModuleNotFoundError, Exception):
    SkiaCanvas = None  # type: ignore[assignment]
    SkiaRenderer = None  # type: ignore[assignment]

from motiongram.renderer import Renderer, ascii_frame_sha256, ascii_frame_text
from motiongram.shapes import (
    Arc,
    BezierCurve,
    Ellipse,
    Line,
    Path,
    Polygon,
    Rectangle,
    RegularPolygon,
    Sector,
    SemiCircle,
)
from motiongram.subtitles import (
    SubtitleCue,
    SubtitleStyle,
    SubtitleTrack,
    active_subtitles,
    sort_cues,
    subtitle_typst_layout,
    validate_subtitle_track,
    read_webvtt,
    write_webvtt,
)
from motiongram.text import CodeBlock, MathExpr, Text
from motiongram.typst_cache import (
    cached_typst_subtitle_svg_path,
    cached_typst_svg_path,
    subtitle_document_for_cache,
    typst_cache_key,
    typst_subtitle_cache_key,
)
from motiongram.value import GradientOverlay, Shadow
from motiongram.world import (
    CHARACTER_HEIGHT_UNITS,
    SemanticPart,
    WorldPortal,
    WorldShellNodes,
    WorldSpec,
    default_world_height,
    ground_strip,
    place_on_ground,
    project_depth_fake,
    screen_to_world,
    world_pixel_affine_coeffs,
    world_shell,
    world_to_screen,
)

__all__ = [
    "__version__",
    "add_blink",
    "add_squash_stretch_drop",
    "align",
    "Animator",
    "Anticipate",
    "apply_timeline",
    "Arc",
    "ascii_frame_sha256",
    "ascii_frame_text",
    "BezierCurve",
    "Blur",
    "cached_typst_svg_path",
    "Camera",
    "CameraPan",
    "CameraZoom",
    "Canvas",
    "CHARACTER_HEIGHT_UNITS",
    "Circle",
    "CircleOutline",
    "CodeBlock",
    "Cube",
    "cubic_bezier",
    "Cylinder",
    "default_world_height",
    "Delay",
    "distribute_evenly",
    "ease_in_back",
    "ease_in_out_cubic",
    "ease_in_out_quad",
    "ease_out_back",
    "ease_out_bounce",
    "ease_out_elastic",
    "Ellipse",
    "ExaggerateEase",
    "FadeIn",
    "FadeOut",
    "FollowThrough",
    "GesturePath",
    "GoldenSpiral",
    "GradientOverlay",
    "ground_strip",
    "KittenVoiceOverBackend",
    "lerp",
    "Line",
    "linear",
    "MathExpr",
    "MoveAlongPath",
    "MoveArc",
    "MoveX",
    "MoveY",
    "Node",
    "NullCanvas",
    "overshoot",
    "Parallel",
    "Path",
    "PerspectiveGrid",
    "PHI",
    "place_on_ground",
    "Polygon",
    "project_depth_fake",
    "PyAVEncoder",
    "RecordingCanvas",
    "Rectangle",
    "RegularPolygon",
    "Renderer",
    "Rotate",
    "RuleOfThirdsGrid",
    "ScaleX",
    "ScaleY",
    "Scene",
    "screen_to_world",
    "Sector",
    "SemanticPart",
    "SemiCircle",
    "Sequence",
    "Shadow",
    "SkiaCanvas",
    "SkiaRenderer",
    "smoothstep",
    "Sphere",
    "SquashStretch",
    "stack_vertical",
    "Stagger",
    "step_frame",
    "SubtitleCue",
    "SubtitleStyle",
    "SubtitleTrack",
    "active_subtitles",
    "cached_typst_subtitle_svg_path",
    "sort_cues",
    "subtitle_document_for_cache",
    "subtitle_typst_layout",
    "typst_subtitle_cache_key",
    "validate_subtitle_track",
    "read_webvtt",
    "write_webvtt",
    "TAU",
    "Text",
    "Timeline",
    "TimeScale",
    "typst_cache_key",
    "VoiceOver",
    "WithSecondary",
    "world_pixel_affine_coeffs",
    "world_shell",
    "world_to_screen",
    "WorldPortal",
    "WorldShellNodes",
    "WorldSpec",
]
