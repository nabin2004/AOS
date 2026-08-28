from __future__ import annotations

from typing import Any
import sympy as sp
from aos_manim_core import BaseValidator, ValidationResult, ValidationSeverity


class RootPrecisionValidator(BaseValidator):
    """Verifies that a discovered root evaluates to zero within tolerance."""

    def __init__(self, tol: float = 1e-4) -> None:
        self.tol = tol

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        expression_str = kwargs.get("expression")
        if not expression_str:
            result.add_issue(
                code="MISSING_EXPRESSION",
                message="RootPrecisionValidator requires 'expression' kwarg.",
                severity=ValidationSeverity.ERROR,
            )
            return result

        try:
            x = sp.Symbol('x')
            expr = sp.sympify(expression_str)
            val = float(expr.subs(x, float(target)))
        except Exception as e:
            result.add_issue(
                code="EVALUATION_ERROR",
                message=f"Could not evaluate expression at root: {e}",
                severity=ValidationSeverity.ERROR,
            )
            return result

        if abs(val) > self.tol:
            result.add_issue(
                code="ROOT_PRECISION_ERROR",
                message=f"Root candidate {target} yields f({target}) = {val:.6e} > tolerance {self.tol:.6e}",
                severity=ValidationSeverity.ERROR,
                details={"root": float(target), "f_val": val, "tolerance": self.tol},
            )
        else:
            result.metadata["f_val"] = val

        return result


class IntegralConvergenceValidator(BaseValidator):
    """Verifies that numerical quadrature matches symbolic integration."""

    def __init__(self, tol: float = 1e-3) -> None:
        self.tol = tol

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        num_res = target
        sym_res = kwargs.get("symbolic_result")

        if sym_res is None:
            result.add_issue(
                code="MISSING_SYMBOLIC_RESULT",
                message="IntegralConvergenceValidator requires 'symbolic_result' kwarg.",
                severity=ValidationSeverity.ERROR,
            )
            return result

        diff = abs(float(num_res) - float(sym_res))
        if diff > self.tol:
            result.add_issue(
                code="INTEGRAL_CONVERGENCE_MISMATCH",
                message=f"Numerical integral {num_res} deviates from symbolic {sym_res} by {diff:.6e} > tol {self.tol:.6e}",
                severity=ValidationSeverity.ERROR,
                details={"numerical": float(num_res), "symbolic": float(sym_res), "diff": diff},
            )

        return result
