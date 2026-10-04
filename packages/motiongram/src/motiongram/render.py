"""Skia-backed frame rendering (scene graph + timeline, then rasterize)."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import numpy.typing as npt

from motiongram.animate import smoothstep
from motiongram.core import Scene
from motiongram.engine import step_frame
from motiongram.subtitles import active_subtitles, subtitle_typst_layout
from motiongram.typst_cache import cached_typst_subtitle_svg_path


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _hex_to_rgba(s: str) -> tuple[int, int, int, int]:
    """Parse ``#RGB``, ``#RRGGBB``, or ``#RRGGBBAA`` into RGBA bytes."""
    h = s.strip().lstrip("#")
    if len(h) == 3:
        r = int((h[0] + h[0]), 16)
        g = int((h[1] + h[1]), 16)
        b = int((h[2] + h[2]), 16)
        a = 255
    elif len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = 255
    elif len(h) == 8:
        r, g, b, a = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)
    else:
        r, g, b, a = 255, 255, 255, 255
    return r, g, b, a


def _skia_color_from_hex(s: str, alpha_mult: float = 1.0) -> int:
    import skia as _skia

    r, g, b, a = _hex_to_rgba(s)
    aa = int(round(_clamp01(alpha_mult * (a / 255.0)) * 255.0))
    return cast(int, _skia.Color(r, g, b, aa))


