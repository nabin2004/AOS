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
@click.argument("topic", default=None, required=False)
@click.option(
    "--stage", "-s",
    type=click.Choice(["all", "classify", "compose", "code", "preflight", "repair"]),
    default="all",
    help="Pipeline stage to execute",
)
@click.option("--dir", "-d", "workspace_dir", default=None, help="Directory for structural JSON and Python artifacts")
@click.option("--mock", is_flag=True, help="Run offline using Pydantic AI TestModel (0 API tokens)")
@click.option("--model", "-m", default=None, help="LLM model override")
@click.option("--file", "-f", default=None, help="Python source file for preflight or repair")
@click.option("--error", "-e", default=None, help="Traceback or compiler error for repair")
@click.option("--inject-mobject-bug", is_flag=True, help="Inject intentional mobject index error to test repair agent")
@click.option("--render", is_flag=True, help="Verify scene compilation with local `manim -ql`")
@click.option("--inspect-last", is_flag=True, help="Inspect details of the most recent local run")
@click.option("--verbose", "-v", is_flag=True, help="Show full prompts and verbose conversation traces")
def hitl_cmd(
    topic: str | None,
    stage: str,
    workspace_dir: str | None,
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
        HitlWorkspace,
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
    workspace = HitlWorkspace(workspace_dir=workspace_dir)
    observer = HitlTerminalObserver(verbose=verbose)

    if inspect_last:
        inspect_last_run(run_store, observer, workspace=workspace)
        return

    if stage == "preflight":
        run_preflight_inspector(file, None if file else topic, observer, run_store, workspace=workspace)
        return

    async def _runner() -> None:
        observer.banner(
            "AOS HITL Local Development Runner",
            f"Mode: {'MOCK (Pydantic AI TestModel)' if mock else 'LIVE LLM'}  |  Stage: {stage.upper()}  |  Workspace: {workspace.workspace_dir.name}",
        )
        observer.step("WORKSPACE", f"Active directory: [bold cyan]{workspace.workspace_dir}[/bold cyan]")

        if not mock:
            try:
                hitl_agents._resolve_llm_config(model_name=model)
            except ValueError as exc:
                observer.error(str(exc))
                observer.console.print(
                    "\n[bold yellow]Tip:[/bold yellow] To test offline without an API key, add the [bold cyan]--mock[/bold cyan] flag:\n"
                    f"  [green]aos cmd hitl --mock \"{topic or 'Fourier Transform'}\"[/green]\n"
                )
                return

        # CLASSIFY
        if stage in ("classify", "all"):
            text_to_classify = topic
            if not text_to_classify:
                inp = workspace.load_input()
                if inp and inp.get("text"):
                    text_to_classify = inp["text"]
                    observer.step("WORKSPACE", f"Loaded input query from [bold cyan]{workspace.input_file.name}[/bold cyan]")
                else:
                    text_to_classify = "Fourier Transform"

            workspace.save_input(text_to_classify)
            res = await run_classify_stage(
                text_to_classify,
                observer,
                run_store,
                workspace=workspace,
                mock=mock,
                model_name=model,
            )
            if not res.animatable and stage == "all":
                observer.warning("Content classified as non-animatable. Halting pipeline.")
                return
            current_topic = res.topic or text_to_classify
            current_text = text_to_classify
        else:
            class_data = workspace.load_classification()
            if topic:
                current_topic = topic
                current_text = topic
            elif class_data:
                current_topic = class_data.get("topic") or "Fourier Transform"
                current_text = class_data.get("query") or current_topic
                observer.step("WORKSPACE", f"Loaded topic '[bold green]{current_topic}[/bold green]' from [bold cyan]{workspace.classification_file.name}[/bold cyan]")
            else:
                inp = workspace.load_input()
                if inp:
                    current_topic = inp.get("topic") or inp.get("text", "Fourier Transform")[:30]
                    current_text = inp.get("text") or current_topic
                else:
                    current_topic = "Fourier Transform"
                    current_text = "Fourier Transform"

        # COMPOSE
        if stage in ("compose", "all"):
            plan = await run_compose_stage(
                current_text,
                current_topic,
                observer,
                run_store,
                workspace=workspace,
                mock=mock,
                model_name=model,
            )
        else:
            loaded_plan, loaded_topic = workspace.load_plan()
            if loaded_plan:
                plan = loaded_plan
                if loaded_topic and not topic:
                    current_topic = loaded_topic
                observer.step("WORKSPACE", f"Loaded visual plan from [bold cyan]{workspace.plan_md_file.name}[/bold cyan]")
            else:
                from dev_hitl import MOCK_PLAN
                plan = MOCK_PLAN

        # CODE
        if stage in ("code", "all"):
            code, scene_name = await run_code_stage(
                plan,
                current_topic,
                observer,
                run_store,
                workspace=workspace,
                mock=mock,
                model_name=model,
                inject_bug=inject_mobject_bug,
            )
        elif file:
            code = Path(file).read_text(encoding="utf-8")
            scene_name = "CustomScene"
        else:
            loaded_code, loaded_scene = workspace.load_code()
            if loaded_code and not inject_mobject_bug:
                code = loaded_code
                scene_name = loaded_scene or "GeneratedScene"
                observer.step("WORKSPACE", f"Loaded existing scene from [bold cyan]{workspace.scene_file.name}[/bold cyan]")
            else:
                from dev_hitl import MOCK_BROKEN_CODE_MOBJECT, MOCK_VALID_CODE
                code = MOCK_BROKEN_CODE_MOBJECT if inject_bug else MOCK_VALID_CODE
                scene_name = "BrokenMobjectScene" if inject_bug else "FourierTransformScene"

        # REPAIR
        if stage == "repair" or (stage == "all" and inject_mobject_bug):
            sample_err = error or workspace.load_error() or (
                "IndexError: list index out of range\n"
                "  File 'scene.py', line 7, in construct\n"
                "    square = formula[5]\n"
                "IndexError: list index out of range"
            )
            code, scene_name = await run_repair_stage(
                code,
                sample_err,
                scene_name,
                observer,
                run_store,
                workspace=workspace,
                mock=mock,
                model_name=model,
            )

        if render:
            run_local_render_check(code, scene_name, observer, workspace=workspace)

        observer.show_workspace_status(workspace)

    asyncio.run(_runner())
