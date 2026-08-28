from __future__ import annotations

from typing import List, Optional, Sequence

from manim import DOWN, LEFT, ORIGIN, RIGHT, UP, VGroup

from .box import LayoutContext, LayoutNode, Rect, Size, fit_mobject, place_mobject


class ContainerNode(LayoutNode):
    def __init__(
        self,
        children: Sequence[LayoutNode],
        *,
        spacing: float = 0.28,
        align: str = "top-left",
        role: str = "body",
        priority: int = 50,
        ratios: Optional[List[float]] = None,
    ) -> None:
        super().__init__(role=role, priority=priority, align=align)
        self._children: List[LayoutNode] = list(children)
        self.spacing = spacing
        self.ratios = ratios

    def children(self) -> Sequence[LayoutNode]:
        return [c for c in self._children if not c.dropped]

    def _active(self) -> List[LayoutNode]:
        return [c for c in self._children if not c.dropped]


class VStack(ContainerNode):
    def measure(self, ctx: LayoutContext, available: Rect) -> Size:
        kids = self._active()
        if not kids:
            return Size(0.01, 0.01)
        spacing = ctx.spacing if self.spacing is None else self.spacing
        widths, heights = [], []
        for child in kids:
            sz = child.measure(ctx, available)
            widths.append(sz.width)
            heights.append(sz.height)
        total_h = sum(heights) + spacing * max(len(kids) - 1, 0)
        return Size(max(widths) if widths else 0.01, total_h)

    def layout(self, ctx: LayoutContext, rect: Rect) -> VGroup:
        kids = self._active()
        group = VGroup()
        if not kids:
            self.mobject = group
            return group
        spacing = self.spacing
        sizes = [child.measure(ctx, rect) for child in kids]
        cursor_top = rect.top
        leftover = rect.height - (sum(s.height for s in sizes) + spacing * max(len(kids) - 1, 0))
        for child, sz in zip(kids, sizes):
            child_h = min(sz.height, max(rect.height * 0.15, sz.height))
            if leftover < 0 and sz.height > 0:
                child_h = sz.height
            child_rect = Rect(rect.x, cursor_top - child_h, rect.width, max(child_h, 0.05))
            if leftover < 0:
                child_rect = Rect(rect.x, cursor_top - sz.height, rect.width, max(sz.height, 0.05))
            mob = child.layout(ctx, child_rect)
            group.add(mob)
            cursor_top = child_rect.bottom - spacing
        self.mobject = group
        return group


class HStack(ContainerNode):
    def measure(self, ctx: LayoutContext, available: Rect) -> Size:
        kids = self._active()
        if not kids:
            return Size(0.01, 0.01)
        widths, heights = [], []
        for child in kids:
            sz = child.measure(ctx, available)
            widths.append(sz.width)
            heights.append(sz.height)
        total_w = sum(widths) + self.spacing * max(len(kids) - 1, 0)
        return Size(total_w, max(heights) if heights else 0.01)

    def layout(self, ctx: LayoutContext, rect: Rect) -> VGroup:
        kids = self._active()
        group = VGroup()
        if not kids:
            self.mobject = group
            return group
        n = len(kids)
        gap_total = self.spacing * max(n - 1, 0)
        usable = max(rect.width - gap_total, 0.05)
        if self.ratios and len(self.ratios) == n:
            total_r = sum(self.ratios) or 1.0
            widths = [usable * (r / total_r) for r in self.ratios]
        else:
            widths = [usable / n] * n
        cursor = rect.x
        for child, w in zip(kids, widths):
            child_rect = Rect(cursor, rect.y, w, rect.height)
            mob = child.layout(ctx, child_rect)
            group.add(mob)
            cursor += w + self.spacing
        self.mobject = group
        return group


