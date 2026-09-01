from manim import *
import numpy as np

class ConvolutionAnimation(Scene):
    def construct(self):
        # Define signal and kernel
        signal_data = [0, 1, 3, 2, 5, 4, 3, 1, 2, 0]
        kernel_data = [1, 2, 1]  # Simple smoothing kernel (unnormalized)
        kernel_sum = sum(kernel_data)
        
        n_signal = len(signal_data)
        n_kernel = len(kernel_data)
        n_output = n_signal - n_kernel + 1  # Valid convolution
        
        # Compute convolution output
        conv_output = []
        for i in range(n_output):
            val = sum(signal_data[i + j] * kernel_data[j] for j in range(n_kernel))
            conv_output.append(val)
        
        max_signal = max(signal_data)
        max_output = max(conv_output)
        
        # Layout parameters
        bar_width = 0.45
        signal_x_start = -5.0
        signal_y_base = 1.0
        signal_y_scale = 0.5
        
        output_x_start = -5.0
        output_y_base = -2.5
        output_y_scale = 0.3
        
        # --- Title ---
        title = Text("1D Convolution", font_size=36, weight=BOLD).to_edge(UP, buff=0.3)
        self.play(Write(title))
        
        # --- Draw Signal bars ---
        signal_bars = VGroup()
        signal_labels_vals = VGroup()
        for i, val in enumerate(signal_data):
            x = signal_x_start + i * (bar_width + 0.15)
            bar = Rectangle(
                width=bar_width,
                height=val * signal_y_scale,
                fill_color=BLUE,
                fill_opacity=0.7,
                stroke_color=BLUE_E,
                stroke_width=2,
            )
            bar.move_to(
                np.array([x, signal_y_base + val * signal_y_scale / 2, 0])
            )
            signal_bars.add(bar)
            
            lbl = Text(str(val), font_size=18).next_to(bar, UP, buff=0.05)
            signal_labels_vals.add(lbl)
        
        signal_label = Text("Signal", font_size=28, color=BLUE).next_to(
            signal_bars, LEFT, buff=0.4
        )
        
        # Signal axis line
        axis_left = signal_x_start - bar_width / 2 - 0.1
        axis_right = signal_x_start + (n_signal - 1) * (bar_width + 0.15) + bar_width / 2 + 0.1
        signal_axis = Line(
            np.array([axis_left, signal_y_base, 0]),
            np.array([axis_right, signal_y_base, 0]),
            color=WHITE,
            stroke_width=2,
        )
        
        self.play(
            Create(signal_axis),
            LaggedStart(*[GrowFromEdge(b, DOWN) for b in signal_bars], lag_ratio=0.1),
            run_time=1.5,
        )
        self.play(
            FadeIn(signal_labels_vals),
            Write(signal_label),
        )
        
        # --- Kernel display ---
        kernel_display_group = VGroup()
        kernel_text = Text("Kernel: [1, 2, 1]", font_size=24, color=GREEN)
        kernel_text.move_to(np.array([4.5, 2.5, 0]))
        kernel_label = Text("Kernel", font_size=28, color=GREEN).next_to(
            kernel_text, UP, buff=0.2
        )
        kernel_display_group.add(kernel_label, kernel_text)
        
        self.play(Write(kernel_display_group))
        
        # --- Output axis ---
        output_axis_left = output_x_start - bar_width / 2 - 0.1
        output_axis_right = output_x_start + (n_output - 1) * (bar_width + 0.15) + bar_width / 2 + 0.1
        output_axis = Line(
            np.array([output_axis_left, output_y_base, 0]),
            np.array([output_axis_right, output_y_base, 0]),
            color=WHITE,
            stroke_width=2,
        )
        output_label = Text("Convolution Output", font_size=28, color=YELLOW).next_to(
            output_axis, LEFT, buff=0.3
        )
        
        self.play(Create(output_axis), Write(output_label))
        
        # --- Sliding window rectangle ---
        def get_window_rect(pos_index):
            x_left = signal_x_start + pos_index * (bar_width + 0.15) - bar_width / 2 - 0.05
            x_right = signal_x_start + (pos_index + n_kernel - 1) * (bar_width + 0.15) + bar_width / 2 + 0.05
            rect = Rectangle(
                width=x_right - x_left,
                height=max_signal * signal_y_scale + 0.6,
                stroke_color=GREEN,
                stroke_width=3,
                fill_color=GREEN,
                fill_opacity=0.1,
            )
            rect.move_to(
                np.array([(x_left + x_right) / 2, signal_y_base + (max_signal * signal_y_scale) / 2, 0])
            )
            return rect
        
        window_rect = get_window_rect(0)
        self.play(Create(window_rect))
        
        # --- Animate convolution step by step ---
        output_bars = VGroup()
        output_val_labels = VGroup()
        
        for i in range(n_output):
            # Move window
            new_rect = get_window_rect(i)
            if i > 0:
                self.play(Transform(window_rect, new_rect), run_time=0.5)
            
            # Highlight element-wise products
            product_labels = VGroup()
            product_sum = 0
            highlighted_bars = []
            
            for j in range(n_kernel):
                idx = i + j
                bar = signal_bars[idx]
                
                # Highlight bar
                highlighted_bars.append(bar)
                
                # Product label
                prod_val = signal_data[idx] * kernel_data[j]
                product_sum += prod_val
                prod_text = Text(
                    f"{signal_data[idx]}×{kernel_data[j]}={prod_val}",
                    font_size=16,
                    color=YELLOW,
                )
                x_pos = signal_x_start + idx * (bar_width + 0.15)
                prod_text.move_to(np.array([x_pos, signal_y_base - 0.35, 0]))
                product_labels.add(prod_text)
            
            # Animate highlights
            highlight_anims = [
                bar.animate.set_fill(YELLOW, opacity=0.9) for bar in highlighted_bars
            ]
            self.play(*highlight_anims, FadeIn(product_labels), run_time=0.5)
            
            # Show sum computation
            sum_text = Text(
                f"Sum = {conv_output[i]}",
                font_size=22,
                color=YELLOW,
                weight=BOLD,
            )
            sum_text.move_to(np.array([4.5, 1.2, 0]))
            self.play(FadeIn(sum_text), run_time=0.3)
            
            # Add output bar
            out_x = output_x_start + i * (bar_width + 0.15)
            out_bar = Rectangle(
                width=bar_width,
                height=conv_output[i] * output_y_scale,
                fill_color=YELLOW,
                fill_opacity=0.7,
                stroke_color=YELLOW_E,
                stroke_width=2,
            )
            out_bar.move_to(
                np.array([out_x, output_y_base + conv_output[i] * output_y_scale / 2, 0])
            )
            
            out_val_lbl = Text(str(conv_output[i]), font_size=18, color=YELLOW).next_to(
                out_bar, UP, buff=0.05
            )
            
            output_bars.add(out_bar)
            output_val_labels.add(out_val_lbl)
            
            self.play(
                GrowFromEdge(out_bar, DOWN),
                FadeIn(out_val_lbl),
                run_time=0.5,
            )
            
            # Reset highlights
            reset_anims = [
                bar.animate.set_fill(BLUE, opacity=0.7) for bar in highlighted_bars
            ]
            self.play(
                *reset_anims,
                FadeOut(product_labels),
                FadeOut(sum_text),
                run_time=0.3,
            )
        
        # Fade out window
        self.play(FadeOut(window_rect))
        
        # Final highlight of output
        self.play(
            output_bars.animate.set_fill(ORANGE, opacity=0.9),
            run_time=0.5,
        )
        self.play(
            output_bars.animate.set_fill(YELLOW, opacity=0.7),
            run_time=0.5,
        )
        
        self.wait(2)