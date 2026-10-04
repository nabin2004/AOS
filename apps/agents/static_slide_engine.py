"""Static Slide Generation Engine for AOS (ManimCE Producer-Consumer Architecture).

This module replaces animation-and-frame-extraction workflows with a clean,
deterministic, still-image presentation slide generation system entirely built
on Manim Community Edition (ManimCE).

Key Architectural Principles:
1. Purely Static Scene Composition:
   - Uses `self.add()`, `VGroup`, `Text`, `MathTex`, `RoundedRectangle`, etc.
   - Absolutely NO animation functions (`self.play`, `Write`, `Create`, `FadeIn`,
     `FadeOut`, `Transform`, `self.wait`, etc.).
2. On-Slide Narration & Speaker Notes:
   - Spoken narration and speaker notes are integrated into clear visual cards/banners
     directly on the slide canvas.
   - Accompanying structured narration files (.json and .txt) are exported alongside
     the image for external audio/TTS synthesis or documentation.
3. Native ManimCE Still-Image Rendering:
   - Uses `save_last_frame=True` / `format="png"`.
   - Produces a single high-definition PNG per slide (no MP4/WebM videos produced).
4. Decoupled Producer-Consumer Architecture:
   - Producer: Emits structured Pydantic models (`StaticSlideData`, `NarrationSpec`).
   - Consumer: Validates content, formats typography, calculates collision-free
     bounding boxes, and renders the static PNG image.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import textwrap
from typing import Any, Literal
from uuid import uuid4

from manim import (
    Scene,
    VGroup,
    Text,
    MathTex,
    Line,
    RoundedRectangle,
    SurroundingRectangle,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    ORIGIN,
    UL,
    UR,
    DL,
    DR,
    tempconfig,
)
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ============================================================================
# 1. Structured Data Models (Producer Output Schema)
# ============================================================================

class SlideStyle(BaseModel):
    """Visual theme and color palette for static slide composition."""
    background_color: str = Field(default="#0B0F19", description="Canvas background hex")
    primary_color: str = Field(default="#38BDF8", description="Title & primary accent (Sky Blue)")
    secondary_color: str = Field(default="#818CF8", description="Secondary accent (Indigo)")
    accent_color: str = Field(default="#F59E0B", description="Highlight & callout border (Amber)")
    success_color: str = Field(default="#10B981", description="Green indicator (Emerald)")
    text_color: str = Field(default="#F8FAFC", description="Primary body text (Slate 50)")
    muted_text_color: str = Field(default="#94A3B8", description="Secondary/notes text (Slate 400)")
    card_bg_color: str = Field(default="#1E293B", description="Card background (Slate 800)")
    card_border_color: str = Field(default="#334155", description="Card border (Slate 700)")
    note_bg_color: str = Field(default="#0F172A", description="Narration card background (Slate 900)")
    font_family: str = Field(default="sans-serif", description="Font family name")


class BulletItem(BaseModel):
    """Individual bullet point with optional label and highlighted keyword."""
    text: str = Field(..., description="Main bullet text")
    prefix: str | None = Field(default=None, description="Optional bold prefix or term")


class ContentBlock(BaseModel):
    """Modular content component for a slide."""
    block_type: Literal["bullets", "equation", "key_definition", "comparison", "callout"] = Field(
        default="bullets"
    )
    title: str | None = Field(default=None, description="Block header or category")
    items: list[str] = Field(default_factory=list, description="Bullet items or definition pairs")
    equation: str | None = Field(default=None, description="LaTeX formula if applicable")
    highlight_color: str | None = Field(default=None, description="Accent color override")


class NarrationSpec(BaseModel):
    """Spoken script and presenter notes associated with the slide."""
    script: str = Field(..., description="Complete voiceover narration or lecture script")
    speaker_notes: str | None = Field(
        default=None,
        description="Concise presenter takeaways or on-slide speaker notes",
    )
    key_terms: list[str] = Field(default_factory=list, description="Key pedagogical keywords")

    @field_validator("speaker_notes", mode="before")
    @classmethod
    def default_speaker_notes(cls, v: str | None, values: Any) -> str:
        if v and v.strip():
            return v.strip()
        # Fall back to a truncated version of the script if not explicitly provided
        return ""


class StaticSlideData(BaseModel):
    """Complete, self-contained specification for a single presentation slide."""
    slide_num: int = Field(default=1, ge=1)
    total_slides: int = Field(default=1, ge=1)
    topic: str = Field(default="Educational Presentation", description="Lecture or topic name")
    title: str = Field(..., min_length=2, max_length=120, description="Slide main title")
    subtitle: str | None = Field(default=None, max_length=160, description="Optional subtitle")
    layout: Literal["standard", "two_column", "formula_focus", "card_grid"] = Field(
        default="standard",
        description="Layout composition strategy",
    )
    blocks: list[ContentBlock] = Field(default_factory=list, description="Ordered content blocks")
    narration: NarrationSpec = Field(..., description="Spoken narration & speaker note text")
    style: SlideStyle = Field(default_factory=SlideStyle, description="Visual theme styling")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Slide title cannot be empty")
        return clean


class StaticSlideResult(BaseModel):
    """Execution output returned by the consumer after rendering a slide."""
    slide_num: int
    image_path: str
    narration_json_path: str
    narration_txt_path: str
    code_path: str
    success: bool
    error: str | None = None


# ============================================================================
# 2. Layout Helpers (Collision-Free, Responsive ManimCE Composition)
# ============================================================================

def create_safe_text(
    text: str,
    font_size: int = 24,
    color: str = "#F8FAFC",
    weight: str = "NORMAL",
    max_width: float = 12.5,
    max_height: float | None = None,
) -> Text:
    """Create a ManimCE Text mobject scaled responsively within dimensional limits."""
    # Normalize special characters for clean rendering
    clean = text.replace("\t", " ").strip()
    mob = Text(clean, font_size=font_size, color=color, weight=weight)
    if mob.width > max_width and max_width > 0:
        mob.scale_to_fit_width(max_width)
    if max_height and mob.height > max_height:
        mob.scale_to_fit_height(max_height)
    return mob


def create_safe_math(
    tex_str: str,
    font_size: int = 32,
    color: str = "#38BDF8",
    max_width: float = 12.0,
) -> MathTex | Text:
    """Create a MathTex mobject with automatic fallback to Text if LaTeX is unavailable."""
    clean_tex = tex_str.strip()
    try:
        mob = MathTex(clean_tex, font_size=font_size, color=color)
        if mob.width > max_width:
            mob.scale_to_fit_width(max_width)
        return mob
    except Exception as exc:
        logger.warning("LaTeX render failed for '%s' (%s); falling back to Text", clean_tex, exc)
        # Unicode fallback replacement
        fallback_str = (
            clean_tex.replace(r"\frac", "")
            .replace(r"\cdot", "·")
            .replace(r"\times", "×")
            .replace(r"\theta", "θ")
            .replace(r"\pi", "π")
            .replace(r"\approx", "≈")
            .replace(r"\sum", "∑")
            .replace(r"\int", "∫")
            .replace(r"\alpha", "α")
            .replace(r"\beta", "β")
            .replace("{", "")
            .replace("}", "")
            .replace(r"\text", "")
            .replace("\\", "")
        )
        return create_safe_text(fallback_str, font_size=font_size - 4, color=color, max_width=max_width)


# ============================================================================
# 3. Consumer: ManimCE Static Slide Scene
# ============================================================================

class StaticSlideScene(Scene):
    """Pure static ManimCE presentation slide.
    
    Adheres strictly to the static composition requirements:
    - Absolutely NO animations (`self.play`, `Write`, `Create`, `FadeIn`, etc.).
    - Uses only `self.add()`, `VGroup`, `Text`, `MathTex`, `RoundedRectangle`.
    - Produces a single high-definition PNG image when rendered with `-s` / `save_last_frame=True`.
    """

    def __init__(self, slide_data: StaticSlideData | None = None, **kwargs: Any) -> None:
        self.slide = slide_data or self._default_sample_slide()
        super().__init__(**kwargs)

    @staticmethod
    def _default_sample_slide() -> StaticSlideData:
        return StaticSlideData(
            slide_num=1,
            total_slides=1,
            topic="Bayesian Inference",
            title="Bayes' Theorem: Prior to Posterior",
            subtitle="How new empirical evidence systematically updates our degree of belief",
            layout="formula_focus",
            blocks=[
                ContentBlock(
                    block_type="equation",
                    equation=r"P(A|B) = \frac{P(B|A) \cdot P(A)}{P(B)}",
                    title="Fundamental Formulation",
                ),
                ContentBlock(
                    block_type="bullets",
                    title="Component Definitions",
                    items=[
                        "P(A|B): Posterior probability of hypothesis A given observation B",
                        "P(B|A): Likelihood of observing evidence B under hypothesis A",
                        "P(A): Prior probability of hypothesis A before evidence",
                        "P(B): Marginal evidence probability acting as normalizing constant",
                    ],
                ),
            ],
            narration=NarrationSpec(
                script=(
                    "Bayes' theorem is the cornerstone of modern probabilistic reasoning. "
                    "It specifies how an initial prior degree of belief P(A) is scaled by "
                    "the likelihood of observing the evidence P(B|A), yielding our updated "
                    "posterior belief P(A|B)."
                ),
                speaker_notes=(
                    "Key Takeaway: The posterior is proportional to Prior × Likelihood. "
                    "Notice that P(B) acts purely as a normalizing constant to ensure probabilities sum to 1."
                ),
                key_terms=["Prior", "Likelihood", "Posterior", "Normalizing Constant"],
            ),
        )

    def construct(self) -> None:
        """Compose the complete slide statically using only self.add()."""
        style = self.slide.style
        self.camera.background_color = style.background_color

        root_group = VGroup()

        # --------------------------------------------------------------------
        # 1. Header Section: Topic Badge, Title, Subtitle, Divider
        # --------------------------------------------------------------------
        header_group = self._build_header(style)
        root_group.add(header_group)

        # --------------------------------------------------------------------
        # 2. Main Content Canvas: Layout-Specific Content Cards
        # --------------------------------------------------------------------
        body_group = self._build_body(style)
        root_group.add(body_group)

        # --------------------------------------------------------------------
        # 3. Narration & Speaker-Notes Footer Panel
        # --------------------------------------------------------------------
        footer_group = self._build_footer(style)
        root_group.add(footer_group)

        # Add everything to the scene at once — PURE STATIC COMPOSITION
        self.add(root_group)

    # ------------------------------------------------------------------------
    # Header Builder
    # ------------------------------------------------------------------------
    def _build_header(self, style: SlideStyle) -> VGroup:
        header = VGroup()

        # Category / Topic Pill Badge
        badge_text = Text(
            f"{self.slide.topic.upper()}  •  SLIDE {self.slide.slide_num}/{self.slide.total_slides}",
            font_size=12,
            color=style.primary_color,
            weight="BOLD",
        )
        badge_box = RoundedRectangle(
            width=badge_text.width + 0.4,
            height=0.35,
            corner_radius=0.08,
            color=style.primary_color,
            stroke_width=1.5,
            fill_color=style.card_bg_color,
            fill_opacity=0.8,
        )
        badge = VGroup(badge_box, badge_text)

        # Title
        title_mob = create_safe_text(
            self.slide.title,
            font_size=32,
            color=style.text_color,
            weight="BOLD",
            max_width=12.6,
        )

        header_items = [badge, title_mob]

        # Optional Subtitle
        if self.slide.subtitle:
            sub_mob = create_safe_text(
                self.slide.subtitle,
                font_size=16,
                color=style.muted_text_color,
                max_width=12.6,
            )
            header_items.append(sub_mob)

        # Subtle separator line
        div_line = Line(
            LEFT * 6.6,
            RIGHT * 6.6,
            color=style.card_border_color,
            stroke_width=1.0,
        )
        header_items.append(div_line)

        header = VGroup(*header_items).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        header.to_edge(UP, buff=0.35)
        return header

    # ------------------------------------------------------------------------
    # Body Builder
    # ------------------------------------------------------------------------
    def _build_body(self, style: SlideStyle) -> VGroup:
        layout = self.slide.layout

        if layout == "two_column":
            return self._build_two_column_layout(style)
        elif layout == "card_grid":
            return self._build_card_grid_layout(style)
        else:
            return self._build_standard_or_formula_layout(style)

    def _build_standard_or_formula_layout(self, style: SlideStyle) -> VGroup:
        """Standard layout with primary formula focus and bullet cards."""
        body = VGroup()

        # Find equation block if any
        eq_block = next((b for b in self.slide.blocks if b.block_type == "equation"), None)
        other_blocks = [b for b in self.slide.blocks if b != eq_block]

        # 1. Primary Equation Card (if present)
        if eq_block and eq_block.equation:
            eq_card = self._create_equation_card(eq_block, style, width=13.0, height=1.35)
            body.add(eq_card)

        # 2. Content & Bullets Card
        bullets_to_show: list[str] = []
        card_title = "Core Principles & Structure"
        for b in other_blocks:
            if b.title and card_title == "Core Principles & Structure":
                card_title = b.title
            bullets_to_show.extend(b.items)

        if not bullets_to_show and not eq_block:
            bullets_to_show = ["Key concept formulation and analytical insight."]

        if bullets_to_show:
            bullet_card = self._create_bullet_card(
                title=card_title,
                items=bullets_to_show[:4],
                style=style,
                width=13.0,
                max_height=2.2 if eq_block else 3.5,
            )
            body.add(bullet_card)

        body.arrange(DOWN, buff=0.25)
        body.move_to(ORIGIN).shift(UP * 0.25)
        return body

    def _build_two_column_layout(self, style: SlideStyle) -> VGroup:
        """Two balanced cards side-by-side."""
        blocks = self.slide.blocks
        left_block = blocks[0] if len(blocks) > 0 else ContentBlock(items=["Left column concept"])
        right_block = blocks[1] if len(blocks) > 1 else ContentBlock(items=["Right column concept"])

        col_width = 6.35
        left_card = self._create_block_card(left_block, style, width=col_width, height=3.6)
        right_card = self._create_block_card(right_block, style, width=col_width, height=3.6)

        two_col = VGroup(left_card, right_card).arrange(RIGHT, buff=0.3)
        two_col.move_to(ORIGIN).shift(UP * 0.25)
        return two_col

    def _build_card_grid_layout(self, style: SlideStyle) -> VGroup:
        """3-card horizontal grid for sequential or multi-component concepts."""
        blocks = self.slide.blocks[:3]
        if not blocks:
            blocks = [ContentBlock(title=f"Aspect {i+1}", items=["Core insight"]) for i in range(3)]

        card_width = 4.1
        cards = []
        for b in blocks:
            c = self._create_block_card(b, style, width=card_width, height=3.5)
            cards.append(c)

        grid = VGroup(*cards).arrange(RIGHT, buff=0.25)
        grid.move_to(ORIGIN).shift(UP * 0.25)
        return grid

    # ------------------------------------------------------------------------
    # Card Primitives
    # ------------------------------------------------------------------------
    def _create_equation_card(
        self,
        block: ContentBlock,
        style: SlideStyle,
        width: float,
        height: float,
    ) -> VGroup:
        bg = RoundedRectangle(
            width=width,
            height=height,
            corner_radius=0.15,
            color=style.accent_color,
            stroke_width=1.5,
            fill_color=style.card_bg_color,
            fill_opacity=0.6,
        )

        elements = []
        if block.title:
            lbl = Text(block.title.upper(), font_size=12, color=style.accent_color, weight="BOLD")
            elements.append(lbl)

        eq_mob = create_safe_math(block.equation or "", font_size=36, color=style.primary_color, max_width=width - 0.8)
        elements.append(eq_mob)

        content = VGroup(*elements).arrange(DOWN, buff=0.15).move_to(bg.get_center())
        return VGroup(bg, content)

    def _create_bullet_card(
        self,
        title: str,
        items: list[str],
        style: SlideStyle,
        width: float,
        max_height: float,
    ) -> VGroup:
        bg = RoundedRectangle(
            width=width,
            height=max_height,
            corner_radius=0.15,
            color=style.card_border_color,
            stroke_width=1.0,
            fill_color=style.card_bg_color,
            fill_opacity=0.5,
        )

        card_content = VGroup()
        if title:
            t_mob = Text(title, font_size=15, color=style.secondary_color, weight="BOLD")
            card_content.add(t_mob)

        bullet_lines = []
        for item in items:
            # Bullet icon / marker
            dot = Text("•", font_size=18, color=style.primary_color)
            txt = create_safe_text(item, font_size=15, color=style.text_color, max_width=width - 1.2)
            line = VGroup(dot, txt).arrange(RIGHT, buff=0.18, aligned_edge=UP)
            bullet_lines.append(line)

        if bullet_lines:
            bullets_group = VGroup(*bullet_lines).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
            card_content.add(bullets_group)

        card_content.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        if card_content.height > max_height - 0.4:
            card_content.scale_to_fit_height(max_height - 0.4)
        card_content.move_to(bg.get_center()).align_to(bg, LEFT).shift(RIGHT * 0.4)

        return VGroup(bg, card_content)

    def _create_block_card(
        self,
        block: ContentBlock,
        style: SlideStyle,
        width: float,
        height: float,
    ) -> VGroup:
        bg = RoundedRectangle(
            width=width,
            height=height,
            corner_radius=0.15,
            color=style.card_border_color,
            stroke_width=1.2,
            fill_color=style.card_bg_color,
            fill_opacity=0.6,
        )

        content = VGroup()
        if block.title:
            t_mob = Text(block.title, font_size=16, color=style.primary_color, weight="BOLD")
            content.add(t_mob)

        if block.equation:
            eq = create_safe_math(block.equation, font_size=26, color=style.accent_color, max_width=width - 0.6)
            content.add(eq)

        bullet_lines = []
        for item in block.items[:5]:
            dot = Text("•", font_size=15, color=style.secondary_color)
            txt = create_safe_text(item, font_size=14, color=style.text_color, max_width=width - 0.9)
            line = VGroup(dot, txt).arrange(RIGHT, buff=0.15, aligned_edge=UP)
            bullet_lines.append(line)

        if bullet_lines:
            content.add(VGroup(*bullet_lines).arrange(DOWN, aligned_edge=LEFT, buff=0.14))

        content.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        if content.height > height - 0.5:
            content.scale_to_fit_height(height - 0.5)
        content.move_to(bg.get_center())

        return VGroup(bg, content)

    # ------------------------------------------------------------------------
    # Footer Builder: Visible On-Slide Narration & Speaker Notes Panel
    # ------------------------------------------------------------------------
    def _build_footer(self, style: SlideStyle) -> VGroup:
        card_width = 13.0
        card_height = 1.25

        bg = RoundedRectangle(
            width=card_width,
            height=card_height,
            corner_radius=0.15,
            color=style.card_border_color,
            stroke_width=1.0,
            fill_color=style.note_bg_color,
            fill_opacity=0.85,
        )

        # Presenter Note Header Tag
        tag_text = Text("SPEAKER NOTE & NARRATION", font_size=11, color=style.accent_color, weight="BOLD")
        
        # Display either explicit speaker notes or a clean summary of the script
        note_str = self.slide.narration.speaker_notes or self.slide.narration.script
        wrapped = textwrap.fill(note_str.strip(), width=105)

        note_mob = Text(
            wrapped,
            font_size=13,
            color=style.text_color,
            line_spacing=1.15,
        )
        if note_mob.width > card_width - 0.8:
            note_mob.scale_to_fit_width(card_width - 0.8)
        if note_mob.height > card_height - 0.45:
            note_mob.scale_to_fit_height(card_height - 0.45)

        content = VGroup(tag_text, note_mob).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        content.move_to(bg.get_center()).align_to(bg, LEFT).shift(RIGHT * 0.35)

        footer = VGroup(bg, content)
        footer.to_edge(DOWN, buff=0.3)
        return footer


# ============================================================================
# 4. Consumer: Static Renderer Execution
# ============================================================================

class StaticSlideConsumer:
    """Consumes structured `StaticSlideData` and renders static PNG images."""

    def __init__(self, quality: str = "medium_quality") -> None:
        # Manim quality mappings: "low_quality" (480p), "medium_quality" (720p), "high_quality" (1080p)
        self.quality = quality

    def render_slide(
        self,
        slide_data: StaticSlideData,
        output_dir: Path,
        stem: str | None = None,
    ) -> StaticSlideResult:
        """Render a single static slide to a PNG image and write narration files.
        
        Outputs:
        - `{output_dir}/{stem}.png`: The static slide image.
        - `{output_dir}/{stem}_narration.json`: Structured narration metadata.
        - `{output_dir}/{stem}_narration.txt`: Plain text script for easy presenter reading.
        - `{output_dir}/{stem}_scene.py`: Reproducible standalone ManimCE source code.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        file_stem = stem or f"slide_{slide_data.slide_num:02d}"
        image_dest = output_dir / f"{file_stem}.png"
        narration_json_dest = output_dir / f"{file_stem}_narration.json"
        narration_txt_dest = output_dir / f"{file_stem}_narration.txt"
        scene_py_dest = output_dir / f"{file_stem}_scene.py"

        # 1. Export Narration Files
        narration_dict = {
            "slide_num": slide_data.slide_num,
            "total_slides": slide_data.total_slides,
            "topic": slide_data.topic,
            "title": slide_data.title,
            "subtitle": slide_data.subtitle,
            "narration_script": slide_data.narration.script,
            "speaker_notes": slide_data.narration.speaker_notes,
            "key_terms": slide_data.narration.key_terms,
        }
        narration_json_dest.write_text(json.dumps(narration_dict, indent=2), encoding="utf-8")
        
        narration_txt_content = (
            f"SLIDE {slide_data.slide_num}: {slide_data.title}\n"
            f"Topic: {slide_data.topic}\n"
            f"{'='*60}\n\n"
            f"SPOKEN NARRATION:\n{slide_data.narration.script}\n\n"
            f"SPEAKER NOTES / KEY TAKEAWAYS:\n{slide_data.narration.speaker_notes}\n"
        )
        narration_txt_dest.write_text(narration_txt_content, encoding="utf-8")

        # 2. Export Standalone Reproducible Python Code
        slide_dict_repr = repr(slide_data.model_dump())
        standalone_code = (
            "# Standalone Static Presentation Slide\n"
            "# Generated by AOS Static Slide Producer-Consumer Engine\n"
            "import sys\n"
            "from pathlib import Path\n"
            "repo_root = Path(__file__).resolve().parents[2]\n"
            "if str(repo_root) not in sys.path:\n"
            "    sys.path.insert(0, str(repo_root))\n\n"
            "from manim import *\n"
            "from apps.agents.static_slide_engine import StaticSlideScene, StaticSlideData\n\n"
            f"slide_spec = StaticSlideData.model_validate({slide_dict_repr})\n\n"
            "class SlideScene(StaticSlideScene):\n"
            "    def __init__(self, **kwargs):\n"
            "        super().__init__(slide_data=slide_spec, **kwargs)\n\n"
            f"# Render via CLI with:\n"
            f"# manim -s -qm --format png {scene_py_dest.name} SlideScene\n"
        )
        scene_py_dest.write_text(standalone_code, encoding="utf-8")

        # 3. Render Static PNG Image using ManimCE
        try:
            with tempconfig({
                "media_dir": str(output_dir),
                "quality": self.quality,
                "save_last_frame": True,
                "format": "png",
                "output_file": file_stem,
                "verbosity": "WARNING",
            }):
                scene = StaticSlideScene(slide_data=slide_data)
                scene.render()

            # Find the written PNG file
            if not image_dest.is_file():
                for candidate in output_dir.rglob(f"*{file_stem}*.png"):
                    if candidate.is_file() and candidate.resolve() != image_dest.resolve():
                        shutil.copy2(candidate, image_dest)
                        break

            if image_dest.is_file() and image_dest.stat().st_size > 0:
                logger.info("Successfully rendered static slide: %s", image_dest)
                return StaticSlideResult(
                    slide_num=slide_data.slide_num,
                    image_path=str(image_dest.resolve()),
                    narration_json_path=str(narration_json_dest.resolve()),
                    narration_txt_path=str(narration_txt_dest.resolve()),
                    code_path=str(scene_py_dest.resolve()),
                    success=True,
                )
            else:
                return StaticSlideResult(
                    slide_num=slide_data.slide_num,
                    image_path=str(image_dest),
                    narration_json_path=str(narration_json_dest),
                    narration_txt_path=str(narration_txt_dest),
                    code_path=str(scene_py_dest),
                    success=False,
                    error="Render did not produce a valid PNG image",
                )

        except Exception as exc:
            logger.exception("Error rendering static slide %d", slide_data.slide_num)
            return StaticSlideResult(
                slide_num=slide_data.slide_num,
                image_path=str(image_dest),
                narration_json_path=str(narration_json_dest),
                narration_txt_path=str(narration_txt_dest),
                code_path=str(scene_py_dest),
                success=False,
                error=str(exc),
            )


