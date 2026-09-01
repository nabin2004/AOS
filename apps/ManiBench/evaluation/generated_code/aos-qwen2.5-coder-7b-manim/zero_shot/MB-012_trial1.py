from manim import *

class WindmillProblem(Scene):
    def construct(self):
        # Parameters
        num_points = 7
        radius = 2.5
        rotation_speed = 0.05
        
        # Create points
        points = VGroup(*[Dot(radius*np.array([np.cos(i*TAU/num_points), np.sin(i*TAU/num_points), 0])) for i in range(num_points)])
        
        # Create line
        line = Line(start=ORIGIN, end=RIGHT*radius, color=YELLOW)
        line_label = MathTex("L").next_to(line, UP)
        
        # Add labels
        title = Text("Windmill Problem", font_size=36).to_edge(UP)
        self.add(title)
        
        # Initial setup
        self.play(FadeIn(points))
        self.wait(0.5)
        
        # Animation loop
        for angle in np.linspace(0, TAU, 100):
            # Update line position
            line.put_start_and_end_on(
                ORIGIN + angle*RIGHT,
                ORIGIN + (angle+rotation_speed)*RIGHT
            )
            
            # Check if line loses a point
            lost_point = None
            for p in points:
                if not line.get_center()[0] - p.get_center()[0] < 0.1:
                    lost_point = p
                    break
            
            if lost_point:
                # Find next point to connect
                next_point = None
                min_distance = float('inf')
                
                for p in points:
                    if p != lost_point:
                        distance = abs(p.get_center()[0] - line.get_center()[0])
                        if distance < min_distance:
                            min_distance = distance
                            next_point = p
                
                if next_point:
                    # Pivot line to connect with next point
                    pivot_angle = np.arctan2(next_point.get_center()[1], next_point.get_center()[0]) - np.arctan2(lost_point.get_center()[1], lost_point.get_center()[0])
                    pivot_line = Line(start=ORIGIN, end=RIGHT*radius, color=YELLOW)
                    pivot_line.rotate(pivot_angle, about_point=ORIGIN)
                    
                    self.play(Transform(line, pivot_line))
                    self.wait(0.1)
            
            self.wait(rotation_speed / TAU)
        
        # Final state
        self.wait(2)