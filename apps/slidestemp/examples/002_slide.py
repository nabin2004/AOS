"""Example 8: three consecutive AP terms with given sum and product.

Render:
  .venv\\Scripts\\manim -ql examples/002_slide.py ArithmeticProgressionExample8
"""

from __future__ import annotations

from manim import DOWN, LEFT, MathTex, VGroup

from aos_manim_core import get_theme, set_theme
from aos_manim_slides import (
    ContentSlide,
    Equation,
    Paragraph,
    Slide,
    SlideScene,
    SlideSpec,
    TitleSlide,
    TwoColumnSlide,
)


class ArithmeticProgressionExample8(SlideScene):
    """Worked example: consecutive AP terms summing to 18 with product 192."""

    def construct(self):
        set_theme("academic_oxford")
        self.camera.background_color = get_theme().background

        self._title()
        self._given()
        self._setup()
        self._sum()
        self._product()
        self._cases()
        self._conclusion()

    def _eq_slide(self, title: str, *blocks) -> None:
        slide = Slide.from_spec(
            SlideSpec(title=title, layout="equation-focus", blocks=list(blocks))
        )
        self.show_slide(slide, transition="fade", lecture=False, run_time=0.9)
        self.pause_slide(2)

    def _title(self) -> None:
        slide = TitleSlide(
            title="Example 8",
            subtitle="Three consecutive terms of an AP",
            author="AOS Manim",
            date="2026",
            affiliation="Arithmetic series",
        )
        self.show_slide(slide, transition="fade", lecture=False, run_time=0.9)
        self.pause_slide(2)

    def _given(self) -> None:
        slide = ContentSlide(
            title="Given",
            bullets=[
                "The sum of three consecutive terms in an arithmetic series is 18.",
                "Their product is 192.",
                "Find these three terms.",
            ],
            theme=get_theme(),
        )
        self.show_slide(slide, transition="fade", lecture=False, run_time=0.9)
        self.pause_slide(2)

    def _setup(self) -> None:
        self._eq_slide(
            "Let the three consecutive terms be",
            Equation(latex=r"a-d,\quad a,\quad a+d"),
            Paragraph(text="Common difference $d$; middle term $a$."),
        )

    def _sum(self) -> None:
        self._eq_slide(
            "From the sum",
            Equation(latex=r"(a-d)+a+(a+d)=18"),
            Equation(latex=r"3a=18"),
            Equation(latex=r"a=6"),
        )

    def _product(self) -> None:
        self._eq_slide(
            "From the product",
            Equation(latex=r"(a-d)\cdot a\cdot(a+d)=192"),
            Equation(latex=r"(6-d)\cdot 6\cdot(6+d)=192"),
            Equation(latex=r"36-d^{2}=32"),
            Equation(latex=r"d^{2}=4\qquad d=\pm 2"),
        )

    def _cases(self) -> None:
        theme = get_theme()
        color = theme.text_main

        left = VGroup(
            MathTex(r"d=2", color=color),
            MathTex(r"a-d=6-2=4", color=color),
            MathTex(r"a=6", color=color),
            MathTex(r"a+d=6+2=8", color=color),
            MathTex(r"4,\ 6,\ 8", color=theme.primary),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.28)

        right = VGroup(
            MathTex(r"d=-2", color=color),
            MathTex(r"a-d=6-(-2)=8", color=color),
            MathTex(r"a=6", color=color),
            MathTex(r"a+d=6+(-2)=4", color=color),
            MathTex(r"8,\ 6,\ 4", color=theme.primary),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.28)

        slide = TwoColumnSlide(
            title="The two cases",
            left_content=left,
            right_content=right,
            theme=theme,
        )
        self.show_slide(slide, transition="fade", lecture=False, run_time=0.9)
        self.pause_slide(2)

    def _conclusion(self) -> None:
        slide = ContentSlide(
            title="Hence",
            bullets=[
                "The three terms of the AP are 4, 6, 8 or 8, 6, 4.",
                "These are the same numbers in reverse order.",
            ],
            theme=get_theme(),
        )
        self.show_slide(slide, transition="fade", lecture=False, run_time=0.9)
        self.pause_slide(2)
