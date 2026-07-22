"""
RUKUMINI — Cinematic Branding Intro (Mathematical Scenery Edition)
=================================================================
A ~16s intro where Euler's Formula and Vitruvian Man visualizations
become cinematic establishing shots (B-roll) behind the branding.

The math scenes are darkened, vignetted, and treated as atmosphere —
not educational content. Think: movie trailer establishing shots.

RENDER:
    manim -pqh intro.py RukuminiIntro      # 1080p60 high quality
    manim -pql intro.py RukuminiIntro      # fast draft

ASSETS:
    ./rukumini.png       -> RUKUMINI wordmark
    ./college_logo.png   -> College logo
"""

import os
import random
import math

import numpy as np
from manim import *

# ============================================================================
# BRAND PALETTE — Dark Premium
# ============================================================================
DEEP_BLACK = "#030303"
CHARCOAL = "#0A0A0A"
RUKUMINI_RED = "#C41E3A"
RUKUMINI_DARK_RED = "#3D0A0A"
RUKUMINI_WHITE = "#E0E0E0"
RUKUMINI_SILVER = "#A0A0A0"
ACCENT_GOLD = "#C9A84C"
ACCENT_AMBER = "#7A5F1E"

RUKUMINI_LOGO_PATH = "./rukumini.png"
COLLEGE_LOGO_PATH = "./college_logo.png"

# Beat map (seconds) — phonk-sync ready
BEATS = {
    "euler_establish": 3.5,
    "euler_fade": 0.8,
    "vitruvian_establish": 3.5,
    "vitruvian_fade": 0.7,
    "impact_flash": 0.4,
    "rukumini_slam": 1.0,
    "rukumini_hold": 2.5,
    "transition": 0.8,
    "college_reveal": 1.0,
    "college_hold": 2.5,
    "outro": 1.3,
    "fade_out": 0.5,
}

# ============================================================================
# UTILITIES
# ============================================================================


def safe_image_or_placeholder(
    path, width, placeholder_text, placeholder_color=RUKUMINI_RED
):
    if os.path.exists(path):
        img = ImageMobject(path)
        img.width = width
        return img
    box = RoundedRectangle(
        width=width,
        height=width * 0.35,
        corner_radius=0.08,
        color=placeholder_color,
        fill_color=Color(placeholder_color).interpolate(Color(DEEP_BLACK), 0.85),
        fill_opacity=1,
        stroke_width=1.5,
        stroke_opacity=0.4,
    )
    label = Text(
        placeholder_text,
        font="Helvetica Neue",
        font_size=18,
        color=Color(placeholder_color).interpolate(Color(RUKUMINI_WHITE), 0.5),
        weight=BOLD,
    ).move_to(box)
    return Group(box, label)


def _make_vignette(opacity=0.7, color=DEEP_BLACK, inner=2.5, outer=12):
    return Annulus(
        inner_radius=inner,
        outer_radius=outer,
        fill_color=color,
        fill_opacity=opacity,
        stroke_width=0,
    )


def _make_film_grain(n_dots=600, opacity=0.025):
    dots = VGroup()
    for _ in range(n_dots):
        dot = Dot(
            point=[random.uniform(-8, 8), random.uniform(-5, 5), 0],
            radius=random.uniform(0.005, 0.012),
            color=RUKUMINI_WHITE,
            fill_opacity=random.uniform(0.015, opacity),
        )
        dots.add(dot)
    return dots


def _make_scan_lines(n=16):
    lines = VGroup()
    for i in range(n):
        y = interpolate(-4.5, 4.5, i / max(n - 1, 1))
        opacity = 0.02 + 0.015 * math.sin(i * 0.7)
        line = Line(
            LEFT * 10,
            RIGHT * 10,
            stroke_width=0.5,
            stroke_opacity=opacity,
            color=RUKUMINI_WHITE,
        )
        line.shift(UP * y)
        lines.add(line)
    return lines


def _make_glow_ring(radius=3, color=RUKUMINI_RED, opacity=0.5):
    layers = VGroup()
    for i in range(3):
        r = radius * (1 + i * 0.12)
        alpha = opacity * (1 - i * 0.25)
        ring = Circle(radius=r, color=color, stroke_width=4 - i, stroke_opacity=alpha)
        layers.add(ring)
    return layers


# ============================================================================
# CINEMATIC MATH SCENERY — Euler's Formula (darkened, atmospheric)
# ============================================================================


