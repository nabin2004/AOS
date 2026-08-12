"""Calculus / function concept builders."""

from __future__ import annotations

from manim import DOWN, DashedLine, Dot, MathTex, Rectangle, Text, VGroup, WHITE

from manim_math.compute import derivative_at, harmonic_oscillator, riemann_sum, sample_function
from manim_math.registry import register_concept
from manim_viz import DEFAULT_THEME, curve_from_samples, make_axes


@register_concept(
    id="function_plot",
    domain="math",
    chapter="2.1",
    title="Function Plot",
    tags=["calculus"],
)
def build_function_plot() -> VGroup:
    xs, ys = sample_function(lambda x: x**2 - 1, -2.5, 2.5)
    plot = curve_from_samples(xs, ys, x_range=(-3, 3, 1), y_range=(-2, 6, 1))
    title = Text("f(x)=x²−1", font_size=26, color=WHITE)
    return VGroup(title, plot).arrange(DOWN, buff=0.25)


@register_concept(
    id="derivative_tangent",
    domain="math",
    chapter="2.2",
    title="Derivative / Tangent",
    tags=["calculus"],
)
def build_derivative_tangent(x0: float = 1.0) -> VGroup:
    f = lambda x: x**2
    y0, slope = derivative_at(f, x0)
    xs, ys = sample_function(f, -1.5, 2.5)
    axes = make_axes(x_range=(-2, 3, 1), y_range=(-1, 6, 1))
    curve = axes.plot_line_graph(
        x_values=list(map(float, xs)),
        y_values=list(map(float, ys)),
        add_vertex_dots=False,
        line_color=DEFAULT_THEME.primary,
    )["line_graph"]
    point = Dot(axes.c2p(x0, y0), color=DEFAULT_THEME.highlight)
    x1, x2 = x0 - 0.8, x0 + 0.8
    tangent = DashedLine(
        axes.c2p(x1, y0 + slope * (x1 - x0)),
        axes.c2p(x2, y0 + slope * (x2 - x0)),
        color=DEFAULT_THEME.accent,
    )
    lab = MathTex(rf"f'({x0:g})={slope:g}", font_size=28)
    lab.next_to(axes, DOWN, buff=0.25)
    return VGroup(axes, curve, tangent, point, lab)


@register_concept(
    id="riemann_sum",
    domain="math",
    chapter="2.3",
    title="Riemann Sum",
    tags=["calculus", "integral"],
)
def build_riemann_sum(n: int = 6) -> VGroup:
    f = lambda x: 0.3 * x**2 + 0.5
    data = riemann_sum(f, 0.0, 3.0, n=n, method="mid")
    axes = make_axes(x_range=(-0.5, 3.5, 1), y_range=(0, 4, 1), scale=0.8)
    xs, ys = sample_function(f, 0.0, 3.0, n=100)
    curve = axes.plot_line_graph(
        x_values=list(map(float, xs)),
        y_values=list(map(float, ys)),
        add_vertex_dots=False,
        line_color=DEFAULT_THEME.primary,
    )["line_graph"]
    rects = VGroup()
    for x, h in zip(data["sample_x"], data["heights"]):
        # approximate rect width in axes coords
        left = float(x) - data["dx"] / 2
        right = float(x) + data["dx"] / 2
        p1 = axes.c2p(left, 0)
        p2 = axes.c2p(right, float(h))
        width = abs(p2[0] - p1[0])
        height = abs(p2[1] - p1[1])
        r = Rectangle(width=width, height=height, color=DEFAULT_THEME.secondary, fill_opacity=0.35)
        r.move_to(axes.c2p(float(x), float(h) / 2))
        rects.add(r)
    lab = MathTex(rf"\approx {data['area']:.3g}", font_size=28)
    lab.next_to(axes, DOWN, buff=0.2)
    title = Text("Midpoint Riemann sum", font_size=24, color=WHITE)
    return VGroup(title, axes, curve, rects, lab).arrange(DOWN, buff=0.15)


@register_concept(
    id="harmonic_oscillator_phase",
    domain="math",
    chapter="2.4",
    title="Harmonic Oscillator",
    tags=["ode", "calculus"],
)
def build_harmonic_oscillator_phase() -> VGroup:
    sol = harmonic_oscillator()
    plot = curve_from_samples(
        sol["t"],
        sol["x"],
        x_range=(0, 8, 2),
        y_range=(-1.5, 1.5, 1),
        color=DEFAULT_THEME.secondary,
    )
    title = Text("x(t) for x''=−ω²x (scipy)", font_size=24, color=WHITE)
    eq = MathTex(r"x''+\omega^2 x=0", font_size=28)
    return VGroup(title, plot, eq).arrange(DOWN, buff=0.2)
