from __future__ import annotations

import ast

from .contracts import CompileError, FailureCategory, FinalCode


def validate_generated_code(final_code: FinalCode) -> list[CompileError]:
    try:
        tree = ast.parse(final_code.code)
    except SyntaxError as exc:
        return [CompileError(category=FailureCategory.SYNTAX_ERROR, message=exc.msg, line=exc.lineno)]

    parents = {
        child: node
        for node in ast.walk(tree)
        for child in ast.iter_child_nodes(node)
    }

    errors: list[CompileError] = []
    imported_names = {
        alias.asname or alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_names.update(
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function_name = _call_name(node.func)
        if function_name == "Background" and _is_self_play_argument(node, parents):
            errors.append(_error(node, FailureCategory.HALLUCINATED_KWARGS, "Background is not a Manim animation"))
        if function_name == "Voiceover" and _is_self_play_argument(node, parents):
            errors.append(_error(node, FailureCategory.HALLUCINATED_KWARGS, "use self.voiceover(...) as a context manager"))
        if function_name == "ParametricFunction" and any(keyword.arg == "points" for keyword in node.keywords):
            errors.append(_error(node, FailureCategory.MALFORMED_POINT_ARRAYS, "ParametricFunction expects a function of t, not a points argument"))

    # Ensure voiceover is not called as a standalone bare statement
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            if _call_name(node.value.func) == "voiceover":
                errors.append(
                    _error(
                        node,
                        FailureCategory.HALLUCINATED_KWARGS,
                        "self.voiceover(...) must be used as a context manager ('with self.voiceover(...):')",
                    )
                )

    # Validate bookmark synchronization
    bookmarks, waited_bookmarks = _find_bookmarks_and_waits(tree)
    undefined_bookmarks = waited_bookmarks - bookmarks
    if undefined_bookmarks:
        errors.append(
            CompileError(
                category=FailureCategory.HALLUCINATED_KWARGS,
                message=f"wait_until_bookmark called for undefined bookmark(s): {', '.join(sorted(undefined_bookmarks))}",
            )
        )

    if _uses_voiceover(tree) and "VoiceoverScene" not in imported_names:
        errors.append(CompileError(category=FailureCategory.MISSING_IMPORTS, message="VoiceoverScene is used but not imported from manim_voiceover"))
    return errors


def _find_bookmarks_and_waits(tree: ast.AST) -> tuple[set[str], set[str]]:
    import re

    bookmarks: set[str] = set()
    waited_bookmarks: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            matches = re.findall(r"<bookmark\s+mark=['\"]([^'\"]+)['\"]\s*/>", node.value)
            bookmarks.update(matches)
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name == "wait_until_bookmark" and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    waited_bookmarks.add(first_arg.value)

    return bookmarks, waited_bookmarks



def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_self_play_argument(node: ast.Call, parents: dict[ast.AST, ast.AST]) -> bool:
    parent = parents.get(node)
    return isinstance(parent, ast.Call) and _call_name(parent.func) == "play"


def _uses_voiceover(tree: ast.AST) -> bool:
    return any(isinstance(node, ast.Attribute) and node.attr == "voiceover" for node in ast.walk(tree))


def _error(node: ast.AST, category: FailureCategory, message: str) -> CompileError:
    return CompileError(category=category, message=message, line=getattr(node, "lineno", None))