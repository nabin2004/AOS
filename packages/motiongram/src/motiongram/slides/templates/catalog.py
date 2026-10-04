"""Template layout generators for all 10 ManimGram Slide archetypes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from motiongram.slides.schema import DeckStyleSpec, SlideSpec, TimelineActionSpec


@dataclass
class TemplateLayout:
    """Pre-calculated mobject instantiation statements and default timeline."""
    mobjects_init_code: list[str] = field(default_factory=list)
    default_timeline: list[TimelineActionSpec] = field(default_factory=list)
    selectors: dict[str, str] = field(default_factory=dict)


def _escape(text: str | None) -> str:
    if not text:
        return ""
    return text.replace('"', '\\"').replace("\n", " ").strip()


def get_template_layout(slide: SlideSpec, style: DeckStyleSpec) -> TemplateLayout:
    """Generate Manim code for the requested slide template within safe canvas bounds."""
    t_name = slide.template
    palette = style.palette
    typo = style.typography

    layout = TemplateLayout()

    if t_name == "title_slide":
        t_text = _escape(slide.title or "Presentation Title")
        sub_text = _escape(slide.subtitle or "")
        code = [
            f'title = Text("{t_text}", font_size={typo.title_font_size}, '
            f'color="{palette.primary}")',
            "title.move_to(UP * 0.6)",
        ]
        if sub_text:
            code.extend([
                f'subtitle = Text("{sub_text}", font_size={typo.body_font_size}, '
                f'color="{palette.text}")',
                "subtitle.next_to(title, DOWN, buff=0.6)",
            ])
        layout.mobjects_init_code = code

    elif t_name == "agenda_slide":
        t_text = _escape(slide.title or "Agenda")
        code = [
            f'title = Text("{t_text}", font_size={typo.heading_font_size}, '
            f'color="{palette.primary}")',
            "title.to_edge(UP, buff=0.6)",
            "agenda_items = VGroup()",
        ]
        items = slide.items or ["Topic 1", "Topic 2", "Topic 3"]
        for idx, item in enumerate(items):
            clean_item = _escape(item)
            code.extend([
                f'item_{idx} = VGroup(',
                f'    Dot(color="{palette.accent}", radius=0.08),',
                f'    Text("{clean_item}", font_size={typo.body_font_size}, '
                f'color="{palette.text}")',
                ').arrange(RIGHT, buff=0.3)',
                f'agenda_items.add(item_{idx})',
            ])
        code.append("agenda_items.arrange(DOWN, aligned_edge=LEFT, buff=0.45).move_to(DOWN * 0.2)")
        layout.mobjects_init_code = code

    elif t_name == "section_divider_slide":
        sec_num = _escape(slide.section_number or "01")
        t_text = _escape(slide.title or "Section")
        layout.mobjects_init_code = [
            f'sec_label = Text("SECTION {sec_num}", font_size={typo.caption_font_size}, '
            f'color="{palette.accent}")',
            "sec_label.move_to(UP * 0.8)",
            f'title = Text("{t_text}", font_size={typo.title_font_size}, '
            f'color="{palette.primary}")',
            "title.next_to(sec_label, DOWN, buff=0.4)",
        ]

    elif t_name == "bullet_reveal_slide":
        t_text = _escape(slide.title or "Key Concepts")
        code = [
            f'title = Text("{t_text}", font_size={typo.heading_font_size}, '
            f'color="{palette.primary}")',
            "title.to_edge(UP, buff=0.6)",
            "bullets = VGroup()",
        ]
        items = slide.items or ["Point 1", "Point 2", "Point 3"]
        for idx, item in enumerate(items):
            clean_item = _escape(item)
            code.extend([
                f'b_{idx} = VGroup(',
                f'    Dot(color="{palette.secondary}", radius=0.07),',
                f'    Text("{clean_item}", font_size={typo.body_font_size}, '
                f'color="{palette.text}")',
                ').arrange(RIGHT, buff=0.3)',
                f'bullets.add(b_{idx})',
            ])
        code.append("bullets.arrange(DOWN, aligned_edge=LEFT, buff=0.45).move_to(DOWN * 0.2)")
        layout.mobjects_init_code = code

    elif t_name == "concept_diagram_slide":
        t_text = _escape(slide.title or "Concept Overview")
        cap_text = _escape(slide.caption or "")
        code = [
            f'title = Text("{t_text}", font_size={typo.heading_font_size}, '
            f'color="{palette.primary}")',
            "title.to_edge(UP, buff=0.6)",
        ]
        if cap_text:
            code.extend([
                f'caption = Text("{cap_text}", font_size={typo.caption_font_size}, '
                f'color="{palette.text}")',
                "caption.to_edge(DOWN, buff=0.6)",
            ])
        layout.mobjects_init_code = code

    elif t_name == "equation_slide":
        t_text = _escape(slide.title or "Key Formula")
        eq_text = (slide.equations[0] if slide.equations else r"E = mc^2")
        cap_text = _escape(slide.caption or "")
        code = [
            f'title = Text("{t_text}", font_size={typo.heading_font_size}, '
            f'color="{palette.primary}")',
            "title.to_edge(UP, buff=0.6)",
            f'equation = MathTex(r"{eq_text}", font_size={typo.equation_font_size}, '
            f'color="{palette.accent}")',
            "equation.move_to(ORIGIN)",
        ]
        if cap_text:
            code.extend([
                f'caption = Text("{cap_text}", font_size={typo.caption_font_size}, '
                f'color="{palette.text}")',
                "caption.to_edge(DOWN, buff=0.6)",
            ])
        layout.mobjects_init_code = code

    elif t_name == "derivation_slide":
        t_text = _escape(slide.title or "Derivation")
        code = [
            f'title = Text("{t_text}", font_size={typo.heading_font_size}, '
            f'color="{palette.primary}")',
            "title.to_edge(UP, buff=0.6)",
            "steps = VGroup()",
        ]
        eqs = slide.equations or [r"f(x) = x^2", r"f'(x) = 2x"]
        for idx, eq in enumerate(eqs):
            code.extend([
                f'step_{idx} = MathTex(r"{eq}", font_size={typo.equation_font_size})',
                f'steps.add(step_{idx})',
            ])
        code.append("steps.arrange(DOWN, buff=0.5).move_to(DOWN * 0.2)")
        layout.mobjects_init_code = code

    elif t_name == "comparison_slide":
        t_text = _escape(slide.title or "Comparison")
        left_h = _escape(slide.left.get("header", "Option A") if slide.left else "Option A")
        right_h = _escape(slide.right.get("header", "Option B") if slide.right else "Option B")
        left_b = _escape(slide.left.get("text", "") if slide.left else "")
        right_b = _escape(slide.right.get("text", "") if slide.right else "")
        code = [
            f'title = Text("{t_text}", font_size={typo.heading_font_size}, '
            f'color="{palette.primary}")',
            "title.to_edge(UP, buff=0.6)",
            "divider = Line(UP * 2.0, DOWN * 2.5, color=DARK_GRAY)",
            f'left_head = Text("{left_h}", font_size={typo.body_font_size}, '
            f'color="{palette.secondary}")',
            f'left_body = Text("{left_b}", font_size={typo.caption_font_size}, '
            f'color="{palette.text}")',
            "left_col = VGroup(left_head, left_body).arrange(DOWN, buff=0.3)"
            ".move_to(LEFT * 3.2 + DOWN * 0.2)",
            f'right_head = Text("{right_h}", font_size={typo.body_font_size}, '
            f'color="{palette.accent}")',
            f'right_body = Text("{right_b}", font_size={typo.caption_font_size}, '
            f'color="{palette.text}")',
            "right_col = VGroup(right_head, right_body).arrange(DOWN, buff=0.3)"
            ".move_to(RIGHT * 3.2 + DOWN * 0.2)",
        ]
        layout.mobjects_init_code = code

    elif t_name == "summary_slide":
        t_text = _escape(slide.title or "Key Takeaways")
        code = [
            f'title = Text("{t_text}", font_size={typo.heading_font_size}, '
            f'color="{palette.primary}")',
            "title.to_edge(UP, buff=0.6)",
            "takeaways = VGroup()",
        ]
        items = slide.items or ["Summary Point 1", "Summary Point 2"]
        for idx, item in enumerate(items):
            clean_item = _escape(item)
            code.extend([
                f't_{idx} = VGroup(',
                f'    Dot(color="{palette.accent}", radius=0.08),',
                f'    Text("{clean_item}", font_size={typo.body_font_size}, '
                f'color="{palette.text}")',
                ').arrange(RIGHT, buff=0.3)',
                f'takeaways.add(t_{idx})',
            ])
        code.append("takeaways.arrange(DOWN, aligned_edge=LEFT, buff=0.5).move_to(DOWN * 0.2)")
        layout.mobjects_init_code = code

    elif t_name == "end_slide":
        t_text = _escape(slide.title or "Thank You")
        sub_text = _escape(slide.subtitle or "Questions & Discussion")
        layout.mobjects_init_code = [
            f'title = Text("{t_text}", font_size={typo.title_font_size}, '
            f'color="{palette.primary}")',
            "title.move_to(UP * 0.5)",
            f'subtitle = Text("{sub_text}", font_size={typo.body_font_size}, '
            f'color="{palette.secondary}")',
            "subtitle.next_to(title, DOWN, buff=0.6)",
        ]

    return layout
