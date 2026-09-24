"""LSP & Static Type Diagnostics Service for Manim Source Code.

Wraps Pyright LSP diagnostics in JSON mode to provide precise line-level feedback
on attribute errors, invalid arguments, typing violations, and missing members
(e.g., VGroup.clear, Camera.frame on standard Scene, etc.) before or during code repair.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.table import Table

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LspDiagnostic:
    file: str
    severity: str  # "error", "warning", "information"
    message: str
    line: int  # 1-indexed line number
    character: int  # 1-indexed column number
    rule: str | None = None
    end_line: int | None = None
    end_character: int | None = None

    @property
    def is_error(self) -> bool:
        return self.severity.lower() == "error"

    @property
    def is_warning(self) -> bool:
        return self.severity.lower() == "warning"

    def format_line(self) -> str:
        rule_tag = f" [{self.rule}]" if self.rule else ""
        return f"Line {self.line}:{self.character} ({self.severity.upper()}): {self.message}{rule_tag}"


@dataclass
class LspDiagnosticReport:
    success: bool
    diagnostics: list[LspDiagnostic] = field(default_factory=list)
    raw_summary: dict[str, Any] = field(default_factory=dict)
    time_taken_sec: float = 0.0
    command_used: str = ""
    error_message: str | None = None

    @property
    def has_errors(self) -> bool:
        return any(d.is_error for d in self.diagnostics)

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.is_error)

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.is_warning)

    @property
    def errors(self) -> list[LspDiagnostic]:
        return [d for d in self.diagnostics if d.is_error]

    @property
    def warnings(self) -> list[LspDiagnostic]:
        return [d for d in self.diagnostics if d.is_warning]

    def format_feedback(self, max_items: int = 15) -> str:
        """Format diagnostics as structured, high-signal feedback for the LLM repair prompt."""
        if not self.diagnostics:
            return "LSP Diagnostics: No errors or warnings detected."

        lines = [
            f"LSP Diagnostics Report ({self.error_count} error(s), {self.warning_count} warning(s)):",
            "CRITICAL: Address these exact lines and compiler findings in your targeted repair:",
        ]

        # Prioritize errors first
        sorted_diags = sorted(self.diagnostics, key=lambda d: (0 if d.is_error else 1, d.line))
        displayed = sorted_diags[:max_items]

        for d in displayed:
            tag = "ERROR" if d.is_error else "WARN"
            clean_msg = d.message.replace("\n", " ").strip()
            rule_str = f" [{d.rule}]" if d.rule else ""
            lines.append(f"- [LINE {d.line}:{d.character}] {tag}: {clean_msg}{rule_str}")

        if len(sorted_diags) > max_items:
            lines.append(f"... and {len(sorted_diags) - max_items} more diagnostic messages.")

        return "\n".join(lines)

    def to_rich_table(self, title: str = "LSP Diagnostics (Pyright)") -> Table:
        """Create a Rich table suitable for CLI terminal display."""
        table = Table(title=title, title_style="bold magenta", border_style="dim")
        table.add_column("Sev", style="bold", width=6)
        table.add_column("Line", style="cyan", width=8)
        table.add_column("Message", style="white")
        table.add_column("Rule", style="dim", width=25)

        for d in self.diagnostics[:20]:
            sev_color = "red" if d.is_error else ("yellow" if d.is_warning else "blue")
            sev_str = f"[{sev_color}]{d.severity.upper()}[/{sev_color}]"
            loc_str = f"{d.line}:{d.character}"
            rule_str = d.rule or "-"
            table.add_row(sev_str, loc_str, d.message.split("\n")[0][:100], rule_str)

        return table


def _detect_pyright_command() -> list[str] | None:
    """Find available Pyright command runner."""
    # 1. Direct pyright binary
    if shutil.which("pyright"):
        return ["pyright"]
    # 2. uv tool / uv run --with pyright
    if shutil.which("uv"):
        return ["uv", "run", "--with", "pyright", "pyright"]
    # 3. npx pyright
    if shutil.which("npx"):
        return ["npx", "--yes", "pyright"]
    return None


def run_pyright_lsp(
    target: str | Path,
    is_code: bool = False,
    timeout: float = 45.0,
) -> LspDiagnosticReport:
    """Run Pyright LSP analysis on a file path or code string and return structured diagnostics.

    Parameters:
        target: File path or raw Python source code string.
        is_code: If True, target is treated as source code string and written to a temporary file.
        timeout: Subprocess timeout in seconds.
    """
    cmd_prefix = _detect_pyright_command()
    if not cmd_prefix:
        return LspDiagnosticReport(
            success=False,
            error_message="Pyright runner not found. Install via `pip install pyright` or ensure `uv` is available.",
        )

    temp_file: Path | None = None
    target_path: Path

    if is_code or isinstance(target, str) and ("\n" in target or not os.path.exists(target)):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(str(target))
            temp_file = Path(f.name)
            target_path = temp_file
    else:
        target_path = Path(target).resolve()

    cmd = [*cmd_prefix, "--outputjson", str(target_path)]

    import time
    start_t = time.perf_counter()

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        elapsed = time.perf_counter() - start_t

        output_str = proc.stdout.strip()
        if not output_str and proc.stderr:
            return LspDiagnosticReport(
                success=False,
                time_taken_sec=elapsed,
                command_used=" ".join(cmd),
                error_message=f"Pyright failed with: {proc.stderr[:400]}",
            )

        try:
            data = json.loads(output_str)
        except json.JSONDecodeError as exc:
            return LspDiagnosticReport(
                success=False,
                time_taken_sec=elapsed,
                command_used=" ".join(cmd),
                error_message=f"Failed to parse Pyright JSON output: {exc}. Raw stdout: {output_str[:200]}",
            )

        raw_diagnostics = data.get("generalDiagnostics", [])
        summary = data.get("summary", {})

        diagnostics: list[LspDiagnostic] = []
        for item in raw_diagnostics:
            rng = item.get("range", {})
            start = rng.get("start", {})
            end = rng.get("end", {})
            # Pyright reports 0-indexed line numbers; convert to 1-indexed for standard user/compiler view
            start_line = start.get("line", 0) + 1
            start_char = start.get("character", 0) + 1
            end_line = (end.get("line", 0) + 1) if "line" in end else None
            end_char = (end.get("character", 0) + 1) if "character" in end else None

            diagnostics.append(
                LspDiagnostic(
                    file=item.get("file", str(target_path)),
                    severity=item.get("severity", "error"),
                    message=item.get("message", "").strip(),
                    line=start_line,
                    character=start_char,
                    rule=item.get("rule"),
                    end_line=end_line,
                    end_character=end_char,
                )
            )

        return LspDiagnosticReport(
            success=True,
            diagnostics=diagnostics,
            raw_summary=summary,
            time_taken_sec=elapsed,
            command_used=" ".join(cmd),
        )

    except subprocess.TimeoutExpired:
        return LspDiagnosticReport(
            success=False,
            time_taken_sec=timeout,
            command_used=" ".join(cmd),
            error_message=f"Pyright LSP timed out after {timeout}s",
        )
    except Exception as exc:
        return LspDiagnosticReport(
            success=False,
            command_used=" ".join(cmd),
            error_message=f"Subprocess error executing Pyright: {exc}",
        )
    finally:
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    import sys
    from rich.console import Console

    console = Console()
    target_arg = sys.argv[1] if len(sys.argv) > 1 else "scene.py"
    console.print(f"[bold cyan]Running LSP analysis on:[/bold cyan] {target_arg}")
    rep = run_pyright_lsp(target_arg)
    if not rep.success:
        console.print(f"[bold red]Error:[/bold red] {rep.error_message}")
        sys.exit(1)

    console.print(rep.to_rich_table())
    console.print(f"\n[dim]{rep.format_feedback()}[/dim]")
