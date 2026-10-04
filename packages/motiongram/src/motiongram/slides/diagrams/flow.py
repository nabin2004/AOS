"""Flow diagram component for pipelines and architectures."""

from __future__ import annotations

from typing import Any

from manim import Arrow, RoundedRectangle, Text, VGroup

from motiongram.slides.diagrams.base import SlideDiagram


class FlowDiagram(SlideDiagram):
    """Pipeline flow diagram with labeled nodes and directed connecting arrows."""

    def __init__(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]] | None = None,
        layout: str = "horizontal",
        box_color: str = "#58C4DD",
        arrow_color: str = "#83C167",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        node_mobs: dict[str, VGroup] = {}
        ordered_mobs: list[VGroup] = []

        # 1. Create nodes
        for node in nodes:
            n_id = node.get("id", "node")
            label_text = node.get("label", n_id)
            color = node.get("color", box_color)

            lbl = Text(str(label_text), font_size=24, color="#FFFFFF")
            box = RoundedRectangle(
                corner_radius=0.15,
                width=max(lbl.width + 0.6, 1.8),
                height=max(lbl.height + 0.5, 0.9),
                color=color,
                fill_color="#222222",
                fill_opacity=0.8,
            )
            node_grp = VGroup(box, lbl)
            node_mobs[n_id] = node_grp
            ordered_mobs.append(node_grp)

            self.register_selector(f"node[{n_id}]", node_grp)
            self.register_selector(f"label[{n_id}]", lbl)
            self.register_selector(f"box[{n_id}]", box)

        # 2. Arrange nodes
        nodes_group = VGroup(*ordered_mobs)
        if layout == "vertical":
            nodes_group.arrange(direction=[0, -1, 0], buff=0.8)
        else:
            nodes_group.arrange(direction=[1, 0, 0], buff=0.8)

        self.add(nodes_group)

        # 3. Create edges
        if edges:
            for edge in edges:
                src_id = edge.get("from")
                tgt_id = edge.get("to")
                if src_id in node_mobs and tgt_id in node_mobs:
                    src_m = node_mobs[src_id]
                    tgt_m = node_mobs[tgt_id]
                    arr = Arrow(
                        src_m.get_right() if layout != "vertical" else src_m.get_bottom(),
                        tgt_m.get_left() if layout != "vertical" else tgt_m.get_top(),
                        buff=0.1,
                        color=arrow_color,
                        stroke_width=3,
                        max_tip_length_to_length_ratio=0.2,
                    )
                    self.add(arr)
                    self.register_selector(f"edge[{src_id}->{tgt_id}]", arr)
