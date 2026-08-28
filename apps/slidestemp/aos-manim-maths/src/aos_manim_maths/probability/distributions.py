from __future__ import annotations

from typing import Optional, Dict, Any
import numpy as np
import scipy.stats as stats
from manim import (
    Axes,
    MathTex,
    VGroup,
    Line,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig


class ProbabilityVisualizer:
    """Visualizes continuous probability distributions and confidence regions."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_normal_distribution_mobjects(
        self,
        mu: float = 0.0,
        sigma: float = 1.0,
        x_range: tuple[float, float, float] = (-4, 4, 1),
        axes_width: float = 7.5,
        axes_height: float = 4.0,
    ) -> Dict[str, Any]:
        t = self.theme
        dist = stats.norm(loc=mu, scale=sigma)
        max_y = float(dist.pdf(mu)) * 1.25

        axes = Axes(
            x_range=x_range,
            y_range=(0, max_y, max_y / 4),
            x_length=axes_width,
            y_length=axes_height,
            axis_config={"color": t.text_muted, "stroke_width": 2},
        )

        pdf_curve = axes.plot(lambda x: float(dist.pdf(x)), color=t.primary, stroke_width=3.5)

        # Shaded 1-sigma region (approx 68.27%)
        sigma1_area = axes.get_area(
            pdf_curve,
            x_range=(mu - sigma, mu + sigma),
            color=t.accent,
            opacity=0.35,
        )

        # Shaded 2-sigma region (approx 95.45%)
        sigma2_left = axes.get_area(
            pdf_curve,
            x_range=(mu - 2 * sigma, mu - sigma),
            color=t.accent_secondary,
            opacity=0.25,
        )
        sigma2_right = axes.get_area(
            pdf_curve,
            x_range=(mu + sigma, mu + 2 * sigma),
            color=t.accent_secondary,
            opacity=0.25,
        )

        # Mean center line
        mean_line = Line(
            axes.c2p(mu, 0),
            axes.c2p(mu, dist.pdf(mu)),
            color=t.highlight_a,
            stroke_width=2.5,
        )

        tex_label = MathTex(
            rf"\mathcal{{N}}(\mu = {mu}, \sigma = {sigma}), \quad P(\mu - \sigma \le X \le \mu + \sigma) \approx 68.3\%",
            color=t.text_main,
            font_size=24,
        ).next_to(axes, UP, aligned_edge=LEFT, buff=0.2)

        return {
            "axes": axes,
            "curve": pdf_curve,
            "sigma1_area": sigma1_area,
            "sigma2_areas": VGroup(sigma2_left, sigma2_right),
            "mean_line": mean_line,
            "label": tex_label,
        }
