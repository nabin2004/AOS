from manim import *

class ElasticCollision(Scene):
    def construct(self):
        # Parameters
        M = 1.0
        m = 100.0
        v0 = 1.0
        
        # Create blocks
        block_a = Square(side_length=0.5, color=BLUE, fill_opacity=0.8)
        block_b = Square(side_length=0.5, color=RED, fill_opacity=0.8)
        
        # Initial positions
        block_a.move_to(RIGHT * 10)
        block_b.move_to(LEFT * 5)
        
        # Velocity vectors
        arrow_a = Arrow(start=block_a.get_top(), end=block_a.get_top() + UP*0.5, buff=0, color=YELLOW)
        arrow_b = Arrow(start=block_b.get_bottom(), end=block_b.get_bottom() + DOWN*0.5, buff=0, color=YELLOW)
        
        # Collision counter
        collision_counter = Integer(0).to_edge(UP)
        
        # Conservation equations
        ke_eq = MathTex(r"\frac{1}{2}mv_1^2 + \frac{1}{2}mv_2^2 = E").next_to(collision_counter, DOWN)
        mom_eq = MathTex(r"mv_1 + mv_2 = P").next_to(ke_eq, DOWN)
        
        # Phase space coordinates
        x_axis = NumberLine(x_range=[0, 10], length=6, color=GREEN).to_edge(DOWN)
        y_axis = NumberLine(x_range=[0, 10], length=6, color=GREEN).rotate(PI/2).to_edge(DOWN)
        axes_group = VGroup(x_axis, y_axis)
        
        # Energy circle
        energy_circle = Circle(radius=np.sqrt(m), color=PURPLE).move_to(ORIGIN)
        
        # Momentum line
        momentum_slope = -np.sqrt(m/M)
        momentum_line = Line(
            start=x_axis.n2p([0, np.sqrt(M)]),
            end=y_axis.n2p([np.sqrt(m), 0]),
            color=ORANGE,
            stroke_width=2
        )
        
        # Arc angle argument
        theta = np.arctan(np.sqrt(m/M))
        arc = Arc(
            radius=1,
            start_angle=-theta,
            angle=2*theta,
            color=GREY
        ).move_to(ORIGIN)
        
        # Animation sequence
        self.play(FadeIn(block_a), FadeIn(block_b))
        self.play(GrowArrow(arrow_a), GrowArrow(arrow_b))
        
        # Collision loop
        n_collisions = 0
        while True:
            # Update velocities using elastic collision formula
            v1_new = (M-m)/(M+m)*v0
            v2_new = 2*M/(M+m)*v0
            
            # Move blocks
            block_a.animate.shift(v1_new * RIGHT * dt).run_time=dt
            block_b.animate.shift(v2_new * LEFT * dt).run_time=dt
            
            # Update arrows
            arrow_a.become(Arrow(start=block_a.get_top(), end=block_a.get_top() + UP*0.5, buff=0, color=YELLOW))
            arrow_b.become(Arrow(start=block_b.get_bottom(), end=block_b.get_bottom() + DOWN*0.5, buff=0, color=YELLOW))
            
            # Check for collision
            if abs(block_a.get_center()[0] - block_b.get_center()[0]) < 0.5:
                # Increment collision counter
                n_collisions += 1
                collision_counter.set_value(n_collisions)
                
                # Update velocities
                v0 = -v1_new
                
                # Trace phase space point
                x_val = np.sqrt(M) * v1_new
                y_val = np.sqrt(m) * v2_new
                dot = Dot(point=axes_group.c2p(x_val, y_val), color=WHITE)
                self.add(dot)
                
                # Add to group for cleanup later
                self.mobjects.append(dot)
                
                # Check for end condition
                if abs(v1_new) <= abs(v2_new):
                    break
                    
            else:
                pass
            
            # Wait for next frame
            self.wait(dt)
        
        # Final state
        final_text = Text(f"# Collisions = {n_collisions}", font_size=24).to_edge(UP)
        self.play(Transform(collision_counter, final_text))
        
        # Show conservation equations
        self.play(Write(ke_eq), Write(mom_eq))
        
        # Show phase space plot
        self.play(Create(axes_group), Create(energy_circle), Create(momentum_line))
        
        # Show arc angle argument
        self.play(Create(arc))
        
        # Slow motion replay
        self.play(
            block_a.animate.shift(-v1_new * RIGHT * 10).set_color(GREEN),
            block_b.animate.shift(-v2_new * LEFT * 10).set_color(GREEN),
            run_time=10,
            rate_func=lambda t: t**2
        )
        
        # Cleanup
        self.remove(*self.mobjects)