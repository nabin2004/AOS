"""Scene graph, timeline, and core composition types."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from motiongram.canvas import Canvas
from motiongram.subtitles import SubtitleTrack


@runtime_checkable
class Drawable(Protocol):
    """Anything that can be drawn onto a canvas; positions accumulate from parents."""

    def draw(self, canvas: Canvas, ox: float = 0.0, oy: float = 0.0) -> None:
        """Render this node to the given canvas at origin (ox, oy) plus local offset."""
        ...


@dataclass(slots=True)
class Camera:
    """Virtual camera — viewport pan/zoom/rotate applied before rendering.

    ``(x, y)`` is the **world-space point** pinned to the viewport center (after
    zoom and rotation). Defaults are non-finite so the renderer uses the scene
    center ``(width/2, height/2)``, matching layouts that put ``(0, 0)`` at the
    top-left of the frame.
    """

    x: float = float("nan")
    y: float = float("nan")
    zoom: float = 1.0
    rotation: float = 0.0


@dataclass(slots=True)
class Node:
    """Base graph node; subclasses add geometry, style, and children."""

    x: float = 0.0
    y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    opacity: float = 1.0
    blur_sigma: float = 0.0
    world_z: float = 0.0
    children: list[Node] = field(default_factory=list)

    def add(self, node: Node) -> None:
        self.children.append(node)

    def draw(self, canvas: Canvas, ox: float = 0.0, oy: float = 0.0) -> None:
        """Apply transforms when backend supports ``push_node_transform``."""
        px = ox + self.x
        py = oy + self.y
        push = getattr(canvas, "push_node_transform", None)
        pop = getattr(canvas, "pop_transform", None)
        if push is not None:
            push(px, py, self.rotation, self.scale_x, self.scale_y, self.opacity, self.blur_sigma)
            self.draw_world(canvas, 0.0, 0.0)
            for child in self.children:
                child.draw(canvas, 0.0, 0.0)
            if pop is not None:
                pop()
        else:
            self.draw_world(canvas, px, py)
            for child in self.children:
                child.draw(canvas, px, py)

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        """Draw this node's own geometry at anchor ``(px, py)`` (scene coords).

        Subclasses override this instead of ``draw``. Default does nothing.
        """
        _ = canvas, px, py

    def update(self, t: float, dt: float) -> None:
        """Advance simulation time; subclasses override and call Node.update for children."""
        for child in self.children:
            child.update(t, dt)


@dataclass(slots=True)
class Circle(Node):
    """Circle outline (raster) plus optional vector style fields (used by Skia backends)."""

    r: float = 1.0
    ch: str = "#"
    progress: float = 1.0  # 1 = full outline; animate via timeline (e.g. CircleOutline).

    fill_color: str = "#FFFFFF"
    stroke_color: str | None = None
    stroke_width: float = 0.0

    @property
    def radius(self) -> float:
        """Alias for ``r`` (compat with older ``shapes.Circle(radius=…)`` examples)."""
        return self.r

    @radius.setter
    def radius(self, value: float) -> None:
        self.r = float(value)

    def draw_world(self, canvas: Canvas, px: float, py: float) -> None:
        n = max(8, int(self.r * 8))
        p = max(0.0, min(1.0, self.progress))
        k = int(n * p)
        for i in range(k):
            ang = 2 * math.pi * i / n
            ix = int(round(px + self.r * math.cos(ang)))
            iy = int(round(py + self.r * math.sin(ang)))
            canvas.set_pixel(ix, iy, self.ch)


@dataclass(slots=True)
class Timeline:
    """Ordered animation tuples: (start, end, target, animator)."""

    entries: tuple[tuple[float, float, Node, Any], ...] = field(default_factory=tuple)

    def add(
        self,
        start: float,
        end: float,
        target: Node,
        animator: Any,
    ) -> Timeline:
        """Return a new timeline with one entry appended (immutable-style API)."""
        return Timeline(entries=(*self.entries, (start, end, target, animator)))

    def without_entry(self, index: int) -> Timeline:
        """Return a new timeline with the entry at ``index`` removed (other entries keep order)."""
        n = len(self.entries)
        if not (0 <= index < n):
            raise IndexError(f"timeline entry index out of range: {index} (len={n})")
        return Timeline(
            entries=tuple(self.entries[i] for i in range(n) if i != index),
        )


@dataclass(slots=True)
class Scene:
    """Root container: resolution, timing, graph, timeline, and optional camera."""

    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    duration: float = 5.0
    root: Node = field(default_factory=Node)
    timeline: Timeline = field(default_factory=Timeline)
    camera: Camera = field(default_factory=Camera)
    subtitle_track: SubtitleTrack | None = None

    def narrate(self, voice_over: Any) -> None:
        """Register narration for mixing into the output audio (stub)."""
        _ = voice_over

    def add_node(self, node: Node) -> None:
        """Add a node to the scene graph."""
        self.root.add(node)

    def add_animation(self, start: float, end: float, target: Node, animator: Any) -> None:
        """Add an animation to the timeline."""
        self.timeline = self.timeline.add(float(start), float(end), target, animator)

    def remove_animation_at(self, index: int) -> None:
        """Remove one timeline entry by index (see :meth:`Timeline.without_entry`)."""
        self.timeline = self.timeline.without_entry(index)
