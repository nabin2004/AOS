from __future__ import annotations

from typing import Any
from aos_manim_core import BaseValidator, ValidationResult, ValidationSeverity
from ..layouts.base_slide import Slide


class SlideOverflowValidator(BaseValidator):
    """Verifies that all child elements in a slide remain within its background boundary."""

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(target, Slide):
            result.add_issue(
                code="INVALID_TARGET",
                message=f"Target must be a Slide instance, got {type(target).__name__}",
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
                    code="SLIDE_CONTENT_OVERFLOW",
                    message=f"Slide content item {i} overflows slide bounding canvas.",
                    severity=ValidationSeverity.WARNING,
                    target=str(child),
                    details={
                        "child_bounds": [c_left, c_right, c_bottom, c_top],
                        "slide_bounds": [bg_left, bg_right, bg_bottom, bg_top],
                    },
                )

        return result
