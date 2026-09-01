from manim import *

class CLTAnimation(Scene):
    def construct(self):
        # Analysis:
        # 1. Mobjects: Original histogram, sample dots, sample mean dots, mean histogram, normal distribution curve, text.
        # 2. Order: Original histogram -> Sample drawing -> Mean calculation & histogram building -> Normal curve overlay -> Text.
        # 3. Transformations: FadeIn, Create, Add, Transform, UpdateFrom.
        # 4. Timing: Synchronize sample drawing and mean calculation.
        # 5. Labels: "Distribution of sample means → Normal distribution".

        # Parameters
        n_samples = 500
        n_means = 100
        sample_size = 30
        original_distribution = "uniform"  # or "bimodal"

        # Original Distribution Histogram
        if original_distribution == "uniform":
            original_data = np.random.uniform(0, 1, n_samples)
        else:  # bimodal
            original_data = np.concatenate([np.random.normal(0.2, 0.1, n_samples // 2),
                                             np.random.normal(0.8, 0.1, n_samples // 2)])

        original_hist, original_bins = np.histogram(original_data, bins=20)
        original_histogram = VGroup(*[Rectangle(width=original_bins[i+1]-original_bins[i], height=original_hist[i], fill_opacity=0.7)
                                      for i in range(len(original_hist))])
        original_histogram.arrange(buff=0.1, aligned_edge=DOWN)
        original_histogram.shift(LEFT * 3)

        self.play(FadeIn(original_histogram))

        # Sample Drawing
        sample_dots = VGroup()
        for _ in range(5):
            sample = np.random.choice(original_data, size=sample_size, replace=False)
            dots = VGroup(*[Dot(original_histogram.get_center() + DOWN * original_hist[i] + RIGHT * (original_bins[i+1]-original_bins[i])/2) for i in range(len(original_hist)) if original_bins[i] <= sample[0] <= original_bins[i+1]])
            sample_dots.add(dots)
            self.play(Create(dots))
            self.wait(0.2)
            sample_dots.remove(dots)

        # Mean Histogram
        mean_histogram = VGroup()
        mean_data = []
        for _ in range(n_means):
            sample = np.random.choice(original_data, size=sample_size, replace=False)
            mean = np.mean(sample)
            mean_data.append(mean)

        mean_hist, mean_bins = np.histogram(mean_data, bins=20)
        mean_bars = VGroup(*[Rectangle(width=mean_bins[i+1]-mean_bins[i], height=mean_hist[i], fill_opacity=0.9)
                             for i in range(len(mean_hist))])
        mean_bars.arrange(buff=0.1, aligned_edge=DOWN)
        mean_bars.shift(RIGHT * 3)

        self.play(FadeIn(mean_bars))

        # Build Mean Histogram
        for i in range(len(mean_bars)):
            self.play(GrowFromCenter(mean_bars[i]))
            self.wait(0.01)

        # Normal Distribution Curve
        mu = np.mean(mean_data)
        sigma = np.std(mean_data)
        x = np.linspace(min(mean_data), max(mean_data), 100)
        normal_curve = Tex(r"N(\mu=" + str(round(mu, 2)) + r", \sigma^2=" + str(round(sigma**2, 2)) + r")")
        normal_curve.scale(0.7)
        normal_curve.next_to(mean_bars, UP)

        self.play(Create(normal_curve))

        # Text
        text = Text("Distribution of sample means → Normal distribution")
        text.to_edge(DOWN)
        self.play(Write(text))

        self.wait(2)