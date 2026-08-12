"""BFS / DFS visit order."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence


def bfs_steps(adjacency: Mapping, start) -> list[dict]:
    visited: set = set()
    order: list = []
    q: deque = deque([start])
    steps = [{"queue": list(q), "visited": [], "current": None, "order": []}]
    while q:
        u = q.popleft()
        if u in visited:
            continue
        visited.add(u)
        order.append(u)
        steps.append({"queue": list(q), "visited": sorted(visited, key=str), "current": u, "order": order.copy()})
        for v in adjacency.get(u, []):
            if v not in visited:
                q.append(v)
        steps.append({"queue": list(q), "visited": sorted(visited, key=str), "current": u, "order": order.copy()})
    return steps


def dfs_steps(adjacency: Mapping, start) -> list[dict]:
    visited: set = set()
    order: list = []
    stack = [start]
    steps = [{"stack": list(stack), "visited": [], "current": None, "order": []}]
    while stack:
        u = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        order.append(u)
        steps.append({"stack": list(stack), "visited": sorted(visited, key=str), "current": u, "order": order.copy()})
        for v in reversed(list(adjacency.get(u, []))):
            if v not in visited:
                stack.append(v)
        steps.append({"stack": list(stack), "visited": sorted(visited, key=str), "current": u, "order": order.copy()})
    return steps


DEFAULT_GRAPH = {
    "A": ["B", "C"],
    "B": ["A", "D", "E"],
    "C": ["A", "F"],
    "D": ["B"],
    "E": ["B", "F"],
    "F": ["C", "E"],
}
