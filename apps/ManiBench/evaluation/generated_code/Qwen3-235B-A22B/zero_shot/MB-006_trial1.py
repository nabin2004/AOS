from manim import *

class CentralLimitTheorem(Scene):
    def construct(self):
        # Title
        title = Text("Central Limit Theorem", font_size=36).to_edge(UP)
        self.play(Write(title))
        self.wait(1)

        # Explanation text
        explanation = Text(
            "Distribution of sample means → Normal distribution",
            font_size=24,
            color=YELLOW
        ).next_to(title, DOWN)
        self.play(Write(explanation))
        self.wait(1)

        # Define axes for original distribution
        ax1 = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 0.3, 0.05],
            x_length=5,
            y_length=3,
            axis_config={"include_tip": False}
        ).shift(LEFT * 3.5 + UP * 0.5)
        ax1_labels = ax1.get_axis_labels(x_label="x", y_label="Density")

        # Bimodal distribution (mixture of two Gaussians)
        def bimodal_pdf(x):
            return 0.5 * (1/(0.5 * np.sqrt(2*np.pi))) * np.exp(-0.5 * ((x - 3)/0.5)**2) + \
                   0.5 * (1/(0.5 * np.sqrt(2*np.pi))) * np.exp(-0.5 * ((x - 7)/0.5)**2)

        # Plot original distribution
        original_curve = ax1.plot(bimodal_pdf, x_range=[1, 9], color=BLUE)
        original_label = Text("Original Distribution", font_size=20).next_to(ax1, DOWN)

        self.play(
            Create(ax1),
            Write(ax1_labels),
            Create(original_curve),
            Write(original_label)
        )
        self.wait(1)

        # Histogram for sample means
        ax2 = Axes(
            x_range=[3, 7, 1],
            y_range=[0, 10, 2],
            x_length=5,
            y_length=3,
            axis_config={"include_tip": False}
        ).shift(RIGHT * 3.5 + UP * 0.5)
        ax2_labels = ax2.get_axis_labels(x_label="Sample Mean", y_label="Frequency")

        sample_mean_label = Text("Distribution of Sample Means", font_size=20).next_to(ax2, DOWN)
        self.play(
            Create(ax2),
            Write(ax2_labels),
            Write(sample_mean_label)
        )
        self.wait(0.5)

        # Simulate drawing samples
        np.random.seed(0)
        sample_means = []
        histogram = None
        n_samples = 300
        sample_size = 25

        # Function to generate sample from bimodal distribution
        def sample_bimodal(n):
            # Choose mode: 0 -> left peak, 1 -> right peak
            modes = np.random.choice([3, 7], size=n, p=[0.5, 0.5])
            return np.random.normal(modes, 0.5)

        for i in range(n_samples):
            # Draw sample and compute mean
            sample = sample_bimodal(sample_size)
            mean_val = np.mean(sample)
            sample_means.append(mean_val)

            # Update histogram every few steps
            if i % 10 == 0 or i == n_samples - 1:
                # Create new histogram
                bins = np.linspace(3, 7, 15)
                counts, _ = np.histogram(sample_means, bins=bins)
                new_histogram = ax2.get_bar_graph(
                    values=counts,
                    bar_colors=GREEN,
                    bar_width=0.8,
                    y_max=10,
                    y_min=0
                )

                if histogram is None:
                    histogram = new_histogram
                    self.play(Create(histogram), run_time=0.5)
                else:
                    self.play(
                        Transform(histogram, new_histogram),
                        run_time=0.2
                    )

        # Fit and show normal distribution curve over final histogram
        mean_of_means = np.mean(sample_means)
        std_of_means = np.std(sample_means)

        normal_curve = ax2.plot(
            lambda x: 10 * (1/(std_of_means * np.sqrt(2*np.pi))) * np.exp(-0.5 * ((x - mean_of_means)/std_of_means)**2),
            x_range=[3, 7],
            color=RED
        )
        normal_label = MathTex(r"\mathcal{N}(\mu, \sigma^2)", color=RED, font_size=30).next_to(normal_curve, UP, buff=0.2)

        self.play(
            Create(normal_curve),
            Write(normal_label)
        )
        self.wait(2)

        # Final animation conclusion
        conclusion = Text("Even if original distribution is not normal...", font_size=24, color=TEAL).to_edge(DOWN * 2)
        conclusion2 = Text("...sample means become normally distributed!", font_size=24, color=TEAL).next_to(conclusion, DOWN)
        self.play(Write(conclusion), Write(conclusion2))
        self.wait(3)

        self.play(
            FadeOut(VGroup(
                title, explanation, ax1, ax1_labels, original_curve, original_label,
                ax2, ax2_labels, sample_mean_label, histogram, normal_curve, normal_label,
                conclusion, conclusion2
            ))
        )