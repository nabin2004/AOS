from manim import *

class CLTAnimation(Scene):
    def construct(self):
        # Title
        title = Text("Central Limit Theorem", font_size=36)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))

        # Create axes for histograms
        axes = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 0.8, 0.2],
            axis_config={"color": BLUE},
        )
        axes_labels = axes.get_axis_labels(x_label="Sample Mean", y_label="Frequency")

        # Arbitrary distribution (bimodal)
        dist_func = lambda x: 0.3 * np.exp(-(x - 2)**2 / 0.5**2) + \
                             0.3 * np.exp(-(x - 7)**2 / 0.5**2)
        
        # Initial histogram with arbitrary distribution
        initial_hist = axes.plot(lambda x: dist_func(x) * 0.5, color=YELLOW)
        initial_hist.set_fill(YELLOW, opacity=0.5)

        # Label for initial distribution
        initial_label = Text("Arbitrary Distribution", font_size=24).to_edge(UP)
        self.play(Create(axes), Write(axes_labels))
        self.play(Create(initial_hist), Write(initial_label))
        self.wait(1)

        # Sample size
        n_samples = 100

        # Create empty histogram for sample means
        sample_means = []
        sample_means_hist = axes.plot(lambda x: 0, color=GREEN)
        sample_means_hist.set_fill(GREEN, opacity=0.5)

        # Animation loop
        for _ in range(n_samples):
            # Draw random samples from arbitrary distribution
            samples = [np.random.normal(loc=4.5, scale=1.5) for _ in range(30)]
            
            # Compute mean of samples
            mean = sum(samples) / len(samples)
            sample_means.append(mean)
            
            # Update histogram for sample means
            if len(sample_means) == 1:
                new_hist = axes.plot(lambda x: 0, color=GREEN)
                new_hist.set_fill(GREEN, opacity=0.5)
                self.play(Transform(sample_means_hist, new_hist))
            else:
                new_hist = axes.plot(lambda x: 0, color=GREEN)
                new_hist.set_fill(GREEN, opacity=0.5)
                self.play(Transform(sample_means_hist, new_hist))
            
            # Add dot at current mean
            dot = Dot(point=axes.c2p(mean, 0), color=RED)
            self.play(Create(dot))
            self.wait(0.05)
            self.play(FadeOut(dot))

        # Convert list of means to numpy array for better visualization
        sample_means_np = np.array(sample_means)

        # Fit normal distribution to sample means
        mu, sigma = norm.fit(sample_means_np)
        normal_dist = axes.plot(lambda x: norm.pdf(x, mu, sigma), color=PURPLE)
        normal_dist.set_stroke(width=3)

        # Final labels
        final_label = Text("Normal Distribution", font_size=24).to_edge(UP)
        arrow = Arrow(start=LEFT, end=RIGHT, buff=0).next_to(final_label, RIGHT)
        
        # Morph histogram to normal distribution
        self.play(
            Transform(sample_means_hist, normal_dist),
            FadeOut(initial_hist),
            FadeOut(initial_label),
            Write(final_label),
            GrowArrow(arrow)
        )
        self.wait(2)

        # Conclusion text
        conclusion = Text("Distribution of sample means → Normal distribution", font_size=24)
        conclusion.to_edge(DOWN)
        self.play(Write(conclusion))
        self.wait(2)

        # Clear scene
        self.play(*[FadeOut(mob) for mob in self.mobjects])