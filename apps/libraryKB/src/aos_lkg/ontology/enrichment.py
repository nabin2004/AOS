"""Semantic enrichment engine for connecting raw API nodes to Capabilities, Concepts, Algorithms, and Manim mappings."""

from __future__ import annotations

from typing import Dict, List, Optional
from aos_lkg.schema.nodes import FunctionNode, ClassNode, NodeType
from aos_lkg.schema.edges import Edge, EdgeType
from aos_lkg.schema.graph import KnowledgeGraph
from aos_lkg.ontology.capabilities import (
    CAPABILITY_DEFINITIONS,
    CONCEPT_DEFINITIONS,
    ALGORITHM_DEFINITIONS,
)
from aos_lkg.ontology.manim_mappings import (
    MANIM_MAPPING_DEFINITIONS,
    ANIMATION_PATTERN_DEFINITIONS,
    PRECISION_RULE_DEFINITIONS,
    CODE_EXAMPLE_DEFINITIONS,
)


API_CAPABILITY_MAPPINGS: Dict[str, List[str]] = {
    # SciPy Optimize
    "scipy.optimize.brentq": ["cap:root_finding_bracketed"],
    "scipy.optimize.brenth": ["cap:root_finding_bracketed"],
    "scipy.optimize.bisect": ["cap:root_finding_bracketed"],
    "scipy.optimize.ridder": ["cap:root_finding_bracketed"],
    "scipy.optimize.newton": ["cap:root_finding_newton"],
    "scipy.optimize.root_scalar": ["cap:root_finding_bracketed", "cap:root_finding_newton"],
    "scipy.optimize.minimize_scalar": ["cap:root_finding_newton"],
    "scipy.optimize.minimize": ["cap:root_finding_newton"],
    "scipy.optimize.least_squares": ["cap:root_finding_newton"],

    # SymPy
    "sympy.solvers.solve": ["cap:symbolic_equation_solving"],
    "sympy.solvers.solveset": ["cap:symbolic_equation_solving"],
    "sympy.solvers.nsolve": ["cap:symbolic_equation_solving", "cap:root_finding_newton"],
    "sympy.diff": ["cap:symbolic_calculus"],
    "sympy.integrate": ["cap:symbolic_calculus"],
    "sympy.series": ["cap:symbolic_calculus"],
    "sympy.limit": ["cap:symbolic_calculus"],

    # SciPy Integrate
    "scipy.integrate.quad": ["cap:numerical_integration"],
    "scipy.integrate.dblquad": ["cap:numerical_integration"],
    "scipy.integrate.trapezoid": ["cap:numerical_integration"],
    "scipy.integrate.cumulative_trapezoid": ["cap:numerical_integration"],
    "scipy.integrate.solve_ivp": ["cap:ode_integration"],
    "scipy.integrate.odeint": ["cap:ode_integration"],

    # SciPy Interpolate
    "scipy.interpolate.CubicSpline": ["cap:spline_interpolation"],
    "scipy.interpolate.make_interp_spline": ["cap:spline_interpolation"],
    "scipy.interpolate.splrep": ["cap:spline_interpolation"],
    "scipy.interpolate.splev": ["cap:spline_interpolation"],

    # Linear Algebra
    "scipy.linalg.eig": ["cap:eigen_decomposition"],
    "numpy.linalg.eig": ["cap:eigen_decomposition"],
    "scipy.linalg.eigh": ["cap:eigen_decomposition"],
    "scipy.linalg.svd": ["cap:matrix_transformation"],
    "scipy.linalg.solve": ["cap:matrix_transformation"],
    "numpy.linalg.solve": ["cap:matrix_transformation"],
    "scipy.linalg.inv": ["cap:matrix_transformation"],

    # Graph Theory
    "networkx.shortest_path": ["cap:graph_shortest_path"],
    "networkx.dijkstra_path": ["cap:graph_shortest_path"],
    "networkx.astar_path": ["cap:graph_shortest_path"],
    "networkx.shortest_path_length": ["cap:graph_shortest_path"],
    "networkx.bfs_edges": ["cap:graph_traversal"],
    "networkx.dfs_edges": ["cap:graph_traversal"],
    "networkx.minimum_spanning_tree": ["cap:graph_traversal"],
    "networkx.spring_layout": ["cap:graph_traversal"],

    # Computational Geometry & Spatial
    "shapely.intersection": ["cap:polygon_geometry_intersection"],
    "shapely.union": ["cap:polygon_geometry_intersection"],
    "shapely.difference": ["cap:polygon_geometry_intersection"],
    "shapely.convex_hull": ["cap:polygon_geometry_intersection", "cap:spatial_convex_hull_voronoi"],
    "shapely.voronoi_polygons": ["cap:spatial_convex_hull_voronoi"],
    "scipy.spatial.ConvexHull": ["cap:spatial_convex_hull_voronoi"],
    "scipy.spatial.Voronoi": ["cap:spatial_convex_hull_voronoi"],
    "scipy.spatial.Delaunay": ["cap:spatial_convex_hull_voronoi"],
    "scipy.spatial.voronoi_plot_2d": ["cap:spatial_convex_hull_voronoi"],

    # Signal & FFT
    "scipy.fft.fft": ["cap:fourier_transform"],
    "scipy.fft.ifft": ["cap:fourier_transform"],
    "numpy.fft.fft": ["cap:fourier_transform"],

    # Special Functions
    "scipy.special.gamma": ["cap:special_functions"],
    "scipy.special.jv": ["cap:special_functions"],
    "scipy.special.legendre": ["cap:special_functions"],
    "scipy.special.erf": ["cap:special_functions"],
}

