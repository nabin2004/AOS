from manim import *
import numpy as np

class BlockCollisionPi(Scene):
    def construct(self):
        # Configuration
        mass_ratio_exp = 4  # 10^4 -> 314 collisions (manageable for animation)
        M = 100**mass_ratio_exp
        m = 1.0
        ratio = m / M
        
        # Initial conditions
        v_A = 0.0
        v_B = 1.0 # Normalized initial velocity
        pos_A = 2.0
        pos_B = -2.0
        
        # Physics constants for visualization scaling
        scale_factor = 0.5 # Scale positions for screen
        time_step = 0.01
        
        # Colors
        color_A = BLUE
        color_B = GREEN
        color_text = WHITE
        
        # --- Mobjects Setup ---
        
        # Blocks
        block_A = Square(side_length=1.0, color=color_A, fill_opacity=0.5).move_to(LEFT * 3 + DOWN * 2)
        block_B = Square(side_length=0.5, color=color_B, fill_opacity=0.5).move_to(LEFT * 6 + DOWN * 2)
        
        # Labels
        label_A = Text(f"Mass M", font_size=24).next_to(block_A, UP, buff=0.1)
        label_B = Text(f"Mass m", font_size=24).next_to(block_B, UP, buff=0.1)
        
        # Velocity Vectors
        vec_A = Arrow(block_A.get_center(), block_A.get_center(), color=color_A, buff=0)
        vec_B = Arrow(block_B.get_center(), block_B.get_center(), color=color_B, buff=0)
        vec_group = VGroup(vec_A, vec_B)
        
        # Collision Counter
        counter_text = Text("Collisions: 0", font_size=36).to_edge(UP)
        collision_count = 0
        
        # Equations
        ke_eq = MathTex(r"\frac{1}{2}Mv_A^2 + \frac{1}{2}mv_B^2 = E", font_size=30).to_edge(RIGHT).shift(UP * 2)
        mom_eq = MathTex(r"Mv_A + mv_B = P", font_size=30).next_to(ke_eq, DOWN, buff=0.5)
        
        # Phase Space Plane (Hidden initially)
        axes = Axes(
            x_range=[-2, 2, 1],
            y_range=[-2, 2, 1],
            axis_config={"include_tip": True, "include_numbers": False},
            x_axis_config={"label_direction": DOWN},
            y_axis_config={"label_direction": LEFT}
        ).scale(0.8).to_edge(RIGHT).shift(DOWN * 1)
        
        x_label = axes.get_x_axis_label(r"x = \sqrt{M}v_A")
        y_label = axes.get_y_axis_label(r"y = \sqrt{m}v_B")
        phase_labels = VGroup(x_label, y_label)
        
        energy_circle = Circle(radius=1.5, color=YELLOW, stroke_opacity=0.3).move_to(axes.get_origin())
        momentum_line = Line(axes.c2p(-2, 2), axes.c2p(2, -2), color=RED, stroke_opacity=0.5)
        
        state_dot = Dot(color=WHITE).move_to(axes.get_origin())
        trace = VMobject(color=WHITE, stroke_width=2)
        trace.set_points_as_corners([axes.get_origin(), axes.get_origin()])
        
        phase_group = VGroup(axes, phase_labels, energy_circle, momentum_line, state_dot, trace)
        phase_group.scale(0.6).next_to(mom_eq, DOWN, buff=0.5)
        
        # Explanation Text
        explanation = Text("Phase Space: Elastic Collisions trace a circle", font_size=24).next_to(phase_group, UP, buff=0.2)
        
        # --- Animation Sequence ---
        
        # 1. Intro
        self.play(Create(block_A), Create(block_B), Write(label_A), Write(label_B))
        self.play(Write(counter_text))
        self.wait(0.5)
        
        # 2. Show Equations
        self.play(Write(ke_eq), Write(mom_eq))
        self.wait(1)
        
        # 3. Start Simulation Loop
        # We simulate physics in python and animate the result
        # To make it viewable, we speed up time or skip frames for high ratios
        # For this demo, we run a simplified version that shows the mechanism
        
        running = True
        total_collisions = 0
        
        # Helper to update visuals
        def update_visuals():
            nonlocal collision_count
            counter_text.become(Text(f"Collisions: {collision_count}", font_size=36).to_edge(UP))
            
            # Update positions
            block_A.move_to(LEFT * 3 + RIGHT * (pos_A * scale_factor) + DOWN * 2)
            block_B.move_to(LEFT * 3 + RIGHT * (pos_B * scale_factor) + DOWN * 2)
            
            # Update vectors (scaled for visibility)
            vec_scale = 2.0
            vec_A.become(Arrow(block_A.get_center(), block_A.get_center() + RIGHT * v_A * vec_scale, color=color_A, buff=0))
            vec_B.become(Arrow(block_B.get_center(), block_B.get_center() + RIGHT * v_B * vec_scale, color=color_B, buff=0))
            
            # Update Phase Space
            # Map v_A, v_B to phase space coordinates
            # Normalize by initial energy radius for display
            E_total = 0.5 * m * (1.0)**2 # Initial energy (v_B=1)
            R_phase = np.sqrt(2 * E_total) # Radius in phase space if axes were unscaled
            
            # Coordinate transformation for display on our specific axes
            # x = sqrt(M)*v_A, y = sqrt(m)*v_B. 
            # We need to normalize these to fit the drawn circle of radius 1.5
            # Max x = sqrt(M)*0 = 0? No, max velocity transfers.
            # Max v_A approx 2*v_B_initial * m/M? No.
            # Let's just map the current state to the circle visually.
            
            # Actual Phase Coords
            px = np.sqrt(M) * v_A
            py = np.sqrt(m) * v_B
            
            # Scale to fit the drawn circle (radius 1.5)
            # Initial state: v_A=0, v_B=1 -> px=0, py=sqrt(m). 
            # We want initial point to be on the circle.
            # So scale factor k = 1.5 / sqrt(m)
            k = 1.5 / np.sqrt(m)
            
            target_point = axes.c2p(px * k, py * k)
            state_dot.move_to(target_point)
            
            # Add to trace
            new_trace = VMobject(color=WHITE, stroke_width=2)
            new_trace.set_points_smoothly([*trace.get_points(), target_point])
            trace.become(new_trace)

        # Initial draw
        update_visuals()
        self.add(vec_group)
        
        # Show Phase Space Concept briefly before full sim
        self.play(FadeIn(phase_group), Write(explanation))
        self.wait(1)
        
        # Simulation Loop (Simplified for animation performance)
        # In a real rigorous sim, we'd calculate exact collision times.
        # Here we step forward. If ratio is huge, we cannot animate every frame.
        # We will animate the first few, then fast forward, then show the result.
        
        max_frames_to_animate = 200 # Limit for video length
        frame_count = 0
        
        # Pre-calculate all collisions to know the end state
        # This is the "Clack" algorithm logic
        sim_vA = 0.0
        sim_vB = 1.0
        sim_posA = 2.0
        sim_posB = -2.0
        sim_collisions = 0
        sim_history = [] # Store states for animation
        
        # We simulate the physics purely to get the count and key frames
        # Since M >> m, B bounces many times between A and Wall (at x=0 effectively? No, problem says A and B)
        # Wait, the standard Pi problem involves a wall at x=0. 
        # The prompt says: "Block A at x=10, Block B at x=0... sliding on frictionless surface".
        # Usually, the Pi digit property requires a WALL for B to bounce off.
        # Without a wall, B hits A, transfers momentum, and they separate. Only 1 collision.
        # I must assume there is a wall at x = -infinity or specifically at x=0 where B starts?
        # "Block B approaches from the left". If no wall, it never bounces back to hit A again.
        # ASSUMPTION: There is an elastic wall at x = -5 (left of start).
        
        wall_pos = -5.0
        
        # Re-simulate with wall
        sim_posA = 2.0
        sim_posB = -2.0
        sim_vA = 0.0
        sim_vB = 1.0 # Moving right
        sim_collisions = 0
        
        # Safety break
        while sim_vB < sim_vA or sim_vB < 0: # Condition: B must be slower than A and moving right to stop
            # Actually condition is: v_A >= v_B and v_B >= 0 (if wall exists)
            # But with wall, B becomes negative, hits wall, becomes positive.
            # Stop when v_A > v_B > 0.
            
            if sim_collisions > 100000: break # Safety
            
            # Move until next event
            # Event 1: B hits A (pos_B + size/2 >= pos_A - size/2)
            # Event 2: B hits Wall (pos_B - size/2 <= wall_pos)
            
            # Simplified point masses for logic
            if sim_vB > sim_vA:
                # Will collide
                dt = (sim_posA - sim_posB) / (sim_vB - sim_vA) - 0.01 # small buffer
                if dt < 0: dt = 0.01
                sim_posA += sim_vA * dt
                sim_posB += sim_vB * dt
                
                # Collision A-B
                # Elastic formulas
                new_vA = ((M - m) * sim_vA + 2 * m * sim_vB) / (M + m)
                new_vB = ((m - M) * sim_vB + 2 * M * sim_vA) / (M + m)
                sim_vA, sim_vB = new_vA, new_vB
                sim_collisions += 1
                
                # Store state
                sim_history.append((sim_posA, sim_posB, sim_vA, sim_vB, sim_collisions))
                
            elif sim_vB < 0:
                # Will hit wall
                dt = (sim_posB - wall_pos) / (-sim_vB) - 0.01
                if dt < 0: dt = 0.01
                sim_posA += sim_vA * dt
                sim_posB += sim_vB * dt
                
                # Collision B-Wall
                sim_vB = -sim_vB
                sim_collisions += 1
                sim_history.append((sim_posA, sim_posB, sim_vA, sim_vB, sim_collisions))
            else:
                # v_A >= v_B and v_B >= 0 -> Done
                break
        
        total_collisions = sim_collisions
        
        # Now animate the stored history or a subset
        self.play(RemoveTextLetterFade(explanation))
        
        # Animate step by step (subsampled if too many)
        step = max(1, len(sim_history) // 100) # Show max 100 steps
        
        for i in range(0, len(sim_history), step):
            pA, pB, vA, vB, count = sim_history[i]
            
            # Update globals for helper
            pos_A, pos_B, v_A, v_B, collision_count = pA, pB, vA, vB, count
            
            update_visuals()
            
            # Only render if significant change or early/late
            if i < 10 or i > len(sim_history) - 10 or i % (step*5) == 0:
                self.wait(0.05) # Fast wait
        
        # Force final state update
        pos_A, pos_B, v_A, v_B, collision_count = sim_history[-1]
        update_visuals()
        self.wait(0.5)
        
        # 4. Final Count Display
        final_count_text = Text(f"# Collisions = {collision_count}", font_size=48, color=YELLOW).to_edge(DOWN)
        self.play(Write(final_count_text))
        
        # 5. Pi Connection
        pi_val = str(np.pi)[0:mass_ratio_exp+2] # e.g. 3.14
        pi_text = Text(f"Digits of π: {pi_val}", font_size=36, color=YELLOW).next_to(final_count_text, UP)
        self.play(Write(pi_text))
        
        # 6. Arc Angle Argument Visualization
        # Show the angle theta in phase space
        theta = np.arctan(np.sqrt(m/M))
        angle_arc = Arc(radius=0.5, start_angle=0, angle=theta, color=RED).move_to(axes.get_origin(), aligned_edge=LEFT)
        angle_label = MathTex(r"\theta = \arctan(\sqrt{m/M})", font_size=24).next_to(angle_arc, RIGHT, buff=0.1)
        
        self.play(Create(angle_arc), Write(angle_label))
        
        bounce_angle_text = Text(f"Each bounce = 2θ", font_size=24).to_edge(DOWN).shift(UP*0.5)
        total_angle_text = Text(f"Total Angle ≈ π", font_size=24).next_to(bounce_angle_text, UP)
        formula_text = MathTex(r"N \cdot 2\theta \approx \pi \implies N \approx \frac{\pi}{2\theta} \approx \frac{\pi}{2\sqrt{m/M}}", font_size=24).next_to(total_angle_text, UP)
        
        self.play(Write(bounce_angle_text))
        self.wait(1)
        self.play(Write(total_angle_text), Write(formula_text))
        
        self.wait(2)

# Note: To see different ratios, change `mass_ratio_exp` at the top.
# 0 -> 1:1 (3 collisions)
# 1 -> 100:1 (31 collisions)
# 2 -> 10000:1 (314 collisions)
# Higher values require skipping more frames in the loop to render in reasonable time.