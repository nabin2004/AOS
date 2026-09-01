from manim import *

class ConvolutionAnimation(Scene):
    def construct(self):
        # Data
        signal = [2, 1, 3, 4, 2, 1, 3, 2]
        kernel = [1, 2, 1]
        
        # Layout parameters
        signal_y = 2.5
        output_y = -2.5
        bar_width = 0.6
        bar_spacing = 0.8
        
        # Create Signal bars (top)
        signal_bars = VGroup()
        for i, val in enumerate(signal):
            bar = Rectangle(
                width=bar_width,
                height=val * 0.5,
                fill_color=BLUE,
                fill_opacity=0.8,
                stroke_color=WHITE,
                stroke_width=2
            )
            bar.move_to([i * bar_spacing, signal_y + val * 0.25, 0])
            signal_bars.add(bar)
        
        signal_label = Text("Signal", font_size=30).next_to(signal_bars, UP, buff=0.5)
        
        # Create Output bars (bottom) - start with minimal height
        output_length = len(signal) - len(kernel) + 1
        output_values = []
        for i in range(output_length):
            val = sum(signal[i+j] * kernel[j] for j in range(len(kernel)))
            output_values.append(val)
        
        output_bars = VGroup()
        for i in range(output_length):
            bar = Rectangle(
                width=bar_width,
                height=0.1,
                fill_color=GREEN,
                fill_opacity=0.8,
                stroke_color=WHITE,
                stroke_width=2
            )
            # Position at baseline (will grow upward)
            bar.move_to([i * bar_spacing, output_y + 0.05, 0])
            output_bars.add(bar)
        
        output_label = Text("Convolution Output", font_size=30).next_to(output_bars, UP, buff=0.5)
        
        # Create Kernel sliding window
        window_width = len(kernel) * bar_spacing - (bar_spacing - bar_width)
        window = Rectangle(
            width=window_width,
            height=3.5,
            stroke_color=RED,
            stroke_width=4,
            fill_color=RED,
            fill_opacity=0.15
        )
        
        # Initial position (centered over first kernel-sized group)
        start_center_x = (signal_bars[0].get_center()[0] + signal_bars[len(kernel)-1].get_center()[0]) / 2
        window.move_to([start_center_x, signal_y + 0.5, 0])
        
        kernel_label = Text("Kernel", font_size=24, color=RED).next_to(window, UP, buff=0.2)
        
        # Initial draw
        self.play(
            Create(signal_bars),
            Write(signal_label),
            Create(output_bars),
            Write(output_label),
            Create(window),
            Write(kernel_label),
            run_time=1.5
        )
        
        # Animate convolution
        for i in range(output_length):
            # Move window to current position
            if i > 0:
                target_center_x = (signal_bars[i].get_center()[0] + signal_bars[i+len(kernel)-1].get_center()[0]) / 2
                self.play(
                    window.animate.move_to([target_center_x, signal_y + 0.5, 0]),
                    kernel_label.animate.next_to(window, UP, buff=0.2),
                    run_time=0.7
                )
            
            # Highlight affected signal bars
            affected_bars = VGroup(*[signal_bars[i+j] for j in range(len(kernel))])
            self.play(
                affected_bars.animate.set_fill(YELLOW, opacity=1),
                run_time=0.3
            )
            
            # Show element-wise multiplication
            products = VGroup()
            for j in range(len(kernel)):
                s_val = signal[i+j]
                k_val = kernel[j]
                text = MathTex(f"{s_val} \\times {k_val}", font_size=22, color=YELLOW)
                text.move_to(signal_bars[i+j].get_top() + UP * 0.5)
                products.add(text)
            
            self.play(FadeIn(products), run_time=0.3)
            
            # Show sum accumulating
            sum_val = output_values[i]
            sum_text = MathTex(f"\\Sigma = {sum_val}", font_size=28, color=GREEN)
            sum_text.move_to(window.get_center())
            
            self.play(
                FadeIn(sum_text),
                run_time=0.3
            )
            
            # Grow output bar to final height
            target_height = sum_val * 0.5
            target_y = output_y + target_height / 2
            
            self.play(
                output_bars[i].animate.stretch_to_fit_height(target_height).move_to([i * bar_spacing, target_y, 0]),
                FadeOut(sum_text),
                FadeOut(products),
                affected_bars.animate.set_fill(BLUE, opacity=0.8),
                run_time=0.6
            )
        
        # Final pause
        self.wait(2)
        
        # Fade out kernel window at end
        self.play(
            FadeOut(window),
            FadeOut(kernel_label),
            run_time=0.5
        )
        self.wait(1)