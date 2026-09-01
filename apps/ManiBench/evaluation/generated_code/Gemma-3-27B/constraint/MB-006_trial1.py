from manim import *

class CentralLimitTheorem(Scene):
    def construct(self):
        # Parameters
        n_samples = 100
        n_bins = 20
        sample_size = 30
        num_means = 100

        # Original Distribution (Uniform)
        original_distribution = [np.random.uniform(0, 1) for _ in range(n_samples)]
        original_histogram = self.create_histogram(original_distribution, n_bins, color=BLUE, label="Uniform Distribution")
        self.play(Create(original_histogram))
        self.wait(1)

        # Sampling Process Visualization
        dots = [Dot(original_histogram.get_bin_center(i) + DOWN * 0.5, color=YELLOW) for i in range(n_bins)]
        for dot in dots:
            self.play(Create(dot))
        self.wait(0.5)

        arrows = []
        for _ in range(sample_size):
            sample = [original_distribution[np.random.randint(0, n_samples)] for _ in range(sample_size)]
            mean = np.mean(sample)
            arrow = Arrow(original_histogram.get_bin_center(np.random.randint(0, n_bins)) + DOWN * 0.5, mean + RIGHT * 2, buff=0.1, color=GREEN)
            arrows.append(arrow)
            self.play(Create(arrow))
            self.wait(0.05)
            for a in arrows:
                a.generate_target()
                a.target.become(FadeOut(a))
            self.play(MoveToTarget(arrows))
            self.remove(*arrows)
            arrows = []

        self.wait(1)
        self.play(FadeOut(*dots))

        # Histogram of Sample Means
        means_histogram = self.create_histogram([], n_bins, color=RED, label="Sample Means")
        self.play(Create(means_histogram))
        self.wait(1)

        # Build Histogram of Sample Means
        for _ in range(num_means):
            sample = [original_distribution[np.random.randint(0, n_samples)] for _ in range(sample_size)]
            mean = np.mean(sample)
            means_histogram.add_data(mean)
            self.play(UpdateBars(means_histogram))
            self.wait(0.02)

        self.wait(2)

        # Overlay Normal Distribution
        x_range = np.linspace(0, 1, 100)
        normal_distribution = normal_pdf(x_range, np.mean(original_distribution), np.std(original_distribution))
        normal_curve = self.create_normal_curve(x_range, normal_distribution, color=GREEN)
        self.play(Create(normal_curve))

        # Text Explanation
        text = Tex("Distribution of sample means → Normal distribution")
        text.move_to(UP * 2)
        self.play(Write(text))

        self.wait(3)

    def create_histogram(self, data, n_bins, color, label):
        histogram = VGroup()
        if data:
            hist, bin_edges = np.histogram(data, bins=n_bins)
            for i in range(n_bins):
                rect = Rectangle(width=bin_edges[i+1] - bin_edges[i], height=hist[i], color=color)
                rect.move_to(bin_edges[i], 0, 0)
                histogram.add(rect)

        label_text = Text(label)
        label_text.next_to(histogram, UP)
        histogram.add(label_text)
        return histogram

    def create_normal_curve(self, x_values, y_values, color):
        curve = VMobject()
        curve.set_points_as_corners([Point(x, y) for x, y in zip(x_values, y_values)])
        curve.set_color(color)
        return curve

def normal_pdf(x, mu, sigma):
    return (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

def UpdateBars(histogram):
    return UpdateFromFunc(lambda m: m.generate_target(), histogram)