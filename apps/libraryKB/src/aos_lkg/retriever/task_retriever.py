"""TaskRetriever: Extracts the minimal, highly-relevant knowledge graph slice for any animation task."""

from __future__ import annotations

from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

from aos_lkg.schema.nodes import (
    BaseNode,
    NodeType,
    CapabilityNode,
    FunctionNode,
    ClassNode,
    ConceptNode,
    AlgorithmNode,
    ManimMappingNode,
    AnimationPatternNode,
    PrecisionRuleNode,
    CodeExampleNode,
)
from aos_lkg.schema.edges import EdgeType
from aos_lkg.storage.graph_store import GraphStore
from aos_lkg.storage.api_index import ApiIndex
from aos_lkg.storage.semantic_index import SemanticIndex, SearchResult
from aos_lkg.retriever.query_parser import QueryParser, ParsedQuery


def canonicalize_api_name(qualname: str) -> str:
    """Normalize internal private subpackage paths to clean public API imports."""
    parts = qualname.split(".")
    if len(parts) > 2:
        # e.g., scipy.optimize._zeros_py.brentq -> scipy.optimize.brentq
        # e.g., networkx.algorithms.shortest_paths.weighted.dijkstra_path -> networkx.dijkstra_path
        clean_parts = [p for p in parts if not p.startswith("_")]
        if len(clean_parts) >= 2:
            return f"{clean_parts[0]}.{clean_parts[1]}.{clean_parts[-1]}" if len(clean_parts) > 2 else qualname
    return qualname


class RetrievedSlice(BaseModel):
    """Structured, minimal knowledge slice designed for downstream LLM generation."""
    query: str
    parsed_intent: ParsedQuery
    primary_capability: Optional[CapabilityNode] = None
    primary_api: Optional[BaseNode] = None
    alternative_apis: List[BaseNode] = Field(default_factory=list)
    algorithms: List[AlgorithmNode] = Field(default_factory=list)
    concepts: List[ConceptNode] = Field(default_factory=list)
    manim_mappings: List[ManimMappingNode] = Field(default_factory=list)
    animation_patterns: List[AnimationPatternNode] = Field(default_factory=list)
    precision_rules: List[PrecisionRuleNode] = Field(default_factory=list)
    code_examples: List[CodeExampleNode] = Field(default_factory=list)
    matched_search_score: float = 0.0


