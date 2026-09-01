from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        # Signal and Kernel Data
        signal_data = [1, 2, 3, 4, 5, 4, 3, 2, 1]
        kernel_data = [0.5, 1, 0.5]
        kernel_length = len(kernel_data)
        signal_length = len(signal_data)

        # Create Axes
        axes_signal = Axes(
            x_range=[0, signal_length, 1],
            y_range=[0, max(signal_data) + 1, 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": False}
        )
        axes_output = Axes(
            x_range=[0, signal_length - kernel_length + 1, 1],
            y_range=[0, max(signal_data) * max(kernel_data) + 1, 1],
            x_length=6,
            y_length=3,
            axis_config={"include_numbers": False}
        )

        # Plot Signal
        signal_graph = axes_signal.plot(
            lambda x: signal_data[int(x)],
            x_range=[0, signal_length],
            color=BLUE,
            weight=0.8
        )
        signal_bars = VGroup(*[
            Rectangle(width=0.8, height=signal_data[i], fill_color=BLUE, stroke_color=BLUE)
            .move_to(axes_signal.c2p(i, 0))
            for i in range(signal_length)
        ])

        # Create Kernel Window
        kernel_window = SurroundingRectangle(
            signal_bars[0],
            color=GREEN,
            buff=0.1
        )

        # Labels
        signal_label = Tex("Signal", color=BLUE).to_corner(UL)
        kernel_label = Tex("Kernel", color=GREEN).to_corner(UR)
        output_label = Tex("Convolution Output", color=RED).to_corner(DR)

        self.play(Create(axes_signal), Create(axes_output), Write(signal_label), Write(kernel_label), Write(output_label))
        self.play(Create(signal_graph), Create(signal_bars))
        self.wait(1)

        # Convolution Calculation and Animation
        output_data = []
        for i in range(signal_length - kernel_length + 1):
            # Move Kernel Window
            self.play(kernel_window.animate.move_to(signal_bars[i].get_center()))

            # Highlight Element-wise Product
            product_region = VGroup(*[
                signal_bars[i + j] for j in range(kernel_length)
            ])
            product_highlight = SurroundingRectangle(
                product_region,
                color=YELLOW,
                opacity=0.5
            )
            self.play(Create(product_highlight))
            self.wait(0.5)
            self.play(Uncreate(product_highlight))

            # Calculate Convolution Value
            convolution_value = sum(signal_data[i + j] * kernel_data[j] for j in range(kernel_length))
            output_data.append(convolution_value)

            # Plot Output Point
            output_point = Dot(axes_output.c2p(i, convolution_value), color=RED)
            self.play(Create(output_point))

        # Plot Output Graph
        output_graph = axes_output.plot(
            lambda x: output_data[int(x)],
            x_range=[0, len(output_data)],
            color=RED
        )

        self.wait(1)
        self.play(Create(output_graph))
        self.wait(2)