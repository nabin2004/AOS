from manim import *
import numpy as np

class ConvolutionAnimation(Scene):
    def construct(self):
        # Define signal and kernel
        signal = np.array([1, 2, 3, 4, 3, 2, 1, 0, 0, 0])
        kernel = np.array([0.5, 1, 0.5])
        
        # Calculate convolution output
        output = np.convolve(signal, kernel, mode='valid')
        
        # Create axes
        signal_axes = Axes(
            x_range=[0, len(signal), 1],
            y_range=[0, 5, 1],
            x_length=8,
            y_length=2,
            axis_config={"color": BLUE}
        ).shift(UP * 2)
        
        kernel_axes = Axes(
            x_range=[0, len(kernel), 1],
            y_range=[0, 1.5, 0.5],
            x_length=2,
            y_length=1,
            axis_config={"color": GREEN}
        ).shift(LEFT * 4)
        
        output_axes = Axes(
            x_range=[0, len(output), 1],
            y_range=[0, 8, 2],
            x_length=6,
            y_length=2,
            axis_config={"color": RED}
        ).shift(DOWN * 2)
        
        # Labels
        signal_label = Text("Signal", font_size=24).next_to(signal_axes, UP)
        kernel_label = Text("Kernel", font_size=24).next_to(kernel_axes, UP)
        output_label = Text("Convolution Output", font_size=24).next_to(output_axes, UP)
        
        # Create signal bars
        signal_bars = VGroup()
        for i, val in enumerate(signal):
            bar = Rectangle(
                width=0.8,
                height=val * 0.4,
                fill_color=BLUE,
                fill_opacity=0.7,
                stroke_color=BLUE
            ).move_to(signal_axes.c2p(i + 0.5, val/2))
            signal_bars.add(bar)
        
        # Create kernel bars
        kernel_bars = VGroup()
        for i, val in enumerate(kernel):
            bar = Rectangle(
                width=0.8,
                height=val * 0.6,
                fill_color=GREEN,
                fill_opacity=0.7,
                stroke_color=GREEN
            ).move_to(kernel_axes.c2p(i + 0.5, val/2))
            kernel_bars.add(bar)
        
        # Create sliding kernel window
        sliding_kernel = kernel_bars.copy()
        sliding_kernel.move_to(signal_axes.c2p(1.5, 0))
        
        # Create output bars (initially empty)
        output_bars = VGroup()
        
        # Show initial setup
        self.play(
            Create(signal_axes),
            Create(kernel_axes),
            Create(output_axes),
            Write(signal_label),
            Write(kernel_label),
            Write(output_label)
        )
        
        self.play(
            Create(signal_bars),
            Create(kernel_bars)
        )
        
        self.play(Create(sliding_kernel))
        
        # Animate convolution
        for i in range(len(output)):
            # Move sliding kernel to position
            target_x = signal_axes.c2p(i + 1.5, 0)[0]
            self.play(
                sliding_kernel.animate.move_to([target_x, sliding_kernel.get_center()[1], 0]),
                run_time=0.5
            )
            
            # Highlight overlapping signal elements
            highlight_bars = VGroup()
            products = []
            
            for j in range(len(kernel)):
                if i + j < len(signal):
                    # Create highlight for signal element
                    highlight = signal_bars[i + j].copy()
                    highlight.set_fill(YELLOW, opacity=0.8)
                    highlight_bars.add(highlight)
                    
                    # Calculate product
                    product = signal[i + j] * kernel[j]
                    products.append(product)
            
            # Show highlighting
            self.play(Create(highlight_bars), run_time=0.3)
            
            # Show product calculation (text)
            product_text = Text(
                f"Sum: {sum(products):.1f}",
                font_size=20
            ).next_to(sliding_kernel, DOWN)
            
            self.play(Write(product_text), run_time=0.3)
            
            # Add output bar
            output_val = output[i]
            output_bar = Rectangle(
                width=0.8,
                height=output_val * 0.25,
                fill_color=RED,
                fill_opacity=0.7,
                stroke_color=RED
            ).move_to(output_axes.c2p(i + 0.5, output_val/2))
            
            output_bars.add(output_bar)
            
            self.play(
                Create(output_bar),
                run_time=0.3
            )
            
            # Clean up highlights and text
            self.play(
                FadeOut(highlight_bars),
                FadeOut(product_text),
                run_time=0.2
            )
        
        # Final pause
        self.wait(2)
        
        # Show formula
        formula = MathTex(
            r"(f * g)[n] = \sum_{m} f[m] \cdot g[n-m]",
            font_size=36
        ).to_edge(DOWN)
        
        self.play(Write(formula))
        self.wait(3)