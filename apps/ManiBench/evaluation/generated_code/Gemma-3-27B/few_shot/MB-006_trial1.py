from manim import *
import numpy as np

class CentralLimitTheorem(Scene):
    def construct(self):
        # Parameters
        n_samples = 1000
        sample_size = 30
        n_bins = 30

        # Original distribution (bimodal)
        def bimodal_dist(x):
            return 0.5 * np.exp(- (x + 2)**2 / 2) + 0.5 * np.exp(- (x - 2)**2 / 2)

        original_samples = [bimodal_dist(np.random.uniform(-5, 5)) for _ in range(n_samples)]
        original_hist = self.create_histogram(original_samples, n_bins, color=BLUE, label="Original Distribution")

        # Histogram of sample means
        sample_means = []
        sample_mean_hist = VGroup()

        # Animation
        self.play(Create(original_hist))
        self.wait(1)

        for _ in range(50):
            samples = np.random.choice(original_samples, size=sample_size, replace=False)
            mean = np.mean(samples)
            sample_means.append(mean)

            # Create a new histogram for each step
            new_hist = self.create_histogram(sample_means, n_bins, color=RED, opacity=0.5)
            sample_mean_hist.add(new_hist)

            self.play(Transform(sample_mean_hist, new_hist), run_time=0.05)

        # Morph to normal distribution
        normal_dist = self.create_normal_distribution_histogram(sample_means, n_bins, color=GREEN)
        self.play(Transform(sample_mean_hist, normal_dist), run_time=1)

        # Label the normal distribution
        normal_label = MathTex("N(\\mu, \\sigma^2)").next_to(sample_mean_hist, UP)
        self.play(Write(normal_label))

        # Text
        text = Text("Distribution of sample means → Normal distribution", font_size=24).to_edge(DOWN)
        self.play(Write(text))

        self.wait(2)

    def create_histogram(self, data, n_bins, color, label=None, opacity=1):
        hist, edges = np.histogram(data, bins=n_bins)
        bars = VGroup(*[Rectangle(width=edges[i+1]-edges[i], height=hist[i], fill_color=color, fill_opacity=opacity)
                        for i in range(len(hist))])
        bars.arrange(aligned_edge=DOWN, buff=0.05)
        bars.move_to(ORIGIN)
        if label:
            label_text = Text(label, font_size=16).next_to(bars, UP)
            return VGroup(bars, label_text)
        return bars

    def create_normal_distribution_histogram(self, data, n_bins, color):
        mu = np.mean(data)
        sigma = np.std(data)
        x = np.linspace(min(data), max(data), 100)
        y = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma)**2)
        
        hist, edges = np.histogram(data, bins=n_bins)
        bars = VGroup(*[Rectangle(width=edges[i+1]-edges[i], height=hist[i], fill_color=color, fill_opacity=0.7)
                        for i in range(len(hist))])
        bars.arrange(aligned_edge=DOWN, buff=0.05)
        bars.move_to(ORIGIN)
        return bars