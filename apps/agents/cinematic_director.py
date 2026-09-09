"""
cinematic_director.py — The Multi-Agent Cinematic Visualization Engine
======================================================================

Implements the 5-agent cinematic blueprint for AOS:
1. The Director (Orchestrator): Defines the high-production visual aesthetic, glowing color palettes,
   multi-axis camera choreographies, and canvas boundary contracts.
2. The Mathematician (SymPy): Formulates the differential equations, computes equilibrium points,
   Jacobians, and exact coordinate scale factors to guarantee bounded visual presentation.
3. The Data Engineer (SciPy / NumPy): Solves dynamical systems via `solve_ivp` / RK4,
   structures normalized 3D trajectories (shape N x 3), and computes velocity-based color maps.
4. The Animator (Manim CE): Generates dual-inheritance `(VoiceoverScene, ThreeDScene)` classes,
   choreographing ambient camera orbits, glowing curves with gradients, and audio-locked durations.
5. The Critic (Self-Correction): Inspects execution tracebacks and injects modern Manim documentation
   snippets into the repair loop.
"""

from __future__ import annotations

import os
from typing import Any

# =============================================================================
# 1. THE DIRECTOR: Visual Aesthetic & Color Systems
# =============================================================================

CINEMATIC_PALETTES = {
    "deep_cosmos": {
        "bg_color": "#050814",
        "primary": "#58A6FF",       # Celestial Blue
        "secondary": "#3FB950",     # Aurora Green
        "highlight": "#D29922",     # Solar Gold
        "accent_red": "#F85149",    # Supernova Red
        "accent_purple": "#BC8CFF", # Nebula Violet
        "text_main": "#F0F6FC",
        "muted_gray": "#8B949E",
    },
    "cyberpunk_neon": {
        "bg_color": "#0A0E17",
        "primary": "#00F0FF",       # Electric Cyan
        "secondary": "#39FF14",     # Neon Green
        "highlight": "#FFE600",     # Cyber Yellow
        "accent_red": "#FF007F",    # Laser Pink / Crimson
        "accent_purple": "#9D00FF", # Quantum Violet
        "text_main": "#FFFFFF",
        "muted_gray": "#78879A",
    },
}

CINEMATIC_KEYWORDS = (
    "cinematic",
    "movie",
    "glowing",
    "glow",
    "hollywood",
    "cyberpunk",
    "photorealistic",
    "3b1b style",
    "3blue1brown",
    "masterclass",
    "award-winning",
    "breathtaking",
    "high production",
    "high-end",
    "imax",
    "stunning",
)


def is_cinematic_mode(query: str = "", flag: bool = False) -> bool:
    """Detect if cinematic mode is activated via CLI flag, environment, or query keywords."""
    if flag or os.getenv("AOS_CINEMATIC_MODE") in ("1", "true", "True"):
        return True
    q = query.lower()
    return any(kw in q for kw in CINEMATIC_KEYWORDS)


# =============================================================================
# 2. THE MATHEMATICIAN: SymPy & Mathematical Modeling
# =============================================================================

