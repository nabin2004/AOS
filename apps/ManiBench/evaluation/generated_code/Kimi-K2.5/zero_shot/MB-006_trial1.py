from manim import *
import numpy as np

class CentralLimitTheorem(Scene):
    def construct(self):
        # Parameters
        n_samples = 150
        sample_size = 30
        n_bins = 15
        
        # Setup random seed for reproducibility
        np.random.seed(42)
        
        # Create bimodal parent distribution (mixture of two normals)
        parent_data = np.concatenate([
            np.random.normal(3, 0.6, 5000),
            np.random.normal(7, 0.6, 5000)
        ])
        parent_data = np.clip(parent_data, 0, 10)
        
        # Create axes for parent distribution (left)
        parent_axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 0.4, 0.1],
            x_length=5,
            y_length=3,
            axis_config={"include_numbers": True, "font_size": 20},
        ).shift(LEFT * 3.5)
        
        parent_title = Text("Parent Distribution\n(Bimodal)", font_size=24).next_to(parent_axes, UP)
        
        # Create axes for sample means (right)
        sample_axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 0.8, 0.2],
            x_length=5,
            y_length=3,
            axis_config={"include_numbers": True, "font_size": 20},
        ).shift(RIGHT * 3.5)
        
        sample_title = Text("Sample Means", font_size=24).next_to(sample_axes, UP)
        
        # Create parent histogram
        parent_hist = self.get_histogram_bars(parent_axes, parent_data, n_bins, BLUE)
        
        # Animation start
        self.play(
            Create(parent_axes),
            Write(parent_title),
            Create(parent_hist),
            run_time=2
        )
        self.wait(0.5)
        
        # Initialize empty sample means list and histogram
        sample_means = []
        sample_hist = self.get_empty_histogram(sample_axes, n_bins, YELLOW)
        
        self.play(
            Create(sample_axes),
            Write(sample_title),
            Create(sample_hist),
            run_time=1
        )
        
        # Text for sampling process
        sampling_text = Text("Drawing samples...", font_size=20).next_to(sample_axes, DOWN)
        sample_counter = Text("n = 0", font_size=20).next_to(sampling_text, DOWN)
        self.play(Write(sampling_text), Write(sample_counter))
        
        # Animate the sampling process
        for i in range(n_samples):
            # Draw random sample and compute mean
            sample = np.random.choice(parent_data, size=sample_size)
            mean = np.mean(sample)
            sample_means.append(mean)
            
            # Update counter
            if i % 5 == 0 or i == n_samples - 1:
                new_counter = Text(f"n = {i+1}", font_size=20).next_to(sampling_text, DOWN)
                new_counter.align_to(sample_counter, LEFT)
                
                # Update histogram every few iterations
                new_hist = self.get_histogram_bars(sample_axes, sample_means, n_bins, YELLOW)
                
                self.play(
                    Transform(sample_hist, new_hist),
                    Transform(sample_counter, new_counter),
                    run_time=0.1
                )
        
        self.play(FadeOut(sampling_text), FadeOut(sample_counter))
        
        # Calculate theoretical parameters
        pop_mean = np.mean(parent_data)
        pop_std = np.std(parent_data)
        se = pop_std / np.sqrt(sample_size)
        
        # Create theoretical normal curve overlay
        theoretical_curve = sample_axes.plot(
            lambda x: self.scaled_normal(x, pop_mean, se, len(sample_means), n_bins, sample_axes),
            x_range=[max(0, pop_mean - 4*se), min(10, pop_mean + 4*se)],
            color=RED,
            stroke_width=3
        )
        
        curve_label = MathTex(r"\mathcal{N}(\mu, \frac{\sigma}{\sqrt{n}})", color=RED, font_size=28)
        curve_label.next_to(theoretical_curve, UP, buff=0.3)
        
        # Show final text
        final_text = Text(
            "Distribution of sample means → Normal distribution",
            font_size=30,
            color=WHITE
        ).to_edge(DOWN, buff=0.3)
        
        # Final animations
        self.play(
            Create(theoretical_curve),
            Write(curve_label),
            run_time=2
        )
        
        self.play(
            Write(final_text),
            run_time=2
        )
        
        self.wait(3)
    
    def get_histogram_bars(self, axes, data, n_bins, color):
        """Create histogram bars from data"""
        if len(data) == 0:
            return self.get_empty_histogram(axes, n_bins, color)
        
        counts, bin_edges = np.histogram(data, bins=n_bins, range=(0, 10))
        max_count = max(counts) if max(counts) > 0 else 1
        y_max = axes.y_range[1]
        
        bars = VGroup()
        bin_width = 10 / n_bins
        
        for i, count in enumerate(counts):
            height = (count / max_count) * y_max * 0.9 if max_count > 0 else 0
            
            bar = Rectangle(
                width=axes.x_length / n_bins * 0.8,
                height=height * axes.y_length / y_max,
                fill_color=color,
                fill_opacity=0.6,
                stroke_color=color,
                stroke_width=1
            )
            
            x_center = bin_edges[i] + bin_width / 2
            x_pos = axes.c2p(x_center, 0)[0]
            bottom_y = axes.c2p(0, 0)[1]
            actual_height = height * axes.y_length / y_max
            
            bar.move_to([x_pos, bottom_y + actual_height/2, 0])
            
            bars.add(bar)
        
        return bars
    
    def get_empty_histogram(self, axes, n_bins, color):
        """Create empty histogram placeholder"""
        bars = VGroup()
        bin_width = 10 / n_bins
        
        for i in range(n_bins):
            bar = Rectangle(
                width=axes.x_length / n_bins * 0.8,
                height=0.01,
                fill_color=color,
                fill_opacity=0.6,
                stroke_color=color,
                stroke_width=1
            )
            
            x_center = (i + 0.5) * bin_width
            x_pos = axes.c2p(x_center, 0)[0]
            bottom_y = axes.c2p(0, 0)[1]
            
            bar.move_to([x_pos, bottom_y + 0.005, 0], aligned_edge=DOWN)
            bars.add(bar)
        
        return bars
    
    def scaled_normal(self, x, mu, sigma, n_samples, n_bins, axes):
        """Return scaled normal PDF to match histogram"""
        pdf = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
        bin_width = 10 / n_bins
        
        # Expected count in bin = n_samples * P(X in bin) ≈ n_samples * pdf * bin_width
        expected_count = n_samples * pdf * bin_width
        
        # Scale to fit in axes (normalize to max expected count at peak)
        max_pdf = 1 / (sigma * np.sqrt(2 * np.pi))
        max_count = n_samples * bin_width * max_pdf
        y_max = axes.y_range[1]
        
        return (expected_count / max_count) * y_max * 0.9