# ============================================================================
# 5. Producer: Structured Slide Generator
# ============================================================================

class StaticSlideProducer:
    """Generates structured presentation slide specifications from topics or queries."""

    @staticmethod
    def create_lesson_slides(topic: str, total_slides: int = 3) -> list[StaticSlideData]:
        """Programmatically generate a sequence of structured slides for a given topic."""
        clean_topic = topic.strip().title()

        slides: list[StaticSlideData] = []

        # Slide 1: Foundations & Formulation
        slides.append(
            StaticSlideData(
                slide_num=1,
                total_slides=total_slides,
                topic=clean_topic,
                title=f"Core Foundations of {clean_topic}",
                subtitle="Theoretical framework and fundamental mathematical definition",
                layout="formula_focus",
                blocks=[
                    ContentBlock(
                        block_type="equation",
                        title="Governing Equation",
                        equation=r"\mathcal{L}(\theta) = \mathbb{E}_{x \sim \mathcal{D}} \left[ \log p_\theta(x) \right]",
                    ),
                    ContentBlock(
                        block_type="bullets",
                        title="Essential Principles",
                        items=[
                            "Defines the analytical objective over the observation domain",
                            "Maximizes parameter likelihood under empirical data distribution",
                            "Provides strong asymptotic consistency and convergence guarantees",
                        ],
                    ),
                ],
                narration=NarrationSpec(
                    script=(
                        f"Welcome to our lecture on {clean_topic}. We begin by establishing the "
                        "primary governing equation. Our objective is to evaluate parameters "
                        "that maximize the expected log-likelihood across the underlying distribution."
                    ),
                    speaker_notes=(
                        "Emphasize the role of the expectation operator. Note how data distribution "
                        "D determines empirical sample convergence."
                    ),
                    key_terms=["Expectation", "Log-Likelihood", "Parameters", "Data Distribution"],
                ),
            )
        )

        # Slide 2: Structural Mechanics (Two-Column Comparison)
        if total_slides >= 2:
            slides.append(
                StaticSlideData(
                    slide_num=2,
                    total_slides=total_slides,
                    topic=clean_topic,
                    title="System Mechanics & Components",
                    subtitle="Comparative analysis of forward dynamics vs optimization constraints",
                    layout="two_column",
                    blocks=[
                        ContentBlock(
                            block_type="bullets",
                            title="Forward Dynamics",
                            items=[
                                "Propagates signal through functional transformations",
                                "Maintains information density across state transitions",
                                "Preserves gradient norms for stable optimization",
                            ],
                        ),
                        ContentBlock(
                            block_type="bullets",
                            title="Optimization Constraints",
                            items=[
                                "Constrains parameter divergence via regularizers",
                                "Controls computational complexity and memory bounds",
                                "Ensures uniform generalization to unobserved test cases",
                            ],
                        ),
                    ],
                    narration=NarrationSpec(
                        script=(
                            "Turning to the structural mechanics, we contrast the forward dynamics "
                            "against the optimization constraints. While forward propagation preserves "
                            "information density, regularization bounds prevent overfitting."
                        ),
                        speaker_notes=(
                            "Contrast the left and right cards: signal preservation versus "
                            "inductive bias control."
                        ),
                        key_terms=["Forward Dynamics", "Optimization Constraints", "Regularization"],
                    ),
                )
            )

        # Slide 3: Synthesis & Practical Applications
        if total_slides >= 3:
            slides.append(
                StaticSlideData(
                    slide_num=3,
                    total_slides=total_slides,
                    topic=clean_topic,
                    title="Synthesis & Pedagogical Takeaways",
                    subtitle="Key insights, operational trade-offs, and real-world deployment",
                    layout="standard",
                    blocks=[
                        ContentBlock(
                            block_type="bullets",
                            title="Summary of Takeaways",
                            items=[
                                "Unified Framework: Synthesizes theoretical modeling with computational scale",
                                "Efficiency Trade-off: Balances convergence rate against per-step resource budget",
                                "Robustness Guarantee: Retains stability under real-world noise and shift",
                                "Implementation Vector: Deploys cleanly with vector-accelerated backends",
                            ],
                        )
                    ],
                    narration=NarrationSpec(
                        script=(
                            f"To conclude our review of {clean_topic}, we observe that balancing "
                            "theoretical rigor with computational efficiency yields robust real-world "
                            "performance across diverse problem domains."
                        ),
                        speaker_notes=(
                            "Review all four takeaways. Invite students to consider how hardware "
                            "acceleration changes the efficiency trade-off."
                        ),
                        key_terms=["Synthesis", "Robustness", "Efficiency", "Vector Acceleration"],
                    ),
                )
            )

        return slides

    @classmethod
    def generate_with_llm(
        cls,
        prompt: str,
        total_slides: int = 3,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> list[StaticSlideData]:
        """Generate tailored presentation slides via an LLM with fallback to structured presets."""
        try:
            from keyframe_engine import get_llm_client, execute_completion_with_fallback

            client, effective_model = get_llm_client(base_url=base_url, api_key=api_key, model=model)

            system_prompt = (
                "You are an expert pedagogical presentation designer. Create clean, structured "
                f"presentation slides for the user's topic. Generate exactly {total_slides} slides.\n"
                "Return a valid JSON object matching this schema:\n"
                "{\n"
                '  "slides": [\n'
                "    {\n"
                '      "slide_num": 1,\n'
                f'      "total_slides": {total_slides},\n'
                '      "topic": "Concise Topic Name",\n'
                '      "title": "Clear Slide Title",\n'
                '      "subtitle": "Informative Subtitle",\n'
                '      "layout": "formula_focus" | "two_column" | "standard" | "card_grid",\n'
                '      "blocks": [\n'
                '        {"block_type": "equation", "title": "Equation Name", "equation": "LaTeX formula"},\n'
                '        {"block_type": "bullets", "title": "Section Title", "items": ["Bullet 1", "Bullet 2"]}\n'
                "      ],\n"
                '      "narration": {\n'
                '        "script": "Full educational explanation to be read by narrator.",\n'
                '        "speaker_notes": "Key takeaway summary visible on the slide.",\n'
                '        "key_terms": ["Term1", "Term2"]\n'
                "      }\n"
                "    }\n"
                "  ]\n"
                "}\n"
                "Do NOT use markdown code fences in the JSON output if possible."
            )

            user_msg = f"Create a {total_slides}-slide structured educational presentation on: {prompt}"

            resp = execute_completion_with_fallback(
                client=client,
                primary_model=effective_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                timeout=30.0,
            )

            raw = resp.choices[0].message.content or ""
            # Strip markdown fences if present
            m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
            clean_json = m.group(1).strip() if m else raw.strip()

            parsed = json.loads(clean_json)
            slide_list = parsed.get("slides", [])
            if slide_list and isinstance(slide_list, list):
                result_slides = [StaticSlideData.model_validate(s) for s in slide_list[:total_slides]]
                if result_slides:
                    logger.info("Successfully generated %d slides using LLM (%s)", len(result_slides), effective_model)
                    return result_slides

        except Exception as exc:
            logger.warning("LLM slide generation fallback to templates (%s)", exc)

        return cls.create_lesson_slides(prompt, total_slides=total_slides)


# ============================================================================
# 6. High-Level Engine Coordinator
# ============================================================================

def run_static_slide_pipeline(
    topic: str,
    output_dir: str | Path,
    total_slides: int = 3,
    quality: str = "medium_quality",
    use_llm: bool = True,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Run the complete end-to-end static slide generation pipeline.
    
    1. Producer emits structured `StaticSlideData` list (via LLM or template presets).
    2. Consumer validates and renders each slide to a high-definition PNG.
    3. Exports accompanying narration scripts and reproducible ManimCE code files.
    4. Returns a detailed manifest of all rendered artifacts.
    """
    out_path = Path(output_dir).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Producer Phase
    producer = StaticSlideProducer()
    if use_llm:
        slides_data = producer.generate_with_llm(
            prompt=topic,
            total_slides=total_slides,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
    else:
        slides_data = producer.create_lesson_slides(topic, total_slides=total_slides)

    # 2. Consumer Phase
    consumer = StaticSlideConsumer(quality=quality)
    results: list[StaticSlideResult] = []

    for slide in slides_data:
        res = consumer.render_slide(slide, output_dir=out_path)
        results.append(res)

    manifest = {
        "ok": all(r.success for r in results),
        "topic": topic,
        "mode": "static_slides",
        "output_dir": str(out_path),
        "total_slides": len(results),
        "slides": [r.model_dump() for r in results],
        "image_files": [r.image_path for r in results if r.success],
        "narration_files": [r.narration_json_path for r in results],
    }

    manifest_file = out_path / "slides_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    test_out = Path("workspace/static_slides_demo")
    result = run_static_slide_pipeline("Bayes' Theorem", output_dir=test_out, total_slides=2)
    print("Static slide pipeline finished:")
    print(json.dumps(result, indent=2))
