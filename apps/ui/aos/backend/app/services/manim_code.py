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
    # Semantic-drift warnings: rewrites that are crash-safe but may change
    # visual meaning.  Surfaced here so VLM / keyframe reviewers can inspect.
    semantic_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreflightResult:
    valid: bool
    errors: tuple[dict[str, object], ...] = ()
    status: str = "safe"
    blocking: bool = False
    issues: tuple[dict[str, object], ...] = ()


_COMMON_MANIM_NAMES = {
    "Scene", "ThreeDScene", "MovingCameraScene", "VoiceoverScene", "Text", "Tex", "MathTex",
    "VGroup", "Group", "VMobject", "Mobject", "Arrow", "Line", "DashedLine", "Dot", "Circle",
    "Rectangle", "SurroundingRectangle", "Brace", "NumberLine", "ValueTracker", "Axes", "NumberPlane",
    "Write", "Create", "DrawBorderThenFill", "FadeIn", "FadeOut", "Uncreate", "Transform",
    "ReplacementTransform", "TransformMatchingTex", "GrowArrow", "Indicate", "Circumscribe",
    "UP", "DOWN", "LEFT", "RIGHT", "ORIGIN", "IN", "OUT", "UL", "UR", "DL", "DR", "PI",
    "BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "ORANGE", "PURPLE", "TEAL", "GRAY", "GREY",
    "BLUE_C", "RED_C", "GREEN_C", "TEAL_C", "YELLOW_C", "GRAY_A", "GREY_A", "GRAY_B", "GREY_B",
    "GRAY_C", "GREY_C", "GRAY_D", "GREY_D", "GRAY_E", "GREY_E", "DARK_GRAY", "DARK_GREY",
    "LIGHT_GRAY", "LIGHT_GREY", "GOLD", "PINK", "MAROON", "SMALL_BUFF",
    "MED_SMALL_BUFF", "MED_LARGE_BUFF", "LARGE_BUFF", "AnimationGroup", "LaggedStart", "Succession",
    "GrowFromCenter", "DEFAULT_FONT_SIZE", "DEGREES",
}
_BUILTIN_NAMES = set(dir(builtins)) | {"np", "numpy", "config", "self"}


# MathTex tokenisation is not stable enough to rely on a chained
# ``get_part_by_tex(...).get_center()`` call.  A symbol may be grouped into a
# larger token, so get_part_by_tex can return None even though it is visible.
# Keep this repair deliberately narrow: only simple object expressions and a
# single-line lookup are rewritten.
#
# NOTE: args group previously excluded parentheses, which rejected valid LaTeX
# strings like "f(x)".  We now allow any non-newline chars (lazy) so args like
# get_part_by_tex("f(x)") match correctly.
_UNSAFE_TEX_CENTER = re.compile(
    r"(?P<object>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)"
    r"\.get_part_by_tex\((?P<args>[^\n]+?)\)\.get_center\(\)"
)
_UNSAFE_TEX_SHIFT = re.compile(
    r"(?P<object>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)"
    r"\.get_part_by_tex\((?P<args>[^\n]+?)\)\.shift\((?P<shift>[^\n]+?)\)"
)
_UNSUPPORTED_SCENE_CAMERA = re.compile(
    r"(?m)^(?P<indent>\s*)self\.camera\.frame\.move_to\((?P<point>[^\n]+)\)\s*$"
)
_MULTI_TEX_LOOKUP = re.compile(
    r"(?P<object>[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)"
    r"\.get_parts_by_tex\((?P<args>[^\n]+?)\)"
)

# Names of Mobject-producing callables that make integer indexing meaningful.
# Used to gate the generic BrittleMobjectIndex check so we don't flag plain
# list/dict subscripts that happen to use an integer key.
_MOBJECT_CONSTRUCTORS = {"MathTex", "Tex", "VGroup", "Group", "VMobject", "Mobject"}
_UNSUPPORTED_TEX_COMPILER = re.compile(
    r"(?m)^(?P<indent>\s*)config(?:\[\s*['\"]tex_compiler['\"]\s*\]|\.tex_compiler)\s*=.*$"
)


