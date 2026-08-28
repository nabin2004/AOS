from __future__ import annotations

from typing import List, Optional, Tuple

from manim import DOWN, LEFT, RIGHT, Text, VGroup

from aos_manim_core import ThemeConfig, get_theme

from ..components.card import Badge, Card
from ..document.model import (
    Callout,
    CodeBlock,
    ContentBlock,
    DiagramRef,
    Equation,
    ImageBlock,
    ListBlock,
    Paragraph,
    SlideSpec,
)
from .box import LayoutContext, LayoutNode, LeafNode, Rect
from .builders import block_to_node, blocks_to_vstack, wrapped_text
from .primitives import Align, Center, Grid, HStack, Overlay, VStack


COLUMN_LAYOUTS = {"two-column", "three-column", "image-text", "text-image", "comparison"}
WIDE_ASPECT = 1.4


def _textish(block: ContentBlock) -> bool:
    return isinstance(block, (Paragraph, ListBlock, Equation, Callout)) and not isinstance(
        block, (DiagramRef, ImageBlock, CodeBlock)
    )


def _visual(block: ContentBlock) -> bool:
    from ..document.model import AnimationSlot

    return isinstance(block, (DiagramRef, ImageBlock, CodeBlock, AnimationSlot))


def split_columns(spec: SlideSpec) -> Tuple[List[ContentBlock], List[ContentBlock], List[ContentBlock]]:
    if spec.columns:
        cols = list(spec.columns) + [[], [], []]
        return cols[0], cols[1], cols[2]
    if spec.left or spec.right:
        return list(spec.left), list(spec.right), []

    left, right, rest = [], [], []
    for block in spec.blocks:
        span = getattr(block, "span", "full")
        if span == "left":
            left.append(block)
        elif span == "right":
            right.append(block)
        elif _visual(block):
            right.append(block)
        else:
            left.append(block)
            rest.append(block)
    if not right:
        return spec.blocks, [], []
    return left, right, []


def build_recipe(spec: SlideSpec, ctx: LayoutContext) -> LayoutNode:
    layout = spec.layout or "title-content"
    if ctx.collapse_columns and layout in COLUMN_LAYOUTS:
        left, right, third = split_columns(spec)
        stacked = list(left) + list(right) + list(third)
        return blocks_to_vstack(stacked or spec.blocks, ctx)

    if layout == "title":
        return _title_recipe(spec, ctx)
    if layout == "section":
        return _section_recipe(spec, ctx)
    if layout == "equation-focus":
        return _equation_focus(spec, ctx)
    if layout == "diagram-focus":
        return _diagram_focus(spec, ctx)
    if layout == "code-focus":
        return _code_focus(spec, ctx)
    if layout == "full-screen":
        return Center(blocks_to_vstack(spec.blocks, ctx))
    if layout == "two-column":
        return _two_column(spec, ctx, ratios=spec.ratios or [0.42, 0.58])
    if layout == "three-column":
        return _three_column(spec, ctx)
    if layout == "comparison":
        return _two_column(spec, ctx, ratios=spec.ratios or [0.5, 0.5])
    if layout == "text-image":
        return _two_column(spec, ctx, ratios=spec.ratios or [0.4, 0.6])
    if layout == "image-text":
        left, right, _ = split_columns(spec)
        if not left and not right:
            visuals = [b for b in spec.blocks if _visual(b)]
            texts = [b for b in spec.blocks if not _visual(b)]
            left, right = visuals, texts
        return HStack(
            [blocks_to_vstack(left, ctx), blocks_to_vstack(right, ctx)],
            spacing=ctx.spacing,
            ratios=spec.ratios or [0.55, 0.45],
        )
    if layout == "quiz":
        return _quiz_recipe(spec, ctx)
    return blocks_to_vstack(spec.blocks, ctx)


