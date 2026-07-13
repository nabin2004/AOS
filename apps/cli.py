"""AOS command-line interface.

    $ aos                                   shows the banner + command list
    $ aos create lecture "query" --duration 10 --subject math --topic calculus
    $ aos create course "query" --duration 10 --totalepisodes 10 --subject math --topic calculus
    $ aos list lectures
    $ aos list courses
    $ aos search lectures "query"
    $ aos search courses "query"
    $ aos play <id>                         opens a dummy HTML player in the browser

Run with: uv run python apps/cli.py <command>

`create` currently produces a mock-but-schema-valid lecture/course (see
packages/store) since the real apps/agents planning pipeline isn't wired up yet.
"""
import sys
import webbrowser
from pathlib import Path
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import store

console = Console()
app = typer.Typer(
    name="aos",
    help="AOS — AI-generated educational animation lectures & courses.",
    no_args_is_help=False,
    add_completion=False,
)
create_app = typer.Typer(help="Create a lecture or a course.")
list_app = typer.Typer(help="List saved lectures or courses.")
search_app = typer.Typer(help="Search saved lectures or courses.")
app.add_typer(create_app, name="create")
app.add_typer(list_app, name="list")
app.add_typer(search_app, name="search")

SUBJECTS = ["math", "cs", "ai"]


def _show_banner() -> None:
    try:
        from terminaltexteffects.effects.effect_decrypt import Decrypt

        effect = Decrypt("AOS")
        with effect.terminal_output() as terminal:
            for frame in effect:
                terminal.print(frame)
    except Exception:
        console.print(Panel.fit("[bold cyan]AOS[/]", subtitle="by Nabin :-)"))


def _show_command_help() -> None:
    table = Table(title="Commands", show_header=True, header_style="bold cyan")
    table.add_column("Command")
    table.add_column("Description")
    rows = [
        ("aos create lecture QUERY --duration 10 --subject math --topic calculus", "Generate a single lecture"),
        ("aos create course QUERY --duration 10 --totalepisodes 10 --subject math --topic calculus", "Generate a multi-episode course"),
        ("aos list lectures", "List saved lectures"),
        ("aos list courses", "List saved courses"),
        ("aos search lectures QUERY", "Search saved lectures"),
        ("aos search courses QUERY", "Search saved courses"),
        ("aos play ID", "Open a lecture/course in the browser"),
    ]
    for cmd, desc in rows:
        table.add_row(cmd, desc)
    console.print(table)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _show_banner()
        _show_command_help()


def _lecture_table(records: list) -> Table:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("id")
    table.add_column("topic")
    table.add_column("subject")
    table.add_column("duration (min)", justify="right")
    table.add_column("course")
    table.add_column("created_at")
    for r in records:
        table.add_row(
            r.id, r.topic, r.subject, f"{r.duration_minutes:.0f}",
            r.course_id or "-", r.created_at,
        )
    return table


def _course_table(records: list) -> Table:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("id")
    table.add_column("topic")
    table.add_column("subject")
    table.add_column("duration (min)", justify="right")
    table.add_column("episodes", justify="right")
    table.add_column("created_at")
    for r in records:
        table.add_row(
            r.id, r.topic, r.subject, f"{r.duration_minutes:.0f}",
            str(r.total_episodes), r.created_at,
        )
    return table


@create_app.command("lecture")
def create_lecture_cmd(
    query: str = typer.Argument(..., help="What the lecture should be about"),
    duration: float = typer.Option(10.0, "--duration", "-d", help="Duration in minutes"),
    subject: str = typer.Option(..., "--subject", "-s", help=f"One of: {', '.join(SUBJECTS)}"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Topic name (defaults to the query)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Also write the generated IR JSON here"),
) -> None:
    record = store.create_lecture(
        query=query,
        topic=topic or query,
        subject=subject,
        duration_minutes=duration,
        output=output,
    )
    console.print(Panel.fit(f"[bold green]Created lecture[/] {record.id}", subtitle=record.topic))
    console.print(f"Play it with: [bold]aos play {record.id}[/]")


@create_app.command("course")
def create_course_cmd(
    query: str = typer.Argument(..., help="What the course should be about"),
    duration: float = typer.Option(10.0, "--duration", "-d", help="Total duration in minutes"),
    totalepisodes: int = typer.Option(10, "--totalepisodes", "-e", help="Number of episodes"),
    subject: str = typer.Option(..., "--subject", "-s", help=f"One of: {', '.join(SUBJECTS)}"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Topic name (defaults to the query)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Also write the generated course JSON here"),
) -> None:
    record = store.create_course(
        query=query,
        topic=topic or query,
        subject=subject,
        duration_minutes=duration,
        total_episodes=totalepisodes,
        output=output,
    )
    console.print(Panel.fit(f"[bold green]Created course[/] {record.id}", subtitle=record.topic))
    console.print(f"Play it with: [bold]aos play {record.id}[/]")


@list_app.command("lectures")
def list_lectures_cmd() -> None:
    records = store.list_lectures()
    if not records:
        console.print("[dim]No lectures yet. Try: aos create lecture \"...\"[/]")
        return
    console.print(_lecture_table(records))


@list_app.command("courses")
def list_courses_cmd() -> None:
    records = store.list_courses()
    if not records:
        console.print("[dim]No courses yet. Try: aos create course \"...\"[/]")
        return
    console.print(_course_table(records))


@search_app.command("lectures")
def search_lectures_cmd(query: str = typer.Argument(..., help="Text to search for")) -> None:
    records = store.search_lectures(query)
    if not records:
        console.print(f"[dim]No lectures match '{query}'.[/]")
        return
    console.print(_lecture_table(records))


@search_app.command("courses")
def search_courses_cmd(query: str = typer.Argument(..., help="Text to search for")) -> None:
    records = store.search_courses(query)
    if not records:
        console.print(f"[dim]No courses match '{query}'.[/]")
        return
    console.print(_course_table(records))


@app.command("play")
def play_cmd(item_id: str = typer.Argument(..., help="A lecture or course id (or unambiguous prefix)")) -> None:
    result = store.resolve(item_id)
    if result is None:
        console.print(f"[bold red]No lecture or course matches '{item_id}'.[/]")
        raise typer.Exit(code=1)

    kind, record = result
    if kind == "lecture":
        path = store.render_lecture_player(record)
    else:
        episodes = [store.load_lecture(eid) for eid in record.episode_ids]
        path = store.render_course_player(record, [e for e in episodes if e is not None])

    webbrowser.open(path.resolve().as_uri())
    console.print(f"Opened [bold]{path}[/]")


if __name__ == "__main__":
    app()
