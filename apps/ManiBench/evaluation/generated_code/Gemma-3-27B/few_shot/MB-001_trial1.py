from manim import *

class ElasticCollision(Scene):
    def construct(self):
        # Parameters
        M = 1  # Mass of block A
        m = 0.01  # Mass of block B (m/M = 100)
        v0 = 5  # Initial velocity of block B
        x_A = 10
        x_B = 0
        n_max = 100  # Maximum number of collisions to simulate
        
        # Blocks
        block_A = Rectangle(width=1, height=0.5, color=RED)
        block_B = Rectangle(width=1, height=0.5, color=BLUE)
        block_A.move_to([x_A, 0, 0])
        block_B.move_to([x_B, 0, 0])

        # Velocity vectors
        v_A_arrow = Arrow(block_A.get_center(), block_A.get_center() + RIGHT * 2, buff=0.1, color=RED)
        v_B_arrow = Arrow(block_B.get_center(), block_B.get_center() + RIGHT * 2, buff=0.1, color=BLUE)
        v_A_arrow.set_stroke(width=2)
        v_B_arrow.set_stroke(width=2)
        
        # Collision counter
        collision_count = 0
        collision_text = Text("Collisions = 0").to_corner(UL)

        # Axes for phase space
        phase_space_axes = Axes(x_range=[-5, 5], y_range=[-5, 5], axis_config={"include_numbers": True})
        phase_space_axes.add_coordinate_labels()
        phase_space_axes.set_axis_orientations(UP, RIGHT)
        
        # Conservation equations
        ke_eq = MathTex("½m_1v_1^2 + ½m_2v_2^2 = E").to_corner(UR)
        momentum_eq = MathTex("m_1v_1 + m_2v_2 = P").next_to(ke_eq, DOWN)

        # Initial state
        self.play(Create(block_A), Create(block_B), Create(v_A_arrow.copy().move_to(block_A.get_center())), Create(v_B_arrow.copy().move_to(block_B.get_center())), Write(collision_text), Write(ke_eq), Write(momentum_eq))
        self.wait(1)

        # Simulation loop
        v_A = 0
        v_B = v0
        
        for i in range(n_max):
            # Collision detection
            if block_B.get_center()[0] >= block_A.get_center()[0]:
                # Elastic collision formulas
                v_A_new = (v_B - v_A) * (m / M) + v_A
                v_B_new = (v_A - v_B) * (M / m) + v_B

                # Update velocities and positions
                v_A = v_A_new
                v_B = v_B_new
                block_A.move_to([block_A.get_center()[0] + v_A, 0, 0])
                block_B.move_to([block_B.get_center()[0] + v_B, 0, 0])

                # Update collision counter
                collision_count += 1
                collision_text.set_text(f"Collisions = {collision_count}")

                # Update velocity vectors
                self.play(
                    v_A_arrow.animate.set_end(block_A.get_center() + RIGHT * v_A),
                    v_B_arrow.animate.set_end(block_B.get_center() + RIGHT * v_B),
                    Write(collision_text),
                    run_time=0.2
                )
                self.wait(0.1)
            
            if v_B <= 0 and v_A <= 0:
                break

        # Final state
        self.play(FadeOut(v_A_arrow), FadeOut(v_B_arrow))
        self.wait(1)

        # Phase space
        self.play(Create(phase_space_axes))
        
        # Ellipse/Circle
        energy = 0.5 * m * v0**2
        ellipse = ParametricFunction(lambda t: [np.sqrt(m) * np.cos(t), np.sqrt(m) * np.sin(t)], t_range=[0, 2 * PI], color=GREEN)
        self.play(Create(ellipse))
        
        # Momentum line
        momentum = m * v0
        line = FunctionGraph(lambda x: (momentum - m * x) / M, x_range=[-5, 5], color=YELLOW)
        self.play(Create(line))
        
        # Arc angle
        theta = np.arctan(np.sqrt(m / M))
        arc_angle_text = MathTex("2\\theta = 2 \\arctan(\\sqrt{\\frac{m}{M}})")
        self.play(Write(arc_angle_text.next_to(phase_space_axes, UP)))
        
        # Mass ratio demonstration
        self.clear()
        
        ratios = [1, 16, 100, 10000, 1000000]
        
        for ratio in ratios:
            m = M / ratio
            collision_count = 0
            v_A = 0
            v_B = v0
            
            block_A = Rectangle(width=1, height=0.5, color=RED)
            block_B = Rectangle(width=1, height=0.5, color=BLUE)
            block_A.move_to([x_A, 0, 0])
            block_B.move_to([x_B, 0, 0])
            
            self.play(Create(block_A), Create(block_B))
            
            for i in range(n_max):
                if block_B.get_center()[0] >= block_A.get_center()[0]:
                    v_A_new = (v_B - v_A) * (m / M) + v_A
                    v_B_new = (v_A - v_B) * (M / m) + v_B
                    v_A = v_A_new
                    v_B = v_B_new
                    block_A.move_to([block_A.get_center()[0] + v_A, 0, 0])
                    block_B.move_to([block_B.get_center()[0] + v_B, 0, 0])
                    collision_count += 1
            
            ratio_text = MathTex(f"m/M = {ratio} \\Rightarrow Collisions = {collision_count}").to_edge(UL)
            self.play(Write(ratio_text))
            self.wait(1)
            self.clear()