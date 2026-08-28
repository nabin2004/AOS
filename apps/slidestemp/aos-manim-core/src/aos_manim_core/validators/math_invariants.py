from __future__ import annotations

import math
from typing import Any, Union
import sympy as sp
from .base import BaseValidator, ValidationResult, ValidationSeverity


class NumericalToleranceValidator(BaseValidator):
    """Verifies that numerical computations are within specified tolerances."""

    def __init__(self, atol: float = 1e-4, rtol: float = 1e-4) -> None:
        self.atol = atol
        self.rtol = rtol

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        expected = kwargs.get("expected")

        if expected is None:
            result.add_issue(
                code="MISSING_EXPECTED_VALUE",
                message="NumericalToleranceValidator requires 'expected' argument in kwargs.",
                severity=ValidationSeverity.ERROR,
            )
            return result

        try:
            val_actual = float(target)
            val_expected = float(expected)
        except (ValueError, TypeError) as e:
            result.add_issue(
                code="NON_NUMERICAL_INPUT",
                message=f"Inputs cannot be converted to floats: {e}",
                severity=ValidationSeverity.ERROR,
            )
            return result

        diff = abs(val_actual - val_expected)
        tolerance = self.atol + self.rtol * abs(val_expected)

        if diff > tolerance:
            result.add_issue(
                code="NUMERICAL_TOLERANCE_EXCEEDED",
                message=f"Value {val_actual} deviates from expected {val_expected} by {diff:.6e} > tolerance {tolerance:.6e}",
                severity=ValidationSeverity.ERROR,
                details={"actual": val_actual, "expected": val_expected, "diff": diff, "tolerance": tolerance},
            )
        else:
            result.metadata["diff"] = diff

        return result


class SymbolicEquivalenceValidator(BaseValidator):
    """Verifies that two symbolic expressions are mathematically equivalent."""

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        expected = kwargs.get("expected")

        if expected is None:
            result.add_issue(
                code="MISSING_EXPECTED_EXPRESSION",
                message="SymbolicEquivalenceValidator requires 'expected' expression in kwargs.",
                severity=ValidationSeverity.ERROR,
            )
            return result

        try:
            expr_actual = sp.sympify(target)
            expr_expected = sp.sympify(expected)
        except Exception as e:
            result.add_issue(
                code="SYMPY_PARSE_ERROR",
                message=f"Failed to parse symbolic expression: {e}",
                severity=ValidationSeverity.ERROR,
            )
            return result

        diff = sp.simplify(expr_actual - expr_expected)
        if diff != 0:
            result.add_issue(
                code="SYMBOLIC_NON_EQUIVALENCE",
                message=f"Expression '{expr_actual}' is not symbolically equivalent to '{expr_expected}'. Diff: '{diff}'",
                severity=ValidationSeverity.ERROR,
                details={"actual": str(expr_actual), "expected": str(expr_expected), "diff": str(diff)},
            )

        return result
