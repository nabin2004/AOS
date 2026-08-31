"""Graph container model with serialization and NetworkX bridge."""

from __future__ import annotations

from typing import Dict, List, Optional, Union
import json
import networkx as nx
from pydantic import BaseModel, Field

from aos_lkg.schema.nodes import (
    BaseNode,
    NodeType,
    LibraryNode,
    ModuleNode,
    FunctionNode,
    ClassNode,
    CapabilityNode,
    ConceptNode,
    AlgorithmNode,
    ManimMappingNode,
    AnimationPatternNode,
    PrecisionRuleNode,
    CodeExampleNode,
)
from aos_lkg.schema.edges import Edge, EdgeType


NODE_CLASS_MAP = {
    NodeType.LIBRARY: LibraryNode,
    NodeType.PACKAGE: LibraryNode,
    NodeType.MODULE: ModuleNode,
    NodeType.FUNCTION: FunctionNode,
    NodeType.CLASS: ClassNode,
    NodeType.CAPABILITY: CapabilityNode,
    NodeType.CONCEPT: ConceptNode,
    NodeType.ALGORITHM: AlgorithmNode,
    NodeType.MANIM_MAPPING: ManimMappingNode,
    NodeType.ANIMATION_PATTERN: AnimationPatternNode,
    NodeType.PRECISION_RULE: PrecisionRuleNode,
    NodeType.CODE_EXAMPLE: CodeExampleNode,
}


def parse_node_dict(data: dict) -> BaseNode:
    """Instantiate a typed Node model from raw dictionary data."""
    node_type_str = data.get("type", "function")
    try:
        node_type = NodeType(node_type_str)
        cls = NODE_CLASS_MAP.get(node_type, BaseNode)
        return cls(**data)
    except Exception:
        return BaseNode(**data)


class KnowledgeGraph(BaseModel):
    """Container for in-memory graph representation."""
    nodes: Dict[str, BaseNode] = Field(default_factory=dict)
    edges: List[Edge] = Field(default_factory=list)

    def add_node(self, node: BaseNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[BaseNode]:
        return self.nodes.get(node_id)

    def get_outgoing_edges(self, source_id: str, edge_type: Optional[EdgeType] = None) -> List[Edge]:
        return [
            e for e in self.edges
            if e.source == source_id and (edge_type is None or e.type == edge_type)
        ]

    def get_incoming_edges(self, target_id: str, edge_type: Optional[EdgeType] = None) -> List[Edge]:
        return [
            e for e in self.edges
            if e.target == target_id and (edge_type is None or e.type == edge_type)
        ]

    def to_networkx(self) -> nx.MultiDiGraph:
        """Convert container to NetworkX MultiDiGraph for traversal and analysis."""
        G = nx.MultiDiGraph()
        for node_id, node in self.nodes.items():
            G.add_node(node_id, **node.model_dump())

        for edge in self.edges:
            G.add_edge(
                edge.source,
                edge.target,
                key=edge.type.value,
                type=edge.type.value,
                weight=edge.weight,
                **edge.metadata
            )
        return G

    @classmethod
    def from_networkx(cls, G: nx.MultiDiGraph) -> KnowledgeGraph:
        """Construct KnowledgeGraph from a NetworkX MultiDiGraph."""
        kg = cls()
        for node_id, data in G.nodes(data=True):
            node = parse_node_dict(data)
            kg.add_node(node)

        for u, v, key, data in G.edges(keys=True, data=True):
            edge_type_val = data.get("type", key)
            try:
                edge_type = EdgeType(edge_type_val)
            except ValueError:
                edge_type = EdgeType.RELATED_TO

            edge_data = {k: v for k, v in data.items() if k not in ("type", "weight")}
            edge = Edge(
                source=str(u),
                target=str(v),
                type=edge_type,
                weight=float(data.get("weight", 1.0)),
                metadata=edge_data
            )
            kg.add_edge(edge)
        return kg
