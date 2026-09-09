"""Normalize LLM Manim source and salvage dumped CodeMode text."""

from __future__ import annotations

import ast
import json as _json
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
_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(?P<payload>\{.*?\})\s*</tool_call>",
    re.DOTALL,
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
        compile(code, "<string>", "exec")
        tree = ast.parse(code)
        for node in tree.body:
            if isinstance(node, (ast.Expr, ast.Assign)) and any(
                isinstance(child, ast.Await) for child in ast.walk(node)
            ):
                return False
        return True
    except (SyntaxError, Exception):
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


_TOOL_CALL_PREFIXES = (
    "await manim_write",
    "await compile_manim_code",
    "await manim_read",
    "await synthesize_narration",
    "await run_code",
    "manim_write(",
    "compile_manim_code(",
    "run_code(",
)


def _strip_toplevel_tool_calls(code: str) -> str:
    """Strip orchestrator tool calls (e.g. await manim_write(...)) mistakenly placed at top level."""
    lines = code.split("\n")
    cleaned: list[str] = []
    skipping_call = False
    paren_depth = 0
    for line in lines:
        stripped = line.strip()
        if not skipping_call:
            if stripped.startswith("await ") or any(stripped.startswith(p) for p in _TOOL_CALL_PREFIXES):
                paren_depth = stripped.count("(") - stripped.count(")")
                if paren_depth > 0:
                    skipping_call = True
                continue
            cleaned.append(line)
        else:
            paren_depth += stripped.count("(") - stripped.count(")")
            if paren_depth <= 0:
                skipping_call = False
            continue
    return "\n".join(cleaned)


def _strip_toplevel_awaits_ast(code: str) -> str:
    """AST-level safety net: strip any top-level Expr/Assign nodes containing an Await or tool call."""
    try:
        tree = ast.parse(code)
    except Exception:
        return code
    new_body = []
    changed = False
    for node in tree.body:
        if isinstance(node, ast.Expr) and (
            isinstance(node.value, ast.Await)
            or any(isinstance(child, ast.Await) for child in ast.walk(node))
        ):
            changed = True
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            func = node.value.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
            if name in ("manim_write", "compile_manim_code", "run_code", "manim_read", "synthesize_narration"):
                changed = True
                continue
        new_body.append(node)
    if changed:
        tree.body = new_body
        try:
            return ast.unparse(tree) + "\n"
        except Exception:
            return code
    return code


