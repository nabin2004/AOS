"""Robust Language Server Protocol (LSP) client: AST indexing, symbol lookup, syntax feedback, and optional `ty check`."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable

IGNORE_DIRS = {".venv", "__pycache__", ".git", ".aos", ".pytest_cache", ".decode", "node_modules", "dist", "build"}


@dataclass(slots=True)
class SymbolInformation:
    name: str
    kind: str
    file_path: Path
    line_number: int
    signature: str = ""
    docstring: str = ""


class TyClient:
    """AST-backed LSP client for fast diagnostics, symbol indexing, and definition lookup."""

    def __init__(self, cwd: Path, ty_bin: str = "ty") -> None:
        self.cwd = cwd.resolve()
        self.ty_bin = ty_bin

    def syntax_check(self, path: Path) -> str:
        """Parse a Python file with ast.parse and return precise error location."""
        if not path.is_file():
            return f"not a file: {path}"
        try:
            source = path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"cannot read file {path.name}: {exc}"

        try:
            ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            rel = path.relative_to(self.cwd) if path.is_relative_to(self.cwd) else path.name
            line_str = f" line {exc.lineno}" if exc.lineno else ""
            col_str = f":{exc.offset}" if exc.offset else ""
            text_snippet = f"\n  Code: {exc.text.strip()}" if exc.text else ""
            return f"syntax error in {rel}{line_str}{col_str}: {exc.msg}{text_snippet}"
        return "syntax ok"

    def ty_available(self) -> bool:
        """Check if `ty` type checker binary is installed in PATH."""
        return shutil.which(self.ty_bin) is not None

    def diagnostics(self, path: Path, *, runner: Callable[[list[str]], Any] | None = None) -> str:
        """Run AST syntax check followed by `ty check` (if available)."""
        syntax = self.syntax_check(path)
        if syntax != "syntax ok":
            return syntax

        if runner is None and not self.ty_available():
            return "syntax ok (ty not installed)"

        try:
            if runner is not None:
                proc = runner([self.ty_bin, "check", str(path)])
            else:
                proc = subprocess.run(
                    [self.ty_bin, "check", str(path)],
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                )
        except FileNotFoundError:
            return "syntax ok (ty not installed)"
        except subprocess.TimeoutExpired:
            return "syntax ok (ty check timed out)"

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        body = "\n".join(part for part in (out, err) if part)
        if proc.returncode == 0:
            return body or "ty check ok"
        return body or f"ty check failed (exit {proc.returncode})"

    def after_write(self, path: Path, *, runner: Callable[[list[str]], Any] | None = None) -> str:
        """Post-write hook that runs diagnostics on Python files."""
        if path.suffix != ".py":
            return ""
        return self.diagnostics(path, runner=runner)

    def _python_files(self, root: Path | None = None) -> list[Path]:
        target = (root or self.cwd).resolve()
        if target.is_file() and target.suffix == ".py":
            return [target]

        py_files: list[Path] = []
        if not target.is_dir():
            return py_files

        for item in target.rglob("*.py"):
            if any(part in IGNORE_DIRS for part in item.parts):
                continue
            py_files.append(item)
        return py_files

    def find_definition(self, symbol: str, target_path: Path | None = None) -> str:
        """Locate definition of a class, function, method, or assignment across python files."""
        symbols = self.search_symbols(query=symbol, target_path=target_path, exact_name=True)
        if not symbols:
            return f"Symbol '{symbol}' not found."

        results = []
        for sym in symbols:
            rel_file = sym.file_path.relative_to(self.cwd) if sym.file_path.is_relative_to(self.cwd) else sym.file_path
            doc_info = f"\n  Docstring: {sym.docstring}" if sym.docstring else ""
            sig_info = f"\n  Signature: {sym.signature}" if sym.signature else ""
            results.append(
                f"Found '{sym.name}' [{sym.kind}] in {rel_file}:{sym.line_number}{sig_info}{doc_info}"
            )
        return "\n\n".join(results)

    def file_symbols(self, path: Path) -> str:
        """List all top-level classes, functions, and methods defined in a single file."""
        if not path.is_file():
            return f"not a file: {path}"
        symbols = self._extract_symbols_from_file(path)
        if not symbols:
            return f"No symbols found in {path.name}."

        rel_file = path.relative_to(self.cwd) if path.is_relative_to(self.cwd) else path.name
        lines = [f"Symbols in {rel_file}:"]
        for sym in symbols:
            sig = f" -> {sym.signature}" if sym.signature else ""
            lines.append(f"  - [{sym.kind}] {sym.name} (line {sym.line_number}){sig}")
        return "\n".join(lines)

    def workspace_symbols(self, query: str = "") -> str:
        """Search workspace Python files for top-level classes and functions matching a query string."""
        symbols = self.search_symbols(query=query, exact_name=False)
        if not symbols:
            q_str = f" matching '{query}'" if query else ""
            return f"No workspace symbols found{q_str}."

        lines = [f"Workspace Symbols ({len(symbols)} found):"]
        for sym in symbols[:50]:  # Limit to 50 results
            rel_file = sym.file_path.relative_to(self.cwd) if sym.file_path.is_relative_to(self.cwd) else sym.file_path
            lines.append(f"  - [{sym.kind}] {sym.name} ({rel_file}:{sym.line_number})")
        if len(symbols) > 50:
            lines.append(f"  ... ({len(symbols) - 50} more symbols truncated)")
        return "\n".join(lines)

    def search_symbols(
        self,
        query: str = "",
        target_path: Path | None = None,
        exact_name: bool = False,
    ) -> list[SymbolInformation]:
        """Core AST search algorithm for symbol indexing."""
        files = self._python_files(target_path)
        results: list[SymbolInformation] = []
        query_lower = query.lower()

        for file in files:
            file_symbols = self._extract_symbols_from_file(file)
            for sym in file_symbols:
                if exact_name:
                    if sym.name == query:
                        results.append(sym)
                else:
                    if not query or query_lower in sym.name.lower():
                        results.append(sym)
        return results

    def _extract_symbols_from_file(self, path: Path) -> list[SymbolInformation]:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except Exception:
            return []

        symbols: list[SymbolInformation] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "AsyncFunction" if isinstance(node, ast.AsyncFunctionDef) else "Function"
                sig = self._format_func_signature(node)
                doc = ast.get_docstring(node) or ""
                symbols.append(
                    SymbolInformation(
                        name=node.name,
                        kind=kind,
                        file_path=path,
                        line_number=node.lineno,
                        signature=sig,
                        docstring=doc.split("\n")[0] if doc else "",
                    )
                )
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                bases = [ast.unparse(b) for b in node.bases]
                base_str = f"({', '.join(bases)})" if bases else ""
                symbols.append(
                    SymbolInformation(
                        name=node.name,
                        kind="Class",
                        file_path=path,
                        line_number=node.lineno,
                        signature=f"class {node.name}{base_str}",
                        docstring=doc.split("\n")[0] if doc else "",
                    )
                )
        return symbols

    def _format_func_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
        try:
            args_str = ast.unparse(node.args)
            returns_str = f" -> {ast.unparse(node.returns)}" if node.returns else ""
            return f"{prefix}{node.name}({args_str}){returns_str}"
        except Exception:
            return f"{prefix}{node.name}(...)"


# Alias for backward compatibility
LspClient = TyClient
