from manim import *

class CentralLimitTheorem(Scene):
    def construct(self):
        # Parameters
        num_samples = 500
        num_bins = 30
        sample_size = 30
        num_iterations = 100

        # Original Distribution (Uniform)
        original_distribution = [np.random.uniform(0, 1) for _ in range(num_samples)]
        original_hist = self.create_histogram(original_distribution, num_bins, color=BLUE, label="Original Distribution")

        # Sample Means Histogram
        sample_means = []
        sample_means_hist = Histogram(
            values=[],
            edge_color=RED,
            width=0.1,
            height=1,
            label="Distribution of Sample Means"
        )

        # Animate the process of taking sample means
        for i in range(num_iterations):
            sample = np.random.choice(original_distribution, size=sample_size, replace=False)
            sample_mean = np.mean(sample)
            sample_means.append(sample_mean)

            sample_means_hist.add_data(sample_mean)
            
            if i % 10 == 0:  # Update histogram every 10 iterations for smoother animation
                self.play(
                    sample_means_hist.animate.set_data(sample_means),
                    run_time=0.05
                )

        # Overlay Normal Distribution
        mu = np.mean(sample_means)
        sigma = np.std(sample_means)
        normal_dist = Normal(mu, sigma)
        normal_curve = normal_dist.graph(x_range=[mu - 3 * sigma, mu + 3 * sigma], color=GREEN)
        normal_label = Tex("Normal Distribution", color=GREEN).next_to(normal_curve, UP)

        self.play(
            sample_means_hist.animate.set_data(sample_means),
            normal_curve.animate.shift(LEFT * 0.5 + DOWN * 0.5),
            normal_label.animate.shift(LEFT * 0.5 + DOWN * 1.2),
            run_time=1
        )

        # Text
        text = Tex("Distribution of sample means → Normal distribution").to_edge(UP)
        self.play(Write(text))

        self.wait(3)

    def create_histogram(self, data, num_bins, color, label):
        hist = Histogram(
            values=data,
            edge_color=color,
            width=0.1,
            height=1,
            label=label
        )
        return hist