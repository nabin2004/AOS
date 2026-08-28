import pytest
import networkx as nx
from aos_manim_core import get_theme, set_theme
from aos_manim_algorithms import (
    ArrayMobject,
    NetworkXGraphVisualizer,
    BinarySearchVisualizer,
    compute_binary_search_steps,
    BubbleSortVisualizer,
    compute_bubble_sort_steps,
    DijkstraVisualizer,
    compute_dijkstra_trace,
    SortedInvariantValidator,
    GraphPathValidator,
)


def test_array_mobject():
    set_theme("modern_dark")
    arr = ArrayMobject([10, 20, 30, 40])
    assert len(arr.cells) == 4
    assert arr.get_cell(0).value == 10
    arr.highlight_index(1)
    arr.reset_all()


def test_binary_search_trace():
    trace = compute_binary_search_steps([2, 4, 6, 8, 10, 12, 14], 10)
    assert trace["found_index"] == 4
    assert len(trace["steps"]) > 0

    vis = BinarySearchVisualizer()
    mobs = vis.build_binary_search_mobjects([2, 4, 6, 8, 10, 12, 14], 10)
    assert mobs["array_mob"] is not None

    cueable = vis.build_cueable_binary_search([2, 4, 6, 8, 10, 12, 14], 10)
    assert cueable.step_count() > 0
    from aos_manim_core import Cue, CueAction

    cueable.apply_cue(None, Cue(mark="s0", target_id="d0", action=CueAction.STEP, payload={"i": 0}))
    assert cueable.applied_step == 0
    last = cueable.step_count() - 1
    cueable.apply_cue(None, Cue(mark="sN", target_id="d0", action=CueAction.STEP, payload={"i": last}))
    assert cueable.applied_step == last
    found = cueable.trace["found_index"]
    assert found >= 0


def test_bubble_sort_trace_and_validator():
    trace = compute_bubble_sort_steps([9, 3, 5, 1, 7])
    assert trace["sorted"] == [1, 3, 5, 7, 9]

    val = SortedInvariantValidator()
    assert val.validate(trace["sorted"]).is_valid
    assert not val.validate([9, 3, 5]).is_valid


def test_networkx_graph_and_dijkstra():
    G = nx.Graph()
    G.add_edge("A", "B", weight=1)
    G.add_edge("B", "C", weight=2)
    G.add_edge("A", "C", weight=4)

    trace = compute_dijkstra_trace(G, "A", "C")
    assert trace["path"] == ["A", "B", "C"]
    assert trace["shortest_distance"] == 3.0

    val = GraphPathValidator()
    assert val.validate(trace["path"], graph=G).is_valid
    assert not val.validate(["A", "C", "D"], graph=G).is_valid

    vis = DijkstraVisualizer()
    mobs = vis.build_dijkstra_mobjects(G, "A", "C")
    assert mobs["graph_mob"] is not None