class SkiaCanvas:
    """Skia drawing surface with optional node transform stack and vector helpers."""

    __slots__ = ("_canvas", "_paint", "_alpha_stack", "_blur_stack")

    def __init__(self, surface: Any) -> None:
        import skia

        self._canvas = surface.getCanvas()
        self._paint = skia.Paint()
        self._paint.setAntiAlias(True)
        self._alpha_stack: list[float] = [1.0]
        self._blur_stack: list[float] = [0.0]

    def _effective_alpha(self) -> float:
        return max(0.0, min(1.0, self._alpha_stack[-1]))

    def _effective_blur(self) -> float:
        return max(0.0, self._blur_stack[-1])

    def _apply_paint_filters(self, paint: Any) -> None:
        import skia

        blur = self._effective_blur()
        if blur > 1e-6:
            filt = skia.ImageFilters.Blur(blur, blur, skia.TileMode.kClamp)
            paint.setImageFilter(filt)

    def push_node_transform(
        self,
        px: float,
        py: float,
        rotation_rad: float,
        sx: float,
        sy: float,
        alpha: float,
        blur_sigma: float,
    ) -> None:
        """Enter node-local coordinates with pivot ``(px, py)``."""
        self._canvas.save()
        self._alpha_stack.append(self._alpha_stack[-1] * _clamp01(alpha))
        self._blur_stack.append(max(self._blur_stack[-1], max(0.0, blur_sigma)))
        self._canvas.translate(px, py)
        self._canvas.rotate(math.degrees(rotation_rad))
        if sx != 0.0 and sy != 0.0:
            self._canvas.scale(float(sx), float(sy))

    def pop_transform(self) -> None:
        self._canvas.restore()
        if len(self._alpha_stack) > 1:
            self._alpha_stack.pop()
        if len(self._blur_stack) > 1:
            self._blur_stack.pop()

    def push_affine_2x3(
        self,
        ax: float,
        bx: float,
        cx: float,
        ay: float,
        by: float,
        cy: float,
    ) -> None:
        """Concat a 2×3 affine: ``x' = ax*x + bx*y + cx``, ``y' = ay*x + by*y + cy``."""

        import skia

        self._canvas.save()
        self._alpha_stack.append(self._alpha_stack[-1])
        self._blur_stack.append(self._blur_stack[-1])
        m = skia.Matrix()
        m.setAll(float(ax), float(bx), float(cx), float(ay), float(by), float(cy), 0.0, 0.0, 1.0)
        self._canvas.concat(m)

    def pop_affine_2x3(self) -> None:
        self.pop_transform()

    def set_pixel(self, x: int, y: int, ch: str = "#") -> None:
        import skia

        self._paint.reset()
        self._paint.setAntiAlias(True)
        self._paint.setStyle(skia.Paint.kFill_Style)
        r, g, b, _a = _hex_to_rgba("#FFFFFF")
        aa = int(round(self._effective_alpha() * 255.0))
        self._paint.setColor(skia.Color(r, g, b, aa))
        self._apply_paint_filters(self._paint)
        _ = ch
        rect = skia.Rect(float(x), float(y), float(x + 1), float(y + 1))
        self._canvas.drawRect(rect, self._paint)

    def stroke_line(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        color: str,
        width: float,
        *,
        dash_pattern: tuple[float, ...] | None = None,
    ) -> None:
        import skia

        self._paint.reset()
        self._paint.setAntiAlias(True)
        self._paint.setStrokeWidth(max(width, 0.001))
        self._paint.setStyle(skia.Paint.kStroke_Style)
        self._paint.setColor(_skia_color_from_hex(color, self._effective_alpha()))
        if dash_pattern:
            effect = skia.DashPathEffect.Make(list(dash_pattern), 0.0)
            self._paint.setPathEffect(effect)
        self._apply_paint_filters(self._paint)
        p = skia.Path()
        p.moveTo(x0, y0)
        p.lineTo(x1, y1)
        self._canvas.drawPath(p, self._paint)

    def stroke_bezier(
        self,
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
        color: str,
        width: float,
        *,
        dash_pattern: tuple[float, ...] | None = None,
    ) -> None:
        import skia

        self._paint.reset()
        self._paint.setAntiAlias(True)
        self._paint.setStrokeWidth(max(width, 0.001))
        self._paint.setStyle(skia.Paint.kStroke_Style)
        self._paint.setColor(_skia_color_from_hex(color, self._effective_alpha()))
        if dash_pattern:
            self._paint.setPathEffect(skia.DashPathEffect.Make(list(dash_pattern), 0.0))
        self._apply_paint_filters(self._paint)
        path = skia.Path()
        path.moveTo(p0[0], p0[1])
        path.cubicTo(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1])
        self._canvas.drawPath(path, self._paint)

    def stroke_arc(
        self,
        cx: float,
        cy: float,
        radius: float,
        start_angle: float,
        sweep_angle: float,
        color: str,
        width: float,
        *,
        dash_pattern: tuple[float, ...] | None = None,
    ) -> None:
        """Stroke circular arc from ``start_angle`` over ``sweep_angle`` (radians)."""
        import skia

        rect = skia.Rect.MakeXYWH(cx - radius, cy - radius, 2 * radius, 2 * radius)
        self._paint.reset()
        self._paint.setAntiAlias(True)
        self._paint.setStrokeWidth(max(width, 0.001))
        self._paint.setStyle(skia.Paint.kStroke_Style)
        self._paint.setColor(_skia_color_from_hex(color, self._effective_alpha()))
        if dash_pattern:
            self._paint.setPathEffect(skia.DashPathEffect.Make(list(dash_pattern), 0.0))
        self._apply_paint_filters(self._paint)
        path = skia.Path()
        path.addArc(rect, math.degrees(start_angle), math.degrees(sweep_angle))
        self._canvas.drawPath(path, self._paint)

    def fill_sector(
        self,
        cx: float,
        cy: float,
        radius: float,
        start_angle: float,
        sweep_angle: float,
        *,
        fill_color: str,
        stroke_color: str | None = None,
        stroke_width: float = 0.0,
    ) -> None:
        """Fill a circular sector (pie wedge) centered at ``(cx, cy)``.

        Angles follow the same convention as :meth:`stroke_arc`: radians,
        ``sweep_angle`` is added to ``start_angle`` (Skia draws the arc in
        degrees internally).
        """
        import skia

        r = max(radius, 0.0)
        if r <= 0.0:
            return

        tau = 2.0 * math.pi
        if abs(sweep_angle) >= tau - 1e-6:
            self.fill_ellipse(
                cx,
                cy,
                r,
                r,
                fill_color=fill_color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
            )
            return

        rect = skia.Rect.MakeXYWH(cx - r, cy - r, 2 * r, 2 * r)
        path = skia.Path()
        path.moveTo(cx, cy)
        path.lineTo(cx + r * math.cos(start_angle), cy + r * math.sin(start_angle))
        path.arcTo(rect, math.degrees(start_angle), math.degrees(sweep_angle), False)
        path.close()

        fill = skia.Paint()
        fill.setAntiAlias(True)
        fill.setStyle(skia.Paint.kFill_Style)
        fill.setColor(_skia_color_from_hex(fill_color, self._effective_alpha()))
        self._apply_paint_filters(fill)
        self._canvas.drawPath(path, fill)

        if stroke_color is not None and stroke_width > 0.0:
            outline = skia.Paint()
            outline.setAntiAlias(True)
            outline.setStyle(skia.Paint.kStroke_Style)
            outline.setStrokeWidth(stroke_width)
            outline.setColor(_skia_color_from_hex(stroke_color, self._effective_alpha()))
            self._apply_paint_filters(outline)
            self._canvas.drawPath(path, outline)

    def stroke_path(
        self,
        commands: list[tuple[str, tuple[float, ...]]],
        color: str,
        width: float,
        *,
        fill_color: str | None = None,
        ox: float = 0.0,
        oy: float = 0.0,
        dash_pattern: tuple[float, ...] | None = None,
    ) -> None:
        import skia

        path = skia.Path()
        for cmd, args in commands:
            if cmd == "M":
                path.moveTo(ox + args[0], oy + args[1])
            elif cmd == "L":
                path.lineTo(ox + args[0], oy + args[1])
            elif cmd == "C":
                path.cubicTo(
                    ox + args[0],
                    oy + args[1],
                    ox + args[2],
                    oy + args[3],
                    ox + args[4],
                    oy + args[5],
                )
            elif cmd == "Z":
                path.close()
        if fill_color:
            fill = skia.Paint()
            fill.setAntiAlias(True)
            fill.setStyle(skia.Paint.kFill_Style)
            fill.setColor(_skia_color_from_hex(fill_color, self._effective_alpha()))
            self._apply_paint_filters(fill)
            self._canvas.drawPath(path, fill)
        self._paint.reset()
        self._paint.setAntiAlias(True)
        self._paint.setStrokeWidth(max(width, 0.001))
        self._paint.setStyle(skia.Paint.kStroke_Style)
        self._paint.setColor(_skia_color_from_hex(color, self._effective_alpha()))
        if dash_pattern:
            self._paint.setPathEffect(skia.DashPathEffect.Make(list(dash_pattern), 0.0))
        self._apply_paint_filters(self._paint)
        self._canvas.drawPath(path, self._paint)

    def fill_polygon(
        self,
        points: tuple[tuple[float, float], ...],
        *,
        fill_color: str,
        stroke_color: str | None,
        stroke_width: float,
        ox: float,
        oy: float,
    ) -> None:
        import skia

        if len(points) < 2:
            return
        pth = skia.Path()
        pth.moveTo(ox + points[0][0], oy + points[0][1])
        for vx, vy in points[1:]:
            pth.lineTo(ox + vx, oy + vy)
        pth.close()

        fill = skia.Paint()
        fill.setAntiAlias(True)
        fill.setStyle(skia.Paint.kFill_Style)
        fill.setColor(_skia_color_from_hex(fill_color, self._effective_alpha()))
        self._apply_paint_filters(fill)
        self._canvas.drawPath(pth, fill)

        if stroke_color is not None and stroke_width > 0.0:
            outline = skia.Paint()
            outline.setAntiAlias(True)
            outline.setStyle(skia.Paint.kStroke_Style)
            outline.setStrokeWidth(stroke_width)
            outline.setColor(_skia_color_from_hex(stroke_color, self._effective_alpha()))
            self._apply_paint_filters(outline)
            self._canvas.drawPath(pth, outline)

    def fill_round_rect(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        radius: float,
        *,
        fill_color: str,
        stroke_color: str | None = None,
        stroke_width: float = 0.0,
    ) -> None:
        import skia

        rect = skia.Rect.MakeLTRB(left, top, right, bottom)
        rr = skia.RRect.MakeRectXY(rect, radius, radius)
        fill = skia.Paint()
        fill.setAntiAlias(True)
        fill.setStyle(skia.Paint.kFill_Style)
        fill.setColor(_skia_color_from_hex(fill_color, self._effective_alpha()))
        self._apply_paint_filters(fill)
        self._canvas.drawRRect(rr, fill)
        if stroke_color is not None and stroke_width > 0.0:
            outline = skia.Paint()
            outline.setAntiAlias(True)
            outline.setStyle(skia.Paint.kStroke_Style)
            outline.setStrokeWidth(stroke_width)
            outline.setColor(_skia_color_from_hex(stroke_color, self._effective_alpha()))
            self._apply_paint_filters(outline)
            self._canvas.drawRRect(rr, outline)

    def fill_ellipse(
        self,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        *,
        fill_color: str,
        stroke_color: str | None = None,
        stroke_width: float = 0.0,
    ) -> None:
        import skia

        rect = skia.Rect.MakeXYWH(cx - rx, cy - ry, 2 * rx, 2 * ry)
        oval = skia.RRect.MakeOval(rect)
        fill = skia.Paint()
        fill.setAntiAlias(True)
        fill.setStyle(skia.Paint.kFill_Style)
        fill.setColor(_skia_color_from_hex(fill_color, self._effective_alpha()))
        self._apply_paint_filters(fill)
        self._canvas.drawRRect(oval, fill)
        if stroke_color is not None and stroke_width > 0.0:
            outline = skia.Paint()
            outline.setAntiAlias(True)
            outline.setStyle(skia.Paint.kStroke_Style)
            outline.setStrokeWidth(stroke_width)
            outline.setColor(_skia_color_from_hex(stroke_color, self._effective_alpha()))
            self._apply_paint_filters(outline)
            self._canvas.drawRRect(oval, outline)


    def fill_linear_gradient_rect(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        stops: tuple[tuple[float, str], ...],
        *,
        angle_rad: float = 0.0,
    ) -> None:
        import skia

        cx = (left + right) / 2.0
        cy = (top + bottom) / 2.0
        dx = math.cos(angle_rad) * (right - left) / 2.0
        dy = math.sin(angle_rad) * (bottom - top) / 2.0
        if not stops:
            return
        positions = [s for s, _ in stops]
        colors = [_skia_color_from_hex(c, self._effective_alpha()) for _, c in stops]
        shader = skia.GradientShader.MakeLinear(
            (skia.Point(cx - dx, cy - dy), skia.Point(cx + dx, cy + dy)),
            colors,
            positions,
            skia.TileMode.kClamp,
        )
        paint = skia.Paint()
        paint.setAntiAlias(True)
        paint.setShader(shader)
        self._apply_paint_filters(paint)
        rect = skia.Rect.MakeLTRB(left, top, right, bottom)
        self._canvas.drawRect(rect, paint)

    def fill_radial_gradient_disc(
        self,
        cx: float,
        cy: float,
        radius: float,
        stops: tuple[tuple[float, str], ...],
    ) -> None:
        import skia

        if not stops:
            return
        positions = [s for s, _ in stops]
        colors = [_skia_color_from_hex(c, self._effective_alpha()) for _, c in stops]
        shader = skia.GradientShader.MakeRadial(
            skia.Point(cx, cy),
            radius,
            colors,
            positions,
            skia.TileMode.kClamp,
        )
        paint = skia.Paint()
        paint.setAntiAlias(True)
        paint.setShader(shader)
        self._apply_paint_filters(paint)
        self._canvas.drawCircle(cx, cy, radius, paint)

    def draw_text(
        self,
        text: str,
        x: float,
        y: float,
        font_size: float,
        color: str,
        *,
        font_family: str = "sans-serif",
    ) -> None:
        import skia

        typeface = skia.Typeface(font_family)
        font = skia.Font(typeface, font_size)
        col = _skia_color_from_hex(color, self._effective_alpha())
        paint = skia.Paint(AntiAlias=True, Color=col)
        self._apply_paint_filters(paint)
        self._canvas.drawString(text, x, y + font_size, font, paint)

    def draw_svg_bytes(self, data: bytes, ox: float, oy: float, scale: float = 1.0) -> None:
        import skia

        stream = skia.MemoryStream(data)
        dom = skia.SVGDOM.MakeFromStream(stream)
        if dom is None:
            return
        self._canvas.save()
        self._canvas.translate(ox, oy)
        self._canvas.scale(scale, scale)
        dom.render(self._canvas)
        self._canvas.restore()