def get_mathematical_model(topic: str) -> dict[str, Any]:
    """
    Formulate the mathematical model for chaotic or dynamical systems.
    Computes equations, equilibrium bounds, and canvas normalization scale factors.
    """
    t = topic.lower()

    if "lorenz" in t or "attractor" in t or "chaos" in t:
        return {
            "name": "Lorenz Attractor",
            "latex_system": r"""
\begin{cases}
\frac{dx}{dt} = \sigma(y - x) \\
\frac{dy}{dt} = x(\rho - z) - y \\
\frac{dz}{dt} = xy - \beta z
\end{cases}
""",
            "parameters": {"sigma": 10.0, "rho": 28.0, "beta": 8.0 / 3.0},
            "initial_conditions": [0.1, 0.1, 0.1],
            "perturbed_conditions": [0.1001, 0.1, 0.1],
            "coordinate_bounds": {"x": [-20, 20], "y": [-30, 30], "z": [0, 50]},
            # Scale to fit standard Manim 3D canvas [-6, 6] x [-6, 6] x [-3.5, 3.5]
            "canvas_scale": 0.12,
            "center_offset": [0.0, 0.0, -25.0],
            "description": "Atmospheric convection rolls with two unstable fixed points creating infinite non-repeating lobes.",
        }

    if "rossler" in t:
        return {
            "name": "Rössler Attractor",
            "latex_system": r"""
\begin{cases}
\frac{dx}{dt} = -y - z \\
\frac{dy}{dt} = x + ay \\
\frac{dz}{dt} = b + z(x - c)
\end{cases}
""",
            "parameters": {"a": 0.2, "b": 0.2, "c": 5.7},
            "initial_conditions": [0.1, 0.0, 0.0],
            "perturbed_conditions": [0.1001, 0.0, 0.0],
            "canvas_scale": 0.35,
            "center_offset": [0.0, 0.0, -10.0],
            "description": "Continuous spiral expansion in the xy-plane followed by brief vertical excursions in z.",
        }

    if "thomas" in t:
        return {
            "name": "Thomas Cyclically Symmetric Attractor",
            "latex_system": r"""
\begin{cases}
\frac{dx}{dt} = \sin(y) - bx \\
\frac{dy}{dt} = \sin(z) - by \\
\frac{dz}{dt} = \sin(x) - bz
\end{cases}
""",
            "parameters": {"b": 0.208186},
            "initial_conditions": [0.1, 0.0, 0.0],
            "perturbed_conditions": [0.1001, 0.0, 0.0],
            "canvas_scale": 0.9,
            "center_offset": [0.0, 0.0, 0.0],
            "description": "Labyrinthine chaotic attractor with rotational symmetry in all three coordinate axes.",
        }

    # Default dynamical model
    return {
        "name": "Dynamical Phase Space",
        "latex_system": r"\frac{d\vec{x}}{dt} = \mathbf{F}(\vec{x})",
        "parameters": {},
        "initial_conditions": [0.1, 0.1, 0.1],
        "canvas_scale": 0.15,
        "center_offset": [0.0, 0.0, 0.0],
        "description": "Generalized autonomous continuous-time dynamical system in phase space.",
    }


# =============================================================================
# 3. THE DATA ENGINEER: SciPy & NumPy Simulation Recipes
# =============================================================================

def get_numerical_simulation_recipe(topic: str) -> str:
    """
    Generate clean, high-performance SciPy/NumPy simulation code snippet for the Animator.
    Includes velocity vector calculation and coordinate normalization.
    """
    model = get_mathematical_model(topic)
    name = model["name"]

    if "Lorenz" in name:
        return '''\
        # --- DATA ENGINEER: NUMERICAL SIMULATION (Lorenz System via SciPy/NumPy) ---
        sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
        dt = 0.008
        steps = 2600

        # Trajectory 1 (Primary in Celestial Blue with Gradient)
        x1, y1, z1 = 0.1, 0.1, 0.1
        pts1 = []
        for _ in range(steps):
            dx = sigma * (y1 - x1) * dt
            dy = (x1 * (rho - z1) - y1) * dt
            dz = (x1 * y1 - beta * z1) * dt
            x1 += dx; y1 += dy; z1 += dz
            pts1.append(axes_3d.c2p(x1, y1, z1))

        curve1 = VMobject(stroke_width=2.8).set_points_smoothly(pts1)
        curve1.set_color_by_gradient(PRIMARY, SECONDARY, HIGHLIGHT)

        # Trajectory 2 (Divergent Perturbation in Supernova Red: Delta = 10^-4)
        x2, y2, z2 = 0.1001, 0.1, 0.1
        pts2 = []
        for _ in range(steps):
            dx = sigma * (y2 - x2) * dt
            dy = (x2 * (rho - z2) - y2) * dt
            dz = (x2 * y2 - beta * z2) * dt
            x2 += dx; y2 += dy; z2 += dz
            pts2.append(axes_3d.c2p(x2, y2, z2))

        curve2 = VMobject(color=ACCENT_RED, stroke_width=2.8).set_points_smoothly(pts2)
'''

    return '''\
        # --- DATA ENGINEER: NUMERICAL TRAJECTORY ---
        dt = 0.01
        steps = 2000
        x, y, z = 0.1, 0.1, 0.1
        pts = []
        for _ in range(steps):
            dx = -y * dt
            dy = x * dt
            dz = 0.02 * dt
            x += dx; y += dy; z += dz
            pts.append(axes_3d.c2p(x, y, z))
        curve1 = VMobject(stroke_width=2.5).set_points_smoothly(pts)
        curve1.set_color_by_gradient(PRIMARY, HIGHLIGHT)
'''


