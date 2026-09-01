from manim import *

class CLTAnimation(Scene):
    def construct(self):
        # Title
        title = Text("Central Limit Theorem", font_size=36)
        self.play(Write(title))
        self.wait(1)
        self.play(FadeOut(title))

        # Create initial distribution (bimodal for contrast)
        axes = Axes(
            x_range=[0, 10],
            y_range=[0, 0.8],
            axis_config={"color": BLUE},
        )
        dist_func = lambda x: 0.3 * np.exp(-((x - 2)**2)) + 0.3 * np.exp(-((x - 8)**2))
        graph = axes.plot(dist_func, color=YELLOW)
        graph_label = MathTex(r"f(x)").next_to(graph, UP)

        # Display initial distribution
        self.play(Create(axes), Create(graph), Write(graph_label))
        self.wait(1)

        # Sample size explanation
        sample_text = Text("Sample Size:", font_size=24).to_edge(UP)
        n_samples = ValueTracker(10)
        sample_display = always_redraw(lambda: 
            Tex(f"{int(n_samples.get_value())}").next_to(sample_text, RIGHT)
        )
        self.play(Write(sample_text), FadeIn(sample_display))
        
        # Generate samples and calculate means
        means = []
        num_samples = int(n_samples.get_value())
        for _ in range(num_samples):
            samples = [np.random.uniform(0, 10) for _ in range(10)]
            mean = sum(samples) / len(samples)
            means.append(mean)
            
            # Update display
            if len(means) % 10 == 0:
                self.play(
                    n_samples.animate.set_value(len(means)),
                    run_time=0.1
                )

        # Create histogram of sample means
        hist_data = [means.count(i) for i in range(int(min(means)), int(max(means))+1)]
        hist = BarChart(
            values=hist_data,
            max_value=max(hist_data),
            bar_names=[str(i) for i in range(int(min(means)), int(max(means))+1)],
            bar_colors=[BLUE_D]*len(hist_data),
            bar_fill_opacity=0.7,
            x_length=8,
            y_length=4,
            x_start=-4,
            y_start=-2,
        ).move_to(DOWN*0.5)
        
        # Label for sample means
        sample_means_label = Text("Sample Means", font_size=24).next_to(hist, UP)
        self.play(Create(hist), Write(sample_means_label))
        self.wait(1)

        # Morph to normal distribution
        normal_dist = axes.plot(lambda x: 0.1 * np.exp(-(x-5)**2), color=GREEN)
        normal_label = MathTex(r"\mathcal{N}(5, \sigma^2)").next_to(normal_dist, DOWN)
        
        self.play(TransformFromCopy(hist, normal_dist), Write(normal_label))
        self.wait(1)

        # Final message
        final_message = Text("Distribution of sample means → Normal distribution", font_size=24)
        self.play(Write(final_message))
        self.wait(2)