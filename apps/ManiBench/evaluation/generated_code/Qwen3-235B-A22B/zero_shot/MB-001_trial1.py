from manim import *
import numpy as np

class BlockCollisionAnimation(Scene):
    def construct(self):
        # Parameters
        mass_ratio_values = [1, 16, 100, 10000, 1000000, 100000000, 10000000000]
        mass_ratio_labels = ["1:1", "16:1", "100:1", "10,000:1", "1,000,000:1", "100,000,000:1", "10,000,000,000:1"]
        expected_collisions = [3, 13, 31, 314, 3141, 31415, 314159]  # Approximate digits of pi

        # Title
        title = Text("The Pi in Block Collisions", font_size=48)
        subtitle = Text("Elastic Collisions and the Emergence of π", font_size=36)
        subtitle.next_to(title, DOWN)
        self.play(Write(title))
        self.play(Write(subtitle))
        self.wait(2)
        self.play(FadeOut(title), FadeOut(subtitle))

        # Explanation text
        explanation = VGroup(
            Text("When a small block collides elastically with a large block"),
            Text("near a wall, the total number of collisions"),
            Text("reveals the digits of π!"),
            Text("Let's explore how...")
        ).arrange(DOWN, buff=0.3).scale(0.7)
        self.play(Write(explanation))
        self.wait(3)
        self.play(FadeOut(explanation))

        # Scene 1: Setup blocks
        for idx, (mass_ratio, label, expected) in enumerate(zip(mass_ratio_values, mass_ratio_labels, expected_collisions)):
            M = mass_ratio
            m = 1.0
            v0 = 2.0  # initial velocity of small block

            # Reset scene
            self.clear()

            # Title for this ratio
            ratio_title = Text(f"Mass Ratio: {label}", font_size=36).to_edge(UP)
            self.play(Write(ratio_title))

            # Create blocks
            block_A = Square(side_length=1, color=BLUE, fill_opacity=0.7).shift(RIGHT * 3)
            block_B = Square(side_length=0.5, color=RED, fill_opacity=0.7).shift(LEFT * 4)
            label_A = Text("A", font_size=24).move_to(block_A.get_center())
            label_B = Text("B", font_size=24).move_to(block_B.get_center())

            # Wall
            wall = Line(UP * 3, DOWN * 3, color=WHITE).shift(LEFT * 6)
            wall_label = Text("Wall", font_size=20).next_to(wall, DOWN)

            # Velocity vectors
            vA = 0.0
            vB = v0
            vec_A = Arrow(block_A.get_top() + LEFT * 0.3, block_A.get_top() + LEFT * 0.3 + UP * vA * 0.5,
                          buff=0, color=YELLOW, max_tip_length_to_length_ratio=0.2)
            vec_B = Arrow(block_B.get_top() + LEFT * 0.3, block_B.get_top() + LEFT * 0.3 + UP * vB * 0.5,
                          buff=0, color=YELLOW, max_tip_length_to_length_ratio=0.2)
            vel_label_A = MathTex("v_A", "=", "0", color=YELLOW, font_size=30).next_to(vec_A, UP, buff=0.1)
            vel_label_B = MathTex("v_B", "=", str(v0), color=YELLOW, font_size=30).next_to(vec_B, UP, buff=0.1)

            # Collision counter
            collision_count = 0
            counter_text = Integer(collision_count).scale(1.5)
            counter_label = Text("Collisions:", font_size=24).next_to(counter_text, LEFT)
            counter_group = VGroup(counter_label, counter_text).to_edge(DOWN, buff=1)

            # Conservation laws
            ke_eq = MathTex(r"\frac{1}{2}m_1v_1^2 + \frac{1}{2}m_2v_2^2 = E", font_size=30).to_edge(UR).shift(LEFT)
            mom_eq = MathTex(r"m_1v_1 + m_2v_2 = P", font_size=30).next_to(ke_eq, DOWN, aligned_edge=LEFT)

            # Phase space
            axes = Axes(
                x_range=[-4, 4, 1],
                y_range=[-4, 4, 1],
                x_length=5,
                y_length=5,
                axis_config={"include_tip": False, "include_numbers": False}
            ).to_corner(DR)
            x_label = axes.get_x_axis_label(r"\sqrt{m_1} v_1", edge=RIGHT, direction=DOWN * 2)
            y_label = axes.get_y_axis_label(r"\sqrt{m_2} v_2", edge=UP, direction=LEFT * 2)
            axes_labels = VGroup(x_label, y_label)

            # Initial phase point
            x_phase = np.sqrt(M) * vA
            y_phase = np.sqrt(m) * vB
            phase_dot = Dot(axes.c2p(x_phase, y_phase), color=GREEN, radius=0.08)
            phase_path = VMobject(color=GREEN)
            phase_path.set_points_as_corners([axes.c2p(x_phase, y_phase), axes.c2p(x_phase, y_phase)])

            # Momentum line
            slope = -np.sqrt(m / M)
            line = Line(
                axes.c2p(-4, -4 * slope),
                axes.c2p(4, 4 * slope),
                color=BLUE_A, stroke_width=2
            )
            mom_line_label = MathTex(r"m_1v_1 + m_2v_2 = P", color=BLUE_A, font_size=20).next_to(line, UR, buff=0.1)

            # Energy circle
            energy = 0.5 * m * vB**2
            radius = np.sqrt(2 * energy)
            circle = Circle(radius=radius * 0.8, color=RED_E, stroke_width=2).move_to(axes.c2p(0, 0))
            circle_label = MathTex(r"E = \frac{1}{2}m_1v_1^2 + \frac{1}{2}m_2v_2^2", color=RED_E, font_size=20)
            circle_label.next_to(circle, UP, buff=0.5)

            # Add all to scene
            self.add(wall, wall_label)
            self.add(block_A, block_B, label_A, label_B)
            self.add(vec_A, vec_B, vel_label_A, vel_label_B)
            self.add(counter_group)
            self.add(ke_eq, mom_eq)
            self.add(axes, axes_labels, phase_dot, phase_path, line, mom_line_label, circle, circle_label)

            # Animation loop
            dt = 0.05
            speed_factor = 0.5 if mass_ratio <= 100 else 0.1
            max_time = 50 if mass_ratio <= 100 else 100

            positions = [(block_A.get_center()[0], block_B.get_center()[0])]
            velocities = [(vA, vB)]
            collision_times = []

            for t in np.arange(0, max_time, dt):
                # Update positions
                new_xA = positions[-1][0] + vA * dt * speed_factor
                new_xB = positions[-1][1] + vB * dt * speed_factor

                # Wall collision (block B)
                if new_xB <= wall.get_right()[0] + 0.25 and vB < 0:
                    vB = -vB
                    collision_count += 1
                    self.play(
                        counter_text.animate.set_value(collision_count),
                        Flash(block_B, color=RED, flash_radius=0.6, line_length=0.3),
                        run_time=0.2
                    )
                    collision_times.append(t)

                # Block collision
                elif new_xB + 0.25 >= new_xA - 0.5 and vB > vA:
                    # Elastic collision formulas
                    vA_new = (2 * m * vB + (M - m) * vA) / (M + m)
                    vB_new = ((M - m) * vB + 2 * M * vA) / (M + m)
                    vA, vB = vA_new, vB_new
                    collision_count += 1
                    self.play(
                        counter_text.animate.set_value(collision_count),
                        Flash(block_A, block_B, color=PURPLE, flash_radius=0.8, line_length=0.4),
                        run_time=0.2
                    )
                    collision_times.append(t)

                # Update positions
                block_A.shift(RIGHT * vA * dt * speed_factor)
                block_B.shift(RIGHT * vB * dt * speed_factor)
                label_A.move_to(block_A.get_center())
                label_B.move_to(block_B.get_center())

                # Update velocity vectors
                new_vec_A = Arrow(
                    block_A.get_top() + LEFT * 0.3,
                    block_A.get_top() + LEFT * 0.3 + UP * max(0, vA) * 0.5,
                    buff=0, color=YELLOW, max_tip_length_to_length_ratio=0.2
                )
                new_vec_B = Arrow(
                    block_B.get_top() + LEFT * 0.3,
                    block_B.get_top() + LEFT * 0.3 + UP * max(0, vB) * 0.5,
                    buff=0, color=YELLOW, max_tip_length_to_length_ratio=0.2
                )
                self.remove(vec_A, vec_B)
                vec_A, vec_B = new_vec_A, new_vec_B
                self.add(vec_A, vec_B)

                # Update velocity labels
                self.remove(vel_label_A, vel_label_B)
                vel_label_A = MathTex("v_A", "=", f"{vA:.2f}", color=YELLOW, font_size=30).next_to(vec_A, UP, buff=0.1)
                vel_label_B = MathTex("v_B", "=", f"{vB:.2f}", color=YELLOW, font_size=30).next_to(vec_B, UP, buff=0.1)
                self.add(vel_label_A, vel_label_B)

                # Update phase space
                x_phase = np.sqrt(M) * vA
                y_phase = np.sqrt(m) * vB
                new_phase_dot = Dot(axes.c2p(x_phase, y_phase), color=GREEN, radius=0.08)
                phase_path.add_points_as_corners([axes.c2p(x_phase, y_phase)])
                self.remove(phase_dot)
                phase_dot = new_phase_dot
                self.add(phase_dot, phase_path)

                # Stop condition: block B moving away and no more collisions likely
                if vB > 0 and vA > vB and new_xB > new_xA:
                    break

                self.wait(dt * 0.1)

            # Final state
            final_text = Text(f"Final: # Collisions = {collision_count}", font_size=36, color=TEAL)
            final_text.to_edge(DOWN)
            self.play(Write(final_text))
            self.wait(2)

            # Phase space explanation
            if idx == 2:  # Only for 100:1
                self.play(FadeOut(*[mob for mob in self.mobjects if mob not in [ratio_title]]))
                explanation_pi = VGroup(
                    Text("The number of collisions approximates the digits of π!"),
                    MathTex(r"\text{For } m/M = 100,\ \text{collisions} = 31 \approx \pi \times 10"),
                    MathTex(r"\text{For } m/M = 10000,\ \text{collisions} = 314 \approx \pi \times 100"),
                    Text("This arises from the geometry of phase space..."),
                ).arrange(DOWN, buff=0.5).scale(0.7)
                self.play(Write(explanation_pi))
                self.wait(5)
                self.play(FadeOut(explanation_pi))

        # Final summary
        self.clear()
        summary = VGroup(
            Text("Why does π appear?", font_size=36, color=YELLOW),
            MathTex(r"\theta = \arctan\left(\sqrt{\frac{m}{M}}\right)", font_size=36),
            MathTex(r"\text{Number of collisions} \approx \frac{\pi}{\theta}", font_size=36),
            Text("Each collision reflects the state point", font_size=30),
            Text("across the momentum line in phase space.", font_size=30),
            Text("The total angle swept gives π!", color=ORANGE, font_size=36)
        ).arrange(DOWN, buff=0.5)
        self.play(Write(summary))
        self.wait(5)

        # End card
        end_card = VGroup(
            Text("The Magic of Mathematics", font_size=48, color=GOLD),
            Text("Elastic Collisions → Digits of π", font_size=36),
            Text("Created with Manim", font_size=24)
        ).arrange(DOWN, buff=0.7)
        self.play(FadeIn(end_card))
        self.wait(3)