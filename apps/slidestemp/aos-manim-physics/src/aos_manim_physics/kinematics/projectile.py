from __future__ import annotations

from typing import Optional, Dict, Any
import numpy as np
from manim import (
    Axes,
    Dot,
    Arrow,
    DashedLine,
    MathTex,
    VGroup,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig


def compute_projectile_data(
    v0: float,
    theta_deg: float,
    g: float = 9.81,
) -> Dict[str, Any]:
    """Computes exact kinematic metrics for ideal projectile motion."""
    theta_rad = np.radians(theta_deg)
    vx = v0 * np.cos(theta_rad)
    vy = v0 * np.sin(theta_rad)

    flight_time = (2.0 * vy) / g
    max_height = (vy ** 2) / (2.0 * g)
    total_range = (v0 ** 2 * np.sin(2.0 * theta_rad)) / g

    def trajectory(x: float | np.ndarray):
        return x * np.tan(theta_rad) - (g * x**2) / (2.0 * v0**2 * np.cos(theta_rad)**2)

    return {
        "v0": v0,
        "theta_deg": theta_deg,
        "theta_rad": theta_rad,
        "vx": vx,
        "vy": vy,
        "g": g,
        "flight_time": flight_time,
        "max_height": max_height,
        "total_range": total_range,
        "trajectory_func": trajectory,
    }


class ProjectileVisualizer:
    """Creates projectile trajectory, launch vector, and peak/range annotation mobjects."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_projectile_mobjects(
        self,
        v0: float = 20.0,
        theta_deg: float = 45.0,
        g: float = 9.81,
        axes_width: float = 8.0,
        axes_height: float = 4.5,
    ) -> Dict[str, Any]:
        data = compute_projectile_data(v0, theta_deg, g)
        t = self.theme

        x_max = data["total_range"] * 1.15
        y_max = data["max_height"] * 1.35

        axes = Axes(
            x_range=(0, x_max, x_max / 5),
            y_range=(0, y_max, y_max / 4),
            x_length=axes_width,
            y_length=axes_height,
            axis_config={"color": t.text_muted, "stroke_width": 2},
        )

        curve = axes.plot(
            data["trajectory_func"],
            x_range=(0, data["total_range"]),
            color=t.primary,
            stroke_width=3.5,
        )

        # Launch arrow
        p_origin = axes.c2p(0, 0)
        p_v0 = axes.c2p(data["vx"] * (x_max / 100), data["vy"] * (y_max / 100))
        launch_vec = Arrow(p_origin, p_v0, buff=0, color=t.accent, stroke_width=3.5)

        # Peak height marker
        p_peak = axes.c2p(data["total_range"] / 2.0, data["max_height"])
        peak_dot = Dot(p_peak, color=t.highlight_a, radius=0.08)

        # Land marker
        p_land = axes.c2p(data["total_range"], 0)
        land_dot = Dot(p_land, color=t.success, radius=0.08)

        tex_meta = MathTex(
            rf"v_0 = {v0:.1f} \, \text{{m/s}}, \quad \theta = {theta_deg}^\circ \implies R = {data['total_range']:.1f} \, \text{{m}}, \quad H = {data['max_height']:.1f} \, \text{{m}}",
            color=t.text_main,
            font_size=24,
        ).next_to(axes, UP, aligned_edge=LEFT, buff=0.2)

        return {
            "axes": axes,
            "curve": curve,
            "launch_vector": launch_vec,
            "peak_dot": peak_dot,
            "land_dot": land_dot,
            "label": tex_meta,
            "data": data,
        }
