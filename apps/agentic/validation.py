"""Manim CE Schema Contracts & Knowledge Registry (v2 — Optimized for 7B Models).

Directly driven by `manim_inheritance_graph.json` and `manim_leaf_roster.json`.
Enforces strict instantiable class constraints across the multi-agent pipeline,
preventing abstract base class hallucinations.

DESIGN PRINCIPLE FOR 7B MODELS:
  Treat the LLM as a categorical decision engine, not a code generator.
  Every output field is either an enum pick or a typed slot — never freeform Python.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Load Knowledge Base Artifacts
# ---------------------------------------------------------------------------
CURRENT_DIR = Path(__file__).parent
GRAPH_FILE = CURRENT_DIR / "manim_inheritance_graph.json"
ROSTER_FILE = CURRENT_DIR / "manim_leaf_roster.json"

if not GRAPH_FILE.exists() or not ROSTER_FILE.exists():
    raise FileNotFoundError(
        f"Missing inheritance graph files in {CURRENT_DIR}. Please run extract_pdf_graphs.py first."
    )

GRAPH_DATA: Dict[str, Any] = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
ROSTER_DATA: Dict[str, list[Dict[str, Any]]] = json.loads(ROSTER_FILE.read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# Knowledge Registry & Lookup Helpers
# ---------------------------------------------------------------------------

class ManimKnowledgeRegistry:
    """Fast in-memory index of the Manim CE inheritance graph."""

    def __init__(self, graph_data: Dict[str, Any], roster_data: Dict[str, Any]):
        self.graph = graph_data
        self.roster = roster_data

        self.nodes_by_name: Dict[str, Dict[str, Any]] = {}
        for branch_name, branch_data in self.graph.get("branches", {}).items():
            for class_name, node in branch_data.get("nodes", {}).items():
                node_copy = dict(node)
                node_copy["branch"] = branch_name
                self.nodes_by_name[class_name] = node_copy

        # Instantiable sets per branch
        self.instantiable_by_branch: Dict[str, Set[str]] = {
            b: {item["class_name"] for item in items} for b, items in self.roster.items()
        }

        # Abstract base class sets
        self.abstract_by_branch: Dict[str, Set[str]] = {
            b: set(self.graph["branches"][b].get("abstract_classes", []))
            for b in self.graph.get("branches", {})
        }

    def get_info(self, class_name: str) -> Optional[Dict[str, Any]]:
        return self.nodes_by_name.get(class_name)

    def is_instantiable(self, class_name: str) -> bool:
        node = self.nodes_by_name.get(class_name)
        return bool(node and node.get("is_instantiable", False))

    def is_abstract_base(self, class_name: str) -> bool:
        node = self.nodes_by_name.get(class_name)
        return bool(node and node.get("is_abstract_base", False))

    def get_children(self, class_name: str) -> list[str]:
        node = self.nodes_by_name.get(class_name)
        return node.get("children", []) if node else []

    def get_parents(self, class_name: str) -> list[str]:
        node = self.nodes_by_name.get(class_name)
        return node.get("parents", []) if node else []

    def get_import_path(self, class_name: str) -> str:
        node = self.nodes_by_name.get(class_name)
        if node and node.get("module"):
            return f"from {node['module']} import {class_name}"
        return f"from manim import {class_name}"


registry = ManimKnowledgeRegistry(GRAPH_DATA, ROSTER_DATA)


# ---------------------------------------------------------------------------
# Core Catalogs — Tiered for 7B Model Reliability
# ---------------------------------------------------------------------------
# The full roster has 211+ classes. A 7B model can reliably pick from ~30.
# These Core sets contain the classes needed for 95% of educational videos.
# Classes outside Core are still valid Manim CE — they're just hidden from
# the LLM's schema to reduce cognitive load and improve selection accuracy.

CORE_MOBJECTS: Set[str] = {
    # Text & Math
    "Text", "Title", "MathTex", "Tex", "DecimalNumber",
    # Coordinate Systems
    "Axes", "NumberPlane", "NumberLine",
    # Geometry — Flat
    "Dot", "Circle", "Square", "Rectangle", "RoundedRectangle",
    "Line", "Arrow", "DashedLine", "Vector",
    "Arc", "RegularPolygon", "Triangle", "Star", "Annulus",
    # Grouping & Annotations
    "VGroup", "SurroundingRectangle", "Brace",
    # Drivers
    "ValueTracker",
    # Functions & Curves
    "FunctionGraph",
}

CORE_ANIMATIONS: Set[str] = {
    # Creation & Drawing
    "Create", "Write", "DrawBorderThenFill",
    # Fading
    "FadeIn", "FadeOut",
    # Growth
    "GrowFromCenter", "GrowArrow", "SpinInFromNothing",
    # Transforms
    "ReplacementTransform", "TransformMatchingTex", "TransformMatchingShapes",
    # Indications
    "Indicate", "Circumscribe", "Flash", "Wiggle", "FocusOn",
    # Composition (for grouped animations)
    "AnimationGroup", "Succession", "LaggedStart",
    # Motion
    "MoveAlongPath", "Rotate",
    # Uncreation
    "Uncreate", "Unwrite",
}

# Scene and Camera choices are small enough to include the full set.
# We add plugin classes (VoiceoverScene, Slide) that aren't in the roster.
_ROSTER_SCENES = registry.instantiable_by_branch.get("Scenes", set())
_ROSTER_CAMERAS = registry.instantiable_by_branch.get("Cameras", set())

SCENE_CLASSES: Set[str] = _ROSTER_SCENES | {"Scene", "VoiceoverScene", "Slide", "ThreeDScene"}
CAMERA_CLASSES: Set[str] = _ROSTER_CAMERAS | {"Camera"}


# ---------------------------------------------------------------------------
# Typed Literals — Core (agent schemas) and Full (reference/fallback)
# ---------------------------------------------------------------------------

CoreMobjectLiteral = Literal.__getitem__(tuple(sorted(CORE_MOBJECTS)))
CoreAnimationLiteral = Literal.__getitem__(tuple(sorted(CORE_ANIMATIONS)))
SceneClassLiteral = Literal.__getitem__(tuple(sorted(SCENE_CLASSES)))
CameraClassLiteral = Literal.__getitem__(tuple(sorted(CAMERA_CLASSES)))

# Full roster Literals — kept for debugging, SFT data gen, and future escalation
_full_mobject_set = registry.instantiable_by_branch.get("Mobjects", set()) | {"VGroup", "Group"}
_full_animation_set = registry.instantiable_by_branch.get("Animations", set())
FullMobjectLiteral = Literal.__getitem__(tuple(sorted(_full_mobject_set)))
FullAnimationLiteral = Literal.__getitem__(tuple(sorted(_full_animation_set)))


# ---------------------------------------------------------------------------
# LaTeX Validation Helper
# ---------------------------------------------------------------------------

def validate_latex_string(tex: str) -> tuple[bool, str]:
    """Quick heuristic LaTeX validation for Manim MathTex/Tex.

    Catches the top failure modes a 7B model produces:
    1. Unbalanced braces
    2. Manim-incompatible LaTeX environments
    3. Common syntax errors
    """
    if not tex or not tex.strip():
        return False, "Empty LaTeX string"

    # Check balanced braces
    open_count = tex.count("{")
    close_count = tex.count("}")
    if open_count != close_count:
        return False, (
            f"Unbalanced braces: {open_count} open '{{' vs {close_count} close '}}'. "
            f"Each '{{' must have a matching '}}'."
        )

    # Check for Manim-incompatible environments (MathTex uses a single-line equation)
    incompatible = [
        (r"\begin{align}", "Use separate MathTex objects instead of align environment"),
        (r"\begin{equation}", "MathTex is already in math mode; drop \\begin{equation}"),
        (r"\newcommand", "MathTex does not support \\newcommand"),
        (r"\usepackage", "MathTex does not support \\usepackage"),
        (r"\documentclass", "MathTex does not support \\documentclass"),
    ]
    for pattern, suggestion in incompatible:
        if pattern in tex:
            return False, f"Unsupported LaTeX: '{pattern}'. {suggestion}"

    return True, "OK"


# ---------------------------------------------------------------------------
# MobjectConfig — Typed Constructor Arguments
# ---------------------------------------------------------------------------
# DESIGN: Instead of freeform `initial_args: str`, the LLM fills typed slots.
# The assembler maps these slots to Python constructor arguments.
# This eliminates ~60% of runtime crashes from malformed Python strings.

class MobjectConfig(BaseModel):
    """Typed configuration for Manim CE mobject constructors.

    Fill ONLY the fields relevant to your chosen manim_class.
    Leave all irrelevant fields as null/unset.
    """
    model_config = ConfigDict(extra="allow")  # Tolerate extra fields from 7B models

    # --- Content (fill ONE of text or tex) ---
    text: Optional[str] = Field(
        default=None,
        description="Display text. Required for Text, Title."
    )
    tex: Optional[str] = Field(
        default=None,
        description=(
            "LaTeX math string WITHOUT $ delimiters. Required for MathTex, Tex. "
            "Example: 'a^2 + b^2 = c^2'"
        ),
    )

    # --- Coordinate Systems (Axes, NumberPlane, NumberLine) ---
    x_range: Optional[list[float]] = Field(
        default=None,
        description="X-axis range as [min, max, step]. Example: [-3, 3, 1]"
    )
    y_range: Optional[list[float]] = Field(
        default=None,
        description="Y-axis range as [min, max, step]. For Axes and NumberPlane."
    )
    x_length: Optional[float] = Field(
        default=None, ge=1.0, le=12.0,
        description="Visual width of axes in scene units."
    )
    y_length: Optional[float] = Field(
        default=None, ge=1.0, le=7.0,
        description="Visual height of axes in scene units."
    )

    # --- Geometry ---
    radius: Optional[float] = Field(
        default=None, ge=0.01, le=5.0,
        description="Radius for Circle, Dot, Arc."
    )
    width: Optional[float] = Field(
        default=None, ge=0.1, le=14.0,
        description="Width for Rectangle/RoundedRectangle, or side_length for Square."
    )
    height: Optional[float] = Field(
        default=None, ge=0.1, le=8.0,
        description="Height for Rectangle, RoundedRectangle."
    )
    n_sides: Optional[int] = Field(
        default=None, ge=3, le=20,
        description="Number of sides for RegularPolygon, or points for Star."
    )

    # --- Drivers & Numbers ---
    initial_value: Optional[float] = Field(
        default=None,
        description="Starting value for ValueTracker or DecimalNumber."
    )

    # --- Functions ---
    function_expr: Optional[str] = Field(
        default=None,
        description=(
            "Python math expression for FunctionGraph. Use 'x' as the variable. "
            "Examples: 'x**2', 'np.sin(x)', '1/(1+x**2)'"
        ),
    )

    # --- References (for derived/attached mobjects) ---
    reference_variable: Optional[str] = Field(
        default=None,
        description="Variable name of the mobject this attaches to. For SurroundingRectangle, Brace."
    )

    # --- Universal Styling ---
    color: Optional[str] = Field(
        default=None,
        description=(
            "Manim color name: WHITE, BLUE, RED, YELLOW, GREEN, ORANGE, PURPLE, "
            "PINK, TEAL, GOLD, MAROON, GREY. Or hex string like '#FF6600'."
        ),
    )
    fill_opacity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    font_size: Optional[int] = Field(default=None, ge=12, le=144)

    # --- Validators ---
    @field_validator("tex")
    @classmethod
    def check_latex(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        ok, msg = validate_latex_string(v)
        if not ok:
            raise ValueError(f"LaTeX error: {msg}")
        return v


def _format_color(color_str: str) -> str:
    """Format a color value for Python code output."""
    if color_str.startswith("#"):
        return f'"{color_str}"'
    return color_str


def _format_range(r: list[float]) -> str:
    """Format range values, converting whole floats to ints for cleaner output."""
    formatted = [int(x) if x == int(x) else x for x in r]
    return str(formatted)


# ---------------------------------------------------------------------------
# Pydantic Schemas (The Agent Contracts)
# ---------------------------------------------------------------------------

class SceneEnvironment(BaseModel):
    """Macro container and timeline settings generated by the Architect."""
    scene_class: SceneClassLiteral = Field(
        description="Macro container (e.g. 'Scene', 'MovingCameraScene', 'ThreeDScene')."
    )
    camera_class: CameraClassLiteral = Field(
        default="Camera",
        description="Camera controller (e.g. 'ThreeDCamera', 'MovingCamera', 'Camera')."
    )
    required_plugins: list[str] = Field(
        default_factory=list,
        description="Required external plugins (e.g. ['manim-voiceover', 'manim-slides'])."
    )
    background_color: str = Field(
        default="#0E1117",
        description="Hex background color."
    )


class ManimMobject(BaseModel):
    """A concrete visual entity allocated by the Prop Master.

    The `config` field replaces the old freeform `initial_args: str`.
    This gives the 7B model typed slots to fill instead of raw Python.
    """
    model_config = ConfigDict(extra="allow")

    variable_name: str = Field(
        description="Valid Python identifier (e.g. 'axes', 'deriv_formula', 'time_tracker')."
    )
    manim_class: CoreMobjectLiteral = Field(
        description="Manim CE class from the verified Core catalog."
    )
    purpose: str = Field(
        description="Pedagogical role (e.g. 'Coordinate frame for plotting f(x)')."
    )
    config: MobjectConfig = Field(
        default_factory=MobjectConfig,
        description="Typed constructor arguments. Fill ONLY the relevant fields."
    )
    group_name: Optional[str] = Field(
        default=None,
        description=(
            "Optional VGroup name for grouping related objects. "
            "Objects sharing the same group_name will be assembled into a VGroup. "
            "Example: 'labels_group', 'equation_steps'"
        ),
    )

    @field_validator("manim_class")
    @classmethod
    def reject_abstract_base_classes(cls, v: str) -> str:
        if registry.is_abstract_base(v):
            children = registry.get_children(v)
            suggestion = f" Use one of: {', '.join(children[:5])}" if children else ""
            raise ValueError(
                f"'{v}' is an abstract base class and cannot be instantiated.{suggestion}"
            )
        return v

    @model_validator(mode="after")
    def validate_required_config(self) -> "ManimMobject":
        """Ensure required config fields are set for each class type."""
        c = self.config
        cls = self.manim_class

        if cls in ("MathTex", "Tex") and not c.tex:
            raise ValueError(
                f"{cls} requires a 'tex' string in config. "
                f"Example: config={{\"tex\": \"a^2 + b^2 = c^2\"}}"
            )
        if cls in ("Text", "Title") and not c.text:
            raise ValueError(
                f"{cls} requires a 'text' string in config. "
                f"Example: config={{\"text\": \"Hello World\"}}"
            )
        return self

    def to_constructor_call(self) -> str:
        """Generate the Python constructor call from typed config.

        This is the core method that eliminates freeform Python string generation.
        The 7B model fills structured fields; this method assembles correct Python.
        """
        args_str = self._build_args_string()
        return f"{self.manim_class}({args_str})"

    def _build_args_string(self) -> str:
        c = self.config
        cls = self.manim_class
        parts: list[str] = []

        # --- Positional arguments (class-specific) ---
        if cls in ("MathTex", "Tex", "SingleStringMathTex"):
            if c.tex:
                # Use triple-quoted raw strings if double quotes appear in LaTeX
                if '"' in c.tex:
                    parts.append(f"r'''{c.tex}'''")
                else:
                    parts.append(f'r"{c.tex}"')

        elif cls in ("Text", "Title", "MarkupText"):
            if c.text:
                safe = c.text.replace('"', '\\"')
                parts.append(f'"{safe}"')

        elif cls == "ValueTracker":
            parts.append(str(c.initial_value if c.initial_value is not None else 0))

        elif cls == "DecimalNumber":
            parts.append(str(c.initial_value if c.initial_value is not None else 0))

        elif cls == "FunctionGraph":
            expr = c.function_expr or "x"
            parts.append(f"lambda x: {expr}")

        elif cls in ("SurroundingRectangle", "Brace"):
            if c.reference_variable:
                parts.append(c.reference_variable)

        # --- Keyword arguments (class-specific) ---
        if cls in ("Axes", "NumberPlane", "NumberLine"):
            if c.x_range:
                parts.append(f"x_range={_format_range(c.x_range)}")
            if c.y_range and cls != "NumberLine":
                parts.append(f"y_range={_format_range(c.y_range)}")
            if c.x_length is not None and cls == "Axes":
                parts.append(f"x_length={c.x_length}")
            if c.y_length is not None and cls == "Axes":
                parts.append(f"y_length={c.y_length}")

        if cls in ("Circle", "Dot", "Arc", "Annulus") and c.radius is not None:
            parts.append(f"radius={c.radius}")

        if cls == "Square" and c.width is not None:
            parts.append(f"side_length={c.width}")

        if cls in ("Rectangle", "RoundedRectangle"):
            if c.width is not None:
                parts.append(f"width={c.width}")
            if c.height is not None:
                parts.append(f"height={c.height}")

        if cls in ("RegularPolygon", "Star") and c.n_sides is not None:
            parts.append(f"n={c.n_sides}")

        # --- Universal styling kwargs ---
        if c.color:
            parts.append(f"color={_format_color(c.color)}")
        if c.fill_opacity is not None:
            parts.append(f"fill_opacity={c.fill_opacity}")
        if c.font_size is not None and cls in (
            "MathTex", "Tex", "Text", "Title", "MarkupText", "DecimalNumber",
        ):
            parts.append(f"font_size={c.font_size}")

        return ", ".join(parts)


class SceneMobjectRoster(BaseModel):
    """The flat cast of nouns emitted by the Prop Master."""
    mobjects: list[ManimMobject]
    spatial_layout_intent: Literal[
        "SPLIT_STAGE", "CENTER_STACK", "FULLSCREEN_GRAPH", "QUADRANT_GRID"
    ] = Field(
        default="SPLIT_STAGE",
        description="Spatial intent informing the Layout Critic."
    )

    def get_imports(self) -> list[str]:
        """Collects unique import statements required by all allocated mobjects."""
        imports = {"from manim import *"}
        for m in self.mobjects:
            info = registry.get_info(m.manim_class)
            if info and info.get("module"):
                imports.add(f"from {info['module']} import {m.manim_class}")
        return sorted(list(imports))

    def get_variable_names(self) -> set[str]:
        """Returns all variable names including auto-generated VGroup names."""
        names = {m.variable_name for m in self.mobjects}
        group_names = {m.group_name for m in self.mobjects if m.group_name}
        return names | group_names

    def get_groups(self) -> dict[str, list[str]]:
        """Returns mapping of group_name -> [member variable names]."""
        groups: dict[str, list[str]] = {}
        for m in self.mobjects:
            if m.group_name:
                groups.setdefault(m.group_name, []).append(m.variable_name)
        return groups


class AnimationEvent(BaseModel):
    """A visual transition step in the scene choreography.

    Richer than the v1 schema: supports grouped animations, transforms,
    rate functions, pacing, and scene cleanup — all as typed fields.
    """
    model_config = ConfigDict(extra="allow")

    target_variables: list[str] = Field(
        min_length=1,
        description="Variable names to animate. Use one for simple, multiple for grouped."
    )
    animation_class: CoreAnimationLiteral = Field(
        description=(
            "Animation class: Create, Write, FadeIn, FadeOut, "
            "ReplacementTransform, Indicate, Circumscribe, GrowFromCenter, etc."
        ),
    )
    audio_bookmark_sync: str = Field(
        description="Voiceover bookmark ID this animation syncs to."
    )
    run_time: float = Field(
        default=1.0, ge=0.1, le=10.0,
        description="Animation duration in seconds."
    )

    # Transform support: ReplacementTransform(source, target)
    source_variable: Optional[str] = Field(
        default=None,
        description="Source variable for ReplacementTransform / TransformMatchingTex."
    )

    # Animation parameters
    rate_func: Literal[
        "linear", "smooth", "there_and_back",
        "rush_into", "rush_from", "ease_in_out_cubic"
    ] = Field(default="smooth", description="Animation easing function.")
    shift_direction: Optional[Literal["UP", "DOWN", "LEFT", "RIGHT"]] = Field(
        default=None, description="Shift direction for FadeIn/FadeOut."
    )
    lag_ratio: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="Stagger ratio for LaggedStart with multiple targets."
    )

    # Pacing: critical for watchable output
    wait_after: float = Field(
        default=0.3, ge=0.0, le=5.0,
        description="Seconds to pause after this animation for viewer comprehension."
    )

    # Scene cleanup: prevents screen clutter
    cleanup_before: list[str] = Field(
        default_factory=list,
        description="Variables to FadeOut before this animation begins."
    )

    @field_validator("animation_class")
    @classmethod
    def reject_abstract_animations(cls, v: str) -> str:
        if registry.is_abstract_base(v):
            children = registry.get_children(v)
            suggestion = f" Choose: {', '.join(children[:5])}" if children else ""
            raise ValueError(
                f"'{v}' is abstract and cannot be instantiated.{suggestion}"
            )
        return v

    @model_validator(mode="after")
    def validate_transform_source(self) -> "AnimationEvent":
        """Ensure transform animations have a source_variable."""
        transform_anims = {"ReplacementTransform", "TransformMatchingTex", "TransformMatchingShapes"}
        if self.animation_class in transform_anims and not self.source_variable:
            raise ValueError(
                f"{self.animation_class} requires a 'source_variable' field — "
                f"the object being transformed FROM."
            )
        return self


class SceneChoreography(BaseModel):
    """The complete temporal script synchronized with voiceover."""
    events: list[AnimationEvent]
    next_slide_bookmarks: list[str] = Field(
        default_factory=list,
        description="Bookmarks that trigger slide boundaries."
    )


# ---------------------------------------------------------------------------
# Cross-Validation Helpers
# ---------------------------------------------------------------------------

def validate_choreography_against_roster(
    choreography: SceneChoreography,
    roster: SceneMobjectRoster,
) -> list[str]:
    """Validates that all variable references in choreography exist in the roster.

    Returns a list of error messages (empty = valid).
    Called by the pipeline between the Choreographer output and the Assembler.
    """
    all_vars = roster.get_variable_names()
    errors: list[str] = []

    for i, event in enumerate(choreography.events):
        # Check animation targets
        for var in event.target_variables:
            if var not in all_vars:
                errors.append(
                    f"Event {i} ({event.animation_class}): target '{var}' "
                    f"not in roster. Available: {sorted(all_vars)}"
                )

        # Check transform source
        if event.source_variable and event.source_variable not in all_vars:
            errors.append(
                f"Event {i} ({event.animation_class}): source '{event.source_variable}' "
                f"not in roster."
            )

        # Check cleanup targets
        for var in event.cleanup_before:
            if var not in all_vars:
                errors.append(
                    f"Event {i}: cleanup target '{var}' not in roster."
                )

    return errors


# ---------------------------------------------------------------------------
# Prompt Summary Helpers — Core (for 7B agent prompts)
# ---------------------------------------------------------------------------

def get_core_mobjects_prompt() -> str:
    """Concise mobject catalog for 7B model system prompts."""
    return (
        "VERIFIED MOBJECTS (choose ONLY from this list):\n"
        "- Text & Math: Text, Title, MathTex, Tex, DecimalNumber\n"
        "- Coordinate Systems: Axes, NumberPlane, NumberLine\n"
        "- Geometry: Dot, Circle, Square, Rectangle, RoundedRectangle, "
        "Line, Arrow, DashedLine, Vector, Arc, RegularPolygon, Triangle, Star, Annulus\n"
        "- Grouping: VGroup, SurroundingRectangle, Brace\n"
        "- Drivers: ValueTracker\n"
        "- Functions: FunctionGraph"
    )


def get_core_animations_prompt() -> str:
    """Concise animation catalog for 7B model system prompts."""
    return (
        "VERIFIED ANIMATIONS (choose ONLY from this list):\n"
        "- Creation: Create, Write, DrawBorderThenFill\n"
        "- Fading: FadeIn, FadeOut\n"
        "- Growth: GrowFromCenter, GrowArrow, SpinInFromNothing\n"
        "- Transforms: ReplacementTransform, TransformMatchingTex, TransformMatchingShapes\n"
        "- Indications: Indicate, Circumscribe, Flash, Wiggle, FocusOn\n"
        "- Composition: AnimationGroup, Succession, LaggedStart\n"
        "- Motion: MoveAlongPath, Rotate\n"
        "- Removal: Uncreate, Unwrite, FadeOut"
    )


# ---------------------------------------------------------------------------
# Full Catalog Helpers — Kept for reference, SFT data gen, and debugging
# ---------------------------------------------------------------------------

def get_categorized_mobjects_prompt_summary() -> str:
    """Generates a full markdown catalog of valid mobjects (all 130+ classes)."""
    categories: Dict[str, list[str]] = {
        "Geometry & Shapes": [],
        "Lines & Vectors": [],
        "Coordinate Systems & Graphs": [],
        "Math & Text": [],
        "Tables & Matrices": [],
        "3D Volumes": [],
        "Drivers & Trackers": [],
    }
    for item in ROSTER_DATA.get("Mobjects", []):
        c = item["class_name"]
        mod = item["module"]
        if "three_d" in mod:
            categories["3D Volumes"].append(c)
        elif "coordinate_systems" in mod or "graph" in mod or "number_line" in mod:
            categories["Coordinate Systems & Graphs"].append(c)
        elif "tex" in mod or "text" in mod or "code" in mod:
            categories["Math & Text"].append(c)
        elif "matrix" in mod or "table" in mod:
            categories["Tables & Matrices"].append(c)
        elif "value_tracker" in mod:
            categories["Drivers & Trackers"].append(c)
        elif "line" in mod:
            categories["Lines & Vectors"].append(c)
        else:
            categories["Geometry & Shapes"].append(c)

    lines = []
    for cat, items in categories.items():
        if items:
            sample = ", ".join(sorted(items)[:12])
            suffix = f" ... (+{len(items) - 12} more)" if len(items) > 12 else ""
            lines.append(f"- **{cat}**: {sample}{suffix}")
    return "\n".join(lines)


def get_categorized_animations_prompt_summary() -> str:
    """Generates a full markdown catalog of valid animations."""
    categories: Dict[str, list[str]] = {
        "Creation & Drawing": [],
        "Fading & Growth": [],
        "Transformations": [],
        "Indications": [],
        "Motion & Speed": [],
    }
    for item in ROSTER_DATA.get("Animations", []):
        c = item["class_name"]
        mod = item["module"]
        if "creation" in mod:
            categories["Creation & Drawing"].append(c)
        elif "fading" in mod or "growing" in mod:
            categories["Fading & Growth"].append(c)
        elif "transform" in mod:
            categories["Transformations"].append(c)
        elif "indication" in mod:
            categories["Indications"].append(c)
        else:
            categories["Motion & Speed"].append(c)

    lines = []
    for cat, items in categories.items():
        if items:
            sample = ", ".join(sorted(items)[:10])
            suffix = f" ... (+{len(items) - 10} more)" if len(items) > 10 else ""
            lines.append(f"- **{cat}**: {sample}{suffix}")
    return "\n".join(lines)