API_ALGORITHM_MAPPINGS: Dict[str, List[str]] = {
    "scipy.optimize.brentq": ["algo:brent_dekker"],
    "scipy.optimize.newton": ["algo:newton_raphson"],
    "networkx.dijkstra_path": ["algo:dijkstra"],
    "networkx.shortest_path": ["algo:dijkstra"],
    "scipy.integrate.solve_ivp": ["algo:rk45_dormand_prince"],
    "scipy.integrate.odeint": ["algo:rk45_dormand_prince"],
    "scipy.spatial.ConvexHull": ["algo:quickhull"],
}

CAPABILITY_PATTERN_MAPPINGS: Dict[str, List[str]] = {
    "cap:root_finding_bracketed": ["pattern:bracket_bisection_narrowing"],
    "cap:root_finding_newton": ["pattern:iterative_tangent_descent"],
    "cap:numerical_integration": ["pattern:riemann_sum_limit"],
    "cap:graph_shortest_path": ["pattern:dijkstra_frontier_expansion"],
    "cap:ode_integration": ["pattern:ode_trajectory_phase_space_3d"],
}

API_ALTERNATIVES: List[tuple[str, str]] = [
    ("scipy.optimize.brentq", "scipy.optimize.bisect"),
    ("scipy.optimize.brentq", "scipy.optimize.newton"),
    ("scipy.optimize.brentq", "scipy.optimize.root_scalar"),
    ("scipy.optimize.brentq", "sympy.solvers.nsolve"),
    ("scipy.integrate.quad", "scipy.integrate.trapezoid"),
    ("scipy.integrate.quad", "sympy.integrate"),
    ("scipy.integrate.solve_ivp", "scipy.integrate.odeint"),
    ("networkx.dijkstra_path", "networkx.astar_path"),
    ("shapely.intersection", "scipy.optimize.root_scalar"),
]


