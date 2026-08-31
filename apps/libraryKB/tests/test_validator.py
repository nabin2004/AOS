"""Unit tests for runtime self-verification, code sandbox, and health reporting."""

import pytest

from aos_lkg.schema.graph import KnowledgeGraph
from aos_lkg.ontology.enrichment import enrich_knowledge_graph
from aos_lkg.extractor.crawler import PackageCrawler
from aos_lkg.validator.runtime_checker import RuntimeChecker
from aos_lkg.validator.code_sandbox import CodeSandbox
from aos_lkg.validator.health_report import generate_health_report


@pytest.fixture(scope="module")
def sample_validated_kg():
    crawler = PackageCrawler(max_depth=1, include_submodules=False)
    kg = crawler.crawl_package("scipy", target_submodules=["optimize"])
    return enrich_knowledge_graph(kg)


def test_runtime_checker_versions(sample_validated_kg):
    ver_results = RuntimeChecker.validate_library_versions(sample_validated_kg)
    assert len(ver_results) > 0
    scipy_res = next(r for r in ver_results if r.library_name == "scipy")
    assert scipy_res.live_version is not None


def test_code_sandbox_execution(sample_validated_kg):
    ex_results = CodeSandbox.test_all_examples(sample_validated_kg)
    assert len(ex_results) > 0
    for res in ex_results:
        assert res.passed is True, f"Example failed: {res.target_api} - {res.error_message}"


def test_generate_health_report(sample_validated_kg):
    report = generate_health_report(sample_validated_kg, sample_api_limit=10)
    assert report.total_nodes > 0
    assert report.overall_health_score >= 50.0
    md = report.to_markdown()
    assert "# AOS Knowledge Graph Health Report" in md
