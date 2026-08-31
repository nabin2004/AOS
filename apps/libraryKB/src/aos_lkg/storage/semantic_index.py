"""SemanticIndex: BM25 and multi-field semantic retrieval over LKG nodes and capabilities."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from aos_lkg.schema.nodes import (
    BaseNode,
    NodeType,
    LibraryNode,
    ModuleNode,
    ClassNode,
    CapabilityNode,
    FunctionNode,
    ConceptNode,
    AlgorithmNode,
    ManimMappingNode,
    AnimationPatternNode,
)
from aos_lkg.schema.graph import KnowledgeGraph


MATH_SYNONYMS: Dict[str, List[str]] = {
    "root": ["zero", "intercept", "crossing", "solve", "brentq", "newton", "root_scalar"],
    "zero": ["root", "intercept", "crossing", "null"],
    "newton": ["tangent", "iteration", "raphson", "derivative", "root_finding"],
    "brent": ["bracket", "bisection", "zero_crossing", "continuous"],
    "integral": ["quadrature", "area", "riemann", "quad", "calculus", "integrate", "simpson"],
    "derivative": ["tangent", "slope", "diff", "rate_of_change", "calculus"],
    "ode": ["differential_equation", "ivp", "runge_kutta", "rk45", "solve_ivp", "trajectory", "lorenz", "attractor", "chaos", "dynamical"],
    "lorenz": ["attractor", "ode", "solve_ivp", "rk45", "phase_portrait", "trajectory", "differential_equations", "chaos"],
    "attractor": ["lorenz", "ode", "solve_ivp", "trajectory", "phase_space", "chaos", "dynamical_system"],
    "chaos": ["lorenz", "attractor", "ode", "solve_ivp", "trajectory", "dynamical"],
    "shortest_path": ["dijkstra", "astar", "distance", "pathfinding", "graph"],
    "dijkstra": ["shortest_path", "graph", "weighted", "priority_queue"],
    "intersection": ["overlap", "polygon", "shapely", "cross", "boolean", "clipping"],
    "spline": ["interpolation", "smooth_curve", "bspline", "cubicspline", "bezier"],
    "eigen": ["eigenvalue", "eigenvector", "decomposition", "matrix_transformation"],
    "fourier": ["fft", "spectrum", "frequency", "harmonics", "ifft", "epicycles"],
    "gradient": ["descent", "optimization", "minimize", "loss", "cost"],
    "manim": ["animation", "mobject", "axes", "scene", "graph", "render"],
}

# Domain conflict matrix: domains that should strongly penalize each other for specialized tasks
DOMAIN_EXCLUSIONS = {
    "differential_equations": {"graph_theory"},
    "graph_theory": {"differential_equations", "calculus"},
    "root_finding": {"graph_theory"},
}


def tokenize(text: str) -> List[str]:
    """Tokenize and normalize text into clean lower-case alphanumeric tokens."""
    if not text:
        return []
    tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    expanded = []
    for t in tokens:
        expanded.append(t)
        if "_" in t:
            expanded.extend([part for part in t.split("_") if part])
        if "." in t:
            expanded.extend([part for part in t.split(".") if part])
    return expanded


def infer_node_domain(node: BaseNode) -> Optional[str]:
    """Infer mathematical domain for any node type."""
    if isinstance(node, (CapabilityNode, ConceptNode, AlgorithmNode)):
        return node.domain
    if isinstance(node, ManimMappingNode):
        return "mathematical_animation"
    if isinstance(node, LibraryNode):
        lname = node.name.lower()
        if "manim" in lname:
            return "mathematical_animation"
        if "scipy" in lname:
            return "calculus"
        if "numpy" in lname:
            return "linear_algebra"
        if "sympy" in lname:
            return "symbolic_algebra"
        if "networkx" in lname:
            return "graph_theory"
        if "shapely" in lname:
            return "computational_geometry"
        if "mpmath" in lname:
            return "special_functions"
    if isinstance(node, (FunctionNode, ClassNode)):
        if "manim" in node.library.lower():
            return "mathematical_animation"
        mod = node.module.lower()
        if "integrate" in mod or "ode" in mod:
            return "differential_equations"
        if "optimize" in mod or "zeros" in mod:
            return "root_finding"
        if "linalg" in mod:
            return "linear_algebra"
        if "fft" in mod or "signal" in mod:
            return "signal_processing"
        if "networkx" in node.library.lower() or "graph" in mod:
            return "graph_theory"
        if "shapely" in node.library.lower() or "spatial" in mod or "geometry" in mod:
            return "computational_geometry"
        if "interpolate" in mod:
            return "interpolation"
        if "solvers" in mod or "calculus" in mod or "sympy" in node.library.lower():
            return "symbolic_algebra"
    if isinstance(node, ModuleNode):
        if "manim" in node.library.lower():
            return "mathematical_animation"
        qmod = node.qualified_name.lower()
        if "integrate" in qmod:
            return "differential_equations"
        if "optimize" in qmod:
            return "root_finding"
        if "linalg" in qmod:
            return "linear_algebra"
        if "spatial" in qmod or "geometry" in qmod:
            return "computational_geometry"
        if "networkx" in qmod:
            return "graph_theory"
        if "interpolate" in qmod:
            return "interpolation"
    return None


class SearchResult(BaseModel):
    node_id: str
    node_type: NodeType
    domain: Optional[str] = None
    score: float
    matched_terms: List[str] = Field(default_factory=list)


class SemanticIndex:
    """Inverted index with BM25 scoring tailored for mathematical and library semantics."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_term_freqs: Dict[str, Counter] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.inverted_index: Dict[str, Set[str]] = defaultdict(set)
        self.node_types: Dict[str, NodeType] = {}
        self.node_domains: Dict[str, Optional[str]] = {}
        self.avg_doc_len: float = 0.0
        self.num_docs: int = 0

    @classmethod
    def from_knowledge_graph(cls, kg: KnowledgeGraph) -> SemanticIndex:
        index = cls()
        for node in kg.nodes.values():
            index.index_node(node)
        index.finalize()
        return index

    def index_node(self, node: BaseNode) -> None:
        """Index a single graph node into the inverted index."""
        text_corpus = []

        # High-weight terms (Name, ID, Domain)
        text_corpus.extend([node.name] * 3)
        text_corpus.append(node.id)
        text_corpus.extend(node.tags * 3)

        domain = infer_node_domain(node)
        self.node_domains[node.id] = domain

        if domain:
            text_corpus.extend([domain] * 3)

        if node.docstring:
            text_corpus.append(node.docstring)

        if isinstance(node, CapabilityNode):
            text_corpus.extend([node.domain] * 4)
            text_corpus.extend([node.description] * 2)
            text_corpus.extend(node.canonical_apis * 3)
            text_corpus.extend(node.concepts * 2)
        elif isinstance(node, FunctionNode):
            text_corpus.extend([node.qualified_name] * 3)
            text_corpus.extend(node.capabilities * 3)
            text_corpus.extend(node.concepts * 2)
            text_corpus.extend(node.algorithms * 2)
        elif isinstance(node, ClassNode):
            text_corpus.extend([node.qualified_name] * 3)
            text_corpus.extend(node.bases * 2)
            text_corpus.extend([m for m in node.methods if not m.startswith("_")][:10])
            text_corpus.extend(getattr(node, "capabilities", []) * 3)
            text_corpus.extend(getattr(node, "concepts", []) * 2)
            text_corpus.extend(getattr(node, "algorithms", []) * 2)
        elif isinstance(node, LibraryNode):
            text_corpus.extend([node.name] * 5)
            if node.description:
                text_corpus.append(node.description)
        elif isinstance(node, ModuleNode):
            text_corpus.extend([node.qualified_name] * 4)
            text_corpus.extend(node.submodules * 2)
            text_corpus.extend(node.exported_symbols[:20])
        elif isinstance(node, ConceptNode):
            text_corpus.extend([node.domain] * 3)
            text_corpus.append(node.description)
            if node.formal_definition:
                text_corpus.append(node.formal_definition)
        elif isinstance(node, AlgorithmNode):
            text_corpus.extend([node.domain] * 3)
            text_corpus.append(node.description)
        elif isinstance(node, ManimMappingNode):
            text_corpus.extend(node.mobject_classes * 4)
            text_corpus.append(node.visual_role)
            text_corpus.append(node.coordinate_adapter)
            text_corpus.append(node.construction_pattern)
            text_corpus.extend(node.best_practices)
        elif isinstance(node, AnimationPatternNode):
            text_corpus.extend([node.pattern_name or node.name] * 3)
            text_corpus.append(node.description)
            text_corpus.extend(node.step_sequence)

        tokens = tokenize(" ".join(text_corpus))
        self.doc_term_freqs[node.id] = Counter(tokens)
        self.doc_lengths[node.id] = len(tokens)
        self.node_types[node.id] = node.type

        for term in set(tokens):
            self.inverted_index[term].add(node.id)

    def finalize(self) -> None:
        """Compute dataset-wide statistics for BM25."""
        self.num_docs = len(self.doc_lengths)
        total_len = sum(self.doc_lengths.values())
        self.avg_doc_len = (total_len / self.num_docs) if self.num_docs > 0 else 1.0

    def search(
        self,
        query: str,
        top_k: int = 10,
        node_types: Optional[List[NodeType]] = None,
        preferred_domains: Optional[List[str]] = None,
        disallowed_domains: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """Search the index using query tokenization, synonym expansion, domain gating, and BM25 ranking."""
        raw_tokens = tokenize(query)
        expanded_tokens: Set[str] = set(raw_tokens)

        # Expand math synonyms
        for t in raw_tokens:
            if t in MATH_SYNONYMS:
                expanded_tokens.update(MATH_SYNONYMS[t])

        scores: Dict[str, float] = defaultdict(float)
        matches: Dict[str, List[str]] = defaultdict(list)

        # Auto-compute disallowed domains from exclusions if preferred domains exist
        active_disallowed: Set[str] = set(disallowed_domains or [])
        if preferred_domains:
            for p_dom in preferred_domains:
                if p_dom in DOMAIN_EXCLUSIONS:
                    active_disallowed.update(DOMAIN_EXCLUSIONS[p_dom])

        for token in expanded_tokens:
            posting = self.inverted_index.get(token, set())
            df = len(posting)
            if df == 0:
                continue

            idf = math.log(1.0 + (self.num_docs - df + 0.5) / (df + 0.5))

            for doc_id in posting:
                if node_types and self.node_types.get(doc_id) not in node_types:
                    continue

                doc_domain = self.node_domains.get(doc_id)

                # Hard domain rejection for severe mismatches (e.g. graph_theory when query is ODE/Lorenz)
                if doc_domain and doc_domain in active_disallowed:
                    continue

                tf = self.doc_term_freqs[doc_id][token]
                doc_len = self.doc_lengths.get(doc_id, 1)

                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                term_score = idf * (numerator / denominator)

                # Give weight boost to original query tokens
                if token in raw_tokens:
                    term_score *= 1.8

                # Priority boost for Capability, Function, Class, and Manim mapping nodes
                ntype = self.node_types.get(doc_id)
                if ntype == NodeType.CAPABILITY:
                    term_score *= 2.0
                elif ntype in (NodeType.FUNCTION, NodeType.CLASS):
                    term_score *= 1.2
                elif ntype == NodeType.MANIM_MAPPING:
                    term_score *= 1.5

                # Domain match boost
                if preferred_domains and doc_domain in preferred_domains:
                    term_score *= 2.5

                scores[doc_id] += term_score
                matches[doc_id].append(token)

        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return [
            SearchResult(
                node_id=doc_id,
                node_type=self.node_types[doc_id],
                domain=self.node_domains.get(doc_id),
                score=round(score, 4),
                matched_terms=matches[doc_id],
            )
            for doc_id, score in sorted_docs
        ]
