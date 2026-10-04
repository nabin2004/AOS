"""Logical world coordinates, viewport portal, and light-weight authoring helpers.

Transforms sit **above** canvas backends (see pipeline in ``WorldPortal``).

Domain: horizontal world ``x`` runs from ``-world_width/2`` … ``+world_width/2``
(for ``world_width=10``, ``x=-5`` is the left edge at ``y=0``).

``Scene.camera`` / :class:`~motiongram.animate.CameraPan` operate in **pixel** space after
:class:`WorldPortal` (portal outputs frame pixels consumed by ``SkiaRenderer``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, NamedTuple

from motiongram.canvas import Canvas
from motiongram.core import Node
from motiongram.shapes import Rectangle

CHARACTER_HEIGHT_UNITS = 1.8
DEFAULT_GROUND_Y = -2.5

Anchor = Literal["center", "top", "bottom", "left", "right"]

__all__ = [
    "CHARACTER_HEIGHT_UNITS",
    "DEFAULT_GROUND_Y",
    "SemanticPart",
    "WorldPortal",
    "WorldShellNodes",
    "WorldSpec",
    "apply_gravity_step",
    "attach",
    "default_world_height",
    "ground_strip",
    "mirror_x",
    "place_on_ground",
    "project_depth_fake",
    "screen_to_world",
    "world_pixel_affine_coeffs",
    "world_shell",
    "world_to_screen",
]


def default_world_height(world_width: float, frame_w: int, frame_h: int) -> float:
    """World height preserving frame aspect ratio (WORLD_WIDTH mapped with frame edges)."""

    if frame_w <= 0:
        raise ValueError("frame_w must be positive")
    return float(world_width) * float(frame_h) / float(frame_w)


@dataclass(slots=True)
class WorldSpec:
    """Logical extents and authoring defaults."""

    world_width: float = 10.0
    world_height: float = 0.0  # 0 = derive from frame when resolving height
    ground_y: float = DEFAULT_GROUND_Y
    y_down: bool = True
    depth_scale_k: float = 0.2
    depth_shift_px: float = 40.0

    def resolved_height(self, frame_w: int, frame_h: int) -> float:
        h = self.world_height
        if h > 0.0:
            return float(h)
        return default_world_height(self.world_width, frame_w, frame_h)


def world_pixel_affine_coeffs(
    spec: WorldSpec, frame_w: int, frame_h: int
) -> tuple[float, float, float, float, float, float]:
    """Affine coeffs ``(ax, bx, cx, ay, by, cy)``: world-units → frame pixels (top-left)."""

    ww = float(spec.world_width)
    hh = spec.resolved_height(frame_w, frame_h)
    if ww <= 0.0 or hh <= 0.0:
        raise ValueError("world_width and resolved world_height must be positive")
    fw, fh = float(frame_w), float(frame_h)
    ax = fw / ww
    bx = 0.0
    cx = fw / 2.0
    ay = 0.0
    if spec.y_down:
        by = fh / hh
        cy = fh / 2.0
    else:
        by = -fh / hh
        cy = fh / 2.0
    return (ax, bx, cx, ay, by, cy)


def world_to_screen(
    x: float,
    y: float,
    *,
    spec: WorldSpec,
    frame_w: int,
    frame_h: int,
    cam_x: float = 0.0,
    cam_y: float = 0.0,
    zoom: float = 1.0,
) -> tuple[float, float]:
    """World ``(x, y)`` → frame pixels (camera args live in world space)."""

    x1 = (float(x) - float(cam_x)) * float(zoom)
    y1 = (float(y) - float(cam_y)) * float(zoom)
    ww = float(spec.world_width)
    hh = spec.resolved_height(frame_w, frame_h)
    sx = (x1 / ww + 0.5) * float(frame_w)
    sy = (
        (y1 / hh + 0.5) * float(frame_h)
        if spec.y_down
        else (-y1 / hh + 0.5) * float(frame_h)
    )
    return (sx, sy)


def screen_to_world(
    sx: float,
    sy: float,
    *,
    spec: WorldSpec,
    frame_w: int,
    frame_h: int,
    cam_x: float = 0.0,
    cam_y: float = 0.0,
    zoom: float = 1.0,
) -> tuple[float, float]:
    """Inverse of :func:`world_to_screen` (rectilinear; ignores rotation)."""

    z = float(zoom)
    if abs(z) < 1e-12:
        raise ValueError("zoom must be non-zero")
    ww = float(spec.world_width)
    hh = spec.resolved_height(frame_w, frame_h)
    x1 = (float(sx) / float(frame_w) - 0.5) * ww
    y1 = (
        (float(sy) / float(frame_h) - 0.5) * hh
        if spec.y_down
        else -(float(sy) / float(frame_h) - 0.5) * hh
    )
    return (x1 / z + float(cam_x), y1 / z + float(cam_y))


def place_on_ground(node: Node, ground_y: float) -> None:
    """Pin ``node.y`` to the logical ground line (world units under a portal)."""

    node.y = float(ground_y)


def ground_strip(
    spec: WorldSpec,
    *,
    ground_y: float | None = None,
    thickness: float = 0.08,
    fill_color: str = "#2C4C3E",
    stroke_color: str | None = None,
    stroke_width: float = 0.0,
) -> Node:
    """Full-width band in world units whose **top** edge sits on the ground line.

    Child :class:`~motiongram.shapes.Rectangle` uses top-left anchoring; the returned
    :class:`~motiongram.core.Node` is placed at ``x = -world_width/2``, ``y = gy`` so
    the strip spans ``[-world_width/2, +world_width/2]`` horizontally and extends
    downward by ``thickness`` (for default ``WorldSpec.y_down``).
    """

    ww = float(spec.world_width)
    if ww <= 0.0:
        raise ValueError("world_width must be positive")
    gy = float(spec.ground_y) if ground_y is None else float(ground_y)
    t = float(thickness)
    if t <= 0.0:
        raise ValueError("thickness must be positive")
    root = Node(x=-ww / 2.0, y=gy)
    root.add(
        Rectangle(
            x=0.0,
            y=0.0,
            width=ww,
            height=t,
            fill_color=fill_color,
            stroke_color=stroke_color,
            stroke_width=float(stroke_width),
        )
    )
    return root


def project_depth_fake(
    z: float,
    *,
    k: float | None = None,
    dy_per_z: float | None = None,
    spec: WorldSpec | None = None,
) -> tuple[float, float]:
    """``(scale, dy)`` for a simple 2.5D illusion (scale + vertical shift)."""

    kk = (float(spec.depth_scale_k) if spec is not None else 0.2) if k is None else float(k)
    dyz = (
        float(spec.depth_shift_px)
        if spec is not None and dy_per_z is None
        else (40.0 if dy_per_z is None else float(dy_per_z))
    )
    scale = 1.0 / (1.0 + float(z) * kk)
    dy = float(z) * dyz
    return (scale, dy)


@dataclass(slots=True)
class SemanticPart(Node):
    """Named logical part of a rig (no geometry until children are added)."""

    role: str | None = None


class WorldShellNodes(NamedTuple):
    """Named containers for intent-targeted composition."""

    world: Node
    background: Node
    midground: Node
    foreground: Node
    props: Node
    characters: Node


def world_shell() -> WorldShellNodes:
    """``world → {bg, mid, fg}`` with ``props`` / ``characters`` under mid."""

    shell_world = Node()
    background = Node()
    midground = Node()
    foreground = Node()
    props = Node()
    characters = Node()
    midground.add(props)
    midground.add(characters)
    shell_world.add(background)
    shell_world.add(midground)
    shell_world.add(foreground)
    return WorldShellNodes(shell_world, background, midground, foreground, props, characters)


def attach(
    child: Node,
    parent: Node,
    anchor: Anchor = "center",
    offset: tuple[float, float] = (0.0, 0.0),
) -> None:
    """Place ``child`` relative to ``parent`` using named anchors (stub)."""

    _ = child, parent, anchor, offset
    raise NotImplementedError(
        "attach(): parent bounds semantics (e.g. sized nodes) missing; duplicate rig "
        "parts by hand for now."
    )


def mirror_x(node_like: Node) -> Node:
    """Deep-mirror a subtree across local X (stub)."""

    _ = node_like
    raise NotImplementedError(
        "mirror_x(): scene-graph deep-copy is undefined; duplicate symmetric "
        "parts manually for now."
    )


def apply_gravity_step(
    node: Node,
    dt: float,
    ground_y: float,
    *,
    gravity: float = 9.8,
    vy_attr: str = "vy",
) -> None:
    """Integrate vertical gravity (stub).

    Prefer timeline animators for authored clip motion; see AGENTS.md.
    """

    _ = node, dt, ground_y, gravity, vy_attr
    raise NotImplementedError(
        "apply_gravity_step() not wired — use timeline animators for authored motion."
    )


@dataclass(slots=True)
class WorldPortal(Node):
    """Map subtree ``x`` / ``y`` in world units to frame pixels."""

    spec: WorldSpec = field(default_factory=WorldSpec)
    frame_width: int = 1920
    frame_height: int = 1080

    def draw(self, canvas: Canvas, ox: float = 0.0, oy: float = 0.0) -> None:
        px = ox + self.x
        py = oy + self.y
        push = getattr(canvas, "push_node_transform", None)
        pop = getattr(canvas, "pop_transform", None)
        apush = getattr(canvas, "push_affine_2x3", None)
        apop = getattr(canvas, "pop_affine_2x3", None)

        coeffs = world_pixel_affine_coeffs(self.spec, self.frame_width, self.frame_height)
        affine_ok = apush is not None and apop is not None

        if push is not None and pop is not None:
            push(px, py, self.rotation, self.scale_x, self.scale_y, self.opacity, self.blur_sigma)
            if affine_ok:
                assert apush is not None and apop is not None
                ax, bx, cx, ay, by, cy = coeffs
                apush(ax, bx, cx, ay, by, cy)
            self.draw_world(canvas, 0.0, 0.0)
            for child in self.children:
                child.draw(canvas, 0.0, 0.0)
            if affine_ok:
                assert apush is not None and apop is not None
                apop()
            pop()
        else:
            self.draw_world(canvas, px, py)
            for child in self.children:
                child.draw(canvas, px, py)