_SUBTITLE_TYST_WARNED = False


def _composite_subtitle_track(surface: Any, scene: Scene, t: float) -> None:
    """Burn active subtitle cues in **screen space** (after camera transform)."""
    global _SUBTITLE_TYST_WARNED
    track = scene.subtitle_track
    if track is None or not track.cues:
        return
    import shutil
    import sys

    import skia

    if shutil.which("typst") is None:
        if not _SUBTITLE_TYST_WARNED:
            print("motiongram: typst not on PATH; subtitles skipped", file=sys.stderr)
            _SUBTITLE_TYST_WARNED = True
        return
    active = active_subtitles(track, t)
    if not active:
        return
    page_w_pt, font_pt = subtitle_typst_layout(scene_width_px=float(scene.width), style=track.style)
    canvas = SkiaCanvas(surface)
    w = float(scene.width)
    h = float(scene.height)
    bottom = h - track.style.bottom_margin
    for cue in active:
        if not cue.typst.strip():
            continue
        svg_path = cached_typst_subtitle_svg_path(
            cue.typst,
            page_width_pt=page_w_pt,
            font_size_pt=font_pt,
            fill_rgb_hex=track.style.color,
        )
        if svg_path is None:
            continue
        data = svg_path.read_bytes()
        dom = skia.SVGDOM.MakeFromStream(skia.MemoryStream(data))
        if dom is None:
            continue
        sz = dom.containerSize()
        scaled_w = sz.width()
        scaled_h = sz.height()
        x = (w - scaled_w) / 2.0
        top = bottom - scaled_h
        canvas.draw_svg_bytes(data, x, top, 1.0)
        bottom = top - track.style.line_gap


