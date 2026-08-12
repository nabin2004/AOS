"""DSA concept builders."""

from __future__ import annotations

from collections.abc import Sequence

from manim import DOWN, Text, VGroup, WHITE

from manim_dsa.compute.bst import bst_insert_steps
from manim_dsa.compute.graph_search import DEFAULT_GRAPH, bfs_steps, dfs_steps
from manim_dsa.compute.search import binary_search_steps
from manim_dsa.compute.sorting import bubble_sort_steps, merge_sort_steps
from manim_dsa.registry import register_concept
from manim_viz import DEFAULT_THEME, array_bars, array_cells, graph_nodes_edges, highlight_indices, tree_layout


@register_concept(
    id="array_bars",
    domain="dsa",
    chapter="1.0",
    title="Array Bars",
    tags=["array"],
)
def build_array_bars(values: Sequence[int] | None = None) -> VGroup:
    values = list(values or [8, 3, 7, 1, 9, 2])
    bars = array_bars(values)
    title = Text("Array", font_size=26, color=WHITE)
    return VGroup(title, bars).arrange(DOWN, buff=0.3)


@register_concept(
    id="bubble_sort",
    domain="dsa",
    chapter="1.1",
    title="Bubble Sort",
    tags=["sorting"],
)
def build_bubble_sort(values: Sequence[int] | None = None) -> VGroup:
    values = list(values or [5, 1, 4, 2, 8])
    steps = bubble_sort_steps(values)
    final = steps[-1]["array"]
    mid = steps[len(steps) // 2]
    bars = array_bars(final)
    highlight_indices(bars, mid.get("highlights") or [])
    title = Text(f"Bubble sort → {final}", font_size=22, color=WHITE)
    note = Text(f"{len(steps)} steps", font_size=18, color=DEFAULT_THEME.soft)
    return VGroup(title, bars, note).arrange(DOWN, buff=0.25)


@register_concept(
    id="merge_sort",
    domain="dsa",
    chapter="1.2",
    title="Merge Sort",
    tags=["sorting"],
)
def build_merge_sort(values: Sequence[int] | None = None) -> VGroup:
    values = list(values or [8, 3, 7, 1, 9, 2])
    steps = merge_sort_steps(values)
    final = steps[-1]["array"]
    bars = array_bars(final)
    title = Text(f"Merge sort → {final}", font_size=22, color=WHITE)
    note = Text(f"{len(steps)} merge steps", font_size=18, color=DEFAULT_THEME.soft)
    return VGroup(title, bars, note).arrange(DOWN, buff=0.25)


@register_concept(
    id="binary_search",
    domain="dsa",
    chapter="1.3",
    title="Binary Search",
    tags=["search"],
)
def build_binary_search(values: Sequence[int] | None = None, target: int = 7) -> VGroup:
    values = list(values or [1, 3, 5, 7, 9, 11])
    steps = binary_search_steps(values, target)
    last = steps[-1]
    cells = array_cells(values)
    hi = []
    if last.get("mid") is not None:
        hi = [last["mid"]]
    elif last.get("lo") is not None and 0 <= last["lo"] < len(values):
        hi = [last["lo"]]
    highlight_indices(cells, hi)
    title = Text(f"Binary search target={target} found={last['found']}", font_size=22, color=WHITE)
    return VGroup(title, cells).arrange(DOWN, buff=0.3)


@register_concept(
    id="bst_insert",
    domain="dsa",
    chapter="2.1",
    title="BST Insert",
    tags=["tree", "bst"],
)
def build_bst_insert(values: Sequence[int] | None = None) -> VGroup:
    values = list(values or [5, 3, 8, 1, 4, 7])
    steps = bst_insert_steps(values)
    last = steps[-1]
    parent = last["parent"]
    root = last["root"]
    positions = tree_layout(parent, root)
    # build adjacency from parent
    adj: dict = {n: [] for n in parent}
    for child, p in parent.items():
        if p is not None:
            adj[p].append(child)
    g = graph_nodes_edges(adj, positions=positions)
    title = Text(f"BST insert {values}", font_size=22, color=WHITE)
    return VGroup(title, g).arrange(DOWN, buff=0.35)


@register_concept(
    id="bfs",
    domain="dsa",
    chapter="2.2",
    title="BFS",
    tags=["graph", "bfs"],
)
def build_bfs(start: str = "A") -> VGroup:
    steps = bfs_steps(DEFAULT_GRAPH, start)
    order = steps[-1]["order"]
    g = graph_nodes_edges(DEFAULT_GRAPH)
    title = Text(f"BFS order: {' → '.join(map(str, order))}", font_size=22, color=WHITE)
    return VGroup(title, g).arrange(DOWN, buff=0.35)


@register_concept(
    id="dfs",
    domain="dsa",
    chapter="2.3",
    title="DFS",
    tags=["graph", "dfs"],
)
def build_dfs(start: str = "A") -> VGroup:
    steps = dfs_steps(DEFAULT_GRAPH, start)
    order = steps[-1]["order"]
    g = graph_nodes_edges(DEFAULT_GRAPH)
    title = Text(f"DFS order: {' → '.join(map(str, order))}", font_size=22, color=WHITE)
    return VGroup(title, g).arrange(DOWN, buff=0.35)
