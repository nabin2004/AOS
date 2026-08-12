"""Autodiff / computational graph (d2l Ch 2.5)."""

from __future__ import annotations

from manim import DOWN, UP, Circle, Line, MathTex, Text, VGroup, WHITE

from manim_ai.compute import autodiff
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


def _node(label: str) -> VGroup:
    c = Circle(radius=0.35, color=DEFAULT_THEME.primary, fill_opacity=0.2)
    t = Text(label, font_size=18, color=WHITE)
    return VGroup(c, t)


@register_concept(
    id="autodiff_graph",
    domain="fundamental",
    chapter="2.5",
    title="Automatic Differentiation Graph",
    description="Simple forward graph for y = (a+b)*c with torch grads.",
    tags=["autodiff"],
)
def build_autodiff_graph(a: float = 2.0, b: float = 3.0, c: float = 4.0) -> VGroup:
    vals = autodiff.graph_abc(a=a, b=b, c=c)
    na = _node(f"a={vals['a']:g}")
    nb = _node(f"b={vals['b']:g}")
    nc = _node(f"c={vals['c']:g}")
    add = _node(f"+={vals['sum']:g}")
    mul = _node("×")
    y = _node(f"y={vals['y']:g}")
    na.move_to([-3.2, 0.9, 0])
    nb.move_to([-3.2, -0.9, 0])
    add.move_to([-1.2, 0, 0])
    nc.move_to([0.5, -1.2, 0])
    mul.move_to([1.5, 0, 0])
    y.move_to([3.2, 0, 0])
    edges = VGroup(
        Line(na.get_right(), add.get_left()),
        Line(nb.get_right(), add.get_left()),
        Line(add.get_right(), mul.get_left()),
        Line(nc.get_top(), mul.get_bottom()),
        Line(mul.get_right(), y.get_left()),
    )
    title = MathTex(r"y=(a+b)\cdot c", font_size=32)
    title.to_edge(UP)
    grads = MathTex(
        rf"\partial y/\partial a={vals['grad_a']:g},\ "
        rf"\partial y/\partial b={vals['grad_b']:g},\ "
        rf"\partial y/\partial c={vals['grad_c']:g}",
        font_size=24,
    )
    grads.next_to(title, DOWN, buff=0.25)
    return VGroup(title, grads, edges, na, nb, nc, add, mul, y)
