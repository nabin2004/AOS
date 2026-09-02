"""Static Manim Community Edition API checks (no render).

Walks constructor calls and rejects kwargs that never appear as named
``__init__`` parameters on the class MRO. That catches hallucinations such as
``element_color`` on ``Matrix`` (they fall through ``**kwargs`` into
``Mobject.__init__`` and crash at runtime even when ``inspect.signature``
looks permissive).
"""

from __future__ import annotations

import ast
import inspect
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable

# Eval-log hallucinations (MB-004 / 006 / 011) — never valid CE constructor kwargs.
BANNED_KWARGS = frozenset({"element_color", "max_value", "max_magnitude", "center_point"})

# manimgl / 3b1b leftovers
BANNED_NAMES = frozenset({
    "ShowCreation",
    "ShowCreationThenDestruction",
    "ShowCreationThenFadeOut",
    "TextMobject",
    "TexMobject",
})

AXES_TYPES = frozenset(
    {
        "Axes",
        "NumberPlane",
        "PolarPlane",
        "ComplexPlane",
        "ThreeDAxes",
        "NumberLine",
    }
)

TEX_CALLEES = frozenset({"MathTex", "Tex", "Title", "TexMobject", "TextMobject"})

# U+2070–U+209F plus common ¹²³
_UNICODE_SCRIPT_RE = re.compile(
    r"[\u00b9\u00b2\u00b3\u2070-\u209f\u2080-\u209c]"
)

_FENCE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)

# Star-import names we resolve without importing manim (tests / no manim env).
STAR_IMPORT_FALLBACK = frozenset(
    {
        "VGroup",
        "VMobject",
        "Mobject",
        "Group",
        "Axes",
        "NumberLine",
        "NumberPlane",
        "ThreeDAxes",
        "PolarPlane",
        "ComplexPlane",
        "Matrix",
        "DecimalMatrix",
        "IntegerMatrix",
        "MobjectMatrix",
        "Arrow",
        "Vector",
        "ArrowVectorField",
        "StreamLines",
        "Circle",
        "Dot",
        "Square",
        "Rectangle",
        "Line",
        "DashedLine",
        "Polygon",
        "RegularPolygon",
        "Triangle",
        "Star",
        "Arc",
        "Annulus",
        "Ellipse",
        "Text",
        "MathTex",
        "Tex",
        "Title",
        "Brace",
        "SurroundingRectangle",
        "FadeIn",
        "FadeOut",
        "Transform",
        "ReplacementTransform",
        "LaggedStart",
        "AnimationGroup",
        "Succession",
        "Create",
        "Write",
        "Indicate",
        "Circumscribe",
        "ValueTracker",
        "DecimalNumber",
        "Integer",
        "BarChart",
        "Table",
        "IntegerTable",
        "DecimalTable",
        "MobjectTable",
        "Code",
        "ImageMobject",
        "SVGMobject",
        "Sphere",
        "Cube",
        "Surface",
        "ParametricFunction",
        "FunctionGraph",
        "TangentLine",
        "Angle",
        "RightAngle",
        "Scene",
        "MovingCameraScene",
        "ThreeDScene",
        "Play",
        "always_redraw",
    }
)


@dataclass(frozen=True)
class LintIssue:
    code: str
    message: str
    lineno: int | None = None


def extract_python(text: str) -> str:
    if not text:
        return ""
    fences = _FENCE_RE.findall(text)
    if fences:
        return fences[-1].strip()
    return text.strip()


def _const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
        return "".join(parts) if parts else None
    return None


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _root_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _root_name(node.value)
    return None


@lru_cache(maxsize=1)
def _manim_namespace() -> dict[str, Any]:
    try:
        import manim as mn
    except ImportError:
        return {}
    out: dict[str, Any] = {}
    for name in dir(mn):
        if name.startswith("_"):
            continue
        obj = getattr(mn, name, None)
        if inspect.isclass(obj):
            out[name] = obj
    return out


def manim_public_classes() -> frozenset[str]:
    ns = _manim_namespace()
    if ns:
        return frozenset(ns)
    return STAR_IMPORT_FALLBACK