class Grid(ContainerNode):
    def __init__(
        self,
        children: Sequence[LayoutNode],
        *,
        rows: Optional[int] = None,
        cols: int = 2,
        spacing: float = 0.25,
        **kwargs,
    ) -> None:
        super().__init__(children, spacing=spacing, **kwargs)
        self.cols = max(cols, 1)
        self.rows = rows

    def measure(self, ctx: LayoutContext, available: Rect) -> Size:
        return Size(available.width, available.height)

    def layout(self, ctx: LayoutContext, rect: Rect) -> VGroup:
        kids = self._active()
        group = VGroup()
        if not kids:
            self.mobject = group
            return group
        cols = self.cols
        rows = self.rows or max((len(kids) + cols - 1) // cols, 1)
        cell_w = (rect.width - self.spacing * (cols - 1)) / cols
        cell_h = (rect.height - self.spacing * (rows - 1)) / rows
        for i, child in enumerate(kids):
            r, c = divmod(i, cols)
            cell = Rect(
                rect.x + c * (cell_w + self.spacing),
                rect.top - (r + 1) * cell_h - r * self.spacing,
                cell_w,
                cell_h,
            )
            group.add(child.layout(ctx, cell))
        self.mobject = group
        return group


class Overlay(ContainerNode):
    def measure(self, ctx: LayoutContext, available: Rect) -> Size:
        w = h = 0.01
        for child in self._active():
            sz = child.measure(ctx, available)
            w = max(w, sz.width)
            h = max(h, sz.height)
        return Size(w, h)

    def layout(self, ctx: LayoutContext, rect: Rect) -> VGroup:
        group = VGroup()
        for child in self._active():
            group.add(child.layout(ctx, rect))
        self.mobject = group
        return group


class Padding(ContainerNode):
    def __init__(self, child: LayoutNode, pad: float = 0.15, **kwargs) -> None:
        super().__init__([child], **kwargs)
        self.pad = pad

    def measure(self, ctx: LayoutContext, available: Rect) -> Size:
        inner = available.inset(self.pad)
        sz = self._children[0].measure(ctx, inner)
        return Size(sz.width + 2 * self.pad, sz.height + 2 * self.pad)

    def layout(self, ctx: LayoutContext, rect: Rect) -> VGroup:
        inner = rect.inset(self.pad)
        mob = self._children[0].layout(ctx, inner)
        group = VGroup(mob)
        self.mobject = group
        return group


class Center(ContainerNode):
    def __init__(self, child: LayoutNode, **kwargs) -> None:
        super().__init__([child], align="center", **kwargs)

    def measure(self, ctx: LayoutContext, available: Rect) -> Size:
        return self._children[0].measure(ctx, available)

    def layout(self, ctx: LayoutContext, rect: Rect) -> VGroup:
        child = self._children[0]
        sz = child.measure(ctx, rect)
        inner = Rect(
            rect.center_x - sz.width / 2.0,
            rect.center_y - sz.height / 2.0,
            sz.width,
            sz.height,
        )
        # Keep the child inside the available rect.
        inner = Rect(
            max(inner.x, rect.x),
            max(inner.y, rect.y),
            min(sz.width, rect.width),
            min(sz.height, rect.height),
        )
        mob = child.layout(ctx, inner)
        group = VGroup(mob)
        self.mobject = group
        return group


class Align(ContainerNode):
    def __init__(self, child: LayoutNode, align: str = "top-left", **kwargs) -> None:
        super().__init__([child], align=align, **kwargs)

    def measure(self, ctx: LayoutContext, available: Rect) -> Size:
        return self._children[0].measure(ctx, available)

    def layout(self, ctx: LayoutContext, rect: Rect) -> VGroup:
        child = self._children[0]
        child.align = self.align
        mob = child.layout(ctx, rect)
        group = VGroup(mob)
        self.mobject = group
        return group


class Box(ContainerNode):
    """Optional framed region; child is padded inside the available rect."""

    def __init__(self, child: LayoutNode, pad: float = 0.12, **kwargs) -> None:
        super().__init__([child], **kwargs)
        self.pad = pad

    def measure(self, ctx: LayoutContext, available: Rect) -> Size:
        return Size(available.width, available.height)

    def layout(self, ctx: LayoutContext, rect: Rect) -> VGroup:
        inner = rect.inset(self.pad)
        mob = self._children[0].layout(ctx, inner)
        group = VGroup(mob)
        self.mobject = group
        return group
