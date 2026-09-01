from manim import *

# Analysis:
# 1. Mobjects: Points (dots), Line
# 2. Order: Points appear, line appears, line rotates, pivot transitions, repeat rotation.
# 3. Transformations: Rotation, point transition (pivot change).
# 4. Timing: Rotation should be continuous. Pivot transitions should be synchronized with line reaching next point.
# 5. Labels: None.

class Windmill(Scene):
    def construct(self):
        n = 6
        points = [
            (-3, 2),
            (-1, -1),
            (1, 3),
            (2, -2),
            (4, 1),
            (3, -3)
        ]
        dots = [Dot(point, color=color, radius=0.1) for point, color in zip(points, [RED, GREEN, BLUE, YELLOW, PURPLE, ORANGE])]
        dots_group = VGroup(*dots)

        line = Line(LEFT, RIGHT)
        line.set_color(WHITE)

        pivot = dots[0]

        def get_line_angle(point):
            return angle_between_vectors(RIGHT, point - pivot)

        def update_line(angle):
            line.rotate(angle - line.angle)
            line.become(line.copy())
            line.put_at(pivot, LEFT)
            line.extend_to(pivot + line.get_unit_vector() * 5)

        def find_next_pivot(current_pivot_index):
            next_index = (current_pivot_index + 1) % n
            return dots[next_index]

        current_pivot_index = 0
        next_pivot = find_next_pivot(current_pivot_index)
        next_angle = get_line_angle(next_pivot)

        self.play(Create(dots_group), Create(line))
        self.wait(1)

        self.play(
            Rotate(line, angle=next_angle, run_time=3, about_point=pivot)
        )
        self.wait(1)

        current_pivot_index = 1
        next_pivot = find_next_pivot(current_pivot_index)
        next_angle = get_line_angle(next_pivot)

        self.play(
            Transform(pivot, next_pivot),
            Rotate(line, angle=next_angle - line.angle, run_time=3, about_point=pivot)
        )
        self.wait(1)

        current_pivot_index = 2
        next_pivot = find_next_pivot(current_pivot_index)
        next_angle = get_line_angle(next_pivot)

        self.play(
            Transform(pivot, next_pivot),
            Rotate(line, angle=next_angle - line.angle, run_time=3, about_point=pivot)
        )
        self.wait(1)

        current_pivot_index = 3
        next_pivot = find_next_pivot(current_pivot_index)
        next_angle = get_line_angle(next_pivot)

        self.play(
            Transform(pivot, next_pivot),
            Rotate(line, angle=next_angle - line.angle, run_time=3, about_point=pivot)
        )
        self.wait(1)

        current_pivot_index = 4
        next_pivot = find_next_pivot(current_pivot_index)
        next_angle = get_line_angle(next_pivot)

        self.play(
            Transform(pivot, next_pivot),
            Rotate(line, angle=next_angle - line.angle, run_time=3, about_point=pivot)
        )
        self.wait(1)

        current_pivot_index = 5
        next_pivot = find_next_pivot(current_pivot_index)
        next_angle = get_line_angle(next_pivot)

        self.play(
            Transform(pivot, next_pivot),
            Rotate(line, angle=next_angle - line.angle, run_time=3, about_point=pivot)
        )
        self.wait(1)