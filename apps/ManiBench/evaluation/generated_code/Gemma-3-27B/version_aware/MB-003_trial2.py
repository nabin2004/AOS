from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        signal = [1, 2, 3, 4, 5]
        kernel = [0.5, 1, 0.5]
        output = [0] * (len(signal) - len(kernel) + 1)

        signal_axis = Axes(
            x_range=[0, len(signal), 1],
            y_range=[0, max(signal) + 1, 1],
            axis_config={"include_numbers": True},
        )
        signal_bars = VGroup(*[
            Rectangle(width=0.8, height=s, fill_color=BLUE, stroke_color=BLACK)
            for s in signal
        ]).arrange(RIGHT, aligned_edge=DOWN)
        signal_bars.next_to(signal_axis, UP)
        signal_label = Tex("Signal", font_size=24).next_to(signal_bars, UP)

        kernel_axis = Axes(
            x_range=[0, len(kernel), 1],
            y_range=[0, max(kernel) + 1, 1],
            axis_config={"include_numbers": True},
        )
        kernel_bars = VGroup(*[
            Rectangle(width=0.8, height=k, fill_color=GREEN, stroke_color=BLACK)
            for k in kernel
        ]).arrange(RIGHT, aligned_edge=DOWN)
        kernel_bars.next_to(kernel_axis, UP)
        kernel_label = Tex("Kernel", font_size=24).next_to(kernel_bars, UP)

        output_axis = Axes(
            x_range=[0, len(output), 1],
            y_range=[0, max(signal) * max(kernel) + 1, 1],
            axis_config={"include_numbers": True},
        )
        output_dots = VGroup()
        output_label = Tex("Convolution Output", font_size=24).next_to(output_axis, UP)

        self.play(Create(signal_axis), Write(signal_label))
        self.play(Create(signal_bars))
        self.play(Create(kernel_axis), Write(kernel_label))
        self.play(Create(kernel_bars))
        self.play(Create(output_axis), Write(output_label))

        for i in range(len(output)):
            # Slide the kernel
            kernel_rect = SurroundingRectangle(signal_bars[i:i+len(kernel)], color=YELLOW)
            self.play(kernel_rect.animate.shift(LEFT * 0.5))

            # Element-wise product
            product = [signal[i+j] * kernel[j] for j in range(len(kernel))]
            product_text = MathTex(*[str(p) for p in product], delimiter="\\times").scale(0.7).next_to(kernel_rect, DOWN)
            self.play(Write(product_text))
            self.wait(0.5)
            self.play(FadeOut(product_text))

            # Accumulate the sum
            output[i] = sum(product)
            dot = Dot(output_axis.coords_to_point(i, output[i]), color=RED)
            output_dots.add(dot)
            self.play(Create(dot))

            self.wait(0.5)
            self.play(FadeOut(kernel_rect))

        self.wait(2)