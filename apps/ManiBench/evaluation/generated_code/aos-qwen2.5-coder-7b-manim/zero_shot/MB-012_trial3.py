from manim import *

class WindmillProblem(Scene):
    def construct(self):
        # Parameters
        num_points = 7
        radius = 2.5
        rotation_speed = 0.05
        
        # Create points
        points = VGroup(*[Dot(radius * np.array([np.cos(i*TAU/num_points), np.sin(i*TAU/num_points), 0])) for i in range(num_points)])
        
        # Create line
        line = Line(start=ORIGIN, end=RIGHT, color=YELLOW)
        line.add_updater(lambda l: l.become(Line(points[0].get_center(), points[1].get_center())))
        
        # Add labels
        title = Text("Windmill Problem", font_size=36).to_edge(UP)
        subtitle = Text(f"{num_points} Points", font_size=24).next_to(title, DOWN)
        
        # Animation sequence
        self.play(FadeIn(title), FadeIn(subtitle))
        self.wait(0.5)
        
        # Initial setup
        self.play(Create(points))
        self.play(Create(line))
        self.wait(0.5)
        
        # Rotate line continuously
        self.add(line)
        self.play(Rotate(line, TAU, rate_func=linear, run_time=TAU / rotation_speed))
        
        # Pivot animation
        pivot_point_index = 0
        for _ in range(2):  # Repeat twice to show the pattern
            # Find next point to pivot to
            next_pivot_index = (pivot_point_index + 1) % num_points
            
            # Update line to pass through current and next point
            line.add_updater(lambda l: l.become(Line(points[pivot_point_index].get_center(), points[next_pivot_index].get_center())))
            
            # Pivot animation
            self.play(
                Rotate(line, -PI, rate_func=linear, run_time=PI / rotation_speed),
                run_time=PI / rotation_speed
            )
            
            # Update pivot index
            pivot_point_index = next_pivot_index
        
        self.wait(1)