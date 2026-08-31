"""HealthReport: Diagnostic summaries and consistency reporting for the AOS LKG."""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from aos_lkg.schema.nodes import NodeType
from aos_lkg.schema.graph import KnowledgeGraph
from aos_lkg.validator.runtime_checker import (
    RuntimeChecker,
    LibraryValidationResult,
    ApiValidationResult,
)
from aos_lkg.validator.code_sandbox import CodeSandbox, ExampleExecutionResult


class GraphHealthReport(BaseModel):
    total_nodes: int
    total_edges: int
    node_counts_by_type: Dict[str, int]
    library_verifications: List[LibraryValidationResult]
    api_verification_summary: Dict[str, int]
    example_executions: List[ExampleExecutionResult]
    overall_health_score: float

    def to_markdown(self) -> str:
        lines = []
        lines.append("# AOS Knowledge Graph Health Report\n")
        lines.append(f"**Overall Health Score**: `{self.overall_health_score:.1f}%`\n")

        lines.append("## Graph Statistics")
        lines.append(f"- **Total Nodes**: {self.total_nodes}")
        lines.append(f"- **Total Edges**: {self.total_edges}")
        lines.append("### Node Breakdown:")
        for ntype, count in sorted(self.node_counts_by_type.items()):
            lines.append(f"  - `{ntype}`: {count}")
        lines.append("")

        lines.append("## Library Versions")
        for lib in self.library_verifications:
            status = "[OK]" if lib.version_matches else "[DRIFT]"
            lines.append(f"- {status} **{lib.library_name}**: Recorded `{lib.recorded_version}` | Live `{lib.live_version}`")
        lines.append("")

        lines.append("## API Signature Integrity")
        lines.append(f"- Verified APIs Checked: {self.api_verification_summary.get('checked', 0)}")
        lines.append(f"- Fully Matching Signatures: {self.api_verification_summary.get('matched', 0)}")
        lines.append(f"- Missing / Errored: {self.api_verification_summary.get('errored', 0)}")
        lines.append("")

        lines.append("## Executable Recipe Verification")
        passed_ex = sum(1 for e in self.example_executions if e.passed)
        total_ex = len(self.example_executions)
        lines.append(f"- Executable Examples: {passed_ex}/{total_ex} passing")
        for ex in self.example_executions:
            status = "[PASS]" if ex.passed else "[FAIL]"
            lines.append(f"  - {status} `{ex.target_api}` ({ex.example_name}) - {ex.execution_time_ms}ms")
            if not ex.passed:
                lines.append(f"    Error: {ex.error_type} - {ex.error_message}")
        lines.append("")

        return "\n".join(lines)


def generate_health_report(kg: KnowledgeGraph, sample_api_limit: int = 50) -> GraphHealthReport:
    """Generate comprehensive health report for a KnowledgeGraph instance."""
    node_counts: Dict[str, int] = {}
    for node in kg.nodes.values():
        t_name = node.type.value if hasattr(node.type, "value") else str(node.type)
        node_counts[t_name] = node_counts.get(t_name, 0) + 1

    lib_results = RuntimeChecker.validate_library_versions(kg)
    api_results = RuntimeChecker.validate_apis(kg, sample_limit=sample_api_limit)
    ex_results = CodeSandbox.test_all_examples(kg)

    checked_apis = len(api_results)
    matched_apis = sum(1 for r in api_results if r.exists and r.signature_matches)
    errored_apis = sum(1 for r in api_results if not r.exists or r.error_message is not None)

    ex_passed = sum(1 for e in ex_results if e.passed)
    ex_total = len(ex_results) if ex_results else 1

    # Health score weighting: 50% API integrity + 50% Example execution
    api_score = (matched_apis / checked_apis * 100.0) if checked_apis > 0 else 100.0
    ex_score = (ex_passed / ex_total * 100.0)
    overall_score = (api_score * 0.5) + (ex_score * 0.5)

    return GraphHealthReport(
        total_nodes=len(kg.nodes),
        total_edges=len(kg.edges),
        node_counts_by_type=node_counts,
        library_verifications=lib_results,
        api_verification_summary={
            "checked": checked_apis,
            "matched": matched_apis,
            "errored": errored_apis,
        },
        example_executions=ex_results,
        overall_health_score=round(overall_score, 1),
    )