@dataclass(slots=True)
class SkiaRenderer:
    """Rasterize the scene at time ``t``; returns HxWx4 ``uint8`` RGBA."""

    clear_color: tuple[int, int, int] = (0, 0, 0)

    def render_frame(
        self,
        scene: Scene,
        t: float,
        *,
        ease: Callable[[float], float] | None = smoothstep,
    ) -> npt.NDArray[np.uint8]:
        import skia

        surface = skia.Surface(scene.width, scene.height)
        raw = surface.getCanvas()
        r, g, b = self.clear_color
        raw.clear(skia.Color(r, g, b, 255))

        dt = 1.0 / scene.fps if scene.fps > 0 else 1.0 / 30.0
        step_frame(scene, t, dt, ease=ease)

        cam = scene.camera
        fx = cam.x if math.isfinite(cam.x) else scene.width / 2.0
        fy = cam.y if math.isfinite(cam.y) else scene.height / 2.0
        raw.save()
        raw.translate(scene.width / 2.0, scene.height / 2.0)
        raw.rotate(math.degrees(cam.rotation))
        z = cam.zoom if abs(cam.zoom) > 1e-9 else 1.0
        raw.scale(z, z)
        raw.translate(-fx, -fy)

        canvas = SkiaCanvas(surface)
        scene.root.draw(canvas, 0.0, 0.0)

        raw.restore()

        _composite_subtitle_track(surface, scene, t)

        img = surface.makeImageSnapshot()
        return np.asarray(img)
