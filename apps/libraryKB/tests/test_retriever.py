"""Unit tests for query parsing, task retrieval, and prompt formatting."""

import pytest

from aos_lkg.schema.graph import KnowledgeGraph
from aos_lkg.ontology.enrichment import enrich_knowledge_graph
from aos_lkg.extractor.crawler import PackageCrawler
from aos_lkg.storage.graph_store import GraphStore
from aos_lkg.storage.api_index import ApiIndex
from aos_lkg.storage.semantic_index import SemanticIndex
from aos_lkg.retriever.query_parser import QueryParser
from aos_lkg.retriever.task_retriever import TaskRetriever
from aos_lkg.retriever.prompt_formatter import PromptFormatter


@pytest.fixture(scope="module")
def enriched_pipeline():
    crawler = PackageCrawler(max_depth=1, include_submodules=False)
    kg = crawler.crawl_package("scipy", target_submodules=["optimize", "integrate"])
    enriched_kg = enrich_knowledge_graph(kg)

    store = GraphStore(enriched_kg)
    api_idx = ApiIndex.from_knowledge_graph(enriched_kg)
    sem_idx = SemanticIndex.from_knowledge_graph(enriched_kg)

    return store, api_idx, sem_idx


def test_query_parser():
    parsed = QueryParser.parse("Animate Newton's method finding root of x^2 - 2 on Axes with ValueTracker")
    assert "root_finding" in parsed.detected_domains
    assert "Axes" in parsed.target_mobjects
    assert "ValueTracker" in parsed.target_mobjects


def test_task_retriever_root_finding(enriched_pipeline):
    store, api_idx, sem_idx = enriched_pipeline
    retriever = TaskRetriever(store, api_idx, sem_idx)

    slice_data = retriever.retrieve("Animate Newton's method for finding sqrt(2)")
    assert slice_data.primary_capability is not None
    assert slice_data.primary_capability.domain == "root_finding"
    assert len(slice_data.precision_rules) > 0


def test_prompt_formatter(enriched_pipeline):
    store, api_idx, sem_idx = enriched_pipeline
    retriever = TaskRetriever(store, api_idx, sem_idx)

    slice_data = retriever.retrieve("Animate Newton's method for x^2 - 2")
    formatted = PromptFormatter.format_llm_context(slice_data)

    assert "[TASK]" in formatted
    assert "[MATH CAPABILITY]" in formatted
    assert "[PRECISION & ANTI-HALLUCINATION RULES]" in formatted
    assert "axes.c2p" in formatted

    # Ensure token size is within target density budget (approx 500-1500 tokens / 3000-8000 chars)
    assert len(formatted) > 200
    assert len(formatted) < 10000
