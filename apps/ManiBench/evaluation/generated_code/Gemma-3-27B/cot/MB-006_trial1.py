from manim import *

class CLTAnimation(Scene):
    def construct(self):
        # Analysis:
        # 1. Mobjects: Original histogram, sample dots, sample mean dots, mean histogram, normal distribution curve, text.
        # 2. Order: Original histogram -> Sample drawing -> Mean calculation & histogram building -> Normal curve overlay -> Text.
        # 3. Transformations: FadeIn, Create, AddUpdate, Transform, etc.
        # 4. Timing: Synchronize sample drawing and mean calculation.
        # 5. Labels: "Distribution of sample means → Normal distribution".

        # Parameters
        n_samples = 500
        n_means = 100
        sample_size = 30
        original_distribution = "uniform"  # or "bimodal"

        # Original Distribution Histogram
        if original_distribution == "uniform":
            original_data = [np.random.uniform(0, 1) for _ in range(n_samples)]
        else:  # bimodal
            original_data = np.concatenate([np.random.normal(0.2, 0.1, n_samples // 2),
                                             np.random.normal(0.8, 0.1, n_samples // 2)])

        original_hist = self.create_histogram(original_data, x_range=(0, 1), color=BLUE, opacity=0.7)
        self.play(FadeIn(original_hist))

        # Sample Drawing and Mean Calculation
        sample_dots = VGroup()
        mean_dots = VGroup()
        mean_values = []

        for _ in range(n_means):
            sample = np.random.choice(original_data, size=sample_size, replace=False)
            sample_dots.add(VGroup(*[Dot(x, y, color=YELLOW) for x, y in zip(sample, [0] * len(sample))]))
            mean_value = np.mean(sample)
            mean_values.append(mean_value)
            mean_dots.add(Dot(mean_value, 1, color=RED))

            self.play(
                Create(sample_dots[-1]),
                FadeOut(sample_dots[-1], shift=DOWN),
                Create(mean_dots[-1]),
                FadeOut(mean_dots[-1], shift=DOWN)
            )

        # Mean Histogram
        mean_hist = self.create_histogram(mean_values, x_range=(0, 1), color=GREEN, opacity=0.9)
        self.play(FadeIn(mean_hist))

        # Normal Distribution Curve
        mu = np.mean(mean_values)
        sigma = np.std(mean_values)
        normal_curve = self.create_normal_curve(mu, sigma, x_range=(0, 1), color=ORANGE, opacity=0.7)
        self.play(FadeIn(normal_curve))

        # Text
        text = Tex("Distribution of sample means → Normal distribution")
        self.play(Write(text))

        self.wait(2)

    def create_histogram(self, data, x_range, color, opacity):
        hist, edges = np.histogram(data, bins=20, range=x_range)
        bars = VGroup()
        for i in range(len(hist)):
            bar = Rectangle(width=edges[i+1] - edges[i], height=hist[i], fill_color=color, fill_opacity=opacity)
            bar.move(x=edges[i], y=0)
            bars.add(bar)
        return bars

    def create_normal_curve(self, mu, sigma, x_range, color, opacity):
        x = np.linspace(x_range[0], x_range[1], 200)
        y = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
        curve = ParametricFunction(lambda t: [t, (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((t - mu) / sigma) ** 2)], t_range=[x_range[0], x_range[1]], color=color, opacity=opacity)
        return curve