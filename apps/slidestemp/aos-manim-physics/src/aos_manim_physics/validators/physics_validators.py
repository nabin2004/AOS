from __future__ import annotations

from typing import Any
import numpy as np
from aos_manim_core import BaseValidator, ValidationResult, ValidationSeverity


class EnergyConservationValidator(BaseValidator):
    """Verifies that energy is conserved in closed conservative physical simulations."""

    def __init__(self, rel_tol: float = 1e-3) -> None:
        self.rel_tol = rel_tol

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        try:
            energies = np.array(target, dtype=float)
        except Exception as e:
            result.add_issue(
                code="INVALID_ENERGY_ARRAY",
                message=f"Could not convert energy sequence to numpy array: {e}",
                severity=ValidationSeverity.ERROR,
            )
            return result

        if len(energies) < 2:
            return result

        e0 = energies[0]
        max_deviation = np.max(np.abs(energies - e0)) / (abs(e0) + 1e-12)

        if max_deviation > self.rel_tol:
            result.add_issue(
                code="ENERGY_CONSERVATION_VIOLATED",
                message=f"Energy deviation {max_deviation:.6e} > tolerance {self.rel_tol:.6e}",
                severity=ValidationSeverity.ERROR,
                details={"max_rel_deviation": float(max_deviation), "tolerance": self.rel_tol},
            )
        else:
            result.metadata["max_rel_deviation"] = float(max_deviation)

        return result
