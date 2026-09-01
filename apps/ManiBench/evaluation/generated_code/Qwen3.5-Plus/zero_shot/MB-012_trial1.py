from manim import *
import numpy as np

class WindmillProblem(Scene):
    def construct(self):
        # Configuration
        n_points = 7
        seed = 42
        np.random.seed(seed)
        
        # Generate points in general position (no three collinear)
        # We generate random points and then perturb them slightly to ensure general position
        points = []
        while len(points) < n_points:
            candidate = np.array([
                np.random.uniform(-3, 3),
                np.random.uniform(-2, 2),
                0
            ])
            # Check if too close to existing points
            if all(np.linalg.norm(candidate - p) > 0.5 for p in points):
                points.append(candidate)
        points = np.array(points)
        
        # Create dots for the points
        dots = VGroup(*[Dot(point, radius=0.08, color=BLUE) for point in points])
        
        # Add labels to points (optional, for clarity)
        labels = VGroup()
        for i, point in enumerate(points):
            label = Text(f"P{i}", font_size=16, color=WHITE)
            label.next_to(point, UR, buff=0.05)
            labels.add(label)
        
        # Initial line setup
        # Find two points that can form an initial line (we'll use the first two for simplicity)
        # In a real windmill, we'd choose a line that doesn't pass through other points
        p1, p2 = points[0], points[1]
        initial_angle = np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
        
        # Create the windmill line
        line_length = 8  # Long enough to span the scene
        windmill_line = Line(
            start=p1 + np.array([np.cos(initial_angle), np.sin(initial_angle), 0]) * (-line_length/2),
            end=p1 + np.array([np.cos(initial_angle), np.sin(initial_angle), 0]) * (line_length/2),
            color=YELLOW,
            stroke_width=3
        )
        
        # Highlight the two pivot points
        pivot_dots = VGroup(
            Dot(p1, radius=0.12, color=RED),
            Dot(p2, radius=0.12, color=RED)
        )
        
        # Title and instructions
        title = Text("The Windmill Problem", font_size=36, color=WHITE)
        title.to_edge(UP)
        
        instruction = Text(
            "A line rotates, always passing through two points.\n"
            "When it hits a new point, it pivots to include it.",
            font_size=24,
            color=LIGHT_GRAY
        )
        instruction.next_to(title, DOWN, buff=0.3)
        
        # Animation sequence
        self.play(Write(title), Write(instruction))
        self.play(FadeIn(dots), FadeIn(labels))
        self.play(Create(windmill_line), FadeIn(pivot_dots))
        self.wait(0.5)
        
        # Windmill animation logic
        # We'll simulate the windmill process by rotating the line and detecting collisions
        current_angle = initial_angle
        current_pivot = p1
        secondary_point = p2
        
        # Track which points are currently on the line
        active_points = [p1, p2]
        
        # Create a tracer for the line's path (optional visual effect)
        tracer = VGroup()
        self.add(tracer)
        
        # Rotate through 180 degrees (pi radians)
        total_rotation = PI
        rotation_speed = 0.5  # radians per second
        total_time = total_rotation / rotation_speed
        
        # We'll use a custom animation that handles the pivoting
        class WindmillAnimation(Animation):
            def __init__(self, line, points, start_angle, start_pivot, start_secondary, **kwargs):
                super().__init__(line, **kwargs)
                self.points = points
                self.start_angle = start_angle
                self.start_pivot = start_pivot
                self.start_secondary = start_secondary
                self.current_angle = start_angle
                self.current_pivot = start_pivot
                self.active_points = [start_pivot, start_secondary]
                self.pivot_dot = None
                self.tracer_lines = VGroup()
                
            def begin(self):
                super().begin()
                # Create initial pivot dot
                self.pivot_dot = Dot(self.current_pivot, radius=0.12, color=RED)
                self.scene.add(self.pivot_dot)
                self.scene.add(self.tracer_lines)
                
            def interpolate_mobject(self, alpha):
                # Calculate current target angle
                target_angle = self.start_angle + alpha * PI
                
                # Simulate small steps to detect collisions
                step_size = 0.01
                current_sim_angle = self.current_angle
                
                while current_sim_angle < target_angle:
                    next_angle = min(current_sim_angle + step_size, target_angle)
                    
                    # Check for collisions in this interval
                    collision_found = False
                    collision_point = None
                    collision_angle = None
                    
                    # For each point not currently active, check if the line sweeps over it
                    for point in self.points:
                        if any(np.allclose(point, ap) for ap in self.active_points):
                            continue
                            
                        # Calculate angle from current pivot to this point
                        point_angle = np.arctan2(point[1] - self.current_pivot[1], 
                                               point[0] - self.current_pivot[0])
                        
                        # Normalize angles to [0, 2*PI)
                        def normalize_angle(a):
                            while a < 0: a += 2*PI
                            while a >= 2*PI: a -= 2*PI
                            return a
                            
                        current_norm = normalize_angle(current_sim_angle)
                        point_norm = normalize_angle(point_angle)
                        next_norm = normalize_angle(next_angle)
                        
                        # Check if point is swept over in this interval
                        # Handle wrap-around case
                        if current_norm <= next_norm:
                            if current_norm <= point_norm <= next_norm:
                                collision_found = True
                                collision_point = point
                                collision_angle = point_angle
                                break
                        else:  # Wrap around
                            if point_norm >= current_norm or point_norm <= next_norm:
                                collision_found = True
                                collision_point = point
                                collision_angle = point_angle
                                break
                    
                    if collision_found and collision_point is not None:
                        # Update active points: keep the collision point and the current pivot
                        # The old secondary point is dropped
                        self.active_points = [self.current_pivot, collision_point]
                        self.current_pivot = collision_point
                        current_sim_angle = collision_angle
                        self.current_angle = collision_angle
                        
                        # Update pivot dot position
                        self.pivot_dot.move_to(self.current_pivot)
                        
                        # Break to let the main loop catch up
                        break
                    else:
                        current_sim_angle = next_angle
                        self.current_angle = next_angle
                
                # Update the line based on current angle and pivot
                direction = np.array([np.cos(self.current_angle), np.sin(self.current_angle), 0])
                line_length = 8
                self.mobject.put_start_and_end_on(
                    self.current_pivot + direction * (-line_length/2),
                    self.current_pivot + direction * (line_length/2)
                )
                
                # Add tracer line occasionally for visual effect
                if int(alpha * 100) % 5 == 0:
                    tracer_line = Line(
                        start=self.mobject.get_start(),
                        end=self.mobject.get_end(),
                        color=YELLOW,
                        stroke_width=1,
                        stroke_opacity=0.3
                    )
                    self.tracer_lines.add(tracer_line)
        
        # Run the windmill animation
        windmill_anim = WindmillAnimation(
            windmill_line, 
            points, 
            initial_angle, 
            p1, 
            p2,
            run_time=total_time,
            rate_func=linear
        )
        
        self.play(windmill_anim)
        self.wait(1)
        
        # Final message
        final_text = Text(
            "After 180° rotation, the line returns to its original orientation\n"
            "but may have different points. The pattern continues infinitely!",
            font_size=20,
            color=GREEN
        )
        final_text.to_edge(DOWN)
        self.play(Write(final_text))
        self.wait(2)