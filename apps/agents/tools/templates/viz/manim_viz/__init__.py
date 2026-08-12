"""Shared Manim visualization primitives for AOS domain plugins."""

from manim_viz.array import array_bars, array_cells, highlight_indices
from manim_viz.coords import make_axes, make_plane
from manim_viz.graph import graph_nodes_edges, tree_layout
from manim_viz.grid import matrix_grid
from manim_viz.particle import particle, particle_with_trail, trajectory_curve
from manim_viz.plots import bar_chart, curve_from_samples
from manim_viz.registry import ConceptRegistry, ConceptSpec
from manim_viz.theme import DEFAULT_THEME, VizTheme
from manim_viz.vectors import labeled_vector_on_plane, vector_arrow

__all__ = [
    "ConceptRegistry",
    "ConceptSpec",
    "DEFAULT_THEME",
    "VizTheme",
    "array_bars",
    "array_cells",
    "bar_chart",
    "curve_from_samples",
    "graph_nodes_edges",
    "highlight_indices",
    "labeled_vector_on_plane",
    "make_axes",
    "make_plane",
    "matrix_grid",
    "particle",
    "particle_with_trail",
    "trajectory_curve",
    "tree_layout",
    "vector_arrow",
]