def _title_recipe(spec: SlideSpec, ctx: LayoutContext) -> LayoutNode:
    theme: ThemeConfig = ctx.theme or get_theme()

    def build_title(_c: LayoutContext, rect: Rect) -> VGroup:
        t = _c.theme or theme
        title = wrapped_text(spec.title or "", _c.title_font_size + 8, rect.width * 0.9, t, color=t.primary, weight="BOLD")
        return VGroup(title)

    def build_subtitle(_c: LayoutContext, rect: Rect) -> VGroup:
        t = _c.theme or theme
        if spec.subtitle:
            sub = wrapped_text(spec.subtitle, _c.heading_font_size - 4, rect.width * 0.85, t, color=t.text_main)
            return VGroup(sub)
        return VGroup()

    def build_meta(_c: LayoutContext, rect: Rect) -> VGroup:
        t = _c.theme or theme
        meta_bits = [x for x in (spec.author, spec.affiliation, spec.date) if x]
        if not meta_bits:
            return VGroup()
        from ..typography import slide_tex

        return VGroup(
            *[
                slide_tex(bit, font_size=_c.body_font_size if i == 0 else _c.caption_font_size, color=t.text_muted)
                for i, bit in enumerate(meta_bits)
            ]
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12)

    title_leaf = LeafNode(build_title, role="title", priority=100, can_scale=True, align="top-left")
    title_leaf.cue_id = "title"

    sub_leaf = LeafNode(build_subtitle, role="title", priority=90, can_scale=True, align="top-left")
    sub_leaf.cue_id = "subtitle"

    head_stack = VStack([title_leaf, sub_leaf], spacing=0.32, align="top-left")

    meta_leaf = LeafNode(build_meta, role="decoration", priority=20, can_scale=True, align="bottom-left")
    meta_leaf.cue_id = "meta"
    meta = Align(meta_leaf, align="bottom-left")

    return Overlay([head_stack, meta])


def _section_recipe(spec: SlideSpec, ctx: LayoutContext) -> LayoutNode:
    theme: ThemeConfig = ctx.theme or get_theme()

    def build(_c: LayoutContext, rect: Rect) -> VGroup:
        t = _c.theme or theme
        group = VGroup()
        if spec.section_number is not None:
            group.add(Badge(f"SECTION {spec.section_number}", color=t.accent, font_size=t.fonts.caption_font_size + 2, theme=t))
        group.add(
            wrapped_text(spec.title or "", _c.title_font_size + 4, rect.width * 0.9, t, color=t.text_main, weight="BOLD")
        )
        if spec.subtitle:
            group.add(wrapped_text(spec.subtitle, _c.body_font_size, rect.width * 0.8, t, color=t.text_muted))
        return group.arrange(DOWN, aligned_edge=LEFT, buff=0.28)

    node = Align(LeafNode(build, role="title", priority=100, can_scale=True, align="top-left"), align="top-left")
    node.cue_id = "section"
    return node


def _partition_focus(spec: SlideSpec, cls) -> Tuple[List[ContentBlock], List[ContentBlock]]:
    main = [b for b in spec.blocks if isinstance(b, cls)]
    rest = [b for b in spec.blocks if not isinstance(b, cls)]
    if not main and spec.blocks:
        main = [spec.blocks[0]]
        rest = spec.blocks[1:]
    return main, rest


def _equation_focus(spec: SlideSpec, ctx: LayoutContext) -> LayoutNode:
    main, rest = _partition_focus(spec, Equation)
    for b in main:
        b.role = "main_equation"
    return VStack(
        [
            Center(blocks_to_vstack(main, ctx) if main else blocks_to_vstack(spec.blocks[:1], ctx)),
            blocks_to_vstack(rest, ctx),
        ],
        spacing=ctx.spacing,
        ratios=None,
    )


