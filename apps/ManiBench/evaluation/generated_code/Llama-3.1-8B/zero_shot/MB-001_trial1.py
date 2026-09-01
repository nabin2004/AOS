from manim import *

class CollisionAnimation(Scene):
    def construct(self):
        # Define constants
        M = 1  # mass of block A
        m = 0.01  # mass of block B
        v0 = 1  # initial velocity of block B
        g = 0  # acceleration due to gravity (not used)

        # Create blocks
        block_A = Rectangle(width=2, height=1, fill_color=BLUE, color=BLUE)
        block_A.to_edge(LEFT)
        block_B = Rectangle(width=2, height=1, fill_color=RED, color=RED)
        block_B.next_to(block_A, RIGHT)

        # Create velocity vectors
        v_A = Arrow(start=block_A.get_center(), end=block_A.get_center() + RIGHT * v0, color=GREEN)
        v_B = Arrow(start=block_B.get_center(), end=block_B.get_center() + RIGHT * v0, color=GREEN)

        # Create collision counter
        collision_counter = Tex("Collisions = 0").next_to(block_A, DOWN)

        # Create velocity updates
        velocity_updates = VGroup()
        for i in range(31):
            velocity_update = Tex(f"v_A = {v0 * (1 - 2 * m / (M + m))}").next_to(block_A, DOWN)
            velocity_updates.add(velocity_update)

        # Create conservation of kinetic energy equation
        kinetic_energy_equation = Tex(r"½m₁v₁² + ½m₂v₂² = E").next_to(block_A, DOWN)

        # Create conservation of momentum equation
        momentum_equation = Tex(r"m₁v₁ + m₂v₂ = P").next_to(block_A, DOWN)

        # Create phase-space coordinate plane
        phase_space_plane = NumberPlane(x_range=[0, 10], y_range=[0, 10])

        # Create state point
        state_point = Dot().move_to(phase_space_plane.c2p(1, 1))

        # Create ellipse
        ellipse = Ellipse(width=10, height=10, color=YELLOW)

        # Create momentum conservation line
        momentum_line = Line(start=phase_space_plane.c2p(0, 0), end=phase_space_plane.c2p(10, 0), color=RED)

        # Create end zone
        end_zone = Rectangle(width=2, height=2, fill_color=GREEN, color=GREEN)
        end_zone.next_to(phase_space_plane, RIGHT)

        # Create arc-angle argument
        arc_angle_argument = Tex(r"2θ = arctan(√(m₂/m₁))").next_to(phase_space_plane, DOWN)

        # Create slow-motion replay
        slow_motion_replay = Tex("Slow-motion replay").next_to(phase_space_plane, DOWN)

        # Animation
        self.add(block_A, block_B, v_A, v_B, collision_counter, velocity_updates, kinetic_energy_equation, momentum_equation, phase_space_plane, state_point, ellipse, momentum_line, end_zone, arc_angle_argument, slow_motion_replay)

        # Animate collision
        for i in range(31):
            # Update velocity vectors
            v_A.set_end(block_A.get_center() + RIGHT * v0 * (1 - 2 * m / (M + m)))
            v_B.set_end(block_B.get_center() + RIGHT * v0 * (1 + 2 * M / (M + m)))

            # Update collision counter
            collision_counter.set_text(f"Collisions = {i + 1}")

            # Update velocity updates
            velocity_updates[i].set_text(f"v_A = {v0 * (1 - 2 * m / (M + m))}")

            # Update state point
            state_point.move_to(phase_space_plane.c2p(sqrt(M * v0 * (1 - 2 * m / (M + m))), sqrt(m * v0 * (1 + 2 * M / (M + m))))

            # Update ellipse
            ellipse.set_height(10 * sqrt(M / (M + m)))

            # Update momentum line
            momentum_line.set_end(phase_space_plane.c2p(sqrt(M * v0 * (1 - 2 * m / (M + m))), 0))

            # Update end zone
            end_zone.move_to(phase_space_plane.c2p(10, 0))

            # Update arc-angle argument
            arc_angle_argument.set_text(f"2θ = arctan(√({m}/{M}))")

            # Update slow-motion replay
            slow_motion_replay.set_text(f"Slow-motion replay (mass ratio: {M/m})")

            # Show animation
            self.play(
                AnimationGroup(
                    block_A.animate.move_to(block_B.get_center()),
                    block_B.animate.move_to(block_A.get_center()),
                    v_A.animate.set_end(block_B.get_center() + RIGHT * v0 * (1 + 2 * M / (M + m))),
                    v_B.animate.set_end(block_A.get_center() + RIGHT * v0 * (1 - 2 * m / (M + m))),
                    rate_func=linear,
                    run_time=1
                ),
                run_time=1
            )

            # Wait for animation to finish
            self.wait()

        # Show final state
        self.play(
            AnimationGroup(
                block_A.animate.move_to(end_zone.get_center()),
                block_B.animate.move_to(end_zone.get_center()),
                v_A.animate.set_end(end_zone.get_center() + RIGHT * v0 * (1 - 2 * m / (M + m))),
                v_B.animate.set_end(end_zone.get_center() + RIGHT * v0 * (1 + 2 * M / (M + m))),
                rate_func=linear,
                run_time=1
            ),
            run_time=1
        )

        # Show conservation of kinetic energy equation
        self.play(Write(kinetic_energy_equation))

        # Show conservation of momentum equation
        self.play(Write(momentum_equation))

        # Show phase-space coordinate plane
        self.play(ShowCreation(phase_space_plane))

        # Show state point
        self.play(ShowCreation(state_point))

        # Show ellipse
        self.play(ShowCreation(ellipse))

        # Show momentum conservation line
        self.play(ShowCreation(momentum_line))

        # Show end zone
        self.play(ShowCreation(end_zone))

        # Show arc-angle argument
        self.play(Write(arc_angle_argument))

        # Show slow-motion replay
        self.play(Write(slow_motion_replay))

        # Show multiple mass ratios
        for mass_ratio in [1, 16, 100, 10000, 10000000000]:
            M = 1
            m = M / mass_ratio
            v0 = 1
            block_A = Rectangle(width=2, height=1, fill_color=BLUE, color=BLUE)
            block_A.to_edge(LEFT)
            block_B = Rectangle(width=2, height=1, fill_color=RED, color=RED)
            block_B.next_to(block_A, RIGHT)
            v_A = Arrow(start=block_A.get_center(), end=block_A.get_center() + RIGHT * v0, color=GREEN)
            v_B = Arrow(start=block_B.get_center(), end=block_B.get_center() + RIGHT * v0, color=GREEN)
            collision_counter = Tex(f"Collisions = 0").next_to(block_A, DOWN)
            velocity_updates = VGroup()
            for i in range(int(3.14159 * mass_ratio)):
                velocity_update = Tex(f"v_A = {v0 * (1 - 2 * m / (M + m))}").next_to(block_A, DOWN)
                velocity_updates.add(velocity_update)
            kinetic_energy_equation = Tex(r"½m₁v₁² + ½m₂v₂² = E").next_to(block_A, DOWN)
            momentum_equation = Tex(r"m₁v₁ + m₂v₂ = P").next_to(block_A, DOWN)
            phase_space_plane = NumberPlane(x_range=[0, 10], y_range=[0, 10])
            state_point = Dot().move_to(phase_space_plane.c2p(1, 1))
            ellipse = Ellipse(width=10, height=10, color=YELLOW)
            momentum_line = Line(start=phase_space_plane.c2p(0, 0), end=phase_space_plane.c2p(10, 0), color=RED)
            end_zone = Rectangle(width=2, height=2, fill_color=GREEN, color=GREEN)
            end_zone.next_to(phase_space_plane, RIGHT)
            arc_angle_argument = Tex(f"2θ = arctan(√({m}/{M}))").next_to(phase_space_plane, DOWN)
            slow_motion_replay = Tex(f"Slow-motion replay (mass ratio: {M/m})").next_to(phase_space_plane, DOWN)
            self.add(block_A, block_B, v_A, v_B, collision_counter, velocity_updates, kinetic_energy_equation, momentum_equation, phase_space_plane, state_point, ellipse, momentum_line, end_zone, arc_angle_argument, slow_motion_replay)
            for i in range(int(3.14159 * mass_ratio)):
                # Update velocity vectors
                v_A.set_end(block_A.get_center() + RIGHT * v0 * (1 - 2 * m / (M + m)))
                v_B.set_end(block_B.get_center() + RIGHT * v0 * (1 + 2 * M / (M + m)))

                # Update collision counter
                collision_counter.set_text(f"Collisions = {i + 1}")

                # Update velocity updates
                velocity_updates[i].set_text(f"v_A = {v0 * (1 - 2 * m / (M + m))}")

                # Update state point
                state_point.move_to(phase_space_plane.c2p(sqrt(M * v0 * (1 - 2 * m / (M + m))), sqrt(m * v0 * (1 + 2 * M / (M + m))))

                # Update ellipse
                ellipse.set_height(10 * sqrt(M / (M + m)))

                # Update momentum line
                momentum_line.set_end(phase_space_plane.c2p(sqrt(M * v0 * (1 - 2 * m / (M + m))), 0))

                # Update end zone
                end_zone.move_to(phase_space_plane.c2p(10, 0))

                # Update arc-angle argument
                arc_angle_argument.set_text(f"2θ = arctan(√({m}/{M}))")

                # Update slow-motion replay
                slow_motion_replay.set_text(f"Slow-motion replay (mass ratio: {M/m})")

                # Show animation
                self.play(
                    AnimationGroup(
                        block_A.animate.move_to(block_B.get_center()),
                        block_B.animate.move_to(block_A.get_center()),
                        v_A.animate.set_end(block_B.get_center() + RIGHT * v0 * (1 + 2 * M / (M + m))),
                        v_B.animate.set_end(block_A.get_center() + RIGHT * v0 * (1 - 2 * m / (M + m))),
                        rate_func=linear,
                        run_time=1
                    ),
                    run_time=1
                )

                # Wait for animation to finish
                self.wait()

        # Show final state
        self.play(
            AnimationGroup(
                block_A.animate.move_to(end_zone.get_center()),
                block_B.animate.move_to(end_zone.get_center()),
                v_A.animate.set_end(end_zone.get_center() + RIGHT * v0 * (1 - 2 * m / (M + m))),
                v_B.animate.set_end(end_zone.get_center() + RIGHT * v0 * (1 + 2 * M / (M + m))),
                rate_func=linear,
                run_time=1
            ),
            run_time=1
        )

        # Show conservation of kinetic energy equation
        self.play(Write(kinetic_energy_equation))

        # Show conservation of momentum equation
        self.play(Write(momentum_equation))

        # Show phase-space coordinate plane
        self.play(ShowCreation(phase_space_plane))

        # Show state point
        self.play(ShowCreation(state_point))

        # Show ellipse
        self.play(ShowCreation(ellipse))

        # Show momentum conservation line
        self.play(ShowCreation(momentum_line))

        # Show end zone
        self.play(ShowCreation(end_zone))

        # Show arc-angle argument
        self.play(Write(arc_angle_argument))

        # Show slow-motion replay
        self.play(Write(slow_motion_replay))

        # Show final text
        final_text = Tex("The final answer is: # Collisions = 31").next_to(phase_space_plane, DOWN)
        self.play(Write(final_text))