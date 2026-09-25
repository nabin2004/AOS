"""Local logging and visual inspection system for HITL Pydantic AI pipeline.

Provides zero-cloud, friction-free local observability:
1. Disables Logfire cloud telemetry (send_to_logfire=False).
2. Pretty-prints rich terminal outputs (agent steps, tool calls, AST issues, diffs, timing, tokens).
3. Persists structured run JSON files locally (.dev_logs/hitl/) with full Pydantic AI message histories.
4. Integrates with Pydantic AI Hooks for lifecycle interception.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel
from rich.box import ROUNDED, SIMPLE
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from app.schemas.video_generation import VideoClassifyResponse
from app.services.manim_code import CodeRepair, PreflightResult

logger = logging.getLogger(__name__)

# Default directory for local development run logs
DEFAULT_LOG_DIR = Path(__file__).resolve().parents[2] / ".dev_logs" / "hitl"
# Default directory for structural HITL workspace artifacts (JSON and Python)
DEFAULT_WORKSPACE_DIR = Path(__file__).resolve().parents[2] / "hitl_workspace"


# ── 1. Logfire Remote Disabler ───────────────────────────────────────────────

def disable_logfire_remote() -> None:
    """Ensure Logfire never sends telemetry across the network in local dev mode."""
    try:
        import logfire
        logfire.configure(
            send_to_logfire=False,
            console=False,
        )
    except Exception as exc:
        logger.debug("Logfire configuration skipped: %s", exc)


# ── 2. Message History Serializer ─────────────────────────────────────────────

def serialize_model_messages(messages: list[Any] | None) -> list[dict[str, Any]]:
    """Convert Pydantic AI ModelMessage instances into JSON-serializable dictionaries."""
    if not messages:
        return []

    serialized: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, dict):
            serialized.append(msg)
            continue
        if isinstance(msg, BaseModel):
            try:
                serialized.append(msg.model_dump(mode="json"))
                continue
            except Exception:
                pass
        elif is_dataclass(msg) and not isinstance(msg, type):
            try:
                serialized.append(asdict(msg))
                continue
            except Exception:
                pass

        # Fallback dictionary or string representation
        if hasattr(msg, "__dict__"):
            try:
                clean_dict = {}
                for k, v in msg.__dict__.items():
                    if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                        clean_dict[k] = v
                    elif hasattr(v, "model_dump"):
                        clean_dict[k] = v.model_dump(mode="json")
                    else:
                        clean_dict[k] = str(v)
                serialized.append(clean_dict)
                continue
            except Exception:
                pass

        serialized.append({"type": type(msg).__name__, "content": str(msg)})

    return serialized


# ── 3. Local Run Storage ──────────────────────────────────────────────────────

class HitlRunStore:
    """Manages saving and reading structured execution runs locally."""

    def __init__(self, log_dir: Path | str | None = None) -> None:
        self.log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.last_run_file = self.log_dir / "last_run.json"

    def record_run(
        self,
        *,
        stage: str,
        topic: str | None = None,
        model_name: str | None = None,
        duration: float = 0.0,
        success: bool = True,
        error_message: str | None = None,
        usage: Any = None,
        messages: list[Any] | None = None,
        preflight: PreflightResult | None = None,
        repair: CodeRepair | None = None,
        artifacts: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Save a structured execution log to disk and update last_run.json."""
        run_id = str(uuid4())
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"run_{timestamp_str}_{stage}_{run_id[:8]}.json"
        log_path = self.log_dir / filename

        usage_dict: dict[str, Any] = {}
        if usage:
            if hasattr(usage, "model_dump"):
                usage_dict = usage.model_dump(mode="json")
            elif hasattr(usage, "__dict__"):
                usage_dict = {
                    k: v for k, v in usage.__dict__.items()
                    if isinstance(v, (int, float, str, bool)) or v is None
                }

        preflight_dict: dict[str, Any] | None = None
        if preflight:
            preflight_dict = {
                "valid": preflight.valid,
                "status": preflight.status,
                "blocking": preflight.blocking,
                "errors": list(preflight.errors),
                "issues": list(preflight.issues),
            }

        repair_dict: dict[str, Any] | None = None
        if repair:
            repair_dict = {
                "changes_count": len(repair.changes),
                "changes": list(repair.changes),
                "semantic_warnings": list(repair.semantic_warnings),
            }

        record = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "topic": topic,
            "model": model_name,
            "success": success,
            "error_message": error_message,
            "duration_seconds": round(duration, 3),
            "usage": usage_dict,
            "preflight": preflight_dict,
            "repair": repair_dict,
            "messages": serialize_model_messages(messages),
            "artifacts": artifacts or {},
            "metadata": metadata or {},
        }

        content = json.dumps(record, indent=2, default=str)
        log_path.write_text(content, encoding="utf-8")
        try:
            self.last_run_file.write_text(content, encoding="utf-8")
        except Exception:
            pass

        return log_path

    def get_last_run(self) -> dict[str, Any] | None:
        """Read the most recent run record from disk."""
        if not self.last_run_file.exists():
            return None
        try:
            return json.loads(self.last_run_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def list_runs(self, limit: int = 10) -> list[Path]:
        """List the newest run log files."""
        files = sorted(
            [f for f in self.log_dir.glob("run_*.json") if f.name != "last_run.json"],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return files[:limit]


# ── 4. Structural HITL Workspace Directory ───────────────────────────────────

class HitlWorkspace:
    """Manages structural file artifacts (JSON and Python) for HITL pipeline execution.

    Keeps artifacts organized in clean, standardized file formats:
    - input.json: Raw text/prompt inputs in JSON format
    - classification.json: Pedagogical classification in JSON format
    - scenes.md: Visual storyboard plan in Markdown format (human readable/editable)
    - plan.json: Visual storyboard plan in JSON format
    - scene.py: Synthesized Manim Community scene in Python code format
    - code.json: Scene metadata, AST preflight status, and LSP diagnostics in JSON format
    - preflight.json: Static AST & LSP diagnostic reports in JSON format
    - error.json: Traceback and classified errors in JSON format
    - repair.json: Self-correcting repair modifications in JSON format
    - manifest.json: Index of active artifacts and latest stage state
    """

    def __init__(self, workspace_dir: Path | str | None = None) -> None:
        self.workspace_dir = Path(workspace_dir).resolve() if workspace_dir else DEFAULT_WORKSPACE_DIR
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        self.input_file = self.workspace_dir / "input.json"
        self.classification_file = self.workspace_dir / "classification.json"
        self.plan_md_file = self.workspace_dir / "scenes.md"
        self.plan_json_file = self.workspace_dir / "plan.json"
        self.scene_file = self.workspace_dir / "scene.py"
        self.code_json_file = self.workspace_dir / "code.json"
        self.preflight_file = self.workspace_dir / "preflight.json"
        self.error_file = self.workspace_dir / "error.json"
        self.repair_file = self.workspace_dir / "repair.json"
        self.manifest_file = self.workspace_dir / "manifest.json"

    # ── Input handling ──
    def save_input(self, text: str, topic: str | None = None) -> Path:
        """Persist raw input text or query into input.json."""
        data = {
            "text": text,
            "topic": topic,
            "updated_at": datetime.now().isoformat(),
        }
        self.input_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.update_manifest(stage="input", topic=topic)
        return self.input_file

    def load_input(self) -> dict[str, Any] | None:
        """Load raw input query/text from input.json if present."""
        if not self.input_file.exists():
            return None
        try:
            return json.loads(self.input_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    # ── Classification handling ──
    def save_classification(
        self,
        classification: VideoClassifyResponse | dict[str, Any],
        query: str | None = None,
    ) -> Path:
        """Save classification output in structured JSON format (classification.json)."""
        if isinstance(classification, VideoClassifyResponse):
            data = {
                "query": query,
                "animatable": classification.animatable,
                "subject": classification.subject,
                "topic": classification.topic,
                "reason": classification.reason,
                "updated_at": datetime.now().isoformat(),
            }
            topic = classification.topic
        else:
            data = dict(classification)
            if query:
                data["query"] = query
            data["updated_at"] = datetime.now().isoformat()
            topic = data.get("topic")

        self.classification_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.update_manifest(stage="classify", topic=topic)
        return self.classification_file

    def load_classification(self) -> dict[str, Any] | None:
        """Read classification.json if present in workspace."""
        if not self.classification_file.exists():
            return None
        try:
            return json.loads(self.classification_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    # ── Plan handling ──
    def save_plan(
        self,
        plan_markdown: str,
        topic: str,
        source_text: str | None = None,
    ) -> tuple[Path, Path]:
        """Save visual plan in Markdown (scenes.md) and structured JSON (plan.json)."""
        self.plan_md_file.write_text(plan_markdown, encoding="utf-8")

        plan_data = {
            "topic": topic,
            "source_text": source_text,
            "plan_markdown": plan_markdown,
            "updated_at": datetime.now().isoformat(),
        }
        self.plan_json_file.write_text(json.dumps(plan_data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.update_manifest(stage="compose", topic=topic)
        return self.plan_md_file, self.plan_json_file

    def load_plan(self) -> tuple[str | None, str | None]:
        """Load (plan_markdown, topic) from scenes.md and plan.json.

        Prefers scenes.md content so any manual human edits in the file take effect.
        """
        plan_md = None
        topic = None

        if self.plan_md_file.exists():
            plan_md = self.plan_md_file.read_text(encoding="utf-8")

        if self.plan_json_file.exists():
            try:
                data = json.loads(self.plan_json_file.read_text(encoding="utf-8"))
                topic = data.get("topic")
                if not plan_md:
                    plan_md = data.get("plan_markdown")
            except Exception:
                pass

        if not topic and self.classification_file.exists():
            try:
                data = json.loads(self.classification_file.read_text(encoding="utf-8"))
                topic = data.get("topic")
            except Exception:
                pass

        return plan_md, topic

    # ── Code handling ──
    def save_code(
        self,
        code: str,
        scene_name: str,
        topic: str | None = None,
        preflight: PreflightResult | None = None,
        repair: CodeRepair | None = None,
        lsp_report: Any = None,
    ) -> tuple[Path, Path]:
        """Save synthesized Manim code in Python (.py) and metadata in JSON (code.json)."""
        self.scene_file.write_text(code, encoding="utf-8")

        preflight_dict = None
        if preflight:
            preflight_dict = {
                "valid": preflight.valid,
                "status": preflight.status,
                "blocking": preflight.blocking,
                "errors": list(preflight.errors),
                "issues": list(preflight.issues),
            }

        lsp_dict = None
        if lsp_report:
            lsp_dict = {
                "has_errors": getattr(lsp_report, "has_errors", False),
                "diagnostics": [d.__dict__ for d in getattr(lsp_report, "diagnostics", [])],
            }

        code_data = {
            "topic": topic,
            "scene_name": scene_name,
            "scene_file": self.scene_file.name,
            "preflight": preflight_dict,
            "lsp": lsp_dict,
            "updated_at": datetime.now().isoformat(),
        }
        self.code_json_file.write_text(json.dumps(code_data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.update_manifest(stage="code", topic=topic)
        return self.scene_file, self.code_json_file

    def load_code(self) -> tuple[str | None, str | None]:
        """Load (code, scene_name) from scene.py and code.json."""
        if not self.scene_file.exists():
            return None, None

        code = self.scene_file.read_text(encoding="utf-8")
        scene_name = "GeneratedScene"

        if self.code_json_file.exists():
            try:
                data = json.loads(self.code_json_file.read_text(encoding="utf-8"))
                scene_name = data.get("scene_name") or scene_name
            except Exception:
                pass

        if scene_name == "GeneratedScene":
            import re
            m = re.search(r"class\s+([A-Za-z0-9_]+)\s*\((?:.*?)Scene(?:.*?)\)", code)
            if m:
                scene_name = m.group(1)

        return code, scene_name

    # ── Preflight handling ──
    def save_preflight(
        self,
        preflight: PreflightResult,
        repair: CodeRepair | None = None,
        lsp_report: Any = None,
    ) -> Path:
        """Save AST and LSP preflight results in JSON format (preflight.json)."""
        data = {
            "valid": preflight.valid,
            "status": preflight.status,
            "blocking": preflight.blocking,
            "errors": list(preflight.errors),
            "issues": list(preflight.issues),
            "repair_changes": list(repair.changes) if repair else [],
            "lsp_errors": getattr(lsp_report, "has_errors", False) if lsp_report else False,
            "updated_at": datetime.now().isoformat(),
        }
        self.preflight_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return self.preflight_file

    def load_preflight(self) -> dict[str, Any] | None:
        """Read preflight.json if present in workspace."""
        if not self.preflight_file.exists():
            return None
        try:
            return json.loads(self.preflight_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    # ── Repair handling ──
    def save_repair(
        self,
        repaired_code: str,
        scene_name: str,
        error: str,
        category: str,
        changes: list[str],
    ) -> tuple[Path, Path]:
        """Save repaired Python scene (updating scene.py, preserving scene_backup.py) and repair.json."""
        if self.scene_file.exists():
            backup_file = self.workspace_dir / "scene_backup.py"
            backup_file.write_text(self.scene_file.read_text(encoding="utf-8"), encoding="utf-8")

        self.scene_file.write_text(repaired_code, encoding="utf-8")

        repair_data = {
            "scene_name": scene_name,
            "category": category,
            "error": error,
            "changes": changes,
            "updated_at": datetime.now().isoformat(),
        }
        self.repair_file.write_text(json.dumps(repair_data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.update_manifest(stage="repair")
        return self.scene_file, self.repair_file

    def load_error(self) -> str | None:
        """Load error string from error.json or error.txt if present."""
        if self.error_file.exists():
            try:
                data = json.loads(self.error_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data.get("error") or data.get("traceback") or str(data)
                return str(data)
            except Exception:
                return self.error_file.read_text(encoding="utf-8")
        error_txt = self.workspace_dir / "error.txt"
        if error_txt.exists():
            return error_txt.read_text(encoding="utf-8")
        return None

    # ── Manifest handling ──
    def update_manifest(self, stage: str, topic: str | None = None) -> Path:
        """Update manifest.json tracking active files in the workspace directory."""
        manifest_data = {
            "workspace_dir": str(self.workspace_dir),
            "last_stage": stage,
            "topic": topic,
            "updated_at": datetime.now().isoformat(),
            "files": {
                "input_json": self.input_file.name if self.input_file.exists() else None,
                "classification_json": self.classification_file.name if self.classification_file.exists() else None,
                "scenes_md": self.plan_md_file.name if self.plan_md_file.exists() else None,
                "plan_json": self.plan_json_file.name if self.plan_json_file.exists() else None,
                "scene_py": self.scene_file.name if self.scene_file.exists() else None,
                "code_json": self.code_json_file.name if self.code_json_file.exists() else None,
                "preflight_json": self.preflight_file.name if self.preflight_file.exists() else None,
                "repair_json": self.repair_file.name if self.repair_file.exists() else None,
            },
        }
        self.manifest_file.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
        return self.manifest_file

    def get_status(self) -> dict[str, Any]:
        """Inspect all available workspace files."""
        return {
            "workspace": str(self.workspace_dir),
            "input": self.input_file.exists(),
            "classification": self.classification_file.exists(),
            "plan_md": self.plan_md_file.exists(),
            "plan_json": self.plan_json_file.exists(),
            "scene_py": self.scene_file.exists(),
            "code_json": self.code_json_file.exists(),
            "preflight": self.preflight_file.exists(),
            "repair": self.repair_file.exists(),
        }


# ── 5. Rich Terminal Observer ─────────────────────────────────────────────────

class HitlTerminalObserver:
    """Renders real-time visual output, syntax formatting, diffs, and diagnostics in terminal."""

    def __init__(
        self,
        console: Console | None = None,
        verbose: bool = False,
        mock_mode: bool = False,
    ) -> None:
        if sys.platform == "win32":
            try:
                if hasattr(sys.stdout, "reconfigure"):
                    sys.stdout.reconfigure(encoding="utf-8")
                if hasattr(sys.stderr, "reconfigure"):
                    sys.stderr.reconfigure(encoding="utf-8")
            except Exception:
                pass
        self.console = console or Console(legacy_windows=False)
        self.verbose = verbose
        self.mock_mode = mock_mode
        # Track whether any stage recovered from a model failure
        self.recovered_stages: list[str] = []

    def banner(self, title: str, subtitle: str = "") -> None:
        """Render a major stage header banner (live mode — cyan)."""
        content = f"[bold white]{title}[/bold white]"
        if subtitle:
            content += f"\n[dim]{subtitle}[/dim]"
        self.console.print(
            Panel(
                content,
                box=ROUNDED,
                style="cyan",
                padding=(0, 2),
            )
        )

    def mock_banner(self, title: str, subtitle: str = "") -> None:
        """Render a stage header with a loud MOCK watermark (amber/yellow).

        Call this instead of banner() for every stage when mock=True so it's
        impossible to mistake offline TestModel output for real LLM output.
        """
        content = (
            f"[bold yellow]\u26a0 MOCK / OFFLINE MODE \u26a0[/bold yellow]\n"
            f"[bold white]{title}[/bold white]"
        )
        if subtitle:
            content += f"\n[dim yellow]{subtitle}  [dim](Pydantic AI TestModel — 0 tokens)[/dim][/dim]"
        self.console.print(
            Panel(
                content,
                box=ROUNDED,
                style="yellow",
                padding=(0, 2),
                title="[bold yellow][ MOCK ][/bold yellow]",
                title_align="right",
            )
        )

    def recovery_alarm(
        self,
        stage: str,
        exc: Exception,
        method: str,
        traceback_str: str = "",
    ) -> None:
        """Render a full-width RED alarm panel when the model failed structured output
        and the pipeline is falling back to a heuristic/regex recovery.

        This makes it impossible to silently treat recovered data as real LLM output.
        """
        self.recovered_stages.append(stage)
        lines = [
            f"[bold red]\u2718 STRUCTURED OUTPUT FAILURE — STAGE: {stage.upper()}[/bold red]",
            "",
            f"[red]Exception:[/red] [bold]{type(exc).__name__}[/bold]: {exc}",
            "",
            f"[bold yellow]Fallback method:[/bold yellow] {method}",
            "[yellow]The data shown below was NOT produced by the LLM — it was recovered"
            " heuristically or via regex from raw model output.[/yellow]",
            "",
            "[dim]Re-run with --verbose to see the full captured message trace.[/dim]",
        ]
        if traceback_str and self.verbose:
            lines += ["", "[dim]── Full Traceback ──[/dim]", f"[dim]{traceback_str}[/dim]"]
        self.console.print(
            Panel(
                "\n".join(lines),
                box=ROUNDED,
                style="red",
                title="[bold red][ RECOVERY ALARM ][/bold red]",
                padding=(0, 2),
            )
        )


    def step(self, badge: str, title: str, detail: str = "") -> None:
        """Render an in-progress step status."""
        badge_str = f"[{badge}]" if not badge.startswith("[") else badge
        text = f"[bold cyan]{badge_str}[/bold cyan] [bold]{title}[/bold]"
        if detail:
            text += f" [dim]({detail})[/dim]"
        self.console.print(text)

    def success(self, msg: str) -> None:
        """Render a success message."""
        self.console.print(f"[bold green][OK][/bold green] {msg}")

    def warning(self, msg: str) -> None:
        """Render a warning message."""
        self.console.print(f"[bold yellow][!][/bold yellow] {msg}")

    def error(self, msg: str) -> None:
        """Render an error message."""
        self.console.print(f"[bold red][FAIL][/bold red] {msg}")

    def show_prompt(self, system_prompt: str, user_prompt: str) -> None:
        """Display prompt details when in verbose mode."""
        if not self.verbose:
            return
        self.console.print(
            Panel(
                f"[bold cyan]System Prompt:[/bold cyan]\n[dim]{system_prompt[:500]}...[/dim]\n\n"
                f"[bold cyan]User Prompt:[/bold cyan]\n{user_prompt[:800]}",
                title="[dim]Prompt Preview[/dim]",
                box=ROUNDED,
                style="dim",
            )
        )

    def show_tool_call(self, tool_name: str, args: dict[str, Any], result: Any = None, duration: float = 0.0) -> None:
        """Render agent tool invocation and result."""
        args_str = json.dumps(args, indent=2, default=str)
        res_str = str(result)[:300] if result is not None else ""
        content = f"[bold green]Tool:[/bold green] [bold]{tool_name}[/bold]"
        if duration > 0:
            content += f" [dim]({duration:.2f}s)[/dim]"
        content += f"\n[cyan]Arguments:[/cyan]\n{args_str}"
        if res_str:
            content += f"\n[yellow]Result Preview:[/yellow]\n{res_str}"

        self.console.print(
            Panel(
                content,
                title="[bold magenta]Agent Tool Execution[/bold magenta]",
                box=ROUNDED,
                style="magenta",
                padding=(0, 1),
            )
        )

    def show_classification(
        self,
        result: VideoClassifyResponse,
        duration: float = 0.0,
        usage: Any = None,
        is_mock: bool = False,
        is_recovered: bool = False,
    ) -> None:
        """Render structured classification output."""
        badge = "[bold green]ANIMATABLE[/bold green]" if result.animatable else "[bold red]NON-ANIMATABLE[/bold red]"
        table = Table(box=SIMPLE, show_header=False, padding=(0, 1))
        table.add_column("Key", style="bold cyan")
        table.add_column("Value")

        table.add_row("Decision", badge)
        table.add_row("Subject", result.subject.upper())
        table.add_row("Topic", result.topic or "[dim]N/A[/dim]")
        table.add_row("Reasoning", result.reason)
        if is_mock:
            table.add_row("Source", "[bold yellow]\u26a0 MOCK (TestModel)[/bold yellow]")
        elif is_recovered:
            table.add_row("Source", "[bold red]\u26a0 RECOVERED (heuristic fallback — NOT real LLM output)[/bold red]")
        if duration > 0:
            table.add_row("Latency", f"{duration:.2f}s")
        if usage and hasattr(usage, "total_tokens"):
            table.add_row("Tokens", f"{usage.total_tokens} total ({getattr(usage, 'input_tokens', 0)} in, {getattr(usage, 'output_tokens', 0)} out)")

        self.console.print(
            Panel(
                table,
                title="[bold cyan]Stage 1: Pedagogical Classification[/bold cyan]",
                box=ROUNDED,
                style="cyan",
            )
        )

    def show_plan(self, plan_markdown: str, topic: str, duration: float = 0.0, usage: Any = None) -> None:
        """Render the generated scenes.md plan."""
        scenes = [line for line in plan_markdown.splitlines() if line.startswith("## Scene")]
        preview = plan_markdown if self.verbose else "\n".join(plan_markdown.splitlines()[:25])
        if not self.verbose and len(plan_markdown.splitlines()) > 25:
            preview += f"\n\n[dim]... (+{len(plan_markdown.splitlines()) - 25} more lines — use --verbose to view all)[/dim]"

        meta_info = f"[bold cyan]Topic:[/bold cyan] {topic}  |  [bold cyan]Detected Scenes:[/bold cyan] {len(scenes)}"
        if duration > 0:
            meta_info += f"  |  [bold cyan]Time:[/bold cyan] {duration:.2f}s"
        if usage and hasattr(usage, "total_tokens"):
            meta_info += f"  |  [bold cyan]Tokens:[/bold cyan] {usage.total_tokens}"

        self.console.print(
            Panel(
                f"{meta_info}\n\n{preview}",
                title="[bold magenta]Stage 2: Composer Plan (scenes.md)[/bold magenta]",
                box=ROUNDED,
                style="magenta",
            )
        )

    def show_code(self, code: str, scene_name: str, duration: float = 0.0, usage: Any = None) -> None:
        """Render the synthesized Manim Python code with syntax highlighting."""
        lines = code.splitlines()
        line_count = len(lines)
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)

        meta = f"[bold green]Scene Class:[/bold green] {scene_name}  |  [bold green]Lines:[/bold green] {line_count}"
        if duration > 0:
            meta += f"  |  [bold green]Time:[/bold green] {duration:.2f}s"
        if usage and hasattr(usage, "total_tokens"):
            meta += f"  |  [bold green]Tokens:[/bold green] {usage.total_tokens}"

        self.console.print(
            Panel(
                syntax,
                title=f"[bold green]Stage 3: Manim Python Code ({scene_name})[/bold green]",
                subtitle=meta,
                box=ROUNDED,
                style="green",
            )
        )

    def show_preflight(self, preflight: PreflightResult, repair: CodeRepair | None = None) -> None:
        """Render preflight AST static validation findings and deterministic fixes."""
        if repair and repair.changes:
            changes_table = Table(box=SIMPLE, show_header=True)
            changes_table.add_column("#", style="dim", width=4)
            changes_table.add_column("Deterministic AST Repair Applied", style="bold yellow")
            for idx, change in enumerate(repair.changes, start=1):
                changes_table.add_row(str(idx), change)

            self.console.print(
                Panel(
                    changes_table,
                    title="[bold yellow]Pre-Flight Deterministic AST Fixes[/bold yellow]",
                    box=ROUNDED,
                    style="yellow",
                )
            )

        if repair and repair.semantic_warnings:
            warnings_text = "\n".join(f"* [bold yellow]{w}[/bold yellow]" for w in repair.semantic_warnings)
            self.console.print(
                Panel(
                    warnings_text,
                    title="[bold yellow][!] Semantic Drift Warnings (Visual Review Recommended)[/bold yellow]",
                    box=ROUNDED,
                    style="yellow",
                )
            )

        if preflight.valid:
            self.console.print(
                Panel(
                    "[bold green][OK] Preflight Passed: Python syntax, AST structures, and ManimCE constructs are clean.[/bold green]",
                    box=ROUNDED,
                    style="green",
                )
            )
            return

        # Show table of static errors
        table = Table(box=ROUNDED, show_header=True)
        table.add_column("Line", style="cyan", width=6)
        table.add_column("Type / Rule", style="bold red", width=24)
        table.add_column("Diagnostic Message")
        table.add_column("Severity", style="bold", width=12)

        for err in preflight.errors:
            line_no = str(err.get("line") or err.get("lineno") or "-")
            err_type = str(err.get("type") or err.get("rule") or "StaticError")
            msg = str(err.get("message") or err.get("msg") or "")
            blocking = "[bold red]BLOCKING[/bold red]" if err.get("blocking", True) else "[yellow]WARNING[/yellow]"
            table.add_row(line_no, err_type, msg, blocking)

        self.console.print(
            Panel(
                table,
                title=f"[bold red]Stage 4: Preflight Validation Failed ({len(preflight.errors)} issue(s))[/bold red]",
                box=ROUNDED,
                style="red",
            )
        )

    def show_lsp(self, report: Any) -> None:
        """Render Pyright LSP static analysis & typing findings in a formatted panel."""
        if not report or not getattr(report, "success", False):
            if report and getattr(report, "error_message", None):
                self.console.print(f"[dim yellow][LSP Notice] {report.error_message}[/dim yellow]")
            return

        if not report.diagnostics:
            self.console.print(
                Panel(
                    "[bold green][OK] LSP Diagnostics Clean: 0 type/attribute errors reported by Pyright.[/bold green]",
                    box=ROUNDED,
                    style="green",
                )
            )
            return

        self.console.print(
            Panel(
                report.to_rich_table(),
                title=f"[bold {'red' if report.has_errors else 'yellow'}]LSP Type & Member Diagnostics ({report.error_count} error(s), {report.warning_count} warning(s))[/bold {'red' if report.has_errors else 'yellow'}]",
                box=ROUNDED,
                style="red" if report.has_errors else "yellow",
            )
        )

    def show_code_diff(self, old_code: str, new_code: str, title: str = "Code Diff") -> None:
        """Render unified diff with colored additions and deletions."""
        diff_lines = list(
            difflib.unified_diff(
                old_code.splitlines(),
                new_code.splitlines(),
                fromfile="original.py",
                tofile="repaired.py",
                lineterm="",
            )
        )
        if not diff_lines:
            self.console.print("[dim]No diff detected between original and repaired code.[/dim]")
            return

        diff_text = Text()
        for line in diff_lines:
            if line.startswith("+++") or line.startswith("---"):
                diff_text.append(line + "\n", style="bold cyan")
            elif line.startswith("@@"):
                diff_text.append(line + "\n", style="bold magenta")
            elif line.startswith("+"):
                diff_text.append(line + "\n", style="bold green")
            elif line.startswith("-"):
                diff_text.append(line + "\n", style="bold red")
            else:
                diff_text.append(line + "\n", style="dim")

        self.console.print(
            Panel(
                diff_text,
                title=f"[bold yellow]{title}[/bold yellow]",
                box=ROUNDED,
                style="yellow",
            )
        )

    def show_run_summary(
        self,
        *,
        stage: str,
        status: str,
        duration: float,
        usage: dict[str, Any],
        log_path: Path,
    ) -> None:
        """Render execution summary footer."""
        status_text = "[bold green]SUCCESS[/bold green]" if status == "success" else "[bold red]FAILED[/bold red]"
        table = Table(box=SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value")

        table.add_row("Stage", stage.upper())
        table.add_row("Status", status_text)
        table.add_row("Total Time", f"{duration:.2f}s")
        if usage:
            table.add_row("Token Usage", f"requests={usage.get('requests', 1)}, in={usage.get('input_tokens', 0)}, out={usage.get('output_tokens', 0)}, total={usage.get('total_tokens', 0)}")
        table.add_row("Local Run Log", f"[underline cyan]{log_path}[/underline cyan]")

        self.console.print(
            Panel(
                table,
                title="[bold white]HITL Local Pipeline Summary[/bold white]",
                box=ROUNDED,
                style="white",
            )
        )

    def show_workspace_status(self, workspace: HitlWorkspace) -> None:
        """Render a summary table of structural files existing in the HITL workspace."""
        table = Table(box=ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("Artifact", style="bold")
        table.add_column("Format", style="cyan")
        table.add_column("Filename", style="white")
        table.add_column("Status", style="green")

        items = [
            ("Raw Input", "JSON", workspace.input_file),
            ("Classification", "JSON", workspace.classification_file),
            ("Visual Plan (scenes.md)", "Markdown", workspace.plan_md_file),
            ("Visual Plan (plan.json)", "JSON", workspace.plan_json_file),
            ("Manim Scene Code", "Python (.py)", workspace.scene_file),
            ("Code Metadata & LSP", "JSON", workspace.code_json_file),
            ("Preflight AST Report", "JSON", workspace.preflight_file),
            ("Repair Report", "JSON", workspace.repair_file),
            ("Pipeline Manifest", "JSON", workspace.manifest_file),
        ]
        for name, fmt, path in items:
            exists = path.exists()
            status_str = f"[bold green]EXISTS ({path.stat().st_size} B)[/bold green]" if exists else "[dim]NOT CREATED[/dim]"
            table.add_row(name, fmt, path.name, status_str)

        self.console.print(
            Panel(
                table,
                title=f"[bold white]HITL Workspace Artifacts ({workspace.workspace_dir.name})[/bold white]",
                box=ROUNDED,
                style="cyan",
            )
        )


# ── 6. Pydantic AI Lifecycle Hooks for Local Dev ──────────────────────────────


def create_hitl_local_dev_hooks(
    observer: HitlTerminalObserver | None = None,
) -> Any:
    """Create a Pydantic AI Hooks capability that logs lifecycle events to the terminal."""
    try:
        from pydantic_ai import RunContext, ToolDefinition
        from pydantic_ai.capabilities import ValidatedToolArgs
        from pydantic_ai.capabilities.hooks import Hooks
        from pydantic_ai.messages import ToolCallPart
        from pydantic_ai.models import ModelRequestContext
    except ImportError:
        logger.debug("Pydantic AI Hooks not available in this environment")
        return None

    obs = observer or HitlTerminalObserver()
    hooks = Hooks()
    tool_start_times: dict[str, float] = {}

    @hooks.on.before_model_request
    async def on_before_model_request(
        ctx: RunContext[Any],
        request_context: ModelRequestContext,
        *args: Any,
        **kwargs: Any,
    ) -> ModelRequestContext:
        msg_count = len(request_context.messages) if hasattr(request_context, "messages") else 0
        if obs.verbose:
            obs.step("LLM", "Requesting LLM Completion", f"{msg_count} messages in context")
        return request_context

    @hooks.on.before_tool_execute
    async def on_before_tool_execute(
        ctx: RunContext[Any],
        *args: Any,
        call: ToolCallPart | None = None,
        tool_def: ToolDefinition | None = None,
        tool_args: ValidatedToolArgs | None = None,
        **kwargs: Any,
    ) -> Any:
        tool_call = call or kwargs.get("call")
        t_args = tool_args or kwargs.get("args")
        tool_name = getattr(tool_call, "tool_name", "unknown_tool")
        tool_start_times[tool_name] = time.perf_counter()
        obs.step("TOOL", f"Invoking Tool: [bold]{tool_name}[/bold]")
        return t_args or args[0] if args else kwargs

    @hooks.on.after_tool_execute
    async def on_after_tool_execute(
        ctx: RunContext[Any],
        *args: Any,
        call: ToolCallPart | None = None,
        tool_def: ToolDefinition | None = None,
        tool_args: ValidatedToolArgs | None = None,
        result: Any = None,
        **kwargs: Any,
    ) -> Any:
        tool_call = call or kwargs.get("call")
        tool_name = getattr(tool_call, "tool_name", "unknown_tool")
        start_t = tool_start_times.pop(tool_name, time.perf_counter())
        elapsed = time.perf_counter() - start_t
        t_args = tool_args or kwargs.get("args")
        arg_dict = t_args.args if hasattr(t_args, "args") else (t_args if isinstance(t_args, dict) else {})
        res = result if result is not None else kwargs.get("result")
        obs.show_tool_call(tool_name, arg_dict if isinstance(arg_dict, dict) else {}, res, duration=elapsed)
        return res

    @hooks.on.run_error
    async def on_run_error(
        ctx: RunContext[Any],
        *args: Any,
        error: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        exc = error or kwargs.get("exc") or (args[0] if args else "Unknown error")
        exc_type = type(exc).__name__ if isinstance(exc, Exception) else "Error"
        obs.error(f"Agent Run Exception: {exc_type} — {exc}")

    return hooks
