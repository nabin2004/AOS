from manim import *

class ChainRuleVisualization(Scene):
    def construct(self):
        # Create axes for g(x) and f(u)
        ax_g = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 8, 2],
            axis_config={"color": BLUE},
        ).shift(LEFT * 3 + DOWN * 0.5)
        
        ax_f = Axes(
            x_range=[0, 4, 1],
            y_range=[0, 8, 2],
            axis_config={"color": GREEN},
        ).shift(RIGHT * 3 + DOWN * 0.5)
        
        # Add labels for axes
        label_g = MathTex("g(x)").next_to(ax_g.get_x_axis(), RIGHT)
        label_f = MathTex("f(u)").next_to(ax_f.get_x_axis(), RIGHT)
        
        # Define g(x) as a parabola
        graph_g = ax_g.plot(lambda x: x**2, color=BLUE)
        dot_g = Dot(point=ax_g.c2p(1, 1), color=YELLOW)
        label_dot_g = MathTex("x").next_to(dot_g, UP)
        
        # Define f(u) as an exponential curve
        graph_f = ax_f.plot(lambda u: np.exp(u), color=GREEN)
        dot_f = Dot(point=ax_f.c2p(1, np.exp(1)), color=YELLOW)
        label_dot_f = MathTex("y").next_to(dot_f, UP)
        
        # Composition equation
        comp_eq = MathTex(r"y = f(g(x))").to_edge(UP)
        
        # Derivative equation
        deriv_eq = MathTex(r"\frac{dy}{dx} = f'(g(x)) \cdot g'(x)").to_edge(DOWN)
        
        # Animation sequence
        self.play(Create(ax_g), Write(label_g))
        self.play(Create(graph_g), FadeIn(dot_g), Write(label_dot_g))
        self.wait()
        
        self.play(Create(ax_f), Write(label_f))
        self.play(Create(graph_f), FadeIn(dot_f), Write(label_dot_f))
        self.wait()
        
        self.play(Write(comp_eq))
        self.wait()
        
        # Show derivative steps
        step1 = MathTex(r"\Delta y \approx f'(u) \Delta u").next_to(comp_eq, DOWN)
        step2 = MathTex(r"\Delta u \approx g'(x) \Delta x").next_to(step1, DOWN)
        step3 = MathTex(r"\Delta y \approx f'(u) \cdot g'(x) \Delta x").next_to(step2, DOWN)
        
        self.play(Write(step1))
        self.wait()
        
        self.play(Write(step2))
        self.wait()
        
        self.play(Write(step3))
        self.wait()
        
        # Final derivative equation
        final_deriv = MathTex(r"\frac{dy}{dx} = f'(g(x)) \cdot g'(x)").move_to(deriv_eq)
        self.play(Transform(step3, final_deriv))
        self.wait()