def normalize_manim_source(code: str) -> str:
    """Repair common LLM formatting issues; leave already-valid source unchanged."""
    if not isinstance(code, str) or not code.strip():
        return code if isinstance(code, str) else ""
    original = code
    if _parses(original):
        return original

    candidate = original.replace("\r\n", "\n")
    candidate = _strip_toplevel_tool_calls(candidate)
    if _parses(candidate):
        return candidate

    steps = (
        _strip_markdown_fences,
        textwrap.dedent,
        _unescape_outside_strings,
        _split_import_then_class,
        _split_collapsed_class_def,
        _split_comments_then_code,
        _break_adjacent_statements,
        _indent_construct_body,
        _strip_toplevel_tool_calls,
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
    candidate = _strip_toplevel_tool_calls(candidate)
    candidate = textwrap.dedent(candidate)
    if "\\n" in candidate or "\\t" in candidate:
        candidate = _unescape_outside_strings(candidate)
    candidate = _split_import_then_class(candidate)
    candidate = _split_collapsed_class_def(candidate)
    candidate = _split_comments_then_code(candidate)
    candidate = _break_adjacent_statements(candidate)
    candidate = _indent_construct_body(candidate)
    candidate = _strip_toplevel_tool_calls(candidate)
    candidate = textwrap.dedent(candidate)
    if _parses(candidate):
        return candidate

    # AST-level safety net
    ast_cleaned = _strip_toplevel_awaits_ast(candidate)
    if _parses(ast_cleaned):
        return ast_cleaned

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


def _extract_from_tool_call(text: str) -> ExtractedCodemode | None:
    """Parse `<tool_call>{"name":"manim_write","arguments":{...}}</tool_call>` dumps."""
    for match in _TOOL_CALL_RE.finditer(text):
        payload = match.group("payload")
        # LLMs often incorrectly emit \' inside JSON strings.
        payload = payload.replace(r"\'", "'")
        try:
            obj = _json.loads(payload)
        except (_json.JSONDecodeError, ValueError):
            continue
        name = obj.get("name", "")
        if name not in ("manim_write", "compile_manim_code"):
            continue
        args = obj.get("arguments") or {}
        raw_code = args.get("code", "")
        if not raw_code or not isinstance(raw_code, str):
            continue
        code = normalize_manim_source(raw_code)
        if not _looks_like_manim_module(code):
            continue
        scene_name = args.get("scene_name") or _first_scene_class_name(code)
        if not scene_name:
            continue
        return ExtractedCodemode(code=code, scene_name=scene_name)
    return None


def extract_codemode_dump(text: str) -> ExtractedCodemode | None:
    """Pull Manim source + scene_name from dumped CodeMode or raw Manim (no eval)."""
    if not isinstance(text, str) or not text.strip():
        return None
    raw = text.strip()

    # Try <tool_call> JSON format first (SFT models may emit these as text).
    tc = _extract_from_tool_call(raw)
    if tc is not None:
        return tc
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
    import_lines = {ast.unparse(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))}
    has_vo_import = any("VoiceoverScene" in l for l in import_lines)
    has_sp_import = any("AOSSpeechService" in l or "aos_speech_service" in l for l in import_lines)
    if not (has_vo_import and has_sp_import):
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


def sanitize_manim_animations(code: str) -> str:
    """Strip invalid arguments (e.g. lists, tuples, raw coordinates) from FadeOut/FadeIn/Create/Write."""
    if not isinstance(code, str) or not code.strip():
        return code if isinstance(code, str) else ""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    # 1. Collect names of variables assigned to non-mobject literals/data structures
    non_mobjects: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            val = node.value
            is_non_mob = False
            if isinstance(val, (ast.List, ast.Tuple, ast.Dict, ast.Set, ast.Constant)):
                is_non_mob = True
            elif isinstance(val, ast.Call):
                cname = getattr(val.func, "id", "") or getattr(val.func, "attr", "")
                if cname in ("array", "zeros", "arange", "linspace", "zeros_like", "ones"):
                    is_non_mob = True
            if is_non_mob:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        non_mobjects.add(target.id)

    # 2. NodeTransformer to clean up animation calls
    class AnimationSanitizer(ast.NodeTransformer):
        def visit_Call(self, node: ast.Call) -> ast.AST:
            self.generic_visit(node)
            cname = getattr(node.func, "id", "") or getattr(node.func, "attr", "")
            if cname in ("FadeOut", "FadeIn", "Create", "Uncreate", "Transform"):
                new_args: list[ast.expr] = []
                for arg in node.args:
                    if isinstance(arg, ast.Call):
                        called = getattr(arg.func, "id", "") or getattr(arg.func, "attr", "")
                        if called in ("Scene", "VoiceoverScene", "ThreeDScene", "VoiceoverSlideScene"):
                            continue
                    if isinstance(arg, ast.Name) and (arg.id in non_mobjects or arg.id in ("Scene", "VoiceoverScene", "ThreeDScene", "self")):
                        continue  # drop non-mobject variable (e.g. coordinate list, Scene class)
                    if isinstance(arg, (ast.List, ast.Tuple, ast.Constant)):
                        continue  # drop literal list/tuple/number
                    new_args.append(arg)
                node.args = new_args
            return node

        def visit_Expr(self, node: ast.Expr) -> ast.AST | None:
            self.generic_visit(node)
            if isinstance(node.value, ast.Call):
                cname = getattr(node.value.func, "id", "") or getattr(node.value.func, "attr", "")
                if cname == "play":
                    valid_play_args: list[ast.expr] = []
                    for arg in node.value.args:
                        if isinstance(arg, ast.Call):
                            aname = getattr(arg.func, "id", "") or getattr(arg.func, "attr", "")
                            if aname in ("FadeOut", "FadeIn", "Create", "Uncreate") and not arg.args:
                                continue  # drop empty animation calls like FadeOut()
                        valid_play_args.append(arg)
                    if not valid_play_args:
                        return None  # remove empty self.play() completely
                    node.value.args = valid_play_args
            return node

    sanitizer = AnimationSanitizer()
    tree = sanitizer.visit(tree)
    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree) + "\n"
    except Exception:
        return code


