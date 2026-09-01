from manim import *

class Convolution1D(Scene):
    def construct(self):
        # Set up axes
        signal_axes = Axes(
            x_range=[-1, 10, 1],
            y_range=[0, 4, 1],
            axis_config={"include_numbers": True},
            x_length=10,
            y_length=3
        ).shift(UP * 2)
        signal_label = Text("Signal", font_size=24).next_to(signal_axes, UP)

        output_axes = Axes(
            x_range=[-1, 10, 1],
            y_range=[0, 15, 5],
            axis_config={"include_numbers": True},
            x_length=10,
            y_length=3
        ).shift(DOWN * 2)
        output_label = Text("Convolution Output", font_size=24).next_to(output_axes, UP)

        # Define signal and kernel
        signal_values = [0, 0, 1, 3, 2, 1, 3, 0, 0, 0, 0]
        kernel_values = [1, 0.5, 0.25]
        kernel_label = Text("Kernel", font_size=20).next_to(signal_axes, DOWN)

        # Create signal bars
        signal_bars = VGroup()
        for x, val in enumerate(signal_values):
            bar = Rectangle(
                height=val * 0.5,
                width=0.5,
                fill_color=BLUE,
                fill_opacity=0.8,
                stroke_width=1
            ).move_to(signal_axes.c2p(x, val / 2), aligned_edge=DOWN)
            signal_bars.add(bar)

        # Create kernel bars (sliding window)
        kernel_bars = VGroup()
        for i, val in enumerate(kernel_values):
            bar = Rectangle(
                height=val * 0.5,
                width=0.5,
                fill_color=RED,
                fill_opacity=0.8,
                stroke_width=1
            )
            kernel_bars.add(bar)
        # Position kernel initially
        for i, bar in enumerate(kernel_bars):
            bar.move_to(signal_axes.c2p(i, kernel_values[i] / 2), aligned_edge=DOWN)

        # Convolution output points
        output_dots = VGroup()
        conv_values = []

        # Add everything to scene
        self.play(
            Create(signal_axes),
            Write(signal_label),
            Create(output_axes),
            Write(output_label),
            Write(kernel_label)
        )
        self.play(Create(signal_bars), Create(kernel_bars))

        # Animate sliding and convolution
        for i in range(len(signal_values) - len(kernel_values) + 1):
            # Highlight current region
            current_region = Rectangle(
                width=1.5,
                height=2,
                color=YELLOW,
                fill_opacity=0.2
            ).move_to(signal_axes.c2p(i + 1, 1), aligned_edge=DOWN)
            if i == 0:
                self.play(FadeIn(current_region))
            else:
                self.play(current_region.animate.move_to(signal_axes.c2p(i + 1, 1), aligned_edge=DOWN))

            # Show element-wise multiplication
            product_texts = VGroup()
            product_sum = 0
            for j in range(len(kernel_values)):
                x_pos = i + j
                product = signal_values[x_pos] * kernel_values[j]
                product_sum += product
                text = MathTex(f"{signal_values[x_pos]}\\cdot{kernel_values[j]}", font_size=30)
                text.next_to(signal_axes.c2p(x_pos, max(signal_values[x_pos], kernel_values[j]) + 0.5), UP)
                product_texts.add(text)
            self.play(Write(product_texts))

            # Move kernel
            self.play(
                kernel_bars.animate.shift(RIGHT * signal_axes.x_axis.unit_size),
                run_time=0.5
            )

            # Show sum
            sum_text = MathTex(f"={product_sum:.2f}", font_size=36).next_to(product_texts, RIGHT)
            self.play(Write(sum_text))

            # Record convolution value
            conv_values.append(product_sum)
            dot = Dot(output_axes.c2p(i, product_sum), color=GREEN, radius=0.05)
            output_dots.add(dot)
            self.play(FadeIn(dot), run_time=0.3)

            # Connect dots if not first
            if len(output_dots) > 1:
                line = Line(
                    output_dots[-2].get_center(),
                    output_dots[-1].get_center(),
                    color=GREEN
                )
                self.play(Create(line), run_time=0.3)

            self.play(FadeOut(product_texts, sum_text), run_time=0.3)

        # Final touches
        self.play(FadeOut(current_region))
        self.wait(2)