from manim import *
import numpy as np

class WindmillProblem(Scene):
    def construct(self):
        n = 7  # Number of points
        points = [
            np.random.uniform(-4, 4, 2) for _ in range(n)
        ]
        points = [Point(p[0], p[1]) for p in points]

        line = Line(start=LEFT * 5, end=RIGHT * 5, color=BLUE)
        line.rotate(PI / 2)  # Start horizontal

        self.play(Create(line))
        for point in points:
            self.play(Create(point))
        self.wait(1)

        # Find initial two points on the line
        p1, p2 = self.find_initial_points(line, points)
        line.put_start_and_end_on(p1, p2)

        angle = 0
        angular_velocity = 0.02
        pivot_threshold = 0.1  # Distance threshold for pivoting

        while angle < PI:
            line.rotate(angular_velocity, about_point=ORIGIN)
            angle += angular_velocity
            self.wait(0.02)

            # Check for points about to be lost
            lost_point = self.find_lost_point(line, points)
            if lost_point:
                # Find a new point to pick up
                new_point = self.find_new_point(line, points, lost_point)
                if new_point:
                    # Pivot the line
                    pivot_angle = angle_between_vectors(line.get_end() - line.get_start(), new_point - line.get_start())
                    line.rotate(-pivot_angle, about_point=line.get_start())
                    self.play(Rotate(line, pivot_angle, about_point=line.get_start()), run_time=0.3)
                    self.wait(0.1)

        self.wait(2)

    def find_initial_points(self, line, points):
        # Find two points closest to the initial line
        distances = [line.distance_point_to_line(p) for p in points]
        indices = np.argsort(distances)[:2]
        return points[indices[0]], points[indices[1]]

    def find_lost_point(self, line, points):
        # Find a point that is about to be on the "wrong" side of the line
        for point in points:
            if line.distance_point_to_line(point) < pivot_threshold:
                return point
        return None

    def find_new_point(self, line, points, lost_point):
        # Find a point that is furthest from the line on the other side
        max_distance = -1
        new_point = None
        for point in points:
            if point != lost_point:
                distance = line.distance_point_to_line(point)
                if distance > max_distance:
                    max_distance = distance
                    new_point = point
        return new_point