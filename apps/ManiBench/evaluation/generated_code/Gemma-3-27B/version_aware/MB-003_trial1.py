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
        signal_label = Tex("Signal").next_to(signal_axis, UP)

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
        kernel_label = Tex("Kernel").next_to(kernel_axis, UP)
        kernel_axis.to_edge(RIGHT)

        output_axis = Axes(
            x_range=[0, len(output), 1],
            y_range=[0, max(signal) * max(kernel) + 1, 1],
            axis_config={"include_numbers": True},
        )
        output_axis.to_edge(DOWN)
        output_label = Tex("Convolution Output").next_to(output_axis, DOWN)
        output_dots = VGroup()

        self.play(Create(signal_axis), Write(signal_label))
        self.play(Create(signal_bars))
        self.play(Create(kernel_axis), Write(kernel_label))
        self.play(Create(kernel_bars))
        self.play(Create(output_axis), Write(output_label))

        for i in range(len(output)):
            # Slide the kernel
            kernel_rect = SurroundingRectangle(signal_bars[i:i+len(kernel)], color=YELLOW)
            self.play(kernel_rect.animate.shift(LEFT * 0.8))

            # Element-wise product
            product = 1
            for j in range(len(kernel)):
                product *= signal[i+j] * kernel[j]
            
            product_text = Tex(f"Product: {product:.2f}").to_edge(UL)
            self.play(Write(product_text))
            self.wait(0.5)
            self.play(Unwrite(product_text))

            # Accumulate output
            output[i] = product
            dot = Dot(output_axis.c2p(i, output[i]), color=RED)
            output_dots.add(dot)
            self.play(Create(dot))

            self.wait(0.5)
            kernel_rect.clear_up_to_date()

        self.wait(1)