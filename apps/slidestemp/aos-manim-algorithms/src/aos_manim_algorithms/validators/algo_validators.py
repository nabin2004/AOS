from __future__ import annotations

from typing import Any, List
import networkx as nx
from aos_manim_core import BaseValidator, ValidationResult, ValidationSeverity


class SortedInvariantValidator(BaseValidator):
    """Verifies that an array is strictly or monotonically sorted."""

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(target, (list, tuple)):
            result.add_issue(
                code="INVALID_TARGET_TYPE",
                message=f"Target must be a list or tuple, got {type(target).__name__}",
                severity=ValidationSeverity.ERROR,
            )
            return result

        for i in range(len(target) - 1):
            if target[i] > target[i + 1]:
                result.add_issue(
                    code="SORT_INVARIANT_VIOLATED",
                    message=f"Element at index {i} ({target[i]}) > element at {i+1} ({target[i+1]})",
                    severity=ValidationSeverity.ERROR,
                    details={"index": i, "val_a": target[i], "val_b": target[i + 1]},
                )
                break

        return result


class GraphPathValidator(BaseValidator):
    """Verifies that a discovered path exists and forms a continuous chain of edges in the graph."""

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        graph: Optional[nx.Graph] = kwargs.get("graph")
        path: List[Any] = target

        if graph is None:
            result.add_issue(
                code="MISSING_GRAPH",
                message="GraphPathValidator requires 'graph' kwarg.",
                severity=ValidationSeverity.ERROR,
            )
            return result

        if not path:
            result.add_issue(
                code="EMPTY_PATH",
                message="Path is empty.",
                severity=ValidationSeverity.WARNING,
            )
            return result

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if not graph.has_edge(u, v):
                result.add_issue(
                    code="INVALID_EDGE_IN_PATH",
                    message=f"Edge ({u}, {v}) does not exist in the graph.",
                    severity=ValidationSeverity.ERROR,
                    details={"u": u, "v": v},
                )

        return result
