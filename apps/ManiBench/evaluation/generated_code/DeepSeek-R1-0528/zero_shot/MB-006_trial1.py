from manim import *
import numpy as np
import math

class CentralLimitTheorem(Scene):
    def construct(self):
        # Set random seed for reproducibility
        np.random.seed(42)
        
        # Parameters
        sample_size = 30
        num_samples = 500
        bin_width = 0.2
        
        # Generate sample means from bimodal distribution
        sample_means = []
        for _ in range(num_samples):
            sample = np.concatenate([
                np.random.normal(-2, 1, sample_size//2),
                np.random.normal(2, 1, sample_size//2)
            ])
            sample_means.append(np.mean(sample))
        
        # Create original distribution histogram
        original_data = np.concatenate([
            np.random.normal(-2, 1, 10000),
            np.random.normal(2, 1, 10000)
        ])
        hist_original = Histogram(
            original_data,
            bin_width=0.2,
            colors=[BLUE_D],
            fill_opacity=0.7
        ).to_edge(LEFT)
        label_original = Text("Original Distribution", font_size=24).next_to(hist_original, UP, buff=0.2)
        
        # Create sample means histogram with ValueTracker
        n_tracker = ValueTracker(0)
        hist_sample_means = always_redraw(lambda: Histogram(
            sample_means[:int(n_tracker.get_value())],
            bin_width=bin_width,
            colors=[GREEN_D],
            fill_opacity=0.7
        ).to_edge(RIGHT))
        label_sample_means = Text("Sample Means", font_size=24).next_to(hist_sample_means, UP, buff=0.2)
        
        # Title
        title = Text("Central Limit Theorem", font_size=40).to_edge(UP)
        
        # Add initial elements
        self.add(title, hist_original, label_original, label_sample_means)
        self.add(hist_sample_means)
        
        # Animate sampling process
        self.play(
            n_tracker.animate.set_value(num_samples),
            run_time=10,
            rate_func=linear
        )
        
        # Replace with static histogram
        self.remove(hist_sample_means)
        hist_static = Histogram(
            sample_means,
            bin_width=bin_width,
            colors=[GREEN_D],
            fill_opacity=0.7
        ).to_edge(RIGHT)
        self.add(hist_static)
        
        # Add normal distribution curve
        axes = hist_static.axes
        mean_val = np.mean(sample_means)
        std_val = np.std(sample_means)
        curve = axes.plot(
            lambda x: (num_samples * bin_width) * (1/(std_val*math.sqrt(2*math.pi))) * math.exp(-0.5*((x-mean_val)/std_val)**2),
            color=YELLOW,
            stroke_width=3
        )
        curve_label = Text("Normal Distribution", font_size=24, color=YELLOW).next_to(curve, UP, buff=0.1)
        
        # Add final text
        central_text = Text("Distribution of sample means → Normal distribution", font_size=30).to_edge(DOWN)
        
        # Animate final elements
        self.play(Create(curve), FadeIn(curve_label), FadeIn(central_text))
        self.wait(3)