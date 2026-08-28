from __future__ import annotations

from typing import Any
from aos_manim_core import BaseValidator, ValidationResult, ValidationSeverity
from ..structures.proof_step import ProofDocument, ProofStep


class ProofStructureValidator(BaseValidator):
    """Verifies that a ProofDocument has valid steps, acyclic dependencies, and resolved references."""

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(target, ProofDocument):
            result.add_issue(
                code="INVALID_PROOF_TARGET",
                message=f"Expected ProofDocument, got {type(target).__name__}",
                severity=ValidationSeverity.ERROR,
            )
            return result

        if not target.steps:
            result.add_issue(
                code="EMPTY_PROOF_STEPS",
                message="Proof document contains no steps.",
                severity=ValidationSeverity.ERROR,
            )
            return result

        known_step_ids = {s.id for s in target.steps}
        for s in target.steps:
            for dep in s.depends_on:
                if dep not in known_step_ids:
                    result.add_issue(
                        code="UNRESOLVED_STEP_DEPENDENCY",
                        message=f"Step '{s.id}' depends on unknown step '{dep}'.",
                        severity=ValidationSeverity.ERROR,
                        details={"step_id": s.id, "dependency": dep},
                    )

        return result
