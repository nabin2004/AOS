"""Simple Rich TUI: transcript, last tool/permission line, slash input."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from educlaw.cli import HELP, _handle_slash
from educlaw.session import create_session
from educlaw.settings import Settings
from educlaw.logo import play_logo

console = Console()


def _emit_factory(state: dict):
    def emit(event: str, payload: object) -> None:
        state["last"] = f"{event}: {payload}"
        if event == "permission_required":
            console.print(Panel(str(payload), title="permission — /yes or /no", border_style="yellow"))
        elif event == "tool":
            console.print(f"[dim]tool[/] {payload}")
        elif event == "abort":
            console.print("[yellow]turn aborted[/]")

    return emit


async def run_tui(cwd: Path, settings: Settings) -> int:
    state = {"last": "idle"}
    handler = create_session(cwd=cwd, settings=settings, emit=_emit_factory(state))
    if not play_logo():
        console.print("Failed to play logo.")
        return 1
    console.print(Panel("EduClaw TUI — /help, /quit. Type while a turn runs to steer.", title="educlaw"))
    while True:
        try:
            line = console.input("[bold]>[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return 0
        if not line:
            continue
        if line in {"/yes", "/y"}:
            if handler.deps.gate.answer(True):
                console.print("[green]approved[/]")
            else:
                console.print("[dim]nothing pending[/]")
            continue
        if line in {"/no", "/n"}:
            if handler.deps.gate.answer(False):
                console.print("[red]denied[/]")
            else:
                console.print("[dim]nothing pending[/]")
            continue
        if line.startswith("/"):
            if await _handle_slash(handler, line):
                return 0
            continue
        if handler.running:
            handler.deps.steering.push(line)
            console.print("[dim]queued until the next model call[/]")
            continue
        try:
            output = await handler.run_turn(line)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]error:[/] {exc}")
            continue
        console.print(Panel(output, title="assistant", border_style="cyan"))
        if state["last"] != "idle":
            console.print(f"[dim]{state['last']}[/]")
    return 0
