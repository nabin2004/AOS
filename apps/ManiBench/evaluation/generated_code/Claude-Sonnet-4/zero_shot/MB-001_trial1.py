from manim import *
import numpy as np

class BlockCollisionAnimation(Scene):
    def construct(self):
        # Configuration
        self.mass_A = 100  # Mass M (larger block)
        self.mass_B = 1    # Mass m (smaller block)
        self.initial_velocity_B = 2
        self.collision_count = 0
        self.max_collisions = 50
        
        # Setup scene
        self.setup_scene()
        self.animate_collisions()
        self.show_phase_space()
        self.show_multiple_ratios()
        
    def setup_scene(self):
        # Create blocks
        self.block_A = Rectangle(width=1.5, height=1, color=BLUE, fill_opacity=0.7)
        self.block_B = Rectangle(width=1, height=1, color=RED, fill_opacity=0.7)
        
        # Position blocks
        self.block_A.move_to([4, -2, 0])
        self.block_B.move_to([-4, -2, 0])
        
        # Labels
        self.label_A = MathTex(f"M = {self.mass_A}").next_to(self.block_A, UP)
        self.label_B = MathTex(f"m = {self.mass_B}").next_to(self.block_B, UP)
        
        # Velocity vectors
        self.velocity_A = 0
        self.velocity_B = self.initial_velocity_B
        
        self.vel_vector_A = Arrow(start=ORIGIN, end=RIGHT, color=BLUE)
        self.vel_vector_B = Arrow(start=ORIGIN, end=RIGHT, color=RED)
        
        self.update_velocity_vectors()
        
        # Collision counter
        self.counter_text = Text(f"Collisions: {self.collision_count}", font_size=24)
        self.counter_text.to_corner(UL)
        
        # Conservation equations
        self.energy_eq = MathTex(r"\frac{1}{2}m_1v_1^2 + \frac{1}{2}m_2v_2^2 = E")
        self.momentum_eq = MathTex(r"m_1v_1 + m_2v_2 = P")
        
        self.energy_eq.to_corner(UR)
        self.momentum_eq.next_to(self.energy_eq, DOWN)
        
        # Add to scene
        self.add(self.block_A, self.block_B, self.label_A, self.label_B)
        self.add(self.vel_vector_A, self.vel_vector_B)
        self.add(self.counter_text, self.energy_eq, self.momentum_eq)
        
    def update_velocity_vectors(self):
        # Update velocity vector positions and lengths
        scale = 0.5
        
        if abs(self.velocity_A) > 0.01:
            self.vel_vector_A.put_start_and_end_on(
                self.block_A.get_center() + UP * 0.8,
                self.block_A.get_center() + UP * 0.8 + RIGHT * self.velocity_A * scale
            )
        else:
            self.vel_vector_A.put_start_and_end_on(ORIGIN, ORIGIN)
            
        if abs(self.velocity_B) > 0.01:
            self.vel_vector_B.put_start_and_end_on(
                self.block_B.get_center() + UP * 0.8,
                self.block_B.get_center() + UP * 0.8 + RIGHT * self.velocity_B * scale
            )
        else:
            self.vel_vector_B.put_start_and_end_on(ORIGIN, ORIGIN)
    
    def elastic_collision(self):
        # Elastic collision formulas
        m1, m2 = self.mass_B, self.mass_A
        v1, v2 = self.velocity_B, self.velocity_A
        
        # New velocities after collision
        v1_new = ((m1 - m2) * v1 + 2 * m2 * v2) / (m1 + m2)
        v2_new = ((m2 - m1) * v2 + 2 * m1 * v1) / (m1 + m2)
        
        self.velocity_B = v1_new
        self.velocity_A = v2_new
        
        self.collision_count += 1
        
    def animate_collisions(self):
        dt = 0.1
        
        for _ in range(self.max_collisions):
            # Check if collision occurs
            if (self.block_B.get_center()[0] >= self.block_A.get_center()[0] - 1.25 and 
                self.velocity_B > self.velocity_A):
                
                # Collision!
                self.elastic_collision()
                
                # Update counter
                new_counter = Text(f"Collisions: {self.collision_count}", font_size=24)
                new_counter.to_corner(UL)
                self.play(Transform(self.counter_text, new_counter), run_time=0.2)
                
                # Flash collision
                flash = Circle(radius=0.5, color=YELLOW, fill_opacity=0.5)
                flash.move_to(self.block_A.get_center())
                self.play(FadeIn(flash), run_time=0.1)
                self.play(FadeOut(flash), run_time=0.1)
                
            # Check if B is moving away and slower than A
            if self.velocity_B <= self.velocity_A and self.velocity_B <= 0:
                break
                
            # Move blocks
            self.block_A.shift(RIGHT * self.velocity_A * dt)
            self.block_B.shift(RIGHT * self.velocity_B * dt)
            
            # Update labels and vectors
            self.label_A.next_to(self.block_A, UP)
            self.label_B.next_to(self.block_B, UP)
            self.update_velocity_vectors()
            
            self.wait(dt)
            
        # Final collision count
        final_text = Text(f"Total Collisions: {self.collision_count}", font_size=36, color=YELLOW)
        final_text.move_to(ORIGIN)
        self.play(Write(final_text))
        self.wait(2)
        self.play(FadeOut(final_text))
        
    def show_phase_space(self):
        # Clear scene
        self.play(*[FadeOut(mob) for mob in self.mobjects])
        
        # Phase space setup
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1],
            x_length=6,
            y_length=6,
            axis_config={"color": WHITE}
        )
        
        x_label = MathTex(r"\sqrt{m_1} v_1").next_to(axes.x_axis, DOWN)
        y_label = MathTex(r"\sqrt{m_2} v_2").next_to(axes.y_axis, LEFT)
        
        # Energy circle
        circle = Circle(radius=2, color=GREEN)
        circle.move_to(axes.get_origin())
        
        # Momentum line
        slope = -np.sqrt(self.mass_B / self.mass_A)
        line = Line(
            start=axes.c2p(-3, -3 * slope),
            end=axes.c2p(3, 3 * slope),
            color=RED
        )
        
        # Phase space title
        title = Text("Phase Space Representation", font_size=32)
        title.to_edge(UP)
        
        self.play(Create(axes), Write(x_label), Write(y_label), Write(title))
        self.play(Create(circle), Create(line))
        
        # Show bouncing point
        angle = 0
        point = Dot(color=YELLOW)
        
        for i in range(8):
            x = 2 * np.cos(angle)
            y = 2 * np.sin(angle)
            point.move_to(axes.c2p(x, y))
            
            if i == 0:
                self.play(FadeIn(point))
            else:
                self.play(point.animate.move_to(axes.c2p(x, y)), run_time=0.5)
                
            angle += 2 * np.arctan(np.sqrt(self.mass_B / self.mass_A))
            
        self.wait(2)
        
    def show_multiple_ratios(self):
        # Clear scene
        self.play(*[FadeOut(mob) for mob in self.mobjects])
        
        # Show different mass ratios and their collision counts
        ratios = [
            (1, 1, 1),
            (16, 1, 9),
            (100, 1, 31),
            (10000, 1, 314),
            (1000000, 1, 3141)
        ]
        
        title = Text("Mass Ratios and Collision Counts", font_size=32)
        title.to_edge(UP)
        self.play(Write(title))
        
        table_data = []
        for i, (M, m, collisions) in enumerate(ratios):
            ratio_text = MathTex(f"M:m = {M}:{m}")
            collision_text = MathTex(f"\\text{{Collisions}} = {collisions}")
            
            ratio_text.move_to([-2, 2 - i * 0.8, 0])
            collision_text.move_to([2, 2 - i * 0.8, 0])
            
            self.play(Write(ratio_text), Write(collision_text), run_time=0.8)
            
        # Pi connection
        pi_text = MathTex(r"\pi = 3.14159...", font_size=48, color=GOLD)
        pi_text.move_to([0, -2.5, 0])
        
        self.play(Write(pi_text))
        self.wait(2)
        
        # Arc angle explanation
        angle_explanation = MathTex(
            r"\text{Each collision: } \theta = 2\arctan\sqrt{\frac{m}{M}}",
            font_size=24
        )
        angle_explanation.next_to(pi_text, DOWN)
        
        self.play(Write(angle_explanation))
        self.wait(3)