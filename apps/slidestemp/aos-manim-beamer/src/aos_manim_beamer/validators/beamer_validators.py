from __future__ import annotations

from typing import Any
from aos_manim_core import BaseValidator, ValidationResult, ValidationSeverity
from ..components.frame import BeamerFrame


class BeamerFrameOverflowValidator(BaseValidator):
    """Verifies that all child blocks in a BeamerFrame remain within frame boundaries."""

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(target, BeamerFrame):
            result.add_issue(
                code="INVALID_BEAMER_TARGET",
                message=f"Expected BeamerFrame, got {type(target).__name__}",
                severity=ValidationSeverity.ERROR,
            )
            return result

        bg_left = target.bg_frame.get_left()[0]
        bg_right = target.bg_frame.get_right()[0]
        bg_top = target.bg_frame.get_top()[1]
        bg_bottom = target.bg_frame.get_bottom()[1]

        for i, child in enumerate(target.content_group):
            c_left = child.get_left()[0]
            c_right = child.get_right()[0]
            c_top = child.get_top()[1]
            c_bottom = child.get_bottom()[1]

            if c_left < bg_left or c_right > bg_right or c_top > bg_top or c_bottom < bg_bottom:
                result.add_issue(
                    code="FRAME_CONTENT_OVERFLOW",
                    message=f"Beamer frame item {i} overflows frame bounding box.",
                    severity=ValidationSeverity.WARNING,
                    target=str(child),
                )

        return result
