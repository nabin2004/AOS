"""Inset graph visual component for plotting metrics in 3D/2D scenes."""

from __future__ import annotations

from motiongram.sci.schema import VisualComponentSpec


class InsetCodeGenerator:
    """Generates Manim Python code for fixed-in-frame 2D inset metric graphs."""

    @staticmethod
    def generate_inset_graph(
        spec: VisualComponentSpec, pts_var: str, is_3d: bool = True
    ) -> str:
        """Generate code for a high-quality inset graph with log-scale support."""
        pos = spec.position.upper() if isinstance(spec.position, str) else "UR"
        width = spec.width
        height = spec.height
        use_log = spec.y_scale == "log"
        log_flag = "log" if use_log else "linear"

        lines = [
            f"# ── Inset graph: {spec.id} ({log_flag} scale) ──",
            f"_raw_{spec.id} = [p for p in {pts_var} if len(p) >= 2]",
            f"_t_vals = [p[0] for p in _raw_{spec.id}] if _raw_{spec.id} else [1.0]",
            f"_y_vals = [p[1] for p in _raw_{spec.id}] if _raw_{spec.id} else [1.0]",
            f"_{spec.id}_t_max = max(_t_vals) if _t_vals else 1.0",
        ]

        if use_log:
            # For log scale: transform y to log10(max(y, eps))
            lines += [
                f"_eps_{spec.id} = 1e-10",
                f"_y_log = [np.log10(max(v, _eps_{spec.id})) for v in _y_vals]",
                f"_{spec.id}_y_min = min(_y_log)",
                f"_{spec.id}_y_max = max(_y_log) + 0.5",  # headroom
                f"_{spec.id}_y_tick = max(1.0, round((_{spec.id}_y_max - _{spec.id}_y_min) / 4, 1))",
                f"{spec.id}_axes = Axes(",
                f"    x_range=[0, _{spec.id}_t_max, max(_{spec.id}_t_max / 5, 0.1)],",
                f"    y_range=[_{spec.id}_y_min, _{spec.id}_y_max, _{spec.id}_y_tick],",
                f"    x_length={width},",
                f"    y_length={height},",
                "    axis_config={'font_size': 14, 'stroke_width': 1.2, 'color': WHITE},",
                "    x_axis_config={'numbers_to_include': None},",
                "    y_axis_config={'numbers_to_include': None},",
                ")",
            ]
        else:
            lines += [
                f"_{spec.id}_y_max = max(max(_y_vals), 1.0) * 1.05",
                f"_{spec.id}_y_tick = max(round(_{spec.id}_y_max / 4, 2), 0.01)",
                f"{spec.id}_axes = Axes(",
                f"    x_range=[0, _{spec.id}_t_max, max(_{spec.id}_t_max / 5, 0.1)],",
                f"    y_range=[0, _{spec.id}_y_max, _{spec.id}_y_tick],",
                f"    x_length={width},",
                f"    y_length={height},",
                "    axis_config={'font_size': 14, 'stroke_width': 1.2, 'color': WHITE},",
                ")",
            ]

        # Position the axes in the corner
        lines.append(f"{spec.id}_axes.to_corner({pos}, buff=0.35)")

        # Semi-transparent background rectangle
        lines += [
            (
                f"{spec.id}_bg = BackgroundRectangle("
                f"{spec.id}_axes, color=BLACK, fill_opacity=0.72, buff=0.25)"
            ),
        ]

        # Axis labels — pre-compute ylabel text to avoid backslash in f-string
        ylabel_text = "log10(|d|)" if use_log else "d"
        lines += [
            f"{spec.id}_xlabel = {spec.id}_axes.get_x_axis_label(",
            f"    Text('t', font_size=12, color=GREY_A),",
            f"    direction=RIGHT, buff=0.05",
            f")",
            f"{spec.id}_ylabel = {spec.id}_axes.get_y_axis_label(",
            f"    Text('{ylabel_text}', font_size=12, color=GREY_A),",
            f"    direction=UP, buff=0.05",
            f")",
        ]

        # Curve with gradient coloring (viridis-style: purple→yellow)
        if use_log:
            lines += [
                f"{spec.id}_curve = VMobject(stroke_width=2.2)",
                f"{spec.id}_pts_2d = [{spec.id}_axes.c2p(p[0], np.log10(max(p[1], 1e-10))) for p in _raw_{spec.id} if p[0] <= _{spec.id}_t_max]",
                f"if len({spec.id}_pts_2d) > 1: {spec.id}_curve.set_points_as_corners({spec.id}_pts_2d)",
                f"{spec.id}_curve.set_color_by_gradient('#440154', '#21908c', '#fde725')",
            ]
        else:
            lines += [
                f"{spec.id}_curve = VMobject(stroke_width=2.2)",
                f"{spec.id}_pts_2d = [{spec.id}_axes.c2p(p[0], p[1]) for p in _raw_{spec.id} if p[0] <= _{spec.id}_t_max]",
                f"if len({spec.id}_pts_2d) > 1: {spec.id}_curve.set_points_as_corners({spec.id}_pts_2d)",
                f"{spec.id}_curve.set_color_by_gradient('#440154', '#21908c', '#fde725')",
            ]

        # Group everything
        lines.append(
            f"{spec.id} = VGroup({spec.id}_bg, {spec.id}_axes, "
            f"{spec.id}_xlabel, {spec.id}_ylabel, {spec.id}_curve)"
        )

        if is_3d:
            lines.append(f"self.add_fixed_in_frame_mobjects({spec.id})")
            lines.append(f"self.remove({spec.id})")

        return "\n        ".join(lines)
