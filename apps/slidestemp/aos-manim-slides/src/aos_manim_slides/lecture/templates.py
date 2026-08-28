from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from manim import (
    BLUE,
    DOWN,
    LEFT,
    RIGHT,
    UP,
    YELLOW,
    Create,
    FadeIn,
    FadeOut,
    GrowFromCenter,
    Line,
    SurroundingRectangle,
    Text,
    Transform,
    TransformFromCopy,
    VGroup,
    Write,
)

from aos_manim_core import ThemeConfig, get_theme

from .helpers import (
    bullet_rows,
    colored_text,
    pin_top_left,
    play_bullets,
    play_column_rows,
    safe_play,
    safe_wait,
    voiceover_from_items,
)
from ..typography import slide_tex


class BrandingIntro(VGroup):
    """Opening brand mark that morphs into the lecture title (need_to_implement Branding)."""

    def __init__(
        self,
        brand: str = "AOS Manim",
        byline: str = "Computational visualization",
        lecture_title: str = "Lecture",
        subtitle: str = "",
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        self.brand = slide_tex(brand, font_size=64, color=t.primary, weight="BOLD")
        self.byline = slide_tex(byline, font_size=28, color=t.text_muted)
        pin_top_left(self.brand, up=1.2, left=0.95)
        self.byline.next_to(self.brand, DOWN, buff=0.75)
        self.byline.align_to(self.brand, LEFT)
        self.box = SurroundingRectangle(self.brand, color=t.text_main, buff=0.28)
        self.lecture_title = slide_tex(lecture_title, font_size=48, color=t.primary, weight="BOLD")
        pin_top_left(self.lecture_title, up=1.2, left=0.95)
        self.subtitle_mob = slide_tex(subtitle, font_size=28, color=t.text_muted) if subtitle else None
        if self.subtitle_mob is not None:
            self.subtitle_mob.next_to(self.lecture_title, DOWN, buff=0.85)
            self.subtitle_mob.align_to(self.lecture_title, LEFT)
        self.add(self.brand)

    def play_on(self, scene: Any) -> None:
        safe_play(scene, Write(self.brand), run_time=1.1)
        safe_wait(scene, 0.35)
        adder = getattr(scene, "add", None)
        if callable(adder):
            adder(self.byline, self.box)
        self.byline.set_opacity(0)
        safe_play(scene, FadeIn(self.byline, shift=0.2 * DOWN), Write(self.box), run_time=0.9)
        safe_wait(scene, 0.45)
        anims: list = [Transform(self.brand, self.lecture_title), FadeOut(self.box), FadeOut(self.byline)]
        if self.subtitle_mob is not None:
            if callable(adder):
                adder(self.subtitle_mob)
            self.subtitle_mob.set_opacity(0)
            anims.append(FadeIn(self.subtitle_mob, shift=0.2 * DOWN))
        safe_play(scene, *anims, run_time=1.1)
        safe_wait(scene, 0.6)


class QuoteCard(VGroup):
    """Centered quote with rule and author (need_to_implement Quote)."""

    def __init__(
        self,
        quote: str,
        author: str = "",
        theme: Optional[ThemeConfig] = None,
        font_size: int = 40,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        from ..typography import wrapped_slide_tex

        self.quote = wrapped_slide_tex(quote, font_size, 11.0, color=t.text_main)
        self.quote.shift(UP * 0.55)
        self.author = slide_tex(author, font_size=26, color=YELLOW, slant="ITALIC")
        self.author.next_to(self.quote, DOWN, buff=1.05)
        self.author.align_to(self.quote, RIGHT)
        self.rule = Line(
            self.author.get_left() + LEFT * 0.15,
            self.author.get_right() + RIGHT * 0.15,
            color=t.border,
            stroke_width=2,
        ).next_to(self.author, UP, buff=0.22)
        self.add(self.quote, self.rule, self.author)

    def play_on(self, scene: Any) -> None:
        self.rule.set_opacity(0)
        self.author.set_opacity(0)
        safe_play(scene, Write(self.quote), run_time=2.4)
        safe_wait(scene, 0.35)
        self.rule.set_opacity(1)
        safe_play(
            scene,
            GrowFromCenter(self.rule),
            FadeIn(self.author, shift=0.2 * UP),
            run_time=1.1,
        )
        safe_wait(scene, 0.8)


class DisclaimerCard(VGroup):
    """Warning title plus highlighted body lines (need_to_implement Disclaimer)."""

    def __init__(
        self,
        title: str = "Disclaimer",
        lines: Optional[Sequence[tuple[str, Dict[str, Any]]]] = None,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        self.title_mob = slide_tex(title.upper(), font_size=40, color=t.error, weight="BOLD")
        pin_top_left(self.title_mob, up=1.0, left=0.9)
        self.line_mobs = VGroup()
        default_lines = lines or [
            ("Outputs of a model require verification.", {"verification": t.success}),
            ("Do not trust them blindly.", {"blindly": t.error}),
        ]
        for text, highlights in default_lines:
            self.line_mobs.add(colored_text(text, font_size=30, theme=t, highlights=highlights))
        self.line_mobs.arrange(DOWN, buff=0.55)
        self.line_mobs.next_to(self.title_mob, DOWN, buff=1.0)
        self.line_mobs.align_to(self.title_mob, LEFT)
        self.add(self.title_mob, self.line_mobs)

    def play_on(self, scene: Any) -> None:
        for line in self.line_mobs:
            line.set_opacity(0)
        safe_play(scene, Write(self.title_mob), run_time=1.0)
        safe_wait(scene, 0.25)
        for i, line in enumerate(self.line_mobs):
            if i == 0:
                safe_play(scene, FadeIn(line, shift=0.25 * UP), run_time=0.7)
            else:
                safe_play(scene, Write(line), run_time=1.4)
            safe_wait(scene, 0.25)


class BulletBoard(VGroup):
    """Title plus sequential bullets fading in from the left (need_to_implement Slide3)."""

    def __init__(
        self,
        title: str,
        items: Sequence[str],
        theme: Optional[ThemeConfig] = None,
        font_size: int = 34,
        show_chrome: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        self.show_chrome = show_chrome
        self.title_text = title
        self.items = list(items)
        self.cue_ids = [f"li{i}" for i in range(len(self.items))]
        self.title_mob = slide_tex(title, font_size=42, color=t.primary, weight="BOLD")
        pin_top_left(self.title_mob, up=0.5, left=0.85)
        self.underline = Line(LEFT * 6.0, RIGHT * 6.0, color=t.border, stroke_width=2)
        self.underline.next_to(self.title_mob, DOWN, buff=0.18)
        self.underline.align_to(self.title_mob, LEFT)
        self.bullet_mobs = bullet_rows(items, theme=t, font_size=font_size, buff=0.5)
        if show_chrome:
            self.bullet_mobs.next_to(self.underline, DOWN, buff=0.7)
            self.bullet_mobs.align_to(self.title_mob, LEFT)
            self.add(self.title_mob, self.underline, self.bullet_mobs)
        else:
            pin_top_left(self.bullet_mobs, up=0.7, left=0.85)
            self.add(self.bullet_mobs)

    def cue_targets(self) -> dict:
        return {cid: mob for cid, mob in zip(self.cue_ids, self.bullet_mobs)}

    def voiceover_script(self) -> str:
        return voiceover_from_items(self.title_text, self.items, self.cue_ids)

    def play_title(self, scene: Any) -> None:
        if not getattr(self, "show_chrome", True):
            return
        safe_play(scene, Write(self.title_mob), FadeIn(self.underline), run_time=0.7)

    def play_item(self, scene: Any, index: int, run_time: float = 0.45) -> None:
        if 0 <= index < len(self.bullet_mobs):
            safe_play(scene, FadeIn(self.bullet_mobs[index], shift=RIGHT), run_time=run_time)

    def play_on(self, scene: Any) -> None:
        for row in self.bullet_mobs:
            row.set_opacity(0)
        self.play_title(scene)
        safe_wait(scene, 0.2)
        play_bullets(scene, self.bullet_mobs)


class TwoColumnBullets(VGroup):
    """Two bullet columns revealed row-by-row (need_to_implement TwoColumnSlide)."""

    def __init__(
        self,
        title: str,
        left_items: Sequence[str],
        right_items: Sequence[str],
        theme: Optional[ThemeConfig] = None,
        font_size: int = 30,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        self.title_text = title
        self.title_mob = slide_tex(title, font_size=40, color=t.primary, weight="BOLD")
        pin_top_left(self.title_mob, up=0.5, left=0.85)
        self.underline = Line(LEFT * 6.2, RIGHT * 6.2, color=t.border, stroke_width=1.5)
        self.underline.next_to(self.title_mob, DOWN, buff=0.18)
        self.underline.align_to(self.title_mob, LEFT)
        self.left_items = list(left_items)
        self.right_items = list(right_items)
        self.cue_ids = [f"li{i}" for i in range(max(len(left_items), len(right_items)))]
        self.left_mobs = bullet_rows(left_items, theme=t, font_size=font_size, buff=0.5)
        self.right_mobs = bullet_rows(right_items, theme=t, font_size=font_size, buff=0.5)
        cols = VGroup(self.left_mobs, self.right_mobs).arrange(RIGHT, buff=1.6, aligned_edge=UP)
        cols.next_to(self.underline, DOWN, buff=0.7)
        cols.align_to(self.title_mob, LEFT)
        self.add(self.title_mob, self.underline, cols)

    def cue_targets(self) -> dict:
        targets = {}
        for i, cid in enumerate(self.cue_ids):
            if i < len(self.left_mobs):
                targets[cid] = self.left_mobs[i]
        return targets

    def voiceover_script(self) -> str:
        spoken = []
        n = max(len(self.left_items), len(self.right_items))
        items = []
        for i in range(n):
            bits = []
            if i < len(self.left_items):
                bits.append(self.left_items[i])
            if i < len(self.right_items):
                bits.append(self.right_items[i])
            items.append(" and ".join(bits))
        return voiceover_from_items(self.title_text, items, self.cue_ids)

    def play_title(self, scene: Any) -> None:
        safe_play(scene, Write(self.title_mob), FadeIn(self.underline), run_time=0.7)

    def play_row(self, scene: Any, index: int, run_time: float = 0.5) -> None:
        anims = []
        if index < len(self.left_mobs):
            anims.append(FadeIn(self.left_mobs[index], shift=RIGHT))
        if index < len(self.right_mobs):
            anims.append(FadeIn(self.right_mobs[index], shift=RIGHT))
        if anims:
            safe_play(scene, *anims, run_time=run_time)

    def row_count(self) -> int:
        return max(len(self.left_mobs), len(self.right_mobs))

    def play_on(self, scene: Any) -> None:
        for row in self.left_mobs:
            row.set_opacity(0)
        for row in self.right_mobs:
            row.set_opacity(0)
        self.play_title(scene)
        safe_wait(scene, 0.2)
        play_column_rows(scene, list(self.left_mobs), list(self.right_mobs))


class CopyExplain(VGroup):
    """Bullets on the left; TransformFromCopy a bullet into a right-hand diagram."""

    def __init__(
        self,
        title: str,
        items: Sequence[str],
        diagrams: Sequence[Any],
        theme: Optional[ThemeConfig] = None,
        font_size: int = 30,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        self.title_mob = slide_tex(title, font_size=40, color=t.primary, weight="BOLD")
        pin_top_left(self.title_mob, up=0.5, left=0.85)
        self.bullet_mobs = bullet_rows(items, theme=t, font_size=font_size, buff=0.5)
        self.bullet_mobs.next_to(self.title_mob, DOWN, buff=0.65)
        self.bullet_mobs.align_to(self.title_mob, LEFT)
        self.cue_ids = [f"li{i}" for i in range(len(items))]
        self.diagrams = VGroup(*diagrams) if diagrams else VGroup()
        for d in self.diagrams:
            d.to_edge(RIGHT, buff=0.7)
            d.align_to(self.bullet_mobs, UP)
        self.add(self.title_mob, self.bullet_mobs, *list(self.diagrams))

    def play_title(self, scene: Any) -> None:
        safe_play(scene, Write(self.title_mob), run_time=0.6)

    def play_all_bullets(self, scene: Any) -> None:
        play_bullets(scene, self.bullet_mobs)

    def play_item(self, scene: Any, index: int, run_time: float = 0.4) -> None:
        if 0 <= index < len(self.bullet_mobs):
            safe_play(scene, FadeIn(self.bullet_mobs[index], shift=RIGHT), run_time=run_time)

    def play_copy(self, scene: Any, index: int, run_time: float = 0.9) -> None:
        if index >= len(self.bullet_mobs) or index >= len(self.diagrams):
            return
        src = self.bullet_mobs[index]
        dest = self.diagrams[index]
        dest.set_opacity(1)
        safe_play(scene, TransformFromCopy(src, dest), run_time=run_time)

    def play_on(self, scene: Any) -> None:
        for d in self.diagrams:
            d.set_opacity(0)
        self.play_title(scene)
        self.play_all_bullets(scene)
        for i in range(min(len(self.bullet_mobs), len(self.diagrams))):
            self.play_copy(scene, i)
            safe_wait(scene, 0.4)
            if i + 1 < len(self.diagrams):
                safe_play(scene, FadeOut(self.diagrams[i]), run_time=0.35)


class CodeReveal(VGroup):
    """Create a code listing, then optional line highlights (need_to_implement CodeWalkThrough)."""

    def __init__(
        self,
        listing: Any,
        title: Optional[str] = None,
        theme: Optional[ThemeConfig] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        t = self.theme
        self.listing = listing
        self.title_mob = None
        if title:
            self.title_mob = slide_tex(title, font_size=38, color=t.primary, weight="BOLD")
            pin_top_left(self.title_mob, up=0.5, left=0.85)
            self.listing.next_to(self.title_mob, DOWN, buff=0.5)
            self.listing.align_to(self.title_mob, LEFT)
            self.add(self.title_mob)
        self.add(self.listing)

    def play_on(self, scene: Any) -> None:
        if self.title_mob is not None:
            safe_play(scene, Write(self.title_mob), run_time=0.55)
        try:
            safe_play(scene, Create(self.listing), run_time=1.2)
        except Exception:
            safe_play(scene, FadeIn(self.listing), run_time=0.7)

    def highlight_line(self, scene: Any, line: int) -> None:
        listing = self.listing
        apply = getattr(listing, "apply_cue", None)
        if callable(apply):
            from aos_manim_core import Cue, CueAction

            apply(scene, Cue(mark=f"L{line}", target_id="code", action=CueAction.STEP, payload={"line": line}))
            return
        hl = getattr(listing, "highlight_line", None)
        if callable(hl):
            hl(line)
