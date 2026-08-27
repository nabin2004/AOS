"""Normalize LLM Manim source and salvage dumped CodeMode text."""

from __future__ import annotations

import ast
import re
import textwrap
from dataclasses import dataclass

_FENCE_OPEN = re.compile(r"^```(?:python|python3|py|text)?\s*$", re.IGNORECASE)
_FENCE_ANY = re.compile(r"^```(?:python|python3|py|text)?\s*", re.IGNORECASE)
_LANGUAGE_TAG_LINE = re.compile(r"^(?:text|python|python3|py)$", re.IGNORECASE)
_COLLAPSED_CLASS_DEF = re.compile(
    r"^([ \t]*)class\s+(\w+)\s*\(([^)]*)\)\s*:\s*(def\s+.+)$",
    re.MULTILINE,
)
_CONSTRUCT_COMMENT_THEN_CODE = re.compile(
    r"^([ \t]*def\s+construct\s*\([^)]*\)\s*:)\s*(#[^\n]*?)\s+"
    r"((?:self\.|[A-Za-z_]\w*\s*=).+)$"
)
_CODE_ASSIGN = re.compile(
    r"\bcode\s*=\s*(?P<q>'''|\"\"\")(?P<body>.*?)(?P=q)",
    re.DOTALL,
)
_INLINE_WRITE = re.compile(
    r"manim_write\s*\(\s*code\s*=\s*(?P<q>'''|\"\"\")(?P<body>.*?)(?P=q)",
    re.DOTALL,
)
_SCENE_NAME = re.compile(
    r"scene_name\s*=\s*['\"](?P<name>[A-Za-z_][A-Za-z0-9_]*)['\"]"
)
_CLASS_NAME = re.compile(
    r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.MULTILINE,
)
_MANIM_IMPORT = re.compile(r"(?:from\s+manim\s+import|import\s+manim)\b")
_SCENE_CLASS = re.compile(
    r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\b"
    r"(?:VoiceoverScene|ThreeDScene|MovingCameraScene|ZoomedScene|Scene)\b",
    re.MULTILINE,
)
_VOICEOVER_IMPORT = "from manim_voiceover import VoiceoverScene"
_SPEECH_IMPORT = "from tools.aos_speech_service import AOSSpeechService"
_IMPORT_THEN_CLASS = re.compile(
    r"(from\s+\S+\s+import\s+\*[ \t]+)(?=class\s+)",
)
_IMPORT_MODULE_THEN_CLASS = re.compile(
    r"(import\s+manim[ \t]+)(?=class\s+)",
)
_COMMENT_THEN_STMT = re.compile(
    r"(#)(.*?)(?=\s+(?:self\.|[A-Za-z_]\w*\s*=))"
)
_IDENT_ASSIGN = re.compile(r"[A-Za-z_]\w*\s*=")
_IDENT_DOT = re.compile(r"[A-Za-z_]\w*\.")


