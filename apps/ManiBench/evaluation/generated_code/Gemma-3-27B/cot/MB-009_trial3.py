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

        # Initial value of x
        x = 0
        
        # Display the accumulated area
        area_text = Tex(f"Area = {f(x):.2f}", color=YELLOW)
        area_text.next_to(axes_f, UP)

        # Display the FTC formula
        ftc_formula = MathTex(r"\int_{0}^{x} f'(t) \, dt = f(x) - f(0)", color=PURPLE, weight=0.7)
        ftc_formula.next_to(area_text, UP)

        # Show initial state
        self.play(Create(axes_f), Create(axes_f_prime))
        self.play(Create(graph_f), Create(graph_f_prime))
        self.play(Write(f_label), Write(f_prime_label))
        self.play(Create(sweep_line[0]), Create(sweep_line[1]))
        self.play(Write(area_text), Write(ftc_formula))

        # Animate the sweep line and accumulated area
        for i in range(1, 101):
            x = -3 + (6 * i) / 100
            sweep_line[0].become(Line(start=axes_f_prime.c2p(x, 0), end=axes_f_prime.c2p(x, f_prime(x)), color=GREEN, stroke_width=2))
            
            polygon_points = []
            for j in range(i):
                x_val = -3 + (6 * j) / 100
                polygon_points.append(axes_f_prime.c2p(x_val, 0))
                polygon_points.append(axes_f_prime.c2p(x_val, f_prime(x_val)))
            polygon_points.append(axes_f_prime.c2p(x, 0))
            polygon_points.append(axes_f_prime.c2p(x, f_prime(x)))
            sweep_line[1].become(Polygon(*polygon_points, color=GREEN, opacity=0.5))
            
            area_text.set_text(f"Area = {f(x):.2f}")
            
            self.play(
                Update(sweep_line[0]),
                Update(sweep_line[1]),
                Update(area_text),
                run_time=0.05
            )

        # Demonstrate with several values of x
        x_values = [-2, -1, 0, 1, 2]
        for x in x_values:
            sweep_line[0].become(Line(start=axes_f_prime.c2p(x, 0), end=axes_f_prime.c2p(x, f_prime(x)), color=GREEN, stroke_width=2))
            polygon_points = []
            for j in range(101):
                x_val = -3 + (6 * j) / 100
                if x_val <= x:
                    polygon_points.append(axes_f_prime.c2p(x_val, 0))
                    polygon_points.append(axes_f_prime.c2p(x_val, f_prime(x_val)))
            sweep_line[1].become(Polygon(*polygon_points, color=GREEN, opacity=0.5))
            area_text.set_text(f"Area = {f(x):.2f}")
            self.play(
                Update(sweep_line[0]),
                Update(sweep_line[1]),
                Update(area_text),
                run_time=0.5
            )
        
        self.wait(2)