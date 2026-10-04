"""Rainy landscape preset: manifest, materialization, and timeline hooks.

This module is the home for the procedural content that used to live entirely in
``examples/principles/26_world_viewport.py``.  It only uses the public MotionGram
world/scene API.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from motiongram import MoveX, MoveY, ground_strip, place_on_ground
from motiongram.core import Node, Scene
from motiongram.shapes import Ellipse, Line, Polygon, Rectangle
from motiongram.world import WorldShellNodes, WorldSpec

# ---------------------------------------------------------------------------
# Small world-space helpers (duplicated from principle demo docstrings on purpose)
# ---------------------------------------------------------------------------


def resting_anchor_y(*, ground_y: float, radius_y: float) -> float:
    """World-space centre-*y* so the bottom of an axis-aligned ellipse rests on *ground_y*.

    In ``WorldSpec``'s default y-down space, the lowest point of an ellipse centred
    at ``cy`` with vertical radius ``radius_y`` is ``cy + radius_y``.  Pinning that
    to ``ground_y`` yields ``cy = ground_y - radius_y``.
    """
    return float(ground_y) - float(radius_y)


# ---------------------------------------------------------------------------
# Manifest (data-only; safe to log, diff, and later lower from an IR)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StarFieldSpec:
    count: int
    columns: int
    """World x of first star: ``-world_width/2 + x_start_off``."""
    x_start_off: float
    x_stride: float
    y0: float
    y_row_stride: float
    y_mod_stride: float
    y_mod_period: int
    star_rx: float
    star_ry: float
    fill_color: str


@dataclass(frozen=True)
class HillTerrainSpec:
    fill_color: str
    """Vertices as ``(x_norm, dy_from_ground)`` with ``x = x_norm * world_width/2``."""
    ring_xy_norm_dy: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class GroundBackdropSpec:
    strip_thickness: float
    strip_fill: str


@dataclass(frozen=True)
class SunSpriteSpec:
    cx: float
    cy: float
    rx: float
    ry: float
    fill_color: str
    stroke_color: str
    stroke_width: float


@dataclass(frozen=True)
class CloudPuff:
    ox: float
    oy: float
    rx: float
    ry: float


@dataclass(frozen=True)
class CloudSpriteSpec:
    fill_color: str
    stroke_color: str
    stroke_width: float
    puffs: tuple[CloudPuff, ...]


@dataclass(frozen=True)
class CloudPlacement:
    cx: float
    cy: float


@dataclass(frozen=True)
class PineTreeSpec:
    x: float
    scale: float


@dataclass(frozen=True)
class RockPlacement:
    cx: float
    rx: float
    ry: float
    fill_color: str


@dataclass(frozen=True)
class GrassStripSpec:
    blades: int
    x0_world_off: float
    x_stride: float
    x_tip_jitter: float
    base_blade: float
    blade_step: float
    blade_period: int
    stroke_color: str
    stroke_width: float


@dataclass(frozen=True)
class FenceSpec:
    posts: int
    x0: float
    x_stride: float
    post_half_w: float
    post_h: float
    corner_r: float
    fill_color: str
    stroke_color: str
    stroke_width: float


@dataclass(frozen=True)
class GroundOrbSpec:
    x: float
    radius: float
    fill_color: str
    stroke_color: str
    stroke_width: float


@dataclass(frozen=True)
class BirdsFlockSpec:
    bodies: tuple[tuple[float, float], ...]
    rx: float
    ry: float
    x_index_jitter: float
    fill_color: str


@dataclass(frozen=True)
class RainFieldSpec:
    seed: int
    waves: int
    drops_per_wave: int
    wave_spacing: float
    x_margin: float
    y0_lo: float
    y0_hi: float
    streak_min: float
    streak_rand: float
    skew_lo: float
    skew_hi: float
    start_jitter: float
    start_stride: float
    fall_past_min: float
    fall_past_rand: float
    stroke_color: str
    stroke_width: float


@dataclass(frozen=True)
class LandscapeAnimationSpec:
    cloud_drift_world: tuple[float, ...]
    rain_duration_base: float
    rain_duration_stride: float
    rain_duration_period: int


@dataclass(frozen=True)
class RainyLandscapeManifest:
    star_field: StarFieldSpec
    hill: HillTerrainSpec
    backdrop: GroundBackdropSpec
    sun: SunSpriteSpec
    cloud_sprite: CloudSpriteSpec
    clouds: tuple[CloudPlacement, ...]
    trees: tuple[PineTreeSpec, ...]
    rocks: tuple[RockPlacement, ...]
    grass: GrassStripSpec
    fence: FenceSpec
    orbs: tuple[GroundOrbSpec, ...]
    birds: BirdsFlockSpec
    rain: RainFieldSpec
    animation: LandscapeAnimationSpec


def default_rainy_landscape_manifest() -> RainyLandscapeManifest:
    """Defaults mirror ``examples/principles/26_world_viewport.py`` as of extraction."""
    return RainyLandscapeManifest(
        star_field=StarFieldSpec(
            count=28,
            columns=7,
            x_start_off=0.35,
            x_stride=10.0 / 6.5,
            y0=-0.4,
            y_row_stride=-0.42,
            y_mod_stride=-0.09,
            y_mod_period=3,
            star_rx=0.028,
            star_ry=0.028,
            fill_color="#E8EAED",
        ),
        hill=HillTerrainSpec(
            fill_color="#262928",
            ring_xy_norm_dy=(
                (-1.0, 0.85),
                (-1.0, -0.02),
                (-0.27, -0.38),
                (0.08, -0.52),
                (0.36, -0.35),
                (1.0, -0.05),
                (1.0, 0.85),
            ),
        ),
        backdrop=GroundBackdropSpec(strip_thickness=0.08, strip_fill="#2E3230"),
        sun=SunSpriteSpec(
            cx=3.55,
            cy=-2.0,
            rx=0.34,
            ry=0.34,
            fill_color="#C73E52",
            stroke_color="#6E2832",
            stroke_width=0.01,
        ),
        cloud_sprite=CloudSpriteSpec(
            fill_color="#D0D4DC",
            stroke_color="#90949C",
            stroke_width=0.004,
            puffs=(
                CloudPuff(-0.16, 0.02, 0.12, 0.07),
                CloudPuff(0.0, 0.0, 0.15, 0.09),
                CloudPuff(0.15, 0.02, 0.11, 0.07),
            ),
        ),
        clouds=(
            CloudPlacement(-3.15, -1.4),
            CloudPlacement(0.65, -1.2),
            CloudPlacement(2.35, -1.7),
            CloudPlacement(-0.85, -1.85),
        ),
        trees=(
            PineTreeSpec(-3.75, 1.08),
            PineTreeSpec(-1.35, 0.92),
            PineTreeSpec(2.05, 1.02),
            PineTreeSpec(3.85, 1.14),
            PineTreeSpec(-0.15, 0.78),
        ),
        rocks=(
            RockPlacement(-4.0, 0.11, 0.06, "#5C5C6A"),
            RockPlacement(4.35, 0.09, 0.05, "#4A4A58"),
            RockPlacement(-2.85, 0.07, 0.04, "#6A6A78"),
            RockPlacement(1.15, 0.08, 0.05, "#50505E"),
        ),
        grass=GrassStripSpec(
            blades=48,
            x0_world_off=0.12,
            x_stride=0.21,
            x_tip_jitter=0.035,
            base_blade=0.09,
            blade_step=0.018,
            blade_period=5,
            stroke_color="#4A6B78",
            stroke_width=0.007,
        ),
        fence=FenceSpec(
            posts=26,
            x0=-4.55,
            x_stride=0.36,
            post_half_w=0.018,
            post_h=0.3,
            corner_r=0.004,
            fill_color="#6B6358",
            stroke_color="#4A4540",
            stroke_width=0.003,
        ),
        orbs=(
            GroundOrbSpec(-2.45, 0.09, "#5DD2E8", "#3D9CAD", 0.012),
            GroundOrbSpec(2.58, 0.075, "#C84A5C", "#A51C30", 0.012),
            GroundOrbSpec(4.05, 0.055, "#454545", "#5DD2E8", 0.012),
        ),
        birds=BirdsFlockSpec(
            bodies=((-2.0, -0.9), (0.2, -1.1), (2.8, -0.8)),
            rx=0.06,
            ry=0.025,
            x_index_jitter=0.02,
            fill_color="#3A3A3A",
        ),
        rain=RainFieldSpec(
            seed=42,
            waves=2,
            drops_per_wave=38,
            wave_spacing=7.15,
            x_margin=0.25,
            y0_lo=-2.38,
            y0_hi=-0.52,
            streak_min=0.10,
            streak_rand=0.07,
            skew_lo=-0.014,
            skew_hi=0.014,
            start_jitter=0.06,
            start_stride=0.185,
            fall_past_min=0.65,
            fall_past_rand=0.35,
            stroke_color="#9BA8B8",
            stroke_width=0.0032,
        ),
        animation=LandscapeAnimationSpec(
            cloud_drift_world=(0.52, 0.38, 0.71, 0.45),
            rain_duration_base=0.55,
            rain_duration_stride=0.045,
            rain_duration_period=7,
        ),
    )


# ---------------------------------------------------------------------------
# Node factories
# ---------------------------------------------------------------------------


def _pine_tree(x: float, ground_y: float, *, scale: float = 1.0) -> Node:
    s = scale
    trunk_h = 0.22 * s
    trunk_w = 0.06 * s

    root = Node(x=x, y=ground_y - trunk_h)
    root.add(
        Rectangle(
            x=-trunk_w / 2.0,
            y=0.0,
            width=trunk_w,
            height=trunk_h,
            corner_radius=0.01 * s,
            fill_color="#5A4A40",
            stroke_color="#3A3228",
            stroke_width=0.004,
        )
    )
    root.add(
        Polygon(
            vertices=(
                (0.0, -0.38 * s),
                (-0.22 * s, trunk_h * 0.98),
                (0.22 * s, trunk_h * 0.98),
            ),
            fill_color="#2A3830",
            stroke_color="#1A241F",
            stroke_width=0.006,
        )
    )
    return root


def _cloud_group(cx: float, cy: float, sprite: CloudSpriteSpec) -> Node:
    group = Node(x=cx, y=cy)
    for puff in sprite.puffs:
        group.add(
            Ellipse(
                x=puff.ox,
                y=puff.oy,
                rx=puff.rx,
                ry=puff.ry,
                fill_color=sprite.fill_color,
                stroke_color=sprite.stroke_color,
                stroke_width=sprite.stroke_width,
            )
        )
    return group


def _orb_on_ground(
    ground_y: float,
    *,
    x: float,
    radius: float,
    fill: str,
    stroke: str,
    stroke_width: float,
) -> Node:
    node = Node(x=x, y=0.0)
    node.add(
        Ellipse(
            x=0.0,
            y=0.0,
            rx=radius,
            ry=radius,
            fill_color=fill,
            stroke_color=stroke,
            stroke_width=stroke_width,
        )
    )
    place_on_ground(node, resting_anchor_y(ground_y=ground_y, radius_y=radius))
    return node


# ---------------------------------------------------------------------------
# Materialization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LandscapeTrackHandles:
    """Transient references for wiring :meth:`Scene.add_animation` after build."""

    clouds: tuple[tuple[Node, float], ...]
    rain: tuple[tuple[Node, float, float, float], ...]


def materialize_rainy_landscape(
    shell: WorldShellNodes,
    spec: WorldSpec,
    manifest: RainyLandscapeManifest,
) -> LandscapeTrackHandles:
    gy = float(spec.ground_y)
    half = float(spec.world_width) / 2.0
    m = manifest

    # Stars ---------------------------------------------------------------
    sf = m.star_field
    stars = Node(x=0.0, y=0.0)
    for i in range(sf.count):
        sx = -half + sf.x_start_off + (i % sf.columns) * sf.x_stride
        sy = sf.y0 + (i // sf.columns) * sf.y_row_stride + (i % sf.y_mod_period) * sf.y_mod_stride
        stars.add(
            Ellipse(
                x=sx,
                y=sy,
                rx=sf.star_rx,
                ry=sf.star_ry,
                fill_color=sf.fill_color,
                stroke_color=None,
                stroke_width=0.0,
            )
        )
    shell.background.add(stars)

    # Hill -----------------------------------------------------------------
    verts = tuple((xn * half, gy + dy) for xn, dy in m.hill.ring_xy_norm_dy)
    shell.background.add(
        Polygon(
            vertices=verts,
            fill_color=m.hill.fill_color,
            stroke_color=None,
            stroke_width=0.0,
        )
    )

    shell.background.add(
        ground_strip(
            spec,
            thickness=m.backdrop.strip_thickness,
            fill_color=m.backdrop.strip_fill,
        )
    )

    # Sun ------------------------------------------------------------------
    sun = Node(x=m.sun.cx, y=m.sun.cy)
    sun.add(
        Ellipse(
            x=0.0,
            y=0.0,
            rx=m.sun.rx,
            ry=m.sun.ry,
            fill_color=m.sun.fill_color,
            stroke_color=m.sun.stroke_color,
            stroke_width=m.sun.stroke_width,
        )
    )
    shell.midground.add(sun)

    # Clouds + tracking anchors -------------------------------------------
    drift_targets: list[tuple[Node, float]] = []
    for placement in m.clouds:
        node = _cloud_group(placement.cx, placement.cy, m.cloud_sprite)
        shell.midground.add(node)
        drift_targets.append((node, float(placement.cx)))

    # Vegetation / props ---------------------------------------------------
    for tree in m.trees:
        shell.midground.add(_pine_tree(tree.x, gy, scale=tree.scale))

    for rock in m.rocks:
        rock_node = Node(x=rock.cx, y=0.0)
        rock_node.add(
            Ellipse(
                x=0.0,
                y=0.0,
                rx=rock.rx,
                ry=rock.ry,
                fill_color=rock.fill_color,
                stroke_color="#3A3A44",
                stroke_width=0.003,
            )
        )
        place_on_ground(
            rock_node,
            resting_anchor_y(ground_y=gy, radius_y=rock.ry),
        )
        shell.midground.add(rock_node)

    # Grass ----------------------------------------------------------------
    g = m.grass
    grass_root = Node(x=0.0, y=0.0)
    for i in range(g.blades):
        gx = -half + g.x0_world_off + i * g.x_stride
        blade_len = g.base_blade + (i % g.blade_period) * g.blade_step
        grass_root.add(
            Line(
                x0=gx,
                y0=gy,
                x1=gx + g.x_tip_jitter,
                y1=gy - blade_len,
                stroke_color=g.stroke_color,
                stroke_width=g.stroke_width,
            )
        )
    shell.midground.add(grass_root)

    # Fence ----------------------------------------------------------------
    f = m.fence
    fence_root = Node(x=0.0, y=0.0)
    for i in range(f.posts):
        fx = f.x0 + i * f.x_stride
        fence_root.add(
            Rectangle(
                x=fx - f.post_half_w,
                y=gy,
                width=2.0 * f.post_half_w,
                height=f.post_h,
                corner_radius=f.corner_r,
                fill_color=f.fill_color,
                stroke_color=f.stroke_color,
                stroke_width=f.stroke_width,
            )
        )
    shell.midground.add(fence_root)

    # Orbs -----------------------------------------------------------------
    for orb in m.orbs:
        shell.midground.add(
            _orb_on_ground(
                gy,
                x=orb.x,
                radius=orb.radius,
                fill=orb.fill_color,
                stroke=orb.stroke_color,
                stroke_width=orb.stroke_width,
            )
        )

    # Birds ----------------------------------------------------------------
    b = m.birds
    birds_root = Node(x=0.0, y=0.0)
    for i, (bx, by) in enumerate(b.bodies):
        birds_root.add(
            Ellipse(
                x=bx + b.x_index_jitter * i,
                y=by,
                rx=b.rx,
                ry=b.ry,
                fill_color=b.fill_color,
                stroke_color=None,
                stroke_width=0.0,
            )
        )
    shell.foreground.add(birds_root)

    # Rain -----------------------------------------------------------------
    r = m.rain
    rng = random.Random(r.seed)
    drops: list[tuple[Node, float, float, float]] = []
    for wave in range(r.waves):
        t0 = wave * r.wave_spacing
        for j in range(r.drops_per_wave):
            x = rng.uniform(-half + r.x_margin, half - r.x_margin)
            y0 = rng.uniform(r.y0_lo, r.y0_hi)
            streak = r.streak_min + rng.random() * r.streak_rand
            skew = rng.uniform(r.skew_lo, r.skew_hi)
            start_t = t0 + j * r.start_stride + rng.random() * r.start_jitter
            drop = Node(x=x, y=y0)
            drop.add(
                Line(
                    x0=0.0,
                    y0=0.0,
                    x1=skew,
                    y1=streak,
                    stroke_color=r.stroke_color,
                    stroke_width=r.stroke_width,
                )
            )
            fall_past = r.fall_past_min + rng.random() * r.fall_past_rand
            y1 = max(y0 + 0.35, gy + fall_past)
            shell.foreground.add(drop)
            drops.append((drop, y0, y1, start_t))

    return LandscapeTrackHandles(clouds=tuple(drift_targets), rain=tuple(drops))


def apply_rainy_landscape_animations(
    scene: Scene,
    *,
    duration: float,
    manifest: RainyLandscapeManifest,
    handles: LandscapeTrackHandles,
) -> None:
    """Push MoveX / MoveY clips for clouds and rain (timeline layer)."""
    d = float(duration)
    anim = manifest.animation
    drift = anim.cloud_drift_world
    for i, (node, cx) in enumerate(handles.clouds):
        delta = drift[i % len(drift)]
        scene.add_animation(0.0, d, node, MoveX(cx, cx + delta))

    for idx, (drop, y0, y1, start_t) in enumerate(handles.rain):
        mod = idx % anim.rain_duration_period
        dur = anim.rain_duration_base + mod * anim.rain_duration_stride
        t0 = max(0.0, min(start_t, d - 0.08))
        t1 = min(t0 + dur, d)
        if t1 - t0 < 0.1:
            continue
        scene.add_animation(t0, t1, drop, MoveY(y0, y1))
