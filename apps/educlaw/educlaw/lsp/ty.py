"""Cheap post-edit feedback: ast.parse plus optional `ty check`."""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path


class TyClient:
    def __init__(self, cwd: Path, ty_bin: str = "ty") -> None:
        self.cwd = cwd.resolve()
        self.ty_bin = ty_bin

    def syntax_check(self, path: Path) -> str:
        source = path.read_text(encoding="utf-8")
        try:
            ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            loc = f"{exc.filename}:{exc.lineno}:{exc.offset}"
            return f"syntax error at {loc}: {exc.msg}"
        return "syntax ok"

    def ty_available(self) -> bool:
        return shutil.which(self.ty_bin) is not None

    def diagnostics(self, path: Path, *, runner=None) -> str:
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

    def after_write(self, path: Path, *, runner=None) -> str:
        if path.suffix != ".py":
            return ""
        return self.diagnostics(path, runner=runner)
