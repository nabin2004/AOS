from manim import *
import numpy as np

class EulersFormula(Scene):
    def construct(self):
        # 1. Setup the Complex Plane
        plane = NumberPlane(
            x_range=[-2, 2, 1],
            y_range=[-2, 2, 1],
            background_line_style={"stroke_opacity": 0.4}
        )
        plane.add_coordinates()
        
        labels = VGroup(
            Tex("Re").next_to(plane.get_x_axis(), RIGHT),
            Tex("Im").next_to(plane.get_y_axis(), UP)
        )

        # 2. The Unit Circle
        circle = Circle(radius=2, color=WHITE)
        
        # 3. Dynamic Elements using a ValueTracker
        # theta goes from 0 to 2*PI
        theta = ValueTracker(0)

        # The moving point on the circle
        dot = always_redraw(lambda: Dot(
            plane.coords_to_point(2 * np.cos(theta.get_value()), 2 * np.sin(theta.get_value())),
            color=YELLOW
        ))

        # The vector from origin to dot
        vector = always_redraw(lambda: Line(
            plane.get_origin(), 
            dot.get_center(), 
            color=YELLOW, 
            stroke_width=6
        ))

        # Projection to Real Axis (cos)
        cos_line = always_redraw(lambda: Line(
            plane.coords_to_point(2 * np.cos(theta.get_value()), 0), 
            dot.get_center(), 
            color=BLUE, 
            stroke_width=4
        ))
        
        # Projection to Imaginary Axis (sin)
        sin_line = always_redraw(lambda: Line(
            plane.coords_to_point(0, 2 * np.sin(theta.get_value())), 
            dot.get_center(), 
            color=RED, 
            stroke_width=4
        ))

        # The angle arc
        arc = always_redraw(lambda: Arc(
            radius=0.5, 
            start_angle=0, 
            angle=theta.get_value(), 
            color=WHITE
        ))

        # 4. The Formula Text
        formula = MathTex(
            "e^{i\\theta} = \\cos(\\theta) + i\\sin(\\theta)",
            font_size=48
        ).to_edge(UP)
        
        # Color coding the formula
        formula[0][0:4].set_color(YELLOW) # e^{i theta}
        formula[0][5:11].set_color(BLUE)   # cos(theta)
        formula[0][13:20].set_color(RED)   # i sin(theta)

        # 5. Animation Sequence
        self.play(Write(plane), Write(labels))
        self.play(Create(circle))
        self.play(Write(formula))
        self.wait(1)

        self.play(FadeIn(dot), Create(vector), Create(arc))
        self.play(Create(cos_line), Create(sin_line))
        self.wait(1)

        # Rotate the vector slowly for one full circle
        self.play(
            theta.animate.set_value(2 * PI), 
            run_time=6, 
            rate_func=linear
        )
        
        self.wait(2)