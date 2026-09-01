from manim import *

# Analysis:
# 1. Mobjects: Signal (bar chart), Kernel (rectangle), Product (text), Output (line graph), Axes.
# 2. Order: Signal & Kernel setup -> Sliding window animation -> Product highlight -> Output graph build.
# 3. Transformations: Shift, FadeIn, Create, Write, Transform.
# 4. Synchronization: Use `wait` and `animate` groups to control timing.
# 5. Labels: "Signal", "Kernel", "Convolution Output".

class ConvolutionAnimation(Scene):
    def construct(self):
        # Signal and Kernel data
        signal_data = [1, 2, 3, 4, 5]
        kernel_data = [0.5, 1, 0.5]

        # Create Axes for Signal
        signal_axes = Axes(
            x_range=[0, len(signal_data), 1],
            y_range=[0, max(signal_data) + 1, 1],
            axis_config={"include_numbers": False},
        )
        signal_axes.add_coordinate_labels()
        signal_axes.shift(UP * 1.5)
        signal_label = Tex("Signal").next_to(signal_axes, UP)

        # Create Signal bars
        signal_bars = VGroup(*[
            Rectangle(width=0.8, height=signal_data[i], fill_color=BLUE, stroke_color=BLUE)
            .move_to(signal_axes.c2p(i, 0))
            for i in range(len(signal_data))
        ])

        # Create Axes for Kernel
        kernel_axes = Axes(
            x_range=[0, len(kernel_data), 1],
            y_range=[0, max(kernel_data) + 1, 1],
            axis_config={"include_numbers": False},
        )
        kernel_axes.add_coordinate_labels()
        kernel_axes.shift(DOWN * 1.5)
        kernel_label = Tex("Kernel").next_to(kernel_axes, DOWN)

        # Create Kernel bars
        kernel_bars = VGroup(*[
            Rectangle(width=0.8, height=kernel_data[i], fill_color=GREEN, stroke_color=GREEN)
            .move_to(kernel_axes.c2p(i, 0))
            for i in range(len(kernel_data))
        ])

        # Create Axes for Convolution Output
        output_axes = Axes(
            x_range=[0, len(signal_data) - len(kernel_data) + 1, 1],
            y_range=[0, max(signal_data) * max(kernel_data) + 1, 1],
            axis_config={"include_numbers": False},
        )
        output_axes.add_coordinate_labels()
        output_axes.shift(LEFT * 3)
        output_label = Tex("Convolution Output").next_to(output_axes, LEFT)

        # Initial display
        self.play(Create(signal_axes), Write(signal_label))
        self.play(Create(signal_bars))
        self.play(Create(kernel_axes), Write(kernel_label))
        self.play(Create(kernel_bars))
        self.play(Create(output_axes), Write(output_label))

        # Sliding window animation
        for i in range(len(signal_data) - len(kernel_data) + 1):
            window_x = i
            window = Rectangle(width=len(kernel_data) * 0.8, height=max(kernel_data), fill_color=YELLOW, stroke_color=YELLOW, opacity=0.5)
            window.move_to(signal_axes.c2p(window_x, 0))

            # Element-wise product
            product = 0
            product_text = Tex(f"Product: {product}")
            product_text.move_to(signal_axes.c2p(window_x + len(kernel_data) / 2, 2))

            for j in range(len(kernel_data)):
                product += signal_data[window_x + j] * kernel_data[j]
                product_text.become_transform(Tex(f"Product: {product}"))
                self.play(
                    window.animate.shift(RIGHT * 0.8),
                    product_text.animate.shift(RIGHT * 0.8)
                )
                self.wait(0.5)

            # Output graph point
            point = Dot(output_axes.c2p(i, product), color=RED)
            self.play(Create(point))

            self.wait(0.5)

        self.wait(2)