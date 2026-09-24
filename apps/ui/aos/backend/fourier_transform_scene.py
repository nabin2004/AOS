from manim import *
import numpy as np

config.background_color = "#0f172a"
config.frame_width = 14.22
config.frame_height = 8.0
config.pixel_width = 1920
config.pixel_height = 1080
config.frame_rate = 60

# Color palette
BLUE_C = "#0077BB"
YELLOW = "#FFD700"
TEAL = "#00B4D8"
WHITE = "#FFFFFF"
GREEN = "#00FF00"
RED = "#FF0000"
GRAY = "#808080"
ORANGE = "#FFA500"

class FourierTransformScene(MovingCameraScene):
    def construct(self):
        self.scene1_title_hook()
        self.scene2_time_vs_frequency()
        self.scene3_core_idea()
        self.scene4_mathematical_definition()
        self.scene5_key_properties()
        self.scene6_square_wave_decomposition()
        self.scene7_inverse_reconstruction()
        self.scene8_summary()

    # ---------------------------------------------------------
    # Scene 1: Title & Hook
    # ---------------------------------------------------------
    def scene1_title_hook(self):
        title = MathTex(r"\mathcal{F}\{f(t)\} = F(\omega)", font_size=72, color=BLUE_C)
        subtitle = MathTex(r"\text{From Time to Frequency}", font_size=36, color=YELLOW)
        subtitle.next_to(title, DOWN, buff=0.3)
        title_group = VGroup(title, subtitle)
        title_group.to_edge(UP, buff=0.5)

        bg_waves = VGroup()
        for freq, amp, opacity in [(1, 0.3, 0.08), (2, 0.2, 0.06), (3, 0.15, 0.05), (5, 0.1, 0.04)]:
            wave = FunctionGraph(
                lambda t: amp * np.sin(freq * TAU * t),
                x_range=[-7.5, 7.5],
                color=WHITE,
                stroke_width=1,
                stroke_opacity=opacity,
            )
            bg_waves.add(wave)
        bg_waves.center()

        signal = ParametricFunction(
            lambda t: np.array([
                t,
                0.5 * np.sin(2 * TAU * t) + 0.3 * np.sin(6 * TAU * t),
                0
            ]),
            t_range=[-7.5, 7.5],
            color=WHITE,
            stroke_width=3,
        )
        signal.shift(DOWN * 2.5)

        self.play(Write(title), Write(subtitle), run_time=2)
        self.play(Create(bg_waves), run_time=3, rate_func=linear)
        drift_anim = bg_waves.animate.shift(LEFT * 0.5)
        self.play(drift_anim, run_time=4, rate_func=linear)
        self.play(Create(signal), run_time=3)
        self.wait(1)

        self.play(
            FadeOut(bg_waves),
            FadeOut(signal),
            title_group.animate.to_corner(UL, buff=0.5).scale(0.7),
            run_time=1.5
        )
        self.title_group = title_group
        self.wait(0.5)

    # ---------------------------------------------------------
    # Scene 2: Time vs Frequency Domain
    # ---------------------------------------------------------
    def scene2_time_vs_frequency(self):
        left_axes = Axes(
            x_range=[0, 4 * PI, PI],
            y_range=[-1.5, 1.5, 0.5],
            x_length=6,
            y_length=3.5,
            axis_config={"color": WHITE, "stroke_width": 1},
            tips=False,
        ).to_edge(LEFT, buff=1).shift(DOWN * 0.5)
        left_labels = left_axes.get_axis_labels(MathTex("t", font_size=24), MathTex("f(t)", font_size=24))

        right_axes = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 1.2, 0.2],
            x_length=6,
            y_length=3.5,
            axis_config={"color": WHITE, "stroke_width": 1},
            tips=False,
        ).to_edge(RIGHT, buff=1).shift(DOWN * 0.5)
        right_labels = right_axes.get_axis_labels(MathTex(r"\omega", font_size=24), MathTex(r"|F(\omega)|", font_size=24))

        time_label = MathTex(r"\text{Time Domain}", font_size=32, color=BLUE_C).next_to(left_axes, UP, buff=0.3)
        freq_label = MathTex(r"\text{Frequency Domain}", font_size=32, color=YELLOW).next_to(right_axes, UP, buff=0.3)

        def composite_func(t):
            return 0.5 * np.sin(1 * t) + 0.3 * np.sin(3 * t)
        composite_wave = left_axes.plot(composite_func, x_range=[0, 4*PI], color=WHITE, stroke_width=3)

        omega1, omega2 = 1, 3
        A1, A2 = 0.5, 0.3
        bar1 = Rectangle(width=0.3, height=0, fill_color=TEAL, fill_opacity=0.8, stroke_width=0)
        bar1.move_to(right_axes.c2p(omega1, 0), aligned_edge=DOWN)
        bar2 = Rectangle(width=0.3, height=0, fill_color=YELLOW, fill_opacity=0.8, stroke_width=0)
        bar2.move_to(right_axes.c2p(omega2, 0), aligned_edge=DOWN)

        bar1_label = MathTex(r"A_1 \delta(\omega-\omega_1)", font_size=20, color=TEAL).next_to(bar1, UP, buff=0.1)
        bar2_label = MathTex(r"A_2 \delta(\omega-\omega_2)", font_size=20, color=YELLOW).next_to(bar2, UP, buff=0.1)

        cursor = Line(UP * 0.1, DOWN * 0.1, color=ORANGE, stroke_width=3)
        cursor.move_to(left_axes.c2p(0, 0))

        self.play(
            Create(left_axes), Create(right_axes),
            Write(left_labels), Write(right_labels),
            Write(time_label), Write(freq_label),
            run_time=2
        )
        self.play(Create(composite_wave), run_time=2)
        self.play(FadeIn(bar1), FadeIn(bar2), FadeIn(bar1_label), FadeIn(bar2_label))

        tracker = ValueTracker(0)
        def update_cursor(mob):
            t = tracker.get_value()
            mob.move_to(left_axes.c2p(t, 0))
        def update_bar1(mob):
            t = tracker.get_value()
            val = abs(0.5 * np.sin(1 * t))
            target_h = right_axes.y_axis.n2p(val)[1] - right_axes.y_axis.n2p(0)[1]
            mob.stretch_to_fit_height(target_h)
            mob.move_to(right_axes.c2p(omega1, 0), aligned_edge=DOWN)
        def update_bar2(mob):
            t = tracker.get_value()
            val = abs(0.3 * np.sin(3 * t))
            target_h = right_axes.y_axis.n2p(val)[1] - right_axes.y_axis.n2p(0)[1]
            mob.stretch_to_fit_height(target_h)
            mob.move_to(right_axes.c2p(omega2, 0), aligned_edge=DOWN)

        cursor.add_updater(update_cursor)
        bar1.add_updater(update_bar1)
        bar2.add_updater(update_bar2)

        self.play(tracker.animate.set_value(4*PI), run_time=6, rate_func=linear)
        cursor.remove_updater(update_cursor)
        bar1.remove_updater(update_bar1)
        bar2.remove_updater(update_bar2)

        final_h1 = right_axes.y_axis.n2p(A1)[1] - right_axes.y_axis.n2p(0)[1]
        final_h2 = right_axes.y_axis.n2p(A2)[1] - right_axes.y_axis.n2p(0)[1]
        self.play(
            bar1.animate.stretch_to_fit_height(final_h1).move_to(right_axes.c2p(omega1, 0), aligned_edge=DOWN),
            bar2.animate.stretch_to_fit_height(final_h2).move_to(right_axes.c2p(omega2, 0), aligned_edge=DOWN),
            run_time=1
        )

        wave1 = left_axes.plot(lambda t: 0.5 * np.sin(1 * t), x_range=[0, 4*PI], color=TEAL, stroke_width=2)
        wave2 = left_axes.plot(lambda t: 0.3 * np.sin(3 * t), x_range=[0, 4*PI], color=YELLOW, stroke_width=2)
        wave1.shift(UP * 2)
        wave2.shift(UP * 2)
        self.play(
            Transform(composite_wave, wave1),
            FadeIn(wave2),
            run_time=2
        )
        self.wait(1)

        self.play(
            FadeOut(left_axes), FadeOut(right_axes),
            FadeOut(left_labels), FadeOut(right_labels),
            FadeOut(time_label), FadeOut(freq_label),
            FadeOut(composite_wave), FadeOut(wave2),
            FadeOut(bar1), FadeOut(bar2),
            FadeOut(bar1_label), FadeOut(bar2_label),
            FadeOut(cursor),
            run_time=1.5
        )

    # ---------------------------------------------------------
    # Scene 3: Core Idea — Correlation with Complex Exponentials
    # ---------------------------------------------------------
    def scene3_core_idea(self):
        cplane = ComplexPlane(
            x_range=[-1.5, 1.5],
            y_range=[-1.5, 1.5],
            background_line_style={"stroke_color": BLUE_C, "stroke_opacity": 0.3},
        ).scale(1.5).to_edge(LEFT, buff=1).shift(UP * 0.5)
        cplane.add_coordinates()
        cplane_label = MathTex(r"\text{Complex Plane: } e^{-i\omega t}", font_size=24, color=TEAL).next_to(cplane, UP, buff=0.2)

        vector = Vector(RIGHT, color=TEAL, stroke_width=4)
        vector.rotate(-PI/4)
        vector.add_updater(lambda m, dt: m.rotate(-dt * TAU, about_point=ORIGIN))

        cos_graph_axes = Axes(
            x_range=[0, 4*PI, PI],
            y_range=[-1.2, 1.2, 0.5],
            x_length=6,
            y_length=2.5,
            axis_config={"color": WHITE, "stroke_width": 1},
            tips=False,
        ).next_to(cplane, RIGHT, buff=1).shift(DOWN * 0.5)
        cos_graph_axes_labels = cos_graph_axes.get_axis_labels(MathTex("t", font_size=20), MathTex(r"\cos(\omega t)", font_size=20))

        def f_t(t):
            return 0.5 * np.sin(t) + 0.3 * np.sin(3*t)
        f_graph = cos_graph_axes.plot(f_t, x_range=[0, 4*PI], color=WHITE, stroke_width=2)

        cos_line = always_redraw(lambda: Line(
            cplane.n2p(0),
            cplane.n2p(vector.get_end()[0] + 0j),
            color=YELLOW,
            stroke_width=2,
            stroke_opacity=0.6
        ))

        cos_curve = cos_graph_axes.plot(lambda t: np.cos(t), x_range=[0, 4*PI], color=YELLOW, stroke_width=1.5, stroke_opacity=0.6)

        def get_product_area():
            area = VGroup()
            xs = np.linspace(0, 4*PI, 80)
            for i in range(len(xs)-1):
                x1, x2 = xs[i], xs[i+1]
                y1 = f_t(x1) * np.cos(x1)
                y2 = f_t(x2) * np.cos(x2)
                if y1 == 0 and y2 == 0:
                    continue
                pts = [
                    cos_graph_axes.c2p(x1, 0),
                    cos_graph_axes.c2p(x1, y1),
                    cos_graph_axes.c2p(x2, y2),
                    cos_graph_axes.c2p(x2, 0),
                ]
                poly = Polygon(*pts, fill_opacity=0.4, stroke_width=0)
                poly.set_fill(GREEN if (y1+y2)/2 > 0 else RED)
                area.add(poly)
            return area
        product_area_updater = always_redraw(get_product_area)

        integral_line = NumberLine(
            x_range=[-2, 2, 0.5],
            length=6,
            color=WHITE,
            stroke_width=2,
            include_numbers=True,
            font_size=20,
        ).next_to(cos_graph_axes, DOWN, buff=0.5)
        integral_label = MathTex(r"\int f(t) e^{-i\omega t} dt", font_size=24, color=YELLOW).next_to(integral_line, LEFT, buff=0.3)
        integral_dot = Dot(color=ORANGE).move_to(integral_line.n2p(0))

        integral_val = ValueTracker(0)
        def update_integral_dot(mob):
            mob.move_to(integral_line.n2p(integral_val.get_value()))
        integral_dot.add_updater(update_integral_dot)

        formula_parts = [
            MathTex(r"F(\omega) =", font_size=36, color=YELLOW),
            MathTex(r"\int_{-\infty}^{\infty}", font_size=36, color=WHITE),
            MathTex(r"f(t)", font_size=36, color=WHITE),
            MathTex(r"e^{-i\omega t}", font_size=36, color=TEAL),
            MathTex(r"dt", font_size=36, color=WHITE),
        ]
        formula_group = VGroup(*formula_parts).arrange(RIGHT, buff=0.1).to_edge(UP, buff=0.5).shift(RIGHT * 2)

        self.play(
            Create(cplane), Write(cplane_label),
            Create(cos_graph_axes), Write(cos_graph_axes_labels),
            Create(f_graph),
            run_time=2
        )
        self.play(GrowArrow(vector))
        self.play(Create(cos_line), Create(cos_curve), run_time=1)
        self.add(vector)
        self.play(Create(product_area_updater), run_time=1)
        self.play(Create(integral_line), Write(integral_label), GrowFromCenter(integral_dot), run_time=1)

        self.play(integral_val.animate.set_value(1.2), run_time=8, rate_func=linear)
        self.wait(1)

        for part in formula_parts:
            self.play(Write(part), run_time=0.8)
            self.wait(0.2)

        self.wait(1)

        vector.clear_updaters()
        integral_dot.clear_updaters()
        self.play(
            FadeOut(cplane), FadeOut(cplane_label),
            FadeOut(cos_graph_axes), FadeOut(cos_graph_axes_labels),
            FadeOut(f_graph), FadeOut(cos_line), FadeOut(cos_curve),
            FadeOut(product_area_updater), FadeOut(integral_line),
            FadeOut(integral_label), FadeOut(integral_dot),
            FadeOut(formula_group), FadeOut(vector),
            run_time=1.5
        )

    # ---------------------------------------------------------
    # Scene 4: Mathematical Definition — Forward & Inverse
    # ---------------------------------------------------------
    def scene4_mathematical_definition(self):
        forward = MathTex(
            r"F(\omega) = \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{\infty} f(t) e^{-i\omega t} dt",
            font_size=40,
            color=WHITE
        )
        forward.set_color_by_tex("F(\omega)", YELLOW)
        forward.set_color_by_tex("f(t)", BLUE_C)
        forward.set_color_by_tex("e^{-i\omega t}", TEAL)
        forward.set_color_by_tex(r"\frac{1}{\sqrt{2\pi}}", YELLOW)

        inverse = MathTex(
            r"f(t) = \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{\infty} F(\omega) e^{i\omega t} d\omega",
            font_size=40,
            color=WHITE
        )
        inverse.set_color_by_tex("f(t)", BLUE_C)
        inverse.set_color_by_tex("F(\omega)", YELLOW)
        inverse.set_color_by_tex("e^{i\omega t}", TEAL)
        inverse.set_color_by_tex(r"\frac{1}{\sqrt{2\pi}}", YELLOW)

        formulas = VGroup(forward, inverse).arrange(RIGHT, buff=2).shift(UP * 0.5)

        forward_label = MathTex(r"\text{Forward } (\mathcal{F})", font_size=28, color=BLUE_C).next_to(forward, UP, buff=0.3)
        inverse_label = MathTex(r"\text{Inverse } (\mathcal{F}^{-1})", font_size=28, color=YELLOW).next_to(inverse, UP, buff=0.3)

        arrow_forward = Arrow(forward.get_right(), inverse.get_left(), color=TEAL, buff=0.5)
        arrow_forward_label = MathTex(r"\mathcal{F}", font_size=28, color=TEAL).next_to(arrow_forward, UP, buff=0.1)
        arrow_inverse = Arrow(inverse.get_left(), forward.get_right(), color=TEAL, buff=0.5)
        arrow_inverse_label = MathTex(r"\mathcal{F}^{-1}", font_size=28, color=TEAL).next_to(arrow_inverse, DOWN, buff=0.1)
        arrow_inverse.shift(DOWN * 0.6)

        bg_series = MathTex(
            r"\sum_{n=-\infty}^{\infty} c_n e^{i n \omega_0 t} \longrightarrow \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{\infty} F(\omega) e^{i\omega t} d\omega",
            font_size=24,
            color=WHITE,
            stroke_opacity=0.3
        ).to_edge(DOWN, buff=0.5)

        self.play(Write(forward), Write(forward_label), run_time=2)
        self.play(Write(inverse), Write(inverse_label), run_time=2)
        self.play(GrowArrow(arrow_forward), Write(arrow_forward_label), GrowArrow(arrow_inverse), Write(arrow_inverse_label), run_time=1.5)
        self.play(FadeIn(bg_series), run_time=1)

        kernel_rect = SurroundingRectangle(forward.get_part_by_tex("e^{-i\omega t}"), color=TEAL, buff=0.05)
        dt_rect = SurroundingRectangle(forward.get_part_by_tex("dt"), color=YELLOW, buff=0.05)
        self.play(Create(kernel_rect), Create(dt_rect), run_time=1)
        self.wait(0.5)
        self.play(FadeOut(kernel_rect), FadeOut(dt_rect))

        self.play(TransformMatchingTex(forward.copy(), inverse), run_time=2)
        self.wait(0.5)

        dot = Dot(color=ORANGE).move_to(forward.get_left() + LEFT * 1)
        self.play(dot.animate.move_to(inverse.get_right() + RIGHT * 1), run_time=1)
        self.play(dot.animate.move_to(forward.get_left() + LEFT * 1), run_time=1)
        check = MathTex(r"\checkmark", font_size=40, color=GREEN).next_to(dot, UP)
        self.play(Write(check), run_time=0.5)
        self.wait(1)

        self.play(
            FadeOut(forward), FadeOut(inverse),
            FadeOut(forward_label), FadeOut(inverse_label),
            FadeOut(arrow_forward), FadeOut(arrow_inverse),
            FadeOut(arrow_forward_label), FadeOut(arrow_inverse_label),
            FadeOut(bg_series), FadeOut(dot), FadeOut(check),
            run_time=1.5
        )

    # ---------------------------------------------------------
    # Scene 5: Key Properties (Rapid Fire)
    # ---------------------------------------------------------
    def scene5_key_properties(self):
        panel_data = [
            {
                "title": r"\text{Linearity}",
                "formula": r"\mathcal{F}\{a f + b g\} = a F + b G",
                "color_a": YELLOW,
                "color_b": TEAL,
            },
            {
                "title": r"\text{Time Shift}",
                "formula": r"\mathcal{F}\{f(t-t_0)\} = e^{-i\omega t_0} F(\omega)",
                "color_a": TEAL,
            },
            {
                "title": r"\text{Scaling}",
                "formula": r"\mathcal{F}\{f(at)\} = \frac{1}{|a|} F(\omega/a)",
                "color_a": ORANGE,
            },
            {
                "title": r"\text{Convolution Theorem}",
                "formula": r"\mathcal{F}\{(f * g)(t)\} = F(\omega) G(\omega)",
                "color_a": GREEN,
            },
        ]

        panels = VGroup()
        for data in panel_data:
            axes_t = Axes(
                x_range=[-3, 3],
                y_range=[-1, 1],
                x_length=3,
                y_length=2,
                tips=False,
                axis_config={"stroke_width": 1, "color": GRAY},
            )
            axes_f = Axes(
                x_range=[-5, 5],
                y_range=[0, 1.5],
                x_length=3,
                y_length=2,
                tips=False,
                axis_config={"stroke_width": 1, "color": GRAY},
            )
            axes_group = VGroup(axes_t, axes_f).arrange(RIGHT, buff=0.3)

            title = MathTex(data["title"], font_size=24, color=WHITE)
            formula = MathTex(data["formula"], font_size=24, color=WHITE)
            if "color_a" in data:
                formula.set_color_by_tex("a", data["color_a"])
                formula.set_color_by_tex("b", data.get("color_b", data["color_a"]))
                formula.set_color_by_tex("t_0", data.get("color_a", TEAL))
            text_group = VGroup(title, formula).arrange(DOWN, buff=0.2)

            panel = VGroup(text_group, axes_group).arrange(DOWN, buff=0.3)
            panels.add(panel)

        panels.arrange_in_grid(rows=2, cols=2, buff=1)
        panels.center()

        grid_title = MathTex(r"\text{Properties of } \mathcal{F}", font_size=36, color=YELLOW).to_edge(UP, buff=0.5)

        self.play(Write(grid_title))
        for i, panel in enumerate(panels):
            self.play(FadeIn(panel, shift=UP * 0.3), run_time=1)
            axes_t = panel[1][0]
            axes_f = panel[1][1]
            if i == 0:
                wave1 = axes_t.plot(lambda t: 0.5*np.sin(t), color=TEAL, stroke_width=2)
                wave2 = axes_t.plot(lambda t: 0.3*np.sin(2*t), color=YELLOW, stroke_width=2)
                sum_wave = axes_t.plot(lambda t: 0.5*np.sin(t)+0.3*np.sin(2*t), color=WHITE, stroke_width=3)
                self.play(Create(wave1), Create(wave2), run_time=1)
                self.play(Transform(wave1, sum_wave), FadeOut(wave2), run_time=1)
                bar1 = Rectangle(width=0.2, height=1, fill_color=TEAL, fill_opacity=0.8).move_to(axes_f.c2p(1, 0.5), aligned_edge=DOWN)
                bar2 = Rectangle(width=0.2, height=0.6, fill_color=YELLOW, fill_opacity=0.8).move_to(axes_f.c2p(2, 0.3), aligned_edge=DOWN)
                self.play(GrowFromEdge(bar1, DOWN), GrowFromEdge(bar2, DOWN), run_time=1)
                self.wait(0.5)
                self.play(FadeOut(wave1), FadeOut(bar1), FadeOut(bar2))
            elif i == 1:
                wave = axes_t.plot(lambda t: 0.5*np.exp(-(t)**2), color=WHITE, stroke_width=3)
                self.play(Create(wave), run_time=1)
                self.play(wave.animate.shift(RIGHT * 1.5), run_time=1)
                cplane = ComplexPlane(x_range=[-1,1], y_range=[-1,1]).scale(0.5).next_to(axes_f, UP, buff=0.2)
                vec = Vector(RIGHT, color=TEAL).rotate(PI/4)
                vec.add_updater(lambda m, dt: m.rotate(dt * TAU, about_point=ORIGIN))
                self.play(FadeIn(cplane), GrowArrow(vec), run_time=0.5)
                self.add(vec)
                self.wait(1)
                vec.clear_updaters()
                self.play(FadeOut(wave), FadeOut(cplane), FadeOut(vec))
            elif i == 2:
                wave1 = axes_t.plot(lambda t: 0.5*np.exp(-t**2), color=WHITE, stroke_width=3)
                wave2 = axes_t.plot(lambda t: 0.5*np.exp(-(2*t)**2), color=TEAL, stroke_width=3)
                self.play(Create(wave1), run_time=1)
                self.play(Transform(wave1, wave2), run_time=1)
                bar1 = Rectangle(width=0.3, height=1, fill_color=TEAL, fill_opacity=0.8).move_to(axes_f.c2p(0, 0.5), aligned_edge=DOWN)
                bar2 = Rectangle(width=0.6, height=0.5, fill_color=YELLOW, fill_opacity=0.8).move_to(axes_f.c2p(0, 0.25), aligned_edge=DOWN)
                self.play(GrowFromEdge(bar1, DOWN), run_time=0.5)
                self.play(Transform(bar1, bar2), run_time=1)
                self.wait(0.5)
                self.play(FadeOut(wave1), FadeOut(bar1))
            elif i == 3:
                rect = axes_t.plot(lambda t: 1 if abs(t)<1 else 0, color=WHITE, stroke_width=3, use_smoothing=False)
                gauss = axes_t.plot(lambda t: 0.5*np.exp(-t**2), color=TEAL, stroke_width=2)
                self.play(Create(rect), Create(gauss), run_time=1)
                conv = axes_t.plot(lambda t: max(0, 1-abs(t)), color=YELLOW, stroke_width=3)
                self.play(Transform(rect, conv), FadeOut(gauss), run_time=1.5)
                bar1 = Rectangle(width=0.3, height=1, fill_color=WHITE, fill_opacity=0.8).move_to(axes_f.c2p(0, 0.5), aligned_edge=DOWN)
                bar2 = Rectangle(width=0.3, height=0.8, fill_color=TEAL, fill_opacity=0.8).move_to(axes_f.c2p(0, 0.4), aligned_edge=DOWN)
                bar3 = Rectangle(width=0.3, height=0.8, fill_color=YELLOW, fill_opacity=0.8).move_to(axes_f.c2p(0, 0.4), aligned_edge=DOWN)
                self.play(GrowFromEdge(bar1, DOWN), GrowFromEdge(bar2, DOWN), run_time=0.5)
                self.play(Transform(bar1, bar3), FadeOut(bar2), run_time=1)
                self.wait(0.5)
                self.play(FadeOut(rect), FadeOut(bar1), FadeOut(bar3))

            self.wait(0.3)

        self.wait(1)

        self.play(FadeOut(panels), FadeOut(grid_title), run_time=1.5)

    # ---------------------------------------------------------
    # Scene 6: Live Example — Square Wave Decomposition
    # ---------------------------------------------------------
    def scene6_square_wave_decomposition(self):
        time_axes = Axes(
            x_range=[-3*PI, 3*PI, PI],
            y_range=[-1.5, 1.5, 0.5],
            x_length=8.5,
            y_length=4.5,
            axis_config={"color": WHITE, "stroke_width": 1.5},
            tips=False,
        ).to_edge(LEFT, buff=0.5).shift(DOWN * 0.3)
        time_labels = time_axes.get_axis_labels(MathTex("t", font_size=24), MathTex("f(t)", font_size=24))

        freq_axes = Axes(
            x_range=[0, 16, 2],
            y_range=[0, 1.5, 0.2],
            x_length=5,
            y_length=4.5,
            axis_config={"color": WHITE, "stroke_width": 1.5},
            tips=False,
        ).to_edge(RIGHT, buff=0.5).shift(DOWN * 0.3)
        freq_labels = freq_axes.get_axis_labels(MathTex(r"\omega", font_size=24), MathTex(r"|F(\omega)|", font_size=24))

        def square_wave(t):
            return 1 if (t % (2*PI)) < PI else -1
        square_func = np.vectorize(square_wave)
        square_graph = time_axes.plot(square_func, x_range=[-3*PI, 3*PI], color=WHITE, stroke_width=2, use_smoothing=False)

        N_tracker = ValueTracker(1)

        def partial_sum(t, N):
            s = 0
            for k in range(1, N+1, 2):
                s += (4/(k*PI)) * np.sin(k*t)
            return s

        partial_graph = always_redraw(lambda: time_axes.plot(
            lambda t: partial_sum(t, int(N_tracker.get_value())),
            x_range=[-3*PI, 3*PI],
            color=TEAL,
            stroke_width=2.5,
        ))

        bars = VGroup()
        bar_labels = VGroup()
        max_k = 15
        for k in range(1, max_k+1, 2):
            height = 4/(k*PI)
            bar = Rectangle(width=0.25, height=0, fill_color=TEAL, fill_opacity=0.8, stroke_width=0)
            bar.move_to(freq_axes.c2p(k, 0), aligned_edge=DOWN)
            bars.add(bar)
            label = MathTex(fr"\frac{{4}}{{{k}\pi}}", font_size=16, color=TEAL).next_to(bar, UP, buff=0.05)
            bar_labels.add(label)
        for k in range(2, max_k+1, 2):
            bar = Rectangle(width=0.25, height=0.05, fill_color=GRAY, fill_opacity=0.4, stroke_width=0)
            bar.move_to(freq_axes.c2p(k, 0), aligned_edge=DOWN)
            bars.add(bar)

        gibbs_box = Rectangle(width=2, height=2, color=ORANGE, stroke_width=2).move_to(time_axes.c2p(0, 0))
        gibbs_label = MathTex(r"\text{Gibbs overshoot} \approx 9\%", font_size=24, color=ORANGE).next_to(gibbs_box, UP, buff=0.2)

        self.play(Create(time_axes), Create(freq_axes), Write(time_labels), Write(freq_labels), run_time=2)
        self.play(Create(square_graph), run_time=1.5)
        self.play(FadeIn(partial_graph), run_time=1)

        for k in range(1, max_k+1, 2):
            idx = (k-1)//2
            bar = bars[idx]
            label = bar_labels[idx]
            target_h = freq_axes.y_axis.n2p(4/(k*PI))[1] - freq_axes.y_axis.n2p(0)[1]
            self.play(
                N_tracker.animate.set_value(k),
                bar.animate.stretch_to_fit_height(target_h).move_to(freq_axes.c2p(k, 0), aligned_edge=DOWN),
                FadeIn(label),
                run_time=0.8
            )
            self.wait(0.3)

        self.wait(1)

        zoom_point = time_axes.c2p(0, 0)
        self.play(
            self.camera.frame.animate.scale(0.3).move_to(zoom_point),
            FadeIn(gibbs_box),
            Write(gibbs_label),
            run_time=2
        )
        self.wait(2)
        self.play(
            self.camera.frame.animate.scale(1/0.3).move_to(ORIGIN),
            FadeOut(gibbs_box),
            FadeOut(gibbs_label),
            run_time=1.5
        )

        self.play(
            FadeOut(time_axes), FadeOut(freq_axes),
            FadeOut(time_labels), FadeOut(freq_labels),
            FadeOut(square_graph), FadeOut(partial_graph),
            FadeOut(bars), FadeOut(bar_labels),
            run_time=1.5
        )

    # ---------------------------------------------------------
    # Scene 7: Inverse Transform — Reconstruction
    # ---------------------------------------------------------
    def scene7_inverse_reconstruction(self):
        freq_axes = Axes(
            x_range=[0, 16, 2],
            y_range=[0, 1.5, 0.2],
            x_length=5,
            y_length=4.5,
            axis_config={"color": WHITE, "stroke_width": 1.5},
            tips=False,
        ).to_edge(LEFT, buff=0.5).shift(DOWN * 0.3)
        freq_labels = freq_axes.get_axis_labels(MathTex(r"\omega", font_size=24), MathTex(r"|F(\omega)|", font_size=24))

        bars = VGroup()
        for k in range(1, 16, 2):
            height = 4/(k*PI)
            bar = Rectangle(width=0.25, height=freq_axes.y_axis.n2p(height)[1]-freq_axes.y_axis.n2p(0)[1],
                           fill_color=TEAL, fill_opacity=0.8, stroke_width=0)
            bar.move_to(freq_axes.c2p(k, 0), aligned_edge=DOWN)
            bars.add(bar)

        time_axes = Axes(
            x_range=[-3*PI, 3*PI, PI],
            y_range=[-1.5, 1.5, 0.5],
            x_length=8.5,
            y_length=4.5,
            axis_config={"color": WHITE, "stroke_width": 1.5},
            tips=False,
        ).to_edge(RIGHT, buff=0.5).shift(DOWN * 0.3)
        time_labels = time_axes.get_axis_labels(MathTex("t", font_size=24), MathTex("f(t)", font_size=24))

        cplane = ComplexPlane(
            x_range=[-2, 2],
            y_range=[-2, 2],
            background_line_style={"stroke_color": BLUE_C, "stroke_opacity": 0.2},
        ).scale(1.2).to_edge(UP, buff=0.5).shift(LEFT * 2)

        phasors = VGroup()
        for k in range(1, 16, 2):
            amp = 4/(k*PI)
            vec = Vector(amp * RIGHT, color=TEAL, stroke_width=3)
            vec.rotate(0)
            vec.k = k
            vec.add_updater(lambda m, dt: m.rotate(dt * m.k * TAU, about_point=ORIGIN))
            phasors.add(vec)

        def get_chain():
            chain = VGroup()
            current_tip = cplane.n2p(0)
            for vec in phasors:
                new_vec = vec.copy()
                new_vec.shift(current_tip - new_vec.get_start())
                chain.add(new_vec)
                current_tip = new_vec.get_end()
            return chain
        chain = always_redraw(get_chain)

        proj_lines = always_redraw(lambda: VGroup(*[
            DashedLine(
                cplane.n2p(complex(vec.get_end()[0], 0)),
                vec.get_end(),
                color=YELLOW,
                stroke_width=1,
                stroke_opacity=0.5
            ) for vec in phasors
        ]))

        def reconstructed_wave(t):
            s = 0
            for k in range(1, 16, 2):
                s += (4/(k*PI)) * np.sin(k*t)
            return s
        recon_graph = time_axes.plot(reconstructed_wave, x_range=[-3*PI, 3*PI], color=TEAL, stroke_width=2.5)

        self.play(Create(freq_axes), Write(freq_labels), Create(time_axes), Write(time_labels), run_time=1.5)
        self.play(FadeIn(bars), run_time=1)
        self.play(Create(cplane), run_time=1)

        for vec in phasors:
            self.play(GrowArrow(vec), run_time=0.2)
        self.play(FadeIn(chain), FadeIn(proj_lines), run_time=1)
        self.wait(3)

        self.play(Create(recon_graph), run_time=2)
        self.wait(2)

        for vec in phasors:
            vec.clear_updaters()
        self.play(
            *[FadeOut(vec) for vec in phasors],
            FadeOut(chain), FadeOut(proj_lines), FadeOut(cplane),
            run_time=1.5
        )

        square_graph = time_axes.plot(
            np.vectorize(lambda t: 1 if (t % (2*PI)) < PI else -1),
            x_range=[-3*PI, 3*PI], color=WHITE, stroke_width=2, use_smoothing=False
        )
        self.play(FadeIn(square_graph), run_time=1)
        self.wait(1)

        self.play(
            FadeOut(freq_axes), FadeOut(freq_labels),
            FadeOut(time_axes), FadeOut(time_labels),
            FadeOut(bars), FadeOut(recon_graph), FadeOut(square_graph),
            run_time=1.5
        )

    # ---------------------------------------------------------
    # Scene 8: Summary & Significance
    # ---------------------------------------------------------
    def scene8_summary(self):
        forward = MathTex(
            r"F(\omega) = \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{\infty} f(t) e^{-i\omega t} dt",
            font_size=36, color=WHITE
        ).set_color_by_tex("F(\omega)", YELLOW).set_color_by_tex("e^{-i\omega t}", TEAL)
        inverse = MathTex(
            r"f(t) = \frac{1}{\sqrt{2\pi}} \int_{-\infty}^{\infty} F(\omega) e^{i\omega t} d\omega",
            font_size=36, color=WHITE
        ).set_color_by_tex("f(t)", BLUE_C).set_color_by_tex("e^{i\omega t}", TEAL)
        equations = VGroup(forward, inverse).arrange(RIGHT, buff=1.5).center()

        apps = [
            (r"\text{Audio}", r"\text{MP3, EQ}", BLUE_C),
            (r"\text{Image}", r"\text{JPEG, Edges}", TEAL),
            (r"\text{Radio}", r"\text{OFDM, WiFi}", YELLOW),
            (r"\text{MRI}", r"\text{k-space}", GREEN),
            (r"\text{Quantum}", r"\text{Wavefunction}", ORANGE),
        ]
        app_mobjects = VGroup()
        for main, sub, color in apps:
            main_t = MathTex(main, font_size=24, color=color)
            sub_t = MathTex(sub, font_size=18, color=WHITE)
            g = VGroup(main_t, sub_t).arrange(DOWN, buff=0.1)
            icon = Circle(radius=0.3, color=color, fill_opacity=0.3)
            g.add(icon)
            g.arrange(RIGHT, buff=0.1)
            app_mobjects.add(g)

        app_mobjects.arrange_in_circle(radius=3)
        app_mobjects.move_to(ORIGIN)

        title = MathTex(r"\text{Fourier Transform: Universal Translator}", font_size=36, color=YELLOW).to_edge(UP, buff=0.5)

        self.play(Write(equations), run_time=2)
        self.play(Write(title), run_time=1)
        self.play(LaggedStart(*[GrowFromCenter(app) for app in app_mobjects], lag_ratio=0.2), run_time=3)
        self.wait(3)

        self.play(
            FadeOut(equations), FadeOut(title), FadeOut(app_mobjects),
            FadeOut(self.title_group),
            run_time=2
        )
        self.wait(1)

if __name__ == "__main__":
    pass