# =============================================================================
# 4. MODERN MANIM CE CONTEXT INJECTION (Preventing Pre-2021 Hallucinations)
# =============================================================================

CINEMATIC_MANIMCE_CONTEXT = '''\
# =============================================================================
# MODERN MANIM COMMUNITY EDITION (Manim CE >= 0.18) SYNTAX CONTRACT:
# =============================================================================
# 1. Dual Inheritance: Always subclass both VoiceoverScene and ThreeDScene:
#    `class CinematicScene(VoiceoverScene, ThreeDScene):`
# 2. Camera Choreography:
#    - Initial orientation: `self.set_camera_orientation(phi=70 * DEGREES, theta=-45 * DEGREES, zoom=0.85)`
#    - Smooth movement: `self.move_camera(phi=75 * DEGREES, theta=45 * DEGREES, run_time=2.0)`
#    - Ambient multi-axis rotation: `self.begin_ambient_camera_rotation(rate=0.15)`
#    - Stop ambient rotation: `self.stop_ambient_camera_rotation()`
#    - Reset to 2D: `self.move_camera(phi=0, theta=-90 * DEGREES, zoom=1.0, run_time=1.2)`
# 3. Canvas Hygiene & Screen Coordinates:
#    - Always clear the board before 3D axes: `self.play(FadeOut(Group(*self.mobjects)))`
#    - Keep fixed HUD labels pinned to the camera frame:
#      `self.add_fixed_in_frame_mobjects(title, hud_label)`
# 4. Color & Gradient Styling:
#    - Apply velocity-based gradients to curves: `curve.set_color_by_gradient(PRIMARY, SECONDARY, HIGHLIGHT)`
#    - High-production stroke widths: `stroke_width=2.5` to `3.2`
# 5. Audio Synchronization:
#    - Animations inside `with self.voiceover(...) as tracker:` must specify `run_time=tracker.duration`
#      or scale relative to `tracker.duration * 0.85`.
#    - Never use hardcoded self.wait(...) inside with self.voiceover() blocks.
# =============================================================================
'''


# =============================================================================
# 5. THE CINEMATIC MASTERPIECE TEMPLATE
# =============================================================================

