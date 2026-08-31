"""End-to-end integration tests for multi-library knowledge graph and retrieval across domains."""

import pytest

from aos_lkg.schema.graph import KnowledgeGraph
from aos_lkg.extractor.crawler import PackageCrawler
from aos_lkg.ontology.enrichment import enrich_knowledge_graph
from aos_lkg.storage.graph_store import GraphStore
from aos_lkg.storage.api_index import ApiIndex
from aos_lkg.storage.semantic_index import SemanticIndex
from aos_lkg.retriever.task_retriever import TaskRetriever
from aos_lkg.retriever.prompt_formatter import PromptFormatter


@pytest.fixture(scope="module")
def full_pipeline():
    crawler = PackageCrawler(max_depth=1, include_submodules=False)
    combined = KnowledgeGraph()

    for pkg_name in ["scipy", "networkx", "shapely", "sympy"]:
        try:
            pkg_kg = crawler.crawl_package(pkg_name)
            for node in pkg_kg.nodes.values():
                combined.add_node(node)
            for edge in pkg_kg.edges:
                combined.add_edge(edge)
        except Exception:
            pass

    enriched = enrich_knowledge_graph(combined)
    store = GraphStore(enriched)
    api_idx = ApiIndex.from_knowledge_graph(enriched)
    sem_idx = SemanticIndex.from_knowledge_graph(enriched)

    return store, api_idx, sem_idx


def test_e2e_newton_root_finding(full_pipeline):
    store, api_idx, sem_idx = full_pipeline
    retriever = TaskRetriever(store, api_idx, sem_idx)

    slice_res = retriever.retrieve("Animate Newton's method for root finding of x^2 - 2")
    assert slice_res.primary_capability is not None
    assert "root_finding" in slice_res.primary_capability.domain

    prompt = PromptFormatter.format_llm_context(slice_res)
    assert "newton" in prompt.lower() or "brentq" in prompt.lower()
    assert "axes.c2p" in prompt


def test_e2e_dijkstra_graph_path(full_pipeline):
    store, api_idx, sem_idx = full_pipeline
    retriever = TaskRetriever(store, api_idx, sem_idx)

    slice_res = retriever.retrieve("Visualize Dijkstra shortest path algorithm on a weighted graph")
    assert slice_res.primary_capability is not None
    assert "graph" in slice_res.primary_capability.domain or "shortest_path" in slice_res.primary_capability.id

    prompt = PromptFormatter.format_llm_context(slice_res)
    assert "dijkstra" in prompt.lower() or "shortest_path" in prompt.lower()
    assert "Graph" in prompt


def test_e2e_curve_intersection(full_pipeline):
    store, api_idx, sem_idx = full_pipeline
    retriever = TaskRetriever(store, api_idx, sem_idx)

    slice_res = retriever.retrieve("Find intersection of two geometric circles and fill overlapping polygon area")
    prompt = PromptFormatter.format_llm_context(slice_res)
    assert "intersection" in prompt.lower()
    assert "Polygon" in prompt or "Dot" in prompt


def test_e2e_ode_trajectory(full_pipeline):
    store, api_idx, sem_idx = full_pipeline
    retriever = TaskRetriever(store, api_idx, sem_idx)

    slice_res = retriever.retrieve("Simulate and plot Lorenz attractor phase space trajectory using ODE integration")
    prompt = PromptFormatter.format_llm_context(slice_res)
    assert "ode" in prompt.lower() or "solve_ivp" in prompt.lower()
