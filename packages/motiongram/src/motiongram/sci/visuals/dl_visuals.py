"""Code generators for Deep Learning visual components in ManimCE."""

from __future__ import annotations

from typing import Any

from motiongram.sci.schema import VisualComponentSpec


def format_color(val: Any) -> str:
    """Format color string or variable name safely for Python code generation."""
    if isinstance(val, str):
        val = val.strip()
        if val.startswith("#"):
            return f'"{val}"'
        if val.startswith('"') or val.startswith("'"):
            return val
        # Manim color constant (e.g. BLUE, YELLOW, RED)
        return val
    return f'"{str(val)}"'


class DeepLearningVisualCodeGenerator:
    """Generates Manim CE code for Deep Learning visual components."""

    # Canonical color palette for Deep Learning
    COLOR_INPUT = '"#58C4DD"'      # Blue
    COLOR_WEIGHT = '"#83C167"'     # Green
    COLOR_ACTIVATION = '"#FFFF00"' # Yellow
    COLOR_LOSS = '"#FF6666"'       # Red
    COLOR_OPTIMIZER = '"#FFE66D"'  # Gold
    COLOR_BACKPROP = '"#FF4081"'   # Pink / Magenta

    @classmethod
    def generate_activation_plot(
        cls, vis: VisualComponentSpec, pts_var: str, axes_id: str
    ) -> str:
        """Generate Manim code for ActivationPlot (2D axes, curve, asymptotes, tracking dot)."""
        vid = vis.id
        style = vis.style or {}
        curve_color = format_color(style.get("color", "#FFFF00"))
        fn_name = style.get("function", "relu").lower()
        show_dot = style.get("show_dot", True)

        lines = [
            f"# ActivationPlot [{vid}]",
            f"{vid}_group = VGroup()",
            f"{vid}_axes = Axes(",
            "    x_range=[-4.0, 4.0, 1.0],",
            "    y_range=[-1.5, 3.5, 1.0],",
            "    x_length=6.0,",
            "    y_length=4.5,",
            "    axis_config={'color': '#78909c', 'stroke_width': 2},",
            ")",
            f"{vid}_group.add({vid}_axes)",
            f"",
            f"# Build activation curve from precomputed samples: {pts_var}",
            f"{vid}_curve = VMobject(color={curve_color}, stroke_width=4)",
            f"if len({pts_var}) > 1:",
            f"    {vid}_curve.set_points_smoothly([{vid}_axes.c2p(p[0], p[1], 0) for p in {pts_var}])",
            f"{vid}_group.add({vid}_curve)",
        ]

        # Add asymptotes for Sigmoid or Tanh
        if fn_name == "sigmoid":
            lines.extend([
                f"# Asymptote lines for Sigmoid at y=0 and y=1",
                f"{vid}_asymp_top = DashedLine({vid}_axes.c2p(-4.0, 1.0, 0), {vid}_axes.c2p(4.0, 1.0, 0), color='#b0bec5', stroke_width=1.5)",
                f"{vid}_asymp_bot = DashedLine({vid}_axes.c2p(-4.0, 0.0, 0), {vid}_axes.c2p(4.0, 0.0, 0), color='#b0bec5', stroke_width=1.5)",
                f"{vid}_label_1 = Text('1.0', font_size=18, color='#b0bec5').next_to({vid}_axes.c2p(0, 1.0, 0), LEFT, buff=0.15)",
                f"{vid}_label_0 = Text('0.0', font_size=18, color='#b0bec5').next_to({vid}_axes.c2p(0, 0.0, 0), LEFT, buff=0.15)",
                f"{vid}_group.add({vid}_asymp_top, {vid}_asymp_bot, {vid}_label_1, {vid}_label_0)",
            ])
        elif fn_name == "tanh":
            lines.extend([
                f"# Asymptote lines for Tanh at y=1 and y=-1",
                f"{vid}_asymp_top = DashedLine({vid}_axes.c2p(-4.0, 1.0, 0), {vid}_axes.c2p(4.0, 1.0, 0), color='#b0bec5', stroke_width=1.5)",
                f"{vid}_asymp_bot = DashedLine({vid}_axes.c2p(-4.0, -1.0, 0), {vid}_axes.c2p(4.0, -1.0, 0), color='#b0bec5', stroke_width=1.5)",
                f"{vid}_label_1 = Text('+1.0', font_size=18, color='#b0bec5').next_to({vid}_axes.c2p(0, 1.0, 0), LEFT, buff=0.15)",
                f"{vid}_label_m1 = Text('-1.0', font_size=18, color='#b0bec5').next_to({vid}_axes.c2p(0, -1.0, 0), LEFT, buff=0.15)",
                f"{vid}_group.add({vid}_asymp_top, {vid}_asymp_bot, {vid}_label_1, {vid}_label_m1)",
            ])

        # Optional Tracking Dot
        if show_dot:
            lines.extend([
                f"{vid}_dot = Dot(color={cls.COLOR_INPUT}, radius=0.08)",
                f"if len({pts_var}) > 0:",
                f"    {vid}_dot.move_to({vid}_axes.c2p({pts_var}[0][0], {pts_var}[0][1], 0))",
                f"{vid}_group.add({vid}_dot)",
            ])

        # Title Label
        title_text = style.get("title", fn_name.upper())
        lines.extend([
            f"{vid}_title = Text('{title_text}', font_size=24, color='#ffffff', weight='BOLD').next_to({vid}_axes, UP, buff=0.2)",
            f"{vid}_group.add({vid}_title)",
            f"{vid} = {vid}_group",
        ])

        return "\n        ".join(lines)

    @classmethod
    def generate_loss_landscape(
        cls, vis: VisualComponentSpec, pts_var: str, axes_id: str
    ) -> str:
        """Generate Manim code for 3D Loss Landscape Surface and contour projections."""
        vid = vis.id

        lines = [
            f"# LossLandscape 3D [{vid}]",
            f"{vid}_group = VGroup()",
            f"# Construct 3D surface from grid equation or points in {axes_id}",
            f"def {vid}_func(u, v):",
            f"    return {axes_id}.c2p(u, v, 0.5 * (u**2 + 2.0 * v**2))",
            f"",
            f"{vid}_surface = Surface(",
            f"    {vid}_func,",
            f"    u_range=[-3.0, 3.0],",
            f"    v_range=[-3.0, 3.0],",
            f"    resolution=(30, 30),",
            f"    should_make_jagged=False,",
            f")",
            f"{vid}_surface.set_fill_by_value(axes={axes_id}, colors=['#0d0887', '#6a00a8', '#b12a90', '#e16462', '#fca636', '#f0f921'], axis=2)",
            f"{vid}_surface.set_style(fill_opacity=0.82, stroke_color='#ffffff', stroke_width=0.4, stroke_opacity=0.3)",
            f"{vid}_group.add({vid}_surface)",
            f"",
            f"# Ground contour floor rings",
            f"for r_val in [0.5, 1.0, 1.8, 2.8]:",
            f"    ring = Circle(radius=r_val, color='#455a64', stroke_width=1.2)",
            f"    ring.move_to({axes_id}.c2p(0, 0, 0))",
            f"    {vid}_group.add(ring)",
            f"",
            f"{vid} = {vid}_group",
        ]

        return "\n        ".join(lines)

    @classmethod
    def generate_optimizer_path(
        cls, vis: VisualComponentSpec, pts_var: str, axes_id: str
    ) -> str:
        """Generate Manim code for Optimizer trajectory path and glowing lead dot."""
        vid = vis.id
        style = vis.style or {}
        color = format_color(style.get("color", "#FFE66D"))
        stroke_width = style.get("stroke_width", 3.5)
        label = style.get("label", "")

        lines = [
            f"# OptimizerPath [{vid}]",
            f"{vid}_group = VGroup()",
            f"{vid}_path = VMobject(color={color}, stroke_width={stroke_width})",
            f"if len({pts_var}) > 1:",
            f"    {vid}_path.set_points_smoothly([{axes_id}.c2p(p[0], p[1], p[2]) for p in {pts_var}])",
            f"{vid}_group.add({vid}_path)",
            f"",
            f"# Lead dot at start",
            f"{vid}_dot = Dot3D(color={color}, radius=0.10) if hasattr(self, 'camera') and hasattr(self.camera, 'phi') else Dot(color={color}, radius=0.10)",
            f"if len({pts_var}) > 0:",
            f"    {vid}_dot.move_to({axes_id}.c2p({pts_var}[0][0], {pts_var}[0][1], {pts_var}[0][2]))",
            f"{vid}_group.add({vid}_dot)",
        ]

        if label:
            lines.extend([
                f"{vid}_label = Text('{label}', font_size=18, color={color}, weight='BOLD')",
                f"if len({pts_var}) > 0:",
                f"    {vid}_label.next_to({vid}_dot, UP + RIGHT, buff=0.15)",
                f"{vid}_group.add({vid}_label)",
            ])

        lines.append(f"{vid} = {vid}_group")
        return "\n        ".join(lines)

    @classmethod
    def generate_network_graph(
        cls, vis: VisualComponentSpec, axes_id: str
    ) -> str:
        """Generate Manim code for Multi-Layer Neural Network diagram."""
        vid = vis.id
        layer_sizes = vis.layer_sizes or [3, 4, 2]
        style = vis.style or {}

        color_in = format_color(style.get("color_input", "#58C4DD"))
        color_weight = format_color(style.get("color_weight", "#83C167"))
        color_act = format_color(style.get("color_activation", "#FFFF00"))
        color_loss = format_color(style.get("color_loss", "#FF6666"))

        lines = [
            f"# NetworkGraph [{vid}]",
            f"{vid}_group = VGroup()",
            f"{vid}_layers = []",
            f"{vid}_edges = VGroup()",
            f"{vid}_layer_groups = VGroup()",
            f"",
            f"layer_sizes_{vid} = {repr(layer_sizes)}",
            f"n_layers_{vid} = len(layer_sizes_{vid})",
            f"x_spacing_{vid} = 2.4",
            f"y_spacing_{vid} = 0.9",
            f"",
            f"# Create layer nodes",
            f"for l_idx, l_size in enumerate(layer_sizes_{vid}):",
            f"    curr_nodes = []",
            f"    layer_x = (l_idx - (n_layers_{vid} - 1) / 2.0) * x_spacing_{vid}",
            f"    node_color = {color_in} if l_idx == 0 else ({color_loss} if l_idx == n_layers_{vid} - 1 else {color_act})",
            f"    for n_idx in range(l_size):",
            f"        node_y = (n_idx - (l_size - 1) / 2.0) * y_spacing_{vid}",
            f"        node = Dot(point=[layer_x, node_y, 0], radius=0.16, color=node_color)",
            f"        node_outline = Circle(radius=0.18, color='#ffffff', stroke_width=1.5).move_to(node)",
            f"        node_grp = VGroup(node, node_outline)",
            f"        curr_nodes.append(node_grp)",
            f"        {vid}_layer_groups.add(node_grp)",
            f"    {vid}_layers.append(curr_nodes)",
            f"",
            f"# Connect adjacent layers with synapses (weights)",
            f"for l_idx in range(n_layers_{vid} - 1):",
            f"    for u_node in {vid}_layers[l_idx]:",
            f"        for v_node in {vid}_layers[l_idx + 1]:",
            f"            edge = Line(u_node[0].get_center(), v_node[0].get_center(), color={color_weight}, stroke_width=1.8, stroke_opacity=0.55)",
            f"            {vid}_edges.add(edge)",
            f"",
            f"{vid}_group.add({vid}_edges)",
            f"{vid}_group.add({vid}_layer_groups)",
            f"{vid} = {vid}_group",
        ]

        return "\n        ".join(lines)

    @classmethod
    def generate_tensor_grid(
        cls, vis: VisualComponentSpec, axes_id: str
    ) -> str:
        """Generate Manim code for TensorGrid heatmap visualization."""
        vid = vis.id
        shape = vis.shape or [3, 3]
        values = vis.values or [[0.1, 0.4, 0.9], [0.3, 0.8, 0.2], [0.7, 0.1, 0.5]]

        lines = [
            f"# TensorGrid [{vid}]",
            f"{vid}_group = VGroup()",
            f"rows_{vid}, cols_{vid} = {shape[0]}, {shape[1]}",
            f"cell_size_{vid} = 0.8",
            f"vals_{vid} = {repr(values)}",
            f"",
            f"for r in range(rows_{vid}):",
            f"    for c in range(cols_{vid}):",
            f"        v_val = vals_{vid}[r][c] if r < len(vals_{vid}) and c < len(vals_{vid}[r]) else 0.5",
            f"        cell_color = interpolate_color(ManimColor('#1a237e'), ManimColor('#00e676'), float(v_val))",
            f"        cell_rect = Square(side_length=cell_size_{vid}, fill_color=cell_color, fill_opacity=0.85, stroke_color='#ffffff', stroke_width=1.5)",
            f"        cx = (c - (cols_{vid} - 1) / 2.0) * cell_size_{vid}",
            f"        cy = ((rows_{vid} - 1) / 2.0 - r) * cell_size_{vid}",
            f"        cell_rect.move_to([cx, cy, 0])",
            f"        txt = Text(f'{{v_val:.2f}}', font_size=14, color='#ffffff').move_to(cell_rect)",
            f"        {vid}_group.add(cell_rect, txt)",
            f"",
            f"{vid} = {vid}_group",
        ]

        return "\n        ".join(lines)
