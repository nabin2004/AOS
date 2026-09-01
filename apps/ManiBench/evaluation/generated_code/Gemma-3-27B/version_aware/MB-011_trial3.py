from manim import *

class HairyBallTheorem(ThreeDScene):
    def construct(self):
        sphere = Sphere(radius=2, resolution=(32, 32))
        sphere.set_shade_in_3d(True)

        self.play(Create(sphere))
        self.wait(1)

        self.camera.reorient(phi=75 * DEGREES, theta=45 * DEGREES)
        self.play(Rotate(sphere, angle=TAU, axis=Z_AXIS, run_time=5))

        # Vector field
        num_vectors = 64
        vectors = VGroup()
        for i in range(num_vectors):
            angle1 = i / num_vectors * TAU
            angle2 = np.random.uniform(0, TAU)
            x = np.cos(angle1) * np.sin(angle2)
            y = np.sin(angle1) * np.sin(angle2)
            z = np.cos(angle2)
            
            vector = Arrow3D(tip_length=0.2, color=BLUE)
            vector.set_direction(x * RIGHT + y * UP + z * OUT)
            vector.move_to(sphere.point_from_angle(angle1, angle2))
            vectors.add(vector)

        self.play(Create(vectors))
        self.wait(2)

        # Attempt to comb
        self.play(
            vectors.animate.set_color(RED),
            run_time=2
        )
        self.wait(1)

        # Highlight bald spot
        bald_spot = sphere.point_from_angle(0, 0)
        dot = SmallCircle(radius=0.1, color=YELLOW)
        dot.move_to(bald_spot)
        
        self.play(Create(dot))
        self.wait(2)

        # Combing failure animation
        for i in range(num_vectors):
            angle1 = i / num_vectors * TAU
            angle2 = np.random.uniform(0, TAU)
            x = np.cos(angle1) * np.sin(angle2)
            y = np.sin(angle1) * np.sin(angle2)
            z = np.cos(angle2)
            
            vector = vectors[i]
            
            if i % 2 == 0:
                vector.animate.set_direction(x * RIGHT + y * UP + z * OUT).set_color(GREEN)
            else:
                vector.animate.set_direction(-x * RIGHT - y * UP - z * OUT).set_color(ORANGE)
            
            self.play(
                vector.animate,
                run_time=0.05
            )
        
        self.wait(2)
        
        self.play(
            FadeOut(sphere, vectors, dot),
            run_time=1
        )