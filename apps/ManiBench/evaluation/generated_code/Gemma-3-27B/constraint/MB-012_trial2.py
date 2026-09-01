from manim import *
import numpy as np

class Windmill(Scene):
    def construct(self):
        n = 6
        points = []
        for i in range(n):
            x = np.random.uniform(-5, 5)
            y = np.random.uniform(-3, 3)
            point = Dot(np.array([x, y, 0]), color=BLUE, radius=0.2)
            points.append(point)
            self.add(point)

        self.wait(1)

        initial_point = points[0]
        line = Line(start=np.array([-5, initial_point.y, 0]), end=np.array([5, initial_point.y, 0]), color=RED)
        self.add(line)

        self.wait(1)

        pivot_point = initial_point
        pivot_point.set_color(GREEN)
        pivot_point.scale(1.2)

        angle = 0
        rotation_speed = 0.1
        
        for i in range(1, n):
            next_point = points[i]
            
            angle_to_next = np.arctan2(next_point.y - pivot_point.y, next_point.x - pivot_point.x)
            
            rotation_angle = angle_to_next
            
            self.play(Rotate(line, angle=rotation_angle, about_point=pivot_point.get_center(), run_time=2))
            
            self.wait(0.5)
            
            pivot_point.set_color(BLUE)
            pivot_point.scale(1)
            next_point.set_color(GREEN)
            next_point.scale(1.2)
            
            self.play(
                Transform(pivot_point, next_point),
                FadeOut(line),
                Create(Line(start=np.array([-5, pivot_point.y, 0]), end=np.array([5, pivot_point.y, 0]), color=RED))
            )
            
            pivot_point.set_color(GREEN)
            pivot_point.scale(1.2)
            
            self.wait(0.5)
            
            angle += rotation_angle
            
        self.wait(2)
        
        self.play(Rotate(line, angle=180, about_point=pivot_point.get_center(), run_time=3))
        self.wait(1)