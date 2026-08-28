from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

from manim import Mobject, VGroup, ORIGIN


@dataclass
class Rect:
    """Axis-aligned layout rectangle in Manim scene units (origin at center of frame)."""

    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y

    @property
    def top(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2.0

    @property
    def center(self) -> List[float]:
        return [self.center_x, self.center_y, 0.0]

    def inset(self, pad: float) -> "Rect":
        pad = min(pad, self.width / 2.0, self.height / 2.0)
        return Rect(self.x + pad, self.y + pad, max(self.width - 2 * pad, 0.01), max(self.height - 2 * pad, 0.01))

    def contains_mobject(self, mob: Mobject, epsilon: float = 0.08) -> bool:
        return (
            mob.get_left()[0] >= self.left - epsilon
            and mob.get_right()[0] <= self.right + epsilon
            and mob.get_bottom()[1] >= self.bottom - epsilon
            and mob.get_top()[1] <= self.top + epsilon
        )


@dataclass
class Size:
    width: float
    height: float


@dataclass
class LayoutContext:
    body_font_size: int = 24
    title_font_size: int = 40
    heading_font_size: int = 32
    equation_font_size: int = 42
    code_font_size: int = 18
    caption_font_size: int = 16
    diagram_scale: float = 1.0
    drop_decorations: bool = False
    collapse_columns: bool = False
    wrap_width: Optional[float] = None
    aspect_ratio: float = 16.0 / 9.0
    spacing: float = 0.28
    theme: object = None

    def copy(self) -> "LayoutContext":
        return LayoutContext(
            body_font_size=self.body_font_size,
            title_font_size=self.title_font_size,
            heading_font_size=self.heading_font_size,
            equation_font_size=self.equation_font_size,
            code_font_size=self.code_font_size,
            caption_font_size=self.caption_font_size,
            diagram_scale=self.diagram_scale,
            drop_decorations=self.drop_decorations,
            collapse_columns=self.collapse_columns,
            wrap_width=self.wrap_width,
            aspect_ratio=self.aspect_ratio,
            spacing=self.spacing,
            theme=self.theme,
        )


BuildFn = Callable[["LayoutContext", Rect], Mobject]


class LayoutNode:
    """Measurable, placeable layout unit. Coordinates are assigned only by the engine."""

    def __init__(
        self,
        *,
        role: str = "body",
        priority: int = 50,
        can_wrap: bool = False,
        can_scale: bool = True,
        align: str = "center",
    ) -> None:
        self.role = role
        self.priority = priority
        self.can_wrap = can_wrap
        self.can_scale = can_scale
        self.align = align
        self.dropped = False
        self.mobject: Optional[Mobject] = None
        self.cue_id: Optional[str] = None
        self.min_width = 0.4
        self.min_height = 0.2
        self.preferred_width: Optional[float] = None
        self.preferred_height: Optional[float] = None
        self.max_width: Optional[float] = None
        self.max_height: Optional[float] = None

    def children(self) -> Sequence["LayoutNode"]:
        return ()

    def measure(self, ctx: LayoutContext, available: Rect) -> Size:
        raise NotImplementedError

    def layout(self, ctx: LayoutContext, rect: Rect) -> Mobject:
        raise NotImplementedError

    def collect_mobjects(self) -> List[Mobject]:
        if self.dropped or self.mobject is None:
            return []
        return [self.mobject]


class LeafNode(LayoutNode):
    def __init__(
        self,
        builder: BuildFn,
        *,
        role: str = "body",
        priority: int = 50,
        can_wrap: bool = False,
        can_scale: bool = True,
        align: str = "center",
        keep_aspect: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(
            role=role,
            priority=priority,
            can_wrap=can_wrap,
            can_scale=can_scale,
            align=align,
        )
        self.builder = builder
        if "keep_aspect" in kwargs:
            keep_aspect = bool(kwargs.pop("keep_aspect"))
        self.keep_aspect = keep_aspect

    def measure(self, ctx: LayoutContext, available: Rect) -> Size:
        if self.dropped:
            return Size(0.0, 0.0)
        mob = self.builder(ctx, available)
        w = float(getattr(mob, "width", 0.0) or 0.0)
        h = float(getattr(mob, "height", 0.0) or 0.0)
        self.preferred_width = w
        self.preferred_height = h
        return Size(max(w, 0.01), max(h, 0.01))

    def layout(self, ctx: LayoutContext, rect: Rect) -> Mobject:
        if self.dropped:
            self.mobject = VGroup()
            return self.mobject
        mob = self.builder(ctx, rect)
        if self.can_scale:
            fit_mobject(mob, rect.width, rect.height, keep_aspect=True)
        place_mobject(mob, rect, self.align)
        self.mobject = mob
        return mob


def fit_mobject(
    mob: Mobject,
    max_w: float,
    max_h: float,
    *,
    keep_aspect: bool = True,
    min_scale: float = 0.35,
) -> Mobject:
    w = float(getattr(mob, "width", 0.0) or 0.0)
    h = float(getattr(mob, "height", 0.0) or 0.0)
    if w <= 1e-6 or h <= 1e-6:
        return mob
    sx = max_w / w
    sy = max_h / h
    if keep_aspect:
        s = min(sx, sy, 1.0)
        if s < 1.0:
            mob.scale(max(s, min_scale))
    else:
        if sx < 1.0 or sy < 1.0:
            mob.stretch_to_fit_width(min(w, max_w))
            if float(mob.height) > max_h:
                mob.stretch_to_fit_height(max_h)
    return mob


def place_mobject(mob: Mobject, rect: Rect, align: str = "center") -> Mobject:
    cx, cy = rect.center_x, rect.center_y
    w = float(getattr(mob, "width", 0.0) or 0.0)
    h = float(getattr(mob, "height", 0.0) or 0.0)
    if align in ("top", "top-center"):
        cy = rect.top - h / 2.0
    elif align in ("bottom", "bottom-center"):
        cy = rect.bottom + h / 2.0
    if align in ("left", "top-left", "bottom-left"):
        cx = rect.left + w / 2.0
    elif align in ("right", "top-right", "bottom-right"):
        cx = rect.right - w / 2.0
    if align == "top-left":
        cy = rect.top - h / 2.0
        cx = rect.left + w / 2.0
    mob.move_to([cx, cy, 0.0])
    return mob