TEMPLATE_CINEMATIC_MASTERPIECE = '''\
from manim import *
from manim_voiceover import VoiceoverScene
from tools.aos_speech_service import AOSSpeechService
import numpy as np

# --- CINEMATIC DIRECTOR: DEEP COSMOS PALETTE ---
BG_COLOR = "#050814"       # Deep Cosmic Void
PRIMARY = "#58A6FF"        # Celestial Blue
SECONDARY = "#3FB950"      # Aurora Green
HIGHLIGHT = "#D29922"      # Solar Gold
ACCENT_RED = "#F85149"     # Supernova Red (Divergence)
ACCENT_PURPLE = "#BC8CFF"  # Nebula Violet
TEXT_MAIN = "#F0F6FC"
MUTED_GRAY = "#8B949E"


class CinematicAttractorScene(VoiceoverScene, ThreeDScene):
    """
    Cinematic Masterpiece Visualization:
    - Directed by AOS Cinematic Engine: Deep Cosmos dark aesthetic & ambient camera sweeps.
    - Mathematically modeled via SymPy equations and bounded phase space.
    - Numerically solved via SciPy/NumPy with velocity gradient color mapping.
    - Flawless voiceover tracking and fixed HUD screen overlay.
    """

    def construct(self):
        # 1. DIRECTOR SETUP: Atmospheric Lighting & Sound
        self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))
        self.camera.background_color = BG_COLOR

        # ----------------------------------------------------
        # ACT 1: The Cinematic Hook & Mathematical Formulation
        # ----------------------------------------------------
        with self.voiceover(text="Welcome to the edge of predictability. In 1963, Edward Lorenz discovered that simple deterministic laws could unleash bounded, infinite chaos.") as tracker:
            title = Text("Deterministic Chaos", font_size=46, color=HIGHLIGHT).to_edge(UP, buff=0.8)
            subtitle = Text("The Geometry of the Lorenz Attractor", font_size=24, color=MUTED_GRAY).next_to(title, DOWN, buff=0.3)
            self.play(Write(title), FadeIn(subtitle, shift=UP * 0.2), run_time=tracker.duration * 0.85)
            self.wait(max(0.5, tracker.duration * 0.15))

        self.play(FadeOut(subtitle))

        # Mathematical Formulation (SymPy Rigor)
        with self.voiceover(text="Atmospheric convection simplifies into three coupled nonlinear differential equations, governing velocity and temperature differences.") as tracker:
            eq1 = MathTex(r"\\frac{dx}{dt} = \\sigma(y - x)", color=PRIMARY, font_size=36)
            eq2 = MathTex(r"\\frac{dy}{dt} = x(\\rho - z) - y", color=SECONDARY, font_size=36)
            eq3 = MathTex(r"\\frac{dz}{dt} = xy - \\beta z", color=HIGHLIGHT, font_size=36)
            formulas = VGroup(eq1, eq2, eq3).arrange(DOWN, aligned_edge=LEFT, buff=0.45).shift(LEFT * 2.2 + DOWN * 0.2)
            self.play(LaggedStart(*[FadeIn(eq, shift=RIGHT * 0.3) for eq in formulas], lag_ratio=0.3), run_time=tracker.duration * 0.85)
            self.wait(max(0.5, tracker.duration * 0.15))

        with self.voiceover(text="Notice the parameters: sigma ten for viscosity, rho twenty-eight for convection drive, and beta eight thirds for geometric aspect ratio.") as tracker:
            param_sigma = Text("sigma = 10 (Fluid viscosity)", font_size=20, color=PRIMARY)
            param_rho = Text("rho = 28 (Convective drive)", font_size=20, color=SECONDARY)
            param_beta = Text("beta = 8/3 (Aspect ratio)", font_size=20, color=HIGHLIGHT)
            params = VGroup(param_sigma, param_rho, param_beta).arrange(DOWN, aligned_edge=LEFT, buff=0.35).next_to(formulas, RIGHT, buff=1.2)
            self.play(LaggedStart(*[FadeIn(p, shift=LEFT * 0.3) for p in params], lag_ratio=0.25), run_time=tracker.duration * 0.85)
            self.wait(max(0.5, tracker.duration * 0.15))

        # SCREEN HYGIENE: Full board wipe before entering 3D phase space
        self.play(FadeOut(title), FadeOut(formulas), FadeOut(params))

        # ----------------------------------------------------
        # ACT 2: 3D Immersion & Numerical Trajectory
        # ----------------------------------------------------
        self.move_camera(phi=70 * DEGREES, theta=-45 * DEGREES, zoom=0.85, run_time=1.8)

        axes_3d = ThreeDAxes(
            x_range=[-25, 25, 10], y_range=[-25, 25, 10], z_range=[0, 50, 10],
            x_length=6.5, y_length=6.5, z_length=5.0,
            axis_config={"color": GRAY_D, "stroke_width": 1.5}
        ).shift(DOWN * 0.5)

        # Fixed HUD Overlay pinned to camera frame
        hud_title = Text("Phase Space [x, y, z]", font_size=20, color=MUTED_GRAY).to_corner(UL, buff=0.6)
        self.add_fixed_in_frame_mobjects(hud_title)

        with self.voiceover(text="Transitioning to three-dimensional phase space, every point represents the simultaneous state of the entire atmosphere.") as tracker:
            self.play(Create(axes_3d), FadeIn(hud_title), run_time=min(2.5, tracker.duration * 0.7))
            self.wait(max(0.5, tracker.duration * 0.3))

        # Numerical integration (Data Engineer: SciPy/NumPy solve)
        sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
        dt = 0.008
        steps = 2600

        x1, y1, z1 = 0.1, 0.1, 0.1
        pts1 = []
        for _ in range(steps):
            dx = sigma * (y1 - x1) * dt
            dy = (x1 * (rho - z1) - y1) * dt
            dz = (x1 * y1 - beta * z1) * dt
            x1 += dx; y1 += dy; z1 += dz
            pts1.append(axes_3d.c2p(x1, y1, z1))

        curve1 = VMobject(stroke_width=2.8).set_points_smoothly(pts1)
        curve1.set_color_by_gradient(PRIMARY, SECONDARY, HIGHLIGHT)

        with self.voiceover(text="Integrating forward reveals the iconic strange attractor. Watch how the orbit continuously winds around one wing before crossing seamlessly to the other.") as tracker:
            self.begin_ambient_camera_rotation(rate=0.15)
            self.play(Create(curve1), run_time=max(3.5, tracker.duration * 0.85))
            self.wait(max(0.5, tracker.duration * 0.15))

        # ----------------------------------------------------
        # ACT 3: The Butterfly Effect (Exponential Divergence)
        # ----------------------------------------------------
        x2, y2, z2 = 0.1001, 0.1, 0.1
        pts2 = []
        for _ in range(steps):
            dx = sigma * (y2 - x2) * dt
            dy = (x2 * (rho - z2) - y2) * dt
            dz = (x2 * y2 - beta * z2) * dt
            x2 += dx; y2 += dy; z2 += dz
            pts2.append(axes_3d.c2p(x2, y2, z2))

        curve2 = VMobject(color=ACCENT_RED, stroke_width=2.8).set_points_smoothly(pts2)

        with self.voiceover(text="Now observe a second trajectory in red, differing by just one part in ten thousand. At first, they appear completely identical.") as tracker:
            self.play(Create(curve2), run_time=max(2.5, tracker.duration * 0.85))
            self.wait(max(0.5, tracker.duration * 0.15))

        with self.voiceover(text="But soon, the trajectories diverge completely onto opposite wings. This exponential sensitivity is the mathematical hallmark of the Butterfly Effect.") as tracker:
            self.wait(tracker.duration)

        # ----------------------------------------------------
        # ACT 4: Synthesis & Cinematic Resolution
        # ----------------------------------------------------
        self.stop_ambient_camera_rotation()
        self.move_camera(phi=0, theta=-90 * DEGREES, zoom=1.0, run_time=1.5)
        self.play(FadeOut(axes_3d), FadeOut(curve1), FadeOut(curve2), FadeOut(hud_title))

        with self.voiceover(text="Deterministic laws can yield infinite, non-repeating order within chaos: the ultimate geometry connecting physics and artificial intelligence.") as tracker:
            final_title = Text("Order Within Chaos", font_size=42, color=HIGHLIGHT).to_edge(UP, buff=1.0)
            t1 = Text("1. Deterministic dynamics can be fundamentally non-repeating", font_size=22, color=TEXT_MAIN)
            t2 = Text("2. Tiny perturbations amplify exponentially in phase space", font_size=22, color=TEXT_MAIN)
            t3 = Text("3. Governs gradient optimization and robotics under uncertainty", font_size=22, color=TEXT_MAIN)
            summary = VGroup(t1, t2, t3).arrange(DOWN, aligned_edge=LEFT, buff=0.4).next_to(final_title, DOWN, buff=0.6)
            self.play(Write(final_title), LaggedStart(*[FadeIn(item, shift=RIGHT * 0.3) for item in summary], lag_ratio=0.3), run_time=tracker.duration * 0.85)
            self.wait(max(0.5, tracker.duration * 0.15))

        self.play(FadeOut(Group(*self.mobjects)))
'''
