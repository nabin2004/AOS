"""LaTeX Static Validator for Manim Source Code.

Extracts all MathTex and Tex strings via AST and runs a fast dry-run compilation
on each to gather ALL LaTeX errors in a single pass, preventing token-blowup
from single-error fast-fails.
"""

from __future__ import annotations

import ast
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LatexDiagnostic:
    line: int
    column: int
    message: str
    tex_string: str


def run_latex_diagnostics(code: str, timeout: float = 10.0) -> list[LatexDiagnostic]:
    """Find all MathTex/Tex strings and validate their LaTeX syntax."""
    diagnostics: list[LatexDiagnostic] = []
    
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return diagnostics  # Let Pyright handle python syntax errors

    # 1. Extract all LaTeX strings
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("MathTex", "Tex"):
                # We only check literal strings passed as args
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        tex_str = arg.value
                        err = _validate_single_tex(tex_str, is_math=(node.func.id == "MathTex"), timeout=timeout)
                        if err:
                            diagnostics.append(
                                LatexDiagnostic(
                                    line=arg.lineno or node.lineno or 1,
                                    column=(arg.col_offset or node.col_offset or 0) + 1,
                                    message=err,
                                    tex_string=tex_str,
                                )
                            )
    return diagnostics


def _validate_single_tex(tex: str, is_math: bool, timeout: float) -> str | None:
    """Compile a single TeX string and return the error message if any."""
    # Build a minimal Manim-like preamble
    # MathTex wraps in \begin{align*} ... \end{align*}
    # Tex wraps in \begin{center} ... \end{center}
    
    body = tex
    if is_math:
        body = f"\\begin{{align*}}\n{tex}\n\\end{{align*}}"
    else:
        body = f"\\begin{{center}}\n{tex}\n\\end{{center}}"

    document = f"""\\documentclass[preview]{{standalone}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{xcolor}}
\\begin{{document}}
{body}
\\end{{document}}"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        tex_file = tmp_path / "test.tex"
        tex_file.write_text(document, encoding="utf-8")
        
        try:
            # Run latex (or pdflatex) in nonstopmode
            # We use latex because manim generates dvi first
            result = subprocess.run(
                ["latex", "-interaction=nonstopmode", "-halt-on-error", "test.tex"],
                cwd=tmp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            
            if result.returncode != 0:
                # Parse the log for the first ! Error
                log_file = tmp_path / "test.log"
                if log_file.exists():
                    log_text = log_file.read_text(encoding="utf-8")
                    return _extract_latex_error(log_text)
                return "LaTeX compilation failed."
                
        except subprocess.TimeoutExpired:
            return "LaTeX compilation timed out."
        except FileNotFoundError:
            logger.warning("latex command not found. Cannot validate LaTeX.")
            return None
            
    return None


def _extract_latex_error(log: str) -> str:
    """Extract the most relevant error message from a LaTeX log."""
    lines = log.splitlines()
    error_lines = []
    capture = False
    
    for line in lines:
        if line.startswith("!"):
            capture = True
            error_lines.append(line.lstrip("! "))
        elif capture:
            if line.strip() == "" or line.startswith("l."):
                if line.startswith("l."):
                    error_lines.append(line.strip())
                break
            error_lines.append(line.strip())
            
    if error_lines:
        return " ".join(error_lines)
    return "Unknown LaTeX error."
