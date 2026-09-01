from manim import *
import numpy as np

class ElasticCollision(Scene):
    def construct(self):
        # Parameters
        M = 1  # Mass of block A
        m = 0.01  # Mass of block B (m/M = 100)
        v0 = 5  # Initial velocity of block B
        x_A = 10
        x_B = 0
        n_max = 100  # Maximum number of collisions to simulate
        
        # Initial state
        block_A = Rectangle(width=1, height=0.5, color=RED).move_to([x_A, 0])
        block_B = Rectangle(width=1, height=0.5, color=BLUE).move_to([x_B, 0])
        arrow_A = Arrow(block_A.get_center(), block_A.get_center() + RIGHT * 0, color=RED)
        arrow_B = Arrow(block_B.get_center(), block_B.get_center() + RIGHT * v0, color=BLUE)
        
        collision_count = 0
        collision_text = Text("# Collisions = 0").to_corner(UL)
        
        # Equations
        ke_eq = MathTex(r"\frac{1}{2}m_1v_1^2 + \frac{1}{2}m_2v_2^2 = E").to_corner(UR)
        momentum_eq = MathTex(r"m_1v_1 + m_2v_2 = P").to_corner(UR).next_to(ke_eq, DOWN)
        
        # Phase space
        phase_space = Axes(x_range=[-5, 5], y_range=[-5, 5], axis_config={"include_numbers": True})
        phase_space.add_coordinate_labels()
        phase_space.set_axis_orientations(UP, RIGHT)
        phase_space_label = Text("Phase Space (√m₁·v₁, √m₂·v₂)", font_size=16).next_to(phase_space, UP)
        
        # Initial phase space point
        initial_state = Dot(phase_space.c2p(np.sqrt(M) * 0, np.sqrt(m) * v0), color=BLUE)
        
        # Ellipse (energy circle)
        E = 0.5 * m * v0**2
        a = np.sqrt(2 * E / M)
        b = np.sqrt(2 * E / m)
        ellipse = Ellipse(width=2 * a, height=2 * b, color=GREEN).move_to(ORIGIN)
        
        # Momentum line
        P = m * v0
        slope = -np.sqrt(M / m)
        intercept = P
        momentum_line = Line(start=phase_space.c2p(-5, intercept), end=phase_space.c2p(5, intercept), color=YELLOW)
        
        # Show initial state
        self.play(Create(block_A), Create(block_B), Create(arrow_A), Create(arrow_B), Write(collision_text), Write(ke_eq), Write(momentum_eq))
        self.wait(1)
        
        # Simulation loop
        v_A = 0
        v_B = v0
        
        for i in range(n_max):
            # Collision
            if block_B.get_center()[0] < block_A.get_center()[0]:
                # Calculate new velocities
                v_A_new = (M * v_A - m * v_B) / (M + m) * 2 + v_A
                v_B_new = (m * v_B - M * v_A) / (M + m) * 2 + v_B
                
                # Update velocities
                v_A = v_A_new
                v_B = v_B_new
                
                # Update blocks' positions
                block_A.move_to([block_A.get_center()[0] + v_A, 0])
                block_B.move_to([block_B.get_center()[0] + v_B, 0])
                
                # Update arrows
                arrow_A.set_end(block_A.get_center() + RIGHT * v_A)
                arrow_B.set_end(block_B.get_center() + RIGHT * v_B)
                
                # Increment collision counter
                collision_count += 1
                collision_text.set_text(f"# Collisions = {collision_count}")
                
                # Update phase space point
                phase_space_point = Dot(phase_space.c2p(np.sqrt(M) * v_A, np.sqrt(m) * v_B), color=BLUE)
                
                self.play(
                    Transform(arrow_A, arrow_A.copy().set_end(block_A.get_center() + RIGHT * v_A)),
                    Transform(arrow_B, arrow_B.copy().set_end(block_B.get_center() + RIGHT * v_B)),
                    Write(collision_text),
                    Create(phase_space_point),
                    run_time=0.1
                )
                self.wait(0.1)
            else:
                break
        
        # Final state
        self.play(FadeOut(arrow_A), FadeOut(arrow_B))
        self.wait(1)
        
        # Demonstrate different mass ratios
        for ratio in [1, 16, 100, 10000, 1000000]:
            M = 1
            m = 1 / ratio
            v0 = 5
            
            block_A = Rectangle(width=1, height=0.5, color=RED).move_to([x_A, 0])
            block_B = Rectangle(width=1, height=0.5, color=BLUE).move_to([x_B, 0])
            arrow_A = Arrow(block_A.get_center(), block_A.get_center() + RIGHT * 0, color=RED)
            arrow_B = Arrow(block_B.get_center(), block_B.get_center() + RIGHT * v0, color=BLUE)
            
            collision_count = 0
            collision_text = Text(f"# Collisions = 0 (m/M = {ratio})").to_corner(UL)
            
            v_A = 0
            v_B = v0
            
            for i in range(n_max):
                if block_B.get_center()[0] < block_A.get_center()[0]:
                    v_A_new = (M * v_A - m * v_B) / (M + m) * 2 + v_A
                    v_B_new = (m * v_B - M * v_A) / (M + m) * 2 + v_B
                    
                    v_A = v_A_new
                    v_B = v_B_new
                    
                    block_A.move_to([block_A.get_center()[0] + v_A, 0])
                    block_B.move_to([block_B.get_center()[0] + v_B, 0])
                    
                    arrow_A.set_end(block_A.get_center() + RIGHT * v_A)
                    arrow_B.set_end(block_B.get_center() + RIGHT * v_B)
                    
                    collision_count += 1
                    collision_text.set_text(f"# Collisions = {collision_count} (m/M = {ratio})")
                    
                    self.play(
                        Transform(arrow_A, arrow_A.copy().set_end(block_A.get_center() + RIGHT * v_A)),
                        Transform(arrow_B, arrow_B.copy().set_end(block_B.get_center() + RIGHT * v_B)),
                        Write(collision_text),
                        run_time=0.05
                    )
                    self.wait(0.05)
                else:
                    break
            
            self.wait(0.5)