def named_init_params(cls: type) -> set[str]:
    """Named ``__init__`` parameters on ``cls`` and every MRO parent."""
    allowed: set[str] = set()
    for base in getattr(cls, "__mro__", ()):
        if base is object:
            break
        init = getattr(base, "__init__", None)
        if init is None:
            continue
        try:
            sig = inspect.signature(init)
        except (TypeError, ValueError):
            continue
        for name, param in sig.parameters.items():
            if name in ("self", "cls"):
                continue
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            allowed.add(name)
    return allowed


def _resolve_alias_map(tree: ast.AST) -> dict[str, str]:
    aliases: dict[str, str] = {}
    public = manim_public_classes()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("manim"):
            for alias in node.names:
                local = alias.asname or alias.name
                if alias.name == "*":
                    for name in public:
                        aliases.setdefault(name, name)
                else:
                    aliases[local] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "manim" or alias.name.startswith("manim."):
                    aliases[alias.asname or alias.name] = alias.name
    return aliases


def _assignment_ctors(tree: ast.AST) -> dict[str, str]:
    assigned: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        ctor = _call_name(node.value.func)
        if not ctor:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                assigned[target.id] = ctor
    return assigned


def lint_source(source: str) -> list[LintIssue]:
    issues: list[LintIssue] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [LintIssue("syntax", f"SyntaxError: {exc.msg}", exc.lineno)]

    aliases = _resolve_alias_map(tree)
    assigned = _assignment_ctors(tree)
    ns = _manim_namespace()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            issues.append(
                LintIssue("banned_name", f"non-CE name {node.id}", node.lineno)
            )

        if not isinstance(node, ast.Call):
            continue

        callee = _call_name(node.func)
        if callee in TEX_CALLEES:
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                text = _const_str(arg)
                if text and _UNICODE_SCRIPT_RE.search(text):
                    issues.append(
                        LintIssue(
                            "unicode_tex",
                            f"{callee} contains Unicode sub/superscripts",
                            node.lineno,
                        )
                    )
                    break

        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "c2p"
        ):
            root = _root_name(node.func.value)
            ctor = assigned.get(root or "", "")
            if ctor not in AXES_TYPES:
                issues.append(
                    LintIssue(
                        "c2p",
                        f"c2p on non-Axes object {root!r} ({ctor or 'unknown'})",
                        node.lineno,
                    )
                )

        if callee is None:
            continue
        ctor = aliases.get(callee, callee)
        kw_names = [kw.arg for kw in node.keywords if kw.arg]
        for kw in kw_names:
            if kw in BANNED_KWARGS:
                issues.append(
                    LintIssue(
                        "banned_kwarg",
                        f"{ctor}(..., {kw}=...) is not a Manim CE constructor argument",
                        node.lineno,
                    )
                )

        cls = ns.get(ctor)
        if cls is None or not kw_names:
            continue
        allowed = named_init_params(cls)
        if not allowed:
            continue
        for kw in kw_names:
            if kw in BANNED_KWARGS:
                continue
            if kw not in allowed:
                issues.append(
                    LintIssue(
                        "unknown_kwarg",
                        f"{ctor}(..., {kw}=...) is not a named MRO parameter",
                        node.lineno,
                    )
                )

    return issues


def lint_assistant_text(text: str) -> list[LintIssue]:
    return lint_source(extract_python(text))


def is_lint_clean(text: str) -> bool:
    return not lint_assistant_text(text)


def coverage_flags(source: str) -> dict[str, int]:
    return {
        "lagged_start": source.count("LaggedStart"),
        "transform": len(re.findall(r"\bTransform\b", source)),
        "fade_in": source.count("FadeIn"),
        "fade_out": source.count("FadeOut"),
        "play": len(re.findall(r"\.play\s*\(", source)),
        "lines": source.count("\n") + (1 if source else 0),
    }


def is_coverage_rich(source: str) -> bool:
    flags = coverage_flags(source)
    stacked_fades = flags["fade_in"] + flags["fade_out"]
    return (
        flags["lagged_start"] >= 1
        or flags["transform"] >= 2
        or stacked_fades >= 3
    )


def assignment_names(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def iter_issues(issues: Iterable[LintIssue]) -> str:
    return "; ".join(f"{i.code}: {i.message}" for i in issues)
