"""Automatic differentiation lecture: declarative slides plus lecture boards.

Render:
  .venv\\Scripts\\manim -ql examples/001_slide.py AutomaticDifferentiationLecture
"""

from __future__ import annotations

from manim import *

from aos_manim_core import get_theme, set_theme
from aos_manim_maths import DerivativeVisualizer
from aos_manim_slides import (
    ContentSlide,
    CopyExplain,
    QuoteCard,
    SectionSlide,
    SlideScene,
    VoiceoverSlideScene,
    TitleSlide,
    TwoColumnBullets,
)


class AutomaticDifferentiationLecture(VoiceoverSlideScene):
    """Title / section / bullets, then quote, agenda, and derivative copy-explain."""

    def construct(self):
        set_theme("academic_oxford")
        self.camera.background_color = get_theme().background
        self._on_stage = None

        self._title()
        self._section()
        self._benefits()
        self._quote()
        self._agenda()
        self._derivative()
        self._proof()

    def _swap(self, mob) -> None:
        outgoing = []
        if self._on_stage is not None:
            outgoing.append(self._on_stage)
        current = self.current_slide
        if current is not None and current is not self._on_stage:
            outgoing.append(current)
            self.current_slide_idx = -1

        visible_mobs = []
        def collect_visible(m):
            fill_op = getattr(m, "fill_opacity", 1.0)
            if callable(fill_op):
                try:
                    fill_op = fill_op()
                except Exception:
                    fill_op = 1.0
            stroke_op = getattr(m, "stroke_opacity", 1.0)
            if callable(stroke_op):
                try:
                    stroke_op = stroke_op()
                except Exception:
                    stroke_op = 1.0
            if fill_op == 0 and stroke_op == 0:
                return
            if len(m.submobjects) == 0:
                visible_mobs.append(m)
            else:
                for sub in m.submobjects:
                    collect_visible(sub)

        collect_visible(mob)

        if outgoing:
            self.play(
                *[FadeOut(m, shift=DOWN*0.3) for m in outgoing],
                *[FadeIn(m, shift=UP*0.3) for m in visible_mobs],
                run_time=0.8
            )
        else:
            self.play(
                *[FadeIn(m, shift=UP*0.3) for m in visible_mobs],
                run_time=0.8
            )
        self.add(mob)
        self._on_stage = mob

    def _title(self) -> None:
        slide = TitleSlide(
            title="Automatic Differentiation",
            subtitle="A Powerful Tool for Numerical Computation",
            author="Educlaw",
            date="2026",
            affiliation="AOS platform",
            total_bookmark_for_this_slide=(
                "Welcome to today's class. Here we will learn about the Automatic differentiation.<bookmark mark='b0'/> "
                "This is one of the fundamental techinque used in the differential programming framework like pytorch.<bookmark mark='b1'/> "
                "Hi, my name is Educlaw. I basically draw animation here at AOS platform<bookmark mark='b2'/> Let's start the lecture."
            )
        )
        self.show_slide(slide, transition="fade", lecture=True, run_time=0.9)

    def _section(self) -> None:
        slide = SectionSlide(
            section_title="Automatic Differentiation",
            subtitle="The Benefits of Automatic Differentiation",
            section_number=1,
            theme=get_theme(),
        )
        self.show_slide(slide, transition="fade", lecture=False, run_time=0.9)
        self.pause_slide(2)

    def _benefits(self) -> None:
        slide = ContentSlide(
            title="The Benefits of Automatic Differentiation",
            bullets=[
                "Automatic differentiation is a powerful tool for numerical computation.",
                "It allows for the efficient computation of derivatives, which are essential in many areas of science and engineering.",
                "Automatic differentiation can be used to compute gradients, Jacobians, and Hessians, which are important in optimization and machine learning.",
            ],
            theme=get_theme(),
        )
        self.show_slide(slide, transition="fade", lecture=False, run_time=0.9)
        self.pause_slide(2)

    def _quote(self) -> None:
        card = QuoteCard(
            "What I cannot create,\nI do not understand.",
            author="— Richard Feynman", # Author's name is not visible in video.
            font_size=44,
        )
        self._swap(card)
        card.play_on(self)

    def _agenda(self) -> None:
        board = TwoColumnBullets(  # Agenda's not visible in video
            "Today's agenda",
            [
                "Slope of a smooth curve",
                "Newton's method",
                "The same calculus in flight",
                "Geometry of water",
                "Halving a search",
            ],
            [
                "The code that searches",
                "A short derivation",
                "One shared theme",
                "What to take with you",
                "Thank you",
            ],
            font_size=28,
        )
        for row in board.left_mobs:
            row.set_opacity(0)
        for row in board.right_mobs:
            row.set_opacity(0)
        self._swap(board)
        board.play_on(self)

    def _derivative(self) -> None:
        vis = DerivativeVisualizer()
        packed = vis.build_derivative_mobjects("x**2 - 2*x", 2.0, axes_width=5.0, axes_height=3.0)
        graph = VGroup(packed["axes"], packed["curve"], packed["tangent_line"], packed["point"]).scale(0.7)
        panel = CopyExplain( ## Subtitle like part is not visible and the diagram is awful in video. Need to fix it.
            "The slope of a curve",
            ["The curve is smooth", "The tangent is the derivative at a point"],
            [graph],
            font_size=28,
        )
        for d in panel.diagrams:
            d.set_opacity(0)
        for row in panel.bullet_mobs:
            row.set_opacity(0)
        self._swap(panel)
        panel.play_on(self)
        self.play(Indicate(packed["tangent_line"], color=get_theme().highlight_a), run_time=0.6)

    def _proof(self) -> None:
        from aos_manim_proofs import DerivationChain, ProofStep, StepType
        chain = DerivationChain(
            theorem=r"x_{n+1}=x_n-\frac{f(x_n)}{f'(x_n)}",
            steps=[
                ProofStep("s1", r"f'(x_n)\neq 0", "local slope", StepType.ASSUMPTION),
                ProofStep("s2", r"y=f(x_n)+f'(x_n)(x-x_n)", "tangent", StepType.INFERENCE, ["s1"]),
                ProofStep("s3", r"0=f(x_n)+f'(x_n)(x_{n+1}-x_n)", "intercept", StepType.QED, ["s2"]),
            ],
            width=10.0,
        ).scale(0.82)
        header = chain.submobjects[0]
        rows = chain.submobjects[1] if len(chain.submobjects) > 1 else VGroup()
        for row in rows:
            row.set_opacity(0)
        title = Text("A short derivation", font_size=36, color=get_theme().primary, weight="BOLD")
        group = VGroup(title, chain).arrange(DOWN, buff=0.35)
        self._swap(group)
        self.beats(
            "Why the update? "
            "<bookmark mark='R0'/>The theorem. "
            "<bookmark mark='R1'/>A nonzero slope. "
            "<bookmark mark='R2'/>The tangent. "
            "<bookmark mark='R3'/>The intercept is the next guess.",
            [
                ("R0", lambda: None),
                ("R1", lambda: self.play(Write(rows[0]), run_time=0.8) if len(rows) else None),
                ("R2", lambda: self.play(Write(rows[1]), run_time=0.8) if len(rows) > 1 else None),
                ("R3", lambda: self.play(Write(rows[2]), run_time=0.8) if len(rows) > 2 else None),
            ],
        )

