"""Documentation-guided, deterministic Manim source repair helpers."""

from __future__ import annotations

import ast
import builtins
import difflib
import re
from dataclasses import dataclass
from typing import Any, Callable


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
_BACKGROUND_COLOR = re.compile(r"(?m)^(?P<indent>\s*)self\.set_background_color\((?P<color>[^)]+)\)\s*$")


@dataclass(frozen=True)
class RepairResult:
    source: str
    changes: tuple[str, ...]
    syntax_valid: bool
    syntax_error: str | None


_COMMON_MANIM_NAMES = {
    "Scene", "ThreeDScene", "MovingCameraScene", "VoiceoverScene", "Text", "Tex", "MathTex", "VGroup",
    "Arrow", "Line", "SurroundingRectangle", "Write", "Create", "FadeIn", "FadeOut", "Transform",
    "ReplacementTransform", "TransformMatchingTex", "GrowArrow", "UP", "DOWN", "LEFT", "RIGHT",
    "ORIGIN", "BLACK", "WHITE", "RED", "GREEN", "BLUE", "YELLOW", "TEAL", "GRAY", "GREY", "PI",
    "BLUE_C", "RED_C", "GREEN_C", "TEAL_C", "YELLOW_C", "GRAY_A", "GREY_A", "GRAY_B", "GREY_B",
    "GRAY_C", "GREY_C", "GRAY_D", "GREY_D", "GRAY_E", "GREY_E", "DARK_GRAY", "DARK_GREY",
    "LIGHT_GRAY", "LIGHT_GREY", "GOLD", "PINK", "MAROON", "SMALL_BUFF",
    "MED_SMALL_BUFF", "MED_LARGE_BUFF", "LARGE_BUFF", "AnimationGroup", "LaggedStart", "Succession",
    "GrowFromCenter", "DEFAULT_FONT_SIZE", "DEGREES",
}


def preflight_source(source: str) -> list[dict[str, object]]:
    """Return all cheap syntax/name diagnostics for MCP callers."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [{
            "type": "SyntaxError",
            "message": exc.msg,
            "line": exc.lineno,
            "column": exc.offset,
            "text": (exc.text or "").strip(),
        }]

    defined = set(dir(builtins)) | {"config", "self"}
    loaded: list[ast.Name] = []
    wildcard = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            defined.update(alias.asname or alias.name for alias in node.names if alias.name != "*")
            wildcard = wildcard or (node.module == "manim" and any(a.name == "*" for a in node.names))
        elif isinstance(node, ast.Import):
            defined.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                defined.add(node.id)
            else:
                loaded.append(node)

    errors = []
    for node in loaded:
        close = difflib.get_close_matches(node.id, _COMMON_MANIM_NAMES, n=1, cutoff=0.78)
        if node.id in defined or (wildcard and (not close or node.id in _COMMON_MANIM_NAMES)):
            continue
        errors.append({
            "type": "PossibleTypo" if close else "UndefinedName",
            "name": node.id,
            "suggestion": close[0] if close else None,
            "message": f"Unknown Manim name '{node.id}'; did you mean '{close[0]}'?" if close else f"Name '{node.id}' is not defined",
            "line": node.lineno,
            "column": node.col_offset + 1,
        })
    return errors


def deterministic_repair(source: str) -> RepairResult:
    """Apply narrow, safe fixes for common generated Manim mistakes."""
    changes: list[str] = []

    def replace_center(match: re.Match[str]) -> str:
        changes.append("Replaced unsafe get_part_by_tex(...).get_center() with the parent mobject center")
        return f"{match.group('object')}.get_center()"

    repaired = _UNSAFE_TEX_CENTER.sub(replace_center, source)

    def replace_shift(match: re.Match[str]) -> str:
        changes.append("Replaced unsafe get_part_by_tex(...).shift(...) endpoint with a stable parent-mobject point")
        return f"({match.group('object')}.get_center() + ({match.group('shift')}))"

    repaired = _UNSAFE_TEX_SHIFT.sub(replace_shift, repaired)

    def replace_multi_tex_lookup(match: re.Match[str]) -> str:
        changes.append("Normalized multi-argument get_parts_by_tex lookup to supported single-token lookups")
        obj = match.group("object")
        args = match.group("args")
        return f"VGroup(*[part for token in ({args},) if (part := {obj}.get_part_by_tex(token)) is not None])"

    repaired = _MULTI_TEX_LOOKUP.sub(replace_multi_tex_lookup, repaired)

    def remove_tex_compiler_override(match: re.Match[str]) -> str:
        changes.append("Removed unsupported config tex_compiler override; Manim controls the active LaTeX compiler")
        return f"{match.group('indent')}pass  # LaTeX compiler is managed by Manim configuration"

    repaired = _UNSUPPORTED_TEX_COMPILER.sub(remove_tex_compiler_override, repaired)

    def remove_scene_camera_move(match: re.Match[str]) -> str:
        changes.append("Removed unsupported self.camera.frame movement; use MovingCameraScene for camera-frame animation")
        return f"{match.group('indent')}pass  # Camera-frame movement requires MovingCameraScene"

    repaired = _UNSUPPORTED_SCENE_CAMERA.sub(remove_scene_camera_move, repaired)

    def replace_background(match: re.Match[str]) -> str:
        changes.append("Replaced unsupported Scene.set_background_color(...) with config.background_color")
        return f"{match.group('indent')}config.background_color = {match.group('color')}"

    repaired = _BACKGROUND_COLOR.sub(replace_background, repaired)
    try:
        ast.parse(repaired)
    except SyntaxError as exc:
        return RepairResult(
            source=repaired,
            changes=tuple(dict.fromkeys(changes)),
            syntax_valid=False,
            syntax_error=f"{exc.msg} at line {exc.lineno}, column {exc.offset}",
        )
    return RepairResult(
        source=repaired,
        changes=tuple(dict.fromkeys(changes)),
        syntax_valid=True,
        syntax_error=None,
    )


def documentation_context(
    *,
    error: str,
    source: str,
    search: Callable[[str, int, str | None], list[Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    """Retrieve focused docs for a repair without sending source elsewhere."""
    query = f"Manim Community Edition repair: {error[-1800:]}\n{source[-1200:]}"
    hits = search(query, top_k, "entry")
    return [
        {
            "score": round(float(hit.score), 4),
            "name": hit.chunk.get("name", ""),
            "module": hit.chunk.get("module", ""),
            "signature": hit.chunk.get("signature", ""),
            "text": hit.chunk.get("text", ""),
        }
        for hit in hits
    ]