class EulerScenery:
    """Euler's formula visualization treated as cinematic B-roll."""

    def __init__(self, scene):
        self.scene = scene
        self.group = VGroup()
        self._build()

    def _build(self):
        # Complex plane — very dim, atmospheric
        self.plane = ComplexPlane(
            x_range=[-2.5, 2.5, 1],
            y_range=[-2.5, 2.5, 1],
            background_line_style={
                "stroke_opacity": 0.06,
                "stroke_color": RUKUMINI_SILVER,
            },
        )
        self.plane.scale(1.3)

        # Unit circle — faint red glow
        self.circle = Circle(
            radius=2.6, color=RUKUMINI_RED, stroke_width=1.5, stroke_opacity=0.25
        )

        # Formula — ghosted in background
        self.formula = MathTex(
            r"e^{ix} = \cos(x) + i\sin(x)", font_size=28, color=RUKUMINI_SILVER
        )
        self.formula.set_opacity(0.12)
        self.formula.to_corner(UL).shift(DOWN * 0.3 + RIGHT * 0.3)

        # Moving point + radius (will be animated)
        self.angle_tracker = ValueTracker(0)

        self.dot = always_redraw(
            lambda: Dot(
                2.6
                * np.array(
                    [
                        np.cos(self.angle_tracker.get_value()),
                        np.sin(self.angle_tracker.get_value()),
                        0,
                    ]
                ),
                color=RUKUMINI_RED,
                radius=0.06,
                fill_opacity=0.8,
            )
        )

        self.radius = always_redraw(
            lambda: Line(
                ORIGIN,
                2.6
                * np.array(
                    [
                        np.cos(self.angle_tracker.get_value()),
                        np.sin(self.angle_tracker.get_value()),
                        0,
                    ]
                ),
                color=RUKUMINI_RED,
                stroke_width=1.5,
                stroke_opacity=0.4,
            )
        )

        # Traced path
        self.traced_path = TracedPath(
            self.dot.get_center,
            stroke_color=RUKUMINI_RED,
            stroke_width=2,
            stroke_opacity=0.3,
        )

        # Projection lines — very faint
        self.h_line = always_redraw(
            lambda: DashedLine(
                2.6
                * np.array(
                    [
                        np.cos(self.angle_tracker.get_value()),
                        np.sin(self.angle_tracker.get_value()),
                        0,
                    ]
                ),
                2.6 * np.array([np.cos(self.angle_tracker.get_value()), 0, 0]),
                color=ACCENT_GOLD,
                stroke_opacity=0.15,
                dash_length=0.08,
            )
        )

        self.v_line = always_redraw(
            lambda: DashedLine(
                2.6
                * np.array(
                    [
                        np.cos(self.angle_tracker.get_value()),
                        np.sin(self.angle_tracker.get_value()),
                        0,
                    ]
                ),
                2.6 * np.array([0, np.sin(self.angle_tracker.get_value()), 0]),
                color=RUKUMINI_RED,
                stroke_opacity=0.15,
                dash_length=0.08,
            )
        )

        # Dark overlay to push it into background
        self.dark_overlay = FullScreenRectangle(
            fill_color=DEEP_BLACK, fill_opacity=0.55
        )

        self.group.add(
            self.plane,
            self.circle,
            self.formula,
            self.traced_path,
            self.radius,
            self.h_line,
            self.v_line,
            self.dot,
            self.dark_overlay,
        )

    def add_to_scene(self):
        self.scene.add(self.group)
        return self

    def animate_trace(self, duration):
        """Trace the full circle over given duration."""
        return self.angle_tracker.animate(run_time=duration).set_value(2 * PI)


# ============================================================================
# CINEMATIC MATH SCENERY — Vitruvian Man (darkened, atmospheric)
# ============================================================================


