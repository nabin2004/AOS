from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define functions
        f = lambda x: 0.5 * x**2
        f_prime = lambda x: x

        # Create axes
        axes_f = Axes(
            x_range=[-3, 3, 1],
            y_range=[0, 5, 1],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True},
        )
        axes_f_prime = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 4, 1],
            x_length=6,
            y_length=4,
            axis_config={"include_numbers": True},
        )
        axes_f.add_coordinate_labels()
        axes_f_prime.add_coordinate_labels()

        # Plot functions
        graph_f = axes_f.plot(f, x_range=[-3, 3], color=BLUE)
        graph_f_prime = axes_f_prime.plot(f_prime, x_range=[-3, 3], color=RED)

        # Label functions
        f_label = Tex("f(x) = 0.5x^2", weight=0.8, critical=True).next_to(graph_f, UP)
        f_prime_label = Tex("f'(x) = x", weight=0.8, critical=True).next_to(graph_f_prime, UP)

        # Initial sweep line
        sweep_line = DashedLine(start=axes_f_prime.coords_to_point(0, 0), end=axes_f_prime.coords_to_point(0, 0), color=GREEN, stroke_width=3)
        area = axes_f_prime.get_area(f_prime, x_range=[0, 0], color=GREEN, opacity=0.5)

        # Accumulated area graph
        axes_accumulated = Axes(
            x_range=[-3, 3, 1],
            y_range=[0, 5, 1],
            x_length=4,
            y_length=4,
            axis_config={"include_numbers": True},
        )
        graph_accumulated = axes_accumulated.plot(f, x_range=[-3, 3], color=BLUE)
        accumulated_label = Tex("Accumulated Area", weight=0.8).next_to(graph_accumulated, UP)

        # FTC formula
        ftc_formula = Tex(r"\int_{0}^{x} f'(t) \, dt = f(x) - f(0)", weight=0.7, critical=True)
        ftc_formula.move_to(DOWN * 2)

        # Initial display
        self.play(Create(axes_f), Create(graph_f), Write(f_label))
        self.wait(1)
        self.play(Create(axes_f_prime), Create(graph_f_prime), Write(f_prime_label))
        self.wait(1)

        # Animate sweep line and area accumulation
        for x in np.arange(0, 3, 0.1):
            sweep_line.become(DashedLine(start=axes_f_prime.coords_to_point(x, 0), end=axes_f_prime.coords_to_point(x, 0), color=GREEN, stroke_width=3))
            area.become(axes_f_prime.get_area(f_prime, x_range=[0, x], color=GREEN, opacity=0.5))
            self.play(
                MoveToTarget(sweep_line),
                UpdateFromFunc(area, lambda a: axes_f_prime.get_area(f_prime, x_range=[0, x], color=GREEN, opacity=0.5)),
            )
            self.wait(0.05)

        self.wait(1)

        # Display accumulated area graph
        self.play(Create(axes_accumulated), Create(graph_accumulated), Write(accumulated_label))
        self.wait(1)

        # Display FTC formula
        self.play(Write(ftc_formula))
        self.wait(2)