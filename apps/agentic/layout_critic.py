"""Deterministic Layout Critic (Spatial Engine) for Manim CE.

Bridges the Prop Master (Mobjects) and Choreographer (Animations) agents.
Resolves spatial blindness, prevents bounding-box collisions, bounds-checks against
the Manim 16:9 camera frame (14.22 x 8.0 units), and emits deterministic placement
directives (.next_to, .to_edge, .move_to, .align_to).

v2 CHANGES:
  - Reads from MobjectConfig dict (typed fields) instead of freeform initial_args
  - Expanded size estimates for all Core 28 classes
  - More accurate sizing using config dimensions (e.g., Axes x_length/y_length)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Manim 16:9 Safe Camera Frame Constants (Manim CE defaults: 14.22 x 8.0)
# ---------------------------------------------------------------------------
FRAME_WIDTH: float = 14.222222222222221
FRAME_HEIGHT: float = 8.0
FRAME_X_RADIUS: float = FRAME_WIDTH / 2.0   # ~7.11
FRAME_Y_RADIUS: float = FRAME_HEIGHT / 2.0  # ~4.00

# Safe Title/Action margins (prevent rendering outside screen boundaries)
SAFE_MARGIN_X: float = 0.8
SAFE_MARGIN_Y: float = 0.6
SAFE_X_MIN: float = -FRAME_X_RADIUS + SAFE_MARGIN_X  # ~ -6.31
SAFE_X_MAX: float = FRAME_X_RADIUS - SAFE_MARGIN_X   # ~ +6.31
SAFE_Y_MIN: float = -FRAME_Y_RADIUS + SAFE_MARGIN_Y  # ~ -3.40
SAFE_Y_MAX: float = FRAME_Y_RADIUS - SAFE_MARGIN_Y   # ~ +3.40

# Standardized Layout Buffers
LABEL_BUFF: float = 0.2
SECTION_BUFF: float = 0.6


class Direction(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UL = "UL"
    UR = "UR"
    DL = "DL"
    DR = "DR"
    ORIGIN = "ORIGIN"

    def to_vector(self) -> Tuple[float, float, float]:
        vectors = {
            Direction.UP: (0.0, 1.0, 0.0),
            Direction.DOWN: (0.0, -1.0, 0.0),
            Direction.LEFT: (-1.0, 0.0, 0.0),
            Direction.RIGHT: (1.0, 0.0, 0.0),
            Direction.UL: (-1.0, 1.0, 0.0),
            Direction.UR: (1.0, 1.0, 0.0),
            Direction.DL: (-1.0, -1.0, 0.0),
            Direction.DR: (1.0, -1.0, 0.0),
            Direction.ORIGIN: (0.0, 0.0, 0.0),
        }
        return vectors[self]


class SpatialZone(str, Enum):
    """Semantic macro zones for canonical pedagogical canvas layouts."""
    TOP_BANNER = "TOP_BANNER"         # Title / Header (y in [3.0, 3.8])
    MAIN_CENTER = "MAIN_CENTER"       # Fullscreen centered focus
    WORKING_MARGIN = "WORKING_MARGIN" # Left margin (x in [-6.5, -2.0])
    HERO_CANVAS = "HERO_CANVAS"       # Main graphics (x in [-2.0, 6.0])
    BOTTOM_FOOTER = "BOTTOM_FOOTER"   # Progress bar, takeaways, subtitles
    QUADRANT_UL = "QUADRANT_UL"
    QUADRANT_UR = "QUADRANT_UR"
    QUADRANT_DL = "QUADRANT_DL"
    QUADRANT_DR = "QUADRANT_DR"


@dataclass
class BoundingBox:
    """Axis-Aligned Bounding Box (AABB) in Manim world coordinates."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @property
    def width(self) -> float:
        return max(0.0, self.x_max - self.x_min)

    @property
    def height(self) -> float:
        return max(0.0, self.y_max - self.y_min)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0)

    def intersects(self, other: BoundingBox, buff: float = 0.15) -> bool:
        """Returns True if this bounding box overlaps with another, including buffer."""
        return not (
            self.x_max + buff < other.x_min
            or self.x_min - buff > other.x_max
            or self.y_max + buff < other.y_min
            or self.y_min - buff > other.y_max
        )

    def is_within_safe_frame(self) -> bool:
        """Verifies if the bounding box sits strictly inside safe camera view."""
        return (
            self.x_min >= SAFE_X_MIN
            and self.x_max <= SAFE_X_MAX
            and self.y_min >= SAFE_Y_MIN
            and self.y_max <= SAFE_Y_MAX
        )

    def shifted(self, dx: float, dy: float) -> BoundingBox:
        return BoundingBox(
            x_min=self.x_min + dx,
            x_max=self.x_max + dx,
            y_min=self.y_min + dy,
            y_max=self.y_max + dy,
        )


