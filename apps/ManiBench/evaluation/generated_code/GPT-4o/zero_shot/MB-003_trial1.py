from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        # Define the signal and kernel
        signal = [1, 2, 3, 4, 3, 2, 1]
        kernel = [0.2, 0.5, 0.2]
        signal_length = len(signal)
        kernel_length = len(kernel)
        output_length = signal_length - kernel_length + 1

        # Axes for the signal, kernel, and output
        signal_axes = Axes(
            x_range=[0, signal_length, 1],
            y_range=[0, max(signal) + 1, 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True},
        ).to_edge(UP)

        kernel_axes = Axes(
            x_range=[0, kernel_length, 1],
            y_range=[0, max(kernel) + 0.5, 0.1],
            x_length=3,
            y_length=1.5,
            axis_config={"include_numbers": False},
        ).next_to(signal_axes, DOWN, buff=1)

        output_axes = Axes(
            x_range=[0, output_length, 1],
            y_range=[0, max(signal) * max(kernel) * kernel_length + 1, 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True},
        ).next_to(signal_axes, DOWN, buff=2.5)

        # Labels
        signal_label = Text("Signal").next_to(signal_axes, UP)
        kernel_label = Text("Kernel").next_to(kernel_axes, UP)
        output_label = Text("Convolution Output").next_to(output_axes, UP)

        # Plot the signal and kernel
        signal_bars = signal_axes.get_bar_graph(
            signal, bar_colors=[BLUE], bar_width=0.8
        )
        kernel_bars = kernel_axes.get_bar_graph(
            kernel, bar_colors=[GREEN], bar_width=0.8
        )

        # Add axes, labels, and initial plots
        self.play(
            Create(signal_axes),
            Create(kernel_axes),
            Create(output_axes),
            Write(signal_label),
            Write(kernel_label),
            Write(output_label),
        )
        self.play(Create(signal_bars), Create(kernel_bars))

        # Sliding kernel and convolution output
        output_values = []
        output_dots = VGroup()
        sliding_window = kernel_axes.get_bar_graph(
            kernel, bar_colors=[YELLOW], bar_width=0.8
        ).move_to(signal_axes.c2p(0, 0), aligned_edge=LEFT)

        self.play(FadeIn(sliding_window))

        for i in range(output_length):
            # Move the sliding window
            target_position = signal_axes.c2p(i, 0)
            self.play(sliding_window.animate.move_to(target_position, aligned_edge=LEFT))

            # Highlight element-wise multiplication
            elementwise_products = [
                signal[j + i] * kernel[j] for j in range(kernel_length)
            ]
            product_bars = signal_axes.get_bar_graph(
                elementwise_products, bar_colors=[RED], bar_width=0.8
            ).move_to(target_position, aligned_edge=LEFT)

            self.play(FadeIn(product_bars))
            self.wait(0.5)

            # Compute and display the sum
            output_value = sum(elementwise_products)
            output_values.append(output_value)
            output_dot = Dot(output_axes.c2p(i, output_value), color=YELLOW)
            output_dots.add(output_dot)

            self.play(FadeOut(product_bars), FadeIn(output_dot))
            self.wait(0.5)

        # Connect the dots to form the output graph
        output_graph = output_axes.plot_line_graph(
            x_values=range(output_length),
            y_values=output_values,
            line_color=YELLOW,
        )

        self.play(Create(output_graph))
        self.wait(2)