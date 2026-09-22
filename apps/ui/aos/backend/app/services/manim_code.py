"""Small deterministic repairs for common Manim source-generation mistakes."""

from __future__ import annotations

import ast
import builtins
import difflib
import re
import tokenize
from io import StringIO
from dataclasses import dataclass


@dataclass(frozen=True)
class CodeRepair:
    code: str
    changes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreflightResult:
    valid: bool
    errors: tuple[dict[str, object], ...] = ()


_COMMON_MANIM_NAMES = {
    "Scene", "ThreeDScene", "MovingCameraScene", "VoiceoverScene", "Text", "Tex", "MathTex",
    "VGroup", "Group", "VMobject", "Mobject", "Arrow", "Line", "DashedLine", "Dot", "Circle",
    "Rectangle", "SurroundingRectangle", "Brace", "NumberLine", "ValueTracker", "Axes", "NumberPlane",
    "Write", "Create", "DrawBorderThenFill", "FadeIn", "FadeOut", "Uncreate", "Transform",
    "ReplacementTransform", "TransformMatchingTex", "GrowArrow", "Indicate", "Circumscribe",
    "UP", "DOWN", "LEFT", "RIGHT", "ORIGIN", "IN", "OUT", "UL", "UR", "DL", "DR", "PI",
    "BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "ORANGE", "PURPLE", "TEAL", "GRAY",
    "BLUE_C", "RED_C", "GREEN_C", "TEAL_C", "YELLOW_C", "GRAY_A", "GREY_A", "SMALL_BUFF",
    "MED_SMALL_BUFF", "MED_LARGE_BUFF", "LARGE_BUFF", "AnimationGroup", "LaggedStart", "Succession",
    "GrowFromCenter", "DEFAULT_FONT_SIZE", "DEGREES",
}
_BUILTIN_NAMES = set(dir(builtins)) | {"np", "numpy", "config", "self"}


# MathTex tokenisation is not stable enough to rely on a chained
# ``get_part_by_tex(...).get_center()`` call.  A symbol may be grouped into a
# larger token, so get_part_by_tex can return None even though it is visible.
# Keep this repair deliberately narrow: only simple object expressions and a
# single-line lookup are rewritten.
_UNSAFE_TEX_CENTER = re.compile(
    r"(?P<object>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)"
    r"\.get_part_by_tex\((?P<args>[^()\n]+)\)\.get_center\(\)"
)
_UNSAFE_TEX_SHIFT = re.compile(
    r"(?P<object>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)"
    r"\.get_part_by_tex\((?P<args>[^()\n]+)\)\.shift\((?P<shift>[^()\n]+)\)"
)
_UNSUPPORTED_SCENE_CAMERA = re.compile(
    r"(?m)^(?P<indent>\s*)self\.camera\.frame\.move_to\((?P<point>[^\n]+)\)\s*$"
)
_MULTI_TEX_LOOKUP = re.compile(
    r"(?P<object>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)"
    r"\.get_parts_by_tex\((?P<args>[^()\n]+)\)"
)
_UNSUPPORTED_TEX_COMPILER = re.compile(
    r"(?m)^(?P<indent>\s*)config(?:\[\s*['\"]tex_compiler['\"]\s*\]|\.tex_compiler)\s*=.*$"
)


class _NameCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.defined: set[str] = set()
        self.loaded: list[ast.Name] = []
        self.has_manim_wildcard = False

    def visit_Import(self, node: ast.Import) -> None:
        self.defined.update(alias.asname or alias.name.split(".")[0] for alias in node.names)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "manim" and any(alias.name == "*" for alias in node.names):
            self.has_manim_wildcard = True
        self.defined.update(alias.asname or alias.name for alias in node.names if alias.name != "*")

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.loaded.append(node)
        else:
            self.defined.add(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.defined.add(node.name)
        self.defined.update(arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs))
        if node.args.vararg:
            self.defined.add(node.args.vararg.arg)
        if node.args.kwarg:
            self.defined.add(node.args.kwarg.arg)
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.defined.add(node.name)
        self.generic_visit(node)