def _diagram_focus(spec: SlideSpec, ctx: LayoutContext) -> LayoutNode:
    from ..document.model import AnimationSlot

    main, rest = _partition_focus(spec, DiagramRef)
    if not main:
        main, rest = _partition_focus(spec, AnimationSlot)
    if not main:
        main, rest = _partition_focus(spec, ImageBlock)
    return VStack(
        [
            blocks_to_vstack(rest[:1], ctx) if rest else LeafNode(lambda c, r: VGroup()),
            Center(blocks_to_vstack(main, ctx) if main else blocks_to_vstack(spec.blocks, ctx)),
            blocks_to_vstack(rest[1:], ctx),
        ],
        spacing=ctx.spacing,
    )


def _code_focus(spec: SlideSpec, ctx: LayoutContext) -> LayoutNode:
    main, rest = _partition_focus(spec, CodeBlock)
    return VStack(
        [blocks_to_vstack(rest, ctx), Center(blocks_to_vstack(main, ctx) if main else blocks_to_vstack(spec.blocks, ctx))],
        spacing=ctx.spacing,
    )


def _two_column(spec: SlideSpec, ctx: LayoutContext, ratios: List[float]) -> LayoutNode:
    left, right, _ = split_columns(spec)
    if not right:
        return blocks_to_vstack(left or spec.blocks, ctx)
    return HStack(
        [blocks_to_vstack(left, ctx), blocks_to_vstack(right, ctx)],
        spacing=ctx.spacing,
        ratios=ratios,
    )


def _three_column(spec: SlideSpec, ctx: LayoutContext) -> LayoutNode:
    a, b, c = split_columns(spec)
    if spec.columns:
        nodes = [blocks_to_vstack(col, ctx) for col in spec.columns]
        return HStack(nodes, spacing=ctx.spacing, ratios=spec.ratios)
    chunks = spec.blocks
    n = max(len(chunks), 1)
    size = (n + 2) // 3
    cols = [chunks[i : i + size] for i in range(0, n, size)] or [chunks]
    return HStack([blocks_to_vstack(col, ctx) for col in cols], spacing=ctx.spacing, ratios=spec.ratios)


def _quiz_recipe(spec: SlideSpec, ctx: LayoutContext) -> LayoutNode:
    theme: ThemeConfig = ctx.theme or get_theme()

    def build_q(_c: LayoutContext, rect: Rect) -> VGroup:
        t = _c.theme or theme
        card = Card(width=min(rect.width, 11.0), height=min(rect.height, 1.3), fill_color=t.surface_variant, theme=t)
        txt = wrapped_text(spec.question or "", _c.body_font_size, min(rect.width, 10.5) - 0.4, t, color=t.text_main, weight="BOLD")
        txt.move_to(card.background_rect.get_center())
        return VGroup(card, txt)

    option_nodes: List[LayoutNode] = []
    labels = list("ABCDEF")
    for i, opt in enumerate(spec.options):
        def build_opt(_c: LayoutContext, rect: Rect, idx=i, text=opt) -> VGroup:
            t = _c.theme or theme
            c = Card(width=min(rect.width, 5.3), height=min(rect.height, 1.0), theme=t)
            lbl = labels[idx] if idx < len(labels) else str(idx + 1)
            badge = Badge(lbl, color=t.primary, font_size=16, theme=t)
            txt = wrapped_text(text, max(_c.body_font_size - 4, 14), max(rect.width - 1.2, 1.0), t)
            badge.next_to(c.background_rect.get_left() + RIGHT * 0.25, RIGHT, buff=0)
            txt.next_to(badge, RIGHT, buff=0.2)
            return VGroup(c, badge, txt)

        option_nodes.append(LeafNode(build_opt, role="body", priority=50, can_scale=True))

    cols = 2 if len(option_nodes) > 1 and not ctx.collapse_columns else 1
    return VStack(
        [LeafNode(build_q, role="body", priority=80, can_scale=True), Grid(option_nodes, cols=cols, spacing=0.3)],
        spacing=0.35,
    )
