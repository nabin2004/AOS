"""
video_templates.py — Production-Grade ManimCE Boilerplate Templates
===================================================================

Provides battle-tested, pedagogical templates for different target durations:
1. Micro-Lesson (1–2 minutes): High impact, single concept, hook -> math -> 3D payoff -> outro.
2. Standard Explainer (3–5 minutes): Dynamic ValueTracker + always_redraw, clean board transitions,
   3D phase space simulation with ambient camera rotation, particle updaters, and divergence.
3. Deep Dive Masterclass (10–15 minutes): Modular chapter architecture, deliberate cognitive pauses,
   split-screen comparisons, progressive complexity building, and multi-camera transitions.

Key design principles enforced:
- Dual Inheritance: (VoiceoverScene, ThreeDScene) for seamless 2D math + 3D camera sweeps.
- Precise Audio Sync: Animations tied directly to tracker.duration (no arbitrary hardcoded waits).
- Screen Hygiene: Explicitly clearing/FadeOut previous mobjects before new coordinate systems.
- Dynamic Updaters: State-driven animations with ValueTracker, always_redraw, and dt updaters.
"""

from __future__ import annotations

# =============================================================================
# Template 1: Micro-Lesson (1–2 Minutes)
# =============================================================================

TEMPLATE_MICRO_LESSON = '''\
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

# --- DESIGN PALETTE ---
BG_COLOR = "#0D1117"
PRIMARY = "#58A6FF"      # Blue
SECONDARY = "#3FB950"    # Green
HIGHLIGHT = "#D29922"    # Gold
TEXT_MAIN = "#F0F6FC"

class MicroLessonScene(VoiceoverScene, ThreeDScene):
    """
    Micro-Lesson (1–2 Minutes):
    High visual impact, fast hook, single core equation, immediate 3D visual payoff, clean exit.
    """
    def construct(self):
        # 1. SETUP
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))
        self.camera.background_color = BG_COLOR

        # 2. THE HOOK (Attention-grabbing visual question)
        with self.voiceover(text="Can the flap of a butterfly's wings in Brazil set off a tornado in Texas?") as tracker:
            hook_title = Text("The Butterfly Effect", font_size=44, color=HIGHLIGHT).to_edge(UP)
            question = Text("Deterministic Chaos in 3D Space", font_size=28, color=TEXT_MAIN).next_to(hook_title, DOWN, buff=0.4)
            self.play(Write(hook_title), run_time=tracker.duration * 0.45)
            self.play(FadeIn(question, shift=UP * 0.2), run_time=tracker.duration * 0.55)

        self.play(FadeOut(hook_title), FadeOut(question))

        # 3. CORE GOVERNING EQUATIONS (Clean 2D math)
        with self.voiceover(text="In 1963, Edward Lorenz simplified atmospheric convection into three coupled non-linear differential equations.") as tracker:
            eq1 = MathTex(r"\\frac{dx}{dt} = \\sigma(y - x)", color=PRIMARY)
            eq2 = MathTex(r"\\frac{dy}{dt} = x(\\rho - z) - y", color=SECONDARY)
            eq3 = MathTex(r"\\frac{dz}{dt} = xy - \\beta z", color=HIGHLIGHT)
            formulas = VGroup(eq1, eq2, eq3).arrange(DOWN, aligned_edge=LEFT, buff=0.5).scale(1.1)
            self.play(LaggedStart(*[FadeIn(eq, shift=UP * 0.2) for eq in formulas], lag_ratio=0.3), run_time=tracker.duration)

        with self.voiceover(text="These equations are completely deterministic, yet their long-term evolution is completely unpredictable.") as tracker:
            box = SurroundingRectangle(formulas, color=YELLOW, buff=0.3)
            self.play(Create(box), run_time=tracker.duration * 0.5)
            self.play(Indicate(formulas), run_time=tracker.duration * 0.5)

        # SCREEN HYGIENE: Completely clear board before introducing 3D phase space
        self.play(FadeOut(formulas), FadeOut(box))

        # 4. 3D VISUAL PAYOFF (Camera movement + Trajectory Simulation)
        self.move_camera(phi=70 * DEGREES, theta=-45 * DEGREES, run_time=1.5)
        axes_3d = ThreeDAxes(
            x_range=[-25, 25, 10], y_range=[-25, 25, 10], z_range=[0, 50, 10],
            x_length=6, y_length=6, z_length=5
        ).shift(DOWN * 0.5)

        with self.voiceover(text="Plotted in phase space, the trajectory orbits continuously around two unstable equilibrium points without ever intersecting.") as tracker:
            self.play(Create(axes_3d), run_time=min(2.0, tracker.duration * 0.3))
            
            # Numerical integration of Lorenz Attractor
            sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
            dt, x, y, z = 0.01, 0.1, 0.1, 0.1
            pts = []
            for _ in range(1600):
                dx = sigma * (y - x) * dt
                dy = (x * (rho - z) - y) * dt
                dz = (x * y - beta * z) * dt
                x, y, z = x + dx, y + dy, z + dz
                pts.append(axes_3d.c2p(x, y, z))
            
            curve = VMobject(color=PRIMARY, stroke_width=2.5).set_points_smoothly(pts)
            self.begin_ambient_camera_rotation(rate=0.15)
            self.play(Create(curve), run_time=max(2.0, tracker.duration - 2.0))

        # 5. OUTRO / SUMMARY
        self.stop_ambient_camera_rotation()
        self.move_camera(phi=0, theta=-90 * DEGREES, run_time=1.0)
        self.play(FadeOut(axes_3d), FadeOut(curve))

        with self.voiceover(text="This infinite non-repeating structure is a strange attractor: the hallmark of chaos.") as tracker:
            takeaway = Text("Order Within Chaos", font_size=42, color=HIGHLIGHT).to_edge(UP)
            summary = Text("Deterministic laws can yield bounded, non-repeating trajectories.", font_size=24, color=TEXT_MAIN).next_to(takeaway, DOWN, buff=0.4)
            self.play(Write(takeaway), Write(summary), run_time=tracker.duration)

        self.play(FadeOut(Group(*self.mobjects)))
'''

