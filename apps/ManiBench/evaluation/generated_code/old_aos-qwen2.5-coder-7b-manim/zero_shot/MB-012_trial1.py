from manim import *

class WindmillProblem(Scene):
    def construct(self):
        # Create random points
        n = 7
        points = [Dot(np.random.uniform(-3, 3, 2)) for _ in range(n)]
        
        # Group points for easy manipulation
        point_group = VGroup(*points)
        
        # Add labels to points
        labels = VGroup()
        for i, point in enumerate(points):
            label = MathTex(f"P_{i+1}").next_to(point, UP)
            labels.add(label)
        
        # Create initial line passing through first two points
        line = Line(start=points[0].get_center(), end=points[1].get_center())
        line_label = MathTex("L").move_to(line.get_center() + RIGHT*0.5 + UP*0.5)
        
        # Add everything to scene
        self.play(Create(point_group))
        self.play(Write(labels))
        self.play(Create(line), Write(line_label))
        self.wait(0.5)
        
        # Function to rotate line around center of mass
        def rotate_line(line, angle):
            center_of_mass = np.mean([p.get_center() for p in points], axis=0)
            return Rotate(
                line,
                angle=angle,
                about_point=center_of_mass,
                rate_func=linear
            )
        
        # Animation loop
        for i in range(100):
            # Rotate line by small angle
            self.play(rotate_line(line, DEGREES/2))
            
            # Check if line loses any points
            current_points = [p for p in points if line.intersection(p)[0]]
            if len(current_points) < 2:
                # Find next pair of points to connect
                min_distance = float('inf')
                next_pair = None
                
                for j in range(len(points)):
                    for k in range(j+1, len(points)):
                        dist = get_norm(points[j].get_center() - points[k].get_center())
                        if dist < min_distance:
                            min_distance = dist
                            next_pair = (j, k)
                
                # Update line to pass through next pair
                new_line = Line(
                    start=points[next_pair[0]].get_center(),
                    end=points[next_pair[1]].get_center()
                )
                new_line_label = MathTex("L").move_to(new_line.get_center() + RIGHT*0.5 + UP*0.5)
                
                self.play(Transform(line, new_line), Transform(line_label, new_line_label))
        
        self.wait(2)