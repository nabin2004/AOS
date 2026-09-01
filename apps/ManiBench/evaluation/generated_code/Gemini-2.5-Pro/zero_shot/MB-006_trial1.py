from manim import *
import numpy as np

class CentralLimitTheorem(Scene):
    """
    An animation demonstrating the Central Limit Theorem.
    1. Shows a non-normal (bimodal) population distribution.
    2. Repeatedly draws samples, calculates their means.
    3. Builds a histogram from the sample means, which gradually
       approaches a normal distribution.
    4. Overlays the theoretical normal distribution curve on the
       final histogram.
    """
    def construct(self):
        # --- CONFIGURATION ---
        # Population parameters (Bimodal distribution from two normal distributions)
        pop_mean1, pop_std1 = 2.5, 0.8
        pop_mean2, pop_std2 = 7.5, 1.2
        
        # Sampling parameters
        sample_size = 30
        total_samples = 2000
        
        # Axes ranges
        x_range = [0, 10, 1]
        pop_y_range = [0, 0.4, 0.1]
        # Y-range for the histogram of sample means. Adjusted for total_samples.
        sampling_y_range = [0, 350, 50] 
        
        # --- HELPER FUNCTIONS ---
        def bimodal_pdf(x):
            """PDF of the bimodal population distribution."""
            term1 = 0.5 * (1 / (pop_std1 * np.sqrt(2 * PI))) * np.exp(-0.5 * ((x - pop_mean1) / pop_std1) ** 2)
            term2 = 0.5 * (1 / (pop_std2 * np.sqrt(2 * PI))) * np.exp(-0.5 * ((x - pop_mean2) / pop_std2) ** 2)
            return term1 + term2

        def generate_bimodal_samples(n):
            """Generate n samples from the bimodal distribution."""
            # Decide for each point if it comes from dist1 or dist2 with 50/50 probability
            choices = np.random.choice([1, 2], size=n)
            samples1 = np.random.normal(pop_mean1, pop_std1, size=np.sum(choices == 1))
            samples2 = np.random.normal(pop_mean2, pop_std2, size=np.sum(choices == 2))
            return np.concatenate([samples1, samples2])

        # --- SCENE SETUP ---
        # Create titles
        pop_title = Text("Population Distribution (Bimodal)").to_edge(UP, buff=0.5).scale(0.8)
        sampling_title = Text(f"Distribution of Sample Means (n={sample_size})").to_edge(UP, buff=0.5).scale(0.8)

        # Create axes
        pop_axes = Axes(
            x_range=x_range,
            y_range=pop_y_range,
            x_length=5,
            y_length=3,
            axis_config={"include_tip": False},
        )
        
        sampling_axes = Axes(
            x_range=x_range,
            y_range=sampling_y_range,
            x_length=6,
            y_length=4,
            axis_config={"include_tip": False},
        )
        
        axes_group = VGroup(pop_axes, sampling_axes).arrange(RIGHT, buff=1.5).to_edge(DOWN, buff=1)

        # --- STEP 1: Show Population Distribution ---
        self.play(Write(pop_title))
        self.play(Create(pop_axes))

        pop_dist_curve = pop_axes.plot(bimodal_pdf, color=BLUE, x_range=[x_range[0], x_range[1]])
        pop_dist_label = pop_axes.get_graph_label(pop_dist_curve, label="PDF", x_val=8.5, direction=UP)
        
        self.play(Create(pop_dist_curve), Write(pop_dist_label))
        self.wait(1)

        # Transition to sampling scene layout
        self.play(
            ReplacementTransform(pop_title, sampling_title),
            VGroup(pop_axes, pop_dist_curve, pop_dist_label).animate.scale(0.7).to_corner(UL, buff=0.5)
        )
        self.play(Create(sampling_axes))
        
        # --- STEP 2 & 3: Animate Sampling and Build Histogram ---
        
        # Pre-compute all sample means for a smooth animation
        sample_means = [np.mean(generate_bimodal_samples(sample_size)) for _ in range(total_samples)]
        
        # Create histogram that will be updated
        num_bins = 40
        hist = Histogram(np.array(sample_means[:1]), number_of_bins=num_bins, x_range=[x_range[0], x_range[1]])
        hist.set_colors([YELLOW, ORANGE])
        
        # Add an updater to the histogram to grow it
        num_samples_tracker = ValueTracker(1)
        
        def update_histogram(h):
            current_num_samples = int(num_samples_tracker.get_value())
            if current_num_samples > 1:
                new_data = np.array(sample_means[:current_num_samples])
                new_hist = Histogram(new_data, number_of_bins=num_bins, x_range=[x_range[0], x_range[1]])
                new_hist.set_colors([YELLOW, ORANGE])
                h.become(new_hist)

        hist.add_updater(update_histogram)
        
        # Add a counter for the number of samples taken
        sample_counter_label = Text("Samples taken:").scale(0.6).next_to(sampling_axes, DOWN, buff=0.3).align_to(sampling_axes, LEFT)
        sample_counter = Integer(1).scale(0.6).next_to(sample_counter_label, RIGHT, buff=0.2)
        sample_counter.add_updater(lambda m: m.set_value(num_samples_tracker.get_value()))

        self.add(hist, sample_counter_label, sample_counter)
        
        # Animate the sampling process by advancing the ValueTracker
        self.play(
            num_samples_tracker.animate.set_value(total_samples),
            run_time=10,
            rate_func=linear
        )
        hist.remove_updater(update_histogram)
        sample_counter.remove_updater(lambda m: m.set_value(num_samples_tracker.get_value()))
        self.wait(1)

        # --- STEP 4: Overlay Normal Distribution ---
        
        # Theoretical parameters of the sampling distribution from CLT
        # For a 50/50 mixture distribution:
        pop_mean = 0.5 * pop_mean1 + 0.5 * pop_mean2
        pop_var = 0.5 * (pop_std1**2 + pop_mean1**2) + 0.5 * (pop_std2**2 + pop_mean2**2) - pop_mean**2
        pop_std = np.sqrt(pop_var)
        
        sampling_mean = pop_mean
        sampling_std = pop_std / np.sqrt(sample_size)

        def normal_pdf(x):
            """PDF of the resulting normal distribution, scaled to match histogram area."""
            bin_width = (x_range[1] - x_range[0]) / num_bins
            scale_factor = total_samples * bin_width
            return scale_factor * (1 / (sampling_std * np.sqrt(2 * PI))) * np.exp(-0.5 * ((x - sampling_mean) / sampling_std) ** 2)

        normal_curve = sampling_axes.plot(normal_pdf, color=RED, x_range=[x_range[0], x_range[1]])
        normal_label = MathTex(r"\mathcal{N}\left(\mu_{\bar{X}}, \sigma_{\bar{X}}^2\right)", color=RED).scale(0.7)
        normal_label.next_to(sampling_axes.c2p(sampling_mean, sampling_axes.y_range[1]), UP, buff=0.2)

        self.play(Create(normal_curve), Write(normal_label))
        self.wait(2)

        # --- STEP 5: Show Final Text ---
        final_text = Text("Distribution of sample means → Normal distribution", t2c={"Normal distribution": RED})
        final_text.scale(0.7).to_edge(DOWN, buff=0.5)

        self.play(Write(final_text))
        self.wait(3)