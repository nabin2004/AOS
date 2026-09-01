from manim import *
import numpy as np

class CentralLimitTheorem(Scene):
    def construct(self):
        # Title
        title = Text("Central Limit Theorem", font_size=48, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        
        # Create axes for original distribution
        axes1 = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 0.5, 0.1],
            x_length=5,
            y_length=3,
            axis_config={"color": WHITE}
        )
        axes1.to_corner(UL, buff=0.5)
        axes1.shift(DOWN * 0.5)
        
        # Create axes for sample means distribution
        axes2 = Axes(
            x_range=[0, 10, 1],
            y_range=[0, 1.5, 0.3],
            x_length=5,
            y_length=3,
            axis_config={"color": WHITE}
        )
        axes2.to_corner(UR, buff=0.5)
        axes2.shift(DOWN * 0.5)
        
        # Labels for axes
        label1 = Text("Original Distribution", font_size=24, color=YELLOW)
        label1.next_to(axes1, DOWN, buff=0.2)
        
        label2 = Text("Sample Means Distribution", font_size=24, color=GREEN)
        label2.next_to(axes2, DOWN, buff=0.2)
        
        self.play(Create(axes1), Create(axes2))
        self.play(Write(label1), Write(label2))
        self.wait(1)
        
        # Create bimodal distribution (original)
        x_vals = np.linspace(0, 10, 100)
        y_vals = 0.15 * np.exp(-((x_vals - 2.5)**2) / 2) + 0.15 * np.exp(-((x_vals - 7.5)**2) / 2)
        
        # Create histogram bars for original distribution
        original_bars = VGroup()
        bar_width = 0.8
        for i in range(10):
            x_center = i + 0.5
            height = 0.15 * np.exp(-((x_center - 2.5)**2) / 2) + 0.15 * np.exp(-((x_center - 7.5)**2) / 2)
            bar = Rectangle(
                width=bar_width,
                height=height * 6,  # Scale for visibility
                color=BLUE,
                fill_opacity=0.7
            )
            bar.move_to(axes1.c2p(x_center, height/2))
            original_bars.add(bar)
        
        self.play(Create(original_bars))
        self.wait(1)
        
        # Initialize sample means histogram
        sample_means = []
        sample_bars = VGroup()
        
        # Animation parameters
        n_iterations = 20
        sample_size = 30
        
        # Text showing the process
        process_text = Text("Drawing samples and computing means...", font_size=24, color=WHITE)
        process_text.to_edge(DOWN, buff=1)
        self.play(Write(process_text))
        
        # Simulate sampling process
        for iteration in range(n_iterations):
            # Generate random sample from bimodal distribution
            samples = []
            for _ in range(sample_size):
                if np.random.random() < 0.5:
                    sample = np.random.normal(2.5, 1)
                else:
                    sample = np.random.normal(7.5, 1)
                sample = np.clip(sample, 0, 10)
                samples.append(sample)
            
            # Calculate sample mean
            sample_mean = np.mean(samples)
            sample_means.append(sample_mean)
            
            # Update histogram of sample means
            new_sample_bars = VGroup()
            
            # Create bins for sample means
            bins = np.linspace(0, 10, 11)
            hist, _ = np.histogram(sample_means, bins=bins, density=True)
            
            for i in range(10):
                x_center = i + 0.5
                height = hist[i] if i < len(hist) else 0
                bar = Rectangle(
                    width=bar_width,
                    height=height * 2,  # Scale for visibility
                    color=GREEN,
                    fill_opacity=0.7
                )
                bar.move_to(axes2.c2p(x_center, height/2))
                new_sample_bars.add(bar)
            
            # Animate the update
            if iteration == 0:
                self.play(Create(new_sample_bars), run_time=0.5)
            else:
                self.play(Transform(sample_bars, new_sample_bars), run_time=0.3)
            
            sample_bars = new_sample_bars
        
        self.wait(1)
        
        # Show normal distribution overlay
        normal_curve = axes2.plot(
            lambda x: 1.5 * np.exp(-((x - 5)**2) / 8) / np.sqrt(2 * np.pi * 4),
            x_range=[0, 10],
            color=RED,
            stroke_width=4
        )
        
        normal_label = Text("Normal Distribution", font_size=20, color=RED)
        normal_label.next_to(normal_curve, UP, buff=0.2)
        
        self.play(Create(normal_curve), Write(normal_label))
        self.wait(1)
        
        # Final message
        final_text = Text(
            "Distribution of sample means → Normal distribution",
            font_size=32,
            color=YELLOW
        )
        final_text.move_to(process_text.get_center())
        
        self.play(Transform(process_text, final_text))
        self.wait(2)
        
        # Show mathematical notation
        clt_formula = MathTex(
            r"\bar{X}_n \sim N\left(\mu, \frac{\sigma^2}{n}\right)",
            font_size=36,
            color=WHITE
        )
        clt_formula.to_edge(DOWN, buff=0.5)
        
        self.play(Write(clt_formula))
        self.wait(3)