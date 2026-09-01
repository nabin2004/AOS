from manim import *

class ChainRule(Scene):
    def construct(self):
        # Define the functions
        g = lambda x: x**2
        f = lambda u: np.exp(u)

        # Create the x-axis
        x_axis = NumberLine(x_range=[-5, 5, 1], include_numbers=True)

        # Create the u-axis
        u_axis = NumberLine(x_range=[-5, 5, 1], include_numbers=True)

        # Create the y-axis
        y_axis = NumberLine(x_range=[-5, 5, 1], include_numbers=True)

        # Create the g(x) function
        g_func = ParametricFunction(lambda t: np.array([t, g(t), 0]), t_range=[-5, 5, 0.1], color=BLUE)

        # Create the f(u) function
        f_func = ParametricFunction(lambda t: np.array([f(t), t, 0]), t_range=[-5, 5, 0.1], color=RED)

        # Create the labels
        g_label = Tex("g(x) = x^2").next_to(g_func, UP)
        f_label = Tex("f(u) = e^u").next_to(f_func, UP)

        # Create the derivative of g
        g_prime = ParametricFunction(lambda t: np.array([t, 2*t, 0]), t_range=[-5, 5, 0.1], color=YELLOW)

        # Create the derivative of f
        f_prime = ParametricFunction(lambda t: np.array([np.exp(t), t, 0]), t_range=[-5, 5, 0.1], color=YELLOW)

        # Create the labels for the derivatives
        g_prime_label = Tex("g'(x) = 2x").next_to(g_prime, UP)
        f_prime_label = Tex("f'(u) = e^u").next_to(f_prime, UP)

        # Create the composition of derivatives
        composition = Tex("d/dx[f(g(x))] = f'(g(x)) \\cdot g'(x)").scale(0.8)

        # Animate the functions
        self.play(Create(x_axis), Create(u_axis), Create(y_axis))
        self.play(Create(g_func), Create(g_label))
        self.play(Create(f_func), Create(f_label))
        self.play(Create(g_prime), Create(g_prime_label))
        self.play(Create(f_prime), Create(f_prime_label))

        # Animate the composition of derivatives
        self.play(Create(composition))

        # Animate the propagation of the infinitesimal change
        self.play(
            g_func.animate.shift(0.1*RIGHT),
            g_prime.animate.shift(0.1*RIGHT),
            f_func.animate.shift(0.1*RIGHT),
            f_prime.animate.shift(0.1*RIGHT),
            rate_func=linear
        )

        # Display the final result
        self.play(
            composition.animate.shift(2*DOWN),
            rate_func=linear
        )

        # Wait for the animation to finish
        self.wait(2)