# ---------------------------------------------------------------------------
# Pydantic Schemas for Layout Directives & Constraint Solver Output
# ---------------------------------------------------------------------------

class PlacementMethod(str, Enum):
    TO_EDGE = "to_edge"
    TO_CORNER = "to_corner"
    NEXT_TO = "next_to"
    ALIGN_TO = "align_to"
    MOVE_TO = "move_to"
    ZONE_ASSIGN = "zone_assign"
    NOOP = "noop"  # For invisible mobjects like ValueTracker


class PlacementConstraint(BaseModel):
    variable_name: str = Field(description="Target variable being positioned.")
    method: PlacementMethod = Field(description="Manim alignment method.")
    reference_variable: Optional[str] = Field(default=None, description="Anchor variable for relative alignment.")
    direction: Optional[Direction] = Field(default=Direction.DOWN, description="Placement vector / direction.")
    buff: float = Field(default=0.5, description="Padding / buffer distance in scene units.")
    zone: Optional[SpatialZone] = Field(default=None, description="Preset canvas zone if absolute.")


class ResolvedLayoutItem(BaseModel):
    variable_name: str
    is_visual: bool = True
    code_statement: str = Field(description="Exact executable Manim Python code line.")
    center_coords: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bbox_dimensions: Tuple[float, float] = (0.0, 0.0)  # (width, height)
    spatial_zone: Optional[SpatialZone] = None


class SceneLayoutState(BaseModel):
    """The verified spatial contract returned by the Layout Critic."""
    placements: list[ResolvedLayoutItem]
    layout_code: list[str] = Field(description="Aggregated ordered Python statements for the scene setup.")
    warnings: list[str] = Field(default_factory=list)
    has_clipping_risk: bool = False
    has_collision_risk: bool = False


# ---------------------------------------------------------------------------
# Deterministic Spatial Estimator & Layout Solver
# ---------------------------------------------------------------------------

