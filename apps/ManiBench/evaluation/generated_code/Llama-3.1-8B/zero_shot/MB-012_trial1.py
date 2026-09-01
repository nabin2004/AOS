from manim import *

class WindmillProblem(Scene):
    def construct(self):
        # Step 1: Create a set of n points scattered randomly
        n = 7
        points = []
        for i in range(n):
            x = random.uniform(-5, 5)
            y = random.uniform(-5, 5)
            points.append(Point(x, y))
        self.play(ShowCreation(VGroup(*points)), run_time=2)

        # Step 2: Create a line starting horizontal, passing through two points
        line = Line(points[0], points[1])
        self.play(ShowCreation(line), run_time=2)

        # Step 3: Rotate the line continuously
        angle = 0
        while angle < 180:
            self.clear()
            self.play(ShowCreation(VGroup(*points)), run_time=2)
            self.play(ShowCreation(line), run_time=2)
            self.play(Rotate(line, angle), run_time=2)
            angle += 10

            # Step 4: Whenever the line is about to lose a point, it pivots to pick up a new point
            if line.is_anti_clockwise(points[0], points[1]):
                new_point = points[0]
                old_point = points[1]
                points[1] = new_point
                line.become(Line(points[0], points[1]))
            else:
                new_point = points[1]
                old_point = points[0]
                points[0] = new_point
                line.become(Line(points[0], points[1]))

            # Step 5: Animate the pivoting process
            self.play(ShowCreation(VGroup(*points)), run_time=2)
            self.play(ShowCreation(line), run_time=2)
            self.play(Rotate(line, angle), run_time=2)

            # Step 6: Show the line rotating through a full 180°, demonstrating that the pattern repeats
            if angle > 180:
                angle = 0

            # Step 7: Visualize the 'windmill' motion dynamically
            self.play(ShowCreation(VGroup(*points)), run_time=2)
            self.play(ShowCreation(line), run_time=2)
            self.play(Rotate(line, angle), run_time=2)