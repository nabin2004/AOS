from manim import *
from manim_voiceover import VoiceoverScene

class LorenzAttractorScene(VoiceoverScene):
    def construct(self):
        # Scene 1: Introduction to Lorenz Attractor 
        self.play(Background(WHITE))

        lore_walk = ParametricFunction(
            lambda t: np.array([
                10 * (1 - np.cos(t)),
                28 * np.sin(t) - t,
                t
            ]),
            t_range=np.linspace(0, 40, 100),
            color=BLUE
        )

        self.play(Create(lore_walk))
        self.wait(2)
        self.play(Voiceover("The Lorenz attractor illustrates a complex set of trajectories in a three-dimensional space."))
        self.wait(2)
        self.play(Voiceover("Developed by Edward Lorenz, it models atmospheric convection, revealing how small changes can lead to drastically different outcomes."))
        self.wait(3)

        # Scene 2: Mathematical Background
        self.clear()
        equations = Text('''
dx/dt = sigma*(y - x)
dy/dt = x*(rho - z) - y
dz/dt = x*y - beta*z
        ''')
        self.play(Write(equations))
        self.wait(3)
        self.play(Voiceover("The equations governing the Lorenz attractor involve differential equations. Let's look at them closely to understand their significance."))
        self.wait(2)
        self.play(Voiceover("The first equation states that the rate of change of x depends on the difference between y and x."))
        self.wait(2)
        self.play(Voiceover("The second equation indicates that the change in y is influenced by both x and z."))
        self.wait(2)
        self.play(Voiceover("Lastly, the third equation describes how z changes due to a product of x and y."))
        self.wait(2)

        # Scene 3: Visualizing the Dynamics
        self.clear()
        trajectory = ParametricFunction(
            lambda t: np.array([
                10 * np.sin(t),
                28 * np.cos(t) - t,
                t
            ]),
            t_range=np.linspace(0, 40, 100),
            color=RED
        )

        self.play(FadeIn(trajectory))
        self.wait(2)
        self.play(GrowFromCenter(trajectory))
        self.wait(2)
        self.play(Voiceover("As we visualize the dynamics, you can see trajectories developing over time, exhibiting the chaotic nature of the Lorenz attractor."))
        self.wait(3)
        self.play(Voiceover("This chaotic behavior exemplifies how initial conditions significantly affect the system's evolution, a core concept in chaos theory."))
        self.wait(5)


