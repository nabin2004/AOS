from manim import *
import numpy as np


class WindmillProblem(Scene):
    def construct(self):
        # Title
        title = Text("The Windmill Problem", font_size=40).to_edge(UP)
        subtitle = Text(
            "IMO 2011 Problem 2", font_size=24, color=YELLOW
        ).next_to(title, DOWN, buff=0.15)
        self.play(Write(title), FadeIn(subtitle))
        self.wait(1)

        # Description
        desc = Text(
            "A line rotates continuously, always passing through\n"
            "at least one point, pivoting when it hits a new point.",
            font_size=22,
            color=GREY_B,
        ).next_to(subtitle, DOWN, buff=0.3)
        self.play(FadeIn(desc))
        self.wait(2)
        self.play(FadeOut(desc))

        # Generate points in general position (no 3 collinear)
        # Hand-picked points to ensure good windmill behavior
        point_coords = [
            np.array([-3.0, -1.5, 0]),
            np.array([-1.5, 1.0, 0]),
            np.array([0.5, -0.8, 0]),
            np.array([1.8, 1.5, 0]),
            np.array([-0.5, 0.3, 0]),
            np.array([2.5, -1.0, 0]),
            np.array([-2.0, -0.2, 0]),
        ]
        n = len(point_coords)

        # Create point dots and labels
        dots = VGroup()
        labels = VGroup()
        colors = [RED, BLUE, GREEN, ORANGE, PURPLE, TEAL, PINK]
        for i, (coord, col) in enumerate(zip(point_coords, colors)):
            dot = Dot(coord, radius=0.08, color=col, z_index=2)
            label = Text(f"P{i+1}", font_size=18, color=col).next_to(
                dot, UR, buff=0.1
            )
            dots.add(dot)
            labels.add(label)

        # Show points appearing
        self.play(
            *[GrowFromCenter(d) for d in dots],
            *[FadeIn(l) for l in labels],
            run_time=1.5,
        )
        self.wait(0.5)

        # Info text
        info = Text(
            f"{n} points in general position (no 3 collinear)",
            font_size=22,
            color=GREY_B,
        ).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(info))
        self.wait(1)

        # --- Windmill Algorithm ---
        # We simulate the windmill process:
        # 1. Start with a pivot point and an initial angle
        # 2. Rotate the line until it hits another point
        # 3. Switch pivot to that point and continue

        def angle_from_pivot(pivot_idx, other_idx, current_angle):
            """Compute the angle of the line from pivot to other point."""
            diff = point_coords[other_idx] - point_coords[pivot_idx]
            return np.arctan2(diff[1], diff[0])

        def normalize_angle(a):
            """Normalize angle to [0, 2*pi)."""
            return a % (2 * np.pi)

        def get_next_hit(pivot_idx, current_angle, direction=1):
            """
            Find the next point hit when rotating from current_angle.
            direction: +1 for CCW, -1 for CW
            Returns (next_point_index, angle_to_rotate)
            """
            best_idx = -1
            best_delta = 2 * np.pi + 1  # more than full rotation

            for i in range(n):
                if i == pivot_idx:
                    continue
                diff = point_coords[i] - point_coords[pivot_idx]
                target_angle = np.arctan2(diff[1], diff[0])

                # We need the angle on both sides of the line
                # The line extends in both directions, so we consider
                # target_angle and target_angle + pi
                for offset in [0, np.pi]:
                    ta = normalize_angle(target_angle + offset)
                    ca = normalize_angle(current_angle)

                    if direction == 1:  # CCW
                        delta = normalize_angle(ta - ca)
                    else:  # CW
                        delta = normalize_angle(ca - ta)

                    # Skip zero delta (current position)
                    if delta < 1e-6:
                        delta = 2 * np.pi  # treat as full rotation

                    if delta < best_delta:
                        best_delta = delta
                        best_idx = i
                        # Determine which side the point is on
                        # to know the actual angle the line should be at
                        if offset == 0:
                            best_actual_angle = target_angle
                        else:
                            best_actual_angle = target_angle  # pivot changes

            return best_idx, best_delta * direction, best_actual_angle

        def find_next_event(pivot_idx, current_angle):
            """
            Rotating CCW, find the smallest positive rotation angle
            to hit any other point with either end of the line.
            Returns (hit_point_idx, rotation_amount, new_angle).
            The new pivot will be hit_point_idx.
            """
            best_idx = -1
            best_rotation = float("inf")

            for i in range(n):
                if i == pivot_idx:
                    continue
                diff = point_coords[i] - point_coords[pivot_idx]
                target = np.arctan2(diff[1], diff[0])

                # The line at angle theta passes through pivot with direction theta
                # Point i is hit when theta = target or theta = target + pi (mod 2pi)
                for offset in [0, np.pi]:
                    needed_angle = normalize_angle(target + offset)
                    ca = normalize_angle(current_angle)
                    rotation = normalize_angle(needed_angle - ca)

                    if rotation < 1e-8:
                        rotation = 2 * np.pi

                    if rotation < best_rotation:
                        best_rotation = rotation
                        best_idx = i

            return best_idx, best_rotation

        # Create the rotating line
        LINE_LENGTH = 8.0

        def create_line(pivot_coord, angle):
            direction = np.array([np.cos(angle), np.sin(angle), 0])
            start = pivot_coord - LINE_LENGTH / 2 * direction
            end = pivot_coord + LINE_LENGTH / 2 * direction
            return Line(start, end, color=YELLOW, stroke_width=3, z_index=1)

        # Initialize: start with point 4 (index 4, the central one) as pivot
        current_pivot = 4
        # Start with a horizontal line
        current_angle = 0.0

        # Adjust starting angle slightly so we don't start exactly on another point
        # Check if any point is exactly on the initial line
        for i in range(n):
            if i == current_pivot:
                continue
            diff = point_coords[i] - point_coords[current_pivot]
            a = np.arctan2(diff[1], diff[0])
            if abs(normalize_angle(a) - normalize_angle(current_angle)) < 0.01 or \
               abs(normalize_angle(a + np.pi) - normalize_angle(current_angle)) < 0.01:
                current_angle += 0.05
                break

        line = create_line(point_coords[current_pivot], current_angle)

        # Pivot indicator
        pivot_ring = Circle(
            radius=0.15,
            color=YELLOW,
            stroke_width=3,
            z_index=3,
        ).move_to(point_coords[current_pivot])

        pivot_label = Text("pivot", font_size=18, color=YELLOW).next_to(
            pivot_ring, DOWN, buff=0.15
        )

        self.play(
            Create(line),
            Create(pivot_ring),
            FadeIn(pivot_label),
            run_time=1,
        )
        self.wait(0.5)

        # Replace info text
        self.play(FadeOut(info))
        status = Text(
            "Line rotates CCW, pivoting at each point it hits",
            font_size=22,
            color=GREY_B,
        ).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(status))

        # Angle tracker for smooth rotation
        angle_tracker = ValueTracker(current_angle)

        # We'll do the windmill for enough steps to cover ~360 degrees total rotation
        total_rotation = 0.0
        target_total = 2 * np.pi  # full 360 degrees
        step = 0
        max_steps = 30  # safety limit

        # Highlight the current pivot
        dots[current_pivot].set_color(YELLOW).scale(1.5)

        # Step counter
        step_text = Text(f"Pivots: 0", font_size=22, color=WHITE).to_edge(
            DOWN, buff=0.7
        )
        self.play(FadeIn(step_text))

        pivot_count = 0

        while total_rotation < target_total and step < max_steps:
            step += 1

            # Find next event
            next_idx, rotation_amount = find_next_event(
                current_pivot, current_angle
            )

            if next_idx == -1:
                break

            # Cap rotation if we'd exceed target
            if total_rotation + rotation_amount > target_total + 0.1:
                rotation_amount = target_total - total_rotation + 0.01

            new_angle = current_angle + rotation_amount

            # Animate rotation around current pivot
            pivot_coord = point_coords[current_pivot]

            # Determine run_time based on rotation amount
            run_time = max(0.3, rotation_amount / (np.pi / 4) * 0.8)
            run_time = min(run_time, 2.0)

            # Create animation: rotate line around pivot
            start_angle = current_angle
            end_angle = new_angle

            def line_updater(mob, alpha, sa=start_angle, ea=end_angle, pc=pivot_coord):
                a = interpolate(sa, ea, alpha)
                direction = np.array([np.cos(a), np.sin(a), 0])
                start_pt = pc - LINE_LENGTH / 2 * direction
                end_pt = pc + LINE_LENGTH / 2 * direction
                mob.put_start_and_end_on(start_pt, end_pt)

            self.play(
                UpdateFromAlphaFunc(line, line_updater),
                run_time=run_time,
                rate_func=linear,
            )

            total_rotation += rotation_amount
            current_angle = new_angle

            if total_rotation >= target_total:
                break

            # Now pivot switches to next_idx
            old_pivot = current_pivot
            current_pivot = next_idx
            pivot_count += 1

            # Flash the hit point
            flash = Flash(
                point_coords[next_idx],
                color=YELLOW,
                flash_radius=0.3,
                line_length=0.15,
                num_lines=8,
                run_time=0.3,
            )

            # Reset old pivot dot
            dots[old_pivot].set_color(colors[old_pivot]).scale(1 / 1.5)
            # Highlight new pivot
            dots[current_pivot].set_color(YELLOW).scale(1.5)

            # Move pivot ring
            new_pivot_label = Text("pivot", font_size=18, color=YELLOW).next_to(
                point_coords[current_pivot], DOWN, buff=0.15
            )

            new_step_text = Text(
                f"Pivots: {pivot_count}", font_size=22, color=WHITE
            ).to_edge(DOWN, buff=0.7)

            self.play(
                flash,
                pivot_ring.animate.move_to(point_coords[current_pivot]),
                Transform(pivot_label, new_pivot_label),
                Transform(step_text, new_step_text),
                run_time=0.4,
            )

        # Final message
        self.play(FadeOut(status))
        final_msg = Text(
            "The windmill completes a full rotation!\n"
            "The pattern repeats periodically.",
            font_size=26,
            color=GREEN,
        ).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(final_msg))

        # Do one more smooth continuous rotation to show the beauty
        self.wait(1)

        self.play(FadeOut(final_msg))
        beauty_msg = Text(
            "Continuous windmill motion",
            font_size=26,
            color=BLUE_B,
        ).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(beauty_msg))

        # Continue for another full rotation, faster
        total_rotation2 = 0.0
        target_total2 = 2 * np.pi
        step2 = 0

        while total_rotation2 < target_total2 and step2 < max_steps:
            step2 += 1
            next_idx, rotation_amount = find_next_event(
                current_pivot, current_angle
            )
            if next_idx == -1:
                break
            if total_rotation2 + rotation_amount > target_total2 + 0.1:
                rotation_amount = target_total2 - total_rotation2 + 0.01

            new_angle = current_angle + rotation_amount
            pivot_coord = point_coords[current_pivot]
            start_angle = current_angle
            end_angle = new_angle
            run_time = max(0.15, rotation_amount / (np.pi / 4) * 0.4)
            run_time = min(run_time, 1.0)

            def line_updater2(mob, alpha, sa=start_angle, ea=end_angle, pc=pivot_coord):
                a = interpolate(sa, ea, alpha)
                direction = np.array([np.cos(a), np.sin(a), 0])
                start_pt = pc - LINE_LENGTH / 2 * direction
                end_pt = pc + LINE_LENGTH / 2 * direction
                mob.put_start_and_end_on(start_pt, end_pt)

            self.play(
                UpdateFromAlphaFunc(line, line_updater2),
                run_time=run_time,
                rate_func=linear,
            )

            total_rotation2 += rotation_amount
            current_angle = new_angle

            if total_rotation2 >= target_total2:
                break

            old_pivot = current_pivot
            current_pivot = next_idx
            pivot_count += 1

            dots[old_pivot].set_color(colors[old_pivot]).scale(1 / 1.5)
            dots[current_pivot].set_color(YELLOW).scale(1.5)

            new_step_text = Text(
                f"Pivots: {pivot_count}", font_size=22, color=WHITE
            ).to_edge(DOWN, buff=0.7)

            self.play(
                pivot_ring.animate.move_to(point_coords[current_pivot]),
                Transform(step_text, new_step_text),
                run_time=0.2,
            )

        self.wait(1)

        # End
        self.play(FadeOut(beauty_msg))
        end_text = VGroup(
            Text("The Windmill Process", font_size=36, color=YELLOW),
            Text(
                "For any set of points in general position,\n"
                "the line visits every point infinitely often.",
                font_size=24,
                color=WHITE,
            ),
        ).arrange(DOWN, buff=0.3).move_to(ORIGIN)

        self.play(
            FadeOut(line),
            FadeOut(pivot_ring),
            FadeOut(pivot_label),
            FadeOut(step_text),
            FadeOut(dots),
            FadeOut(labels),
            FadeOut(title),
            FadeOut(subtitle),
        )
        self.play(FadeIn(end_text))
        self.wait(3)
        self.play(FadeOut(end_text))