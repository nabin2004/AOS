from manim import *
import numpy as np

class TaylorSeriesExpansion(Scene):
    def construct(self):
        # Title
        title = Text("Taylor Series Expansion of sin(x)", font_size=36).to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # Create axes
        axes = Axes(
            x_range=[-7, 7, 1],
            y_range=[-2.5, 2.5, 1],
            x_length=12,
            y_length=5,
            axis_config={"include_numbers": True, "font_size": 20},
            tips=True,
        ).shift(DOWN * 0.3)

        axes_labels = axes.get_axis_labels(x_label="x", y_label="y")

        self.play(Create(axes), Write(axes_labels))
        self.wait(0.5)

        # Plot original function sin(x) in black
        sin_graph = axes.plot(lambda x: np.sin(x), x_range=[-7, 7], color=WHITE, stroke_width=3)
        sin_label = MathTex(r"f(x) = \sin(x)", font_size=28, color=WHITE).next_to(axes, RIGHT, buff=0.1).shift(UP * 2)

        self.play(Create(sin_graph), Write(sin_label))
        self.wait(0.5)

        # Taylor series terms for sin(x) around x=0
        # sin(x) = x - x^3/3! + x^5/5! - x^7/7! + x^9/9! - x^11/11! + ...
        # P0(x) = 0
        # P1(x) = x
        # P2(x) = x (same as P1 since x^2 coefficient is 0)
        # P3(x) = x - x^3/6
        # P4(x) = x - x^3/6 (same)
        # P5(x) = x - x^3/6 + x^5/120
        # P6(x) = same
        # P7(x) = x - x^3/6 + x^5/120 - x^7/5040
        # We'll show orders 0, 1, 3, 5, 7, 9, 11, 13 (non-trivial terms)

        def taylor_sin(x, n_terms):
            """Compute partial sum of Taylor series for sin(x) with n_terms non-zero terms."""
            result = 0.0
            for k in range(n_terms):
                power = 2 * k + 1
                coeff = ((-1) ** k) / np.math.factorial(power)
                result += coeff * (x ** power)
            return result

        # Colors for each successive approximation
        colors = [
            YELLOW,       # P0: constant (0)
            RED,          # P1: linear term (x)
            BLUE,         # P3: cubic term
            GREEN,        # P5: quintic term
            ORANGE,       # P7
            PURPLE,       # P9
            PINK,         # P11
            TEAL,         # P13
        ]

        # LaTeX for each partial sum
        taylor_formulas = [
            r"P_0(x) = 0",
            r"P_1(x) = x",
            r"P_3(x) = x - \frac{x^3}{6}",
            r"P_5(x) = x - \frac{x^3}{6} + \frac{x^5}{120}",
            r"P_7(x) = \cdots - \frac{x^7}{5040}",
            r"P_9(x) = \cdots + \frac{x^9}{362880}",
            r"P_{11}(x) = \cdots - \frac{x^{11}}{39916800}",
            r"P_{13}(x) = \cdots + \frac{x^{13}}{6227020800}",
        ]

        # Term descriptions
        term_descriptions = [
            "0th order: constant term",
            "1st order: linear term",
            "3rd order: cubic term",
            "5th order: quintic term",
            "7th order term",
            "9th order term",
            "11th order term",
            "13th order term",
        ]

        # Orders corresponding to each step
        orders = [0, 1, 3, 5, 7, 9, 11, 13]
        n_terms_list = [0, 1, 2, 3, 4, 5, 6, 7]  # number of non-zero terms

        prev_graph = None
        prev_formula = None
        prev_desc = None

        for i in range(8):
            n_terms = n_terms_list[i]
            color = colors[i]

            # Create the Taylor approximation graph
            if n_terms == 0:
                taylor_graph = axes.plot(
                    lambda x: 0.0, x_range=[-7, 7], color=color, stroke_width=2.5
                )
            else:
                nt = n_terms  # capture for lambda
                taylor_graph = axes.plot(
                    lambda x, nt=nt: np.clip(taylor_sin(x, nt), -10, 10),
                    x_range=[-7, 7],
                    color=color,
                    stroke_width=2.5,
                )

            # Formula
            formula = MathTex(taylor_formulas[i], font_size=26, color=color)
            formula.to_corner(UL).shift(DOWN * 0.8 + RIGHT * 0.2)

            # Description
            desc = Text(term_descriptions[i], font_size=22, color=color)
            desc.next_to(formula, DOWN, aligned_edge=LEFT, buff=0.15)

            if prev_graph is None:
                self.play(
                    Create(taylor_graph),
                    Write(formula),
                    Write(desc),
                    run_time=1.5,
                )
            else:
                self.play(
                    ReplacementTransform(prev_graph, taylor_graph),
                    ReplacementTransform(prev_formula, formula),
                    ReplacementTransform(prev_desc, desc),
                    run_time=1.5,
                )

            self.wait(0.8)

            prev_graph = taylor_graph
            prev_formula = formula
            prev_desc = desc

        # Show convergence text
        convergence_text = Text(
            "Higher-order terms improve approximation",
            font_size=28,
            color=YELLOW,
        ).to_edge(DOWN, buff=0.4)

        box = SurroundingRectangle(convergence_text, color=YELLOW, buff=0.15, corner_radius=0.1)

        self.play(Write(convergence_text), Create(box), run_time=1.5)
        self.wait(1)

        # Final demonstration: show all approximations simultaneously
        self.play(
            FadeOut(prev_graph),
            FadeOut(prev_formula),
            FadeOut(prev_desc),
            run_time=0.5,
        )

        all_graphs = VGroup()
        legend_items = VGroup()

        for i in range(8):
            n_terms = n_terms_list[i]
            color = colors[i]
            nt = n_terms

            if nt == 0:
                g = axes.plot(lambda x: 0.0, x_range=[-7, 7], color=color, stroke_width=1.5)
            else:
                g = axes.plot(
                    lambda x, nt=nt: np.clip(taylor_sin(x, nt), -10, 10),
                    x_range=[-7, 7],
                    color=color,
                    stroke_width=1.5 + 0.2 * i,
                )
            all_graphs.add(g)

            # Legend entry
            line_sample = Line(ORIGIN, RIGHT * 0.4, color=color, stroke_width=3)
            label = MathTex(f"P_{{{orders[i]}}}", font_size=20, color=color)
            entry = VGroup(line_sample, label).arrange(RIGHT, buff=0.1)
            legend_items.add(entry)

        legend_items.arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        legend_items.to_corner(UR).shift(DOWN * 0.8 + LEFT * 0.2)
        legend_bg = BackgroundRectangle(legend_items, color=BLACK, fill_opacity=0.7, buff=0.1)

        self.play(
            *[Create(g) for g in all_graphs],
            FadeIn(legend_bg),
            *[Write(item) for item in legend_items],
            run_time=3,
        )
        self.wait(1)

        # Highlight that higher orders match better
        highlight_text = Text(
            "As n → ∞, Pₙ(x) → sin(x)",
            font_size=30,
            color=YELLOW,
        ).next_to(convergence_text, UP, buff=0.2)

        self.play(Write(highlight_text), run_time=1.5)
        self.wait(2)

        # Numerical coefficients display
        self.play(
            FadeOut(all_graphs),
            FadeOut(legend_bg),
            FadeOut(legend_items),
            FadeOut(highlight_text),
            FadeOut(convergence_text),
            FadeOut(box),
            FadeOut(sin_graph),
            FadeOut(sin_label),
            FadeOut(axes),
            FadeOut(axes_labels),
            FadeOut(title),
            run_time=1,
        )

        # Show numerical coefficients
        coeff_title = Text("Taylor Series Coefficients for sin(x)", font_size=32, color=WHITE).to_edge(UP)
        self.play(Write(coeff_title))

        coefficients = [
            (1, r"a_1 = +1", r"= \frac{1}{1!} = 1.000000"),
            (3, r"a_3 = -\frac{1}{6}", r"= -\frac{1}{3!} \approx -0.166667"),
            (5, r"a_5 = +\frac{1}{120}", r"= +\frac{1}{5!} \approx +0.008333"),
            (7, r"a_7 = -\frac{1}{5040}", r"= -\frac{1}{7!} \approx -0.000198"),
            (9, r"a_9 = +\frac{1}{362880}", r"= +\frac{1}{9!} \approx +0.000003"),
        ]

        coeff_group = VGroup()
        for idx, (n, term, val) in enumerate(coefficients):
            color = colors[idx + 1] if idx + 1 < len(colors) else WHITE
            line = MathTex(term, val, font_size=28, color=color)
            coeff_group.add(line)

        coeff_group.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        coeff_group.center().shift(DOWN * 0.3)

        for line in coeff_group:
            self.play(Write(line), run_time=0.8)
            self.wait(0.3)

        # Final formula
        final_formula = MathTex(
            r"\sin(x) = \sum_{k=0}^{\infty} \frac{(-1)^k}{(2k+1)!} x^{2k+1}",
            font_size=36,
            color=YELLOW,
        ).to_edge(DOWN, buff=0.5)

        final_box = SurroundingRectangle(final_formula, color=YELLOW, buff=0.15, corner_radius=0.1)

        self.play(Write(final_formula), Create(final_box), run_time=1.5)
        self.wait(3)