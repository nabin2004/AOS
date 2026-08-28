from __future__ import annotations

from typing import List, Optional

from manim import DOWN, LEFT, RIGHT, UP, Dot, MathTex, Text, VGroup, ImageMobject, Code

from aos_manim_core import ThemeConfig, get_theme

from ..components.card import Badge, CalloutBox
from ..document.model import (
    AnimationSlot,
    Block,
    Callout,
    CodeBlock,
    ColumnGroup,
    ContentBlock,
    DiagramRef,
    Equation,
    Heading,
    ImageBlock,
    ListBlock,
    Paragraph,
    RawMobject,
)
from ..diagrams.registry import build_animation, build_diagram
from ..typography import slide_tex, wrapped_slide_tex
from .box import LayoutContext, LayoutNode, LeafNode, Rect
from .primitives import HStack, VStack


def wrapped_text(
    text: str,
    font_size: int,
    max_width: float,
    theme: ThemeConfig,
    *,
    color=None,
    weight: str = "NORMAL",
) -> VGroup:
    color = color or theme.text_main
    return wrapped_slide_tex(text, font_size, max_width, color=color, weight=weight)


def block_to_node(block: ContentBlock, ctx: LayoutContext) -> LayoutNode:
    theme: ThemeConfig = ctx.theme or get_theme()
    role = getattr(block, "role", "body")
    priority = block.resolved_priority

    if ctx.drop_decorations and priority <= 10:
        node = LeafNode(lambda c, r: VGroup(), role=role, priority=priority)
        node.dropped = True
        return node

    if isinstance(block, Paragraph):
        def build_p(c: LayoutContext, rect: Rect) -> VGroup:
            t = c.theme or theme
            return wrapped_text(block.text, c.body_font_size, rect.width, t, color=t.text_main)

        node = LeafNode(build_p, role=role, priority=priority, can_wrap=True, align="top-left")
        node.cue_id = block.id
        return node

    if isinstance(block, Heading):
        def build_h(c: LayoutContext, rect: Rect) -> VGroup:
            t = c.theme or theme
            size = c.heading_font_size if block.level <= 2 else c.body_font_size
            return wrapped_text(block.text, size, rect.width, t, color=t.primary, weight="BOLD")

        node = LeafNode(build_h, role=role, priority=priority, can_wrap=True, align="top-left")
        node.cue_id = block.id
        return node

    if isinstance(block, Equation):
        def build_eq(c: LayoutContext, rect: Rect) -> VGroup:
            t = c.theme or theme
            try:
                mob = MathTex(block.latex, font_size=c.equation_font_size, color=t.text_main)
            except Exception:
                mob = Text(block.latex, font_size=c.body_font_size, color=t.text_main, font=t.fonts.text_font)
            return VGroup(mob)

        node = LeafNode(build_eq, role=role, priority=priority, can_scale=True, align="center")
        node.cue_id = block.id
        return node

    if isinstance(block, ListBlock):
        item_ids = list(block.item_ids) if block.item_ids else [None] * len(block.items)
        leaves: List[LayoutNode] = []
        for item, iid in zip(block.items, item_ids):

            def build_item(c: LayoutContext, rect: Rect, item_text: str = item) -> VGroup:
                t = c.theme or theme
                dot = Dot(radius=0.07, color=t.primary)
                txt = wrapped_text(
                    item_text,
                    c.body_font_size,
                    max(rect.width - 0.4, 1.0),
                    t,
                    color=t.text_main,
                )
                return VGroup(dot, txt).arrange(RIGHT, buff=0.2, aligned_edge=UP)

            leaf = LeafNode(build_item, role=role, priority=priority, can_wrap=True, align="top-left")
            leaf.cue_id = iid
            leaves.append(leaf)
        stack = VStack(leaves, spacing=0.22, align="top-left")
        return stack

    if isinstance(block, Callout):
        def build_call(c: LayoutContext, rect: Rect) -> VGroup:
            t = c.theme or theme
            box = CalloutBox(
                block.title,
                block.body,
                width=min(rect.width, 10.5),
                height=max(1.2, min(rect.height, 1.8)),
                theme=t,
            )
            return VGroup(box)

        node = LeafNode(build_call, role=role, priority=priority, can_scale=True, align="center")
        node.cue_id = block.id
        return node

    if isinstance(block, CodeBlock):
        def build_code(c: LayoutContext, rect: Rect) -> VGroup:
            t = c.theme or theme
            try:
                code_mob = Code(
                    code_string=block.code,
                    language=block.language or "python",
                    background="window",
                    font_size=c.code_font_size,
                )
            except Exception:
                lines = block.code.splitlines() or [""]
                code_mob = VGroup(
                    *[
                        Text(line if line else " ", font_size=c.code_font_size, font=t.fonts.code_font, color=t.text_main)
                        for line in lines
                    ]
                ).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
            return VGroup(code_mob)

        node = LeafNode(build_code, role=role, priority=priority, can_scale=True, align="top-left")
        node.cue_id = block.id
        return node

    if isinstance(block, ImageBlock):
        def build_img(c: LayoutContext, rect: Rect) -> VGroup:
            t = c.theme or theme
            try:
                img = ImageMobject(block.path)
            except Exception:
                img = Text(block.caption or block.path, font_size=c.caption_font_size, color=t.text_muted)
            group = VGroup(img)
            if block.caption:
                cap = wrapped_text(block.caption, c.caption_font_size, rect.width, t, color=t.text_muted)
                group = VGroup(img, cap).arrange(DOWN, buff=0.12)
            return group

        node = LeafNode(build_img, role=role, priority=priority, can_scale=True, keep_aspect=True)
        node.cue_id = block.id
        return node

    if isinstance(block, DiagramRef):
        def build_d(c: LayoutContext, rect: Rect) -> VGroup:
            t = c.theme or theme
            target_w = rect.width * c.diagram_scale
            target_h = rect.height * c.diagram_scale
            return build_diagram(block.name, target_w, target_h, t, **block.kwargs)

        node = LeafNode(build_d, role=role, priority=priority, can_scale=True, keep_aspect=True)
        node.cue_id = block.id
        return node

    if isinstance(block, AnimationSlot):
        def build_anim(c: LayoutContext, rect: Rect) -> VGroup:
            t = c.theme or theme
            scale = getattr(c, "diagram_scale", 1.0)
            target_w = rect.width * scale
            target_h = rect.height * scale
            return build_animation(block.name, target_w, target_h, t, **block.kwargs)

        node = LeafNode(build_anim, role=role, priority=priority, can_scale=True, keep_aspect=True, align="center")
        node.cue_id = block.id
        return node

    if isinstance(block, RawMobject):
        def build_raw(c: LayoutContext, rect: Rect) -> VGroup:
            mob = block.mobject
            return VGroup(mob.copy()) if mob is not None else VGroup()

        node = LeafNode(build_raw, role=role, priority=priority, can_scale=True)
        node.cue_id = block.id
        return node

    if isinstance(block, ColumnGroup):
        cols = [blocks_to_vstack(col, ctx) for col in block.columns]
        return HStack(cols, spacing=ctx.spacing, ratios=block.ratios)

    def build_fallback(c: LayoutContext, rect: Rect) -> VGroup:
        t = c.theme or theme
        return VGroup(Text(str(block), font_size=c.caption_font_size, color=t.text_muted))

    return LeafNode(build_fallback, role=role, priority=priority)


def blocks_to_vstack(blocks: List[ContentBlock], ctx: LayoutContext) -> VStack:
    nodes = [block_to_node(b, ctx) for b in blocks]
    if not nodes:
        nodes = [LeafNode(lambda c, r: VGroup())]
    return VStack(nodes, spacing=ctx.spacing, align="top")
