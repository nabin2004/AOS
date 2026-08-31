"""BenchmarkEvaluator: Rigorous quantitative accuracy scoring across canonical animation tasks."""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from aos_lkg.benchmark.dataset import BenchmarkTestCase, BENCHMARK_SUITE
from aos_lkg.retriever.task_retriever import TaskRetriever, RetrievedSlice
from aos_lkg.storage.graph_store import GraphStore
from aos_lkg.storage.api_index import ApiIndex
from aos_lkg.storage.semantic_index import SemanticIndex


class TestCaseEvaluation(BaseModel):
    test_id: str
    query: str
    category: str
    capability_passed: bool
    api_passed: bool
    dimension_passed: bool
    manim_passed: bool
    retrieved_capability: Optional[str] = None
    retrieved_api: Optional[str] = None
    retrieved_dimension: str = "2D"
    retrieved_mobjects: List[str] = Field(default_factory=list)
    failure_notes: Optional[str] = None


class BenchmarkSummary(BaseModel):
    total_tests: int
    capability_accuracy: float
    api_accuracy: float
    dimension_accuracy: float
    manim_accuracy: float
    overall_benchmark_score: float
    test_evaluations: List[TestCaseEvaluation]


class BenchmarkEvaluator:
    """Runs automated benchmark evaluation on the LKG retrieval engine."""

    def __init__(self, task_retriever: TaskRetriever):
        self.retriever = task_retriever

    def evaluate_all(self, suite: Optional[List[BenchmarkTestCase]] = None) -> BenchmarkSummary:
        cases = suite or BENCHMARK_SUITE
        evaluations: List[TestCaseEvaluation] = []

        for case in cases:
            slice_res: RetrievedSlice = self.retriever.retrieve(case.query)

            # Check Capability
            cap_id = slice_res.primary_capability.id if slice_res.primary_capability else ""
            cap_domain = slice_res.primary_capability.domain if slice_res.primary_capability else ""
            cap_passed = (cap_id == case.expected_capability_id) or (cap_domain == case.expected_domain)

            # Check API
            api_qual = slice_res.primary_api.qualified_name if slice_res.primary_api else ""
            api_name = slice_res.primary_api.name if slice_res.primary_api else ""
            api_passed = any(
                exp.lower() in api_qual.lower() or exp.lower() in api_name.lower()
                for exp in case.expected_api_substrings
            )

            # Check Dimension
            dim_passed = (slice_res.parsed_intent.dimension == case.expected_dimension)

            # Check Manim Mobjects
            mobs_retrieved = []
            for mm in slice_res.manim_mappings:
                mobs_retrieved.extend(mm.mobject_classes)
            manim_passed = True
            if case.expected_mobjects:
                manim_passed = any(exp_mob in mobs_retrieved for exp_mob in case.expected_mobjects)

            failures = []
            if not cap_passed:
                failures.append(f"Cap mismatch: got '{cap_id}', expected '{case.expected_capability_id}'")
            if not api_passed:
                failures.append(f"API mismatch: got '{api_qual}', expected one of {case.expected_api_substrings}")
            if not dim_passed:
                failures.append(f"Dim mismatch: got '{slice_res.parsed_intent.dimension}', expected '{case.expected_dimension}'")

            evaluations.append(
                TestCaseEvaluation(
                    test_id=case.id,
                    query=case.query,
                    category=case.category,
                    capability_passed=cap_passed,
                    api_passed=api_passed,
                    dimension_passed=dim_passed,
                    manim_passed=manim_passed,
                    retrieved_capability=cap_id,
                    retrieved_api=api_qual,
                    retrieved_dimension=slice_res.parsed_intent.dimension,
                    retrieved_mobjects=mobs_retrieved[:3],
                    failure_notes="; ".join(failures) if failures else None,
                )
            )

        total = len(evaluations)
        cap_acc = (sum(1 for e in evaluations if e.capability_passed) / total) * 100.0 if total else 0.0
        api_acc = (sum(1 for e in evaluations if e.api_passed) / total) * 100.0 if total else 0.0
        dim_acc = (sum(1 for e in evaluations if e.dimension_passed) / total) * 100.0 if total else 0.0
        manim_acc = (sum(1 for e in evaluations if e.manim_passed) / total) * 100.0 if total else 0.0

        overall = (cap_acc * 0.35) + (api_acc * 0.35) + (dim_acc * 0.15) + (manim_acc * 0.15)

        return BenchmarkSummary(
            total_tests=total,
            capability_accuracy=round(cap_acc, 1),
            api_accuracy=round(api_acc, 1),
            dimension_accuracy=round(dim_acc, 1),
            manim_accuracy=round(manim_acc, 1),
            overall_benchmark_score=round(overall, 1),
            test_evaluations=evaluations,
        )
