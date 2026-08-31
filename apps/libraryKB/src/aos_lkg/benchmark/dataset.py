"""Canonical Benchmark Dataset: Ground-truth mathematical animation tasks for evaluation."""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class BenchmarkTestCase(BaseModel):
    id: str
    query: str
    category: str
    expected_domain: str
    expected_api_substrings: List[str]
    expected_capability_id: str
    expected_mobjects: List[str] = Field(default_factory=list)
    expected_dimension: str = "2D"
    description: str = ""


BENCHMARK_SUITE: List[BenchmarkTestCase] = [
    # 1. Chaotic Systems & ODEs
    BenchmarkTestCase(
        id="bm_ode_lorenz",
        query="Animate Lorenz attractor",
        category="Dynamical Systems / Chaos",
        expected_domain="differential_equations",
        expected_api_substrings=["solve_ivp", "odeint"],
        expected_capability_id="cap:ode_integration",
        expected_mobjects=["ThreeDAxes"],
        expected_dimension="3D",
        description="Chaotic 3D ODE phase space trajectory",
    ),
    BenchmarkTestCase(
        id="bm_ode_rossler",
        query="Simulate and plot Rossler attractor phase space in 3D",
        category="Dynamical Systems / Chaos",
        expected_domain="differential_equations",
        expected_api_substrings=["solve_ivp", "odeint"],
        expected_capability_id="cap:ode_integration",
        expected_mobjects=["ThreeDAxes"],
        expected_dimension="3D",
        description="Rossler chaotic attractor numerical integration",
    ),
    BenchmarkTestCase(
        id="bm_ode_pendulum",
        query="Animate double pendulum phase portrait using Runge-Kutta ODE integration",
        category="Dynamical Systems",
        expected_domain="differential_equations",
        expected_api_substrings=["solve_ivp", "odeint"],
        expected_capability_id="cap:ode_integration",
        expected_mobjects=["Axes", "ThreeDAxes"],
        expected_dimension="2D",
        description="Nonlinear pendulum trajectory simulation",
    ),

    # 2. Root Finding & Scalar Equations
    BenchmarkTestCase(
        id="bm_root_newton_sqrt",
        query="Animate Newton's method for finding sqrt(2)",
        category="Root Finding",
        expected_domain="root_finding",
        expected_api_substrings=["newton", "brentq", "root_scalar"],
        expected_capability_id="cap:root_finding_newton",
        expected_mobjects=["Axes", "Dot"],
        expected_dimension="2D",
        description="Newton-Raphson tangent line root progression",
    ),
    BenchmarkTestCase(
        id="bm_root_brent_zero",
        query="Find continuous zero crossing bracket on [1, 3] with Brent-Dekker method",
        category="Root Finding",
        expected_domain="root_finding",
        expected_api_substrings=["brentq", "bisect", "root_scalar"],
        expected_capability_id="cap:root_finding_bracketed",
        expected_mobjects=["Axes", "Dot", "NumberLine"],
        expected_dimension="2D",
        description="Bracketed zero crossing convergence",
    ),
    BenchmarkTestCase(
        id="bm_root_symbolic_poly",
        query="Solve exact polynomial roots symbolically using SymPy",
        category="Symbolic Algebra",
        expected_domain="symbolic_algebra",
        expected_api_substrings=["solve", "solveset", "nsolve"],
        expected_capability_id="cap:symbolic_equation_solving",
        expected_mobjects=["MathTex"],
        expected_dimension="2D",
        description="Symbolic algebraic equation solving",
    ),

    # 3. Calculus & Quadrature
    BenchmarkTestCase(
        id="bm_calc_riemann_sum",
        query="Animate Riemann sum rectangles converging to definite integral area",
        category="Calculus",
        expected_domain="calculus",
        expected_api_substrings=["quad", "trapezoid", "cumulative_trapezoid"],
        expected_capability_id="cap:numerical_integration",
        expected_mobjects=["Axes", "Polygon"],
        expected_dimension="2D",
        description="Adaptive quadrature and Riemann sum limit",
    ),
    BenchmarkTestCase(
        id="bm_calc_symbolic_diff",
        query="Compute symbolic derivative and Taylor series expansion",
        category="Symbolic Calculus",
        expected_domain="symbolic_algebra",
        expected_api_substrings=["diff", "series", "integrate"],
        expected_capability_id="cap:symbolic_calculus",
        expected_mobjects=["MathTex", "Axes"],
        expected_dimension="2D",
        description="Symbolic differentiation and Taylor series",
    ),

    # 4. Graph Theory & Network Algorithms
    BenchmarkTestCase(
        id="bm_graph_dijkstra",
        query="Visualize shortest path using Dijkstra algorithm on a weighted graph",
        category="Graph Theory",
        expected_domain="graph_theory",
        expected_api_substrings=["dijkstra_path", "shortest_path", "astar_path"],
        expected_capability_id="cap:graph_shortest_path",
        expected_mobjects=["Graph"],
        expected_dimension="2D",
        description="Dijkstra priority queue shortest path search",
    ),
    BenchmarkTestCase(
        id="bm_graph_bfs_traversal",
        query="Animate breadth-first search BFS traversal tree on a network",
        category="Graph Theory",
        expected_domain="graph_theory",
        expected_api_substrings=["bfs_edges", "bfs_tree", "dfs_edges", "minimum_spanning_tree"],
        expected_capability_id="cap:graph_traversal",
        expected_mobjects=["Graph"],
        expected_dimension="2D",
        description="BFS level-order graph exploration",
    ),
    BenchmarkTestCase(
        id="bm_graph_mst",
        query="Compute and animate Minimum Spanning Tree MST on a graph",
        category="Graph Theory",
        expected_domain="graph_theory",
        expected_api_substrings=["minimum_spanning_tree", "shortest_path"],
        expected_capability_id="cap:graph_traversal",
        expected_mobjects=["Graph"],
        expected_dimension="2D",
        description="Kruskal / Prim minimum spanning tree",
    ),

    # 5. Computational Geometry & Spatial
    BenchmarkTestCase(
        id="bm_geom_polygon_intersect",
        query="Find intersection of two geometric circles and fill overlapping polygon area",
        category="Computational Geometry",
        expected_domain="computational_geometry",
        expected_api_substrings=["intersection", "Polygon", "union"],
        expected_capability_id="cap:polygon_geometry_intersection",
        expected_mobjects=["Polygon", "Axes"],
        expected_dimension="2D",
        description="2D Boolean shape clipping and overlap polygon",
    ),
    BenchmarkTestCase(
        id="bm_geom_convex_hull",
        query="Compute and animate 2D Convex Hull for random point cloud",
        category="Computational Geometry",
        expected_domain="computational_geometry",
        expected_api_substrings=["ConvexHull", "convex_hull"],
        expected_capability_id="cap:spatial_convex_hull_voronoi",
        expected_mobjects=["Polygon", "Dot"],
        expected_dimension="2D",
        description="Quickhull spatial polygon enclosing",
    ),
    BenchmarkTestCase(
        id="bm_geom_voronoi",
        query="Visualize Voronoi diagram tessellation of seed points",
        category="Computational Geometry",
        expected_domain="computational_geometry",
        expected_api_substrings=["Voronoi", "Delaunay"],
        expected_capability_id="cap:spatial_convex_hull_voronoi",
        expected_mobjects=["Polygon", "Dot"],
        expected_dimension="2D",
        description="Voronoi partitioning and Delaunay dual",
    ),

    # 6. Linear Algebra & Transformations
    BenchmarkTestCase(
        id="bm_linalg_eigenvectors",
        query="Visualize 2D linear transformation and invariant eigenvectors",
        category="Linear Algebra",
        expected_domain="linear_algebra",
        expected_api_substrings=["eig", "eigh"],
        expected_capability_id="cap:eigen_decomposition",
        expected_mobjects=["Axes", "Arrow"],
        expected_dimension="2D",
        description="Eigenvalues and directional eigenvectors",
    ),
    BenchmarkTestCase(
        id="bm_linalg_svd",
        query="Compute Singular Value Decomposition SVD matrix deformation",
        category="Linear Algebra",
        expected_domain="linear_algebra",
        expected_api_substrings=["svd", "solve", "inv"],
        expected_capability_id="cap:matrix_transformation",
        expected_mobjects=["Axes", "Arrow"],
        expected_dimension="2D",
        description="SVD singular vectors and orthogonal rotation",
    ),

    # 7. Interpolation & Splines
    BenchmarkTestCase(
        id="bm_interp_cubic_spline",
        query="Fit and animate smooth cubic spline interpolation through control points",
        category="Interpolation",
        expected_domain="interpolation",
        expected_api_substrings=["CubicSpline", "make_interp_spline", "splrep"],
        expected_capability_id="cap:spline_interpolation",
        expected_mobjects=["Axes", "Dot", "ParametricFunction"],
        expected_dimension="2D",
        description="C2 continuous piecewise cubic polynomial interpolation",
    ),

    # 8. Signal Processing & Fourier
    BenchmarkTestCase(
        id="bm_signal_fft",
        query="Compute FFT frequency spectrum decomposition of audio signal",
        category="Signal Processing",
        expected_domain="signal_processing",
        expected_api_substrings=["fft", "ifft"],
        expected_capability_id="cap:fourier_transform",
        expected_mobjects=["Axes", "ParametricFunction"],
        expected_dimension="2D",
        description="Fast Fourier Transform harmonic decomposition",
    ),
    BenchmarkTestCase(
        id="bm_signal_fourier_series",
        query="Animate Fourier series epicycles reconstructing a square wave",
        category="Signal Processing",
        expected_domain="signal_processing",
        expected_api_substrings=["fft", "square", "diff", "series"],
        expected_capability_id="cap:fourier_transform",
        expected_mobjects=["Axes", "Circle", "Arrow"],
        expected_dimension="2D",
        description="Fourier harmonic epicycle progression",
    ),
]
