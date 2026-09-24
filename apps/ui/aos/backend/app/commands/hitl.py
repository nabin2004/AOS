"""AOS CLI Command for testing the Pydantic AI HITL pipeline locally.

Allows running stages (classify, compose, code, preflight, repair, all)
from `aos cmd hitl` with local logging and Rich terminal output.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from app.commands import command


@command("hitl", help="Run and test the Pydantic AI HITL pipeline locally")
@click.argument("topic", default="Fourier Transform", required=False)
@click.option(
    "--stage", "-s",
    type=click.Choice(["all", "classify", "compose", "code", "preflight", "repair"]),
    default="all",
    help="Pipeline stage to execute",
)
@click.option("--mock", is_flag=True, help="Run offline using Pydantic AI TestModel (0 API tokens)")
@click.option("--model", "-m", default=None, help="LLM model override")
@click.option("--file", "-f", default=None, help="Python source file for preflight or repair")
@click.option("--error", "-e", default=None, help="Traceback or compiler error for repair")
@click.option("--inject-mobject-bug", is_flag=True, help="Inject intentional mobject index error to test repair agent")
@click.option("--render", is_flag=True, help="Verify scene compilation with local `manim -ql`")
@click.option("--inspect-last", is_flag=True, help="Inspect details of the most recent local run")
@click.option("--verbose", "-v", is_flag=True, help="Show full prompts and verbose conversation traces")
def hitl_cmd(
    topic: str,
    stage: str,
    mock: bool,
    model: str | None,
    file: str | None,
    error: str | None,
    inject_mobject_bug: bool,
    render: bool,
    inspect_last: bool,
    verbose: bool,
) -> None:
    import sys
    backend_dir = str(Path(__file__).resolve().parents[2])
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from dev_hitl import (
        HitlRunStore,
        HitlTerminalObserver,
        disable_logfire_remote,
        inspect_last_run,
        run_classify_stage,
        run_code_stage,
        run_compose_stage,
        run_local_render_check,
        run_preflight_inspector,
        run_repair_stage,
    )
    import app.agents.hitl_agents as hitl_agents

    disable_logfire_remote()
    run_store = HitlRunStore()
    observer = HitlTerminalObserver(verbose=verbose)

    if inspect_last:
        inspect_last_run(run_store, observer)
        return

    if stage == "preflight":
        run_preflight_inspector(file, None if file else topic, observer, run_store)
        return

    async def _runner() -> None:
        observer.banner(
            "AOS HITL Local Development Runner",
            f"Mode: {'MOCK (Pydantic AI TestModel)' if mock else 'LIVE LLM'}  |  Stage: {stage.upper()}",
        )

        if not mock:
            try:
                hitl_agents._resolve_llm_config(model_name=model)
            except ValueError as exc:
                observer.error(str(exc))
                observer.console.print(
                    "\n[bold yellow]Tip:[/bold yellow] To test offline without an API key, add the [bold cyan]--mock[/bold cyan] flag:\n"
                    f"  [green]aos cmd hitl --mock \"{topic}\"[/green]\n"
                )
                return

        # CLASSIFY
        current_topic = topic
        if stage in ("classify", "all"):
            res = await run_classify_stage(topic, observer, run_store, mock=mock, model_name=model)
            if not res.animatable and stage == "all":
                observer.warning("Content classified as non-animatable. Halting pipeline.")
                return
            current_topic = res.topic or topic

        # COMPOSE
        from dev_hitl import MOCK_PLAN, MOCK_VALID_CODE, MOCK_BROKEN_CODE_MOBJECT
        plan = MOCK_PLAN
        if stage in ("compose", "all"):
            plan = await run_compose_stage(topic, current_topic, observer, run_store, mock=mock, model_name=model)

        # CODE
        code = MOCK_VALID_CODE
        scene_name = "FourierTransformScene"
        if stage in ("code", "all"):
            code, scene_name = await run_code_stage(
                plan, current_topic, observer, run_store,
                mock=mock, model_name=model, inject_bug=inject_mobject_bug
            )
        elif file:
            code = Path(file).read_text(encoding="utf-8")
            scene_name = "CustomScene"

        # REPAIR
        if stage == "repair" or (stage == "all" and inject_mobject_bug):
            sample_err = error or (
                "IndexError: list index out of range\n"
                "  File 'scene.py', line 7, in construct\n"
                "    square = formula[5]\n"
                "IndexError: list index out of range"
            )
            code, scene_name = await run_repair_stage(
                code, sample_err, scene_name, observer, run_store, mock=mock, model_name=model
            )

        if render:
            run_local_render_check(code, scene_name, observer)

    asyncio.run(_runner())
