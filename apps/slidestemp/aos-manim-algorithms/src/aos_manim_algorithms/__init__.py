"""
AOS Manim Algorithms: Computational algorithms and data structure visualization plugin.
"""

from .structures.array import ArrayMobject, ArrayCell
from .structures.graph import NetworkXGraphVisualizer
from .algorithms.searching import BinarySearchVisualizer, BinarySearchCueable, compute_binary_search_steps
from .algorithms.sorting import BubbleSortVisualizer, compute_bubble_sort_steps
from .algorithms.graph_algos import DijkstraVisualizer, compute_dijkstra_trace
from .validators.algo_validators import SortedInvariantValidator, GraphPathValidator

__version__ = "0.1.0"

__all__ = [
    "ArrayMobject",
    "ArrayCell",
    "NetworkXGraphVisualizer",
    "BinarySearchVisualizer",
    "BinarySearchCueable",
    "compute_binary_search_steps",
    "BubbleSortVisualizer",
    "compute_bubble_sort_steps",
    "DijkstraVisualizer",
    "compute_dijkstra_trace",
    "SortedInvariantValidator",
    "GraphPathValidator",
]
