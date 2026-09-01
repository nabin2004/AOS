from manim import *

class FundamentalTheoremOfCalculus(Scene):
    def construct(self):
        # Define the function and its derivative
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
            y_range=[-2, 2, 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True},
        )

        axes_f.add_coordinate_labels()
        axes_f_prime.add_coordinate_labels()

        # Plot the function and its derivative
        graph_f = axes_f.plot(f, x_range=[-3, 3], color=BLUE, label="f(x)")
        graph_f_prime = axes_f_prime.plot(f_prime, x_range=[-3, 3], color=RED, label="f'(x)")

        # Add labels to the graphs
        f_label = axes_f.get_graph_label(graph_f, weight=0.8)
        f_prime_label = axes_f_prime.get_graph_label(graph_f_prime, weight=0.8)

        # Create a vertical line for the sweep
        sweep_line = VGroup(
            Line(start=axes_f_prime.c2p(0, 0), end=axes_f_prime.c2p(0, f_prime(0)), color=GREEN, stroke_width=2),
            Polygon(color=GREEN, opacity=0.5)
        )
        sweep_line[1].set_fill(color=GREEN, opacity=0.5)

        # Display the FTC formula
        ftc_formula = MathTex(
            "\\int_{0}^{x} f'(t) \, dt = f(x) - f(0)",
            font_size=36,
        ).to_edge(UP)

        # Initial state
        self.play(Create(axes_f), Create(axes_f_prime))
        self.play(Create(graph_f), Create(graph_f_prime))
        self.play(Write(f_label), Write(f_prime_label))
        self.play(Create(sweep_line[0]))
        self.play(Create(ftc_formula))

        # Animate the sweep line and accumulated area
        x_val = 0
        for i in range(101):
            x_val = -3 + (6 * i) / 100
            sweep_line[0].move_to(axes_f_prime.c2p(x_val, 0))
            sweep_line[1].become(Polygon(
                axes_f_prime.c2p(0, 0),
                axes_f_prime.c2p(x_val, 0),
                axes_f_prime.c2p(x_val, f_prime(x_val)),
                axes_f_prime.c2p(0, f_prime(x_val))
            ))
            
            # Calculate the accumulated area
            area = integrate(f_prime, 0, x_val)
            
            # Display the accumulated area
            area_rect = Rectangle(width=x_val, height=area, color=YELLOW, opacity=0.5)
            area_rect.move_to(axes_f.c2p(0, 0))
            
            # Update the area rectangle
            if i == 0:
                self.play(Create(area_rect))
            else:
                self.play(Transform(area_rect, Rectangle(width=x_val, height=area, color=YELLOW, opacity=0.5).move_to(axes_f.c2p(0, 0))))
            
            self.wait(0.02)

        # Demonstrate with several values of x
        x_values = [-2, -1, 0, 1, 2]
        for x in x_values:
            area = integrate(f_prime, 0, x)
            area_rect = Rectangle(width=x, height=area, color=YELLOW, opacity=0.5)
            area_rect.move_to(axes_f.c2p(0, 0))
            
            f_x = f(x)
            f_0 = f(0)
            
            self.play(
                Transform(area_rect, Rectangle(width=x, height=area, color=YELLOW, opacity=0.5).move_to(axes_f.c2p(0, 0))),
                Write(MathTex(f"f({x}) = {f_x:.2f}", font_size=24).next_to(ftc_formula, DOWN)),
                Write(MathTex(f"f(0) = {f_0:.2f}", font_size=24).next_to(MathTex(f"f({x}) = {f_x:.2f}", font_size=24), DOWN))
            )
            self.wait(1)