from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Title
        title = Text("Fundamental Theorem of Calculus", font_size=40).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # --- PART 1: Show f(x) and f'(x) ---

        # Create axes for f(x) on top
        axes_f = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 8, 2],
            x_length=5,
            y_length=2.5,
            axis_config={"include_numbers": True, "font_size": 20},
            tips=False,
        ).shift(UP * 1.5 + LEFT * 3)

        f_label = MathTex("f(x) = x^2", font_size=28, color=BLUE).next_to(axes_f, UP, buff=0.15)

        # f(x) = x^2
        f_graph = axes_f.plot(lambda x: x**2, x_range=[0, 3.5], color=BLUE)

        self.play(Create(axes_f), Write(f_label))
        self.play(Create(f_graph))
        self.wait(0.5)

        # Create axes for f'(x) below
        axes_fp = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 8, 2],
            x_length=5,
            y_length=2.5,
            axis_config={"include_numbers": True, "font_size": 20},
            tips=False,
        ).shift(DOWN * 2 + LEFT * 3)

        fp_label = MathTex("f'(x) = 2x", font_size=28, color=GREEN).next_to(axes_fp, UP, buff=0.15)

        # f'(x) = 2x
        fp_graph = axes_fp.plot(lambda x: 2 * x, x_range=[0, 3.5], color=GREEN)

        self.play(Create(axes_fp), Write(fp_label))
        self.play(Create(fp_graph))
        self.wait(0.5)

        # --- PART 2: Show the FTC equation ---
        ftc_eq = MathTex(
            r"\int_0^x f'(t)\, dt = f(x) - f(0)",
            font_size=32,
            color=YELLOW
        ).shift(RIGHT * 3.5 + UP * 2.5)
        self.play(Write(ftc_eq))
        self.wait(0.5)

        ftc_specific = MathTex(
            r"\int_0^x 2t\, dt = x^2 - 0 = x^2",
            font_size=28,
            color=YELLOW
        ).next_to(ftc_eq, DOWN, buff=0.3)
        self.play(Write(ftc_specific))
        self.wait(0.5)

        # --- PART 3: Accumulated area axes on the right ---
        axes_area = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 8, 2],
            x_length=4,
            y_length=2.5,
            axis_config={"include_numbers": True, "font_size": 20},
            tips=False,
        ).shift(RIGHT * 3.5 + DOWN * 1)

        area_label = MathTex(
            r"A(x) = \int_0^x 2t\, dt",
            font_size=24,
            color=ORANGE
        ).next_to(axes_area, UP, buff=0.15)

        self.play(Create(axes_area), Write(area_label))
        self.wait(0.3)

        # --- PART 4: Animate sweeping vertical line and accumulating area ---

        # Tracker for x value
        x_tracker = ValueTracker(0.01)

        # Shaded area under f'(x)
        shaded_area = always_redraw(lambda:
            axes_fp.get_area(
                fp_graph,
                x_range=[0, x_tracker.get_value()],
                color=ORANGE,
                opacity=0.4,
            )
        )

        # Vertical line on f'(x) axes
        v_line_fp = always_redraw(lambda:
            DashedLine(
                axes_fp.c2p(x_tracker.get_value(), 0),
                axes_fp.c2p(x_tracker.get_value(), 2 * x_tracker.get_value()),
                color=RED,
                stroke_width=2,
            )
        )

        # Vertical line on f(x) axes
        v_line_f = always_redraw(lambda:
            DashedLine(
                axes_f.c2p(x_tracker.get_value(), 0),
                axes_f.c2p(x_tracker.get_value(), x_tracker.get_value()**2),
                color=RED,
                stroke_width=2,
            )
        )

        # Dot on f(x) graph
        dot_f = always_redraw(lambda:
            Dot(
                axes_f.c2p(x_tracker.get_value(), x_tracker.get_value()**2),
                color=RED,
                radius=0.06,
            )
        )

        # Accumulated area graph (traced path)
        accumulated_graph = always_redraw(lambda:
            axes_area.plot(
                lambda x: x**2,
                x_range=[0, x_tracker.get_value()],
                color=ORANGE,
                stroke_width=3,
            )
        )

        # Dot on accumulated area graph
        dot_area = always_redraw(lambda:
            Dot(
                axes_area.c2p(x_tracker.get_value(), x_tracker.get_value()**2),
                color=RED,
                radius=0.06,
            )
        )

        # Value display
        value_display = always_redraw(lambda:
            MathTex(
                f"x = {x_tracker.get_value():.1f},\\quad "
                f"\\int_0^{{{x_tracker.get_value():.1f}}} 2t\\,dt = {x_tracker.get_value()**2:.2f}",
                font_size=24,
                color=WHITE,
            ).to_edge(DOWN, buff=0.3)
        )

        self.play(
            FadeIn(shaded_area),
            FadeIn(v_line_fp),
            FadeIn(v_line_f),
            FadeIn(dot_f),
            FadeIn(accumulated_graph),
            FadeIn(dot_area),
            FadeIn(value_display),
        )

        # Sweep from 0 to 3
        self.play(
            x_tracker.animate.set_value(3),
            run_time=5,
            rate_func=linear,
        )
        self.wait(1)

        # --- PART 5: Demonstrate several specific values ---
        highlight_values = [1, 2, 3]

        for xv in highlight_values:
            self.play(x_tracker.animate.set_value(xv), run_time=1)

            # Show correspondence
            corr_text = MathTex(
                f"x={xv}:" + r"\quad \int_0^{" + str(xv) + r"} 2t\,dt = " + str(xv) + r"^2 = " + str(xv**2),
                font_size=26,
                color=YELLOW,
            ).to_edge(DOWN, buff=0.05)

            # Highlight dot on f(x)
            highlight_dot_f = Dot(
                axes_f.c2p(xv, xv**2),
                color=YELLOW,
                radius=0.1,
            )
            highlight_dot_area = Dot(
                axes_area.c2p(xv, xv**2),
                color=YELLOW,
                radius=0.1,
            )

            # Arrow connecting the two dots
            self.play(
                FadeIn(corr_text),
                Flash(highlight_dot_f, color=YELLOW, flash_radius=0.3),
                Flash(highlight_dot_area, color=YELLOW, flash_radius=0.3),
            )
            self.wait(0.8)
            self.play(FadeOut(corr_text))

        # --- PART 6: Final emphasis ---
        self.play(x_tracker.animate.set_value(0.01), run_time=1.5)
        self.play(x_tracker.animate.set_value(3.5), run_time=4, rate_func=linear)

        # Draw the full accumulated area graph in blue to show it matches f(x)
        full_area_graph = axes_area.plot(
            lambda x: x**2, x_range=[0, 3.5], color=BLUE, stroke_width=4
        )
        match_label = MathTex(
            r"A(x) = x^2 = f(x)",
            font_size=28,
            color=BLUE,
        ).next_to(axes_area, DOWN, buff=0.2)

        self.play(Create(full_area_graph), Write(match_label))
        self.wait(0.5)

        # Final box around the theorem
        box = SurroundingRectangle(ftc_eq, color=YELLOW, buff=0.15)
        self.play(Create(box))
        self.wait(0.5)

        conclusion = Text(
            "The integral of the derivative recovers the original function!",
            font_size=24,
            color=WHITE,
        ).to_edge(DOWN, buff=0.15)
        self.play(Write(conclusion))
        self.wait(2)

        # Fade everything out
        self.play(*[FadeOut(mob) for mob in self.mobjects])
        self.wait(0.5)