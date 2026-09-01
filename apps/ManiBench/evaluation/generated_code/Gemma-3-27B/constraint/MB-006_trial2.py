from manim import *

class CentralLimitTheorem(Scene):
    def construct(self):
        # Parameters
        n_samples = 1000
        n_bins = 30
        sample_size = 30
        num_means = 100

        # Original Distribution (Uniform)
        original_distribution = [np.random.uniform(0, 1) for _ in range(n_samples)]
        original_hist, _ = np.histogram(original_distribution, bins=n_bins)
        original_bars = VGroup(*[Rectangle(width=1/n_bins, height=h, fill_color=BLUE, stroke_color=BLACK) for h in original_hist])
        original_bars.arrange(RIGHT, aligned_edge=DOWN)
        original_bars.scale(0.5)
        original_label = Tex("Uniform Distribution").next_to(original_bars, UP)

        self.play(Create(original_bars), Write(original_label))
        self.wait(1)

        # Sampling Process Visualization
        dots = VGroup(*[Dot(color=YELLOW) for _ in range(sample_size)])
        dots.arrange(RIGHT, buff=0.1)
        dots.move_to(UP * 2)

        arrows = VGroup(*[Arrow(start=d.get_center(), end=original_bars.get_center() + (i/n_bins, 0), color=YELLOW) for i, d in enumerate(dots)])

        self.play(Create(dots))
        self.play(*[Create(arrow) for arrow in arrows])
        self.wait(0.5)

        # Sample Means Histogram
        means_hist = []
        mean_bars = VGroup()

        for _ in range(num_means):
            sample = [np.random.uniform(0, 1) for _ in range(sample_size)]
            mean = np.mean(sample)
            means_hist.append(mean)

            hist, _ = np.histogram(means_hist, bins=n_bins)
            new_bars = VGroup(*[Rectangle(width=1/n_bins, height=h, fill_color=GREEN, stroke_color=BLACK) for h in hist])
            new_bars.arrange(RIGHT, aligned_edge=DOWN)
            new_bars.scale(0.5)
            new_bars.move_to(DOWN)

            if mean_bars:
                self.play(Transform(mean_bars, new_bars))
            else:
                self.play(Create(mean_bars))
            self.wait(0.02)

        self.wait(1)

        # Normal Distribution Overlay
        mu = 0.5
        sigma = sample_size**-0.5
        x = np.linspace(0, 1, 200)
        normal_curve = ParametricFunction(lambda t: [t, (1/(sigma * np.sqrt(2*np.pi))) * np.exp(-0.5 * ((t - mu)/sigma)**2)], t_range=[0, 1], color=RED)
        normal_curve.scale(0.5)
        normal_curve.move_to(DOWN)

        self.play(Create(normal_curve))

        # Text Explanation
        text = Tex("Distribution of sample means → Normal distribution").to_edge(UP)
        sample_size_text = Tex(f"Sample size (n) = {sample_size}").next_to(text, DOWN)

        self.play(Write(text), Write(sample_size_text))
        self.wait(2)