class _NameCollector(ast.NodeVisitor):
    """Collect module-level and class-level name definitions.

    Function parameters are scoped to their function so that a parameter
    named ``n`` in method A does not suppress ``UndefinedName`` for bare ``n``
    in method B where it was never defined.
    """

    def __init__(self) -> None:
        self.defined: set[str] = set()
        self.loaded: list[ast.Name] = []
        self.has_manim_wildcard = False
        self._function_param_sets: list[set[str]] = []

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
        # The function name itself is module/class-level visible.
        self.defined.add(node.name)
        # Collect parameter names as a scoped set for this function only.
        param_names: set[str] = set()
        param_names.update(arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs))
        if node.args.vararg:
            param_names.add(node.args.vararg.arg)
        if node.args.kwarg:
            param_names.add(node.args.kwarg.arg)
        # Push params into defined only for the duration of visiting this node.
        self._function_param_sets.append(param_names)
        self.defined |= param_names
        self.generic_visit(node)
        # Pop: remove params that are not also defined at a higher scope.
        self._function_param_sets.pop()
        outer_params = set().union(*self._function_param_sets) if self._function_param_sets else set()
        for p in param_names - outer_params:
            self.defined.discard(p)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.defined.add(node.name)
        self.generic_visit(node)


def preflight_manim_code(code: str) -> PreflightResult:
    """Run cheap static checks before invoking the expensive Manim renderer."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        syntax_err = {
            "type": "SyntaxError",
            "severity": "error",
            "blocking": True,
            "message": exc.msg,
            "line": exc.lineno,
            "column": exc.offset,
            "text": (exc.text or "").strip(),
        }
        return PreflightResult(
            valid=False,
            errors=(syntax_err,),
            status="failed",
            blocking=True,
            issues=(syntax_err,),
        )

    collector = _NameCollector()
    collector.visit(tree)
    errors: list[dict[str, object]] = []
    # If no wildcard import, check for obviously undefined names;
    # otherwise let Pyright LSP perform authoritative type and symbol analysis.
    if not collector.has_manim_wildcard:
        for node in collector.loaded:
            if node.id not in collector.defined and node.id not in _BUILTIN_NAMES:
                errors.append(
                    {
                        "type": "UndefinedName",
                        "name": node.id,
                        "suggestion": None,
                        "message": f"Name '{node.id}' is not defined",
                        "line": node.lineno,
                        "column": node.col_offset + 1,
                    }
                )

    # These are valid Python, but common generated-code failures that otherwise
    # cost a full Manim render before being discovered. Keep collecting rather
    # than returning on the first finding so one repair request gets the whole
    # diagnostic bundle.
    #
    # Build the set of names proven to be Mobject-backed so BrittleMobjectIndex
    # is only emitted for actual Mobjects, not plain list/dict subscripts.
    mobject_names = _collect_mobject_names(tree)
    # Run the precise pass first so we can deduplicate against its line/col keys.
    precise_findings = _find_mobject_index_mismatches(tree, code)
    precise_keys: set[tuple[int, int]] = {
        (int(f["line"]), int(f["column"])) for f in precise_findings
    }

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
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, int)
        ):
            col = node.col_offset + 1
            # Skip sites already covered by the precise pass (deduplication).
            if (node.lineno, col) in precise_keys:
                continue
            # Only flag names proven to be Mobject-backed; skip plain list/dict.
            if isinstance(node.value, ast.Name) and node.value.id in mobject_names:
                errors.append({
                    "type": "BrittleMobjectIndex",
                    "severity": "warning",
                    "message": (
                        "Integer indexing of a generated Mobject may be out of range; "
                        "use a checked submobject or get_part_by_tex."
                    ),
                    "line": node.lineno,
                    "column": col,
                    "index": node.slice.value,
                })

    errors.extend(_find_nonraw_tex_strings(code))
    errors.extend(precise_findings)

    for item in errors:
        item["blocking"] = item.get("severity", "error") == "error"

    has_blocking = any(item.get("blocking", False) for item in errors)
    status_val = "safe" if not errors else ("failed" if has_blocking else "warning")

    return PreflightResult(
        valid=not has_blocking,
        errors=tuple(errors),
        status=status_val,
        blocking=has_blocking,
        issues=tuple(errors),
    )


def _collect_mobject_names(tree: ast.AST) -> set[str]:
    """Return all names assigned from a known Mobject constructor.

    Used to gate ``BrittleMobjectIndex`` warnings to proven-Mobject bases,
    avoiding false positives for plain list/dict/tuple subscripts.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        callee: str | None = None
        if isinstance(node.value.func, ast.Name):
            callee = node.value.func.id
        elif isinstance(node.value.func, ast.Attribute):
            callee = node.value.func.attr
        if callee not in _MOBJECT_CONSTRUCTORS:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def _find_mobject_index_mismatches(tree: ast.AST, code: str) -> list[dict[str, object]]:
    """Compare literal Mobject indexes with their local construction shape.

    This catches semantic failures such as ``eq = MathTex("x = y")`` followed
    by ``eq[1]`` before Manim has to render. Unknown/dynamic definitions are
    reported as warnings so valid code is not rejected merely because static
    analysis cannot prove its shape.
    """
    definitions: dict[str, tuple[int | None, str, int, list[str]]] = {}
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
        # Collect string literal args so auto-fix can suggest get_part_by_tex.
        tex_args: list[str] = []
        for arg in call.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                tex_args.append(arg.value)
        definitions[node.targets[0].id] = (
            count,
            ast.get_source_segment(code, call) or callee,
            node.lineno,
            tex_args,
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
        count, expression, definition_line, tex_args = definition
        idx = node.slice.value
        finding: dict[str, object] = {
            "type": "MobjectIndexOutOfRange" if count is not None and idx >= count else "MobjectIndexShapeCheck",
            "name": name,
            "index": idx,
            "definition_line": definition_line,
            "definition": expression,
            "line": node.lineno,
            "column": node.col_offset + 1,
            "message": (
                f"{name}[{idx}] is not valid for this statically known construction with {count} top-level part(s)."
                if count is not None and idx >= count
                else f"Check {name}[{idx}] against the construction before indexing."
            ),
            "suggestion": "split MathTex/Tex into explicit arguments, use isolate, or transform the whole mobject safely",
        }
        # Attach auto-fix hint when tex args are statically known.
        if tex_args and 0 <= idx < len(tex_args):
            finding["auto_fix_hint"] = f"{name}.get_part_by_tex({tex_args[idx]!r})"
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


def _auto_fix_mobject_indexes(code: str) -> tuple[str, list[str]]:
    """Replace statically-provable Mobject integer subscripts with get_part_by_tex calls.

    Only rewrites sites where:
    1. The variable is assigned from MathTex/Tex with plain string literal args.
    2. The index is a non-negative integer within the known arg list.
    3. isolate= is NOT used (which changes arg semantics).

    Sites that don't meet these criteria are left for the LLM repair agent.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code, []

    tex_constructors = {"MathTex", "Tex"}
    definitions: dict[str, tuple[list[str], int]] = {}  # name → (tex_args, def_lineno)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        call = node.value
        callee = call.func.id if isinstance(call.func, ast.Name) else None
        if callee not in tex_constructors:
            continue
        if any(keyword.arg == "isolate" for keyword in call.keywords):
            continue  # isolate= makes the shape dynamic; skip
        tex_args: list[str] = []
        for arg in call.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                tex_args.append(arg.value)
        if not tex_args:
            continue
        definitions[node.targets[0].id] = (tex_args, node.lineno)

    # Collect replacement sites; sort in reverse source order to preserve offsets.
    replacements: list[tuple[int, int, str, str]] = []  # (start, end, old, new)
    lines = code.splitlines(keepends=True)
    line_offsets: list[int] = []
    pos = 0
    for ln in lines:
        line_offsets.append(pos)
        pos += len(ln)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name):
            continue
        if not isinstance(node.slice, ast.Constant) or not isinstance(node.slice.value, int):
            continue
        name = node.value.id
        if name not in definitions:
            continue
        tex_args, _ = definitions[name]
        idx = node.slice.value
        if idx < 0 or idx >= len(tex_args):
            continue  # out-of-range; leave for LLM
        new_expr = f"{name}.get_part_by_tex({tex_args[idx]!r})"
        seg = ast.get_source_segment(code, node)
        if seg is None:
            continue
        start_offset = line_offsets[node.lineno - 1] + node.col_offset
        end_offset = start_offset + len(seg)
        replacements.append((start_offset, end_offset, seg, new_expr))

    if not replacements:
        return code, []

    changes: list[str] = []
    for start, end, old, new in sorted(replacements, key=lambda r: r[0], reverse=True):
        code = code[:start] + new + code[end:]
        changes.append(f"Auto-fixed Mobject index: {old!r} → {new!r}")
    return code, changes


def repair_manim_code(code: str) -> CodeRepair:
    """Make known generated-source compatibility fixes before compilation."""
    if not code:
        return CodeRepair(code="")

    changes: list[str] = []
    semantic_warnings: list[str] = []

    def replace_unsafe_center(match: re.Match[str]) -> str:
        obj = match.group("object")
        part_expr = match.group("args")
        # Record semantic drift: get_center() of the whole mobject vs the part.
        semantic_warnings.append(
            f"Rewrote {obj}.get_part_by_tex({part_expr}).get_center() → {obj}.get_center(): "
            "now returns centroid of the whole mobject, not the specific part. "
            "Verify arrow/label positioning in keyframe review."
        )
        changes.append(
            f"Replaced unsafe get_part_by_tex({part_expr}).get_center() with stable parent-mobject center "
            "(semantic drift: centroid may differ — see semantic_warnings)"
        )
        return f"{obj}.get_center()  # REVIEW: was get_part_by_tex({part_expr}).get_center()"

    repaired = _UNSAFE_TEX_CENTER.sub(replace_unsafe_center, code)

    def replace_unsafe_shift(match: re.Match[str]) -> str:
        obj = match.group("object")
        part_expr = match.group("args")
        shift_expr = match.group("shift")
        semantic_warnings.append(
            f"Rewrote {obj}.get_part_by_tex({part_expr}).shift({shift_expr}) → expression using {obj}.get_center(): "
            "now shifts relative to the whole-mobject centroid. Verify positioning in keyframe review."
        )
        changes.append(
            f"Replaced unsafe get_part_by_tex({part_expr}).shift() with stable parent-mobject point "
            "(semantic drift: centroid may differ — see semantic_warnings)"
        )
        return (
            f"({obj}.get_center() + ({shift_expr}))"
            f"  # REVIEW: was get_part_by_tex({part_expr}).shift({shift_expr})"
        )

    repaired = _UNSAFE_TEX_SHIFT.sub(replace_unsafe_shift, repaired)

    def replace_multi_tex_lookup(match: re.Match[str]) -> str:
        # get_parts_by_tex returns ALL matching occurrences.  The previous
        # rewrite used one get_part_by_tex per token, silently dropping
        # duplicates.  Preserve cardinality with a VGroup comprehension that
        # filters by tex_string membership.
        obj = match.group("object")
        args = match.group("args")
        changes.append(
            "Replaced get_parts_by_tex (all-matches) with a VGroup comprehension "
            "that preserves cardinality across all matching parts"
        )
        return (
            f"VGroup(*[p for p in {obj} if p.tex_string in ({args},)])"
            f"  # was: {obj}.get_parts_by_tex({args})"
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

    # Prefix plain string literals passed to Tex/MathTex with r.
    repaired, raw_changes = _repair_nonraw_tex_strings(repaired)
    changes.extend(raw_changes)

    # Auto-fix provable integer Mobject subscripts → get_part_by_tex calls.
    # Runs after raw-string pass so tex strings are already prefixed.
    repaired, index_changes = _auto_fix_mobject_indexes(repaired)
    changes.extend(index_changes)

    return CodeRepair(
        code=repaired,
        changes=tuple(dict.fromkeys(changes)),
        semantic_warnings=tuple(semantic_warnings),
    )


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