def _parses(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _strip_markdown_fences(code: str) -> str:
    lines = code.replace("\r\n", "\n").split("\n")
    if not lines:
        return code
    start = 0
    end = len(lines)
    while end > start and not lines[end - 1].strip():
        end -= 1
    first = lines[0].strip()
    if first.startswith("```"):
        start = 1
        if not _FENCE_OPEN.match(first) and _FENCE_ANY.match(first):
            rest = _FENCE_ANY.sub("", lines[0], count=1)
            if rest.strip():
                lines[0] = rest
                start = 0
    if end > start and lines[end - 1].strip().startswith("```"):
        end -= 1
    inner = lines[start:end]
    inner = [
        ln
        for ln in inner
        if not _LANGUAGE_TAG_LINE.match(ln.strip()) and ln.strip() != "```"
    ]
    return "\n".join(inner)


def _unescape_outside_strings(code: str) -> str:
    """Turn ``\\n`` / ``\\t`` into real newlines/tabs only outside string literals."""
    out: list[str] = []
    i = 0
    n = len(code)
    quote: str | None = None
    while i < n:
        if quote is None:
            if code.startswith(('"""', "'''"), i):
                quote = code[i : i + 3]
                out.append(quote)
                i += 3
                continue
            ch = code[i]
            if ch in ("'", '"'):
                if (
                    i > 0
                    and code[i - 1].lower() == "r"
                    and (i < 2 or not code[i - 2].isalnum())
                ):
                    quote = ch
                    out.append(ch)
                    i += 1
                    continue
                quote = ch
                out.append(ch)
                i += 1
                continue
            if ch == "\\" and i + 1 < n and code[i + 1] in "nt":
                out.append("\n" if code[i + 1] == "n" else "\t")
                i += 2
                continue
            out.append(ch)
            i += 1
            continue

        if quote in ('"""', "'''"):
            if code.startswith(quote, i):
                out.append(quote)
                i += len(quote)
                quote = None
                continue
            out.append(code[i])
            i += 1
            continue

        ch = code[i]
        if ch == "\\" and i + 1 < n:
            out.append(code[i : i + 2])
            i += 2
            continue
        if ch == quote:
            out.append(ch)
            quote = None
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _split_import_then_class(code: str) -> str:
    code = _IMPORT_THEN_CLASS.sub(r"\1\n", code)
    return _IMPORT_MODULE_THEN_CLASS.sub(r"\1\n", code)


def _is_stmt_start(text: str, index: int) -> bool:
    if text.startswith("self.", index):
        return True
    if _IDENT_ASSIGN.match(text, index):
        return True
    if _IDENT_DOT.match(text, index):
        return True
    return False


def _leading_ws(line: str) -> str:
    match = re.match(r"[ \t]*", line)
    return match.group(0) if match else ""


def _split_comment_then_stmt_line(line: str) -> list[str]:
    """Turn ``stmt # Comment next = ...`` into comment line + following stmt."""
    quote: str | None = None
    depth = 0
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if quote is not None:
            if quote in ('"""', "'''"):
                if line.startswith(quote, i):
                    i += len(quote)
                    quote = None
                    continue
                i += 1
                continue
            if ch == "\\" and i + 1 < n:
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if line.startswith(('"""', "'''"), i):
            quote = line[i : i + 3]
            i += 3
            continue
        if ch in ("'", '"'):
            quote = ch
            i += 1
            continue
        if ch in "([{":
            depth += 1
            i += 1
            continue
        if ch in ")]}" and depth:
            depth -= 1
            i += 1
            continue
        if ch == "#" and depth == 0:
            rest = line[i:]
            match = _COMMENT_THEN_STMT.match(rest)
            if not match:
                return [line]
            comment_len = match.end()
            prefix = line[:i].rstrip()
            comment = rest[:comment_len].rstrip()
            stmt = rest[comment_len:].lstrip()
            indent = _leading_ws(line)
            parts: list[str] = []
            if prefix:
                parts.append(prefix)
            parts.append(f"{indent}{comment}")
            if stmt:
                parts.append(f"{indent}{stmt}")
            return parts
        i += 1
    return [line]


def _split_comments_then_code(code: str) -> str:
    out: list[str] = []
    for line in code.split("\n"):
        out.extend(_split_comment_then_stmt_line(line))
    return "\n".join(out)


def _break_adjacent_statements_line(line: str) -> str:
    indent = _leading_ws(line)
    out: list[str] = []
    i = 0
    n = len(line)
    quote: str | None = None
    depth = 0
    while i < n:
        ch = line[i]
        if quote is not None:
            if quote in ('"""', "'''"):
                if line.startswith(quote, i):
                    out.append(quote)
                    i += len(quote)
                    quote = None
                    continue
                out.append(ch)
                i += 1
                continue
            if ch == "\\" and i + 1 < n:
                out.append(line[i : i + 2])
                i += 2
                continue
            out.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if line.startswith(('"""', "'''"), i):
            quote = line[i : i + 3]
            out.append(quote)
            i += 3
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch in "([{":
            depth += 1
            out.append(ch)
            i += 1
            continue
        if ch in ")]}" and depth:
            depth -= 1
            out.append(ch)
            i += 1
            if depth == 0:
                j = i
                while j < n and line[j] in " \t":
                    j += 1
                if j > i and _is_stmt_start(line, j):
                    out.append("\n" + indent)
                    i = j
                    continue
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _break_adjacent_statements(code: str) -> str:
    return "\n".join(_break_adjacent_statements_line(line) for line in code.split("\n"))


def _split_collapsed_class_def(code: str) -> str:
    def repl(match: re.Match[str]) -> str:
        indent, name, bases, rest = match.group(1, 2, 3, 4)
        return f"{indent}class {name}({bases}):\n{indent}    {rest.strip()}"

    code = _COLLAPSED_CLASS_DEF.sub(repl, code)
    fixed_lines: list[str] = []
    for line in code.split("\n"):
        m = _CONSTRUCT_COMMENT_THEN_CODE.match(line)
        if m:
            def_indent = re.match(r"[ \t]*", m.group(1))
            body_indent = (def_indent.group(0) if def_indent else "") + "    "
            fixed_lines.append(f"{m.group(1)} {m.group(2)}")
            fixed_lines.append(f"{body_indent}{m.group(3)}")
            continue
        fixed_lines.append(line)
    return "\n".join(fixed_lines)


def _indent_construct_body(code: str) -> str:
    lines = code.split("\n")
    out: list[str] = []
    in_construct = False
    construct_indent = 0

    def leading_spaces(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue

        indent = leading_spaces(line)
        is_class = re.match(r"class\s+\w+", stripped) is not None
        is_def = re.match(r"def\s+\w+", stripped) is not None

        if is_class and indent == 0:
            in_construct = False
            out.append(line)
            continue

        if in_construct and is_def and indent <= construct_indent:
            in_construct = False

        if is_def and re.match(r"def\s+construct\s*\(", stripped):
            in_construct = True
            construct_indent = indent
            out.append(line)
            continue

        if in_construct:
            min_body = construct_indent + 4
            if indent < min_body and not (is_class and indent == 0):
                out.append((" " * min_body) + stripped)
                continue

        out.append(line)

    return "\n".join(out)


def normalize_manim_source(code: str) -> str:
    """Repair common LLM formatting issues; leave already-valid source unchanged."""
    if not isinstance(code, str) or not code.strip():
        return code if isinstance(code, str) else ""
    original = code
    if _parses(original):
        return original

    candidate = original.replace("\r\n", "\n")
    steps = (
        _strip_markdown_fences,
        textwrap.dedent,
        _unescape_outside_strings,
        _split_import_then_class,
        _split_collapsed_class_def,
        _split_comments_then_code,
        _break_adjacent_statements,
        _indent_construct_body,
        textwrap.dedent,
    )
    for step in steps:
        nxt = step(candidate)
        if nxt != candidate:
            candidate = nxt
            if _parses(candidate):
                return candidate

    # Apply remaining transforms even if an earlier one did not change text.
    candidate = _strip_markdown_fences(original.replace("\r\n", "\n"))
    candidate = textwrap.dedent(candidate)
    if "\\n" in candidate or "\\t" in candidate:
        candidate = _unescape_outside_strings(candidate)
    candidate = _split_import_then_class(candidate)
    candidate = _split_collapsed_class_def(candidate)
    candidate = _split_comments_then_code(candidate)
    candidate = _break_adjacent_statements(candidate)
    candidate = _indent_construct_body(candidate)
    candidate = textwrap.dedent(candidate)
    if _parses(candidate):
        return candidate
    return candidate if candidate.strip() else original


@dataclass(frozen=True)
class ExtractedCodemode:
    code: str
    scene_name: str


def _first_class_name(code: str) -> str | None:
    match = _CLASS_NAME.search(code)
    return match.group(1) if match else None


def _looks_like_manim_module(code: str) -> bool:
    if not code or not _MANIM_IMPORT.search(code):
        return False
    if _SCENE_CLASS.search(code):
        return True
    return bool(_CLASS_NAME.search(code) and re.search(r"\bdef\s+construct\s*\(", code))


def _first_scene_class_name(code: str) -> str | None:
    match = _SCENE_CLASS.search(code)
    if match:
        return match.group(1)
    return _first_class_name(code)


def extract_codemode_dump(text: str) -> ExtractedCodemode | None:
    """Pull Manim source + scene_name from dumped CodeMode or raw Manim (no eval)."""
    if not isinstance(text, str) or not text.strip():
        return None
    raw = text.strip()
    body: str | None = None
    assign = _CODE_ASSIGN.search(raw)
    if assign:
        body = assign.group("body")
    else:
        inline = _INLINE_WRITE.search(raw)
        if inline:
            body = inline.group("body")
    if body is None:
        code = normalize_manim_source(raw)
        if not _looks_like_manim_module(code):
            return None
        scene_name = _first_scene_class_name(code)
        if not scene_name:
            return None
        return ExtractedCodemode(code=code, scene_name=scene_name)

    code = normalize_manim_source(body.strip("\n"))
    if not code.strip():
        return None
    scene_name: str | None = None
    for match in _SCENE_NAME.finditer(raw):
        scene_name = match.group("name")
    if not scene_name:
        scene_name = _first_scene_class_name(code)
    if not scene_name:
        return None
    return ExtractedCodemode(code=code, scene_name=scene_name)

def _base_id(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _has_set_speech_service(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if child.func.attr == "set_speech_service":
                return True
    return False


has_set_speech_service = _has_set_speech_service


def _has_voiceover_call(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name) and func.id == "voiceover":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "voiceover":
                return True
    return False


def _passes_voiceover_gate(code: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    classes = [
        n
        for n in tree.body
        if isinstance(n, ast.ClassDef)
        and any(_base_id(b) == "VoiceoverScene" for b in n.bases)
    ]
    if not classes:
        return False
    return any(
        _has_voiceover_call(cls) and _has_set_speech_service(cls) for cls in classes
    )


def _speech_service_stmt() -> ast.stmt:
    return ast.parse(
        'self.set_speech_service(AOSSpeechService(voice="alba", cache_dir="voiceover_cache"))'
    ).body[0]


def _insert_voiceover_imports(tree: ast.Module) -> None:
    lines = {ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))}
    to_add: list[ast.stmt] = []
    if _VOICEOVER_IMPORT not in lines and "VoiceoverScene" not in "\n".join(lines):
        to_add.append(ast.parse(_VOICEOVER_IMPORT).body[0])
    if "aos_speech_service" not in "\n".join(lines):
        to_add.append(ast.parse(_SPEECH_IMPORT).body[0])
    if not to_add:
        return
    insert_at = 0
    for i, node in enumerate(tree.body):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            insert_at = i + 1
        elif insert_at:
            break
    tree.body[insert_at:insert_at] = to_add


def _upgrade_scene_bases(tree: ast.Module) -> None:
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if any(_base_id(b) == "VoiceoverScene" for b in node.bases):
            continue
        if any(_base_id(b) == "ThreeDScene" for b in node.bases):
            continue
        node.bases = [
            ast.Name(id="VoiceoverScene", ctx=ast.Load())
            if _base_id(b) == "Scene"
            else b
            for b in node.bases
        ]
        if not node.bases:
            node.bases = [ast.Name(id="VoiceoverScene", ctx=ast.Load())]


def _ensure_construct_speech(tree: ast.Module) -> None:
    for cls in tree.body:
        if not isinstance(cls, ast.ClassDef):
            continue
        if not any(_base_id(b) == "VoiceoverScene" for b in cls.bases):
            continue
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef) or item.name != "construct":
                continue
            if not _has_set_speech_service(item):
                item.body.insert(0, _speech_service_stmt())


def ensure_voiceover_scene(code: str) -> str:
    """Upgrade plain Scene dumps to VoiceoverScene + AOSSpeechService.

    Does not invent voiceover text. Silent plays stay silent so compile can
    refuse missing or filler narration.
    """
    if not isinstance(code, str) or not code.strip():
        return code if isinstance(code, str) else ""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    if _passes_voiceover_gate(code):
        return code

    _insert_voiceover_imports(tree)
    _upgrade_scene_bases(tree)
    _ensure_construct_speech(tree)
    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree) + "\n"
    except Exception:
        return code


def prepare_manim_source(code: str) -> str:
    """Normalize LLM source then ensure VoiceoverScene + speech service."""
    return ensure_voiceover_scene(normalize_manim_source(code))
