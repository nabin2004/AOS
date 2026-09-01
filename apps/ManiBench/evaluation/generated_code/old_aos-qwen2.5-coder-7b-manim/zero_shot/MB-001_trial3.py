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
        mom_slope = -np.sqrt(m/M)
        mom_line = Line(
            start=x_axis.n2p([0, np.sqrt(M)]),
            end=y_axis.n2p([np.sqrt(M)/mom_slope, 0]),
            color=ORANGE,
            stroke_width=2
        )
        
        # Arc angle argument
        theta = np.arctan(np.sqrt(m/M))
        arc = Arc(
            radius=1,
            start_angle=-theta,
            angle=2*theta,
            color=PINK
        ).move_to(ORIGIN)
        
        # Animation sequence
        self.play(FadeIn(block_a), FadeIn(block_b))
        self.play(GrowArrow(arrow_a), GrowArrow(arrow_b))
        
        # Collision loop
        n_collisions = 0
        while True:
            # Update velocities
            va = M * (M - m) / (M + m) * v0
            vb = 2 * m * v0 / (M + m)
            
            # Move blocks
            block_a.animate.shift(LEFT * (va - v0) * dt).run_time=dt
            block_b.animate.shift(RIGHT * (vb - v0) * dt).run_time=dt
            
            # Update arrows
            arrow_a.become(Arrow(start=block_a.get_top(), end=block_a.get_top() + UP*0.5, buff=0, color=YELLOW))
            arrow_b.become(Arrow(start=block_b.get_bottom(), end=block_b.get_bottom() + DOWN*0.5, buff=0, color=YELLOW))
            
            # Check for collision
            if abs(block_a.get_x() - block_b.get_x()) < 0.5:
                # Increment counter
                n_collisions += 1
                collision_counter.set_value(n_collisions)
                
                # Update equations
                ke_eq.next_to(collision_counter, DOWN)
                mom_eq.next_to(ke_eq, DOWN)
                
                # Update phase space coordinates
                x_point = Dot(point=[np.sqrt(M)*va, 0, 0], color=WHITE)
                y_point = Dot(point=[0, np.sqrt(m)*vb, 0], color=WHITE)
                
                # Update momentum line
                new_mom_line = Line(
                    start=x_axis.n2p([0, np.sqrt(M)]),
                    end=y_axis.n2p([np.sqrt(M)/mom_slope, 0]),
                    color=ORANGE,
                    stroke_width=2
                )
                
                # Update arc angle
                new_theta = np.arctan(np.sqrt(m/M))
                new_arc = Arc(
                    radius=1,
                    start_angle=-new_theta,
                    angle=2*new_theta,
                    color=PINK
                ).move_to(ORIGIN)
                
                # Play update animations
                self.play(
                    block_a.animate.shift(LEFT * (va - v0)),
                    block_b.animate.shift(RIGHT * (vb - v0)),
                    Transform(arrow_a, arrow_a.copy()),
                    Transform(arrow_b, arrow_b.copy()),
                    Write(ke_eq),
                    Write(mom_eq),
                    FadeOut(x_point), FadeOut(y_point),
                    FadeIn(x_point), FadeIn(y_point),
                    ReplacementTransform(mom_line, new_mom_line),
                    ReplacementTransform(arc, new_arc)
                )
                
                # Check for end condition
                if va <= vb:
                    break
                
                # Prepare next iteration
                v0 = va
                block_a.move_to(RIGHT * 10)
                block_b.move_to(LEFT * 5)
                arrow_a.become(Arrow(start=block_a.get_top(), end=block_a.get_top() + UP*0.5, buff=0, color=YELLOW))
                arrow_b.become(Arrow(start=block_b.get_bottom(), end=block_b.get_bottom() + DOWN*0.5, buff=0, color=YELLOW))
        
        # Final state
        final_text = Text(f"# Collisions = {n_collisions}", font_size=24).to_edge(UP)
        self.play(Transform(collision_counter, final_text))
        
        # Slow motion replay
        self.play(
            block_a.animate.shift(LEFT * (va - v0) * 10),
            block_b.animate.shift(RIGHT * (vb - v0) * 10),
            run_time=10,
            rate_func=lambda t: t**2
        )