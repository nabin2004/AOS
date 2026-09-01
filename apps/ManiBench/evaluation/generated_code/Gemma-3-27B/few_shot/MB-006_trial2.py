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

        original_samples = np.random.normal(loc=0, scale=1, size=n_samples)
        #original_samples = [bimodal_dist(x) for x in np.linspace(-5, 5, n_samples)]

        # Histograms
        original_hist = VGroup(*[Rectangle(width=0.2, height=count/n_samples, fill_color=BLUE, stroke_width=0)
                                 for count in np.histogram(original_samples, bins=n_bins)[0]])
        original_hist.arrange_in_grid(1, n_bins, buff=0.05)
        original_hist.to_edge(LEFT)

        sample_means = []
        sample_mean_hist = VGroup()

        # Generate sample means
        for _ in range(n_samples):
            sample = np.random.normal(loc=0, scale=1, size=sample_size)
            #sample = [bimodal_dist(x) for x in np.random.uniform(-5, 5, sample_size)]
            sample_mean = np.mean(sample)
            sample_means.append(sample_mean)

        # Create histogram of sample means
        counts, bins = np.histogram(sample_means, bins=n_bins)
        sample_mean_hist = VGroup(*[Rectangle(width=0.2, height=count/n_samples, fill_color=GREEN, stroke_width=0)
                                     for count in counts])
        sample_mean_hist.arrange_in_grid(1, n_bins, buff=0.05)
        sample_mean_hist.to_edge(RIGHT)

        # Normal distribution curve
        mu = np.mean(sample_means)
        sigma = np.std(sample_means)
        normal_curve = axes.plot(lambda x: (1/(sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma)**2),
                                  x_range=[mu - 3*sigma, mu + 3*sigma], color=YELLOW)

        axes = Axes(x_range=[min(original_samples)-1, max(original_samples)+1], y_range=[0, 1], axis_config={"include_numbers": False})
        axes.add_coordinate_labels()
        axes.to_edge(DOWN)

        # Animation
        self.play(Create(original_hist), Write(MathTex("Distribution of original data").next_to(original_hist, UP)))
        self.wait(1)

        self.play(Create(sample_mean_hist), Write(MathTex("Distribution of sample means").next_to(sample_mean_hist, UP)))
        self.wait(1)

        self.play(Transform(sample_mean_hist, normal_curve), run_time=3)
        self.play(Create(axes))
        self.play(Write(MathTex("→ Normal distribution").next_to(normal_curve, UP)))
        self.wait(2)