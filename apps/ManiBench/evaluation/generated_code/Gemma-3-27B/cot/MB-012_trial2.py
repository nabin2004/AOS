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

        line = Line(start=(-5, 0), end=(5, 0), color=WHITE)

        def get_angle(point):
            return np.arctan2(point[1], point[0])

        def rotate_line(angle):
            line.rotate(angle, about_point=ORIGIN)

        def get_pivot_point(i):
            return points[i]

        pivot_index = 0
        pivot_point = get_pivot_point(pivot_index)

        line.point_from_proportion(0).move_to(pivot_point)
        line.point_from_proportion(1).move_to(pivot_point + (5, 0))

        self.play(Create(dots_group), Create(line))
        self.wait(1)

        angle = 0
        while angle < 180:
            angle += 0.5
            rotate_line(angle * DEGREES)
            self.wait(0.01)

            # Check if line is about to lose a point
            next_pivot_index = (pivot_index + 1) % n
            next_pivot_point = get_pivot_point(next_pivot_index)
            next_angle = get_angle(next_pivot_point)
            
            if abs(angle - next_angle) < 2:
                pivot_index = next_pivot_index
                pivot_point = get_pivot_point(pivot_index)
                line.point_from_proportion(0).move_to(pivot_point)
                line.point_from_proportion(1).move_to(pivot_point + (5, 0))
                self.wait(0.2)

        self.wait(2)