def enrich_knowledge_graph(kg: KnowledgeGraph) -> KnowledgeGraph:
    """
    Enrich a base KnowledgeGraph with curated ontology nodes and semantic relationships.
    """
    # 1. Add all Curated Ontological Nodes
    for cap in CAPABILITY_DEFINITIONS:
        kg.add_node(cap)
    for concept in CONCEPT_DEFINITIONS:
        kg.add_node(concept)
    for algo in ALGORITHM_DEFINITIONS:
        kg.add_node(algo)
    for manim_m in MANIM_MAPPING_DEFINITIONS:
        kg.add_node(manim_m)
    for pattern in ANIMATION_PATTERN_DEFINITIONS:
        kg.add_node(pattern)
    for rule in PRECISION_RULE_DEFINITIONS:
        kg.add_node(rule)
    for ex in CODE_EXAMPLE_DEFINITIONS:
        kg.add_node(ex)

    # 2. Build index of API (function and class) nodes by qualified name, short name, and direct name
    api_by_qualname: Dict[str, str] = {}
    for node_id, node in kg.nodes.items():
        if isinstance(node, (FunctionNode, ClassNode)):
            api_by_qualname[node.qualified_name] = node_id
            parts = node.qualified_name.split(".")
            if len(parts) >= 2:
                short_qual = f"{parts[0]}.{parts[1]}.{parts[-1]}" if len(parts) > 2 else node.qualified_name
                api_by_qualname[short_qual] = node_id
            if len(parts) >= 3:
                api_by_qualname[f"{parts[0]}.{parts[-1]}"] = node_id

    # 3. Connect Capabilities to Concepts, Manim Mappings, Patterns, and Rules
    for cap in CAPABILITY_DEFINITIONS:
        for concept_id in cap.concepts:
            if kg.get_node(concept_id):
                kg.add_edge(Edge(source=cap.id, target=concept_id, type=EdgeType.USEFUL_FOR))

        for manim_id in cap.manim_targets:
            if kg.get_node(manim_id):
                kg.add_edge(Edge(source=cap.id, target=manim_id, type=EdgeType.VISUALIZES_WITH))

        if cap.id in CAPABILITY_PATTERN_MAPPINGS:
            for pat_id in CAPABILITY_PATTERN_MAPPINGS[cap.id]:
                if kg.get_node(pat_id):
                    kg.add_edge(Edge(source=cap.id, target=pat_id, type=EdgeType.ANIMATES_VIA))

    # Connect Precision Rules broadly
    for rule in PRECISION_RULE_DEFINITIONS:
        for cap in CAPABILITY_DEFINITIONS:
            kg.add_edge(Edge(source=cap.id, target=rule.id, type=EdgeType.GOVERNED_BY))

    # Connect Code Examples
    for ex in CODE_EXAMPLE_DEFINITIONS:
        if ex.target_api in api_by_qualname:
            matched_id = api_by_qualname[ex.target_api]
            kg.add_edge(Edge(source=matched_id, target=ex.id, type=EdgeType.HAS_EXAMPLE))

    # 4. Connect Extracted Functions and Classes to Capabilities & Algorithms
    for api_name, cap_ids in API_CAPABILITY_MAPPINGS.items():
        matched_id = api_by_qualname.get(api_name)
        if matched_id:
            api_node = kg.get_node(matched_id)
            if isinstance(api_node, (FunctionNode, ClassNode)):
                for cap_id in cap_ids:
                    if hasattr(api_node, "capabilities") and cap_id not in api_node.capabilities:
                        api_node.capabilities.append(cap_id)
                    kg.add_edge(Edge(source=matched_id, target=cap_id, type=EdgeType.PROVIDES))

    for api_name, algo_ids in API_ALGORITHM_MAPPINGS.items():
        matched_id = api_by_qualname.get(api_name)
        if matched_id:
            api_node = kg.get_node(matched_id)
            if isinstance(api_node, (FunctionNode, ClassNode)):
                for algo_id in algo_ids:
                    if hasattr(api_node, "algorithms") and algo_id not in api_node.algorithms:
                        api_node.algorithms.append(algo_id)
                    kg.add_edge(Edge(source=matched_id, target=algo_id, type=EdgeType.IMPLEMENTS))

    # 5. Connect Alternative APIs
    for api1, api2 in API_ALTERNATIVES:
        id1 = api_by_qualname.get(api1)
        id2 = api_by_qualname.get(api2)
        if id1 and id2:
            kg.add_edge(Edge(source=id1, target=id2, type=EdgeType.ALTERNATIVE_TO))
            kg.add_edge(Edge(source=id2, target=id1, type=EdgeType.ALTERNATIVE_TO))

    # 6. Connect Crawled Manim Classes to Curated ManimMappingNodes
    for manim_m in MANIM_MAPPING_DEFINITIONS:
        for mob_cls_name in manim_m.mobject_classes:
            for node in list(kg.nodes.values()):
                if isinstance(node, ClassNode) and node.library == "manim" and node.name == mob_cls_name:
                    kg.add_edge(Edge(source=node.id, target=manim_m.id, type=EdgeType.IMPLEMENTS))
                    kg.add_edge(Edge(source=manim_m.id, target=node.id, type=EdgeType.DEFINES))

    return kg