def enrich_existing_voiceovers(code: str, teaching_beats: list[str] | None = None) -> str:
    """Enrich short or truncated voiceover lines with full pedagogical teaching script narration, and enforce calm pauses."""
    if not isinstance(code, str) or not code.strip():
        return code if isinstance(code, str) else ""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    beat_idx = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                ctx = item.context_expr
                if isinstance(ctx, ast.Call):
                    cname = getattr(ctx.func, "id", "") or getattr(ctx.func, "attr", "")
                    if cname == "voiceover":
                        curr_text = ""
                        text_kw = None
                        for kw in ctx.keywords:
                            if kw.arg == "text" and isinstance(kw.value, ast.Constant):
                                curr_text = str(kw.value.value)
                                text_kw = kw
                                break
                        if not text_kw and ctx.args and isinstance(ctx.args[0], ast.Constant):
                            curr_text = str(ctx.args[0].value)

                        if teaching_beats and beat_idx < len(teaching_beats):
                            target_narration = teaching_beats[beat_idx]
                            # Replace if current text is short (< 15 words) or generic
                            if len(curr_text.split()) < 15 or len(curr_text) < 80:
                                if text_kw:
                                    text_kw.value = ast.Constant(value=target_narration)
                                elif ctx.args:
                                    ctx.args[0] = ast.Constant(value=target_narration)
                        beat_idx += 1

                        # Ensure calm pause at the end of each beat
                        has_wait = False
                        if node.body:
                            last_stmt = node.body[-1]
                            if isinstance(last_stmt, ast.Expr) and isinstance(last_stmt.value, ast.Call):
                                fname = getattr(last_stmt.value.func, "id", "") or getattr(last_stmt.value.func, "attr", "")
                                if fname == "wait":
                                    has_wait = True
                                    if last_stmt.value.args and isinstance(last_stmt.value.args[0], ast.Constant):
                                        if isinstance(last_stmt.value.args[0].value, (int, float)) and last_stmt.value.args[0].value < 1.5:
                                            last_stmt.value.args[0] = ast.Constant(value=2.0)
                        if not has_wait:
                            node.body.append(
                                ast.Expr(
                                    value=ast.Call(
                                        func=ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr="wait", ctx=ast.Load()),
                                        args=[ast.Constant(value=2.0)],
                                        keywords=[],
                                    )
                                )
                            )

    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree) + "\n"
    except Exception:
        return code


def prepare_manim_source(code: str, teaching_beats: list[str] | None = None) -> str:
    """Normalize LLM source, sanitize animation calls, ensure VoiceoverScene, and enrich voiceovers."""
    code = normalize_manim_source(code)
    # Define common missing color constants or imports that LLMs frequently use (e.g. CYAN)
    color_header = ""
    if "CYAN" in code and not re.search(r"^\s*CYAN\s*=", code, re.MULTILINE):
        color_header += 'CYAN = "#00FFFF"\n'
    if "MAGENTA" in code and not re.search(r"^\s*MAGENTA\s*=", code, re.MULTILINE):
        color_header += 'MAGENTA = "#FF00FF"\n'
    if color_header:
        code = color_header + code
    code = sanitize_manim_animations(code)
    code = ensure_voiceover_scene(code)
    if teaching_beats:
        code = enrich_existing_voiceovers(code, teaching_beats)
    return code


