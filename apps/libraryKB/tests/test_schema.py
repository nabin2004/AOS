"""Unit tests for AOS LKG schema models and graph conversions."""

import pytest
import networkx as nx

from aos_lkg.schema.nodes import (
    NodeType,
    FunctionNode,
    CapabilityNode,
    ParameterInfo,
    ReturnInfo,
    ManimMappingNode,
    PrecisionRuleNode,
)
from aos_lkg.schema.edges import Edge, EdgeType
from aos_lkg.schema.graph import KnowledgeGraph, parse_node_dict


def test_function_node_creation():
    fn = FunctionNode(
        id="fn:scipy.optimize.brentq",
        name="brentq",
        library="scipy",
        module="scipy.optimize",
        qualified_name="scipy.optimize.brentq",
        signature_str="(f, a, b, xtol=2e-12)",
        parameters=[
            ParameterInfo(name="f", type_str="Callable", is_required=True),
            ParameterInfo(name="a", type_str="float", is_required=True),
            ParameterInfo(name="b", type_str="float", is_required=True),
            ParameterInfo(name="xtol", type_str="float", default_str="2e-12", is_required=False),
        ],
        returns_info=ReturnInfo(type_str="float", description="Root of f between a and b"),
        capabilities=["cap:root_finding_bracketed"],
    )

    assert fn.id == "fn:scipy.optimize.brentq"
    assert fn.name == "brentq"
    assert len(fn.parameters) == 4
    assert fn.parameters[0].is_required is True
    assert fn.parameters[3].is_required is False
    assert fn.returns_info.type_str == "float"


def test_knowledge_graph_networkx_roundtrip():
    kg = KnowledgeGraph()

    fn = FunctionNode(
        id="fn:scipy.optimize.newton",
        name="newton",
        library="scipy",
        module="scipy.optimize",
        qualified_name="scipy.optimize.newton",
        signature_str="(func, x0, fprime=None)",
    )
    cap = CapabilityNode(
        id="cap:root_finding_newton",
        name="Newton Root Finding",
        domain="root_finding",
        description="Iterative tangent root finding",
    )

    kg.add_node(fn)
    kg.add_node(cap)

    edge = Edge(
        source=fn.id,
        target=cap.id,
        type=EdgeType.PROVIDES,
    )
    kg.add_edge(edge)

    # Convert to NetworkX
    nx_g = kg.to_networkx()
    assert isinstance(nx_g, nx.MultiDiGraph)
    assert fn.id in nx_g
    assert cap.id in nx_g
    assert nx_g.has_edge(fn.id, cap.id)

    # Convert back from NetworkX
    restored_kg = KnowledgeGraph.from_networkx(nx_g)
    assert len(restored_kg.nodes) == 2
    assert restored_kg.get_node(fn.id).name == "newton"
    assert len(restored_kg.edges) == 1
    assert restored_kg.edges[0].type == EdgeType.PROVIDES


def test_parse_node_dict():
    data = {
        "id": "rule:test_rule",
        "name": "Test Precision Rule",
        "type": "precision_rule",
        "rule_id": "PR-999",
        "title": "Do not hardcode",
        "anti_pattern": "Dot([1,0,0])",
        "correct_pattern": "axes.c2p(1,0)",
        "rationale": "Exact scaling",
        "enforcement_level": "STRICT",
    }
    node = parse_node_dict(data)
    assert isinstance(node, PrecisionRuleNode)
    assert node.rule_id == "PR-999"
    assert node.enforcement_level == "STRICT"
