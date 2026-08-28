from __future__ import annotations

from typing import Any, List, Optional
import numpy as np
from manim import config, Mobject
from .base import BaseValidator, ValidationResult, ValidationSeverity


class CanvasBoundsValidator(BaseValidator):
    """Verifies that Mobjects remain comfortably within the camera frame bounds."""

    def __init__(self, margin: float = 0.4, frame_width: Optional[float] = None, frame_height: Optional[float] = None) -> None:
        self.margin = margin
        self.frame_width = frame_width or config.frame_width
        self.frame_height = frame_height or config.frame_height

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        result = ValidationResult()
        if not isinstance(target, Mobject):
            result.add_issue(
                code="INVALID_TARGET_TYPE",
                message=f"Target must be a Manim Mobject, got {type(target).__name__}",
                severity=ValidationSeverity.ERROR,
            )
            return result

        # Bounding box is [min_x, min_y, min_z] to [max_x, max_y, max_z]
        left = target.get_left()[0]
        right = target.get_right()[0]
        top = target.get_top()[1]
        bottom = target.get_bottom()[1]

        max_x = (self.frame_width / 2.0) - self.margin
        min_x = -max_x
        max_y = (self.frame_height / 2.0) - self.margin
        min_y = -max_y

        if left < min_x:
            result.add_issue(
                code="BOUNDS_LEFT_OVERFLOW",
                message=f"Mobject extends beyond left bound: left={left:.2f} < min_x={min_x:.2f}",
                severity=ValidationSeverity.WARNING,
                target=str(target),
                details={"left": left, "min_x": min_x},
            )
        if right > max_x:
            result.add_issue(
                code="BOUNDS_RIGHT_OVERFLOW",
                message=f"Mobject extends beyond right bound: right={right:.2f} > max_x={max_x:.2f}",
                severity=ValidationSeverity.WARNING,
                target=str(target),
                details={"right": right, "max_x": max_x},
            )
        if top > max_y:
            result.add_issue(
                code="BOUNDS_TOP_OVERFLOW",
                message=f"Mobject extends beyond top bound: top={top:.2f} > max_y={max_y:.2f}",
                severity=ValidationSeverity.WARNING,
                target=str(target),
                details={"top": top, "max_y": max_y},
            )
        if bottom < min_y:
            result.add_issue(
                code="BOUNDS_BOTTOM_OVERFLOW",
                message=f"Mobject extends beyond bottom bound: bottom={bottom:.2f} < min_y={min_y:.2f}",
                severity=ValidationSeverity.WARNING,
                target=str(target),
                details={"bottom": bottom, "min_y": min_y},
            )

        return result


class CollisionValidator(BaseValidator):
    """Verifies that two Mobjects do not produce unintended visual overlap."""

    def __init__(self, tolerance: float = 0.05) -> None:
        self.tolerance = tolerance

    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        """Target can be a list/tuple of two Mobjects or a parent Mobject with children."""
        result = ValidationResult()
        mob_a: Mobject
        mob_b: Mobject

        if isinstance(target, (list, tuple)) and len(target) >= 2:
            mob_a, mob_b = target[0], target[1]
        elif "other" in kwargs and isinstance(target, Mobject):
            mob_a, mob_b = target, kwargs["other"]
        else:
            result.add_issue(
                code="INVALID_COLLISION_INPUT",
                message="CollisionValidator requires two Mobjects to compare.",
                severity=ValidationSeverity.ERROR,
            )
            return result

        a_left, a_right = mob_a.get_left()[0], mob_a.get_right()[0]
        a_bottom, a_top = mob_a.get_bottom()[1], mob_a.get_top()[1]

        b_left, b_right = mob_b.get_left()[0], mob_b.get_right()[0]
        b_bottom, b_top = mob_b.get_bottom()[1], mob_b.get_top()[1]

        # Check for non-overlap
        x_overlap = not (a_right < b_left + self.tolerance or b_right < a_left + self.tolerance)
        y_overlap = not (a_top < b_bottom + self.tolerance or b_top < a_bottom + self.tolerance)

        if x_overlap and y_overlap:
            result.add_issue(
                code="COLLISION_DETECTED",
                message="Unintended spatial overlap detected between Mobjects.",
                severity=ValidationSeverity.WARNING,
                details={
                    "box_a": [a_left, a_right, a_bottom, a_top],
                    "box_b": [b_left, b_right, b_bottom, b_top],
                },
            )

        return result
