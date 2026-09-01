from manim import *
import random
import math

class WindmillProblem(ThreeDScene):
    def construct(self):
        # Set up the scene
        title = Title("The Windmill Problem", font_size=40)
        self.add(title)

        # Define number of points
        n = 7
        points_coords = []
        min_dist = 0.7
        max_tries = 100

        # Generate random points in general position (no three collinear)
        while len(points_coords) < n:
            x = random.uniform(-4, 4)
            y = random.uniform(-2, 2)
            valid = True
            for px, py in points_coords:
                if (x - px)**2 + (y - py)**2 < min_dist**2:
                    valid = False
                    break
            if not valid:
                continue

            # Check for three collinear points if we have at least 2 already
            new_point = np.array([x, y, 0])
            collinear = False
            for i in range(len(points_coords)):
                for j in range(i + 1, len(points_coords)):
                    p1 = np.array([points_coords[i][0], points_coords[i][1], 0])
                    p2 = np.array([points_coords[j][0], points_coords[j][1], 0])
                    # Cross product to check collinearity
                    if np.linalg.norm(np.cross(new_point - p1, p2 - p1)) < 1e-5:
                        collinear = True
                        break
                if collinear:
                    break
            if not collinear:
                points_coords.append((x, y))

        # Create MObjects for points
        dots = VGroup()
        point_labels = VGroup()
        dot_objects = {}
        for i, (x, y) in enumerate(points_coords):
            dot = Dot(point=[x, y, 0], color=BLUE, radius=0.06)
            label = MathTex(f"P_{i}", font_size=30).next_to(dot, UP, buff=0.15)
            dots.add(dot)
            point_labels.add(label)
            dot_objects[(x, y)] = (dot, label)

        # Add points and labels
        self.play(FadeIn(dots), Write(point_labels))

        # Sort points by y-coordinate to find the starting horizontal line
        sorted_points = sorted(points_coords, key=lambda p: p[1])
        # Start with the two lowest points
        p1 = sorted_points[0]
        p2 = sorted_points[1]
        dot1, label1 = dot_objects[p1]
        dot2, label2 = dot_objects[p2]

        # Highlight the initial two points
        self.play(
            dot1.animate.set_color(RED),
            dot2.animate.set_color(RED),
            label1.animate.set_color(RED),
            label2.animate.set_color(RED)
        )

        # Create initial line (horizontal)
        line = Line(
            start=np.array([p1[0], p1[1], 0]),
            end=np.array([p2[0], p2[1], 0]),
            color=YELLOW
        ).extend_to_border()
        line.set_color(YELLOW)
        self.play(Create(line))

        # Label the line
        line_label = MathTex(r"\ell", font_size=36).next_to(line.get_end(), DR, buff=0.2).set_color(YELLOW)
        self.play(Write(line_label))

        # Function to create line through two points
        def get_line_through(p, q):
            v = np.array([q[0] - p[0], q[1] - p[1], 0])
            if np.linalg.norm(v) == 0:
                return Line(ORIGIN, ORIGIN)
            v = v / np.linalg.norm(v)
            return Line(p + 10*v, p - 10*v, color=YELLOW)

        # Current pivot point and direction
        current_pivot = p1
        other_point = p2
        current_line = get_line_through(current_pivot, other_point)
        current_angle = math.atan2(other_point[1] - current_pivot[1], other_point[0] - current_pivot[0])

        # Keep track of visited states to detect cycle
        visited_states = set()
        total_rotation = 0
        max_rotation = PI  # 180 degrees

        # Animation speed
        angular_speed = 0.5  # radians per frame approx
        dt = 1 / 15  # time step

        # Start rotating
        self.wait(1)

        while total_rotation < max_rotation:
            # Find next point to hit when rotating counterclockwise around pivot
            candidates = []
            pivot = current_pivot
            px, py = pivot

            for (x, y) in points_coords:
                if (x, y) == pivot or (x, y) == other_point:
                    continue
                dx, dy = x - px, y - py
                angle = math.atan2(dy, dx)
                # Normalize angle relative to current direction
                rel_angle = (angle - current_angle) % (2 * PI)
                if rel_angle > 1e-5:  # must be strictly greater
                    candidates.append((rel_angle, (x, y)))

            if not candidates:
                break

            # Find the smallest positive angle (next point to hit)
            next_angle_rel, next_point = min(candidates, key=lambda x: x[0])
            target_angle = current_angle + next_angle_rel

            # Animate rotation to that angle
            steps = int(next_angle_rel / (angular_speed * dt)) or 1
            angles = np.linspace(current_angle, target_angle, steps)

            for angle in angles:
                new_line = get_line_through(pivot, (pivot[0] + math.cos(angle), pivot[1] + math.sin(angle)))
                line.become(new_line)
                line_label.next_to(new_line.get_end(), DR, buff=0.2)
                self.remove(line_label)
                self.add(line_label)
                self.wait(dt)

            # Update total rotation
            total_rotation += next_angle_rel
            current_angle = target_angle

            # Pivot: the line now rotates around the new point
            # The old other point becomes the new pivot? No: the new contact point becomes the new pivot
            # Actually: the line now pivots around the newly hit point
            # So: current_pivot becomes next_point, and other_point becomes the old pivot
            # But we must ensure the line still passes through two points

            # Highlight the new pivot
            new_dot, new_label = dot_objects[next_point]
            old_dot, old_label = dot_objects[current_pivot]

            self.play(
                old_dot.animate.set_color(BLUE),
                old_label.animate.set_color(WHITE),
                new_dot.animate.set_color(RED),
                new_label.animate.set_color(RED),
                run_time=0.5
            )

            # Update state
            other_point = current_pivot
            current_pivot = next_point

            # Check for cycle (same pivot and same direction mod PI)
            state_key = (current_pivot, round(current_angle % PI, 3))
            if state_key in visited_states:
                # We've returned to a previous state — cycle detected
                break
            visited_states.add(state_key)

        # Final message
        cycle_text = Text("Pattern repeats every 180°", font_size=30, color=GREEN).to_edge(DOWN)
        self.play(Write(cycle_text))

        # Hold
        self.wait(3)