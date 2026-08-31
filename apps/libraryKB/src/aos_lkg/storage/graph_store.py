"""GraphStore: Persistence (JSONL) and NetworkX traversal engine for the AOS LKG."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import networkx as nx

from aos_lkg.schema.nodes import (
    BaseNode,
    NodeType,
    FunctionNode,
    CapabilityNode,
    ConceptNode,
    AlgorithmNode,
    ManimMappingNode,
    AnimationPatternNode,
    PrecisionRuleNode,
    CodeExampleNode,
)
from aos_lkg.schema.edges import Edge, EdgeType
from aos_lkg.schema.graph import KnowledgeGraph, parse_node_dict


class GraphStore:
    """Manages LKG graph persistence (JSONL) and NetworkX multi-hop traversals."""

    def __init__(self, graph: Optional[KnowledgeGraph] = None):
        self.graph: KnowledgeGraph = graph or KnowledgeGraph()
        self._nx_graph: Optional[nx.MultiDiGraph] = None

    @property
    def nx_graph(self) -> nx.MultiDiGraph:
        """Cached NetworkX MultiDiGraph representation."""
        if self._nx_graph is None:
            self._nx_graph = self.graph.to_networkx()
        return self._nx_graph

    def invalidate_cache(self) -> None:
        self._nx_graph = None

    def save_jsonl(self, filepath: str | Path) -> None:
        """Save KnowledgeGraph to JSONL format."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for node in self.graph.nodes.values():
                record = {"record_type": "node", "data": node.model_dump()}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            for edge in self.graph.edges:
                record = {"record_type": "edge", "data": edge.model_dump()}
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    @classmethod
    def load_jsonl(cls, filepath: str | Path) -> GraphStore:
        """Load KnowledgeGraph from JSONL format."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Knowledge graph file not found: {path}")

        kg = KnowledgeGraph()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                rec_type = record.get("record_type")
                data = record.get("data", {})

                if rec_type == "node":
                    node = parse_node_dict(data)
                    kg.add_node(node)
                elif rec_type == "edge":
                    edge = Edge(**data)
                    kg.add_edge(edge)

        return cls(kg)

    # --- TRAVERSAL & QUERY METHODS ---

    def get_apis_for_capability(self, cap_id: str) -> List[BaseNode]:
        """Find all FunctionNodes and ClassNodes providing a specific capability."""
        apis: List[BaseNode] = []
        for edge in self.graph.edges:
            if edge.target == cap_id and edge.type == EdgeType.PROVIDES:
                node = self.graph.get_node(edge.source)
                if isinstance(node, (FunctionNode, ClassNode)):
                    apis.append(node)
        return apis

    def get_manim_mappings_for_capability(self, cap_id: str) -> List[ManimMappingNode]:
        """Find all ManimMappingNodes connected to a capability."""
        mappings: List[ManimMappingNode] = []
        for edge in self.graph.edges:
            if edge.source == cap_id and edge.type == EdgeType.VISUALIZES_WITH:
                node = self.graph.get_node(edge.target)
                if isinstance(node, ManimMappingNode):
                    mappings.append(node)
        return mappings

    def get_animation_patterns(self, cap_id: str) -> List[AnimationPatternNode]:
        """Find all AnimationPatternNodes associated with a capability."""
        patterns: List[AnimationPatternNode] = []
        for edge in self.graph.edges:
            if edge.source == cap_id and edge.type == EdgeType.ANIMATES_VIA:
                node = self.graph.get_node(edge.target)
                if isinstance(node, AnimationPatternNode):
                    patterns.append(node)
        return patterns

    def get_precision_rules(self, cap_id: Optional[str] = None) -> List[PrecisionRuleNode]:
        """Retrieve relevant PrecisionRuleNodes."""
        rules: List[PrecisionRuleNode] = []
        if cap_id:
            for edge in self.graph.edges:
                if edge.source == cap_id and edge.type == EdgeType.GOVERNED_BY:
                    node = self.graph.get_node(edge.target)
                    if isinstance(node, PrecisionRuleNode):
                        rules.append(node)
        if not rules:
            # Return all general precision rules
            rules = [n for n in self.graph.nodes.values() if isinstance(n, PrecisionRuleNode)]
        return rules

    def get_algorithms_for_api(self, api_id: str) -> List[AlgorithmNode]:
        """Find algorithms implemented by an API."""
        algos: List[AlgorithmNode] = []
        for edge in self.graph.edges:
            if edge.source == api_id and edge.type == EdgeType.IMPLEMENTS:
                node = self.graph.get_node(edge.target)
                if isinstance(node, AlgorithmNode):
                    algos.append(node)
        return algos

    def get_examples_for_api(self, api_id: str) -> List[CodeExampleNode]:
        """Find verified code examples attached to an API."""
        examples: List[CodeExampleNode] = []
        for edge in self.graph.edges:
            if edge.source == api_id and edge.type == EdgeType.HAS_EXAMPLE:
                node = self.graph.get_node(edge.target)
                if isinstance(node, CodeExampleNode):
                    examples.append(node)
        return examples

    def get_minimal_subgraph(
        self,
        seed_node_ids: List[str],
        depth: int = 2,
    ) -> KnowledgeGraph:
        """Extract minimal connected subgraph starting from seed nodes."""
        G = self.nx_graph
        subgraph_nodes: Set[str] = set()

        for seed in seed_node_ids:
            if seed in G:
                subgraph_nodes.add(seed)
                # Forward and backward BFS neighborhood
                frontier = {seed}
                for _ in range(depth):
                    next_frontier = set()
                    for node in frontier:
                        # Successors
                        for succ in G.successors(node):
                            if succ not in subgraph_nodes:
                                subgraph_nodes.add(succ)
                                next_frontier.add(succ)
                        # Predecessors (e.g. Function -> Capability)
                        for pred in G.predecessors(node):
                            if pred not in subgraph_nodes:
                                subgraph_nodes.add(pred)
                                next_frontier.add(pred)
                    frontier = next_frontier

        # Construct new KnowledgeGraph from extracted nodes and induced edges
        sub_kg = KnowledgeGraph()
        for nid in subgraph_nodes:
            node = self.graph.get_node(nid)
            if node:
                sub_kg.add_node(node)

        for edge in self.graph.edges:
            if edge.source in subgraph_nodes and edge.target in subgraph_nodes:
                sub_kg.add_edge(edge)

        return sub_kg