class VitruvianScenery:
    """Vitruvian Man / Golden Ratio as cinematic B-roll."""

    def __init__(self, scene):
        self.scene = scene
        self.group = VGroup()
        self._build()

    def _build(self):
        # Golden spiral — atmospheric
        self.spiral = self._make_golden_spiral(opacity=0.2)
        self.spiral.scale(1.4)

        # Circle and square — faint
        self.circle = Circle(
            radius=2.4, color=RUKUMINI_RED, stroke_width=1.5, stroke_opacity=0.2
        )
        self.square = Square(
            side_length=4.8, color=ACCENT_GOLD, stroke_width=1.5, stroke_opacity=0.15
        )

        # Vitruvian figure — wireframe style, very dim
        self.figure = self._make_wireframe_figure(opacity=0.18)

        # Phi formula — ghosted
        self.phi_formula = MathTex(
            r"\Phi = \frac{1 + \sqrt{5}}{2} \approx 1.618",
            font_size=24,
            color=RUKUMINI_SILVER,
        )
        self.phi_formula.set_opacity(0.1)
        self.phi_formula.to_corner(DR).shift(UP * 0.3 + LEFT * 0.3)

        # Golden ratio line — faint
        self.golden_line = self._make_golden_line(opacity=0.15)

        # Dark overlay
        self.dark_overlay = FullScreenRectangle(fill_color=DEEP_BLACK, fill_opacity=0.6)

        self.group.add(
            self.spiral,
            self.circle,
            self.square,
            self.figure,
            self.phi_formula,
            self.golden_line,
            self.dark_overlay,
        )

    def _make_golden_spiral(self, opacity=0.2):
        """Approximate golden spiral from quarter-circle arcs."""
        arcs = VGroup()
        phi = 1.618
        # Fibonacci-like squares: 1, 1, 2, 3, 5, 8 scaled down
        sizes = [0.5, 0.5, 1.0, 1.5, 2.5, 4.0]
        centers = [
            [0, 0, 0],
            [0.5, 0, 0],
            [0.5, 0.5, 0],
            [-0.5, 0.5, 0],
            [-0.5, -1.0, 0],
            [1.5, -1.0, 0],
        ]
        angles = [
            (0, PI / 2),
            (0, PI / 2),
            (PI / 2, PI),
            (PI, 3 * PI / 2),
            (3 * PI / 2, 2 * PI),
            (0, PI / 2),
        ]
        for i, (size, center, (start, end)) in enumerate(zip(sizes, centers, angles)):
            arc = Arc(
                radius=size,
                start_angle=start,
                angle=end - start,
                color=ACCENT_GOLD,
                stroke_width=2,
                stroke_opacity=opacity * (1 - i * 0.1),
            )
            arc.move_to(center)
            arcs.add(arc)
        return arcs

    def _make_wireframe_figure(self, opacity=0.18):
        """Minimalist wireframe human figure."""
        g = VGroup()
        # Head
        head = Circle(
            radius=0.35, color=RUKUMINI_WHITE, stroke_width=1.2, stroke_opacity=opacity
        ).shift(UP * 1.3)
        # Body
        body = Line(
            UP * 0.95,
            DOWN * 0.3,
            color=RUKUMINI_WHITE,
            stroke_width=1.5,
            stroke_opacity=opacity,
        )
        # Arms (outstretched to match circle)
        left_arm = Line(
            UP * 0.6 + LEFT * 0.15,
            LEFT * 2.2 + UP * 0.2,
            color=RUKUMINI_WHITE,
            stroke_width=1.2,
            stroke_opacity=opacity,
        )
        right_arm = Line(
            UP * 0.6 + RIGHT * 0.15,
            RIGHT * 2.2 + UP * 0.2,
            color=RUKUMINI_WHITE,
            stroke_width=1.2,
            stroke_opacity=opacity,
        )
        # Legs
        left_leg = Line(
            DOWN * 0.3,
            DOWN * 2.2 + LEFT * 0.7,
            color=RUKUMINI_WHITE,
            stroke_width=1.2,
            stroke_opacity=opacity,
        )
        right_leg = Line(
            DOWN * 0.3,
            DOWN * 2.2 + RIGHT * 0.7,
            color=RUKUMINI_WHITE,
            stroke_width=1.2,
            stroke_opacity=opacity,
        )
        # Center dot (navel)
        navel = Dot(ORIGIN, color=ACCENT_GOLD, radius=0.04, fill_opacity=opacity * 2)

        g.add(head, body, left_arm, right_arm, left_leg, right_leg, navel)
        return g

    def _make_golden_line(self, opacity=0.15):
        """Golden ratio division line."""
        line = Line(
            LEFT * 3.5,
            RIGHT * 3.5,
            color=ACCENT_GOLD,
            stroke_width=2,
            stroke_opacity=opacity,
        )
        # Mark the golden cut
        cut_x = 3.5 / 1.618 - 3.5 / 2  # approximately
        cut = Dot(
            [cut_x, 0, 0], color=ACCENT_GOLD, radius=0.05, fill_opacity=opacity * 3
        )
        return VGroup(line, cut)

    def add_to_scene(self):
        self.scene.add(self.group)
        return self


# ============================================================================
# MAIN SCENE
# ============================================================================


