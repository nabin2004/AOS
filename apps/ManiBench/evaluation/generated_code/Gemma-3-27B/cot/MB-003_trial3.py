from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        # 1. Signal and Kernel
        signal = [1, 2, 3, 4, 5]
        kernel = [0.5, 1, 0.5]
        n = len(signal)
        k = len(kernel)

        # Create signal as a bar chart
        signal_bars = VGroup(*[Bar(height=val, width=0.8, color=BLUE, stroke_width=0) for val in signal])
        signal_bars.arrange(RIGHT, aligned_edge=DOWN)
        signal_label = Tex("Signal", color=BLUE).next_to(signal_bars, UP)

        # Create kernel as a rectangle
        kernel_rect = Rectangle(width=k * 0.8, height=0.5, color=GREEN, stroke_width=0)
        kernel_label = Tex("Kernel", color=GREEN).next_to(kernel_rect, UP)

        # 2. Output Graph (Axes)
        axes = Axes(x_range=[0, n], y_range=[0, max(signal) * max(kernel)], x_length=5, y_length=3, axis_config={"color": GREY})
        axes.add_coordinate_labels()
        convolution_output_graph = axes.plot_line([], color=RED)
        convolution_label = Tex("Convolution Output", color=RED).next_to(axes, UP)

        # Group initial elements
        self.play(Create(signal_bars), Write(signal_label), Create(kernel_rect), Write(kernel_label), Create(axes), Write(convolution_label))

        # 3. Sliding Window and Convolution Calculation
        output = []
        for i in range(n - k + 1):
            # Move Kernel
            kernel_rect.move_to(signal_bars[i].get_center() + DOWN * 0.5)

            # Highlight element-wise product
            product = [signal[j] * kernel[j] for j in range(k)]
            product_text = MathTex(*[str(p) for p in product], color=YELLOW).next_to(kernel_rect, DOWN)

            # Calculate convolution output
            convolution_value = sum(product)
            output.append(convolution_value)

            # Update output graph
            convolution_output_graph.add_data_point((i, convolution_value))

            self.play(
                MoveToTarget(kernel_rect),
                Write(product_text),
                Create(convolution_output_graph),
            )
            self.wait(0.5)
            self.play(FadeOut(product_text))

        # Final state
        self.play(FadeOut(kernel_rect), FadeOut(signal_bars), FadeOut(signal_label), FadeOut(kernel_label))
        self.wait(1)