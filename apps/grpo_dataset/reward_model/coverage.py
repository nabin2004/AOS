from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CoverageResult:
    score: float
    per_dimension: dict[str, float]


def coverage_score(code: str, coverage_spec: dict[str, Any]) -> CoverageResult:
    reqs = coverage_spec.get("requirements", {})
    total = 0.0
    denom = 0.0
    per_dimension: dict[str, float] = {}

    for dim, spec in reqs.items():
        expected = spec.get("expected", [])
        weight = float(spec.get("weight", 0.0))

        if not expected:
            dim_score = 0.0
        else:
            hits = sum(1 for token in expected if token in code)
            dim_score = hits / len(expected)

        per_dimension[dim] = dim_score
        total += weight * dim_score
        denom += weight

    return CoverageResult(score=(total / denom if denom else 0.0), per_dimension=per_dimension)
