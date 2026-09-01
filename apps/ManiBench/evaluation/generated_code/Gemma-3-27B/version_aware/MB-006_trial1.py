from manim import *
import numpy as np

class CLT(Scene):
    def construct(self):
        # Parameters
        num_samples = 100
        num_means = 500
        original_distribution = "uniform"  # or "bimodal"
        
        # Original Distribution
        if original_distribution == "uniform":
            original_data = np.random.uniform(0, 1, num_samples)
        elif original_distribution == "bimodal":
            original_data = np.concatenate([np.random.normal(0.2, 0.1, num_samples // 2),
                                             np.random.normal(0.8, 0.1, num_samples // 2)])
        
        # Create histograms
        hist_original, axes_original = self.create_histogram(original_data, x_range=(0, 1), num_bars=20, label="Original Distribution")
        hist_means, axes_means = self.create_histogram(np.zeros(1), x_range=(0, 1), num_bars=20, label="Distribution of Sample Means")
        
        # Animate original distribution
        self.play(Create(hist_original), run_time=2)
        self.play(Write(axes_original.get_axis_labels(x_label="Value")))
        
        # Calculate and plot sample means
        sample_means = []
        for _ in range(num_means):
            sample = np.random.choice(original_data, size=num_samples)
            sample_means.append(np.mean(sample))
        
        # Update histogram with sample means
        hist_means.set_data(sample_means)
        
        # Animate the morphing of the histogram
        self.play(Create(hist_means), run_time=5)
        self.play(Write(axes_means.get_axis_labels(x_label="Sample Mean")))
        
        # Overlay normal distribution
        mu = np.mean(sample_means)
        sigma = np.std(sample_means)
        
        normal_curve = self.create_normal_curve(mu, sigma, x_range=(0, 1), color=YELLOW)
        
        self.play(Create(normal_curve))
        
        # Add text
        text = Text("Distribution of sample means → Normal distribution")
        self.play(Write(text))
        
        self.wait(3)

    def create_histogram(self, data, x_range, num_bars, label):
        axes = Axes(x_range=x_range, y_range=[0, max(1, np.max(data))], x_length=6, y_length=3)
        axes.add_coordinate_labels()
        hist = axes.hist(data, num_bars=num_bars, color=BLUE, label=label)
        return hist, axes

    def create_normal_curve(self, mu, sigma, x_range, color):
        x = np.linspace(x_range[0], x_range[1], 100)
        y = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
        
        curve = ParametricFunction(lambda t: [t, (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((t - mu) / sigma) ** 2)], t_range=[x_range[0], x_range[1]], color=color)
        return curve