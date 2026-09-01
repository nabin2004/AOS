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
        signal_graph = signal_axes.plot(
            lambda x: signal_data[int(x)], x_range=[0, signal_length - 1, 0.01], color=BLUE
        )
        signal_labels = Tex("Signal").next_to(signal_axes, UP)

        # Create the kernel as a rectangle
        kernel_rect = Rectangle(
            width=kernel_width,
            height=max(signal_data) * 0.3,
            color=GREEN,
            opacity=0.7,
        )
        kernel_labels = Tex("Kernel").next_to(kernel_rect, UP)

        # Create axes for the convolution output
        output_axes = Axes(
            x_range=[0, signal_length - kernel_width + 1, 1],
            y_range=[0, max(signal_data) * 2, 1],
            axis_config={"include_numbers": False},
        )
        output_graph = output_axes.plot(
            lambda x: 0, x_range=[0, signal_length - kernel_width, 0.01], color=RED
        )
        output_labels = Tex("Convolution Output").next_to(output_axes, UP)

        # Initial setup
        self.play(Create(signal_axes), Create(signal_graph), Write(signal_labels))
        self.play(Create(kernel_rect), Write(kernel_labels))
        self.play(Create(output_axes), Create(output_graph), Write(output_labels))
        self.wait(1)

        # Slide the kernel and calculate convolution
        convolution_output = []
        for i in range(signal_length - kernel_width + 1):
            # Move the kernel
            self.play(kernel_rect.animate.shift(RIGHT * 1))

            # Calculate element-wise product
            product = [signal_data[j + i] * kernel_data[j] for j in range(kernel_width)]

            # Highlight the product region
            highlight_rect = Rectangle(
                width=kernel_width,
                height=max(signal_data) * 0.3,
                color=YELLOW,
                opacity=0.5,
            ).move_to(signal_axes.c2p(i, 0))
            self.play(Create(highlight_rect))
            self.wait(0.5)
            self.play(Uncreate(highlight_rect))

            # Calculate the sum (integral)
            sum_val = sum(product)
            convolution_output.append(sum_val)

            # Add a point to the output graph
            point = Dot(output_axes.c2p(i, sum_val), color=RED)
            self.play(Create(point))
            self.wait(0.2)

        # Final state
        self.wait(2)