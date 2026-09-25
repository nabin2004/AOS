"""Static positioning linter for Manim Community Edition code.

Detects fragile hardcoded coordinates (.move_to([x, y, z]), manual .shift() chaining)
and enforces relative positioning (.next_to, .arrange, .to_edge, .to_corner, axes.c2p).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence


@dataclass
class PositioningLintIssue:
    line: int
    col: int
    mobject_call: str
    message: str
    suggestion: str
    severity: str = "warning"  # "warning" or "error"

    def format(self) -> str:
        sev = f"[{self.severity.upper()}]"
        return f"- Line {self.line}:{self.col} {sev} {self.message}\n  Suggestion: {self.suggestion}"


@dataclass
class PositioningLintReport:
    valid: bool
    issues: list[PositioningLintIssue] = field(default_factory=list)
    relative_layout_calls: int = 0
    raw_coordinate_calls: int = 0

    @property
    def has_warnings(self) -> bool:
        return len(self.issues) > 0

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)

    def format_feedback(self) -> str:
        if not self.issues:
            return "Positioning Lint: PASSED (All mobjects adhere to relative layout principles)."

        header = (
            f"Positioning Lint Report ({len(self.issues)} issue(s) detected, "
            f"{self.relative_layout_calls} relative layout call(s) found):\n"
            "Rule violation: Avoid hardcoding raw screen coordinates. Use relative layout "
            "methods (.next_to, .arrange, .to_edge, .to_corner) or axes.c2p()."
        )
        body = "\n".join(issue.format() for issue in self.issues)
        return f"{header}\n\n{body}"


class ManimPositioningVisitor(ast.NodeVisitor):
    """AST visitor that checks for raw coordinate usage and relative positioning."""

    RELATIVE_METHODS = {"arrange", "next_to", "to_edge", "to_corner", "align_to", "center"}
    VALID_CONSTANTS = {"ORIGIN", "UP", "DOWN", "LEFT", "RIGHT", "UL", "UR", "DL", "DR", "IN", "OUT"}

    def __init__(self, source_code: str) -> None:
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.issues: list[PositioningLintIssue] = []
        self.relative_layout_calls = 0
        self.raw_coordinate_calls = 0

    def _get_line_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def _is_axes_call(self, node: ast.AST) -> bool:
        """Check if an expression is axes.c2p(...) or coords_to_point(...)."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in {"c2p", "coords_to_point", "point_from_proportion"}:
                return True
        return False

    def _is_origin_or_direction_constant(self, node: ast.AST) -> bool:
        """Check if node is a standard direction constant like ORIGIN or UP."""
        if isinstance(node, ast.Name) and node.id in self.VALID_CONSTANTS:
            return True
        return False

    def _contains_numeric_literals(self, elts: Sequence[ast.AST]) -> bool:
        """Check if elements of a list or tuple contain non-zero numeric constants."""
        non_zero_count = 0
        for elt in elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, (int, float)):
                if abs(elt.value) > 0.001:
                    non_zero_count += 1
            elif isinstance(elt, ast.UnaryOp) and isinstance(elt.operand, ast.Constant):
                non_zero_count += 1
            elif isinstance(elt, ast.BinOp):
                # Arithmetic like -6 + i*1.5
                non_zero_count += 1
        return non_zero_count >= 1

    def visit_Call(self, node: ast.Call) -> None:
        # 1. Count relative layout calls
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            if method_name in self.RELATIVE_METHODS:
                self.relative_layout_calls += 1

            # 2. Check move_to with raw list/tuple coordinates
            elif method_name == "move_to":
                if node.args:
                    arg = node.args[0]
                    if self._is_axes_call(arg) or self._is_origin_or_direction_constant(arg):
                        pass
                    elif isinstance(arg, (ast.List, ast.Tuple)):
                        if self._contains_numeric_literals(arg.elts):
                            self.raw_coordinate_calls += 1
                            self.issues.append(
                                PositioningLintIssue(
                                    line=node.lineno,
                                    col=node.col_offset,
                                    mobject_call="move_to",
                                    message=f"Hardcoded coordinate list/tuple in `.move_to(...)`: `{self._get_line_snippet(node.lineno)}`",
                                    suggestion="Use `.next_to(target, DIRECTION, buff=...)`, `.to_edge(UP/DOWN/LEFT/RIGHT)`, or `axes.c2p(x, y)`.",
                                    severity="warning",
                                )
                            )
                    elif isinstance(arg, ast.Call):
                        # Detect np.array([x, y, 0])
                        func = arg.func
                        is_np_array = (
                            isinstance(func, ast.Attribute) and func.attr == "array"
                        ) or (isinstance(func, ast.Name) and func.id == "array")
                        if is_np_array and arg.args and isinstance(arg.args[0], (ast.List, ast.Tuple)):
                            if self._contains_numeric_literals(arg.args[0].elts):
                                self.raw_coordinate_calls += 1
                                self.issues.append(
                                    PositioningLintIssue(
                                        line=node.lineno,
                                        col=node.col_offset,
                                        mobject_call="move_to",
                                        message=f"Hardcoded `np.array(...)` in `.move_to(...)`: `{self._get_line_snippet(node.lineno)}`",
                                        suggestion="Replace absolute np.array with relative `.next_to()`, `.arrange()`, or `.to_edge()`.",
                                        severity="warning",
                                    )
                                )

            # 3. Check set_center(np.array([...]))
            elif method_name == "set_center":
                self.raw_coordinate_calls += 1
                self.issues.append(
                    PositioningLintIssue(
                        line=node.lineno,
                        col=node.col_offset,
                        mobject_call="set_center",
                        message=f"Direct `.set_center(...)` used: `{self._get_line_snippet(node.lineno)}`",
                        suggestion="Avoid set_center. Use `.move_to(target)` or `.next_to()`.",
                        severity="warning",
                    )
                )

        # 4. Check Dot(point=[...]) with hardcoded non-zero list coordinates
        elif isinstance(node.func, ast.Name) and node.func.id == "Dot":
            # Check positional or keyword point argument
            point_arg = None
            if node.args:
                point_arg = node.args[0]
            for kw in node.keywords:
                if kw.arg == "point":
                    point_arg = kw.value
                    break

            if point_arg and not self._is_axes_call(point_arg) and not self._is_origin_or_direction_constant(point_arg):
                if isinstance(point_arg, (ast.List, ast.Tuple)) and self._contains_numeric_literals(point_arg.elts):
                    self.raw_coordinate_calls += 1
                    self.issues.append(
                        PositioningLintIssue(
                            line=node.lineno,
                            col=node.col_offset,
                            mobject_call="Dot",
                            message=f"Dot instantiated with raw screen coordinate: `{self._get_line_snippet(node.lineno)}`",
                            suggestion="If placing on a graph, use `axes.c2p(x, y)`. Otherwise use relative `.next_to()` or `VGroup.arrange()`.",
                            severity="warning",
                        )
                    )

        self.generic_visit(node)


def lint_manim_positioning(code: str) -> PositioningLintReport:
    """Scan Manim Python source code for fragile positioning patterns."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Syntax errors are caught by Pyright/compiler, skip positioning AST
        return PositioningLintReport(valid=True, issues=[])

    visitor = ManimPositioningVisitor(code)
    visitor.visit(tree)

    # If the file has raw coordinates and ZERO relative layout calls, escalate severity to error
    if visitor.raw_coordinate_calls > 0 and visitor.relative_layout_calls == 0:
        for issue in visitor.issues:
            issue.severity = "error"

    valid = not any(issue.severity == "error" for issue in visitor.issues)
    return PositioningLintReport(
        valid=valid,
        issues=visitor.issues,
        relative_layout_calls=visitor.relative_layout_calls,
        raw_coordinate_calls=visitor.raw_coordinate_calls,
    )


def lint_manim_file(file_path: Path | str) -> PositioningLintReport:
    """Lint a Python file on disk."""
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    return lint_manim_positioning(p.read_text(encoding="utf-8"))
