from __future__ import annotations

from typing import Optional, Dict, Any
import numpy as np
from scipy.integrate import solve_ivp
from manim import (
    VGroup,
    Dot,
    Line,
    MathTex,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    ORIGIN,
)
from aos_manim_core import get_theme, ThemeConfig


def simulate_pendulum(
    length: float = 2.5,
    theta0_deg: float = 30.0,
    g: float = 9.81,
    t_span: tuple[float, float] = (0, 10),
    num_points: int = 300,
) -> Dict[str, Any]:
    """Solves the exact nonlinear pendulum ODE."""
    theta0_rad = np.radians(theta0_deg)

    def ode(t, y):
        theta, omega = y
        dtheta_dt = omega
        domega_dt = -(g / length) * np.sin(theta)
        return [dtheta_dt, domega_dt]

    t_eval = np.linspace(t_span[0], t_span[1], num_points)
    sol = solve_ivp(ode, t_span, [theta0_rad, 0.0], t_eval=t_eval, rtol=1e-8, atol=1e-8)

    thetas = sol.y[0]
    omegas = sol.y[1]

    # Total energy conservation E = 1/2 m L^2 omega^2 + m g L (1 - cos(theta)) (per unit mass)
    energies = 0.5 * (length**2) * (omegas**2) + g * length * (1.0 - np.cos(thetas))

    return {
        "t": sol.t,
        "theta": thetas,
        "omega": omegas,
        "energy": energies,
        "length": length,
        "g": g,
    }


class PendulumVisualizer:
    """Visualizes physical pendulum state with pivot, rod, and bob."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_pendulum_mobjects(
        self,
        length: float = 2.5,
        theta0_deg: float = 30.0,
        pivot_pos: list[float] = [0, 2.0, 0],
    ) -> Dict[str, Any]:
        sim = simulate_pendulum(length=length, theta0_deg=theta0_deg)
        t = self.theme

        pivot = Dot(pivot_pos, color=t.text_muted, radius=0.08)
        theta_rad = np.radians(theta0_deg)

        bob_pos = [
            pivot_pos[0] + length * np.sin(theta_rad),
            pivot_pos[1] - length * np.cos(theta_rad),
            0,
        ]
        rod = Line(pivot_pos, bob_pos, color=t.border, stroke_width=3.0)
        bob = Dot(bob_pos, color=t.accent, radius=0.18)

        tex = MathTex(
            rf"\ddot{{\theta}} + \frac{{g}}{{L}}\sin\theta = 0, \quad \theta_0 = {theta0_deg}^\circ",
            color=t.text_main,
            font_size=24,
        ).to_corner(UP + LEFT)

        return {
            "pivot": pivot,
            "rod": rod,
            "bob": bob,
            "label": tex,
            "simulation": sim,
        }
