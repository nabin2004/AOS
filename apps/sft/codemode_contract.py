"""Local copy of CodeMode star-import checks for SFT load/filter (no agents import)."""

from __future__ import annotations

import json
import re
from typing import Any

_STAR_IMPORT_LINE_RE = re.compile(r"^\s*from\s+manim\s+import\s+\*")
_NESTED_RUN_CODE_RE = re.compile(r"\bawait\s+run_code\s*\(|\brun_code\s*\(")


def run_code_has_star_import(code: str) -> bool:
    """True when ``from manim import *`` appears outside a triple-quoted string."""
    if not code or not isinstance(code, str):
        return False
    in_triple: str | None = None
    for line in code.splitlines():
        if in_triple is not None:
            if in_triple in line:
                in_triple = None
            continue

        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        for quote in ("'''", '"""'):
            if quote not in line:
                continue
            first = line.find(quote)
            rest = line[first + len(quote) :]
            if quote not in rest:
                in_triple = quote
            break

        if in_triple is None and _STAR_IMPORT_LINE_RE.match(line):
            return True
    return False


def run_code_has_nested_run_code(code: str) -> bool:
    """True when run_code is invoked inside another run_code body."""
    if not code or not isinstance(code, str):
        return False
    return bool(_NESTED_RUN_CODE_RE.search(code))


def run_code_has_multiline_single_quoted_string(code: str) -> bool:
    """True when a single- or double-quoted string literal spans a newline."""
    if not code or not isinstance(code, str):
        return False

    i = 0
    n = len(code)
    while i < n:
        if code.startswith("'''", i) or code.startswith('"""', i):
            quote = code[i : i + 3]
            i += 3
            while i < n:
                if code.startswith(quote, i):
                    i += 3
                    break
                i += 1
            continue

        if code[i] not in "\"'":
            i += 1
            continue

        quote = code[i]
        i += 1
        has_newline = False
        while i < n:
            ch = code[i]
            if ch == "\\":
                i += 2
                continue
            if ch == "\n":
                has_newline = True
            if ch == quote:
                if has_newline:
                    return True
                i += 1
                break
            i += 1
        continue

    return False


def codemode_violations(code: str) -> list[str]:
    """Return violation codes for a run_code body."""
    violations: list[str] = []
    if run_code_has_star_import(code):
        violations.append("codemode_star_import")
    if run_code_has_nested_run_code(code):
        violations.append("codemode_nested_run_code")
    if run_code_has_multiline_single_quoted_string(code):
        violations.append("codemode_multiline_single_quote")
    return violations


def extract_run_code_body(arguments: Any) -> str | None:
    """Pull CodeMode source from OpenAI-style tool-call arguments."""
    if arguments is None:
        return None
    if isinstance(arguments, str):
        raw = arguments.strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        return extract_run_code_body(parsed)
    if not isinstance(arguments, dict):
        return None
    if isinstance(arguments.get("code"), str):
        return arguments["code"]
    inner = arguments.get("input")
    if isinstance(inner, str):
        try:
            nested = json.loads(inner)
        except json.JSONDecodeError:
            return inner
        if isinstance(nested, dict) and isinstance(nested.get("code"), str):
            return nested["code"]
        return inner
    if isinstance(inner, dict) and isinstance(inner.get("code"), str):
        return inner["code"]
    return None


def messages_violate_codemode(messages: list[dict[str, Any]] | None) -> bool:
    """True if any assistant run_code call violates the CodeMode contract."""
    return bool(codemode_message_violations(messages))


def codemode_message_violations(messages: list[dict[str, Any]] | None) -> list[str]:
    """Return all CodeMode violation codes found in assistant run_code calls."""
    if not isinstance(messages, list):
        return []
    violations: list[str] = []
    for msg in messages:
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        for tc in msg.get("tool_calls") or []:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function") or {}
            if not isinstance(fn, dict) or fn.get("name") != "run_code":
                continue
            body = extract_run_code_body(fn.get("arguments"))
            if body is None:
                continue
            for code in codemode_violations(body):
                if code not in violations:
                    violations.append(code)
    return violations
