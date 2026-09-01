from manim import *
import numpy as np

class WindmillProblem(Scene):
    def construct(self):
        # Configuration
        n_points = 6
        np.random.seed(42)  # For reproducible random points
        
        # Generate random points in general position
        points_coords = []
        while len(points_coords) < n_points:
            x = np.random.uniform(-3, 3)
            y = np.random.uniform(-2, 2)
            # Ensure no three points are collinear (simple check)
            if len(points_coords) < 2:
                points_coords.append([x, y, 0])
            else:
                # Check if new point is roughly collinear with any existing pair
                is_collinear = False
                for i in range(len(points_coords)):
                    for j in range(i + 1, len(points_coords)):
                        p1, p2 = points_coords[i], points_coords[j]
                        # Check if points are roughly collinear
                        cross_product = abs((x - p1[0]) * (p2[1] - p1[1]) - (y - p1[1]) * (p2[0] - p1[0]))
                        if cross_product < 0.1:
                            is_collinear = True
                            break
                    if is_collinear:
                        break
                if not is_collinear:
                    points_coords.append([x, y, 0])
        
        # Create point objects
        points = VGroup()
        point_labels = VGroup()
        for i, coord in enumerate(points_coords):
            point = Dot(coord, color=BLUE, radius=0.08)
            label = Text(f"P{i+1}", font_size=20).next_to(point, UP, buff=0.1)
            points.add(point)
            point_labels.add(label)
        
        # Title
        title = Text("Windmill Problem", font_size=36).to_edge(UP)
        
        # Show initial setup
        self.play(Write(title))
        self.play(Create(points), Write(point_labels))
        self.wait(1)
        
        # Find initial line through two points (start with first two points)
        p1_idx, p2_idx = 0, 1
        p1, p2 = points_coords[p1_idx], points_coords[p2_idx]
        
        # Create initial line
        line_length = 8
        direction = np.array(p2) - np.array(p1)
        direction = direction / np.linalg.norm(direction)
        
        # Extend line in both directions
        start_point = np.array(p1) - direction * line_length/2
        end_point = np.array(p1) + direction * line_length/2
        
        windmill_line = Line(start_point, end_point, color=RED, stroke_width=3)
        
        # Highlight initial two points
        highlight1 = Circle(radius=0.15, color=YELLOW).move_to(p1)
        highlight2 = Circle(radius=0.15, color=YELLOW).move_to(p2)
        
        self.play(Create(windmill_line))
        self.play(Create(highlight1), Create(highlight2))
        self.wait(1)
        
        # Animation parameters
        total_rotation = PI  # 180 degrees
        rotation_steps = 60
        angle_step = total_rotation / rotation_steps
        
        # Current pivot point and angle
        pivot_point = np.array(p1)
        current_angle = np.arctan2(direction[1], direction[0])
        
        # Track which points are currently on the line
        current_points = [p1_idx, p2_idx]
        
        # Animation loop
        for step in range(rotation_steps):
            new_angle = current_angle + angle_step
            
            # Check if we need to pivot to a new point
            # Find the next point that the line will hit
            min_angle_diff = float('inf')
            next_pivot_idx = None
            next_angle = new_angle
            
            for i, point_coord in enumerate(points_coords):
                if i in current_points:
                    continue
                
                # Calculate angle to this point from current pivot
                to_point = np.array(point_coord) - pivot_point
                point_angle = np.arctan2(to_point[1], to_point[0])
                
                # Normalize angle difference
                angle_diff = (point_angle - current_angle) % (2 * PI)
                if angle_diff > PI:
                    angle_diff -= 2 * PI
                
                # Check if this point is in the direction of rotation
                if 0 < angle_diff < angle_step * 2 and angle_diff < min_angle_diff:
                    min_angle_diff = angle_diff
                    next_pivot_idx = i
                    next_angle = point_angle
            
            # If we found a point to pivot to, do the pivot
            if next_pivot_idx is not None:
                # Animate to the pivot point
                pivot_angle = next_angle
                new_direction = np.array([np.cos(pivot_angle), np.sin(pivot_angle), 0])
                new_start = pivot_point - new_direction * line_length/2
                new_end = pivot_point + new_direction * line_length/2
                new_line = Line(new_start, new_end, color=RED, stroke_width=3)
                
                # Update highlights
                self.remove(highlight1, highlight2)
                
                # Determine which point to keep and which to replace
                if np.linalg.norm(np.array(points_coords[current_points[0]]) - pivot_point) < 0.1:
                    # Pivot point is current_points[0], replace current_points[1]
                    current_points[1] = next_pivot_idx
                else:
                    # Pivot point is current_points[1], replace current_points[0]
                    current_points[0] = next_pivot_idx
                
                highlight1 = Circle(radius=0.15, color=YELLOW).move_to(points_coords[current_points[0]])
                highlight2 = Circle(radius=0.15, color=YELLOW).move_to(points_coords[current_points[1]])
                
                self.play(
                    Transform(windmill_line, new_line),
                    Create(highlight1),
                    Create(highlight2),
                    run_time=0.1
                )
                
                # Update pivot point and angle
                pivot_point = np.array(points_coords[next_pivot_idx])
                current_angle = pivot_angle
            else:
                # Normal rotation
                new_direction = np.array([np.cos(new_angle), np.sin(new_angle), 0])
                new_start = pivot_point - new_direction * line_length/2
                new_end = pivot_point + new_direction * line_length/2
                new_line = Line(new_start, new_end, color=RED, stroke_width=3)
                
                self.play(Transform(windmill_line, new_line), run_time=0.05)
                current_angle = new_angle
        
        # Final message
        final_text = Text("The windmill completes a 180° rotation,\nmaintaining contact with 2 points", 
                         font_size=24).to_edge(DOWN)
        self.play(Write(final_text))
        self.wait(2)
        
        # Show the pattern repeats
        repeat_text = Text("Pattern repeats every 180°", font_size=24, color=GREEN).next_to(final_text, UP)
        self.play(Write(repeat_text))
        self.wait(2)