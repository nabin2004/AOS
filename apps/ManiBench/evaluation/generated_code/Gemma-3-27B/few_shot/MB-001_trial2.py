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
        
        # Initial setup
        block_A = Rectangle(width=1, height=0.5, color=RED)
        block_B = Rectangle(width=1, height=0.5, color=BLUE)
        block_A.move_to([x_A, 0, 0])
        block_B.move_to([x_B, 0, 0])

        v_A_arrow = Arrow(block_A.get_center(), block_A.get_center() + RIGHT * 0, color=RED)
        v_B_arrow = Arrow(block_B.get_center(), block_B.get_center() + RIGHT * v0, color=BLUE)

        collision_count = 0
        collision_text = Text("# Collisions = 0").to_corner(UL)

        energy_text = MathTex(r"\frac{1}{2}m_1v_1^2 + \frac{1}{2}m_2v_2^2 = E").to_corner(UR)
        momentum_text = MathTex(r"m_1v_1 + m_2v_2 = P").next_to(energy_text, DOWN)

        self.play(Create(block_A), Create(block_B), Create(v_A_arrow), Create(v_B_arrow), Write(collision_text), Write(energy_text), Write(momentum_text))
        self.wait(1)

        # Simulation loop
        v_A = 0
        v_B = v0
        positions = []
        
        for i in range(n_max):
            # Collision detection
            if block_B.get_center()[0] >= block_A.get_center()[0]:
                # Elastic collision formulas
                v_A_new = (v_B * (m / M))
                v_B_new = (v_A * (M / m))
                
                # Update velocities and positions
                v_A = v_A_new
                v_B = v_B_new
                
                # Update arrows
                v_A_arrow.set_end(block_A.get_center() + RIGHT * v_A)
                v_B_arrow.set_end(block_B.get_center() + RIGHT * v_B)
                
                # Increment collision counter
                collision_count += 1
                collision_text.set_text(f"# Collisions = {collision_count}")
                
                # Move blocks
                block_A.move_to([block_A.get_center()[0] + v_A, 0, 0])
                block_B.move_to([block_B.get_center()[0] + v_B, 0, 0])
                
                self.play(
                    UpdateFromFunc(v_A_arrow, lambda x: block_A.get_center() + RIGHT * v_A),
                    UpdateFromFunc(v_B_arrow, lambda x: block_B.get_center() + RIGHT * v_B),
                    UpdateFromFunc(block_A, lambda x: [block_A.get_center()[0] + v_A, 0, 0]),
                    UpdateFromFunc(block_B, lambda x: [block_B.get_center()[0] + v_B, 0, 0]),
                    Write(collision_text),
                    run_time=0.1
                )
                
                positions.append((block_A.get_center()[0], block_B.get_center()[0]))
                
                if v_B <= 0 and v_A >= 0:
                    break
        
        # Final state
        self.wait(1)
        final_text = Text("Collision Complete", font_size=36, color=GREEN).to_edge(DOWN)
        self.play(Write(final_text))
        self.wait(2)

        # Phase space
        self.clear()
        axes = Axes(x_range=[-5, 5], y_range=[-5, 5], axis_config={"include_numbers": True})
        axes.add_coordinate_labels()
        
        circle = Circle(radius=np.sqrt(v0**2), color=GREEN)
        
        line = Line(axes.c2p(-5, -v0), axes.c2p(5, v0), color=YELLOW)
        
        self.play(Create(axes), Create(circle), Create(line))
        self.wait(2)
        
        # Mass ratio demonstration
        self.clear()
        ratios = [1, 16, 100, 10000, 1000000]
        
        for ratio in ratios:
            m = M / ratio
            v0 = 5
            collision_count = 0
            
            block_A = Rectangle(width=1, height=0.5, color=RED)
            block_B = Rectangle(width=1, height=0.5, color=BLUE)
            block_A.move_to([x_A, 0, 0])
            block_B.move_to([x_B, 0, 0])
            
            v_A_arrow = Arrow(block_A.get_center(), block_A.get_center() + RIGHT * 0, color=RED)
            v_B_arrow = Arrow(block_B.get_center(), block_B.get_center() + RIGHT * v0, color=BLUE)
            
            collision_text = Text(f"# Collisions (m/M = {ratio}) = 0").to_corner(UL)
            
            self.play(Create(block_A), Create(block_B), Create(v_A_arrow), Create(v_B_arrow), Write(collision_text))
            self.wait(0.5)
            
            v_A = 0
            v_B = v0
            
            for i in range(n_max):
                if block_B.get_center()[0] >= block_A.get_center()[0]:
                    v_A_new = (v_B * (m / M))
                    v_B_new = (v_A * (M / m))
                    
                    v_A = v_A_new
                    v_B = v_B_new
                    
                    v_A_arrow.set_end(block_A.get_center() + RIGHT * v_A)
                    v_B_arrow.set_end(block_B.get_center() + RIGHT * v_B)
                    
                    collision_count += 1
                    collision_text.set_text(f"# Collisions (m/M = {ratio}) = {collision_count}")
                    
                    block_A.move_to([block_A.get_center()[0] + v_A, 0, 0])
                    block_B.move_to([block_B.get_center()[0] + v_B, 0, 0])
                    
                    self.play(
                        UpdateFromFunc(v_A_arrow, lambda x: block_A.get_center() + RIGHT * v_A),
                        UpdateFromFunc(v_B_arrow, lambda x: block_B.get_center() + RIGHT * v_B),
                        UpdateFromFunc(block_A, lambda x: [block_A.get_center()[0] + v_A, 0, 0]),
                        UpdateFromFunc(block_B, lambda x: [block_B.get_center()[0] + v_B, 0, 0]),
                        Write(collision_text),
                        run_time=0.05
                    )
                    
                    if v_B <= 0 and v_A >= 0:
                        break
            
            self.wait(0.5)
            self.clear()