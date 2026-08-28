from __future__ import annotations

import heapq
from typing import Optional, List, Dict, Any, Tuple
import networkx as nx
from aos_manim_core import get_theme, ThemeConfig
from ..structures.graph import NetworkXGraphVisualizer


def compute_dijkstra_trace(
    graph: nx.Graph,
    source: Any,
    target: Any,
) -> Dict[str, Any]:
    """Generates step-by-step Dijkstra execution trace."""
    distances: Dict[Any, float] = {node: float('inf') for node in graph.nodes()}
    distances[source] = 0.0
    previous: Dict[Any, Optional[Any]] = {node: None for node in graph.nodes()}

    pq: List[Tuple[float, Any]] = [(0.0, source)]
    visited = set()
    steps = []

    while pq:
        curr_dist, curr_node = heapq.heappop(pq)

        if curr_node in visited:
            continue
        visited.add(curr_node)

        step_info = {
            "current_node": curr_node,
            "current_distance": curr_dist,
            "visited_so_far": list(visited),
            "distances": dict(distances),
        }
        steps.append(step_info)

        if curr_node == target:
            break

        for neighbor in graph.neighbors(curr_node):
            weight = graph[curr_node][neighbor].get('weight', 1.0)
            new_dist = curr_dist + weight

            if new_dist < distances[neighbor]:
                distances[neighbor] = new_dist
                previous[neighbor] = curr_node
                heapq.heappush(pq, (new_dist, neighbor))

    # Reconstruct path
    path = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = previous[curr]
    path.reverse()

    if path and path[0] != source:
        path = []

    return {
        "source": source,
        "target": target,
        "path": path,
        "shortest_distance": distances.get(target, float('inf')),
        "steps": steps,
    }


class DijkstraVisualizer:
    """Visualizes Dijkstra's shortest path algorithm on NetworkX graphs."""

    def __init__(self, theme: Optional[ThemeConfig] = None) -> None:
        self.theme = theme or get_theme()

    def build_dijkstra_mobjects(
        self,
        graph: nx.Graph,
        source: Any,
        target: Any,
        layout: str = "spring",
    ) -> Dict[str, Any]:
        trace = compute_dijkstra_trace(graph, source, target)
        g_vis = NetworkXGraphVisualizer(theme=self.theme)
        mobs = g_vis.build_graph_mobject(graph, layout=layout)

        return {
            "graph_mob": mobs["graph_mob"],
            "trace": trace,
        }
