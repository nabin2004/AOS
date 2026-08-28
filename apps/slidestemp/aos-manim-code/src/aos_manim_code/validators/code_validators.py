from __future__ import annotations

import ast
from typing import Any
from aos_manim_core import BaseValidator, ValidationResult, ValidationSeverity


class AstSyntaxValidator(BaseValidator):
    """Verifies that code strings are syntactically valid Python."""

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        code_str = str(target)
        try:
            tree = ast.parse(code_str)
            result.metadata["node_count"] = len(list(ast.walk(tree)))
        except SyntaxError as e:
            result.add_issue(
                code="PYTHON_SYNTAX_ERROR",
                message=f"SyntaxError in code: {e.msg} at line {e.lineno}",
                severity=ValidationSeverity.ERROR,
                details={"line": e.lineno, "offset": e.offset},
            )

        return result


class StackDepthValidator(BaseValidator):
    """Verifies that call stack depth does not exceed safety limits."""

    def __init__(self, max_depth: int = 50) -> None:
        self.max_depth = max_depth

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        depth = int(target)
        if depth > self.max_depth:
            result.add_issue(
                code="STACK_OVERFLOW_RISK",
                message=f"Stack depth {depth} exceeds max allowed depth {self.max_depth}",
                severity=ValidationSeverity.ERROR,
                details={"depth": depth, "max_depth": self.max_depth},
            )
        return result
