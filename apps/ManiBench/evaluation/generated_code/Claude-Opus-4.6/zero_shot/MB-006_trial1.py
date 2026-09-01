from manim import *
import numpy as np

class CentralLimitTheorem(Scene):
    def construct(self):
        # Title
        title = Text("Central Limit Theorem", font_size=40, color=YELLOW)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # Parameters
        num_bins = 20
        num_iterations = 50
        sample_size_start = 2
        sample_size_end = 30
        num_final_samples = 500

        # --- Left side: Original Distribution (Bimodal) ---
        left_title = Text("Original Distribution\n(Bimodal)", font_size=20, color=BLUE)
        left_title.move_to(UP * 2.5 + LEFT * 4)

        # Create bimodal distribution samples
        np.random.seed(42)
        bimodal_samples = np.concatenate([
            np.random.normal(2, 0.5, 5000),
            np.random.normal(6, 0.5, 5000)
        ])

        # Build histogram for original distribution
        orig_hist_height = 2.5
        orig_hist_width = 3.0
        orig_bins = np.linspace(0, 8, num_bins + 1)
        orig_counts, _ = np.histogram(bimodal_samples, bins=orig_bins)
        orig_max_count = orig_counts.max()

        orig_bars = VGroup()
        bar_width = orig_hist_width / num_bins
        for i, count in enumerate(orig_counts):
            bar_height = (count / orig_max_count) * orig_hist_height
            bar = Rectangle(
                width=bar_width * 0.9,
                height=max(bar_height, 0.01),
                fill_color=BLUE,
                fill_opacity=0.7,
                stroke_color=WHITE,
                stroke_width=0.5
            )
            bar.move_to(
                LEFT * 5.5 + RIGHT * (i * bar_width + bar_width / 2) + DOWN * 0.5 + UP * bar_height / 2
            )
            orig_bars.add(bar)

        # Axis for original
        orig_axis = Line(
            LEFT * 5.5 + DOWN * 0.5,
            LEFT * 5.5 + RIGHT * orig_hist_width + DOWN * 0.5,
            color=WHITE
        )
        orig_y_axis = Line(
            LEFT * 5.5 + DOWN * 0.5,
            LEFT * 5.5 + DOWN * 0.5 + UP * orig_hist_height,
            color=WHITE
        )

        orig_group = VGroup(orig_bars, orig_axis, orig_y_axis)
        orig_group.move_to(LEFT * 3.5 + DOWN * 0.5)

        left_title.next_to(orig_group, UP, buff=0.3)

        self.play(Write(left_title))
        self.play(Create(orig_axis), Create(orig_y_axis))
        self.play(LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in orig_bars], lag_ratio=0.03))
        self.wait(0.5)

        # --- Right side: Distribution of Sample Means ---
        right_title = Text("Distribution of\nSample Means", font_size=20, color=GREEN)

        means_hist_height = 2.5
        means_hist_width = 3.0
        # The mean of bimodal is ~4, range of means will be narrower
        means_bins = np.linspace(2, 6, num_bins + 1)
        means_bar_width = means_hist_width / num_bins

        # Axis for means
        means_axis = Line(ORIGIN, RIGHT * means_hist_width, color=WHITE)
        means_y_axis = Line(ORIGIN, UP * means_hist_height, color=WHITE)

        means_axis_group = VGroup(means_axis, means_y_axis)
        means_axis_group.move_to(RIGHT * 3.5 + DOWN * 0.5, aligned_edge=DOWN)
        # Adjust position
        means_origin = means_axis.get_start()

        right_title.next_to(means_axis_group, UP, buff=0.8)

        self.play(Write(right_title))
        self.play(Create(means_axis), Create(means_y_axis))
        self.wait(0.3)

        # Animate sampling process
        sample_means = []
        current_bars = VGroup()

        # Info text
        info_text = Text("Sample size: n = 2", font_size=18, color=WHITE)
        info_text.next_to(means_axis_group, DOWN, buff=0.3)
        count_text = Text("Samples: 0", font_size=18, color=WHITE)
        count_text.next_to(info_text, DOWN, buff=0.15)
        self.play(Write(info_text), Write(count_text))

        # Phase 1: Animate individual samples being drawn (small n)
        sample_size = 5
        new_info = Text(f"Sample size: n = {sample_size}", font_size=18, color=WHITE)
        new_info.move_to(info_text.get_center())
        self.play(Transform(info_text, new_info))

        for iteration in range(30):
            # Draw sample
            sample = np.random.choice(bimodal_samples, size=sample_size)
            sample_mean = np.mean(sample)
            sample_means.append(sample_mean)

            # Flash effect on original distribution
            if iteration < 10:
                flash_dot = Dot(
                    orig_group.get_center() + UP * 0.5,
                    color=YELLOW, radius=0.08
                )
                arrow = Arrow(
                    orig_group.get_center() + UP * 0.5,
                    means_axis_group.get_center() + UP * 0.5,
                    color=YELLOW,
                    stroke_width=2,
                    max_tip_length_to_length_ratio=0.1
                )

                # Update histogram
                counts, _ = np.histogram(sample_means, bins=means_bins)
                max_count = max(counts.max(), 1)

                new_bars = VGroup()
                for i, count in enumerate(counts):
                    bar_height = (count / max_count) * means_hist_height
                    bar = Rectangle(
                        width=means_bar_width * 0.9,
                        height=max(bar_height, 0.01),
                        fill_color=GREEN,
                        fill_opacity=0.7,
                        stroke_color=WHITE,
                        stroke_width=0.5
                    )
                    bar.next_to(means_axis.get_start(), RIGHT, buff=0)
                    bar.shift(RIGHT * i * means_bar_width + RIGHT * means_bar_width * 0.05)
                    bar.align_to(means_axis, DOWN)
                    orig_center = bar.get_center()
                    bar.move_to(
                        means_axis.get_start() + RIGHT * (i * means_bar_width + means_bar_width / 2) + UP * max(bar_height, 0.01) / 2
                    )
                    new_bars.add(bar)

                new_count = Text(f"Samples: {len(sample_means)}", font_size=18, color=WHITE)
                new_count.move_to(count_text.get_center())

                self.play(
                    FadeIn(flash_dot, scale=0.5),
                    GrowArrow(arrow),
                    run_time=0.2
                )
                self.play(
                    FadeOut(flash_dot),
                    FadeOut(arrow),
                    Transform(current_bars, new_bars) if len(current_bars) > 0 else FadeIn(new_bars),
                    Transform(count_text, new_count),
                    run_time=0.2
                )
                if len(current_bars) == 0:
                    current_bars = new_bars
            else:
                # Faster updates without arrows
                counts, _ = np.histogram(sample_means, bins=means_bins)
                max_count = max(counts.max(), 1)

                new_bars = VGroup()
                for i, count in enumerate(counts):
                    bar_height = (count / max_count) * means_hist_height
                    bar = Rectangle(
                        width=means_bar_width * 0.9,
                        height=max(bar_height, 0.01),
                        fill_color=GREEN,
                        fill_opacity=0.7,
                        stroke_color=WHITE,
                        stroke_width=0.5
                    )
                    bar.move_to(
                        means_axis.get_start() + RIGHT * (i * means_bar_width + means_bar_width / 2) + UP * max(bar_height, 0.01) / 2
                    )
                    new_bars.add(bar)

                new_count = Text(f"Samples: {len(sample_means)}", font_size=18, color=WHITE)
                new_count.move_to(count_text.get_center())

                self.play(
                    Transform(current_bars, new_bars),
                    Transform(count_text, new_count),
                    run_time=0.1
                )

        # Phase 2: Add many more samples quickly with increasing sample size
        for sample_size in [10, 30]:
            new_info = Text(f"Sample size: n = {sample_size}", font_size=18, color=WHITE)
            new_info.move_to(info_text.get_center())
            self.play(Transform(info_text, new_info), run_time=0.3)

            # Reset means for new sample size
            sample_means = []

            for iteration in range(200):
                sample = np.random.choice(bimodal_samples, size=sample_size)
                sample_mean = np.mean(sample)
                sample_means.append(sample_mean)

            # Adjust bins for this sample size
            mean_of_means = np.mean(sample_means)
            std_of_means = np.std(sample_means)
            adjusted_bins = np.linspace(
                mean_of_means - 4 * std_of_means,
                mean_of_means + 4 * std_of_means,
                num_bins + 1
            )

            counts, _ = np.histogram(sample_means, bins=adjusted_bins)
            max_count = max(counts.max(), 1)

            new_bars = VGroup()
            for i, count in enumerate(counts):
                bar_height = (count / max_count) * means_hist_height
                bar = Rectangle(
                    width=means_bar_width * 0.9,
                    height=max(bar_height, 0.01),
                    fill_color=GREEN,
                    fill_opacity=0.7,
                    stroke_color=WHITE,
                    stroke_width=0.5
                )
                bar.move_to(
                    means_axis.get_start() + RIGHT * (i * means_bar_width + means_bar_width / 2) + UP * max(bar_height, 0.01) / 2
                )
                new_bars.add(bar)

            new_count = Text(f"Samples: {len(sample_means)}", font_size=18, color=WHITE)
            new_count.move_to(count_text.get_center())

            self.play(
                Transform(current_bars, new_bars),
                Transform(count_text, new_count),
                run_time=1.0
            )
            self.wait(0.5)

        # Phase 3: Final large sample with n=30, overlay normal curve
        self.wait(0.5)

        # Draw normal distribution curve overlay
        mean_val = np.mean(sample_means)
        std_val = np.std(sample_means)

        # Create the normal curve
        x_start = adjusted_bins[0]
        x_end = adjusted_bins[-1]
        x_range = x_end - x_start

        def normal_pdf(x):
            return (1 / (std_val * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean_val) / std_val) ** 2)

        max_pdf = normal_pdf(mean_val)

        # Map the curve to the histogram coordinates
        curve_points = []
        num_curve_points = 100
        for i in range(num_curve_points + 1):
            x = x_start + (x_end - x_start) * i / num_curve_points
            y = normal_pdf(x)
            # Map x to screen coordinates
            screen_x = means_axis.get_start()[0] + (x - x_start) / x_range * means_hist_width
            screen_y = means_axis.get_start()[1] + (y / max_pdf) * means_hist_height
            curve_points.append([screen_x, screen_y, 0])

        normal_curve = VMobject()
        normal_curve.set_points_smoothly([np.array(p) for p in curve_points])
        normal_curve.set_color(RED)
        normal_curve.set_stroke(width=3)

        normal_label = Text("Normal\nDistribution", font_size=16, color=RED)
        normal_label.next_to(normal_curve, RIGHT, buff=0.1)

        self.play(Create(normal_curve), run_time=1.5)
        self.play(Write(normal_label))
        self.wait(0.5)

        # Add mu and sigma labels
        mu_text = MathTex(r"\mu = " + f"{mean_val:.2f}", font_size=24, color=YELLOW)
        sigma_text = MathTex(r"\sigma = " + f"{std_val:.2f}", font_size=24, color=YELLOW)
        stats_group = VGroup(mu_text, sigma_text).arrange(DOWN, buff=0.1)
        stats_group.next_to(means_axis_group, DOWN, buff=0.8)

        self.play(Write(stats_group))
        self.wait(0.5)

        # Final text
        final_text = Text(
            "Distribution of sample means → Normal distribution",
            font_size=28,
            color=YELLOW
        )
        final_text.to_edge(DOWN, buff=0.3)

        # Add a surrounding rectangle for emphasis
        box = SurroundingRectangle(final_text, color=YELLOW, buff=0.15)

        self.play(Write(final_text), Create(box), run_time=1.5)
        self.wait(0.5)

        # CLT formula
        clt_formula = MathTex(
            r"\bar{X}_n \xrightarrow{d} \mathcal{N}\left(\mu, \frac{\sigma^2}{n}\right)",
            font_size=32,
            color=WHITE
        )
        clt_formula.next_to(final_text, UP, buff=0.3)
        self.play(Write(clt_formula))

        self.wait(3)