def _math_to_speech(tex: str, topic: str = "") -> str:
    """Convert a math formula or LaTeX string into natural spoken English for voiceover."""
    t = tex.strip()
    # Specific pedagogical translations for core mathematical expressions
    if "e^{i" in t or "e^{ix" in t or "e^{i\\theta" in t:
        if "cos" in t and "sin" in t:
            return "Euler's formula connects the complex exponential e to the i theta directly to cosine theta plus i sine theta."
        if "\\pi" in t and ("-1" in t or "= 0" in t or "+ 1" in t):
            return "Evaluating at pi yields Euler's identity: e to the i pi plus one equals zero."
        return "The complex exponential e to the i theta describes rotation along the unit circle."
    if "\\text{Re}" in t or "Re(" in t:
        return "The horizontal axis represents the real component of the complex number."
    if "\\text{Im}" in t or "Im(" in t:
        return "The vertical axis represents the imaginary component of the complex number."
    if "|z| = 1" in t or "|z|=1" in t:
        return "On the unit circle, every point has distance one from the origin."
    if "\\frac{\\pi}{2}" in t:
        return "An angle of pi over two represents a ninety degree rotation counterclockwise."
    if "\\frac{dx}{dt}" in t or "sigma(y" in t or "\\sigma(y" in t:
        return "The rate of change of x is proportional to the difference between y and x, governed by the Prandtl number sigma."
    if "\\frac{dy}{dt}" in t or "(\\rho - z)" in t or "(rho - z)" in t:
        return "The rate of change of y incorporates convection driven by rho, tempered by the nonlinear term x times z."
    if "\\frac{dz}{dt}" in t or "xy - \\beta" in t or "xy - beta" in t:
        return "The vertical temperature distortion z grows with x times y and decays proportionally to beta times z."
    if "\\vec{v}" in t:
        return "We track the instantaneous phase space state vector as it moves through the vector field."

    replacements = [
        (r"\\cos", " cosine "),
        (r"\\sin", " sine "),
        (r"\\tan", " tangent "),
        (r"\\pi", " pi "),
        (r"\\theta", " theta "),
        (r"\\alpha", " alpha "),
        (r"\\beta", " beta "),
        (r"\\times", " times "),
        (r"\\cdot", " dot "),
        (r"\\approx", " approximately equals "),
        (r"\\rightarrow", " approaches "),
        (r"\\int", " the integral of "),
        (r"\\sum", " the sum of "),
        (r"\\infty", " infinity "),
        (r"\^", " to the "),
        (r"=", " equals "),
        (r"\+", " plus "),
        (r"-", " minus "),
        (r"/", " over "),
    ]
    for pattern, repl in replacements:
        t = re.sub(pattern, repl, t)
    t = re.sub(r"\\[a-zA-Z]+", " ", t)
    t = re.sub(r"[{}\\$]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) < 4:
        return f"Observe how this foundational property governs {topic}." if topic else "Observe how this foundational property governs the system."
    return f"We examine the relationship where {t}, revealing the underlying mathematical structure."


def _extract_text_constant(node: ast.AST) -> str | None:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            val = child.value.strip()
            if len(val) >= 3 and not val.startswith(("#", "\\begin", "\\end")):
                return val
    return None


def auto_wrap_missing_voiceovers(
    code: str,
    topic: str = "this concept",
    teaching_beats: list[str] | None = None,
) -> str:
    """Wrap bare self.play(...) calls in VoiceoverScene with with self.voiceover(text=...): blocks."""
    if not isinstance(code, str) or not code.strip():
        return code if isinstance(code, str) else ""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    voiceover_classes = [
        n
        for n in tree.body
        if isinstance(n, ast.ClassDef)
        and any(_base_id(b) in ("VoiceoverScene", "VoiceoverSlideScene") for b in n.bases)
    ]
    if not voiceover_classes:
        return code
    if any(_has_voiceover_call(cls) for cls in voiceover_classes):
        return code

    clean_topic = re.sub(r"[^A-Za-z0-9 ]", "", topic).strip() or "this mathematical concept"

    for cls in voiceover_classes:
        construct_fn = None
        for item in cls.body:
            if isinstance(item, ast.FunctionDef) and item.name == "construct":
                construct_fn = item
                break
        if not construct_fn:
            continue

        var_text: dict[str, str] = {}
        for stmt in construct_fn.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        txt = _extract_text_constant(stmt.value)
                        if txt:
                            var_text[target.id] = txt

        new_body: list[ast.stmt] = []
        beat_idx = 0
        default_pedagogy = [
            f"In this lesson, we explore the foundations and visual intuition of {clean_topic}.",
            f"We first establish the coordinate framework to visualize how {clean_topic} behaves.",
            f"Notice how the visual components interact to illustrate this central concept.",
            f"Examining this step closely provides clear geometric and algebraic intuition.",
            f"This relationship unifies the individual parts into a single cohesive framework.",
            f"This completes our visual exploration, demonstrating the deep mathematical harmony of {clean_topic}.",
        ]

        for stmt in construct_fn.body:
            is_play = False
            is_fade_out = False
            play_text = None
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                func = stmt.value.func
                if isinstance(func, ast.Attribute) and func.attr == "play":
                    is_play = True
                    for arg in stmt.value.args:
                        if isinstance(arg, ast.Call):
                            cname = getattr(arg.func, "id", "") or getattr(arg.func, "attr", "")
                            if cname in ("FadeOut", "Uncreate", "ShrinkToCenter"):
                                is_fade_out = True
                        for sub in ast.walk(arg):
                            if isinstance(sub, ast.Name) and sub.id in var_text:
                                play_text = var_text[sub.id]
                                break
                            elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                                if len(sub.value.strip()) >= 4:
                                    play_text = sub.value.strip()
                                    break
                        if play_text:
                            break

            if is_play and is_fade_out and beat_idx > 0:
                new_body.append(stmt)
                continue

            if is_play:
                if teaching_beats and beat_idx < len(teaching_beats):
                    narration = teaching_beats[beat_idx]
                elif play_text:
                    if any(sym in play_text for sym in ("\\", "=", "+", "^", "_")):
                        narration = _math_to_speech(play_text, clean_topic)
                    else:
                        clean_extracted = re.sub(r"[^A-Za-z0-9 ,.'-]", "", play_text).strip()
                        if clean_extracted and len(clean_extracted) >= 4:
                            if any(k in clean_extracted.lower() for k in ("euler", "formula", "identity", "equation")):
                                narration = f"We introduce {clean_extracted}, connecting core mathematical principles."
                            elif any(k in clean_extracted.lower() for k in ("complex", "trigonometry", "circle")):
                                narration = f"This visual highlights the bridge between {clean_extracted} and geometry."
                            else:
                                narration = f"Consider {clean_extracted}, observing how it clarifies the underlying relationship."
                        else:
                            narration = default_pedagogy[min(beat_idx, len(default_pedagogy) - 1)]
                else:
                    narration = default_pedagogy[min(beat_idx, len(default_pedagogy) - 1)]
                beat_idx += 1

                if narration.lower().startswith("here we have"):
                    narration = "Notice " + narration[12:]
                elif narration.lower().startswith("let's look at this on the board"):
                    narration = f"Now we examine the structure of {clean_topic}."

                with_stmt = ast.With(
                    items=[
                        ast.withitem(
                            context_expr=ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id="self", ctx=ast.Load()),
                                    attr="voiceover",
                                    ctx=ast.Load(),
                                ),
                                args=[],
                                keywords=[
                                    ast.keyword(
                                        arg="text",
                                        value=ast.Constant(value=narration),
                                    )
                                ],
                            ),
                            optional_vars=ast.Name(id="tracker", ctx=ast.Store()),
                        )
                    ],
                    body=[stmt],
                )
                new_body.append(with_stmt)
            else:
                new_body.append(stmt)

        construct_fn.body = new_body

    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree) + "\n"
    except Exception:
        return code
