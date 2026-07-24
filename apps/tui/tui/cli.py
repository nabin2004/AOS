"""Typer CLI: ``aos-tui`` entry point."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Annotated, Any

import store
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

APP_NAME = "AOS"
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
ASCII_ART_PATH = PACKAGE_ROOT / "ascii-art.txt"
SUBJECTS = ["math", "cs", "ai"]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

console = Console()
app = typer.Typer(
    name=APP_NAME,
    help="AOS — AI-powered animation system.",
    no_args_is_help=True,
    add_completion=False,
)


def _load_intro_logo() -> str:
    try:
        return ASCII_ART_PATH.read_text(encoding="utf-8").rstrip()
    except Exception:
        return ""


def _play_intro(stream: Any | None = None) -> bool:
    output = stream or sys.stdout
    if not hasattr(output, "isatty") or not output.isatty():
        return False

    logo = _load_intro_logo()
    if not logo.strip():
        return False

    try:
        from terminaltexteffects.effects.effect_beams import Beams
    except ImportError:
        typer.echo(logo)
        return True

    try:
        effect = Beams(logo)
        with effect.terminal_output() as terminal:
            for frame in effect:
                terminal.print(frame)
    except Exception:
        typer.echo(logo)

    return True


def _lecture_table(records: list) -> Table:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("id")
    table.add_column("topic")
    table.add_column("subject")
    table.add_column("duration (min)", justify="right")
    table.add_column("course")
    table.add_column("created_at")
    for record in records:
        table.add_row(
            record.id,
            record.topic,
            record.subject,
            f"{record.duration_minutes:.0f}",
            record.course_id or "-",
            record.created_at,
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
    for record in records:
        table.add_row(
            record.id,
            record.topic,
            record.subject,
            f"{record.duration_minutes:.0f}",
            str(record.total_episodes),
            record.created_at,
        )
    return table


@app.command("doctor")
def doctor_cmd() -> None:
    """Validate bundled assets and local store paths."""
    ok = True

    if ASCII_ART_PATH.is_file():
        typer.secho("ascii-art.txt: OK", fg=typer.colors.GREEN)
    else:
        typer.secho(f"ascii-art.txt: missing ({ASCII_ART_PATH})", fg=typer.colors.RED)
        ok = False

    data_path = store.data_dir()
    if data_path.is_dir():
        typer.secho(f"store data dir: OK ({data_path})", fg=typer.colors.GREEN)
    else:
        typer.secho(f"store data dir: unreachable ({data_path})", fg=typer.colors.RED)
        ok = False

    agents_env = PACKAGE_ROOT.parent / "agents" / ".env"
    if agents_env.is_file():
        typer.secho(f"agents .env: found ({agents_env})", fg=typer.colors.GREEN)
    else:
        typer.secho(
            "agents .env: not found (optional until pipeline commands are wired)",
            fg=typer.colors.YELLOW,
        )

    if not ok:
        raise typer.Exit(code=1)


@app.command("chat")
def chat_cmd() -> None:
    """Interactive prompt loop."""
    console.print("[dim]Enter a prompt, or type exit to quit.[/dim]\n")

    while True:
        try:
            text = Prompt.ask("[bold cyan]>[/]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print()
            break

        if not text:
            continue
        if text.lower() in {"exit", "quit", "q"}:
            break

        # TODO: handle prompt
        console.print(f"[dim]You said:[/dim] {text}")


lecture_typer = typer.Typer(help="Single-lecture planning and generation.")
app.add_typer(lecture_typer, name="lecture")


@lecture_typer.command("plan")
def lecture_plan(
    prompt: Annotated[
        str | None,
        typer.Option("--prompt", "-p", help="Lecture topic to plan"),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Save outline as JSON"),
    ] = None,
) -> None:
    """Plan a single lecture outline (shows outline without generating)."""
    if not prompt:
        prompt = typer.prompt(
            typer.style("Enter lecture topic", fg=typer.colors.CYAN, bold=True)
        )

    typer.secho(f"Planning: {prompt}", fg=typer.colors.CYAN)
    if out:
        typer.echo(f"Would save outline to {out.expanduser()}")
    # TODO: wire apps/agents pipeline


@lecture_typer.command("generate")
def lecture_generate(
    prompt: Annotated[
        str | None,
        typer.Option("--prompt", "-p", help="Lecture topic"),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Output .md path"),
    ] = None,
) -> None:
    """Generate a single lecture from a topic."""
    if not prompt:
        prompt = typer.prompt(
            typer.style("Enter lecture topic", fg=typer.colors.CYAN, bold=True)
        )

    typer.secho(f"Generating: {prompt}", fg=typer.colors.CYAN)
    if out:
        typer.echo(f"Would write lecture to {out.expanduser()}")
    # TODO: wire apps/agents pipeline


course_typer = typer.Typer(help="Multi-lecture course planning and generation.")
app.add_typer(course_typer, name="course")


@course_typer.command("plan")
def course_plan(
    prompt: Annotated[
        str | None,
        typer.Option("--prompt", "-p", help="Course topic to plan"),
    ] = None,
    lectures: Annotated[
        int,
        typer.Option("--lectures", "-n", min=2, max=8, help="Number of lectures (2–8)"),
    ] = 4,
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Save plan as JSON"),
    ] = None,
) -> None:
    """Plan a course curriculum (shows outline without writing lectures)."""
    if not prompt:
        prompt = typer.prompt(
            typer.style("Enter course topic", fg=typer.colors.CYAN, bold=True)
        )

    typer.secho(
        f"Planning course ({lectures} lectures): {prompt}", fg=typer.colors.CYAN
    )
    if out:
        typer.echo(f"Would save plan to {out.expanduser()}")
    # TODO: wire course pipeline


@course_typer.command("generate")
def course_generate(
    prompt: Annotated[
        str | None,
        typer.Option("--prompt", "-p", help="Course topic"),
    ] = None,
    lectures: Annotated[
        int,
        typer.Option("--lectures", "-n", min=2, max=8, help="Number of lectures (2–8)"),
    ] = 4,
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Output directory"),
    ] = None,
) -> None:
    """Generate a full course from a topic."""
    if not prompt:
        prompt = typer.prompt(
            typer.style("Enter course topic", fg=typer.colors.CYAN, bold=True)
        )

    typer.secho(
        f"Generating course ({lectures} lectures): {prompt}",
        fg=typer.colors.CYAN,
    )
    if out:
        typer.echo(f"Would write course to {out.expanduser()}")
    # TODO: wire course pipeline


anim_typer = typer.Typer(help="Manim animation planning and rendering.")
app.add_typer(anim_typer, name="anim")


@anim_typer.command("plan")
def anim_plan(
    lecture_file: Annotated[
        Path | None,
        typer.Argument(help="Lecture .md file to plan scenes for"),
    ] = None,
    prompt: Annotated[
        str | None,
        typer.Option(
            "--prompt", "-p", help="Inline lecture text (alternative to file)"
        ),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Save scene plan as JSON"),
    ] = None,
) -> None:
    """Plan Manim animation scenes for a lecture."""
    if lecture_file is not None:
        path = lecture_file.expanduser().resolve()
        if not path.is_file():
            typer.secho(f"File not found: {path}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        typer.secho(f"Planning scenes for: {path}", fg=typer.colors.CYAN)
    elif prompt:
        typer.secho("Planning scenes for inline prompt", fg=typer.colors.CYAN)
    else:
        typer.secho(
            "Provide a lecture .md file argument or --prompt with lecture text.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    if out:
        typer.echo(f"Would save scene plan to {out.expanduser()}")
    # TODO: wire manim render pipeline


@anim_typer.command("render")
def anim_render(
    lecture_file: Annotated[
        Path | None,
        typer.Argument(help="Lecture .md file to render"),
    ] = None,
    prompt: Annotated[
        str | None,
        typer.Option(
            "--prompt", "-p", help="Inline lecture text (alternative to file)"
        ),
    ] = None,
    out_dir: Annotated[
        Path | None,
        typer.Option(
            "--out-dir", "-o", help="Video output directory (default: videos/)"
        ),
    ] = None,
) -> None:
    """Render Manim animations for a lecture."""
    if lecture_file is not None:
        path = lecture_file.expanduser().resolve()
        if not path.is_file():
            typer.secho(f"File not found: {path}", fg=typer.colors.RED)
            raise typer.Exit(code=1)
        typer.secho(f"Rendering: {path}", fg=typer.colors.CYAN)
    elif prompt:
        typer.secho("Rendering inline prompt", fg=typer.colors.CYAN)
    else:
        typer.secho(
            "Provide a lecture .md file argument or --prompt with lecture text.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    output = out_dir or Path("videos")
    typer.echo(f"Would write videos to {output.expanduser()}")
    # TODO: wire manim render pipeline


library_typer = typer.Typer(help="Browse and manage saved lectures and courses.")
app.add_typer(library_typer, name="library")

library_create_typer = typer.Typer(help="Create a lecture or a course.")
library_list_typer = typer.Typer(help="List saved lectures or courses.")
library_search_typer = typer.Typer(help="Search saved lectures or courses.")
library_typer.add_typer(library_create_typer, name="create")
library_typer.add_typer(library_list_typer, name="list")
library_typer.add_typer(library_search_typer, name="search")


@library_create_typer.command("lecture")
def library_create_lecture(
    query: Annotated[str, typer.Argument(help="What the lecture should be about")],
    duration: Annotated[
        float, typer.Option("--duration", "-d", help="Duration in minutes")
    ] = 10.0,
    subject: Annotated[
        str, typer.Option("--subject", "-s", help=f"One of: {', '.join(SUBJECTS)}")
    ] = ...,
    topic: Annotated[
        str | None,
        typer.Option("--topic", "-t", help="Topic name (defaults to the query)"),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Also write the generated IR JSON here"),
    ] = None,
) -> None:
    """Create a mock-but-schema-valid lecture in the local library."""
    record = store.create_lecture(
        query=query,
        topic=topic or query,
        subject=subject,
        duration_minutes=duration,
        output=output,
    )
    console.print(
        Panel.fit(f"[bold green]Created lecture[/] {record.id}", subtitle=record.topic)
    )
    console.print(f"Play it with: [bold]aos-tui library play {record.id}[/]")


@library_create_typer.command("course")
def library_create_course(
    query: Annotated[str, typer.Argument(help="What the course should be about")],
    duration: Annotated[
        float, typer.Option("--duration", "-d", help="Total duration in minutes")
    ] = 10.0,
    totalepisodes: Annotated[
        int, typer.Option("--totalepisodes", "-e", help="Number of episodes")
    ] = 10,
    subject: Annotated[
        str, typer.Option("--subject", "-s", help=f"One of: {', '.join(SUBJECTS)}")
    ] = ...,
    topic: Annotated[
        str | None,
        typer.Option("--topic", "-t", help="Topic name (defaults to the query)"),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output", "-o", help="Also write the generated course JSON here"
        ),
    ] = None,
) -> None:
    """Create a mock-but-schema-valid course in the local library."""
    record = store.create_course(
        query=query,
        topic=topic or query,
        subject=subject,
        duration_minutes=duration,
        total_episodes=totalepisodes,
        output=output,
    )
    console.print(
        Panel.fit(f"[bold green]Created course[/] {record.id}", subtitle=record.topic)
    )
    console.print(f"Play it with: [bold]aos-tui library play {record.id}[/]")


@library_list_typer.command("lectures")
def library_list_lectures() -> None:
    """List saved lectures."""
    records = store.list_lectures()
    if not records:
        console.print(
            '[dim]No lectures yet. Try: aos-tui library create lecture "..."[/]'
        )
        return
    console.print(_lecture_table(records))


@library_list_typer.command("courses")
def library_list_courses() -> None:
    """List saved courses."""
    records = store.list_courses()
    if not records:
        console.print(
            '[dim]No courses yet. Try: aos-tui library create course "..."[/]'
        )
        return
    console.print(_course_table(records))


@library_search_typer.command("lectures")
def library_search_lectures(
    query: Annotated[str, typer.Argument(help="Text to search for")],
) -> None:
    """Search saved lectures."""
    records = store.search_lectures(query)
    if not records:
        console.print(f"[dim]No lectures match '{query}'.[/]")
        return
    console.print(_lecture_table(records))


@library_search_typer.command("courses")
def library_search_courses(
    query: Annotated[str, typer.Argument(help="Text to search for")],
) -> None:
    """Search saved courses."""
    records = store.search_courses(query)
    if not records:
        console.print(f"[dim]No courses match '{query}'.[/]")
        return
    console.print(_course_table(records))


@library_typer.command("play")
def library_play(
    item_id: Annotated[
        str, typer.Argument(help="A lecture or course id (or unambiguous prefix)")
    ],
) -> None:
    """Open a lecture or course in the browser."""
    result = store.resolve(item_id)
    if result is None:
        console.print(f"[bold red]No lecture or course matches '{item_id}'.[/]")
        raise typer.Exit(code=1)

    kind, record = result
    if kind == "lecture":
        path = store.render_lecture_player(record)
    else:
        episodes = [store.load_lecture(episode_id) for episode_id in record.episode_ids]
        path = store.render_course_player(
            record, [episode for episode in episodes if episode is not None]
        )

    webbrowser.open(path.resolve().as_uri())
    console.print(f"Opened [bold]{path}[/]")


def main() -> None:
    is_tty = getattr(sys.stdout, "isatty", lambda: False)()
    if not sys.argv[1:] and is_tty and _play_intro(sys.stdout):
        typer.echo()
    app()


if __name__ == "__main__":
    main()
