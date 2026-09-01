from manim import *
import numpy as np

class CentralLimitTheorem(Scene):
    def construct(self):
        # Title
        title = Text("Central Limit Theorem", font_size=40)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)

        # Parameters
        sample_size = 30
        num_samples_total = 500
        bin_count = 30
        x_range = [-3, 3, 0.1]
        
        # Axes for the sampling distribution (bottom)
        axes = Axes(
            x_range=x_range,
            y_range=[0, 0.5, 0.1],
            axis_config={"include_tip": False, "numbers_to_exclude": [0]},
            x_length=8,
            y_length=4,
        ).shift(DOWN * 0.5)
        
        x_label = axes.get_x_axis_label(r"\bar{x} (\text{Sample Mean})")
        y_label = axes.get_y_axis_label(r"\text{Frequency}", direction=LEFT)
        
        self.play(Create(axes), Write(x_label), Write(y_label))
        self.wait(0.5)

        # Initial empty histogram bars (VGroup)
        # We will update these bars dynamically
        bars = VGroup()
        bin_width = (x_range[1] - x_range[0]) / bin_count
        for i in range(bin_count):
            rect = Rectangle(
                width=bin_width, 
                height=0, 
                stroke_width=0, 
                fill_color=BLUE, 
                fill_opacity=0.7
            )
            # Position rect based on bin index
            x_pos = x_range[0] + (i * bin_width) + (bin_width / 2)
            rect.move_to(axes.c2p(x_pos, 0), aligned_edge=DOWN)
            bars.add(rect)
        
        self.add(bars)

        # Normal Distribution Curve (Target)
        def normal_pdf(x):
            return (1 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * x**2) * 0.4 # Scaled for visual fit
        
        normal_curve = axes.plot(normal_pdf, color=YELLOW, x_range=x_range, stroke_width=3)
        normal_label = MathTex(r"\mathcal{N}(0, 1)", color=YELLOW).next_to(normal_curve, UR, buff=0.2)
        
        # Text explanation
        explanation = Text(
            "Distribution of sample means → Normal distribution", 
            font_size=24
        ).to_edge(DOWN)
        self.play(Write(explanation))

        # Simulation Logic
        sample_means = []
        
        # Animation Loop
        # We simulate in batches to update the animation smoothly
        batch_size = 10
        total_batches = num_samples_total // batch_size
        
        # Counter for samples drawn
        counter = Integer(0).to_corner(UR)
        self.play(Write(counter))

        for i in range(total_batches):
            # Generate batch of sample means
            # Source distribution: Uniform(-sqrt(3), sqrt(3)) has variance 1, mean 0
            # Or just standard uniform and normalize later. Let's use Uniform(-2, 2) for variety
            # CLT says mean of samples approaches Normal regardless of source.
            batch_means = []
            for _ in range(batch_size):
                samples = np.random.uniform(-2, 2, sample_size)
                batch_means.append(np.mean(samples))
            
            sample_means.extend(batch_means)
            
            # Calculate histogram heights
            counts, bin_edges = np.histogram(sample_means, bins=bin_count, range=(x_range[0], x_range[1]))
            max_height = 0.45 # Cap height to fit axes
            
            # Normalize counts to fit the visual scale roughly
            # As N increases, the max count increases. We scale relative to current max or fixed max.
            # To show convergence, let's scale by total samples to approximate probability density
            densities = counts / (len(sample_means) * bin_width)
            
            # Scale factor to match the normal curve visual height (approx 0.4)
            # Theoretical max of standard normal PDF is ~0.4. 
            # Our densities should approach this.
            
            new_heights = densities * 0.95 # Slight adjustment for visual padding

            # Update Bars
            animations = []
            for j, rect in enumerate(bars):
                target_h = new_heights[j]
                # Clamp height
                target_h = min(target_h, max_height)
                
                # Create target rectangle for transformation
                new_rect = Rectangle(
                    width=bin_width,
                    height=target_h,
                    stroke_width=0,
                    fill_color=BLUE,
                    fill_opacity=0.7
                )
                x_pos = x_range[0] + (j * bin_width) + (bin_width / 2)
                new_rect.move_to(axes.c2p(x_pos, 0), aligned_edge=DOWN)
                
                animations.append(Transform(rect, new_rect))
            
            # Update counter
            new_count = len(sample_means)
            anim_counter = counter.animate.set_value(new_count)
            
            self.play(*animations, anim_counter, run_time=0.15)

        # Final Polish
        # Overlay the theoretical normal curve clearly
        self.play(Create(normal_curve), Write(normal_label), run_time=2)
        
        self.wait(2)