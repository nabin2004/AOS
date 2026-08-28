from __future__ import annotations

from typing import Optional, List, Dict, Any
import numpy as np
import sympy as sp
import scipy.optimize as opt
from manim import (
    Axes,
    Dot,
    Line,
    MathTex,
    VGroup,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig, Cue, CueAction, apply_standard_cue


def compute_newton_steps(
    expression_str: str,
    x0: float,
    max_steps: int = 5,
    tol: float = 1e-6,
) -> Dict[str, Any]:
    """Generates step-by-step Newton-Raphson convergence data."""
    x = sp.Symbol('x')
    expr = sp.sympify(expression_str)
    diff_expr = sp.diff(expr, x)

    f = sp.lambdify(x, expr, modules=["numpy"])
    df = sp.lambdify(x, diff_expr, modules=["numpy"])

    steps: List[Dict[str, float]] = []
    curr_x = float(x0)

    for i in range(max_steps):
        curr_y = float(f(curr_x))
        curr_slope = float(df(curr_x))
        if abs(curr_slope) < 1e-12:
            break
        next_x = curr_x - curr_y / curr_slope
        steps.append({
            "step": i + 1,
            "x": curr_x,
            "y": curr_y,
            "slope": curr_slope,
            "next_x": next_x,
        })
        if abs(next_x - curr_x) < tol:
            curr_x = next_x
            break
        curr_x = next_x

    # Also compute exact / numerical root
    exact_root = float(curr_x)

    return {
        "expression": expression_str,
        "latex_expr": sp.latex(expr),
        "steps": steps,
        "root": exact_root,
        "f": f,
    }


class RootFindingVisualizer:
    """Generates Newton-Raphson step tangent lines and root convergence visuals."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_root_finding_mobjects(
        self,
        expression_str: str,
        x0: float,
        x_range: tuple[float, float, float] = (-1, 4, 1),
        y_range: tuple[float, float, float] = (-4, 8, 2),
        axes_width: float = 7.0,
        axes_height: float = 4.5,
    ) -> Dict[str, Any]:
        data = compute_newton_steps(expression_str, x0)
        t = self.theme

        axes = Axes(
            x_range=x_range,
            y_range=y_range,
            x_length=axes_width,
            y_length=axes_height,
            axis_config={"color": t.text_muted, "stroke_width": 2},
        )
        curve = axes.plot(data["f"], color=t.primary, stroke_width=3.5)

        step_lines = VGroup()
        step_dots = VGroup()

        for s in data["steps"]:
            # Point on curve (x_k, f(x_k))
            p_curve = axes.c2p(s["x"], s["y"])
            # Point on x-axis (x_{k+1}, 0)
            p_next = axes.c2p(s["next_x"], 0)
            # Vertical drop to x_axis
            p_axis = axes.c2p(s["x"], 0)

            dot_curve = Dot(p_curve, color=t.accent, radius=0.07)
            dot_axis = Dot(p_axis, color=t.highlight_a, radius=0.06)

            vert_line = Line(p_axis, p_curve, color=t.text_muted, stroke_width=1.5).set_opacity(0.6)
            tangent_line = Line(p_curve, p_next, color=t.accent_secondary, stroke_width=2.5)

            step_dots.add(dot_curve, dot_axis)
            step_lines.add(vert_line, tangent_line)

        # Root marker
        root_dot = Dot(axes.c2p(data["root"], 0), color=t.success, radius=0.09)

        tex_root = MathTex(
            rf"f(x) = {data['latex_expr']} = 0 \implies x^* \approx {data['root']:.5f}",
            color=t.text_main,
            font_size=24,
        ).next_to(axes, UP, aligned_edge=LEFT, buff=0.2)

        return {
            "axes": axes,
            "curve": curve,
            "step_lines": step_lines,
            "step_dots": step_dots,
            "root_dot": root_dot,
            "label": tex_root,
            "data": data,
        }

    def build_cueable_root_finding(
        self,
        expression_str: str,
        x0: float,
        x_range: tuple[float, float, float] = (-1, 4, 1),
        y_range: tuple[float, float, float] = (-4, 8, 2),
        axes_width: float = 7.0,
        axes_height: float = 4.5,
        show_all_steps: bool = True,
    ) -> "NewtonCueable":
        packed = self.build_root_finding_mobjects(
            expression_str,
            x0,
            x_range=x_range,
            y_range=y_range,
            axes_width=axes_width,
            axes_height=axes_height,
        )
        return NewtonCueable(packed, theme=self.theme, show_all_steps=show_all_steps)


class NewtonCueable(VGroup):
    """Newton diagram that can reveal the base plot, then each iteration."""

    def __init__(self, packed: Dict[str, Any], theme: Optional[ThemeConfig] = None, show_all_steps: bool = True, **kwargs) -> None:
        super().__init__(**kwargs)
        self.theme = theme or get_theme()
        self.data = packed.get("data") or {}
        self.base = VGroup(packed["axes"], packed["curve"])
        if packed.get("label") is not None:
            self.base.add(packed["label"])
        self.step_groups: List[VGroup] = []
        lines = packed.get("step_lines")
        dots = packed.get("step_dots")
        n_steps = len(self.data.get("steps") or [])
        if lines is not None and dots is not None and n_steps:
            # build_root_finding_mobjects adds 2 lines and 2 dots per step
            for i in range(n_steps):
                group = VGroup()
                li = i * 2
                if li < len(lines):
                    group.add(lines[li])
                if li + 1 < len(lines):
                    group.add(lines[li + 1])
                di = i * 2
                if di < len(dots):
                    group.add(dots[di])
                if di + 1 < len(dots):
                    group.add(dots[di + 1])
                self.step_groups.append(group)
        self.root_dot = packed.get("root_dot")
        self.add(self.base, *self.step_groups)
        if self.root_dot is not None:
            self.add(self.root_dot)
        if not show_all_steps:
            for g in self.step_groups:
                g.set_opacity(0)
            if self.root_dot is not None:
                self.root_dot.set_opacity(0)

    def cue_targets(self) -> Dict[str, Any]:
        targets: Dict[str, Any] = {"base": self.base}
        for i, g in enumerate(self.step_groups):
            targets[f"s{i}"] = g
        if self.root_dot is not None:
            targets["root"] = self.root_dot
        return targets

    def step_count(self) -> int:
        return len(self.step_groups)

    def apply_cue(self, scene: Any, cue: Cue) -> None:
        if cue.action == CueAction.REVEAL:
            apply_standard_cue(scene, cue, self.base, theme=self.theme)
            return
        if cue.action == CueAction.STEP:
            i = int((cue.payload or {}).get("i", 0))
            if 0 <= i < len(self.step_groups):
                apply_standard_cue(
                    scene,
                    Cue(mark=cue.mark, target_id=cue.target_id, action=CueAction.REVEAL),
                    self.step_groups[i],
                    theme=self.theme,
                )
            if i >= len(self.step_groups) - 1 and self.root_dot is not None:
                apply_standard_cue(
                    scene,
                    Cue(mark=cue.mark, target_id=cue.target_id, action=CueAction.REVEAL),
                    self.root_dot,
                    theme=self.theme,
                )
            return
        apply_standard_cue(scene, cue, self.base, theme=self.theme)
