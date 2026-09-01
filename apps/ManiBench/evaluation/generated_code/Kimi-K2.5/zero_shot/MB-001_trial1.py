from manim import *
import numpy as np

class CollidingBlocksPi(Scene):
    def construct(self):
        # Configuration
        self.camera.background_color = "#1e1e1e"
        
        # Title
        title = Text("Colliding Blocks & Digits of π", font_size=48, color=WHITE)
        subtitle = Text("Elastic Collisions on a Frictionless Surface", font_size=24, color=GRAY)
        subtitle.next_to(title, DOWN)
        
        self.play(Write(title), FadeIn(subtitle))
        self.wait(1)
        self.play(title.animate.to_edge(UP), subtitle.animate.next_to(title, DOWN))
        
        # Part 1: Physical Demonstration with mass ratio 1:1
        self.demonstrate_physical_collision(mass_ratio=1.0, expected_collisions=3, run_time=15)
        
        # Part 2: Phase Space Explanation
        self.explain_phase_space()
        
        # Part 3: Different Mass Ratios
        ratios = [1, 16, 100, 10000]
        collision_counts = [3, 10, 31, 314]
        
        for ratio, count in zip(ratios, collision_counts):
            if ratio == 1:
                continue  # Already did 1:1
            self.show_mass_ratio_comparison(ratio, count)
        
        # Part 4: The Pi Connection
        self.show_pi_formula()
        
        # End
        self.wait(2)

    def demonstrate_physical_collision(self, mass_ratio, expected_collisions, run_time=15):
        """Animate the physical blocks colliding"""
        # Setup
        m_small = 1.0
        m_large = mass_ratio * m_small
        
        # Create floor
        floor = Line(LEFT * 6, RIGHT * 6, color=GRAY)
        floor.shift(DOWN * 2)
        
        # Wall at left
        wall = Rectangle(height=2, width=0.5, color=WHITE, fill_opacity=0.3)
        wall.next_to(floor, LEFT, buff=0)
        wall.align_to(floor, DOWN)
        wall_label = Text("Wall", font_size=20).next_to(wall, UP)
        
        # Blocks
        block_small = Square(side_length=0.6, color=BLUE, fill_opacity=0.8)
        block_large = Square(side_length=1.0 if mass_ratio <= 100 else 0.8, color=RED, fill_opacity=0.8)
        
        block_small.move_to(floor.get_left() + RIGHT * 0.8 + UP * 0.3)
        block_large.move_to(floor.get_center() + RIGHT * 2 + UP * 0.5)
        
        # Labels
        label_small = MathTex(f"m={m_small}", color=BLUE).next_to(block_small, UP)
        label_large = MathTex(f"M={int(m_large)}", color=RED).next_to(block_large, UP)
        
        # Velocity vectors (initially zero for large, right for small)
        v_small = ValueTracker(2.0)  # Initial velocity
        v_large = ValueTracker(0.0)
        
        arrow_small = always_redraw(lambda: 
            Arrow(block_small.get_top(), block_small.get_top() + UP * v_small.get_value(), 
                  color=YELLOW, buff=0, max_tip_length_to_length_ratio=0.3)
        )
        arrow_large = always_redraw(lambda: 
            Arrow(block_large.get_top(), block_large.get_top() + UP * v_large.get_value(), 
                  color=YELLOW, buff=0, max_tip_length_to_length_ratio=0.3)
        )
        
        v_label_small = always_redraw(lambda: 
            MathTex(f"v_1={v_small.get_value():.2f}", font_size=20, color=YELLOW)
            .next_to(arrow_small, UP)
        )
        v_label_large = always_redraw(lambda: 
            MathTex(f"v_2={v_large.get_value():.2f}", font_size=20, color=YELLOW)
            .next_to(arrow_large, UP)
        )
        
        # Collision counter
        counter = ValueTracker(0)
        counter_text = always_redraw(lambda: 
            Text(f"Collisions: {int(counter.get_value())}", font_size=32, color=WHITE)
            .to_edge(UR)
        )
        
        # Energy and Momentum displays
        energy_eq = MathTex(r"\frac{1}{2}mv_1^2 + \frac{1}{2}Mv_2^2 = E", font_size=28)
        momentum_eq = MathTex(r"mv_1 + Mv_2 = P", font_size=28)
        equations = VGroup(energy_eq, momentum_eq).arrange(DOWN, aligned_edge=LEFT)
        equations.to_edge(DL)
        
        # Add everything
        self.play(
            Create(floor), Create(wall), Write(wall_label),
            FadeIn(block_small), FadeIn(block_large),
            Write(label_small), Write(label_large),
            Create(arrow_small), Create(arrow_large),
            Write(v_label_small), Write(v_label_large),
            Write(counter_text),
            Write(equations)
        )
        
        # Physics simulation
        dt = 0.05
        pos_small = np.array([0.8, -1.7, 0])  # Relative to floor left
        pos_large = np.array([4.0, -1.5, 0])  # x=4 on the floor
        
        vel_small = 2.0
        vel_large = 0.0
        
        collisions = 0
        max_time = run_time
        elapsed = 0
        
        # Animation loop
        while collisions < expected_collisions and elapsed < max_time:
            # Calculate time to next event
            if vel_small > vel_large:  # Small catching up or moving away
                t_to_hit = (pos_large[0] - pos_small[0] - 0.5) / (vel_small - vel_large) if vel_small > vel_large else float('inf')
            else:
                t_to_hit = float('inf')
            
            t_to_wall = (pos_small[0] - 0.3) / abs(vel_small) if vel_small < 0 else float('inf')
            
            if t_to_hit < 0 or t_to_hit > 100: t_to_hit = float('inf')
            if t_to_wall < 0 or t_to_wall > 100: t_to_wall = float('inf')
            
            dt_step = min(t_to_hit, t_to_wall, 0.5)  # Max 0.5s per step
            
            if dt_step < 0.001:
                dt_step = 0.1
            
            # Animate movement
            new_pos_small = pos_small + np.array([vel_small * dt_step, 0, 0])
            new_pos_large = pos_large + np.array([vel_large * dt_step, 0, 0])
            
            self.play(
                block_small.animate.move_to(new_pos_small),
                block_large.animate.move_to(new_pos_large),
                v_small.animate.set_value(vel_small),
                v_large.animate.set_value(vel_large),
                run_time=dt_step * 0.5,  # Speed up
                rate_func=linear
            )
            
            pos_small = new_pos_small
            pos_large = new_pos_large
            elapsed += dt_step * 0.5
            
            # Check collision
            if abs(t_to_hit - dt_step) < 0.01 or pos_small[0] + 0.3 >= pos_large[0] - 0.5:
                # Elastic collision
                v1, v2 = self.calculate_collision(m_small, m_large, vel_small, vel_large)
                vel_small, vel_large = v1, v2
                collisions += 1
                self.play(counter.animate.set_value(collisions), run_time=0.2)
                
                # Flash effect
                flash = Flash(block_large, color=WHITE, line_length=0.3, num_lines=8)
                self.play(flash, run_time=0.3)
                
            elif abs(t_to_wall - dt_step) < 0.01 or pos_small[0] <= 0.3:
                # Wall collision (elastic, velocity reverses)
                vel_small = -vel_small
                collisions += 1
                self.play(counter.animate.set_value(collisions), run_time=0.2)
                
                flash = Flash(wall, color=WHITE, line_length=0.3, num_lines=8)
                self.play(flash, run_time=0.3)
        
        # Final state
        self.wait(1)
        final_text = Text(f"Total Collisions: {collisions}", font_size=36, color=GREEN)
        final_text.next_to(counter_text, DOWN)
        self.play(Write(final_text))
        self.wait(2)
        
        # Cleanup
        self.play(
            *[FadeOut(mob) for mob in self.mobjects if mob not in [self.title, self.subtitle]]
        )

    def calculate_collision(self, m1, m2, v1, v2):
        """Calculate velocities after elastic collision"""
        v1_new = ((m1 - m2) * v1 + 2 * m2 * v2) / (m1 + m2)
        v2_new = (2 * m1 * v1 + (m2 - m1) * v2) / (m1 + m2)
        return v1_new, v2_new

    def explain_phase_space(self):
        """Show the phase space diagram"""
        title = Text("Phase Space Analysis", font_size=40).to_edge(UP)
        self.play(Write(title))
        
        # Create axes
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=6,
            y_length=6,
            axis_config={"include_tip": True, "numbers_to_exclude": [0]}
        ).shift(DOWN * 0.5)
        
        x_label = MathTex(r"x = \sqrt{M} \cdot v_2", font_size=24).next_to(axes.x_axis, RIGHT)
        y_label = MathTex(r"y = \sqrt{m} \cdot v_1", font_size=24).next_to(axes.y_axis, UP)
        
        self.play(Create(axes), Write(x_label), Write(y_label))
        
        # Energy circle
        circle = Circle(radius=2, color=BLUE, stroke_opacity=0.6)
        circle.move_to(axes.c2p(0, 0))
        circle_label = MathTex(r"x^2 + y^2 = 2E", color=BLUE, font_size=28).next_to(circle, UR)
        
        self.play(Create(circle), Write(circle_label))
        
        # Momentum line
        slope = -1.0  # For equal masses
        line = Line(axes.c2p(-2, 2 * slope + 1), axes.c2p(2, -2 * slope + 1), color=RED)
        line_label = MathTex(r"\sqrt{M}x + \sqrt{m}y = P", color=RED, font_size=28).next_to(line, LEFT)
        
        self.play(Create(line), Write(line_label))
        
        # Show intersection points
        dot1 = Dot(axes.c2p(1.5, 1.5), color=YELLOW)
        dot2 = Dot(axes.c2p(-1.5, -1.5), color=YELLOW)
        
        self.play(FadeIn(dot1))
        self.play(Transform(dot1.copy(), dot2), run_time=1)
        
        # Explanation text
        text = VGroup(
            Text("Each collision:", font_size=24),
            Text("• Block-Block: Jump to other intersection", font_size=20),
            Text("• Block-Wall: Reflect y-coordinate", font_size=20),
            Text("Path traces arcs on the circle", font_size=24, color=YELLOW)
        ).arrange(DOWN, aligned_edge=LEFT).to_edge(DR)
        
        self.play(Write(text))
        self.wait(3)
        
        # Show angle
        angle_arc = Arc(radius=1.5, start_angle=PI/4, angle=PI/2, color=GREEN)
        angle_arc.move_arc_center_to(axes.c2p(0, 0))
        angle_label = MathTex(r"2\theta", color=GREEN, font_size=24).next_to(angle_arc, RIGHT)
        
        self.play(Create(angle_arc), Write(angle_label))
        
        formula = MathTex(r"\theta = \arctan\sqrt{\frac{m}{M}}", font_size=28).next_to(text, UP)
        self.play(Write(formula))
        self.wait(3)
        
        self.play(*[FadeOut(mob) for mob in self.mobjects if mob not in [self.title, self.subtitle]])

    def show_mass_ratio_comparison(self, ratio, expected_count):
        """Show collision count for specific mass ratio"""
        group = VGroup()
        
        ratio_text = MathTex(f"\\frac{{M}}{{m}} = {ratio}", font_size=48)
        count_text = MathTex(f"\\text{{Collisions}} = {expected_count}", font_size=48, color=YELLOW)
        
        if ratio == 100:
            pi_hint = MathTex(r"\approx 10 \times \pi", font_size=36, color=GREEN)
            group = VGroup(ratio_text, count_text, pi_hint).arrange(DOWN)
        elif ratio == 10000:
            pi_hint = MathTex(r"\approx 100 \times \pi", font_size=36, color=GREEN)
            group = VGroup(ratio_text, count_text, pi_hint).arrange(DOWN)
        else:
            group = VGroup(ratio_text, count_text).arrange(DOWN)
        
        group.move_to(ORIGIN)
        
        self.play(Write(ratio_text))
        self.wait(0.5)
        self.play(Write(count_text))
        
        if ratio in [100, 10000]:
            self.wait(0.5)
            self.play(Write(pi_hint))
        
        self.wait(2)
        self.play(FadeOut(group))

    def show_pi_formula(self):
        """Show the mathematical connection to pi"""
        title = Text("The Universal Pattern", font_size=40).to_edge(UP)
        self.play(Write(title))
        
        formula = MathTex(
            r"\text{Collisions} = \left\lfloor \frac{\pi}{\arctan\sqrt{m/M}} \right\rfloor",
            font_size=36
        )
        
        approximation = MathTex(
            r"\approx \pi \sqrt{\frac{M}{m}} \quad \text{for } M \gg m",
            font_size=32,
            color=YELLOW
        ).next_to(formula, DOWN)
        
        example = MathTex(
            r"M/m = 100^n \Rightarrow \text{Collisions} \approx \pi \cdot 10^n",
            font_size=32,
            color=GREEN
        ).next_to(approximation, DOWN * 2)
        
        digits = VGroup(
            Text("3", font_size=48, color=BLUE),
            Text("31", font_size=48, color=BLUE),
            Text("314", font_size=48, color=BLUE),
            Text("3141", font_size=48, color=BLUE),
            Text("...", font_size=48, color=BLUE)
        ).arrange(RIGHT, buff=1).next_to(example, DOWN * 2)
        
        self.play(Write(formula))
        self.wait(1)
        self.play(Write(approximation))
        self.wait(1)
        self.play(Write(example))
        self.wait(1)
        self.play(Write(digits))
        self.wait(3)
        
        # Final conclusion
        conclusion = Text("Physics computes π through collisions!", 
                         font_size=32, color=WHITE).to_edge(DOWN)
        self.play(Write(conclusion))
        self.wait(3)

    @property
    def title(self):
        # Helper to keep title accessible
        for mob in self.mobjects:
            if isinstance(mob, Text) and "Colliding Blocks" in mob.text:
                return mob
        return VMobject()

    @property
    def subtitle(self):
        for mob in self.mobjects:
            if isinstance(mob, Text) and "Elastic" in mob.text:
                return mob
        return VMobject()