class RukuminiIntro(Scene):
    def construct(self):
        self.camera.background_color = DEEP_BLACK

        # Persistent ambient overlays
        self.film_grain = _make_film_grain()
        self.scan_lines = _make_scan_lines()
        self.vignette = _make_vignette(opacity=0.45, inner=2.8, outer=12)
        self.add(self.film_grain, self.scan_lines, self.vignette)

        # Execute
        self.euler_shot()
        self.vitruvian_shot()
        self.rukumini_reveal()
        self.college_reveal()

    # ------------------------------------------------------------------
    # SHOT 1: Euler's Formula — Cinematic Establishing Shot
    # ------------------------------------------------------------------
    def euler_shot(self):
        """Euler's formula traces a circle in the background like a movie establishing shot."""
        bg = FullScreenRectangle(fill_color=DEEP_BLACK, fill_opacity=1)
        self.add(bg)

        # Build scenery
        euler = EulerScenery(self).add_to_scene()

        # Camera "push in" — scale up subtly while tracing
        self.play(
            euler.animate_trace(BEATS["euler_establish"] * 0.85),
            euler.group.animate(run_time=BEATS["euler_establish"]).scale(1.15),
            run_time=BEATS["euler_establish"],
        )

        # Brief hold on the completed circle
        self.wait(BEATS["euler_establish"] * 0.15)

        # Fade out to black (not removing, just fading for transition)
        self.play(
            euler.group.animate(run_time=BEATS["euler_fade"]).set_opacity(0),
            run_time=BEATS["euler_fade"],
        )
        self.remove(euler.group)
        self.euler_bg = bg

    # ------------------------------------------------------------------
    # SHOT 2: Vitruvian Man — Cinematic Establishing Shot
    # ------------------------------------------------------------------
    def vitruvian_shot(self):
        """Vitruvian Man / Golden Ratio as second establishing shot."""
        vitruvian = VitruvianScenery(self).add_to_scene()

        # Slow "camera drift" + elements fading in sequentially
        # First, spiral draws itself
        spiral_draw_time = BEATS["vitruvian_establish"] * 0.35
        self.play(
            *[Create(arc, run_time=spiral_draw_time * 0.8) for arc in vitruvian.spiral],
            run_time=spiral_draw_time,
        )

        # Then circle and square fade in
        self.play(
            FadeIn(vitruvian.circle, run_time=BEATS["vitruvian_establish"] * 0.15),
            FadeIn(vitruvian.square, run_time=BEATS["vitruvian_establish"] * 0.15),
            run_time=BEATS["vitruvian_establish"] * 0.15,
        )

        # Figure draws in
        self.play(
            Create(vitruvian.figure, run_time=BEATS["vitruvian_establish"] * 0.25),
            run_time=BEATS["vitruvian_establish"] * 0.25,
        )

        # Golden line + phi formula ghost in
        self.play(
            FadeIn(vitruvian.golden_line, run_time=BEATS["vitruvian_establish"] * 0.1),
            FadeIn(vitruvian.phi_formula, run_time=BEATS["vitruvian_establish"] * 0.1),
            run_time=BEATS["vitruvian_establish"] * 0.1,
        )

        # Slow zoom out / drift
        self.play(
            vitruvian.group.animate(
                run_time=BEATS["vitruvian_establish"] * 0.15,
                rate_func=rate_functions.ease_in_out_sine,
            ).scale(0.92),
            run_time=BEATS["vitruvian_establish"] * 0.15,
        )

        # Fade to black
        self.play(
            vitruvian.group.animate(run_time=BEATS["vitruvian_fade"]).set_opacity(0),
            run_time=BEATS["vitruvian_fade"],
        )
        self.remove(vitruvian.group)

    # ------------------------------------------------------------------
    # 3. RUKUMINI LOGO SLAM — After the math scenery establishes mood
    # ------------------------------------------------------------------
    def rukumini_reveal(self):
        logo = safe_image_or_placeholder(
            RUKUMINI_LOGO_PATH, width=8.0, placeholder_text="RUKUMINI"
        )
        logo.move_to(ORIGIN)
        logo.scale(2.0)
        logo.set_opacity(0)

        # Multi-layer glow
        glow = _make_glow_ring(radius=2.8, color=RUKUMINI_RED, opacity=0.55)
        glow.set_opacity(0)

        # Ambient soft bloom
        ambient = Circle(
            radius=4.5,
            color=RUKUMINI_DARK_RED,
            stroke_width=0,
            fill_color=RUKUMINI_DARK_RED,
            fill_opacity=0,
        )

        logo_group = Group(ambient, glow, logo)
        self.add(logo_group)

        # IMPACT FLASH — brief white screen flash
        flash_rect = FullScreenRectangle(fill_color=RUKUMINI_WHITE, fill_opacity=0.12)
        self.add(flash_rect)

        # Logo slams in with bounce
        slam_time = BEATS["rukumini_slam"]
        self.play(
            logo.animate(run_time=slam_time, rate_func=rate_functions.ease_out_bounce)
            .scale(0.5)
            .set_opacity(1),
            glow.animate(run_time=slam_time, rate_func=rate_functions.ease_out_expo)
            .set_opacity(0.55)
            .scale(1.2),
            ambient.animate(
                run_time=slam_time * 1.2, rate_func=rate_functions.ease_out_quad
            ).set_fill(opacity=0.06),
            flash_rect.animate(run_time=slam_time * 0.3).set_fill(opacity=0),
            run_time=slam_time,
        )
        self.remove(flash_rect)

        # Cinematic shake
        self._cinematic_shake(logo_group, intensity=0.14, duration=0.32)

        # Breathing hold
        hold_time = BEATS["rukumini_hold"]
        for _ in range(3):
            self.play(
                logo.animate(
                    run_time=hold_time * 0.15, rate_func=rate_functions.ease_in_out_sine
                ).scale(1.012),
                glow.animate(
                    run_time=hold_time * 0.15, rate_func=rate_functions.ease_in_out_sine
                ).set_stroke_opacity(0.7),
                run_time=hold_time * 0.15,
            )
            self.play(
                logo.animate(
                    run_time=hold_time * 0.18, rate_func=rate_functions.ease_in_out_sine
                ).scale(1 / 1.012),
                glow.animate(
                    run_time=hold_time * 0.18, rate_func=rate_functions.ease_in_out_sine
                ).set_stroke_opacity(0.4),
                run_time=hold_time * 0.18,
            )

        self.rukumini_group = logo_group

    # ------------------------------------------------------------------
    # 4. COLLEGE REVEAL — Glitch transition
    # ------------------------------------------------------------------
    def college_reveal(self):
        college_logo = safe_image_or_placeholder(
            COLLEGE_LOGO_PATH,
            width=6.5,
            placeholder_text="COLLEGE",
            placeholder_color=ACCENT_GOLD,
        )
        college_logo.move_to(ORIGIN)
        college_logo.set_opacity(0)
        college_logo.scale(0.7)

        gold_glow = _make_glow_ring(radius=2.5, color=ACCENT_GOLD, opacity=0.45)
        gold_glow.set_opacity(0)

        # Glitch bars
        glitch_bars = VGroup()
        for _ in range(10):
            bar = Rectangle(
                width=random.uniform(2, 7),
                height=random.uniform(0.015, 0.06),
                color=ACCENT_GOLD,
                fill_color=ACCENT_GOLD,
                fill_opacity=random.uniform(0.3, 0.7),
                stroke_width=0,
            )
            bar.move_to([random.uniform(-3.5, 3.5), random.uniform(-2.5, 2.5), 0])
            bar.set_opacity(0)
            glitch_bars.add(bar)

        self.add(glitch_bars, gold_glow, college_logo)

        # GLITCH TRANSITION
        trans_time = BEATS["transition"]

        # RGB split on outgoing
        for dx in [0.14, -0.09, 0.06, -0.04]:
            self.play(
                self.rukumini_group.animate(run_time=0.07).shift(RIGHT * dx),
                run_time=0.07,
            )

        # Glitch bars flash
        self.play(
            *[
                bar.animate(run_time=trans_time * 0.25).set_opacity(
                    random.uniform(0.5, 0.85)
                )
                for bar in glitch_bars
            ],
            self.rukumini_group.animate(run_time=trans_time * 0.25).set_opacity(0.25),
            run_time=trans_time * 0.25,
        )

        # Crossfade
        self.play(
            FadeOut(self.rukumini_group, run_time=trans_time * 0.35),
            *[
                bar.animate(run_time=trans_time * 0.15).set_opacity(0)
                for bar in glitch_bars
            ],
            college_logo.animate(
                run_time=trans_time * 0.45, rate_func=rate_functions.ease_out_expo
            )
            .scale(1 / 0.7)
            .set_opacity(1),
            gold_glow.animate(
                run_time=trans_time * 0.45, rate_func=rate_functions.ease_out_expo
            )
            .set_opacity(0.45)
            .scale(1.12),
            run_time=trans_time * 0.45,
        )
        self.remove(self.rukumini_group, glitch_bars)

        # Reveal settle
        reveal_time = BEATS["college_reveal"]
        self.play(
            college_logo.animate(
                run_time=reveal_time * 0.5, rate_func=rate_functions.ease_out_back
            ),
            run_time=reveal_time * 0.5,
        )
        self.play(
            Rotate(college_logo, angle=0.015, rate_func=there_and_back, run_time=0.25),
            run_time=0.25,
        )

        # Hold
        hold_time = BEATS["college_hold"]
        for _ in range(3):
            self.play(
                gold_glow.animate(
                    run_time=hold_time * 0.12, rate_func=rate_functions.ease_in_out_sine
                ).set_stroke_opacity(0.65),
                run_time=hold_time * 0.12,
            )
            self.play(
                gold_glow.animate(
                    run_time=hold_time * 0.21, rate_func=rate_functions.ease_in_out_sine
                ).set_stroke_opacity(0.35),
                run_time=hold_time * 0.21,
            )

        # OUTRO
        outro_time = BEATS["outro"]
        burst = self._make_burst_particles(35, color=ACCENT_GOLD, spread=7)
        burst.set_opacity(0)
        self.add(burst)

        outro_vignette = _make_vignette(opacity=0, inner=1.5, outer=12)
        self.add(outro_vignette)

        self.play(
            burst.animate(
                run_time=outro_time * 0.45, rate_func=rate_functions.ease_out_expo
            )
            .set_opacity(random.uniform(0.5, 0.75))
            .scale(1.4),
            outro_vignette.animate(
                run_time=outro_time, rate_func=rate_functions.ease_in_quad
            ).set_fill(opacity=0.75),
            run_time=outro_time * 0.55,
        )

        # Final fade
        self.play(
            FadeOut(college_logo, run_time=BEATS["fade_out"] * 0.6),
            FadeOut(gold_glow, run_time=BEATS["fade_out"] * 0.6),
            FadeOut(burst, run_time=BEATS["fade_out"] * 0.4),
            FadeOut(outro_vignette, run_time=BEATS["fade_out"]),
            FadeOut(self.euler_bg, run_time=BEATS["fade_out"]),
            FadeOut(self.film_grain, run_time=BEATS["fade_out"]),
            FadeOut(self.scan_lines, run_time=BEATS["fade_out"]),
            FadeOut(self.vignette, run_time=BEATS["fade_out"]),
            run_time=BEATS["fade_out"],
        )

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def _cinematic_shake(self, target, intensity=0.12, duration=0.32):
        original = target.get_center().copy()
        steps = 6
        for i in range(steps):
            decay = 1 - (i / steps) ** 2
            offset = np.array(
                [
                    random.uniform(-intensity, intensity) * decay,
                    random.uniform(-intensity, intensity) * decay,
                    0,
                ]
            )
            self.play(
                target.animate(run_time=duration / steps).move_to(original + offset),
                run_time=duration / steps,
            )
        self.play(
            target.animate(run_time=duration / steps).move_to(original),
            run_time=duration / steps,
        )

    def _make_burst_particles(self, n=35, color=ACCENT_GOLD, spread=7):
        particles = VGroup()
        for _ in range(n):
            angle = random.uniform(0, TAU)
            speed = random.uniform(1.5, spread)
            start = ORIGIN + np.array(
                [random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), 0]
            )
            end = ORIGIN + np.array(
                [math.cos(angle) * speed, math.sin(angle) * speed, 0]
            )
            ptype = random.choice(["dot", "line", "square"])
            if ptype == "dot":
                p = Dot(
                    point=start,
                    radius=random.uniform(0.02, 0.05),
                    color=color,
                    fill_opacity=random.uniform(0.4, 0.85),
                )
            elif ptype == "line":
                p = Line(
                    start,
                    start
                    + np.array(
                        [
                            math.cos(angle) * random.uniform(0.3, 0.7),
                            math.sin(angle) * random.uniform(0.3, 0.7),
                            0,
                        ]
                    ),
                    stroke_width=random.uniform(1, 2.5),
                    stroke_opacity=random.uniform(0.3, 0.75),
                    color=color,
                )
            else:
                p = Square(
                    side_length=random.uniform(0.04, 0.09),
                    color=color,
                    fill_color=color,
                    fill_opacity=random.uniform(0.25, 0.6),
                    stroke_width=0,
                ).move_to(start)
            particles.add(p)
        return particles
