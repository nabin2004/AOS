from manim import *
import numpy as np

class EigenvectorAnimation(Scene):
    def construct(self):
        # Define the 2x2 matrix
        matrix = [[2, 1], [1, 2]]
        A = np.array(matrix, dtype=float)

        # Compute eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eig(A)
        # eigenvalues: [3, 1], eigenvectors: columns are [1/√2, 1/√2] and [-1/√2, 1/√2]

        lambda1 = eigenvalues[0]  # 3
        lambda2 = eigenvalues[1]  # 1
        v1 = eigenvectors[:, 0]   # [1/√2, 1/√2]
        v2 = eigenvectors[:, 1]   # [-1/√2, 1/√2]

        # Normalize eigenvectors for display
        v1_norm = v1 / np.linalg.norm(v1)
        v2_norm = v2 / np.linalg.norm(v2)

        # Title
        title = Text("Eigenvectors Under Matrix Transformation", font_size=36)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title))
        self.wait(0.5)

        # Show the matrix
        matrix_label = MathTex(
            r"A = \begin{bmatrix} 2 & 1 \\ 1 & 2 \end{bmatrix}",
            font_size=36
        )
        matrix_label.to_corner(UL, buff=0.5).shift(DOWN * 0.8)
        self.play(Write(matrix_label))
        self.wait(0.5)

        # Create number plane
        plane = NumberPlane(
            x_range=[-5, 5, 1],
            y_range=[-5, 5, 1],
            x_length=8,
            y_length=8,
            background_line_style={
                "stroke_color": BLUE_E,
                "stroke_width": 1,
                "stroke_opacity": 0.4,
            },
            axis_config={"stroke_width": 2},
        )
        plane.shift(RIGHT * 0.5)

        self.play(Create(plane), run_time=1.5)

        # Basis vectors
        e1_arrow = Arrow(
            plane.c2p(0, 0), plane.c2p(1, 0),
            buff=0, color=GREEN, stroke_width=4
        )
        e2_arrow = Arrow(
            plane.c2p(0, 0), plane.c2p(0, 1),
            buff=0, color=YELLOW, stroke_width=4
        )
        e1_label = MathTex(r"\mathbf{e}_1", font_size=30, color=GREEN).next_to(e1_arrow, DOWN, buff=0.1)
        e2_label = MathTex(r"\mathbf{e}_2", font_size=30, color=YELLOW).next_to(e2_arrow, LEFT, buff=0.1)

        self.play(
            GrowArrow(e1_arrow), Write(e1_label),
            GrowArrow(e2_arrow), Write(e2_label),
        )
        self.wait(0.5)

        # Eigenvector arrows (before transformation)
        ev1_end = plane.c2p(v1_norm[0] * 2, v1_norm[1] * 2)
        ev2_end = plane.c2p(v2_norm[0] * 2, v2_norm[1] * 2)

        ev1_arrow = Arrow(
            plane.c2p(0, 0), ev1_end,
            buff=0, color=RED, stroke_width=5
        )
        ev2_arrow = Arrow(
            plane.c2p(0, 0), ev2_end,
            buff=0, color=BLUE, stroke_width=5
        )

        ev1_label = MathTex(r"\mathbf{v}_1", font_size=30, color=RED)
        ev1_label.next_to(ev1_arrow.get_end(), UR, buff=0.1)
        ev2_label = MathTex(r"\mathbf{v}_2", font_size=30, color=BLUE)
        ev2_label.next_to(ev2_arrow.get_end(), UL, buff=0.1)

        self.play(
            GrowArrow(ev1_arrow), Write(ev1_label),
            GrowArrow(ev2_arrow), Write(ev2_label),
        )
        self.wait(0.5)

        # Some "ordinary" vectors to show they rotate
        ordinary_vectors = []
        ordinary_colors = [PURPLE_B, ORANGE, TEAL_B, PINK]
        ordinary_dirs = [
            np.array([1.0, 0.3]),
            np.array([-0.5, 1.5]),
            np.array([1.5, -0.5]),
            np.array([-1.0, -1.2]),
        ]
        for i, d in enumerate(ordinary_dirs):
            arr = Arrow(
                plane.c2p(0, 0),
                plane.c2p(d[0], d[1]),
                buff=0,
                color=ordinary_colors[i],
                stroke_width=3,
                stroke_opacity=0.7,
            )
            ordinary_vectors.append(arr)

        self.play(*[GrowArrow(v) for v in ordinary_vectors], run_time=0.8)
        self.wait(0.3)

        # Explanation before transformation
        info_text = Text(
            "Now applying transformation A...",
            font_size=28, color=WHITE
        ).to_edge(DOWN, buff=0.4)
        self.play(Write(info_text))
        self.wait(0.5)

        # --- Apply transformation smoothly ---
        # We need to animate all vectors and the grid transforming

        # Store original positions for interpolation
        # We'll use updaters with a ValueTracker

        t_tracker = ValueTracker(0)

        # Function to compute interpolated transformed point
        def lerp_transform(original_coords, t):
            """Interpolate between identity and A transformation."""
            orig = np.array(original_coords[:2])
            transformed = A @ orig
            result = (1 - t) * orig + t * transformed
            return result

        # Create copies for animation
        # Animate grid lines
        # We'll create a set of grid lines and animate them

        # Horizontal and vertical grid lines
        grid_lines = VGroup()
        for x in np.arange(-5, 6, 1):
            line = Line(plane.c2p(x, -5), plane.c2p(x, 5), stroke_width=1, stroke_color=BLUE_E, stroke_opacity=0.4)
            grid_lines.add(line)
        for y in np.arange(-5, 6, 1):
            line = Line(plane.c2p(-5, y), plane.c2p(5, y), stroke_width=1, stroke_color=BLUE_E, stroke_opacity=0.4)
            grid_lines.add(line)

        # We'll use ApplyMatrix-like approach but manually for all objects
        # Actually, let's use a different approach: animate using ValueTracker

        # Remove the plane background lines and replace with our own animated grid
        # For simplicity, let's use ApplyMatrix on a group

        # Collect all objects that should transform
        # We need to be more careful. Let's use a different strategy:
        # Fade out current elements, create a fresh setup, and use ApplyMatrix

        self.play(
            FadeOut(info_text),
            FadeOut(e1_label), FadeOut(e2_label),
            FadeOut(ev1_label), FadeOut(ev2_label),
        )

        # Group everything that transforms
        transform_group = VGroup(
            plane, e1_arrow, e2_arrow,
            ev1_arrow, ev2_arrow,
            *ordinary_vectors
        )

        # Create labels that will update position
        # We'll add them back after transformation

        # Show eigenvalue info
        eigen_info = VGroup(
            MathTex(r"\lambda_1 = 3", font_size=32, color=RED),
            MathTex(r"\lambda_2 = 1", font_size=32, color=BLUE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        eigen_info.to_corner(UR, buff=0.5).shift(DOWN * 0.5)

        self.play(Write(eigen_info))
        self.wait(0.3)

        # Apply the matrix transformation smoothly
        # The matrix transformation in plane coordinates
        # plane.c2p maps grid coords to screen coords
        # We need to apply the linear map in the plane's coordinate system

        # Get the plane's transformation info
        x_unit = plane.c2p(1, 0) - plane.c2p(0, 0)
        y_unit = plane.c2p(0, 1) - plane.c2p(0, 0)
        origin = plane.c2p(0, 0)

        # The matrix in screen coordinates
        # If plane maps (a,b) -> origin + a*x_unit + b*y_unit
        # Then applying A means (a,b) -> A@(a,b) -> origin + (A@(a,b))[0]*x_unit + (A@(a,b))[1]*y_unit
        # In screen coords, this is a linear map around origin

        # Screen-space matrix
        # P = [x_unit | y_unit] (as columns, but these are 3D vectors)
        P = np.column_stack([x_unit, y_unit])  # 3x2
        # Transform: screen_point = origin + P @ grid_coords
        # After A: screen_point = origin + P @ A @ grid_coords
        # = origin + (P @ A @ P_inv) @ (screen_point - origin)  ... but P is not square

        # Simpler: use ApplyMatrix with the matrix, but we need to account for plane offset
        # Actually, Manim's ApplyMatrix applies around ORIGIN by default
        # We need to apply around the plane's origin

        plane_origin = plane.c2p(0, 0)

        # The screen-space linear transformation matrix (3x3)
        # We need to figure out how grid coordinates map to screen coordinates
        sx = np.linalg.norm(x_unit[:2])  # scale in x
        sy = np.linalg.norm(y_unit[:2])  # scale in y

        # Since the plane is axis-aligned and uniformly scaled:
        # screen = plane_origin + diag(sx, sy) @ grid
        # After A: screen = plane_origin + diag(sx, sy) @ A @ diag(1/sx, 1/sy) @ (screen - plane_origin)
        # So the screen-space matrix is: diag(sx, sy) @ A @ diag(1/sx, 1/sy)

        S = np.diag([sx, sy])
        S_inv = np.diag([1/sx, 1/sy])
        screen_matrix = S @ A @ S_inv  # 2x2

        # But since sx == sy for a uniform NumberPlane, this simplifies to A itself
        # Let's verify
        # Actually for NumberPlane with equal x_length and y_length over equal ranges, sx == sy

        transform_text = Text(
            "Applying A to all vectors...",
            font_size=28, color=YELLOW
        ).to_edge(DOWN, buff=0.4)
        self.play(Write(transform_text))

        # Apply transformation
        self.play(
            transform_group.animate.apply_matrix(
                A,
                about_point=plane_origin
            ),
            run_time=2.5,
            rate_func=smooth,
        )
        self.wait(0.5)

        self.play(FadeOut(transform_text))

        # Now add labels back
        # Eigenvector 1 after transformation: scaled by lambda1=3
        ev1_end_new = plane_origin + A @ np.array([v1_norm[0] * 2, v1_norm[1] * 2, 0])[:2].tolist() + [0]
        # Actually let's just position labels near the arrow ends

        ev1_label_new = MathTex(
            r"\mathbf{v}_1", r"\text{ (scaled by } \lambda_1=3\text{)}",
            font_size=26, color=RED
        )
        ev1_label_new.next_to(ev1_arrow.get_end(), UR, buff=0.15)

        ev2_label_new = MathTex(
            r"\mathbf{v}_2", r"\text{ (scaled by } \lambda_2=1\text{)}",
            font_size=26, color=BLUE
        )
        ev2_label_new.next_to(ev2_arrow.get_end(), UL, buff=0.15)

        self.play(Write(ev1_label_new), Write(ev2_label_new))
        self.wait(0.5)

        # Highlight that eigenvectors are special
        # Draw dashed lines along eigenvector directions to show they stayed on the same line
        ev1_line = DashedLine(
            plane_origin + np.array([-v1_norm[0]*4, -v1_norm[1]*4, 0]),
            plane_origin + np.array([v1_norm[0]*6, v1_norm[1]*6, 0]),
            color=RED, stroke_width=2, dash_length=0.15
        )
        ev2_line = DashedLine(
            plane_origin + np.array([-v2_norm[0]*4, -v2_norm[1]*4, 0]),
            plane_origin + np.array([v2_norm[0]*4, v2_norm[1]*4, 0]),
            color=BLUE, stroke_width=2, dash_length=0.15
        )

        self.play(Create(ev1_line), Create(ev2_line), run_time=1)
        self.wait(0.5)

        # Highlight box
        highlight_box = SurroundingRectangle(
            VGroup(ev1_arrow, ev2_arrow),
            color=GOLD, buff=0.3, stroke_width=3
        )

        special_text = Text(
            "Eigenvectors stay on their original line!",
            font_size=32, color=GOLD
        ).to_edge(DOWN, buff=0.5)

        self.play(
            Create(highlight_box),
            Write(special_text),
            run_time=1.5
        )
        self.wait(1)

        # Show the key equation
        equation = MathTex(
            r"A\mathbf{v} = \lambda\mathbf{v}",
            font_size=48, color=GOLD
        )
        equation_box = SurroundingRectangle(equation, color=GOLD, buff=0.2)
        eq_group = VGroup(equation, equation_box)
        eq_group.move_to(ORIGIN).shift(DOWN * 0.5)

        # Create a background rectangle for the equation
        bg_rect = BackgroundRectangle(eq_group, color=BLACK, fill_opacity=0.85, buff=0.3)

        self.play(
            FadeIn(bg_rect),
            Write(equation),
            Create(equation_box),
            run_time=1.5
        )
        self.wait(1)

        # Final summary
        summary = VGroup(
            MathTex(r"A\mathbf{v}_1 = 3\mathbf{v}_1", font_size=36, color=RED),
            MathTex(r"A\mathbf{v}_2 = 1\cdot\mathbf{v}_2", font_size=36, color=BLUE),
        ).arrange(DOWN, buff=0.3)
        summary.next_to(eq_group, DOWN, buff=0.5)
        summary_bg = BackgroundRectangle(summary, color=BLACK, fill_opacity=0.85, buff=0.2)

        self.play(FadeIn(summary_bg), Write(summary), run_time=1.5)
        self.wait(1)

        # Final note about other vectors
        other_note = Text(
            "Other vectors both rotate AND scale — they are NOT eigenvectors",
            font_size=24, color=GREY_A
        ).to_edge(DOWN, buff=0.15)
        other_bg = BackgroundRectangle(other_note, color=BLACK, fill_opacity=0.8, buff=0.1)

        self.play(
            FadeOut(special_text),
            FadeIn(other_bg),
            Write(other_note),
            run_time=1
        )
        self.wait(2)

        # Flash eigenvectors
        self.play(
            ev1_arrow.animate.set_stroke(width=8),
            ev2_arrow.animate.set_stroke(width=8),
            rate_func=there_and_back,
            run_time=1.5
        )
        self.wait(1)

        # Fade everything out
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=1.5)
        self.wait(0.5)