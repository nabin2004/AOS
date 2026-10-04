"""Trajectory, tracer dot, and dynamic divergence visual components."""

from __future__ import annotations

from typing import Any

from motiongram.sci.schema import VisualComponentSpec


def format_color(val: Any) -> str:
    """Format color string or variable name."""
    if isinstance(val, str):
        if val.startswith("#") or val.startswith('"') or val.startswith("'"):
            return val if (val.startswith('"') or val.startswith("'")) else f'"{val}"'
        # Check if Manim color constant (e.g. BLUE_E, YELLOW, TEAL_A)
        return val
    return f'"{str(val)}"'


class TrajectoryCodeGenerator:
    """Generates Manim Python code for trajectories, dots, and dynamic lines."""

    @staticmethod
    def generate_curve(spec: VisualComponentSpec, pts_var: str, axes_var: str) -> str:
        """Generate code for VMobject trajectory curve."""
        style = spec.style
        stroke_width = style.get("stroke_width", 2.5)
        opacity = style.get("opacity", 0.9)
        gradient = style.get("color_gradient", None)
        single_color = style.get("color", "BLUE")

        lines = [
            f"{spec.id} = VMobject(stroke_width={stroke_width}, stroke_opacity={opacity})",
            f"{spec.id}_pts = [{axes_var}.c2p(*p) for p in {pts_var}]",
            f"{spec.id}.set_points_as_corners({spec.id}_pts)",
        ]

        if gradient and isinstance(gradient, list) and len(gradient) > 1:
            grad_str = ", ".join(format_color(c) for c in gradient)
            lines.append(f"{spec.id}.set_color_by_gradient({grad_str})")
        else:
            lines.append(f"{spec.id}.set_color({format_color(single_color)})")

        return "\n        ".join(lines)

    @staticmethod
    def generate_tracer_dot(
        spec: VisualComponentSpec, pts_var: str, axes_var: str, is_3d: bool = True
    ) -> str:
        """Generate code for tracer dot (Dot3D or Dot)."""
        style = spec.style
        color = format_color(style.get("color", "YELLOW"))
        radius = style.get("radius", 0.12)
        dot_cls = "Dot3D" if is_3d else "Dot"

        return (
            f"{spec.id} = {dot_cls}(\n"
            f"            point={axes_var}.c2p(*{pts_var}[0]),\n"
            f"            radius={radius},\n"
            f"            color={color},\n"
            f"        )"
        )

    @staticmethod
    def generate_dynamic_line(spec: VisualComponentSpec) -> str:
        """Generate code for always_redraw dynamic divergence line connecting two dots."""
        style = spec.style
        color = format_color(style.get("color", "YELLOW"))
        stroke_width = style.get("stroke_width", 2.0)
        opacity = style.get("opacity", 0.65)
        from_dot = spec.from_dot
        to_dot = spec.to_dot

        return (
            f"{spec.id} = always_redraw(\n"
            f"            lambda: Line(\n"
            f"                {from_dot}.get_center(),\n"
            f"                {to_dot}.get_center(),\n"
            f"                stroke_width={stroke_width},\n"
            f"                color={color},\n"
            f"                stroke_opacity={opacity},\n"
            f"            )\n"
            f"        )"
        )

    @staticmethod
    def generate_vector_field(spec: VisualComponentSpec, axes_var: str, is_3d: bool = True) -> str:
        """Generate code for 3D or 2D vector field substrate."""
        style = spec.style
        opacity = style.get("opacity", 0.18)
        color = format_color(style.get("color", "BLUE"))
        if is_3d:
            return (
                f"# 3D Vector field substrate\n"
                f"        {spec.id} = VGroup(*[\n"
                f"            Line({axes_var}.c2p(x, y, z), {axes_var}.c2p(x + 1.2, y + 1.2, z + 1.2),\n"
                f"                 stroke_width=1.0, stroke_opacity={opacity}, color={color})\n"
                f"            for x in np.linspace(-25, 25, 4)\n"
                f"            for y in np.linspace(-25, 25, 4)\n"
                f"            for z in np.linspace(5, 45, 3)\n"
                f"        ])"
            )
        else:
            return (
                f"# 2D Vector field\n"
                f"        {spec.id} = ArrowVectorField(\n"
                f"            lambda p: np.array([p[1], 0, 0]),\n"
                f"            length_func=lambda norm: 0.4,\n"
                f"            opacity={opacity},\n"
                f"        )"
            )

    @staticmethod
    def generate_vector_arrow(spec: VisualComponentSpec, axes_var: str) -> str:
        """Generate code for 2D basis vector arrow."""
        style = spec.style
        color = format_color(style.get("color", "GREEN"))
        label = style.get("label", "")
        if "i_hat" in spec.id or "i" in label:
            end = f"{axes_var}.c2p(1, 0)"
        elif "j_hat" in spec.id or "j" in label:
            end = f"{axes_var}.c2p(0, 1)"
        else:
            end = f"{axes_var}.c2p(1, 1)"
        return f"{spec.id} = Arrow({axes_var}.c2p(0, 0), {end}, buff=0, color={color})"

    @staticmethod
    def generate_null_space(spec: VisualComponentSpec, axes_var: str) -> str:
        """Generate code for kernel null space dashed line."""
        style = spec.style
        color = format_color(style.get("color", "YELLOW"))
        return f"{spec.id} = DashedLine({axes_var}.c2p(-6, 3), {axes_var}.c2p(6, -3), color={color}, stroke_width=2.5)"

    @staticmethod
    def generate_paddle_wheel(spec: VisualComponentSpec, axes_var: str) -> str:
        """Generate code for microscopic circulation paddle wheel probe."""
        style = spec.style
        color = format_color(style.get("color", "BLUE"))
        radius = style.get("radius", 0.6)
        pos = spec.position if isinstance(spec.position, list) else [0, 1, 0]
        pos_str = f"{axes_var}.c2p({pos[0]}, {pos[1]})" if len(pos) >= 2 else "ORIGIN"
        return (
            f"{spec.id} = VGroup(\n"
            f"            Line(LEFT * {radius}, RIGHT * {radius}, color={color}, stroke_width=3),\n"
            f"            Line(UP * {radius}, DOWN * {radius}, color={color}, stroke_width=3),\n"
            f"            Dot(radius=0.08, color={color})\n"
            f"        ).move_to({pos_str})"
        )

    @staticmethod
    def generate_number_plane(spec: VisualComponentSpec, axes_var: str) -> str:
        """Generate code for NumberPlane visual."""
        style = spec.style
        opacity = style.get("opacity", 0.4)
        return f"{spec.id} = NumberPlane(background_line_style={{'stroke_opacity': {opacity}}})"
