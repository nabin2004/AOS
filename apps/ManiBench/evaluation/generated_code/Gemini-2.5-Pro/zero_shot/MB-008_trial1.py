from manim import *

class ChainRuleAnimation(Scene):
    def construct(self):
        # Set a light theme for better visibility
        self.camera.background_color = WHITE
        Text.set_default(color=BLACK)
        MathTex.set_default(color=BLACK)
        Mobject.set_default(color=BLACK)

        # 1. DEFINE FUNCTIONS AND AXES
        def g(x):
            return 0.25 * x**2 + 1

        def f(u):
            return 0.5 * np.sin(2 * (u - 1)) + 2.5

        def g_prime(x):
            return 0.5 * x

        def f_prime(u):
            return 1.0 * np.cos(2 * (u - 1))

        # Create axes for g(x) and f(u)
        ax1 = Axes(
            x_range=[-1, 4, 1], y_range=[0, 5, 1],
            x_length=6, y_length=4,
            axis_config={"color": BLACK, "include_tip": False},
        ).to_corner(UL, buff=1)

        ax2 = Axes(
            x_range=[0, 5, 1], y_range=[0, 4, 1],
            x_length=6,