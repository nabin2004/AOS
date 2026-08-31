"""Unit tests for GraphStore, APIIndex, and SemanticIndex."""

import tempfile
from pathlib import Path
import pytest

from aos_lkg.schema.nodes import FunctionNode, CapabilityNode, ManimMappingNode
from aos_lkg.schema.edges import Edge, EdgeType
from aos_lkg.schema.graph import KnowledgeGraph
from aos_lkg.storage.graph_store import GraphStore
from aos_lkg.storage.api_index import ApiIndex
from aos_lkg.storage.semantic_index import SemanticIndex


@pytest.fixture
def sample_kg():
    kg = KnowledgeGraph()

    fn = FunctionNode(
        id="fn:scipy.optimize.brentq",
        name="brentq",
        library="scipy",
        module="scipy.optimize",
        qualified_name="scipy.optimize.brentq",
        signature_str="(f, a, b)",
        capabilities=["cap:root_finding_bracketed"],
        docstring="Find root of f in [a, b] using Brent's method.",
    )
    cap = CapabilityNode(
        id="cap:root_finding_bracketed",
        name="Bracketed Root Finding",
        domain="root_finding",
        description="Finds scalar zeros of continuous 1D functions",
        canonical_apis=["scipy.optimize.brentq"],
        tags=["root_finding", "zero_crossing"],
    )
    manim_node = ManimMappingNode(
        id="manim:Axes",
        name="Axes",
        mobject_classes=["Axes"],
        coordinate_adapter="axes.c2p(x, y)",
    )

    kg.add_node(fn)
    kg.add_node(cap)
    kg.add_node(manim_node)

    kg.add_edge(Edge(source=fn.id, target=cap.id, type=EdgeType.PROVIDES))
    kg.add_edge(Edge(source=cap.id, target=manim_node.id, type=EdgeType.VISUALIZES_WITH))

    return kg


def test_graph_store_jsonl_roundtrip(sample_kg):
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = Path(tmpdir) / "test_graph.jsonl"
        store = GraphStore(sample_kg)
        store.save_jsonl(jsonl_path)

        loaded_store = GraphStore.load_jsonl(jsonl_path)
        assert len(loaded_store.graph.nodes) == 3
        assert len(loaded_store.graph.edges) == 2

        apis = loaded_store.get_apis_for_capability("cap:root_finding_bracketed")
        assert len(apis) == 1
        assert apis[0].name == "brentq"


def test_api_index(sample_kg):
    index = ApiIndex.from_knowledge_graph(sample_kg)
    entry = index.get_by_qualname("scipy.optimize.brentq")
    assert entry is not None
    assert entry.name == "brentq"
    assert entry.module == "scipy.optimize"

    by_name = index.search_by_name("brentq")
    assert len(by_name) == 1


def test_semantic_index(sample_kg):
    sem_idx = SemanticIndex.from_knowledge_graph(sample_kg)
    results = sem_idx.search("Find root zero crossing using brent")
    assert len(results) > 0
    top_id = results[0].node_id
    assert top_id in ("cap:root_finding_bracketed", "fn:scipy.optimize.brentq")