# =============================================================================
# Template 2: Standard Explainer (3–5 Minutes)
# =============================================================================

TEMPLATE_STANDARD_EXPLAINER = '''\
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

BG_COLOR = "#0D1117"
PRIMARY = "#58A6FF"
SECONDARY = "#3FB950"
HIGHLIGHT = "#D29922"
ACCENT_RED = "#F85149"
TEXT_MAIN = "#F0F6FC"

class StandardExplainerScene(VoiceoverScene, ThreeDScene):
    """
    Standard Explainer (3–5 Minutes):
    Combines 2D dynamic state management (ValueTracker + always_redraw), clean transition,
    3D phase space simulation, particle tracing, divergence demonstration, and key takeaway.
    """
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))
        self.camera.background_color = BG_COLOR

        # ----------------------------------------------------
        # ACT 1: 2D Foundations & Dynamic Updaters
        # ----------------------------------------------------
        with self.voiceover(text="Welcome to this visual exploration. Before entering chaos, let us examine how derivatives describe dynamic change.") as tracker:
            title = Text("Phase Space & Dynamical Systems", font_size=40, color=HIGHLIGHT).to_edge(UP)
            self.play(Write(title), run_time=tracker.duration * 0.8)
            self.wait(max(0.5, tracker.duration * 0.2))

        # State management via ValueTracker
        t_tracker = ValueTracker(-2.5)

        axes_2d = Axes(
            x_range=[-3, 3, 1], y_range=[-1, 9, 2],
            x_length=7, y_length=4.5,
            axis_config={"color": GRAY_C, "stroke_width": 2}
        ).to_edge(LEFT, buff=0.8)

        curve_2d = axes_2d.plot(lambda x: x**2, color=PRIMARY, x_range=[-2.8, 2.8])
        curve_lbl = axes_2d.get_graph_label(curve_2d, label=r"f(x) = x^2", x_val=2.2, direction=UR)

        # Dynamic point + tangent with always_redraw
        dot = always_redraw(
            lambda: Dot(point=axes_2d.c2p(t_tracker.get_value(), t_tracker.get_value()**2), color=HIGHLIGHT, radius=0.1)
        )
        tangent = always_redraw(
            lambda: axes_2d.get_tangent_line(t_tracker.get_value(), curve_2d, length=3.5, line_func=Line).set_color(SECONDARY)
        )
        slope_val = always_redraw(
            lambda: MathTex(rf"\\text{{Slope }} = {2 * t_tracker.get_value():.2f}", font_size=30, color=TEXT_MAIN).to_corner(UR, buff=1.0)
        )

        with self.voiceover(text="As the state x changes continuously, the tangent line reveals the instantaneous velocity vector governing the system.") as tracker:
            self.play(Create(axes_2d), Create(curve_2d), Write(curve_lbl), run_time=2.0)
            self.play(FadeIn(dot), Create(tangent), Write(slope_val), run_time=1.5)
            rem = max(1.0, tracker.duration - 3.5)
            self.play(t_tracker.animate.set_value(2.2), run_time=rem, rate_func=smooth)

        # SCREEN HYGIENE: Completely clear board before 3D transition
        self.play(FadeOut(Group(*self.mobjects)))

        # ----------------------------------------------------
        # ACT 2: 3D Lorenz System & Particle Orbit
        # ----------------------------------------------------
        self.move_camera(phi=70 * DEGREES, theta=-45 * DEGREES, zoom=0.85, run_time=1.5)

        axes_3d = ThreeDAxes(
            x_range=[-25, 25, 10], y_range=[-25, 25, 10], z_range=[0, 50, 10],
            x_length=6, y_length=6, z_length=5
        ).shift(DOWN * 0.5)

        with self.voiceover(text="In three-dimensional phase space, atmospheric dynamics are governed by three interacting variables: x, y, and z.") as tracker:
            self.play(Create(axes_3d), run_time=min(2.5, tracker.duration * 0.5))
            eqs = MathTex(
                r"\\begin{cases} \\dot{x} = \\sigma(y - x) \\\\ \\dot{y} = x(\\rho - z) - y \\\\ \\dot{z} = xy - \\beta z \\end{cases}",
                font_size=32, color=TEXT_MAIN
            ).to_corner(UL)
            self.add_fixed_in_frame_mobjects(eqs)
            self.play(Write(eqs), run_time=max(1.0, tracker.duration * 0.5))

        # Numerical integration for primary trajectory
        sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
        dt = 0.01
        x1, y1, z1 = 0.1, 0.1, 0.1
        pts1 = []
        for _ in range(2000):
            dx = sigma * (y1 - x1) * dt
            dy = (x1 * (rho - z1) - y1) * dt
            dz = (x1 * y1 - beta * z1) * dt
            x1, y1, z1 = x1 + dx, y1 + dy, z1 + dz
            pts1.append(axes_3d.c2p(x1, y1, z1))

        curve1 = VMobject(color=PRIMARY, stroke_width=2.5).set_points_smoothly(pts1)

        with self.voiceover(text="Integrating forward in time reveals the iconic butterfly attractor. Notice the smooth, continuous trajectory tracing both lobes.") as tracker:
            self.begin_ambient_camera_rotation(rate=0.15)
            self.play(Create(curve1), run_time=max(2.0, tracker.duration * 0.85))
            self.wait(max(0.5, tracker.duration * 0.15))

        # ----------------------------------------------------
        # ACT 3: Sensitive Dependence & Divergence (Chaos)
        # ----------------------------------------------------
        x2, y2, z2 = 0.1001, 0.1, 0.1  # Tiny perturbation: 1e-4
        pts2 = []
        for _ in range(2000):
            dx = sigma * (y2 - x2) * dt
            dy = (x2 * (rho - z2) - y2) * dt
            dz = (x2 * y2 - beta * z2) * dt
            x2, y2, z2 = x2 + dx, y2 + dy, z2 + dz
            pts2.append(axes_3d.c2p(x2, y2, z2))

        curve2 = VMobject(color=ACCENT_RED, stroke_width=2.5).set_points_smoothly(pts2)

        with self.voiceover(text="Now watch what happens when we start a second trajectory with a difference of just one ten-thousandth. Initially they overlap...") as tracker:
            self.play(Create(curve2), run_time=max(2.0, tracker.duration * 0.8))
            self.wait(max(0.5, tracker.duration * 0.2))

        with self.voiceover(text="...but soon they completely diverge into completely different lobes. This sensitive dependence is the definition of chaos.") as tracker:
            self.wait(tracker.duration)

        # ----------------------------------------------------
        # ACT 4: Synthesis & Clean Exit
        # ----------------------------------------------------
        self.stop_ambient_camera_rotation()
        self.move_camera(phi=0, theta=-90 * DEGREES, zoom=1.0, run_time=1.2)
        self.play(FadeOut(axes_3d), FadeOut(curve1), FadeOut(curve2), FadeOut(eqs))

        with self.voiceover(text="Understanding deterministic chaos empowers modern AI and control theory to handle uncertainty in complex dynamical worlds.") as tracker:
            final_title = Text("Deterministic Chaos", font_size=42, color=HIGHLIGHT).to_edge(UP)
            bullet1 = Text("1. Completely deterministic: zero randomness in equations", font_size=26, color=TEXT_MAIN)
            bullet2 = Text("2. Exponential sensitivity: initial differences amplify", font_size=26, color=TEXT_MAIN)
            bullet3 = Text("3. Bounded topology: infinite non-repeating attractor", font_size=26, color=TEXT_MAIN)
            bullets = VGroup(bullet1, bullet2, bullet3).arrange(DOWN, aligned_edge=LEFT, buff=0.4).next_to(final_title, DOWN, buff=0.6)
            self.play(Write(final_title), LaggedStart(*[FadeIn(b, shift=RIGHT * 0.3) for b in bullets], lag_ratio=0.3), run_time=tracker.duration)

        self.play(FadeOut(Group(*self.mobjects)))
'''