class TaskRetriever:
    """Multi-stage hierarchical retriever mapping tasks to minimal graph slices."""

    def __init__(
        self,
        graph_store: GraphStore,
        api_index: ApiIndex,
        semantic_index: SemanticIndex,
    ):
        self.graph_store = graph_store
        self.api_index = api_index
        self.semantic_index = semantic_index

    def retrieve(self, query_str: str, max_alternatives: int = 3) -> RetrievedSlice:
        """Hierarchically retrieve the optimal knowledge slice for a user query."""
        parsed = QueryParser.parse(query_str)

        # 1. Hierarchical Stage 1: Retrieve Best Matching Capability
        cap_results = self.semantic_index.search(
            query=query_str,
            top_k=5,
            node_types=[NodeType.CAPABILITY],
            preferred_domains=parsed.detected_domains,
        )

        primary_cap: Optional[CapabilityNode] = None
        best_score = 0.0

        if cap_results:
            best_cap_node = self.graph_store.graph.get_node(cap_results[0].node_id)
            if isinstance(best_cap_node, CapabilityNode):
                primary_cap = best_cap_node
                best_score = cap_results[0].score

        # 2. Hierarchical Stage 2: Discover Candidate APIs Constrained by Capability & Domain
        candidate_apis: List[BaseNode] = []
        seen_api_base_names: Set[str] = set()

        def add_candidate(fn: BaseNode):
            base_key = fn.name
            if base_key not in seen_api_base_names:
                seen_api_base_names.add(base_key)
                candidate_apis.append(fn)

        # A) Pull APIs directly linked to primary capability in the graph
        if primary_cap:
            linked_apis = self.graph_store.get_apis_for_capability(primary_cap.id)
            for fn in linked_apis:
                add_candidate(fn)

            # Also resolve canonical APIs defined on capability node
            for canon_name in primary_cap.canonical_apis:
                entry = self.api_index.get_by_qualname(canon_name)
                if entry:
                    node = self.graph_store.graph.get_node(entry.id)
                    if isinstance(node, (FunctionNode, ClassNode)):
                        add_candidate(node)
                else:
                    # Search by short function name
                    short_name = canon_name.split(".")[-1]
                    for match_entry in self.api_index.search_by_name(short_name):
                        node = self.graph_store.graph.get_node(match_entry.id)
                        if isinstance(node, (FunctionNode, ClassNode)):
                            add_candidate(node)

        # B) Query semantic search for functions and classes with strict domain gating
        pref_domains = [primary_cap.domain] if primary_cap else parsed.detected_domains
        api_results = self.semantic_index.search(
            query=query_str,
            top_k=15,
            node_types=[NodeType.FUNCTION, NodeType.CLASS],
            preferred_domains=pref_domains,
        )

        for res in api_results:
            node = self.graph_store.graph.get_node(res.node_id)
            if isinstance(node, (FunctionNode, ClassNode)):
                # Strict domain compatibility check
                if primary_cap:
                    if primary_cap.domain == "differential_equations":
                        if "integrate" not in node.module.lower() and "ode" not in node.module.lower():
                            continue
                    elif primary_cap.domain == "root_finding":
                        if "optimize" not in node.module.lower() and "solvers" not in node.module.lower():
                            continue
                    elif primary_cap.domain == "graph_theory":
                        if "networkx" not in node.library.lower():
                            continue
                    elif primary_cap.domain == "computational_geometry":
                        if "shapely" not in node.library.lower() and "spatial" not in node.module.lower():
                            continue
                add_candidate(node)

        # Rank candidate APIs using query keyword alignment and capability relevance
        raw_tokens = [t.lower() for t in query_str.replace("'", " ").replace("-", " ").split() if len(t) > 2]

        def score_candidate(fn: BaseNode) -> float:
            score = 0.0
            fn_name_lower = fn.name.lower()
            fn_qual_lower = getattr(fn, "qualified_name", "").lower()

            matched_in_name = 0
            # Exact keyword in API name is the strongest signal
            for t in raw_tokens:
                if t in fn_name_lower:
                    score += 30.0
                    matched_in_name += 1
                elif t in fn_qual_lower:
                    score += 10.0

            # Strong boost for matching multiple query terms in function/class name
            if matched_in_name >= 2:
                score += (matched_in_name * 25.0)

            # High priority for APIs linked directly to the capability
            if primary_cap:
                if fn in linked_apis:
                    score += 10.0
                for idx, canon in enumerate(primary_cap.canonical_apis):
                    if canon.endswith(fn.name) or fn_qual_lower.endswith(canon.lower()):
                        score += 20.0 - (idx * 2.0)

            if fn.docstring:
                doc_lower = fn.docstring.lower()
                for t in raw_tokens:
                    if t in doc_lower:
                        score += 1.0

            return score

        candidate_apis.sort(key=score_candidate, reverse=True)

        primary_api: Optional[BaseNode] = candidate_apis[0] if candidate_apis else None
        alt_apis: List[BaseNode] = []

        if primary_api:
            # Add explicit graph ALTERNATIVE_TO relations
            for edge in self.graph_store.graph.edges:
                if edge.source == primary_api.id and edge.type == EdgeType.ALTERNATIVE_TO:
                    alt_node = self.graph_store.graph.get_node(edge.target)
                    if isinstance(alt_node, (FunctionNode, ClassNode)) and alt_node.name not in seen_api_base_names:
                        alt_apis.append(alt_node)
                        seen_api_base_names.add(alt_node.name)

            # Fill remaining distinct candidate APIs
            for c in candidate_apis[1:]:
                if c.name != primary_api.name and c.name not in [a.name for a in alt_apis]:
                    if len(alt_apis) < max_alternatives:
                        alt_apis.append(c)

        # 3. Retrieve connected Algorithms
        algorithms: List[AlgorithmNode] = []
        if primary_api:
            algorithms.extend(self.graph_store.get_algorithms_for_api(primary_api.id))
        if not algorithms and primary_cap:
            for algo in [n for n in self.graph_store.graph.nodes.values() if isinstance(n, AlgorithmNode)]:
                if algo.domain == primary_cap.domain and algo not in algorithms:
                    algorithms.append(algo)

        # 4. Retrieve connected Concepts
        concepts: List[ConceptNode] = []
        if primary_cap:
            for cid in primary_cap.concepts:
                c_node = self.graph_store.graph.get_node(cid)
                if isinstance(c_node, ConceptNode) and c_node not in concepts:
                    concepts.append(c_node)

        # 5. Retrieve Dimensionality-Aware Manim Mappings & Animation Patterns
        manim_mappings: List[ManimMappingNode] = []
        animation_patterns: List[AnimationPatternNode] = []

        is_3d = (parsed.dimension == "3D") or (primary_cap and primary_cap.dimension == "3D")
        is_1d = (parsed.dimension == "1D") or (primary_cap and primary_cap.dimension == "1D")

        # Select 3D / 1D / 2D primary mapping
        if is_3d:
            three_d_node = self.graph_store.graph.get_node("manim:ThreeDAxes")
            if isinstance(three_d_node, ManimMappingNode):
                manim_mappings.append(three_d_node)
            pat_3d = self.graph_store.graph.get_node("pattern:ode_trajectory_phase_space_3d")
            if isinstance(pat_3d, AnimationPatternNode):
                animation_patterns.append(pat_3d)
        elif is_1d:
            one_d_node = self.graph_store.graph.get_node("manim:NumberLine")
            if isinstance(one_d_node, ManimMappingNode):
                manim_mappings.append(one_d_node)

        if primary_cap:
            for mm in self.graph_store.get_manim_mappings_for_capability(primary_cap.id):
                if mm not in manim_mappings:
                    manim_mappings.append(mm)
            for pat in self.graph_store.get_animation_patterns(primary_cap.id):
                if pat not in animation_patterns:
                    animation_patterns.append(pat)

        if not manim_mappings:
            axes_node = self.graph_store.graph.get_node("manim:Axes")
            if isinstance(axes_node, ManimMappingNode):
                manim_mappings.append(axes_node)

        # 6. Retrieve Precision Rules
        precision_rules = self.graph_store.get_precision_rules(primary_cap.id if primary_cap else None)

        # 7. Retrieve Code Examples
        code_examples: List[CodeExampleNode] = []
        if primary_api:
            code_examples.extend(self.graph_store.get_examples_for_api(primary_api.id))
            for ex in [n for n in self.graph_store.graph.nodes.values() if isinstance(n, CodeExampleNode)]:
                if ex.target_api == primary_api.qualified_name or primary_api.qualified_name.endswith(ex.target_api):
                    if ex not in code_examples:
                        code_examples.append(ex)

        if not code_examples and primary_cap:
            for ex in [n for n in self.graph_store.graph.nodes.values() if isinstance(n, CodeExampleNode)]:
                if any(api in ex.target_api for api in primary_cap.canonical_apis):
                    if ex not in code_examples:
                        code_examples.append(ex)

        return RetrievedSlice(
            query=query_str,
            parsed_intent=parsed,
            primary_capability=primary_cap,
            primary_api=primary_api,
            alternative_apis=alt_apis[:max_alternatives],
            algorithms=algorithms,
            concepts=concepts,
            manim_mappings=manim_mappings[:3],
            animation_patterns=animation_patterns[:2],
            precision_rules=precision_rules[:3],
            code_examples=code_examples[:2],
            matched_search_score=best_score,
        )
