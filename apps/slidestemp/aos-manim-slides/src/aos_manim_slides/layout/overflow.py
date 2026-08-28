from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from manim import Mobject

from .box import LayoutContext, LayoutNode, Rect, fit_mobject, place_mobject
from .recipes import COLUMN_LAYOUTS, build_recipe


@dataclass
class OverflowIssue:
    code: str
    message: str


@dataclass
class LayoutReport:
    attempts: int = 0
    tactics: List[str] = field(default_factory=list)
    overflow_cleared: bool = False
    final_aspect: float = 16.0 / 9.0
    issues: List[OverflowIssue] = field(default_factory=list)


def check_overflow(root: LayoutNode, rect: Rect, epsilon: float = 0.1) -> List[OverflowIssue]:
    issues: List[OverflowIssue] = []
    if root.mobject is None:
        return issues
    if not _fits(root.mobject, rect, epsilon):
        issues.append(
            OverflowIssue(
                code="CONTENT_OVERFLOW",
                message="Laid-out content exceeds the slide content rectangle.",
            )
        )
    for child in root.children():
        if child.mobject is None or child.dropped:
            continue
        if not _fits(child.mobject, rect, epsilon + 0.05):
            issues.append(
                OverflowIssue(
                    code="CHILD_OVERFLOW",
                    message=f"Child role={child.role} exceeds content rectangle.",
                )
            )
    return issues


def _fits(mob: Mobject, rect: Rect, epsilon: float) -> bool:
    w = float(getattr(mob, "width", 0.0) or 0.0)
    h = float(getattr(mob, "height", 0.0) or 0.0)
    if w <= 1e-6 and h <= 1e-6:
        return True
    return (
        mob.get_left()[0] >= rect.left - epsilon
        and mob.get_right()[0] <= rect.right + epsilon
        and mob.get_bottom()[1] >= rect.bottom - epsilon
        and mob.get_top()[1] <= rect.top + epsilon
    )


TACTIC_ORDER = (
    "drop_decoration",
    "reduce_body_font",
    "collapse_columns",
    "scale_diagram",
    "reduce_equation",
    "reduce_title",
)


def apply_tactic(ctx: LayoutContext, name: str) -> bool:
    """Mutate context for the named tactic. Returns True if a change was made."""
    if name == "drop_decoration" and not ctx.drop_decorations:
        ctx.drop_decorations = True
        return True
    if name == "reduce_body_font" and ctx.body_font_size > 16:
        ctx.body_font_size = max(16, ctx.body_font_size - 4)
        return True
    if name == "collapse_columns" and not ctx.collapse_columns:
        ctx.collapse_columns = True
        return True
    if name == "scale_diagram" and ctx.diagram_scale > 0.45:
        ctx.diagram_scale = max(0.45, ctx.diagram_scale * 0.82)
        return True
    if name == "reduce_equation" and ctx.equation_font_size > 22:
        ctx.equation_font_size = max(22, ctx.equation_font_size - 6)
        return True
    if name == "reduce_title" and ctx.title_font_size > 22:
        ctx.title_font_size = max(22, ctx.title_font_size - 4)
        ctx.heading_font_size = max(18, ctx.heading_font_size - 3)
        return True
    return False


class OverflowSolver:
    """Priority-aware heuristic fitter. Does not uniformly shrink everything."""

    def __init__(self, max_attempts: int = 8) -> None:
        self.max_attempts = max_attempts

    def fit(
        self,
        spec,
        ctx: LayoutContext,
        content_rect: Rect,
    ) -> Tuple[LayoutNode, LayoutReport]:
        report = LayoutReport(final_aspect=ctx.aspect_ratio)
        tactic_idx = 0
        root: Optional[LayoutNode] = None
        for attempt in range(1, self.max_attempts + 1):
            report.attempts = attempt
            root = build_recipe(spec, ctx)
            root.layout(ctx, content_rect)
            issues = check_overflow(root, content_rect)
            report.issues = issues
            if not issues:
                report.overflow_cleared = True
                return root, report
            changed = False
            while tactic_idx < len(TACTIC_ORDER) and not changed:
                name = TACTIC_ORDER[tactic_idx]
                tactic_idx += 1
                if name == "collapse_columns" and spec.layout not in COLUMN_LAYOUTS and not spec.left:
                    continue
                changed = apply_tactic(ctx, name)
                if changed:
                    report.tactics.append(name)
            if not changed:
                break
        if report.issues and root is not None and root.mobject is not None:
            fit_mobject(root.mobject, content_rect.width, content_rect.height)
            place_mobject(root.mobject, content_rect, "center")
            report.tactics.append("scale_root")
            report.issues = check_overflow(root, content_rect)
            report.overflow_cleared = not report.issues
        report.overflow_cleared = not report.issues
        assert root is not None
        return root, report
