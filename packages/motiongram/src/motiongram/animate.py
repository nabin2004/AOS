"""Animation helpers, animator protocol, and timeline evaluation."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from motiongram.core import Circle, Node, Scene
from motiongram.easing import cubic_bezier, ease_out_back, ease_out_elastic

# (global_t, start, end, target, animator, u_eased) — invoked after ``apply`` succeeds.
TimelineOnApply = Callable[[float, float, float, Node, Any, float], None]


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation from ``a`` to ``b`` with ``t`` in [0, 1]."""
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    """Hermite ease in-out; clamps ``t`` to [0, 1]."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def apply_timeline(
    scene: Scene,
    t: float,
    *,
    ease: Callable[[float], float] | None = smoothstep,
    on_apply: TimelineOnApply | None = None,
) -> None:
    """Apply all timeline entries at global scene time ``t``.

    Maps global time to segment-local ``u``, then optionally applies ``ease``.

    If ``on_apply`` is set, it is called after each successful ``anim.apply`` with
    ``(t, start, end, target, anim, u_eased)`` for debugging or tooling.
    """
    for start, end, target, anim in scene.timeline.entries:
        if end <= start:
            continue
        if t <= start:
            u = 0.0
        elif t >= end:
            u = 1.0
        else:
            u = (t - start) / (end - start)
        u_eased = ease(u) if ease is not None else u
        apply_fn = getattr(anim, "apply", None)
        if apply_fn is not None:
            apply_fn(target, u_eased)
            if on_apply is not None:
                on_apply(t, start, end, target, anim, u_eased)


@runtime_checkable
class Animator(Protocol):
    """Interpolates a node between t=0 and t=1 within a timeline segment."""

    def apply(self, node: Node, t: float) -> None:
        """Apply eased progress ``t`` in [0, 1] to ``node``."""
        ...


@dataclass(slots=True)
class MoveX:
    """Set ``node.x`` between ``x0`` (t=0) and ``x1`` (t=1)."""

    x0: float
    x1: float

    def apply(self, node: Node, t: float) -> None:
        node.x = lerp(self.x0, self.x1, t)


@dataclass(slots=True)
class MoveY:
    """Set ``node.y`` between ``y0`` (t=0) and ``y1`` (t=1)."""

    y0: float
    y1: float

    def apply(self, node: Node, t: float) -> None:
        node.y = lerp(self.y0, self.y1, t)


@dataclass(slots=True)
class CircleOutline:
    """Set ``Circle.progress`` in [0, 1] from segment-local ``t``."""

    def apply(self, node: Node, t: float) -> None:
        if not isinstance(node, Circle):
            raise TypeError("CircleOutline only applies to Circle nodes")
        node.progress = max(0.0, min(1.0, t))


class Parallel:
    """Run several animators on the same node with the same segment-local ``t``."""

    __slots__ = ("animators",)

    def __init__(self, *animators: Any) -> None:
        self.animators = animators

    def apply(self, node: Node, t: float) -> None:
        for anim in self.animators:
            apply_fn = getattr(anim, "apply", None)
            if apply_fn is not None:
                apply_fn(node, t)


class Sequence:
    """Partition ``t ∈ [0, 1]`` into equal sub-segments and run exactly one child at a time.

    Only the active sub-animator runs each frame; other properties keep their previous values.
    Align segment boundaries so ``local_t=1`` of segment ``k`` matches
    ``local_t=0`` of ``k+1`` where needed.
    """

    __slots__ = ("animators",)

    def __init__(self, *animators: Any) -> None:
        self.animators = animators

    def apply(self, node: Node, t: float) -> None:
        n = len(self.animators)
        if n == 0:
            return
        t = max(0.0, min(1.0, t))
        segment = 1.0 / n
        i = min(int(t / segment), n - 1)
        local_t = (t - i * segment) / segment if segment > 0 else 0.0
        apply_fn = getattr(self.animators[i], "apply", None)
        if apply_fn is not None:
            apply_fn(node, local_t)


@dataclass(slots=True)
class Delay:
    """Run ``animator`` only when ``start <= t <= end`` (``t`` is parent's segment-local time).

    Outside that window this is a no-op (inner ``apply`` is not called). For a pinned start pose,
    set initial node state or use another animator.
    """

    animator: Any
    start: float
    end: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.start < self.end <= 1.0):
            raise ValueError("Delay requires 0 <= start < end <= 1")

    def apply(self, node: Node, t: float) -> None:
        if t < self.start or t > self.end:
            return
        span = self.end - self.start
        local_t = (t - self.start) / span
        apply_fn = getattr(self.animator, "apply", None)
        if apply_fn is not None:
            apply_fn(node, local_t)


@dataclass(slots=True)
class ScaleX:
    """Scale ``node.scale_x`` between ``sx0`` and ``sx1``."""

    sx0: float = 1.0
    sx1: float = 1.0

    def apply(self, node: Node, t: float) -> None:
        node.scale_x = lerp(self.sx0, self.sx1, t)


@dataclass(slots=True)
class ScaleY:
    """Scale ``node.scale_y`` between ``sy0`` and ``sy1``."""

    sy0: float = 1.0
    sy1: float = 1.0

    def apply(self, node: Node, t: float) -> None:
        node.scale_y = lerp(self.sy0, self.sy1, t)


@dataclass(slots=True)
class Rotate:
    """Interpolate ``node.rotation`` (radians)."""

    angle0: float = 0.0
    angle1: float = 0.0

    def apply(self, node: Node, t: float) -> None:
        node.rotation = lerp(self.angle0, self.angle1, t)

@dataclass(slots=True)
class SquashStretch:
    """Volume-preserving oscillation along ``axis`` (``sx * sy ≈ 1``)."""

    amount: float = 0.35
    axis: str = "y"

    def apply(self, node: Node, t: float) -> None:
        phase = math.sin(math.pi * t)
        k = 1.0 + self.amount * phase
        axis = self.axis.lower()
        if axis == "y":
            node.scale_y = k
            node.scale_x = 1.0 / max(k, 1e-6)
        elif axis == "x":
            node.scale_x = k
            node.scale_y = 1.0 / max(k, 1e-6)
        else:
            node.scale_x = math.sqrt(1.0 / max(k, 1e-6))
            node.scale_y = k


@dataclass(slots=True)
class FadeIn:
    """Animate ``node.opacity`` from ``start`` to ``end``."""

    start: float = 0.0
    end: float = 1.0

    def apply(self, node: Node, t: float) -> None:
        node.opacity = lerp(self.start, self.end, t)


@dataclass(slots=True)
class FadeOut:
    """Animate ``node.opacity`` downward."""

    start: float = 1.0
    end: float = 0.0

    def apply(self, node: Node, t: float) -> None:
        node.opacity = lerp(self.start, self.end, t)


@dataclass(slots=True)
class Blur:
    """Animate ``node.blur_sigma`` between endpoints."""

    sigma0: float = 0.0
    sigma1: float = 8.0

    def apply(self, node: Node, t: float) -> None:
        node.blur_sigma = lerp(self.sigma0, self.sigma1, t)


def _quad_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    u: float,
) -> tuple[float, float]:
    """Quadratic Bézier interpolation."""
    omu = 1.0 - u
    x = omu * omu * p0[0] + 2 * omu * u * p1[0] + u * u * p2[0]
    y = omu * omu * p0[1] + 2 * omu * u * p1[1] + u * u * p2[1]
    return x, y


@dataclass(slots=True)
class MoveArc:
    """Arc motion using a quadratic midpoint lifted by ``arc_height``."""

    x0: float = 0.0
    y0: float = 0.0
    x1: float = 100.0
    y1: float = 0.0
    arc_height: float = 40.0

    def apply(self, node: Node, t: float) -> None:
        mx = (self.x0 + self.x1) / 2.0
        my = (self.y0 + self.y1) / 2.0
        dx = self.x1 - self.x0
        dy = self.y1 - self.y0
        length = math.hypot(dx, dy) or 1.0
        nx = -dy / length
        ny = dx / length
        cx = mx + nx * self.arc_height
        cy = my + ny * self.arc_height
        px, py = _quad_point((self.x0, self.y0), (cx, cy), (self.x1, self.y1), t)
        node.x = px
        node.y = py


def _polyline_length(points: tuple[tuple[float, float], ...]) -> tuple[list[float], float]:
    if len(points) < 2:
        return [0.0], 0.0
    seg_lens: list[float] = []
    total = 0.0
    for i in range(len(points) - 1):
        ax, ay = points[i]
        bx, by = points[i + 1]
        ln = math.hypot(bx - ax, by - ay)
        seg_lens.append(ln)
        total += ln
    cum = [0.0]
    run = 0.0
    for ln in seg_lens:
        run += ln
        cum.append(run)
    return cum, total


@dataclass(slots=True)
class MoveAlongPath:
    """Move node anchor along a polyline at constant speed."""

    points: tuple[tuple[float, float], ...] = ()

    def apply(self, node: Node, t: float) -> None:
        pts = self.points
        if len(pts) == 0:
            return
        if len(pts) == 1:
            node.x, node.y = pts[0]
            return
        cum, total = _polyline_length(pts)
        if total <= 1e-9:
            node.x, node.y = pts[-1]
            return
        dist = max(0.0, min(1.0, t)) * total
        # locate segment
        idx = 0
        while idx < len(cum) - 1 and cum[idx + 1] < dist:
            idx += 1
        seg_start = cum[idx]
        seg_end = cum[idx + 1]
        span = max(seg_end - seg_start, 1e-9)
        u = (dist - seg_start) / span
        ax, ay = pts[idx]
        bx, by = pts[idx + 1]
        node.x = lerp(ax, bx, u)
        node.y = lerp(ay, by, u)


@dataclass(slots=True)
class Anticipate:
    """Remap progress with a subtle backward dip via a Bézier curve."""

    animator: Any
    p1x: float = 0.38
    p1y: float = -0.18
    p2x: float = 0.62
    p2y: float = 1.02

    def apply(self, node: Node, t: float) -> None:
        u = cubic_bezier(t, self.p1x, self.p1y, self.p2x, self.p2y)
        apply_fn = getattr(self.animator, "apply", None)
        if apply_fn is not None:
            apply_fn(node, u)


@dataclass(slots=True)
class FollowThrough:
    """Elastic settling curve layered on top of another animator."""

    animator: Any

    def apply(self, node: Node, t: float) -> None:
        u = ease_out_elastic(t)
        apply_fn = getattr(self.animator, "apply", None)
        if apply_fn is not None:
            apply_fn(node, u)


@dataclass(slots=True)
class TimeScale:
    """Rewrap inner animator with extra easing on segment-local time."""

    animator: Any
    ease: Callable[[float], float] | None = None

    def apply(self, node: Node, t: float) -> None:
        u = self.ease(t) if self.ease is not None else t
        apply_fn = getattr(self.animator, "apply", None)
        if apply_fn is not None:
            apply_fn(node, u)


class WithSecondary:
    """Run two animators at the same normalized time (staging helper)."""

    __slots__ = ("primary", "secondary")

    def __init__(self, primary: Any, secondary: Any) -> None:
        self.primary = primary
        self.secondary = secondary

    def apply(self, node: Node, t: float) -> None:
        for anim in (self.primary, self.secondary):
            apply_fn = getattr(anim, "apply", None)
            if apply_fn is not None:
                apply_fn(node, t)


@dataclass(slots=True)
class Stagger:
    """Partition ``t`` across many targets (timeline ``target`` is ignored)."""

    targets: tuple[Node, ...]
    animator: Any

    def apply(self, node: Node, t: float) -> None:
        _ = node
        vals = self.targets
        n = len(vals)
        if n == 0:
            return
        span = 1.0 / n
        i = min(int(t / span), n - 1)
        local_t = (t - i * span) / span if span > 0 else 0.0
        tgt = vals[i]
        apply_fn = getattr(self.animator, "apply", None)
        if apply_fn is not None:
            apply_fn(tgt, local_t)


@dataclass(slots=True)
class CameraPan:
    """Pan ``scene.camera`` between two focal points."""

    scene: Scene
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0

    def apply(self, node: Node, t: float) -> None:
        _ = node
        self.scene.camera.x = lerp(self.x0, self.x1, t)
        self.scene.camera.y = lerp(self.y0, self.y1, t)


@dataclass(slots=True)
class CameraZoom:
    """Animate ``scene.camera.zoom``."""

    scene: Scene
    zoom0: float = 1.0
    zoom1: float = 1.4

    def apply(self, node: Node, t: float) -> None:
        _ = node
        self.scene.camera.zoom = lerp(self.zoom0, self.zoom1, t)


@dataclass(slots=True)
class ExaggerateEase:
    """Push motion readability using ``ease_out_back``."""

    animator: Any

    def apply(self, node: Node, t: float) -> None:
        u = ease_out_back(t)
        apply_fn = getattr(self.animator, "apply", None)
        if apply_fn is not None:
            apply_fn(node, u)


@dataclass(slots=True)
class Animation:
    """Concrete animation wrapper (fade, move, transform — TBD)."""

    name: str = "noop"

    def as_animator(self) -> Any:
        """Return an ``Animator`` implementation (stub)."""
        return _NoopAnimator()


class _NoopAnimator:
    """Placeholder animator."""

    def apply(self, node: Node, t: float) -> None:
        _ = node, t
