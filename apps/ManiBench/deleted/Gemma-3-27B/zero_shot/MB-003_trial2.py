from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        # Define signal and kernel
        signal = [1, 2, 3, 4, 5, 4, 3, 2, 1]
        kernel = [0.1, 0.2, 0.3, 0.2, 0.1]
        kernel_size = len(kernel)
        signal_len = len(signal)

        # Create axes for signal and output
        signal_ax = Axes(
            x_range=[0, signal_len],
            y_range=[0, max(signal) + 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True},
        )
        signal_ax.add_coordinate_labels()
        signal_ax.axis.set_color(BLUE)
        signal_label = Text("Signal", color=BLUE).next_to(signal_ax, UP)

        output_ax = Axes(
            x_range=[0, signal_len - kernel_size + 1],
            y_range=[0, max(signal) * max(kernel) + 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True},
        )
        output_ax.add_coordinate_labels()
        output_ax.axis.set_color(GREEN)
        output_label = Text("Convolution Output", color=GREEN).next_to(output_ax, UP)

        # Plot signal
        signal_graph = signal_ax.plot(
            [(i, signal[i]) for i in range(signal_len)], color=BLUE
        )

        # Create kernel representation
        kernel_rects = VGroup(
            *[
                Rectangle(width=1, height=kernel[i], color=RED)
                for i in range(kernel_size)
            ]
        ).arrange(RIGHT, aligned_edge=DOWN)
        kernel_label = Text("Kernel", color=RED).next_to(kernel_rects, UP)

        # Initial position of kernel
        kernel_rects.move_to(signal_ax.coords_to_point(0, 0))

        # Output graph
        output_graph = VGroup()

        # Animation
        self.play(Create(signal_ax), Create(signal_graph), Write(signal_label))
        self.play(Create(output_ax), Write(output_label))
        self.play(Create(kernel_rects), Write(kernel_label))

        for i in range(signal_len - kernel_size + 1):
            # Move kernel
            self.play(
                kernel_rects.animate.shift(RIGHT * 1)
            )

            # Calculate convolution value
            convolution_value = sum(
                signal[i + j] * kernel[j] for j in range(kernel_size)
            )

            # Add point to output graph
            point = Dot(output_ax.coords_to_point(i, convolution_value), color=GREEN)
            output_graph.add(point)
            self.play(Create(point))

        self.play(FadeOut(kernel_rects), FadeOut(kernel_label))
        self.wait(2)