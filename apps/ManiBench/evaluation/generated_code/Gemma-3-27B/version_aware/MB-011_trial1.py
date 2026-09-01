from manim import *

class HairyBallTheorem(ThreeDScene):
    def construct(self):
        sphere = Sphere(radius=2, resolution=(32, 32))
        sphere.set_shade_in_3d(True)

        self.play(Create(sphere))
        self.wait(1)

        self.camera.recenter(sphere)
        self.camera.set_euler_angles(theta=30 * DEGREES, phi=45 * DEGREES)
        self.play(self.camera.rotate(axis=UP, angle=TAU, run_time=5))

        num_arrows = 100
        arrows = VGroup()
        for i in range(num_arrows):
            theta = i / num_arrows * TAU
            phi = np.random.uniform(0, TAU)
            x = sphere.radius * np.sin(phi) * np.cos(theta)
            y = sphere.radius * np.sin(phi) * np.sin(theta)
            z = sphere.radius * np.cos(phi)
            point = np.array([x, y, z])

            # Tangent vector (approximation)
            dx = np.cos(phi) * np.cos(theta)
            dy = np.cos(phi) * np.sin(theta)
            dz = -np.sin(phi)
            vector = np.array([dx, dy, dz])
            vector = vector / np.linalg.norm(vector) * 0.5

            arrow = Arrow(start=point, end=point + vector, color=BLUE, stroke_width=1)
            arrows.add(arrow)

        self.play(Create(arrows))
        self.wait(2)

        # Attempt to comb the vectors
        self.play(
            arrows.animate.shift(DOWN * 0.5)
        )
        self.wait(1)

        # Highlight a bald spot
        bald_spot = Sphere(radius=0.1, color=RED)
        bald_spot.move_to(np.array([0, 0, sphere.radius]))
        self.play(Create(bald_spot))
        self.wait(2)

        # Show the failure of continuous orientation
        self.play(
            arrows.animate.set_color(RED),
            bald_spot.animate.set_color(YELLOW)
        )
        self.wait(2)

        self.play(
            FadeOut(sphere, arrows, bald_spot)
        )
        self.wait(1)