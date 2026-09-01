from manim import *

class BlockCollisionPi(Scene):
    """
    An animation demonstrating the connection between elastic collisions
    of blocks and the digits of Pi, as popularized by 3Blue1Brown and
    based on the work of Gregory Galperin.

    The animation covers:
    1. A physical simulation of two blocks and a wall.
    2. The conservation laws of energy and momentum.
    3. A transition to a phase-space diagram where the dynamics
       become rotations.
    4. The geometric argument explaining why the number of collisions
       can be calculated using an angle derived from the mass ratio.
    5. A demonstration for various mass ratios, showing how the number
       of collisions approximates digits of Pi.
    """
    def construct(self):
        # --------------------------------------------------------------------
        # Introduction and Setup
        # --------------------------------------------------------------------
        intro_title = Text("The Block Collision Problem and π", font_size=48)
        self.play(Write(intro_title))
        self.wait(1)
        self.play(FadeOut(intro_title))

        # We use M/m = 100^k, so m/M = 100^-k.
        # The prompt's "m/M = 100" is interpreted as M/m = 100 for the pi connection to work.
        mass_ratio = 100