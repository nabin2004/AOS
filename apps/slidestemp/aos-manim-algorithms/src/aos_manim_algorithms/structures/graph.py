from __future__ import annotations

from typing import Optional, Dict, Any, List, Union
import networkx as nx
from manim import (
    Graph,
    VGroup,
    Text,
    MathTex,
    UP,
    DOWN,
    LEFT,
    RIGHT,
)
from aos_manim_core import get_theme, ThemeConfig


class NetworkXGraphVisualizer:
    """Bridges NetworkX computational graphs with Manim visual graph representations."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_graph_mobject(
        self,
        nx_graph: nx.Graph,
        layout: str = "spring",
        layout_scale: float = 3.0,
        vertex_radius: float = 0.35,
    ) -> Dict[str, Any]:
        t = self.theme
        vertices = list(nx_graph.nodes())
        edges = list(nx_graph.edges())

        # Vertex config with theme styling
        vertex_config = {
            "radius": vertex_radius,
            "fill_color": t.surface,
            "fill_opacity": 1.0,
            "stroke_color": t.primary,
            "stroke_width": 3.0,
        }

        # Edge config
        edge_config = {
            "stroke_color": t.border,
            "stroke_width": 2.5,
        }

        # Labels
        labels = {v: Text(str(v), font_size=18, color=t.text_main, font=t.fonts.text_font) for v in vertices}

        graph_mob = Graph(
            vertices,
            edges,
            layout=layout,
            layout_scale=layout_scale,
            labels=labels,
            vertex_config=vertex_config,
            edge_config=edge_config,
        )

        return {
            "graph_mob": graph_mob,
            "nx_graph": nx_graph,
            "vertices": vertices,
            "edges": edges,
        }