# =============================================================================
# Template 3: Deep Dive Masterclass (10–15 Minutes)
# =============================================================================

TEMPLATE_DEEP_DIVE_MASTERCLASS = '''\
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService

BG_COLOR = "#0D1117"
PRIMARY = "#58A6FF"
SECONDARY = "#3FB950"
HIGHLIGHT = "#D29922"
ACCENT_RED = "#F85149"
TEXT_MAIN = "#F0F6FC"
MUTED_GRAY = "#8B949E"

class DeepDiveMasterclassScene(VoiceoverScene, ThreeDScene):
    """
    Deep Dive Masterclass (10–15 Minutes):
    Structured into modular class methods (chapters). Employs deliberate cognitive pauses,
    progressive complexity building, multi-angle camera sweeps, and full pedagogical depth.
    """
    def construct(self):
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))
        self.camera.background_color = BG_COLOR

        # Long-form lectures must be modularized into distinct chapters
        self.chapter_1_introduction()
        self.chapter_2_governing_dynamics()
        self.chapter_3_phase_space_simulation()
        self.chapter_4_divergence_and_lyapunov()
        self.chapter_5_modern_ai_applications()

    def chapter_1_introduction(self):
        with self.voiceover(text="Welcome to this masterclass on deterministic chaos and nonlinear dynamical systems.") as tracker:
            title = Text("Deterministic Chaos", font_size=52, color=HIGHLIGHT).to_edge(UP, buff=1.0)
            subtitle = Text("Order, Geometry, and Predictability Limits in Science and AI", font_size=26, color=MUTED_GRAY).next_to(title, DOWN, buff=0.4)
            self.play(Write(title), FadeIn(subtitle, shift=UP * 0.2), run_time=tracker.duration * 0.8)
            self.wait(max(0.5, tracker.duration * 0.2))

        with self.voiceover(text="For centuries, classical physics believed that knowing exact initial conditions guaranteed complete prediction of the future.") as tracker:
            laplace_quote = Text(r'"We may regard the present state of the universe as the effect of its past."', font_size=24, slant=ITALIC, color=TEXT_MAIN)
            self.play(FadeIn(laplace_quote), run_time=tracker.duration)

        with self.voiceover(text="However, in complex nonlinear systems, this deterministic dream breaks down completely.") as tracker:
            cross_out = Line(LEFT * 4, RIGHT * 4, color=ACCENT_RED, stroke_width=4).move_to(laplace_quote)
            self.play(Create(cross_out), run_time=tracker.duration * 0.7)
            self.wait(max(0.5, tracker.duration * 0.3))

        self.play(FadeOut(title), FadeOut(subtitle), FadeOut(laplace_quote), FadeOut(cross_out))

    def chapter_2_governing_dynamics(self):
        with self.voiceover(text="Let us begin with the mathematical formulation. The Lorenz system consists of three coupled ordinary differential equations.") as tracker:
            chap_title = Text("Chapter 1: The Governing Equations", font_size=32, color=PRIMARY).to_corner(UL)
            eq_dx = MathTex(r"\\frac{dx}{dt} = \\sigma(y - x)", font_size=38, color=PRIMARY)
            eq_dy = MathTex(r"\\frac{dy}{dt} = x(\\rho - z) - y", font_size=38, color=SECONDARY)
            eq_dz = MathTex(r"\\frac{dz}{dt} = xy - \\beta z", font_size=38, color=HIGHLIGHT)
            eqs = VGroup(eq_dx, eq_dy, eq_dz).arrange(DOWN, aligned_edge=LEFT, buff=0.6).center()
            self.play(Write(chap_title), run_time=1.0)
            self.play(LaggedStart(*[FadeIn(eq, shift=UP * 0.3) for eq in eqs], lag_ratio=0.35), run_time=tracker.duration - 1.0)

        with self.voiceover(text="Notice the parameters: sigma represents the Prandtl number, rho represents the Rayleigh number, and beta is the geometric factor.") as tracker:
            params = VGroup(
                Text("sigma = 10 (Fluid viscosity)", font_size=22, color=PRIMARY),
                Text("rho = 28 (Convective heat drive)", font_size=22, color=SECONDARY),
                Text("beta = 8/3 (Physical aspect ratio)", font_size=22, color=HIGHLIGHT),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.3).to_edge(RIGHT, buff=0.8)
            self.play(FadeIn(params, shift=LEFT * 0.3), run_time=tracker.duration)

        with self.voiceover(text="Crucially, the terms x times z and x times y are nonlinear. This nonlinearity prevents closed-form analytical solutions.") as tracker:
            nonlin_box = SurroundingRectangle(VGroup(eq_dy[0][6:8], eq_dz[0][6:8]), color=YELLOW, buff=0.15)
            self.play(Create(nonlin_box), run_time=tracker.duration * 0.6)
            self.wait(max(0.5, tracker.duration * 0.4))

        self.play(FadeOut(chap_title), FadeOut(eqs), FadeOut(params), FadeOut(nonlin_box))

    def chapter_3_phase_space_simulation(self):
        # 3D Phase Space Exploration
        self.move_camera(phi=65 * DEGREES, theta=-55 * DEGREES, zoom=0.85, run_time=2.0)
        axes = ThreeDAxes(
            x_range=[-25, 25, 10], y_range=[-25, 25, 10], z_range=[0, 50, 10],
            x_length=6.5, y_length=6.5, z_length=5.0
        ).shift(DOWN * 0.5)

        with self.voiceover(text="Because the system has three state variables, we represent its complete state as a single trajectory in 3D phase space.") as tracker:
            self.play(Create(axes), run_time=min(2.5, tracker.duration * 0.5))
            self.wait(max(0.5, tracker.duration * 0.5))

        # Integrate primary trajectory
        sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
        dt = 0.008
        x, y, z = 0.1, 0.1, 0.1
        pts = []
        for _ in range(2400):
            dx = sigma * (y - x) * dt
            dy = (x * (rho - z) - y) * dt
            dz = (x * y - beta * z) * dt
            x, y, z = x + dx, y + dy, z + dz
            pts.append(axes.c2p(x, y, z))

        curve = VMobject(color=PRIMARY, stroke_width=2.2).set_points_smoothly(pts)

        with self.voiceover(text="Watch as the point traces out the attractor. It spirals outward on one wing, crosses through the center, and spirals on the other.") as tracker:
            self.begin_ambient_camera_rotation(rate=0.12)
            self.play(Create(curve), run_time=max(3.0, tracker.duration * 0.85))
            self.wait(max(0.5, tracker.duration * 0.15))

        # Cognitive Breathing Room: Silent camera rotation to allow visual digestion
        self.move_camera(phi=75 * DEGREES, theta=25 * DEGREES, run_time=3.0)

        with self.voiceover(text="The trajectory is strictly bounded within a finite volume, yet it never intersects itself and never repeats an exact cycle.") as tracker:
            self.wait(tracker.duration)

        self.stop_ambient_camera_rotation()
        self.axes_ref = axes
        self.curve_ref = curve

    def chapter_4_divergence_and_lyapunov(self):
        axes = self.axes_ref
        curve = self.curve_ref

        with self.voiceover(text="The defining signature of chaos is sensitive dependence on initial conditions, quantified by positive Lyapunov exponents.") as tracker:
            lyap_text = Text("Sensitive Dependence: |delta x(t)| ~ e^(lambda t)", font_size=28, color=HIGHLIGHT).to_corner(UL)
            self.add_fixed_in_frame_mobjects(lyap_text)
            self.play(Write(lyap_text), run_time=tracker.duration * 0.7)
            self.wait(max(0.5, tracker.duration * 0.3))

        # Second nearby trajectory
        sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
        dt = 0.008
        x2, y2, z2 = 0.10001, 0.1, 0.1
        pts2 = []
        for _ in range(2400):
            dx = sigma * (y2 - x2) * dt
            dy = (x2 * (rho - z2) - y2) * dt
            dz = (x2 * y2 - beta * z2) * dt
            x2, y2, z2 = x2 + dx, y2 + dy, z2 + dz
            pts2.append(axes.c2p(x2, y2, z2))

        curve2 = VMobject(color=ACCENT_RED, stroke_width=2.2).set_points_smoothly(pts2)

        with self.voiceover(text="Here, the red trajectory starts with a difference of just ten parts per million. Notice how rapidly the two curves diverge.") as tracker:
            self.begin_ambient_camera_rotation(rate=0.15)
            self.play(Create(curve2), run_time=max(2.5, tracker.duration * 0.8))
            self.wait(max(0.5, tracker.duration * 0.2))

        self.stop_ambient_camera_rotation()
        self.move_camera(phi=0, theta=-90 * DEGREES, zoom=1.0, run_time=1.5)
        self.play(FadeOut(axes), FadeOut(curve), FadeOut(curve2), FadeOut(lyap_text))

    def chapter_5_modern_ai_applications(self):
        with self.voiceover(text="Today, chaos theory directly impacts modern machine learning and physical artificial intelligence.") as tracker:
            title = Text("Chaos in Modern Artificial Intelligence", font_size=40, color=HIGHLIGHT).to_edge(UP)
            self.play(Write(title), run_time=tracker.duration * 0.7)
            self.wait(max(0.5, tracker.duration * 0.3))

        with self.voiceover(text="Recurrent neural networks, gradient optimization landscapes, and reinforcement learning control policies all encounter chaotic dynamics.") as tracker:
            grid = VGroup(
                VGroup(Text("Recurrent Dynamics", font_size=24, color=PRIMARY), Text("Vanishing & exploding gradients in phase space", font_size=18, color=MUTED_GRAY)).arrange(DOWN, aligned_edge=LEFT),
                VGroup(Text("Loss Landscapes", font_size=24, color=SECONDARY), Text("Complex non-convex topology and saddle transitions", font_size=18, color=MUTED_GRAY)).arrange(DOWN, aligned_edge=LEFT),
                VGroup(Text("Robust Control", font_size=24, color=HIGHLIGHT), Text("Bypassing butterfly effects in physical robotics", font_size=18, color=MUTED_GRAY)).arrange(DOWN, aligned_edge=LEFT),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.5).shift(LEFT * 1.5)
            self.play(LaggedStart(*[FadeIn(item, shift=RIGHT * 0.4) for item in grid], lag_ratio=0.3), run_time=tracker.duration)

        with self.voiceover(text="By mastering deterministic chaos, we build architectures that are truly resilient in an uncertain world. Thank you for watching.") as tracker:
            conclusion_box = SurroundingRectangle(grid, color=PRIMARY, buff=0.3)
            self.play(Create(conclusion_box), run_time=tracker.duration * 0.5)
            self.wait(max(0.5, tracker.duration * 0.5))

        self.play(FadeOut(Group(*self.mobjects)))
'''


# =============================================================================
# Helper function to get duration-matched boilerplate
# =============================================================================

def get_template_for_duration(length: str) -> str:
    """Return the ideal ManimCE boilerplate template based on target duration."""
    l = (length or "").lower().strip()
    if l in ("short", "1m", "2m", "1min", "2min", "1", "2"):
        return TEMPLATE_MICRO_LESSON
    if l in ("long", "10m", "15m", "10min", "15min", "10", "15"):
        return TEMPLATE_DEEP_DIVE_MASTERCLASS
    # Default to 3–5 minute standard explainer
    return TEMPLATE_STANDARD_EXPLAINER
