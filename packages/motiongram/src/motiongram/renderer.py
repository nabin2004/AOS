from __future__ import annotations

import hashlib
import sys
import time
from typing import Any

from motiongram.animate import apply_timeline
from motiongram.core import Node, Scene
from motiongram.engine import step_frame


def ascii_frame_text(frame: list[list[str]]) -> str:
    """Join frame rows into one string (row-major, newline between rows)."""

    return "\n".join("".join(row) for row in frame)


def ascii_frame_sha256(frame: list[list[str]]) -> str:
    """Deterministic digest of an ASCII frame (for snapshot tests)."""

    return hashlib.sha256(ascii_frame_text(frame).encode()).hexdigest()


class AsciiFrameCanvas:
    """Binds a renderer and frame so nodes can call set_pixel(x, y, ch)."""

    __slots__ = ("_renderer", "_frame")

    def __init__(self, renderer: Renderer, frame: list[list[str]]) -> None:
        self._renderer = renderer
        self._frame = frame

    def set_pixel(self, x: int, y: int, ch: str = "#") -> None:
        """Satisfies :class:`~motiongram.canvas.Canvas` for raster ASCII."""
        self._renderer.set_pixel(self._frame, x, y, ch)


class Renderer:
    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        fps: float = 30.0,
        bg: str = "black",
        *,
        debug: bool = False,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.bg = bg
        self.debug = debug
        self.scene = Scene(width=width, height=height, fps=fps)

    @staticmethod
    def _log_timeline_apply(
        t: float,
        start: float,
        end: float,
        target: Node,
        anim: Any,
        u_eased: float,
    ) -> None:
        parts = [
            f"[t={t:.3f}]",
            f"{type(anim).__name__}",
            f"segment=[{start:.3f},{end:.3f}]",
            f"target_id={id(target)}",
            f"u={u_eased:.3f}",
        ]
        if hasattr(target, "x"):
            parts.append(f"x={target.x!r}")
        if hasattr(target, "progress"):
            parts.append(f"progress={target.progress!r}")
        print(" ".join(parts), file=sys.stderr)

    def blank_frame(self) -> list[list[str]]:
        """Create a blank frame with the background character."""
        return [[self.bg for _ in range(self.width)] for _ in range(self.height)]

    def set_pixel(self, frame: list[list[str]], x: int, y: int, ch: str = "#") -> None:
        """Write one character to the frame; out-of-bounds writes are clipped."""
        if not ch:
            return
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        frame[y][x] = ch[0]

    def line(
        self,
        frame: list[list[str]],
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        ch: str = "#",
    ) -> None:
        """Draw a line from (x1, y1) to (x2, y2) using Bresenham's line algorithm."""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)


        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1

        err = dx - dy

        while True:
            self.set_pixel(frame, x1, y1, ch)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def circle(self, frame: list[list[str]], cx: int, cy: int, r: int, ch: str = "#") -> None:
        """Draw a circle centered at (cx, cy) with radius r using the midpoint circle algorithm."""
        x = 0
        y = r
        d = 1 - r

        while x <= y:
            self.set_pixel(frame, cx + x, cy + y, ch)
            self.set_pixel(frame, cx - x, cy + y, ch)
            self.set_pixel(frame, cx + x, cy - y, ch)
            self.set_pixel(frame, cx - x, cy - y, ch)
            self.set_pixel(frame, cx + y, cy + x, ch)
            self.set_pixel(frame, cx - y, cy + x, ch)
            self.set_pixel(frame, cx + y, cy - x, ch)
            self.set_pixel(frame, cx - y, cy - x, ch)

            if d < 0:
                d += 2 * x + 3
            else:
                d += 2 * (x - y) + 5
                y -= 1
            x += 1

    def render(self, scene: Scene, *, show_output: bool = True) -> None:
        """Render one still at global time 0 (applies timeline at ``t=0``)."""
        on_apply = self._log_timeline_apply if self.debug else None
        apply_timeline(scene, 0.0, on_apply=on_apply)
        frame = self.blank_frame()
        canvas = AsciiFrameCanvas(self, frame)
        scene.root.draw(canvas, 0.0, 0.0)
        if show_output:
            self.show(frame, ansi_clear=False)

    def play(
        self,
        scene: Scene,
        *,
        realtime: bool = True,
        debug: bool | None = None,
        show_output: bool = True,
    ) -> None:
        """Playback: ``apply_timeline`` + draw each frame until ``scene.duration``.

        ``realtime=True``: terminal cursor + sleep pacing. ``realtime=False``: no wall clock.
        ``show_output=False``: skip printing frames. ``debug``: log applies to stderr.
        """
        if scene.fps <= 0:
            raise ValueError("scene.fps must be positive")
        dbg = self.debug if debug is None else debug
        on_apply = self._log_timeline_apply if dbg else None
        dt = 1.0 / scene.fps
        n_frames = max(1, round(scene.duration * scene.fps))
        if realtime:
            print("\033[?25l", end="", flush=True)
        try:
            for i in range(n_frames):
                start = time.perf_counter()
                t_frame = min(scene.duration, (i + 1) * dt)
                step_frame(scene, t_frame, dt, on_apply=on_apply)
                frame = self.blank_frame()
                canvas = AsciiFrameCanvas(self, frame)
                scene.root.draw(canvas, 0.0, 0.0)
                if show_output:
                    self.show(frame, ansi_clear=realtime)
                if realtime:
                    elapsed = time.perf_counter() - start
                    time.sleep(max(0.0, dt - elapsed))
        finally:
            if realtime:
                print("\033[?25h", end="", flush=True)

    def show(self, frame: list[list[str]], *, ansi_clear: bool = False) -> None:
        """Print the frame to the terminal."""
        if ansi_clear:
            print("\033[2J\033[H", end="", flush=True)
        for row in frame:
            print("".join(row))
