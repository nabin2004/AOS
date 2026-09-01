from manim import *
import numpy as np
import random

class WindmillAnimation(Scene):
    def construct(self):
        # Setup
        random.seed(42)
        np.random.seed(42)
        n_points = 6
        
        # Generate random points in general position (no three collinear)
        points = []
        min_dist = 0.8
        for _ in range(100):
            if len(points) >= n_points:
                break
            x = random.uniform(-4.5, 4.5)
            y = random.uniform(-3, 3)
            candidate = np.array([x, y, 0])
            
            # Check minimum distance to existing points
            valid = True
            for p in points:
                if np.linalg.norm(candidate - p) < min_dist:
                    valid = False
                    break
            if valid:
                points.append(candidate)
        
        # Create dots and labels
        dots = VGroup(*[Dot(p, color=BLUE, radius=0.1) for p in points])
        labels = VGroup(*[
            MathTex(str(i), font_size=24, color=WHITE).next_to(dots[i], DOWN, buff=0.15) 
            for i in range(n_points)
        ])
        
        # Title
        title = Text("Windmill Process", font_size=36).to_edge(UP)
        subtitle = Text("Rotating line through ≥2 points", font_size=24, color=GRAY).next_to(title, DOWN)
        
        self.play(FadeIn(title), FadeIn(subtitle))
        self.play(FadeIn(dots), FadeIn(labels))
        self.wait(0.5)
        
        # Initialize windmill with first two points
        pivot_idx = 0
        # Calculate initial angle to make line "horizontal-ish"
        vec = points[1] - points[0]
        current_angle = np.arctan2(vec[1], vec[0]) % np.pi
        
        # Create the windmill line (long enough to cover screen)
        direction = np.array([np.cos(current_angle), np.sin(current_angle), 0])
        windmill = Line(
            points[pivot_idx] - direction * 12,
            points[pivot_idx] + direction * 12,
            color=RED,
            stroke_width=4
        )
        
        # Pivot indicator
        pivot_highlight = SurroundingRectangle(dots[pivot_idx], color=YELLOW, buff=0.2)
        pivot_text = Text("Pivot", font_size=20, color=YELLOW).next_to(dots[pivot_idx], UP, buff=0.3)
        
        # Angle display
        angle_tracker = ValueTracker(0)
        angle_display = always_redraw(lambda: MathTex(
            f"\\text{{Rotation: }} {angle_tracker.get_value():.2f}^\\circ",
            font_size=28
        ).to_corner(DR))
        
        # Initial setup animation
        self.play(
            Create(windmill),
            Create(pivot_highlight),
            FadeIn(pivot_text),
            FadeIn(angle_display)
        )
        self.wait(0.5)
        
        # Windmill algorithm
        total_rotation = 0
        max_rotation = np.pi  # 180 degrees
        step_count = 0
        max_steps = 20  # Safety break
        
        while total_rotation < max_rotation - 0.01 and step_count < max_steps:
            step_count += 1
            
            # Find next point to hit
            min_angle_diff = float('inf')
            next_idx = -1
            
            for i in range(n_points):
                if i == pivot_idx:
                    continue
                vec_to_point = points[i] - points[pivot_idx]
                point_angle = np.arctan2(vec_to_point[1], vec_to_point[0])
                
                # Calculate smallest positive rotation needed (mod π because line is undirected)
                angle_diff = (point_angle - current_angle) % np.pi
                
                # Ensure we don't pick the same line direction (epsilon check)
                if angle_diff > 0.001 and angle_diff < min_angle_diff:
                    min_angle_diff = angle_diff
                    next_idx = i
            
            if next_idx == -1:
                break
            
            # Animate rotation
            # Duration proportional to angle for constant angular velocity feel
            duration = max(0.4, min_angle_diff * 1.5)
            
            self.play(
                Rotate(
                    windmill, 
                    angle=min_angle_diff, 
                    about_point=points[pivot_idx], 
                    rate_func=linear
                ),
                angle_tracker.animate.set_value(
                    (angle_tracker.get_value() + np.degrees(min_angle_diff)) % 180
                ),
                run_time=duration
            )
            
            total_rotation += min_angle_diff
            current_angle = (current_angle + min_angle_diff) % np.pi
            
            # Switch pivot to the new point
            old_pivot_idx = pivot_idx
            pivot_idx = next_idx
            
            # Visual feedback: flash the new pivot and update highlight
            new_pivot_highlight = SurroundingRectangle(dots[pivot_idx], color=YELLOW, buff=0.2)
            new_pivot_text = Text("Pivot", font_size=20, color=YELLOW).next_to(dots[pivot_idx], UP, buff=0.3)
            
            self.play(
                Transform(pivot_highlight, new_pivot_highlight),
                Transform(pivot_text, new_pivot_text),
                Indicate(dots[pivot_idx], color=YELLOW, scale_factor=1.5),
                run_time=0.3
            )
            
            # Brief pause to show the pivot change
            self.wait(0.2)
        
        # Completion
        completion_text = Text("180° completed - pattern repeats", font_size=28, color=GREEN)
        completion_text.next_to(subtitle, DOWN)
        
        self.play(
            FadeIn(completion_text),
            Flash(windmill, color=YELLOW, line_length=0.5, num_lines=12),
            run_time=1
        )
        self.wait(2)
        
        # Fade out
        self.play(
            FadeOut(windmill),
            FadeOut(pivot_highlight),
            FadeOut(pivot_text),
            FadeOut(dots),
            FadeOut(labels),
            FadeOut(title),
            FadeOut(subtitle),
            FadeOut(completion_text),
            FadeOut(angle_display)
        )