class LayoutCritic:
    """Deterministic Spatial Engine for Manim CE.

    1. Filters out non-spatial mobjects (e.g., ValueTracker).
    2. Heuristically approximates mobject AABBs prior to rendering.
    3. Resolves constraint graph dependencies (Topological ordering).
    4. Detects AABB intersections and calculates non-overlapping shifts.
    5. Clamps and scales objects to prevent screen clipping.
    6. Emits executable Python layout statements for the Choreographer.
    """

    NON_VISUAL_CLASSES = {"ValueTracker", "ComplexValueTracker"}

    ZONE_DEFINITIONS: Dict[SpatialZone, Tuple[float, float, float, float]] = {
        SpatialZone.TOP_BANNER: (0.0, 3.4, 11.0, 0.8), # y in [3.0, 3.8]
        SpatialZone.MAIN_CENTER: (0.0, 0.0, 11.0, 5.5),
        SpatialZone.WORKING_MARGIN: (-4.25, 0.0, 4.5, 5.2), # x in [-6.5, -2.0]
        SpatialZone.HERO_CANVAS: (2.0, 0.0, 8.0, 5.2), # x in [-2.0, 6.0]
        SpatialZone.BOTTOM_FOOTER: (0.0, -2.85, 11.0, 0.6),
        SpatialZone.QUADRANT_UL: (-3.3, 1.6, 5.5, 2.5),
        SpatialZone.QUADRANT_UR: (3.3, 1.6, 5.5, 2.5),
        SpatialZone.QUADRANT_DL: (-3.3, -1.6, 5.5, 2.5),
        SpatialZone.QUADRANT_DR: (3.3, -1.6, 5.5, 2.5),
    }

    def estimate_mobject_size(
        self,
        manim_class: str,
        config: dict,
    ) -> Tuple[float, float]:
        """Approximates width and height of standard Manim CE classes.

        v2: Reads from typed MobjectConfig dict instead of freeform initial_args.
        This enables more accurate sizing from Axes x_length/y_length, text length, etc.
        """
        if manim_class in self.NON_VISUAL_CLASSES:
            return (0.0, 0.0)

        # --- Text & Math ---
        if manim_class in ("MathTex", "Tex", "SingleStringMathTex"):
            tex = config.get("tex", "") or ""
            char_count = max(8, len(tex))
            width = min(6.5, max(1.2, char_count * 0.18))
            return (width, 0.8)

        if manim_class == "Title":
            text = config.get("text", "") or ""
            width = min(8.0, max(4.0, len(text) * 0.22))
            return (width, 0.9)

        if manim_class in ("Text", "MarkupText"):
            text = config.get("text", "") or ""
            char_count = max(8, len(text))
            width = min(6.5, max(1.5, char_count * 0.16))
            return (width, 0.8)

        if manim_class == "DecimalNumber":
            return (1.5, 0.5)

        # --- Coordinate Systems ---
        if manim_class in ("Axes",):
            x_len = config.get("x_length") or 5.8
            y_len = config.get("y_length") or 4.0
            return (float(x_len), float(y_len))

        if manim_class in ("NumberPlane", "ComplexPlane"):
            return (6.0, 4.0)

        if manim_class == "NumberLine":
            return (6.0, 0.4)

        # --- Geometry: Points & Circles ---
        if manim_class in ("Dot", "AnnotationDot"):
            radius = config.get("radius") or 0.08
            return (float(radius) * 2, float(radius) * 2)

        if manim_class == "Circle":
            radius = config.get("radius") or 1.0
            return (float(radius) * 2, float(radius) * 2)

        if manim_class == "Arc":
            radius = config.get("radius") or 1.0
            return (float(radius) * 2, float(radius) * 2)

        if manim_class == "Annulus":
            return (2.0, 2.0)

        if manim_class == "AnnularSector":
            return (2.0, 2.0)

        # --- Geometry: Rectangles & Squares ---
        if manim_class == "Square":
            side = config.get("width") or 2.0
            return (float(side), float(side))

        if manim_class in ("Rectangle", "RoundedRectangle"):
            w = config.get("width") or 3.5
            h = config.get("height") or 1.8
            return (float(w), float(h))

        # --- Geometry: Polygons ---
        if manim_class in ("RegularPolygon", "Triangle"):
            return (2.0, 2.0)

        if manim_class == "Star":
            return (2.0, 2.0)

        # --- Geometry: Lines & Arrows ---
        if manim_class in ("Line", "DashedLine"):
            return (3.0, 0.1)

        if manim_class in ("Arrow", "Vector"):
            return (3.0, 0.3)

        # --- Functions & Curves ---
        if manim_class == "FunctionGraph":
            return (5.5, 3.5)

        if manim_class == "ParametricFunction":
            return (4.0, 3.0)

        # --- Grouping & Annotations ---
        if manim_class == "VGroup":
            return (0.0, 0.0)  # Size depends on contents, handled separately

        if manim_class == "SurroundingRectangle":
            # Size depends on the referenced mobject + buff
            ref_var = config.get("reference_variable")
            # We can't resolve this without the actual object; use a reasonable default
            return (3.0, 1.5)

        if manim_class in ("Brace", "BraceBetweenPoints"):
            return (3.0, 0.4)

        # --- Tables & Matrices ---
        if manim_class in ("Matrix", "DecimalMatrix", "IntegerMatrix", "Table"):
            return (4.0, 2.5)

        # --- Default fallback ---
        return (2.5, 1.5)

    def solve(
        self,
        roster_items: list[dict],
        explicit_constraints: Optional[list[PlacementConstraint]] = None,
    ) -> SceneLayoutState:
        """Computes deterministic positions, prevents collisions, and yields Python code.

        v2: roster_items dicts now contain 'config' dict instead of 'initial_args' string.
        """
        resolved: list[ResolvedLayoutItem] = []
        occupied_boxes: Dict[str, BoundingBox] = {}
        warnings: list[str] = []
        layout_code_lines: list[str] = []
        has_clipping = False
        has_collision = False

        constraints_map: Dict[str, PlacementConstraint] = {}
        if explicit_constraints:
            for c in explicit_constraints:
                constraints_map[c.variable_name] = c

        visual_items = []
        for item in roster_items:
            var_name = item.get("variable_name")
            m_class = item.get("manim_class")

            if m_class in self.NON_VISUAL_CLASSES:
                resolved.append(
                    ResolvedLayoutItem(
                        variable_name=var_name,
                        is_visual=False,
                        code_statement=f"# {var_name} ({m_class}) is a driver; no canvas placement needed.",
                        center_coords=(0.0, 0.0, 0.0),
                        bbox_dimensions=(0.0, 0.0),
                    )
                )
            else:
                visual_items.append(item)

        # Strategy Selection:
        # If we have both coordinate axes and mathematical formulas, adopt a SPLIT stage
        has_axes = any(i.get("manim_class") in {"Axes", "NumberPlane", "ComplexPlane"} for i in visual_items)
        has_formulas = any(i.get("manim_class") in {"MathTex", "Tex"} for i in visual_items)
        stage_mode = "SPLIT" if (has_axes and has_formulas) else "CENTER"

        for idx, item in enumerate(visual_items):
            var_name = item.get("variable_name")
            m_class = item.get("manim_class")
            config = item.get("config") or {}
            # Handle the case where config is a MobjectConfig Pydantic model (call dict())
            if hasattr(config, "model_dump"):
                config = config.model_dump()

            w, h = self.estimate_mobject_size(m_class, config)

            constraint = constraints_map.get(var_name)
            scale_prefix = ""

            # Check if initial width exceeds safe zone width
            max_allowed_w = 5.5 if stage_mode == "SPLIT" else 11.0
            if w > max_allowed_w:
                w = max_allowed_w
                scale_prefix = f"{var_name}.scale_to_fit_width({max_allowed_w})\n"

            if constraint:
                placed_box, base_placement = self._resolve_explicit_constraint(
                    var_name, constraint, w, h, occupied_boxes
                )
                assigned_zone = constraint.zone
            else:
                placed_box, base_placement, assigned_zone = self._resolve_heuristic_placement(
                    var_name, m_class, idx, w, h, stage_mode, occupied_boxes
                )

            # Collision Check & Relaxation Loop
            for other_name, other_box in occupied_boxes.items():
                if placed_box.intersects(other_box, buff=0.2):
                    has_collision = True
                    warnings.append(
                        f"Collision detected between '{var_name}' and '{other_name}'. Applying orthogonal relaxation."
                    )
                    # Relax by placing strictly below the colliding object
                    shift_dy = - (other_box.height / 2.0 + placed_box.height / 2.0 + 0.35)
                    placed_box = placed_box.shifted(0.0, shift_dy)
                    base_placement = f"{var_name}.next_to({other_name}, DOWN, buff=0.35)"

            # Bounds Check and Clamping
            if not placed_box.is_within_safe_frame():
                has_clipping = True
                warnings.append(f"Mobject '{var_name}' out of safe 16:9 boundary. Clamping to frame.")
                cx = max(SAFE_X_MIN + w / 2, min(SAFE_X_MAX - w / 2, placed_box.center[0]))
                cy = max(SAFE_Y_MIN + h / 2, min(SAFE_Y_MAX - h / 2, placed_box.center[1]))
                placed_box = BoundingBox(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)
                base_placement = f"{var_name}.move_to([{round(cx, 2)}, {round(cy, 2)}, 0])"

            occupied_boxes[var_name] = placed_box
            cx, cy = placed_box.center

            full_code = f"{scale_prefix}{base_placement}".strip()
            layout_code_lines.append(full_code)

            resolved.append(
                ResolvedLayoutItem(
                    variable_name=var_name,
                    is_visual=True,
                    code_statement=full_code,
                    center_coords=(round(cx, 3), round(cy, 3), 0.0),
                    bbox_dimensions=(round(w, 3), round(h, 3)),
                    spatial_zone=assigned_zone,
                )
            )

        return SceneLayoutState(
            placements=resolved,
            layout_code=layout_code_lines,
            warnings=warnings,
            has_clipping_risk=has_clipping,
            has_collision_risk=has_collision,
        )

    def _resolve_explicit_constraint(
        self,
        var_name: str,
        constraint: PlacementConstraint,
        w: float,
        h: float,
        occupied: Dict[str, BoundingBox],
    ) -> Tuple[BoundingBox, str]:
        method = constraint.method

        if method == PlacementMethod.TO_EDGE:
            dir_str = constraint.direction.value if constraint.direction else "UP"
            vx, vy, _ = (constraint.direction or Direction.UP).to_vector()
            buff = constraint.buff
            cx = vx * (FRAME_X_RADIUS - SAFE_MARGIN_X - w / 2.0)
            cy = vy * (FRAME_Y_RADIUS - SAFE_MARGIN_Y - h / 2.0)
            box = BoundingBox(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)
            return box, f"{var_name}.to_edge({dir_str}, buff={buff})"

        if method == PlacementMethod.NEXT_TO and constraint.reference_variable in occupied:
            ref_box = occupied[constraint.reference_variable]
            dir_str = constraint.direction.value if constraint.direction else "DOWN"
            vx, vy, _ = (constraint.direction or Direction.DOWN).to_vector()
            buff = constraint.buff
            ref_cx, ref_cy = ref_box.center

            if vx != 0:
                cx = ref_cx + vx * (ref_box.width / 2.0 + w / 2.0 + buff)
                cy = ref_cy
            else:
                cx = ref_cx
                cy = ref_cy + vy * (ref_box.height / 2.0 + h / 2.0 + buff)

            box = BoundingBox(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)
            return box, f"{var_name}.next_to({constraint.reference_variable}, {dir_str}, buff={buff})"

        box = BoundingBox(-w / 2, w / 2, -h / 2, h / 2)
        return box, f"{var_name}.move_to(ORIGIN)"

    def _resolve_heuristic_placement(
        self,
        var_name: str,
        manim_class: str,
        index: int,
        w: float,
        h: float,
        stage_mode: str,
        occupied: Dict[str, BoundingBox],
    ) -> Tuple[BoundingBox, str, Optional[SpatialZone]]:
        # 1. Header / Title
        if manim_class in {"Title"} or (manim_class in {"Text", "MarkupText"} and index == 0):
            cx, cy, _, _ = self.ZONE_DEFINITIONS[SpatialZone.TOP_BANNER]
            box = BoundingBox(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)
            return box, f"{var_name}.to_edge(UP, buff=0.5)", SpatialZone.TOP_BANNER

        # 2. Split Stage: Working Margin (Derivations) vs Hero Canvas (Visuals)
        if stage_mode == "SPLIT":
            if manim_class in {"Axes", "NumberPlane", "ComplexPlane", "FunctionGraph"}:
                cx, cy, _, _ = self.ZONE_DEFINITIONS[SpatialZone.HERO_CANVAS]
                box = BoundingBox(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)
                return box, f"{var_name}.to_edge(RIGHT, buff={SECTION_BUFF})", SpatialZone.HERO_CANVAS
            elif manim_class in {"MathTex", "Tex"}:
                # Find if an item already exists in WORKING_MARGIN
                existing_margin = [
                    (name, b) for name, b in occupied.items()
                    if b.center[0] < -2.0 and b.center[1] < 2.5
                ]
                if existing_margin:
                    last_name, last_box = existing_margin[-1]
                    cx = last_box.x_min + (w / 2.0)  # Anchor to left edge
                    cy = last_box.y_min - SECTION_BUFF - (h / 2.0)
                    box = BoundingBox(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)
                    return box, f"{var_name}.next_to({last_name}, DOWN, buff={SECTION_BUFF}, aligned_edge=LEFT)", SpatialZone.WORKING_MARGIN
                else:
                    cx, cy, _, _ = self.ZONE_DEFINITIONS[SpatialZone.WORKING_MARGIN]
                    box = BoundingBox(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)
                    return box, f"{var_name}.to_edge(LEFT, buff={SECTION_BUFF})", SpatialZone.WORKING_MARGIN

        # 3. Default Center Stage
        if not occupied:
            box = BoundingBox(-w / 2, w / 2, -h / 2, h / 2)
            return box, f"{var_name}.move_to(ORIGIN)", SpatialZone.MAIN_CENTER
        else:
            last_name = list(occupied.keys())[-1]
            last_box = occupied[last_name]
            cx = 0.0
            cy = last_box.y_min - SECTION_BUFF - (h / 2.0)
            box = BoundingBox(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2)
            return box, f"{var_name}.next_to({last_name}, DOWN, buff={SECTION_BUFF})", SpatialZone.MAIN_CENTER


# Singleton instance
layout_critic = LayoutCritic()
