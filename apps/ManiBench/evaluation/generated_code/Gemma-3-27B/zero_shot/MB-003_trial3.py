from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        # Define signal and kernel
        signal = [1, 2, 3, 4, 5, 4, 3, 2, 1]
        kernel = [0.2, 0.4, 0.4]
        kernel_size = len(kernel)
        signal_length = len(signal)

        # Create axes for signal and output
        signal_axis = NumberPlane(
            x_range=[0, signal_length],
            y_range=[0, max(signal) + 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True}
        )
        signal_axis.add_coordinate_labels()
        signal_axis.shift(LEFT * 2)

        output_axis = NumberPlane(
            x_range=[0, signal_length - kernel_size + 1],
            y_range=[0, max(signal) * max(kernel) + 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": True}
        )
        output_axis.add_coordinate_labels()
        output_axis.shift(RIGHT * 2)

        # Plot signal
        signal_graph = VGroup(*[
            Dot(signal_axis.coords_to_point(i, signal[i]), color=BLUE)
            for i in range(signal_length)
        ])
        signal_line = VMobject(color=BLUE)
        signal_line.set_points_as_corners(signal_graph.get_points())
        signal_group = VGroup(signal_line, signal_graph)

        # Create kernel as a rectangle
        kernel_rect = Rectangle(width=kernel_size, height=max(kernel), color=GREEN)
        kernel_rect.move_to(signal_axis.coords_to_point(-1, max(kernel) / 2))

        # Label signal and kernel
        signal_label = Tex("Signal", color=BLUE).next_to(signal_axis, UP)
        kernel_label = Tex("Kernel", color=GREEN).next_to(kernel_rect, UP)

        # Output graph
        output_graph = VGroup()
        output_label = Tex("Convolution Output", color=RED).next_to(output_axis, UP)

        # Show initial setup
        self.play(Create(signal_axis), Create(output_axis), Write(signal_label), Write(kernel_label))
        self.play(Create(signal_group), Create(kernel_rect))

        # Convolution animation
        for i in range(signal_length - kernel_size + 1):
            # Move kernel
            kernel_rect.move_to(signal_axis.coords_to_point(i, max(kernel) / 2))

            # Element-wise product
            product = 0
            product_terms = VGroup()
            for j in range(kernel_size):
                val = signal[i + j] * kernel[j]
                product += val
                term_text = Tex(f"({signal[i + j]} * {kernel[j]}) = {val}", color=YELLOW).next_to(kernel_rect, DOWN, buff=0.2)
                product_terms.add(term_text)

            self.play(
                MoveToTarget(kernel_rect),
                Create(product_terms)
            )
            self.wait(0.5)
            self.play(FadeOut(product_terms))

            # Add to output graph
            dot = Dot(output_axis.coords_to_point(i, product), color=RED)
            output_graph.add(dot)

            self.play(Create(dot))
            self.wait(0.2)

        # Connect output points
        output_line = VMobject(color=RED)
        output_line.set_points_as_corners(output_graph.get_points())
        output_group = VGroup(output_line, output_graph)

        self.play(Create(output_group), Write(output_label))

        self.wait(2)