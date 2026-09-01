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

        # Clear initial distribution
        self.play(FadeOut(initial_hist), FadeOut(initial_label))

        # Sample size
        n_samples = 100

        # Create empty histogram for sample means
        sample_means_hist = axes.plot(lambda x: 0, color=GREEN)
        sample_means_hist.set_fill(GREEN, opacity=0.5)

        # Label for sample means
        sample_means_label = Text("Sample Means", font_size=24).to_edge(UP)
        self.play(Create(sample_means_hist), Write(sample_means_label))
        self.wait(1)

        # Generate samples and update histogram
        all_means = []
        for _ in range(n_samples):
            # Draw random samples from arbitrary distribution
            samples = [np.random.normal(loc=np.random.uniform(2, 7), scale=0.5) 
                       for _ in range(30)]
            
            # Calculate mean
            mean = np.mean(samples)
            all_means.append(mean)
            
            # Update histogram
            new_hist = axes.plot(lambda x: sum((x == m) for m in all_means) / len(all_means), color=GREEN)
            new_hist.set_fill(GREEN, opacity=0.5)
            
            self.play(Transform(sample_means_hist, new_hist))
            self.wait(0.05)

        # Final normal distribution approximation
        final_dist = axes.plot(lambda x: norm.pdf(x, loc=np.mean(all_means), scale=np.std(all_means)), color=PURPLE)
        final_dist.set_stroke(width=3)
        
        # Label for final distribution
        final_label = Text("Normal Distribution", font_size=24).next_to(final_dist, UP)
        
        # Transition to final distribution
        self.play(Transform(sample_means_hist, final_dist), Write(final_label))
        self.wait(1)

        # Conclusion text
        conclusion = Text("Distribution of sample means → Normal distribution", font_size=24)
        self.play(FadeOut(sample_means_label), FadeOut(final_label))
        self.play(Write(conclusion))
        self.wait(2)