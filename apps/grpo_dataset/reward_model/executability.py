from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExecutabilityResult:
    passed: bool
    parse_error: str | None = None
    runtime_error: str | None = None


def check_executability(code_path: Path, timeout_seconds: int = 60) -> ExecutabilityResult:
    source = code_path.read_text(encoding="utf-8")
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return ExecutabilityResult(passed=False, parse_error=str(exc))

    command = [sys.executable, str(code_path)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds)
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or "unknown runtime error"
        return ExecutabilityResult(passed=False, runtime_error=err)

    return ExecutabilityResult(passed=True)
