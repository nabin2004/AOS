from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        # Define signal and kernel
        signal = [1, 2, 3, 4, 5]
        kernel = [0.1, 0.2, 0.3]

        # Create signal plot
        signal_plot = VGroup()
        for i, value in enumerate(signal):
            dot = Dot(radius=0.1, color=BLUE)
            dot.move_to(LEFT * i + DOWN * 2)
            signal_plot.add(dot)
            label = Tex(str(value)).next_to(dot, RIGHT)
            signal_plot.add(label)

        # Create kernel plot
        kernel_plot = VGroup()
        for i, value in enumerate(kernel):
            dot = Dot(radius=0.1, color=RED)
            dot.move_to(LEFT * i + DOWN * 3)
            kernel_plot.add(dot)
            label = Tex(str(value)).next_to(dot, RIGHT)
            kernel_plot.add(label)

        # Create convolution output plot
        output_plot = VGroup()
        for i in range(len(signal) - len(kernel) + 1):
            output_value = 0
            for j, value in enumerate(signal[i:i+len(kernel)]):
                output_value += value * kernel[j]
            dot = Dot(radius=0.1, color=YELLOW)
            dot.move_to(LEFT * i + DOWN * 4)
            output_plot.add(dot)
            label = Tex(str(output_value)).next_to(dot, RIGHT)
            output_plot.add(label)

        # Animate convolution operation
        for i in range(len(signal) - len(kernel) + 1):
            self.play(
                signal_plot.shift, LEFT,
                kernel_plot.shift, LEFT,
                output_plot.shift, LEFT,
                rate_func=linear,
                run_time=0.5
            )
            self.play(
                signal_plot.shift, RIGHT,
                kernel_plot.shift, RIGHT,
                output_plot.shift, RIGHT,
                rate_func=linear,
                run_time=0.5
            )
            self.wait()

        # Create labels
        signal_label = Tex('Signal').move_to(UP * 2 + LEFT * 3)
        kernel_label = Tex('Kernel').move_to(UP * 2 + LEFT * 3 + DOWN * 2)
        output_label = Tex('Convolution Output').move_to(UP * 2 + LEFT * 3 + DOWN * 4)

        # Add labels to scene
        self.add(signal_plot, kernel_plot, output_plot)
        self.add(signal_label, kernel_label, output_label)