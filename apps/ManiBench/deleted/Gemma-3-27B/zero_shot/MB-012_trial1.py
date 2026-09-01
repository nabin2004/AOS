from manim import *

class WindmillProblem(Scene):
    def construct(self):
        # Parameters
        n = 7  # Number of points
        radius = 4
        points = []
        for i in range(n):
            angle = i * PI / n
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            points.append(Point(x, y))

        # Create point objects
        point_objects = VGroup(*[Dot(point.coords, color=BLUE) for point in points])
        point_objects.arrange_in_circle(radius=radius)

        # Initial line
        line = Line(points[0].coords, points[1].coords, color=GREEN)

        # Angle of the line
        angle = line.get_angle()

        # Rotate the line
        self.play(Create(point_objects))
        self.play(Create(line))

        self.wait(1)

        for i in range(n - 1):
            next_point_index = (i + 2) % n
            next_point = points[next_point_index]

            # Calculate the angle to the next point
            next_angle = angle_between_points(line.get_end(), next_point)

            # Rotate the line
            self.play(
                Rotate(line, angle=next_angle - angle, about_point=line.get_center()),
                run_time=1
            )
            angle = next_angle
            self.wait(0.5)

        # Rotate through 180 degrees
        self.play(
            Rotate(line, angle=PI, about_point=line.get_center()),
            run_time=2
        )
        self.wait(1)

        # Show the pattern repeats
        self.play(
            Rotate(line, angle=-PI, about_point=line.get_center()),
            run_time=2
        )
        self.wait(1)

        self.play(FadeOut(point_objects, line))

def angle_between_points(p1, p2):
    """Calculates the angle between two points."""
    return np.arctan2(p2[1] - p1[1], p2[0] - p1[0])