"""Learning rate schedules (d2l Ch 12.11)."""

from __future__ import annotations

from manim import DOWN, Axes, Text, VGroup, WHITE

from manim_ai.compute import schedules as sched_ops
from manim_ai.core.registry import register_concept
from manim_ai.core.theme import DEFAULT_THEME


@register_concept(
    id="lr_schedules",
    domain="optimization",
    chapter="12.11",
    title="Learning Rate Schedules",
    tags=["optimization"],
)
def build_lr_schedules() -> VGroup:
    curves = sched_ops.schedule_curves(n=100)
    axes = Axes(x_range=[0, 100, 20], y_range=[0, 0.012, 0.004], x_length=6.5, y_length=3).scale(0.8)
    colors = {
        "constant": DEFAULT_THEME.primary,
        "step": DEFAULT_THEME.secondary,
        "cosine": DEFAULT_THEME.attention,
    }
    plots = []
    for name, (t, y) in curves.items():
        plots.append(
            axes.plot_line_graph(
                x_values=[float(x) for x in t],
                y_values=[float(v) for v in y],
                add_vertex_dots=False,
                line_color=colors[name],
            )["line_graph"]
        )
    title = Text("LR schedules: constant / step / cosine", font_size=24, color=WHITE)
    return VGroup(title, axes, *plots).arrange(DOWN, buff=0.2)
