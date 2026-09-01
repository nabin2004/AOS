from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        # Signal and Kernel
        signal = [1, 2, 3, 4, 5]
        kernel = [0.5, 1, 0.5]
        n_signal = len(signal)
        n_kernel = len(kernel)

        # Axes for Signal and Output
        axes_signal = Axes(x_range=[0, n_signal], y_range=[0, 6], axis_config={"include_numbers": True})
        axes_output = Axes(x_range=[0, n_signal - n_kernel + 1], y_range=[0, 10], axis_config={"include_numbers": True})

        # Labels
        signal_label = Text("Signal", font_size=24).to_edge(UL)
        kernel_label = Text("Kernel", font_size=24).to_edge(UR)
        output_label = Text("Convolution Output", font_size=24).to_edge(DL)

        # Signal Bar Chart
        signal_bars = VGroup(*[Bar(x=i, height=signal[i], width=0.8, color=BLUE) for i in range(n_signal)])
        signal_bars.move_to(axes_signal.get_origin())

        # Kernel Representation (Rectangle)
        kernel_rect = Rectangle(width=n_kernel, height=1, color=GREEN, fill_opacity=0.5)
        kernel_rect.move_to(axes_signal.c2p(0, 0))

        # Output Graph
        output_graph = axes_output.plot(lambda x: 0, color=RED)
        output_points = []

        # Convolution Calculation and Animation
        self.play(Create(axes_signal), Write(signal_label), Create(signal_bars), Create(axes_output), Write(output_label))
        self.play(Create(kernel_rect), Write(kernel_label))
        self.wait(1)

        for i in range(n_signal - n_kernel + 1):
            # Move Kernel
            self.play(kernel_rect.animate.shift(RIGHT * 1))

            # Element-wise Product
            product = 0
            product_terms = []
            for j in range(n_kernel):
                term = signal[i + j] * kernel[j]
                product += term
                product_terms.append(MathTex(f"{signal[i+j]} \\times {kernel[j]} = {term}").next_to(kernel_rect, DOWN, buff=0.5 * j))

            self.play(*[Write(term) for term in product_terms])
            self.wait(0.5)
            self.play(*[FadeOut(term) for term in product_terms])

            # Update Output Graph
            new_point = axes_output.c2p(i, product)
            dot = Dot(new_point, color=RED)
            output_points.append(dot)
            self.play(Create(dot))

            # Update Output Graph Line
            output_graph.add_points_as_corners(output_points)

        self.wait(2)
        self.play(FadeOut(kernel_rect, signal_bars, output_graph, *output_points))
        self.play(Write(Text("Convolution Complete!", font_size=36, color=GREEN).move_to(axes_signal.get_origin())))
        self.wait(1)