def preflight_manim_code(code: str) -> PreflightResult:
    """Run cheap static checks before invoking the expensive Manim renderer."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return PreflightResult(
            valid=False,
            errors=(
                {
                    "type": "SyntaxError",
                    "message": exc.msg,
                    "line": exc.lineno,
                    "column": exc.offset,
                    "text": (exc.text or "").strip(),
                },
            ),
        )

    collector = _NameCollector()
    collector.visit(tree)
    errors: list[dict[str, object]] = []
    for node in collector.loaded:
        if node.id in collector.defined or node.id in _BUILTIN_NAMES:
            continue
        close = difflib.get_close_matches(node.id, _COMMON_MANIM_NAMES, n=1, cutoff=0.78)
        if collector.has_manim_wildcard and (not close or node.id in _COMMON_MANIM_NAMES):
            continue
        errors.append(
            {
                "type": "UndefinedName" if not close else "PossibleTypo",
                "name": node.id,
                "suggestion": close[0] if close else None,
                "message": f"Name '{node.id}' is not defined" if not close else f"Unknown Manim name '{node.id}'; did you mean '{close[0]}'?",
                "line": node.lineno,
                "column": node.col_offset + 1,
            }
        )

    # These are valid Python, but common generated-code failures that otherwise
    # cost a full Manim render before being discovered. Keep collecting rather
    # than returning on the first finding so one repair request gets the whole
    # diagnostic bundle.
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == "BOTTOM":
            errors.append({
                "type": "UnsupportedManimName",
                "name": "BOTTOM",
                "suggestion": "DOWN",
                "message": "Manim uses DOWN; BOTTOM is not a direction constant.",
                "line": node.lineno,
                "column": node.col_offset + 1,
            })
        elif isinstance(node, ast.Attribute) and node.attr == "set_text":
            errors.append({
                "type": "UnsupportedManimMethod",
                "name": "set_text",
                "suggestion": "construct a new Text/MathTex mobject and use ReplacementTransform",
                "message": "Generated Manim code calls set_text(), which is not a reliable ManimCE mobject API.",
                "line": node.lineno,
                "column": node.col_offset + 1,
            })
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
            errors.append({
                "type": "BrittleMobjectIndex",
                "severity": "warning",
                "message": "Integer indexing of a generated Mobject may be out of range; use a checked submobject or get_part_by_tex.",
                "line": node.lineno,
                "column": node.col_offset + 1,
                "index": node.slice.value,
            })

    errors.extend(_find_nonraw_tex_strings(code))
    errors.extend(_find_mobject_index_mismatches(tree, code))

    return PreflightResult(
        valid=not any(item.get("severity", "error") == "error" for item in errors),
        errors=tuple(errors),
    )


def _find_mobject_index_mismatches(tree: ast.AST, code: str) -> list[dict[str, object]]:
    """Compare literal Mobject indexes with their local construction shape.

    This catches semantic failures such as ``eq = MathTex("x = y")`` followed
    by ``eq[1]`` before Manim has to render. Unknown/dynamic definitions are
    reported as warnings so valid code is not rejected merely because static
    analysis cannot prove its shape.
    """
    definitions: dict[str, tuple[int | None, str, int]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        call = node.value
        callee = call.func.id if isinstance(call.func, ast.Name) else None
        if callee not in {"MathTex", "Tex", "VGroup", "Group"}:
            continue
        isolate = any(keyword.arg == "isolate" for keyword in call.keywords)
        count = None if isolate else len(call.args)
        definitions[node.targets[0].id] = (
            count,
            ast.get_source_segment(code, call) or callee,
            node.lineno,
        )

    findings: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name):
            continue
        if not isinstance(node.slice, ast.Constant) or not isinstance(node.slice.value, int):
            continue
        name = node.value.id
        definition = definitions.get(name)
        if definition is None:
            continue
        count, expression, definition_line = definition
        finding: dict[str, object] = {
            "type": "MobjectIndexOutOfRange" if count is not None and node.slice.value >= count else "MobjectIndexShapeCheck",
            "name": name,
            "index": node.slice.value,
            "definition_line": definition_line,
            "definition": expression,
            "line": node.lineno,
            "column": node.col_offset + 1,
            "message": (
                f"{name}[{node.slice.value}] is not valid for this statically known construction with {count} top-level part(s)."
                if count is not None and node.slice.value >= count
                else f"Check {name}[{node.slice.value}] against the construction before indexing."
            ),
            "suggestion": "split MathTex/Tex into explicit arguments, use isolate, or transform the whole mobject safely",
        }
        if count is None:
            finding["severity"] = "warning"
        findings.append(finding)
    return findings


def _find_nonraw_tex_strings(code: str) -> list[dict[str, object]]:
    """Find LaTeX strings where Python will consume backslash escapes.

    AST loses the original string prefix, so tokenize is used here. This is a
    diagnostic only: it intentionally reports every offending literal in one
    pass, including the easy-to-miss ``"e \\approx 2.718"`` case.
    """
    findings: list[dict[str, object]] = []
    lines = code.splitlines()
    try:
        tokens = tokenize.generate_tokens(StringIO(code).readline)
        for token in tokens:
            if token.type != tokenize.STRING:
                continue
            prefix_match = re.match(r"(?i)^([rubf]*)", token.string)
            prefix = (prefix_match.group(1) if prefix_match else "").lower()
            if "r" in prefix or "\\" not in token.string:
                continue
            line = lines[token.start[0] - 1] if 0 < token.start[0] <= len(lines) else ""
            before = line[: token.start[1]]
            if not re.search(r"\b(?:MathTex|Tex|SingleStringMathTex)\s*\([^\n]*$", before):
                continue
            findings.append({
                "type": "NonRawTexString",
                "message": "LaTeX string contains backslashes but is not raw; Python may convert \\a, \\t, \\n, etc. into control characters.",
                "suggestion": "prefix the literal with r, for example MathTex(r\"e \\approx 2.718\")",
                "line": token.start[0],
                "column": token.start[1] + 1,
                "text": token.string,
            })
    except (tokenize.TokenError, IndentationError):
        # SyntaxError is reported by ast.parse; do not hide it behind a second
        # tokenizer failure.
        return findings
    return findings


def repair_manim_code(code: str) -> CodeRepair:
    """Make known generated-source compatibility fixes before compilation."""
    if not code:
        return CodeRepair(code="")

    changes: list[str] = []

    def replace_unsafe_center(match: re.Match[str]) -> str:
        changes.append(
            "Replaced unsafe get_part_by_tex(...).get_center() lookup with a stable parent-mobject center"
        )
        return f"{match.group('object')}.get_center()"

    repaired = _UNSAFE_TEX_CENTER.sub(replace_unsafe_center, code)

    def replace_unsafe_shift(match: re.Match[str]) -> str:
        changes.append(
            "Replaced unsafe get_part_by_tex(...).shift(...) endpoint with a stable parent-mobject point"
        )
        return f"({match.group('object')}.get_center() + ({match.group('shift')}))"

    repaired = _UNSAFE_TEX_SHIFT.sub(replace_unsafe_shift, repaired)

    def replace_multi_tex_lookup(match: re.Match[str]) -> str:
        changes.append(
            "Normalized multi-argument get_parts_by_tex lookup to supported single-token lookups"
        )
        obj = match.group("object")
        args = match.group("args")
        return (
            f"VGroup(*[part for token in ({args},) "
            f"if (part := {obj}.get_part_by_tex(token)) is not None])"
        )

    repaired = _MULTI_TEX_LOOKUP.sub(replace_multi_tex_lookup, repaired)

    def remove_tex_compiler_override(match: re.Match[str]) -> str:
        changes.append(
            "Removed unsupported config tex_compiler override; Manim controls the active LaTeX compiler"
        )
        return f"{match.group('indent')}pass  # LaTeX compiler is managed by Manim configuration"

    repaired = _UNSUPPORTED_TEX_COMPILER.sub(remove_tex_compiler_override, repaired)

    def remove_scene_camera_move(match: re.Match[str]) -> str:
        changes.append(
            "Removed unsupported self.camera.frame movement; use MovingCameraScene for camera-frame animation"
        )
        return f"{match.group('indent')}pass  # Camera-frame movement requires MovingCameraScene"

    repaired = _UNSUPPORTED_SCENE_CAMERA.sub(remove_scene_camera_move, repaired)

    if re.search(r"\bBOTTOM\b", repaired):
        repaired = re.sub(r"\bBOTTOM\b", "DOWN", repaired)
        changes.append("Replaced unsupported BOTTOM direction constant with DOWN")

    # Prefix plain string literals passed to Tex/MathTex with r. This fixes
    # Python escape processing before LaTeX is invoked, without touching normal
    # prose strings elsewhere in the scene.
    repaired, raw_changes = _repair_nonraw_tex_strings(repaired)
    changes.extend(raw_changes)
    return CodeRepair(code=repaired, changes=tuple(dict.fromkeys(changes)))


def _repair_nonraw_tex_strings(code: str) -> tuple[str, list[str]]:
    lines = code.splitlines(keepends=True)
    offsets: list[int] = []
    total = 0
    for line in lines:
        offsets.append(total)
        total += len(line)
    replacements: list[tuple[int, int, str]] = []
    try:
        for token in tokenize.generate_tokens(StringIO(code).readline):
            if token.type != tokenize.STRING:
                continue
            prefix_match = re.match(r"(?i)^([rubf]*)(['\"])", token.string)
            if not prefix_match or "r" in prefix_match.group(1).lower() or "f" in prefix_match.group(1).lower():
                continue
            if "\\" not in token.string:
                continue
            line = lines[token.start[0] - 1] if 0 < token.start[0] <= len(lines) else ""
            if not re.search(r"\b(?:MathTex|Tex|SingleStringMathTex)\s*\([^\n]*$", line[: token.start[1]]):
                continue
            start = offsets[token.start[0] - 1] + token.start[1]
            prefix_end = start + len(prefix_match.group(1))
            replacements.append((prefix_end, prefix_end, "r"))
    except (tokenize.TokenError, IndentationError):
        return code, []
    for start, end, value in reversed(replacements):
        code = code[:start] + value + code[end:]
    return code, [f"Converted {len(replacements)} non-raw Tex/MathTex literal(s) to raw strings"] if replacements else []
