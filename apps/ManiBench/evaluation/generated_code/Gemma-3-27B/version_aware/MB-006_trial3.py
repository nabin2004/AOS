from manim import *
import numpy as np

class CLTAnimation(Scene):
    def construct(self):
        # Parameters
        num_samples = 100
        num_trials = 500
        original_distribution = "uniform"  # or "bimodal"
        mean_color = BLUE
        sample_mean_color = RED

        # Original Distribution
        if original_distribution == "uniform":
            original_data = np.random.uniform(0, 1, num_samples)
        elif original_distribution == "bimodal":
            original_data = np.concatenate([np.random.normal(0.2, 0.1, num_samples // 2),
                                             np.random.normal(0.8, 0.1, num_samples // 2)])
        else:
            raise ValueError("Invalid original distribution.")

        original_histogram = self.create_histogram(original_data, x_range=(0, 1), num_bins=10, color=mean_color)
        original_histogram.generate_target()
        original_histogram.target.shift(LEFT * 3)
        self.play(Create(original_histogram))
        self.play(Transform(original_histogram, original_histogram.target))

        # Sample Means Distribution
        sample_means = []
        for _ in range(num_trials):
            sample = np.random.choice(original_data, size=num_samples)
            sample_means.append(np.mean(sample))

        sample_means_histogram = self.create_histogram(sample_means, x_range=(0, 1), num_bins=20, color=sample_mean_color)
        sample_means_histogram.generate_target()
        sample_means_histogram.target.shift(RIGHT * 3)

        self.play(Create(sample_means_histogram))

        # Morphing Animation
        normal_distribution = self.create_normal_distribution_curve(np.mean(sample_means), np.std(sample_means), x_range=(0, 1))
        self.play(Transform(sample_means_histogram, normal_distribution))

        # Overlay/Label
        normal_label = Tex("Normal distribution", color=sample_mean_color).next_to(normal_distribution, UP)
        self.play(Create(normal_label))

        # Text
        text = Tex("Distribution of sample means → Normal distribution").to_edge(DOWN)
        self.play(Write(text))

        self.wait(2)

    def create_histogram(self, data, x_range, num_bins, color):
        hist, bin_edges = np.histogram(data, bins=num_bins, range=x_range)
        bars = VGroup(*[Rectangle(width=bin_edges[i+1] - bin_edges[i], height=hist[i], fill_color=color, stroke_color=color)
                        for i in range(len(hist))])
        bars.arrange(RIGHT, aligned_edge=DOWN)
        bars.next_to(ORIGIN, UP)
        return bars

    def create_normal_distribution_curve(self, mean, std, x_range):
        axes = Axes(x_range=[x_range[0], x_range[1]], y_range=[0, 1], x_length=6, y_length=3)
        axes.add_coordinate_labels()
        curve = axes.plot(lambda x: (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std) ** 2),
                           x_range=[x_range[0], x_range[1]], color=RED)
        return VGroup(axes, curve)