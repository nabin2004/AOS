"""Detect filler / placeholder Manim voiceover lines (AST string constants)."""

from __future__ import annotations

import ast
import re

FILLER_VOICEOVER = "filler_voiceover"

_FILLER_EXACT = frozenset(
    {
        "watch this next step",
        "let's begin",
        "let's look at this on the board",
        "let's look at this",
        "let's take a look at this",
        "let's take a look",
        "as you can see",
        "here is the equation",
        "this is the equation",
        "now we see",
        "let's explore this",
        "isn't that amazing",
        "how beautiful",
        "this is magical",
        "pretty cool, right",
        "isn't mathematics wonderful",
        "let's explore this identity further",
    }
)

_FILLER_PREFIXES = (
    "here we have ",
    "let's look at this",
    "let's take a look",
    "as you can see",
    "now we see",
    "here is the equation",
    "this is the equation",
    "let's explore this",
)

_STAGE_DIRECTION = re.compile(
    r"^(display|create|show|highlight|clear|fade|write the|watch this|"
    r"let's begin|look at this next|here we have)\b",
    re.IGNORECASE,
)

_WS = re.compile(r"\s+")

FILLER_HINT = (
    "Voiceover must teach a learning point, not announce that an object "
    "appeared. Do not copy on-screen Tex into speech. Do not say "
    "'Let's look at this on the board' or 'Here we have …'."
)


def normalize_narration(text: str) -> str:
    stripped = _WS.sub(" ", (text or "").strip()).rstrip(".").strip()
    return stripped.lower()


def is_filler_narration(text: str) -> bool:
    """True if spoken text is generic filler, stage direction, or Tex-copy prefix."""
    raw = (text or "").strip()
    if not raw:
        return True
    normalized = normalize_narration(raw)
    if not normalized:
        return True
    if normalized in _FILLER_EXACT:
        return True
    if any(normalized.startswith(prefix) for prefix in _FILLER_PREFIXES):
        return True
    if _STAGE_DIRECTION.match(raw):
        return True
    return False


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def iter_voiceover_texts(code: str) -> list[str]:
    """Return constant ``text=`` values on ``voiceover(...)`` calls."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    texts: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) != "voiceover":
            continue
        for kw in node.keywords:
            if kw.arg == "text" and isinstance(kw.value, ast.Constant):
                if isinstance(kw.value.value, str):
                    texts.append(kw.value.value)
    return texts


def filler_voiceover_error(code: str) -> str | None:
    """Return ``filler_voiceover`` if any voiceover line is banned filler."""
    for text in iter_voiceover_texts(code):
        if is_filler_narration(text):
            return FILLER_VOICEOVER
    return None
