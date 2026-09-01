from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        # Signal and Kernel data
        signal_data = [1, 2, 3, 4, 5, 4, 3, 2, 1]
        kernel_data = [0.5, 1, 0.5]
        kernel_width = len(kernel_data)
        signal_length = len(signal_data)

        # Create axes for the signal
        signal_axes = Axes(
            x_range=[0, signal_length, 1],
            y_range=[0, max(signal_data) * 1.2, 1],
            axis_config={"include_numbers": False},
        )
        signal_axes.add_coordinate_labels()
        signal_graph = signal_axes.plot(
            lambda x: signal_data[int(x)], x_range=[0, signal_length - 1, 0.1], color=BLUE
        )
        signal_axes.add(signal_graph)
        signal_label = Tex("Signal", color=BLUE).next_to(signal_axes, UP)

        # Create kernel as a rectangle
        kernel_rect = Rectangle(
            width=kernel_width,
            height=max(signal_data) * 0.5,
            color=GREEN,
            opacity=0.7,
        )

        # Create axes for the convolution output
        output_axes = Axes(
            x_range=[0, signal_length - kernel_width + 1, 1],
            y_range=[0, max(signal_data) * 2, 1],
            axis_config={"include_numbers": False},
        )
        output_axes.add_coordinate_labels()
        output_graph = output_axes.plot(
            lambda x: 0, x_range=[0, signal_length - kernel_width, 0.1], color=RED
        )
        output_axes.add(output_graph)
        output_label = Tex("Convolution Output", color=RED).next_to(output_axes, UP)

        kernel_label = Tex("Kernel", color=GREEN).next_to(kernel_rect, UP)

        self.play(Create(signal_axes), Create(signal_graph), Write(signal_label))
        self.wait(1)

        self.play(Create(kernel_rect), Write(kernel_label))
        self.wait(1)

        # Animate the sliding window
        for i in range(signal_length - kernel_width + 1):
            kernel_rect.move_to(signal_axes.c2p(i, 0), aligned_edge=LEFT)

            # Highlight the element-wise product
            product_sum = 0
            for j in range(kernel_width):
                product = signal_data[i + j] * kernel_data[j]
                product_sum += product

            product_text = Tex(f"Product: {product_sum:.2f}", color=YELLOW)
            product_text.move_to(signal_axes.c2p(i + kernel_width / 2, max(signal_data) * 1.1), aligned_edge=LEFT)

            # Add point to the output graph
            output_point = Dot(output_axes.c2p(i, product_sum), color=RED)
            output_graph.add_data_point(output_axes.c2p(i, product_sum))

            self.play(
                MoveToTarget(kernel_rect),
                Write(product_text),
                Create(output_point),
            )
            self.wait(0.5)
            self.remove(product_text)

        self.play(Create(output_axes), Create(output_graph), Write(output_label))
        self.wait(2)