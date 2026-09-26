"""Marp to Manim Compiler — Deterministic AST parsing and layout-dispatch engine.

Bridges declarative Marp presentation markdown to executable Manim Community Edition code
using a fixed, robust 6-archetype layout vocabulary:
1. 'title'       -> Prominent centered header, subtitle, branding/topic footer.
2. 'bullets'     -> Header anchored to UP, sequential BulletedList with FadeIn(shift=UP).
3. 'two-col'     -> Dual VGroups split at screen x=0 (left at x=-3.5, right at x=3.5).
4. 'code-focus'  -> Header + syntax-highlighted Code mobject with container window.
5. 'math-focus'  -> Header + prominent MathTex expressions with step-by-step Write.
6. 'quote'       -> Stylized italic quote text with author attribution.

Operates deterministically in <50ms without hallucination risk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

import markdown_it
from markdown_it.token import Token


# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class MarpSlide:
    """Structured representation of a single Marp slide extracted from AST."""
    index: int
    layout: str = "bullets"               # "title" | "bullets" | "two-col" | "code-focus" | "math-focus" | "quote"
    title: str = ""
    subtitle: str | None = None
    bullets: list[str] = field(default_factory=list)
    code: str | None = None
    code_lang: str = "python"
    math_equations: list[str] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    col1_items: list[str] = field(default_factory=list)
    col2_items: list[str] = field(default_factory=list)
    quote_text: str | None = None
    quote_author: str | None = None
    voiceover: str | None = None
    theme: str | None = None
    header: str | None = None
    footer: str | None = None


@dataclass
class MarpCompilerResult:
    """Result of compiling a Marp presentation into Manim Python code."""
    code: str
    slides: list[MarpSlide]
    scene_name: str
    slide_count: int
    target: Literal["video", "slides"] = "video"


# ── Parser & Layout Extractor ─────────────────────────────────────────────────

class MarpParser:
    """Parses Marp presentation markdown into structured MarpSlide models using markdown-it-py."""

    def __init__(self) -> None:
        self.md = markdown_it.MarkdownIt("commonmark", {"breaks": True, "html": True})

    def parse(self, marp_text: str) -> list[MarpSlide]:
        """Parse Marp markdown text into an ordered list of MarpSlide instances."""
        cleaned_text = marp_text.replace("\r\n", "\n")
        global_meta, raw_slides = self._extract_frontmatter_and_slides(cleaned_text)

        slides: list[MarpSlide] = []
        for idx, raw_content in enumerate(raw_slides):
            slide = self._parse_slide(idx + 1, raw_content, global_meta if idx == 0 else {})
            if slide:
                slides.append(slide)

        if not slides:
            slides.append(MarpSlide(index=1, layout="title", title="Marp Presentation"))

        return slides

    def _extract_frontmatter_and_slides(self, text: str) -> tuple[dict[str, str], list[str]]:
        """Extract top-level frontmatter and split remaining slides by standard Marp dividers (---)."""
        content = text.strip()
        global_meta: dict[str, str] = {}

        # If document starts with YAML frontmatter bounded by --- ... ---
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", content, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    global_meta[k.strip().lower()] = v.strip().strip('"\'')
            content = content[fm_match.end():].strip()

        parts = re.split(r"(?m)^---\s*$", content)
        slide_parts = [p.strip() for p in parts if p.strip()]
        return global_meta, slide_parts

    def _parse_slide(self, index: int, raw_text: str, default_meta: dict[str, str] | None = None) -> MarpSlide | None:
        """Parse raw slide markdown into a MarpSlide object."""
        slide = MarpSlide(index=index)

        # Apply global frontmatter defaults if available
        if default_meta:
            if "voiceover" in default_meta and not slide.voiceover:
                slide.voiceover = default_meta["voiceover"]
            if "theme" in default_meta and not slide.theme:
                slide.theme = default_meta["theme"]
            if "header" in default_meta and not slide.header:
                slide.header = default_meta["header"]
            if "footer" in default_meta and not slide.footer:
                slide.footer = default_meta["footer"]

        # 1. Extract HTML comment directives like <!-- _class: two-col -->
        directive_matches = re.findall(r"<!--\s*_?class:\s*([\w\-]+)\s*-->", raw_text, re.IGNORECASE)
        if directive_matches:
            slide.layout = directive_matches[0].lower().strip()

        # 2. Extract YAML-like frontmatter key-value pairs if present
        lines = raw_text.splitlines()
        remaining_lines: list[str] = []

        for line in lines:
            line_str = line.strip()
            if line_str.startswith("layout:"):
                layout_val = line_str.split(":", 1)[1].strip().strip('"\'')
                slide.layout = layout_val.lower()
                continue
            if line_str.startswith("voiceover:"):
                slide.voiceover = line_str.split(":", 1)[1].strip().strip('"\'')
                continue
            if line_str.startswith("theme:"):
                slide.theme = line_str.split(":", 1)[1].strip().strip('"\'')
                continue
            if line_str.startswith("title:") and not slide.title:
                slide.title = line_str.split(":", 1)[1].strip().strip('"\'')
                continue
            if line_str.startswith(("marp:", "paginate:", "size:", "header:", "footer:", "style:", "math:", "_header:", "_footer:")):
                continue
            if line_str.startswith("<!--") and "-->" in line_str:
                continue
            remaining_lines.append(line)

        body_text = "\n".join(remaining_lines).strip()
        if not body_text and not slide.title:
            return None

        # 3. Parse AST tokens using markdown-it
        tokens: list[Token] = self.md.parse(body_text)

        i = 0
        while i < len(tokens):
            token = tokens[i]

            # Headings
            if token.type == "heading_open":
                tag = token.tag
                inline_content = ""
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    inline_content = tokens[i + 1].content.strip()
                if tag in ("h1", "h2") and not slide.title:
                    slide.title = inline_content
                elif not slide.subtitle:
                    slide.subtitle = inline_content
                elif not slide.title:
                    slide.title = inline_content
                i += 2
                continue

            # Fenced Code Blocks
            if token.type == "fence":
                slide.code = token.content.rstrip()
                slide.code_lang = token.info.strip() or "python"
                if slide.layout not in ("two-col", "quote"):
                    slide.layout = "code-focus"
                i += 1
                continue

            # Blockquotes
            if token.type == "blockquote_open":
                quote_lines: list[str] = []
                j = i + 1
                while j < len(tokens) and tokens[j].type != "blockquote_close":
                    if tokens[j].type == "inline":
                        quote_lines.append(tokens[j].content.strip())
                    j += 1
                full_quote = " ".join(quote_lines)
                author_match = re.search(r"[—\-]\s*(.+)$", full_quote)
                if author_match:
                    slide.quote_author = author_match.group(1).strip()
                    slide.quote_text = full_quote[:author_match.start()].strip()
                else:
                    slide.quote_text = full_quote
                slide.layout = "quote"
                i = j + 1
                continue

            # Bullet Lists
            if token.type == "bullet_list_open":
                j = i + 1
                current_item = ""
                while j < len(tokens) and tokens[j].type != "bullet_list_close":
                    if tokens[j].type == "inline":
                        current_item = tokens[j].content.strip()
                    elif tokens[j].type == "list_item_close":
                        if current_item:
                            slide.bullets.append(current_item)
                            current_item = ""
                    j += 1
                i = j + 1
                continue

            # Paragraphs
            if token.type == "paragraph_open":
                if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                    p_content = tokens[i + 1].content.strip()
                    math_matches = re.findall(r"\${1,2}([^$]+)\${1,2}", p_content)
                    if math_matches and len(p_content) < len(math_matches[0]) + 10:
                        slide.math_equations.extend(math_matches)
                        if slide.layout not in ("two-col", "code-focus"):
                            slide.layout = "math-focus"
                    elif p_content:
                        slide.paragraphs.append(p_content)
                i += 2
                continue

            i += 1

        # 4. Auto-detect layout if still default
        slide.layout = self._infer_layout(slide)

        # 5. Populate two-col columns if layout is two-col
        if slide.layout == "two-col":
            self._split_two_columns(slide)

        return slide

    def _infer_layout(self, slide: MarpSlide) -> str:
        """Infer best layout archetype if not explicitly set."""
        if slide.layout in ("two-col", "code-focus", "math-focus", "quote", "title", "bullets"):
            return slide.layout

        if slide.index == 1 and not slide.bullets and not slide.code:
            return "title"
        if slide.code:
            return "code-focus"
        if slide.math_equations and not slide.bullets:
            return "math-focus"
        if slide.quote_text:
            return "quote"
        if slide.bullets:
            return "bullets"
        return "bullets"

    def _split_two_columns(self, slide: MarpSlide) -> None:
        """Split bullets or paragraphs into left and right column lists."""
        all_items = list(slide.bullets) if slide.bullets else list(slide.paragraphs)
        if not all_items:
            slide.col1_items = ["Column 1 Content"]
            slide.col2_items = ["Column 2 Content"]
            return

        mid = (len(all_items) + 1) // 2
        slide.col1_items = all_items[:mid]
        slide.col2_items = all_items[mid:]


# ── Manim Code Emitter ────────────────────────────────────────────────────────

class MarpManimCompiler:
    """Compiles parsed MarpSlide representations into executable Manim Community Python code."""

    def __init__(self, parser: MarpParser | None = None) -> None:
        self.parser = parser or MarpParser()

    def compile(
        self,
        marp_text: str,
        scene_name: str = "MarpLectureScene",
        target: Literal["video", "slides"] = "video",
    ) -> MarpCompilerResult:
        """Parse Marp markdown and emit complete Manim Community Edition code."""
        slides = self.parser.parse(marp_text)
        code = self.emit_code(slides, scene_name=scene_name, target=target)
        return MarpCompilerResult(
            code=code,
            slides=slides,
            scene_name=scene_name,
            slide_count=len(slides),
            target=target,
        )

    def emit_code(
        self,
        slides: list[MarpSlide],
        scene_name: str = "MarpLectureScene",
        target: Literal["video", "slides"] = "video",
    ) -> str:
        """Generate the complete Manim Python source code."""
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "", scene_name)
        if not clean_name:
            clean_name = "MarpLectureScene"
        if not clean_name.endswith("Scene"):
            clean_name = f"{clean_name}Scene"

        is_slides = target == "slides"
        base_class = "Slide" if is_slides else "Scene"
        import_stmt = (
            "from manim import *\nfrom manim_slides import Slide\n"
            if is_slides
            else "from manim import *\n"
        )

        code_lines: list[str] = [
            "# Auto-generated by AOS MarpManimCompiler (Deterministic AST Engine)",
            "# Follows ManimCE Tier 1 relative layout vocabulary strictly.",
            import_stmt,
            f"class {clean_name}({base_class}):",
            "    def construct(self):",
            "        # Configure presentation screen dimensions (16:9 safe bounds)",
        ]

        for idx, slide in enumerate(slides):
            code_lines.append(f"\n        # ─── Slide {slide.index}: {slide.layout.upper()} ───")
            if slide.title:
                code_lines.append(f"        # Topic: {slide.title}")
            slide_code = self._emit_slide_code(slide, is_slides=is_slides, is_last=(idx == len(slides) - 1))
            code_lines.append(slide_code)

        code_lines.append("\n        self.wait(1.0)\n")
        return "\n".join(code_lines)

    def _emit_slide_code(self, slide: MarpSlide, is_slides: bool, is_last: bool) -> str:
        """Emit Manim code for an individual slide archetype."""
        idx = slide.index
        var_group = f"slide_{idx}_group"

        emitters = {
            "title": self._emit_title_slide,
            "bullets": self._emit_bullets_slide,
            "two-col": self._emit_two_col_slide,
            "code-focus": self._emit_code_slide,
            "math-focus": self._emit_math_slide,
            "quote": self._emit_quote_slide,
        }

        emitter = emitters.get(slide.layout, self._emit_bullets_slide)
        body = emitter(slide, var_group)

        pause_code = "        self.next_slide()\n" if is_slides else "        self.wait(2.5)\n"
        cleanup_code = (
            f"        self.play(FadeOut({var_group}))\n        self.wait(0.5)\n"
            if not is_last
            else ""
        )

        return f"{body}\n{pause_code}{cleanup_code}"

    def _emit_title_slide(self, slide: MarpSlide, var_group: str) -> str:
        title_text = self._escape_str(slide.title or "Presentation Title")
        sub_text = self._escape_str(slide.subtitle or "")
        lines = [
            f"        title_{slide.index} = Text({title_text}, font_size=48, color=BLUE_B)",
            f"        title_{slide.index}.move_to(ORIGIN + UP * 0.8)",
        ]
        if sub_text:
            lines.extend([
                f"        subtitle_{slide.index} = Text({sub_text}, font_size=28, color=GREY_B)",
                f"        subtitle_{slide.index}.next_to(title_{slide.index}, DOWN, buff=0.45)",
                f"        {var_group} = VGroup(title_{slide.index}, subtitle_{slide.index})",
                f"        self.play(Write(title_{slide.index}, run_time=1.2))",
                f"        self.play(FadeIn(subtitle_{slide.index}, shift=0.2 * UP), run_time=0.8)",
            ])
        else:
            lines.extend([
                f"        {var_group} = VGroup(title_{slide.index})",
                f"        self.play(Write(title_{slide.index}, run_time=1.2))",
            ])
        return "\n".join(lines)

    def _emit_bullets_slide(self, slide: MarpSlide, var_group: str) -> str:
        title_text = self._escape_str(slide.title or "Key Concepts")
        bullets = slide.bullets or slide.paragraphs or ["Core Insight"]
        bullet_args = ", ".join(self._escape_str(b) for b in bullets[:6])

        lines = [
            f"        title_{slide.index} = Title({title_text}, font_size=38, color=BLUE_C)",
            f"        title_{slide.index}.to_edge(UP, buff=0.5)",
            f"        bullets_{slide.index} = BulletedList({bullet_args}, font_size=28)",
            f"        bullets_{slide.index}.next_to(title_{slide.index}, DOWN, buff=0.6).to_edge(LEFT, buff=1.0)",
            f"        {var_group} = VGroup(title_{slide.index}, bullets_{slide.index})",
            f"        self.play(Write(title_{slide.index}, run_time=0.8))",
            f"        for item in bullets_{slide.index}:",
            f"            self.play(FadeIn(item, shift=0.2 * UP), run_time=0.5)",
            f"            self.wait(0.3)",
        ]
        return "\n".join(lines)

    def _emit_two_col_slide(self, slide: MarpSlide, var_group: str) -> str:
        title_text = self._escape_str(slide.title or "Comparative Overview")
        col1 = slide.col1_items or ["Left Concept 1", "Left Concept 2"]
        col2 = slide.col2_items or ["Right Concept 1", "Right Concept 2"]
        col1_args = ", ".join(self._escape_str(c) for c in col1[:4])
        col2_args = ", ".join(self._escape_str(c) for c in col2[:4])

        lines = [
            f"        title_{slide.index} = Title({title_text}, font_size=38, color=BLUE_C)",
            f"        title_{slide.index}.to_edge(UP, buff=0.5)",
            f"        col1_{slide.index} = BulletedList({col1_args}, font_size=24)",
            f"        col2_{slide.index} = BulletedList({col2_args}, font_size=24)",
            f"        col1_{slide.index}.move_to(LEFT * 3.4 + DOWN * 0.4)",
            f"        col2_{slide.index}.move_to(RIGHT * 3.4 + DOWN * 0.4)",
            f"        divider_{slide.index} = Line(UP * 2.0, DOWN * 2.6, color=GREY_C, stroke_width=1.5)",
            f"        {var_group} = VGroup(title_{slide.index}, col1_{slide.index}, col2_{slide.index}, divider_{slide.index})",
            f"        self.play(Write(title_{slide.index}, run_time=0.8))",
            f"        self.play(Create(divider_{slide.index}), run_time=0.5)",
            f"        self.play(FadeIn(col1_{slide.index}, shift=LEFT*0.3), FadeIn(col2_{slide.index}, shift=RIGHT*0.3), run_time=0.8)",
        ]
        return "\n".join(lines)

    def _emit_code_slide(self, slide: MarpSlide, var_group: str) -> str:
        title_text = self._escape_str(slide.title or "Code Walkthrough")
        raw_code = slide.code or "def main():\n    print('Hello Marp!')"
        lang = slide.code_lang or "python"

        lines = [
            f"        title_{slide.index} = Title({title_text}, font_size=38, color=BLUE_C)",
            f"        title_{slide.index}.to_edge(UP, buff=0.5)",
            f"        code_content_{slide.index} = {repr(raw_code)}",
            f"        code_box_{slide.index} = Code(",
            f"            code=code_content_{slide.index},",
            f"            language={repr(lang)},",
            f"            font_size=20,",
            f"            line_spacing=0.8,",
            f"            background='window',",
            f"            insert_line_no=True,",
            f"        ).next_to(title_{slide.index}, DOWN, buff=0.5)",
            f"        {var_group} = VGroup(title_{slide.index}, code_box_{slide.index})",
            f"        self.play(Write(title_{slide.index}, run_time=0.8))",
            f"        self.play(Create(code_box_{slide.index}), run_time=1.2)",
        ]
        return "\n".join(lines)

    def _emit_math_slide(self, slide: MarpSlide, var_group: str) -> str:
        title_text = self._escape_str(slide.title or "Mathematical Formulation")
        eqs = slide.math_equations or ["f(x) = \\sigma(W x + b)"]
        eq_raw = eqs[0]

        lines = [
            f"        title_{slide.index} = Title({title_text}, font_size=38, color=BLUE_C)",
            f"        title_{slide.index}.to_edge(UP, buff=0.5)",
            f"        formula_{slide.index} = MathTex({repr(eq_raw)}, font_size=44, color=YELLOW_B)",
            f"        formula_{slide.index}.next_to(title_{slide.index}, DOWN, buff=1.2)",
        ]
        if slide.bullets:
            bullet_args = ", ".join(self._escape_str(b) for b in slide.bullets[:3])
            lines.extend([
                f"        desc_{slide.index} = BulletedList({bullet_args}, font_size=26)",
                f"        desc_{slide.index}.next_to(formula_{slide.index}, DOWN, buff=0.8).to_edge(LEFT, buff=1.0)",
                f"        {var_group} = VGroup(title_{slide.index}, formula_{slide.index}, desc_{slide.index})",
                f"        self.play(Write(title_{slide.index}, run_time=0.8))",
                f"        self.play(Write(formula_{slide.index}, run_time=1.2))",
                f"        self.play(FadeIn(desc_{slide.index}, shift=0.2*UP), run_time=0.8)",
            ])
        else:
            lines.extend([
                f"        {var_group} = VGroup(title_{slide.index}, formula_{slide.index})",
                f"        self.play(Write(title_{slide.index}, run_time=0.8))",
                f"        self.play(Write(formula_{slide.index}, run_time=1.2))",
            ])
        return "\n".join(lines)

    def _emit_quote_slide(self, slide: MarpSlide, var_group: str) -> str:
        raw_quote = slide.quote_text or "Simplicity is the prerequisite for reliability."
        raw_author = slide.quote_author or "Edsger W. Dijkstra"

        lines = [
            f"        quote_{slide.index} = Text({repr(raw_quote)}, font='CMU Serif', font_size=32, slant=ITALIC, line_spacing=0.85)",
            f"        quote_{slide.index}.move_to(ORIGIN + UP * 0.3)",
            f"        author_{slide.index} = Text({repr(f'— {raw_author}')}, font='CMU Serif', font_size=24, color=GREY_B)",
            f"        author_{slide.index}.next_to(quote_{slide.index}, DOWN, buff=0.5).align_to(quote_{slide.index}, RIGHT)",
            f"        {var_group} = VGroup(quote_{slide.index}, author_{slide.index})",
            f"        self.play(Write(quote_{slide.index}, run_time=1.5))",
            f"        self.play(FadeIn(author_{slide.index}, shift=0.2*UP), run_time=0.6)",
        ]
        return "\n".join(lines)

    def _escape_str(self, text: str) -> str:
        """Escape text safely as a Python string literal."""
        return repr(text.strip())
