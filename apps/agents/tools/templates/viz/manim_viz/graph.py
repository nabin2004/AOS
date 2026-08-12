"""Small graph / tree layout primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from manim import Circle, Line, Text, VGroup, WHITE

from manim_viz.theme import DEFAULT_THEME, VizTheme


def graph_nodes_edges(
    adjacency: Mapping[str, Sequence[str]] | Mapping[int, Sequence[int]],
    *,
    positions: Mapping | None = None,
    theme: VizTheme | None = None,
    radius: float = 0.28,
) -> VGroup:
    """
    Draw an undirected-looking digraph. If positions missing, place on a circle.
    """
    import math

    theme = theme or DEFAULT_THEME
    nodes = list(adjacency.keys())
    n = len(nodes)
    if positions is None:
        positions = {}
        for i, node in enumerate(nodes):
            ang = 2 * math.pi * i / max(n, 1) - math.pi / 2
            positions[node] = (2.2 * math.cos(ang), 1.6 * math.sin(ang), 0)

    node_mobs: dict = {}
    group_nodes = VGroup()
    for node in nodes:
        c = Circle(radius=radius, color=theme.primary, fill_opacity=0.25)
        t = Text(str(node), font_size=18, color=WHITE)
        g = VGroup(c, t)
        g.move_to(positions[node])
        node_mobs[node] = g
        group_nodes.add(g)

    edges = VGroup()
    seen: set[tuple] = set()
    for u, nbrs in adjacency.items():
        for v in nbrs:
            key = tuple(sorted((str(u), str(v))))
            if key in seen:
                continue
            seen.add(key)
            if v not in node_mobs:
                continue
            edges.add(
                Line(
                    node_mobs[u][0].get_center(),
                    node_mobs[v][0].get_center(),
                    stroke_opacity=0.7,
                    color=theme.soft,
                )
            )
    return VGroup(edges, group_nodes)


def tree_layout(
    parent: Mapping,
    root,
    *,
    x_gap: float = 1.2,
    y_gap: float = 1.0,
) -> dict:
    """
    Assign 3D positions for a tree given parent[child]=parent (root maps to None).
    Children inferred by inverting parent map.
    """
    children: dict = {root: []}
    for child, p in parent.items():
        if p is None:
            continue
        children.setdefault(p, []).append(child)
        children.setdefault(child, [])

    positions: dict = {}

    def place(node, x: float, depth: int, span: float) -> None:
        positions[node] = (x, -depth * y_gap, 0)
        kids = children.get(node, [])
        if not kids:
            return
        width = span
        left = x - width / 2
        step = width / len(kids)
        for i, kid in enumerate(kids):
            place(kid, left + step * (i + 0.5), depth + 1, step * 0.9)

    place(root, 0.0, 0, max(2.0, x_gap * max(1, len(children.get(root, [])))))
    return positions
