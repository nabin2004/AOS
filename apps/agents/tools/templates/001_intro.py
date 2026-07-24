from manim import *
from theme import *

lecture_number = 1
nameOfTitle = "Backpropagation"
subtitle = "Teaching a Neural Network to Learn"
COLOR_NAME = WHITE


class Branding(Scene):
    def construct(self):
        # self.camera.background_color = COLOR_NAME

        brand = Text("RUKUMINI", font_size=70, color=BLUE)
        self.play(Write(brand))
        self.wait(1)
        box = SurroundingRectangle(brand, color=WHITE, buff=MED_SMALL_BUFF)
        _N_letter = brand.copy()
        nabin = Text("by Nabin", font_size=30)
        nabin.move_to(DOWN * 0.9)
        self.play(Transform(_N_letter[6][0], nabin))
        self.play(Write(box))
        self.wait(2)

        self.play(Unwrite(brand))
        self.wait(1)

        title = Title(f"Lecture {lecture_number}")
        self.play(Transform(box[0], title))

        lecture_no = Text(f"{nameOfTitle}", font_size=50, color=BLUE)
        sub = Text(subtitle, font_size=30)
        sub.move_to(DOWN * 0.8)
        self.play(Write(lecture_no), Transform(_N_letter[6], sub))
        self.wait(1)

        self.clear()
        self.wait(2)


class Slide1(Scene):
    def construct(self):
        title = Text("Click to add title", font_size=50, color=BLUE)
        subtitle = Text("Click to add title", font_size=30).move_to(DOWN)

        self.play(Write(title, run_time=3))
        self.play(FadeIn(subtitle))
        self.wait(1)


class Slide2(Scene):
    def construct(self):
        title = Title("Click to add title")
        self.play(Write(title))
        text = Text("Click to add title", font_size=36)

        self.play(Write(text))
        self.wait(2)


class Quote(Scene):
    """
    Notes:
    > max 3-4 words per line
    """

    def construct(self):

        quote = Text(
            "Study what interests you\nin the most undisciplined,\nirreverent and original manner possible.",
            font="CMU Serif",
            font_size=52,
            line_spacing=0.8,
        )

        quote.set_color(WHITE)

        author = Text(
            "— Richard Feynman",
            font="CMU Serif",
            font_size=30,
            color=GREY_B,
            slant=ITALIC,
        )

        author.next_to(quote, DOWN, buff=0.7)
        author.align_to(quote, RIGHT)

        # Decorative line
        line = Line(
            author.get_left() + LEFT * 0.2,
            author.get_right() + RIGHT * 0.2,
            color=GREY_C,
            stroke_width=2,
        ).next_to(author, UP, buff=0.25)

        self.play(
            Write(quote),
            run_time=4,
            rate_func=smooth,
        )

        self.wait(0.5)

        self.play(
            GrowFromCenter(line),
            FadeIn(author, shift=0.2 * UP),
            run_time=1.2,
        )

        self.wait(3)

        self.play(
            FadeOut(VGroup(quote, line, author)),
            run_time=1.5,
        )


from manim import *


class Slide3(Scene):
    def construct(self):
        title = Title(
            "Click to add title",
            include_underline=True,
        )

        bullets = BulletedList(
            "Click to add title",
            "Click to add title",
            "Click to add title",
            "Click to add title",
            "Click to add title",
            "Click to add title",
            font_size=38,
            buff=0.6,
        )

        logo = ManimBanner().scale(0.7)

        bullets.next_to(title, DOWN, buff=0.8)
        bullets.to_edge(LEFT, buff=0.8)

        logo.to_edge(RIGHT, buff=0.8)
        logo.align_to(bullets, UP)

        bullets.next_to(title, DOWN, buff=0.8)
        bullets.align_to(title, LEFT)

        self.add(logo)

        self.play(Write(title))
        self.wait(0.3)

        for bullet in bullets:
            self.play(FadeIn(bullet, shift=RIGHT), run_time=0.5)

        self.wait()


