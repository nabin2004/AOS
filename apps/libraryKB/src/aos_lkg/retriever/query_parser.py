"""QueryParser: Analyzes user animation requests to detect domain, dimensionality, constraints, and intent."""

from __future__ import annotations

import re
from typing import List, Optional, Set
from pydantic import BaseModel, Field


class ParsedQuery(BaseModel):
    raw_query: str
    detected_domains: List[str] = Field(default_factory=list)
    dimension: str = "2D"
    math_entities: List[str] = Field(default_factory=list)
    prefers_symbolic: bool = False
    prefers_numerical: bool = True
    target_mobjects: List[str] = Field(default_factory=list)


DOMAIN_KEYWORDS = {
    "root_finding": ["root", "zero", "brentq", "newton", "bisect", "crossing", "solve", "sqrt", "equation"],
    "calculus": ["integral", "derivative", "riemann", "area", "quad", "calculus", "tangent", "quadrature", "simpson"],
    "differential_equations": [
        "ode", "ivp", "lorenz", "attractor", "chaos", "chaotic", "runge_kutta", "rk45", "phase", "trajectory",
        "dynamical", "rossler", "pendulum", "double pendulum", "predator", "prey", "orbit", "vector field"
    ],
    "interpolation": ["spline", "interpolate", "smooth", "curve", "cubic_spline", "bspline", "bezier"],
    "linear_algebra": ["matrix", "eigen", "eigenvalue", "eigenvector", "svd", "transformation", "vector", "basis", "pca"],
    "graph_theory": ["graph", "dijkstra", "shortest_path", "bfs", "dfs", "tree", "mst", "network", "node", "edge", "spanning"],
    "computational_geometry": ["polygon", "intersection", "convex_hull", "voronoi", "delaunay", "hull", "shapely", "clipping"],
    "signal_processing": ["fourier", "fft", "frequency", "harmonics", "spectrum", "epicycles"],
    "optimization": ["gradient descent", "minimize", "optimize", "objective", "loss function", "cost function"],
}

MOBJECT_KEYWORDS = {
    "ThreeDAxes": ["threedaxes", "3d axes", "3d", "lorenz", "surface", "sphere", "space curve", "attractor", "three d"],
    "Axes": ["axes", "plot", "function", "curve", "cartesian"],
    "NumberLine": ["number line", "numberline", "1d", "scalar axis"],
    "Dot": ["dot", "point", "marker", "vertex"],
    "Graph": ["graph", "nodes", "network"],
    "Polygon": ["polygon", "shape", "region", "hull"],
    "ValueTracker": ["tracker", "dynamic", "animate value", "slider"],
    "MathTex": ["latex", "formula", "equation", "text"],
}


class QueryParser:
    """Extracts intent and domain hints from natural language animation queries."""

    @staticmethod
    def parse(query: str) -> ParsedQuery:
        q_lower = query.lower()
        detected_domains: Set[str] = set()

        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", q_lower):
                    detected_domains.add(domain)

        # Detect Mobject mentions
        target_mobjects: Set[str] = set()
        for mob, keywords in MOBJECT_KEYWORDS.items():
            for kw in keywords:
                if kw in q_lower:
                    target_mobjects.add(mob)

        # Determine spatial dimensionality
        dimension = "2D"
        if any(w in q_lower for w in ["3d", "three-d", "threed", "lorenz", "attractor", "rossler", "sphere", "surface", "spatial 3d"]):
            dimension = "3D"
            target_mobjects.add("ThreeDAxes")
        elif any(w in q_lower for w in ["1d", "number line", "bisection interval", "scalar line"]):
            dimension = "1D"

        # Check symbolic vs numerical preference
        prefers_symbolic = any(
            w in q_lower for w in ["exact", "symbolic", "closed form", "closed-form", "analytic", "sympy"]
        )
        prefers_numerical = not prefers_symbolic or any(
            w in q_lower for w in ["numerical", "scipy", "approximate", "simulate", "step-by-step", "iteration", "ode", "solve_ivp"]
        )

        # Extract mathematical formulas or expressions
        math_entities = re.findall(r"([a-zA-Z]\(x\)|x\^?[0-9]+|[0-9]+\.[0-9]+|\\sqrt\{?[0-9]+\}?|sqrt\([0-9]+\))", query)

        return ParsedQuery(
            raw_query=query,
            detected_domains=sorted(list(detected_domains)),
            dimension=dimension,
            math_entities=math_entities,
            prefers_symbolic=prefers_symbolic,
            prefers_numerical=prefers_numerical,
            target_mobjects=sorted(list(target_mobjects)),
        )