class TwoColumnSlide(Scene):
    def construct(self):
        title = Title(
            "Click to add title",
            include_underline=True,
        )

        # Left column
        left_list = BulletedList(
            "Click to add title",
            "Click to add title",
            "Click to add title",
            font_size=36,
            buff=0.6,
        )

        # Right column
        right_list = BulletedList(
            "Click to add title",
            "Click to add title",
            "Click to add title",
            font_size=36,
            buff=0.6,
        )

        # Arrange the two columns
        columns = VGroup(left_list, right_list)
        columns.arrange(RIGHT, buff=1.8, aligned_edge=UP)
        columns.next_to(title, DOWN, buff=0.8)

        self.play(Write(title))
        self.wait(0.3)

        # Animate row by row
        max_rows = max(len(left_list), len(right_list))

        for i in range(max_rows):
            animations = []

            if i < len(left_list):
                animations.append(FadeIn(left_list[i], shift=RIGHT))

            if i < len(right_list):
                animations.append(FadeIn(right_list[i], shift=RIGHT))

            self.play(*animations, run_time=0.5)

        self.wait()


from manim import *


class Disclaimer(Scene):
    def construct(self):
        tit = Title("DISCLAIMER", color=RED)

        line1 = Text(
            "LLMs are non-deterministic systems.",
            font_size=40,
            t2c={"non-deterministic": YELLOW},
        )
        line2 = Text(
            "Their outputs require verification and should not be trusted blindly.",
            font_size=30,
            t2c={"verification": GREEN, "not be trusted blindly": RED},
        )

        body = VGroup(line1, line2).arrange(DOWN, buff=0.5)
        body.next_to(tit, DOWN, buff=1.0)

        self.play(Write(tit), run_time=1.2)
        self.wait(0.3)
        self.play(FadeIn(line1, shift=UP * 0.3), run_time=0.8)
        self.wait(0.4)
        self.play(Write(line2), run_time=2)

        self.wait(2)

        self.play(FadeOut(VGroup(tit, body)), run_time=0.8)


class ArchitectureExplaining(Scene):
    def construct(self):
        title = Title("Transformer Encoder")

        bullets = BulletedList(
            "Multi-Head Attention",
            "Add \\& LayerNorm",
            "MLP / Feed Forward",
            "Residual Connection",
            font_size=34,
        )

        bullets.to_edge(LEFT)
        bullets.next_to(title, DOWN)

        self.play(Write(title))
        self.play(FadeIn(bullets))

        # ------------------------
        # Multi-Head Attention
        # ------------------------

        attention_box = RoundedRectangle(
            width=4,
            height=2,
            corner_radius=0.2,
            color=BLUE,
        )

        attention_text = Text("Multi-Head\nAttention", font_size=30)

        attention = VGroup(attention_box, attention_text)

        attention.to_edge(RIGHT)

        self.play(TransformFromCopy(bullets[0], attention))

        self.wait(2)

        self.play(FadeOut(attention))

        # ------------------------
        # MLP
        # ------------------------

        mlp_box = RoundedRectangle(
            width=4,
            height=2,
            corner_radius=0.2,
            color=GREEN,
        )

        mlp_text = Text("Feed Forward\nNetwork", font_size=30)

        mlp = VGroup(mlp_box, mlp_text)

        mlp.to_edge(RIGHT)

        self.play(TransformFromCopy(bullets[2], mlp))

        self.wait(2)


class CodeWalkThrough(Scene):
    def construct(self):
        listing = Code(
            "codess/helloworld.py",
            tab_width=4,
            formatter_style="vs",
            # background="window",
            language="python",
            # background_config={"stroke_color": WHITE},
            # paragraph_config={"font": "Noto Sans Mono"},
        )

        self.play(Create(listing))
        self.wait()


class EquationMorphing(Scene):
    def construct(self):
        pass


class Proof(Scene):
    def construct(self):
        pass


class Timeline(Scene):
    def construct(self):
        pass
